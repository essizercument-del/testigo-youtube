# Testigo YouTube

Testigo ölçümlerinden her gün otomatik dikey video (Shorts) üretip YouTube'a yükler.
Seslendirme yok: ekran yazısı + animasyonlu grafik + arka plan müziği.

## Nasıl çalışır

1. `data/olcumler.json` içindeki ölçümlerden sıradaki video seçilir
   (önce her cihazın kendi videosu, sonra sıralama, sonra ikili kıyaslar).
2. Video kare kare çizilir, ffmpeg ile MP4 yapılır (1080×1920, 30 fps).
3. YouTube'a yüklenir, `data/durum.json` güncellenir ve repo'ya kaydedilir.
4. GitHub Actions bunu her gün 09:47'de (TR) kendiliğinden yapar.

## Yeni ölçüm eklemek

`data/olcumler.json` dosyasına bir kayıt ekle. İki tür var:

**Dönem ölçümü** (prizde günlerce ölçülen cihaz):
```json
{
  "id": "camasir-makinesi",
  "cihaz": "Marka Model Çamaşır Makinesi",
  "kisa_ad": "Çamaşır makinesi",
  "tip": "donem",
  "kwh": 18.4,
  "gun": 30,
  "anlik_watt": 2100,
  "link": "https://testigotr.com.tr/yazi-adresi/",
  "etiketler": ["çamaşır makinesi elektrik tüketimi"]
}
```

**Kullanım başına ölçüm** (kettle, kurutma makinesi gibi):
```json
{
  "id": "ornek-kettle",
  "cihaz": "Marka Model Su Isıtıcı",
  "kisa_ad": "Su ısıtıcı",
  "tip": "kullanim",
  "kwh": 0.121,
  "kullanim_adi": "kaynatma",
  "sure_sn": 205,
  "haftalik_kullanim": 14,
  "anlik_watt": 2069
}
```

İsteğe bağlı alanlar: `anlik_watt`, `sure_sn`, `haftalik_kullanim` (varsa aylık tahmin yapılır),
`not` (ölçüm ekranında küçük not), `soru` (açılış sorusunu değiştirir), `link`, `etiketler`.
`id` benzersiz olmalı ve değiştirilmemeli.

## Görsel ve klip eklemek

`media/<id>/` klasörüne koy (örn. `media/buzdolabi/`):
- `.jpg/.png` → açılış ve ölçüm sahnesinin arka planı (yavaş yakınlaştırmalı)
- `.mp4/.mov` → ölçüm sahnesinin arka planı (5–10 sn yeter, dikeye kırpılır)

Görsel yoksa koyu tasarım zemini kullanılır.

## Müzik

`assets/muzik/` klasörüne telifsiz parça (mp3/m4a/wav) koyarsan her video için birini seçer.
YouTube Studio → Ses Kitaplığı'ndaki parçalar uygun. Klasör boşsa basit bir ambiyans altlığını kendisi üretir.

## Elle çalıştırma

GitHub → **Actions → Günlük video → Run workflow**
- `yukle` kapalı: sadece video üretilir, sayfanın altındaki **Artifacts**'tan indirilir (önizleme için).
- `plan`: belirli bir video, örn. `tek:buzdolabi`, `siralama:4`, `kiyas:buzdolabi+sigma-comfort-klima`.

Bilgisayarda:
```
pip install -r requirements.txt
python -m testigo_yt --liste                  # tüm planlar ve durumları
python -m testigo_yt --onizleme               # sıradakini üret, out/ altına video + kareler
python -m testigo_yt --plan tek:buzdolabi
```

## Ayarlar (`config.json`)

- `tarife`: kademe sınırı ve TL/kWh fiyatları (tarife değişince buradan güncelle)
- `yukleme.gizlilik`: `private` / `unlisted` / `public`
- `video.muzik_ses_db`: müzik seviyesi

## Secrets

Repo → Settings → Secrets and variables → Actions:
`YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` (hepsi `get_token.py` çıktısından).

Google Cloud'daki uygulama "Test" modundaysa refresh token 7 günde bir sona erer.
O durumda `get_token.py`'yi tekrar çalıştırıp `YT_REFRESH_TOKEN`'ı güncelle.
Kalıcı çözüm: gizlilik politikası + hizmet şartları sayfalarını ekleyip uygulamayı yayınlamak.

Doğrulanmamış (denetimden geçmemiş) API projeleriyle yüklenen videoları YouTube private olarak kilitler.
Public yayın için Google'ın YouTube API denetim formu doldurulmalı; o zamana kadar videoları
Studio'dan elle public yap.
