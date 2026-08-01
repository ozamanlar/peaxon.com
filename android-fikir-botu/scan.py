#!/usr/bin/env python3
"""
Android proje fikri tarayıcı.
Reddit ve GitHub'dan "yapılmamış uygulama fikri" sinyallerini toplayıp
Telegram'a günlük özet olarak gönderir.

Gerekli ortam değişkenleri (GitHub Actions secrets olarak eklenecek):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  GH_TOKEN (opsiyonel ama önerilir - GitHub arama rate limitini artırır)
"""

import os
import time
import requests

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

SUBREDDITS = [
    "androidapps",
    "AppIdeas",
    "SomebodyMakeThis",
    "SideProject",
    "androiddev",
]

# Reddit'te aratılacak kalıplar - ihtiyaç/talep ifade eden cümle kalıpları
REDDIT_PHRASES = [
    "is there an app",
    "wish there was an app",
    "app idea",
    "why doesn't this exist",
    "someone should build",
    "looking for an app that",
]

# GitHub arama sorguları - Android/Kotlin ekosisteminde tekrarlanan
# feature request / boşluk sinyalleri
GITHUB_QUERIES = [
    'language:Kotlin "feature request" in:title,body android',
    'topic:android-app "please add" in:body',
]

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
REDDIT_HEADERS = {"User-Agent": "android-fikir-botu/1.0"}
GITHUB_HEADERS = {"Accept": "application/vnd.github+json"}

MIN_UPVOTES = 5          # Reddit gönderisi için minimum oy eşiği
MIN_COMMENTS = 3         # Reddit gönderisi için minimum yorum eşiği
MAX_ITEMS_PER_SECTION = 8

gh_token = os.environ.get("GH_TOKEN")
if gh_token:
    GITHUB_HEADERS["Authorization"] = f"Bearer {gh_token}"


# ---------------------------------------------------------------------------
# Reddit tarama
# ---------------------------------------------------------------------------

def fetch_reddit_hits():
    """Belirlenen subredditlerde, son 1 gün içinde, belirlenen kalıpları
    içeren gönderileri arar. Reddit'in genel (auth gerektirmeyen) arama
    JSON endpoint'ini kullanır."""
    hits = []
    for sub in SUBREDDITS:
        for phrase in REDDIT_PHRASES:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {
                "q": phrase,
                "restrict_sr": 1,
                "sort": "new",
                "t": "day",
                "limit": 15,
            }
            try:
                resp = requests.get(url, headers=REDDIT_HEADERS, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[reddit] r/{sub} '{phrase}' hata: {e}")
                continue

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                ups = post.get("ups", 0)
                comments = post.get("num_comments", 0)
                if ups < MIN_UPVOTES and comments < MIN_COMMENTS:
                    continue
                hits.append({
                    "title": post.get("title", "").strip(),
                    "url": "https://reddit.com" + post.get("permalink", ""),
                    "subreddit": sub,
                    "score": ups + comments * 2,  # yorum ağırlıklı skor
                })
            time.sleep(1)  # Reddit'e nazik davran

    # aynı gönderi birden fazla kalıpla eşleşmiş olabilir -> tekilleştir
    seen = {}
    for h in hits:
        seen[h["url"]] = h
    result = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return result[:MAX_ITEMS_PER_SECTION]


# ---------------------------------------------------------------------------
# GitHub tarama
# ---------------------------------------------------------------------------

def fetch_github_hits():
    """GitHub Search API ile son 1 gün içinde açılmış, Android/Kotlin
    ekosisteminde 'feature request' / boşluk sinyali veren issue'ları arar."""
    hits = []
    since = "created:>=" + time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400))
    for query in GITHUB_QUERIES:
        url = "https://api.github.com/search/issues"
        params = {"q": f"{query} {since}", "sort": "reactions", "order": "desc", "per_page": 10}
        try:
            resp = requests.get(url, headers=GITHUB_HEADERS, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[github] '{query}' hata: {e}")
            continue

        for item in data.get("items", []):
            hits.append({
                "title": item.get("title", "").strip(),
                "url": item.get("html_url", ""),
                "repo": item.get("repository_url", "").split("/")[-1],
                "score": item.get("reactions", {}).get("total_count", 0) + item.get("comments", 0),
            })
        time.sleep(1)

    seen = {}
    for h in hits:
        seen[h["url"]] = h
    result = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return result[:MAX_ITEMS_PER_SECTION]


# ---------------------------------------------------------------------------
# Telegram gönderimi
# ---------------------------------------------------------------------------

def format_message(reddit_hits, github_hits):
    lines = ["📱 *Günlük Android Fikir Taraması*", ""]

    lines.append("🔴 *Reddit*")
    if reddit_hits:
        for h in reddit_hits:
            lines.append(f"• [{h['title']}]({h['url']}) — r/{h['subreddit']}")
    else:
        lines.append("_Bugün eşik üzerinde sonuç yok._")

    lines.append("")
    lines.append("🐙 *GitHub*")
    if github_hits:
        for h in github_hits:
            lines.append(f"• [{h['title']}]({h['url']}) — {h['repo']}")
    else:
        lines.append("_Bugün eşik üzerinde sonuç yok._")

    return "\n".join(lines)


def send_telegram(message):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = TELEGRAM_API.format(token=token)

    # Telegram mesaj limiti 4096 karakter - gerekirse böl
    chunks = [message[i:i + 4000] for i in range(0, len(message), 4000)] or [message]
    for chunk in chunks:
        resp = requests.post(url, data={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=15)
        if not resp.ok:
            print(f"[telegram] gönderim hatası: {resp.status_code} {resp.text}")
        time.sleep(1)


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------

def main():
    reddit_hits = fetch_reddit_hits()
    github_hits = fetch_github_hits()
    message = format_message(reddit_hits, github_hits)
    send_telegram(message)
    print("Tamamlandı.")
    print(message)


if __name__ == "__main__":
    main()
