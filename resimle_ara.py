"""İnternette aynı/benzer ürünleri bulur (SerpApi Google Lens).

SERPAPI_KEY yoksa ya da fotoğrafın internetten erişilebilir adresi yoksa SAHTE örnek döner.
Bulamadığı bilgiyi None bırakır; rakam uydurmaz.
"""
import json
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request

SERPAPI_URL = "https://serpapi.com/search.json"
ZAMAN_ASIMI = 20  # saniye


def _sahte():
    return {
        "sahte": True,
        "durum": "Arama yapılmadı: SERPAPI_KEY ya da fotoğrafın internet adresi yok (sahte örnek gösteriliyor).",
        "birebir_bulundu": False,
        "benzer_sayisi": 14,
        "fiyat_min": 240.0,
        "fiyat_max": 420.0,
        "ilgi": "orta",
        "fiyat_medyan": 329.0,
        "en_ucuz": [
            {"site": "ornek-site-1.com", "baslik": "Örnek ürün", "fiyat": 249.9},
            {"site": "ornek-site-2.com", "baslik": "Örnek ürün", "fiyat": 329.0},
        ],
        "en_yorumlu": [
            {"site": "ornek-site-3.com", "baslik": "Örnek ürün", "fiyat": 399.0, "yorum": 120, "puan": 4.5},
        ],
    }


def _bos(hata):
    return {
        "sahte": False, "durum": hata, "birebir_bulundu": False, "benzer_sayisi": None,
        "fiyat_min": None, "fiyat_max": None, "ilgi": None, "fiyat_medyan": None, "en_ucuz": [], "en_yorumlu": [], "hata": hata,
    }


def _tl_mi(fiyat):
    """Fiyat Türk lirası mı? SerpApi 'currency' (₺/TRY/TL) ya da 'value' yazısına bakar; emin değilse hayır."""
    birim = str(fiyat.get("currency") or "").strip().upper()
    if birim in ("₺", "TRY", "TL"):
        return True
    if birim:
        return False
    yazi = str(fiyat.get("value") or "").upper()
    return "₺" in yazi or "TL" in yazi or "TRY" in yazi


def ara(foto_bytes, analiz, foto_url=None, firma="", kategori="", model=""):
    """Her raporda SerpApi'ye yalnızca 1 sorgu atar (Google Lens, visual_matches)."""
    anahtar = os.getenv("SERPAPI_KEY")
    if not anahtar or not foto_url or "localhost" in foto_url or "127.0.0.1" in foto_url:
        return _sahte()
    metin = " ".join(x for x in (firma, model, kategori if kategori != "diğer" else "") if x).strip()
    parametre = {
        "engine": "google_lens", "url": foto_url, "type": "visual_matches",
        "hl": "tr", "country": "tr", "api_key": anahtar,
    }
    if metin:
        parametre["q"] = metin  # firma + model + kategori: Lens aramasını doğru ürüne yönlendirir
    try:
        with urllib.request.urlopen(f"{SERPAPI_URL}?{urllib.parse.urlencode(parametre)}", timeout=ZAMAN_ASIMI) as r:
            veri = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            mesaj = json.load(e).get("error")
        except Exception:
            mesaj = None
        return _bos("Arama servisi hata verdi: HTTP " + str(e.code) + (f": {mesaj}" if mesaj else ""))
    except Exception as e:  # ağ hatası / zaman aşımı
        return _bos(f"Arama servisine ulaşılamadı ({type(e).__name__}).")
    if veri.get("error"):
        return _bos(f"Arama servisi hata verdi: {veri['error']}")

    eslesmeler = veri.get("visual_matches") or []
    liste, doviz = [], 0
    for e in eslesmeler:
        p = e.get("price") or {}
        fiyat = p.get("extracted_value")
        if isinstance(fiyat, (int, float)) and fiyat > 0 and not _tl_mi(p):
            doviz += 1
            fiyat = None  # döviz fiyatı kullanılmaz
        yorum = e.get("reviews")
        puan = e.get("rating")
        liste.append({
            "site": e.get("source") or "bulamadım",
            "baslik": e.get("title") or "bulamadım",
            "fiyat": float(fiyat) if isinstance(fiyat, (int, float)) and fiyat > 0 else None,
            "yorum": int(yorum) if isinstance(yorum, (int, float)) else None,
            "puan": float(puan) if isinstance(puan, (int, float)) else None,
            "link": e.get("link"),
            "resim": e.get("thumbnail") or e.get("image"),
        })
    fiyatlar = sorted(x["fiyat"] for x in liste if x["fiyat"] is not None)
    en_ucuz = sorted((x for x in liste if x["fiyat"] is not None), key=lambda x: x["fiyat"])[:5]
    en_yorumlu = sorted((x for x in liste if x["yorum"]), key=lambda x: -x["yorum"])[:5]
    if eslesmeler:
        durum = f"Google Lens arandı, {len(eslesmeler)} eşleşme geldi."
        if doviz:
            durum += f" {doviz} döviz fiyatı hesaba katılmadı."
    else:
        durum = "Google Lens arandı ama eşleşme gelmedi."
    return {
        "sahte": False,
        "durum": durum,
        "birebir_bulundu": False,  # görsel eşleşme birebir model kanıtı değildir
        "benzer_sayisi": len(eslesmeler) if eslesmeler else None,
        "fiyat_min": fiyatlar[0] if fiyatlar else None,
        "fiyat_max": fiyatlar[-1] if fiyatlar else None,
        "fiyat_medyan": statistics.median(fiyatlar) if fiyatlar else None,
        "ilgi": None,  # bu servis satış/ilgi verisi vermez; yorum sayısı varsa listede gösterilir
        "en_ucuz": en_ucuz,
        "en_yorumlu": en_yorumlu,
    }
