"""İnternette aynı/benzer ürünleri bulur. ŞİMDİLİK SAHTE örnek döndürür.

İleride: Google Cloud Vision Web Detection (GOOGLE_VISION_API_KEY).
Bulamadığı bilgiyi None olarak bırakmalı; rakam uydurulmamalı.
"""
import os


def ara(foto_bytes, analiz):
    anahtar = os.getenv("GOOGLE_VISION_API_KEY")  # ileride kullanılacak
    # TODO: anahtar varsa Web Detection çağır, aşağıdaki biçimde sonuç dön.
    return {
        "sahte": True,
        "birebir_bulundu": False,  # False ise rapor en başta bunu söyler
        "benzer_sayisi": 14,
        "fiyat_min": 240.0,
        "fiyat_max": 420.0,
        "ilgi": "orta",  # düşük / orta / yüksek / None (bilinmiyorsa)
        "ornekler": [
            {"site": "ornek-site-1.com", "fiyat": 249.9},
            {"site": "ornek-site-2.com", "fiyat": 329.0},
            {"site": "ornek-site-3.com", "fiyat": 399.0},
        ],
    }
