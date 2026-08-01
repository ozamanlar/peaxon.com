# Android Fikir Botu

Reddit ve GitHub'ı günlük tarayıp yapılmamış uygulama fikri sinyallerini
Telegram'a gönderen otomasyon.

## Kurulum

1. Bu klasörü kendi GitHub reponda yayınla (public veya private, fark etmez).

2. Telegram bot oluştur:
   - Telegram'da **@BotFather**'a git, `/newbot` yaz, adını belirle.
   - Sana verdiği **token**'ı not al.

3. Chat ID'ni öğren:
   - Oluşturduğun botla Telegram'da bir mesaj at (örn. "merhaba").
   - Tarayıcıda şu adrese git: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Dönen JSON içinde `"chat":{"id": ...}` alanındaki sayı senin chat_id'in.

4. Repo ayarlarında secret ekle:
   - GitHub repo → Settings → Secrets and variables → Actions → New repository secret
   - `TELEGRAM_BOT_TOKEN` → bot token'ı
   - `TELEGRAM_CHAT_ID` → chat id'yi
   - `GROQ_API_KEY` → (opsiyonel ama önerilir) console.groq.com üzerinden ücretsiz alınan API key.
     Bu key olmadan da script çalışır, sadece ham liste gönderir (skor/yorum olmadan).

5. Workflow otomatik olarak her gün 07:00 (İstanbul saati) çalışır.
   İstersen Actions sekmesinden "Run workflow" ile elle de tetikleyebilirsin.

## Ayarları değiştirmek

`scan.py` içindeki şu listeler üzerinden özelleştirebilirsin:
- `SUBREDDITS` — taranacak subredditler
- `REDDIT_PHRASES` — aranacak talep kalıpları
- `GITHUB_QUERIES` — GitHub arama sorguları
- `MIN_UPVOTES` / `MIN_COMMENTS` — Reddit için eşik değerleri

## Notlar

- Reddit tarafı auth gerektirmez (genel JSON API kullanılıyor), bu yüzden
  rate limit'e takılmamak için istekler arasında 1 saniye bekletiliyor.
- GitHub tarafı `secrets.GITHUB_TOKEN` (Actions'ın otomatik sağladığı token)
  ile çalışır, ekstra bir şey yapmana gerek yok.
- Reddit tarafı son 1 haftayı tarar (`t=week`), GitHub tarafı son 1 günü
  tarar (`created:>=`). Reddit'te günlük pencere çoğu zaman boş sonuç
  verdiği için haftalık tutuldu — günlük çalıştığında tekrar eden sonuçlar
  görebilirsin, bu normaldir.
- `GROQ_API_KEY` tanımlıysa, toplanan ham sonuçlar Groq'a (llama-3.3-70b)
  gönderilip senin "minimum zaman/maliyet, niş problem" kriterine göre
  1-10 puanlanır ve `MIN_FIT_SCORE` (varsayılan 6) altındakiler elenir.
  Groq ücretsiz kotasını console.groq.com üzerinden görebilirsin.
