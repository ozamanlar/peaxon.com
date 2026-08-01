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
- Günlük çalıştığı için sadece son 24 saatteki içerikleri tarar
  (`t=day` ve `created:>=` filtreleri bu yüzden var).
