#!/usr/bin/env python3
"""
Android proje fikri tarayıcı.
Reddit ve GitHub'dan "yapılmamış uygulama fikri" sinyallerini toplayıp
Telegram'a günlük özet olarak gönderir.

Gerekli ortam değişkenleri (GitHub Actions secrets olarak eklenecek):
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  GH_TOKEN     (opsiyonel ama önerilir - GitHub arama rate limitini artırır)
  GROQ_API_KEY (opsiyonel - varsa sonuçlar Groq ile değerlendirilip filtrelenir)
"""

import os
import json
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

MIN_UPVOTES = 2          # Reddit gönderisi için minimum oy eşiği
MIN_COMMENTS = 1         # Reddit gönderisi için minimum yorum eşiği
MAX_ITEMS_PER_SECTION = 10   # Groq değerlendirmesi öncesi ham liste boyutu

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MIN_FIT_SCORE = 6        # Groq'un 1-10 uygunluk puanında bu ve üzeri gösterilir

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
                "t": "week",
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
# Groq ile değerlendirme (opsiyonel katman)
# ---------------------------------------------------------------------------

EVAL_SYSTEM_PROMPT = """Sen bir Android bağımsız geliştirici danışmanısın.
Kullanıcının kriteri: minimum zaman, minimum maliyet, maksimum gelir.
Yani tek kişilik, hızlı yapılabilen, niş bir problemi çözen, büyük altyapı
gerektirmeyen Android uygulama fikirlerini arıyor. Büyük açık kaynak
projelerine yapılan teknik feature request'ler (bir kütüphaneye özellik
eklemek gibi) onun için değerli DEĞİLDİR - sadece bağımsız bir uygulama
fikrine dönüşebilecek sinyaller değerlidir.

Sana bir liste JSON gönderilecek. Her öğe için:
- fit_score: 1-10 arası, kullanıcının kriterine ne kadar uyduğu (10 = mükemmel bağımsız app fikri)
- yorum: tek cümlelik Türkçe değerlendirme (neden uygun/değil, varsa rakip durumu)

SADECE aşağıdaki formatta bir JSON array döndür, başka hiçbir açıklama ekleme:
[{"url": "...", "fit_score": 0, "yorum": "..."}, ...]
"""


def evaluate_with_groq(items):
    """Ham liste öğelerini Groq'a gönderip uygunluk skoru ve kısa yorum
    aldırır. GROQ_API_KEY yoksa veya çağrı başarısız olursa, orijinal
    listeyi değişiklik yapmadan döndürür (skorsuz/yorumsuz)."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or not items:
        return items

    payload_items = [{"url": it["url"], "title": it["title"]} for it in items]

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload_items, ensure_ascii=False)},
                ],
                "temperature": 0.3,
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        evaluations = {e["url"]: e for e in json.loads(raw)}
    except Exception as e:
        print(f"[groq] değerlendirme hatası, ham liste kullanılacak: {e}")
        return items

    enriched = []
    for it in items:
        ev = evaluations.get(it["url"])
        if not ev:
            continue
        if ev.get("fit_score", 0) < MIN_FIT_SCORE:
            continue
        it = dict(it)
        it["fit_score"] = ev.get("fit_score")
        it["yorum"] = ev.get("yorum", "")
        enriched.append(it)

    enriched.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    return enriched


# ---------------------------------------------------------------------------
# Telegram gönderimi
# ---------------------------------------------------------------------------

def _format_item(h, source_label):
    line = f"• [{h['title']}]({h['url']}) — {source_label}"
    if "fit_score" in h:
        line += f"\n   ⭐ {h['fit_score']}/10 — {h['yorum']}"
    return line


def format_message(reddit_hits, github_hits):
    lines = ["📱 *Günlük Android Fikir Taraması*", ""]

    lines.append("🔴 *Reddit*")
    if reddit_hits:
        for h in reddit_hits:
            lines.append(_format_item(h, f"r/{h['subreddit']}"))
    else:
        lines.append("_Bu dönem eşik üzerinde/uygun sonuç yok._")

    lines.append("")
    lines.append("🐙 *GitHub*")
    if github_hits:
        for h in github_hits:
            lines.append(_format_item(h, h["repo"]))
    else:
        lines.append("_Bu dönem eşik üzerinde/uygun sonuç yok._")

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
    reddit_hits = evaluate_with_groq(fetch_reddit_hits())
    github_hits = evaluate_with_groq(fetch_github_hits())
    message = format_message(reddit_hits, github_hits)
    send_telegram(message)
    print("Tamamlandı.")
    print(message)


if __name__ == "__main__":
    main()
