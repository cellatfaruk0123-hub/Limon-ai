# Limon Çocuk – Ürün Testi (iskelet)

Toptancıda görülen çocuk takımının fotoğrafını yükleyip alış fiyatı, adet ve kumaş bilgisini girince
altı maddelik bir rapor çıkaran küçük web sayfası: karar, satma ihtimali, internetteki benzerleri,
satış fiyatı ve kâr, beden/renk önerisi, zamanlama.

**Durum:** Bu bir iskelettir. Rapordaki içerik SAHTE ÖRNEKTİR (en üstte kırmızı uyarı çıkar).
Sadece "Satış fiyatı ve kâr" (KDV %10) gerçek hesaplanır. Bilgi bulunamazsa "bulamadım" yazılır.

## Dosyalar
- `app.py` – web sunucusu (Flask)
- `templates/index.html` – tek sayfa (telefona uygun)
- `foto_analiz.py` – fotoğrafı yorumlar (ileride Gemini ücretsiz anahtarıyla)
- `resimle_ara.py` – internette benzer ürün arar (ileride Google Cloud Vision Web Detection ile)
- `rapor.py` – raporu birleştirir, kâr hesabını yapar
- `.env.example` – anahtarlar için örnek; `.env` olarak kopyalayıp doldurulur

## Çalıştırma
```
pip install -r requirements.txt
python app.py
```
Sonra tarayıcıda `http://localhost:5000` açılır. Anahtarlar kodun içine yazılmaz, `.env` dosyasından okunur.

## Servisleri bağlama (sonra)
`foto_analiz.py` ve `resimle_ara.py` içindeki `TODO` yerlerine gerçek servis çağrısı yazılır;
fonksiyonların döndürdüğü sözlük biçimi aynı kaldığı sürece diğer dosyalar değişmez.
