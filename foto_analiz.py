"""Fotoğrafı yorumlar. ŞİMDİLİK SAHTE örnek döndürür.

İleride: Gemini (ücretsiz anahtar, GEMINI_API_KEY) ile gerçek yorum.
Bu fonksiyonun aynı biçimde sözlük döndürmesi yeterli; rapor.py değişmez.
"""
import os


def analiz_et(foto_bytes):
    anahtar = os.getenv("GEMINI_API_KEY")  # ileride kullanılacak
    # TODO: anahtar varsa Gemini'ye fotoğrafı gönder, aşağıdaki biçimde sonuç dön.
    return {
        "sahte": True,
        "urun_turu": "Çocuk pijama takımı (örnek)",
        "renkler": ["pembe", "krem", "gri melanj"],
        "desen": "Küçük ayıcık baskılı (örnek)",
        "kumas_tahmini": "bulamadım",
    }
