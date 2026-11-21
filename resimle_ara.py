"""İnternette aynı/benzer ürünleri bulur (SerpApi Google Lens).

SERPAPI_KEY yoksa ya da fotoğrafın internetten erişilebilir adresi yoksa SAHTE örnek döner.
Bulamadığı bilgiyi None bırakır; rakam uydurmaz.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

SERPAPI_URL = "https://serpapi.com/search.json"


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


def ara(foto_bytes, analiz, foto_url=None, firma="", kategori=""):
    anahtar = os.getenv("SERPAPI_KEY")
    if not anahtar or not foto_url or "localhost" in foto_url or "127.0.0.1" in foto_url:
        return _sahte()
    metin = " ".join(x for x in (firma, kategori if kategori != "diğer" else "") if x).strip()

    def sorgula(tur, firma_ile=True):
        parametre = {
            "engine": "google_lens", "url": foto_url, "type": tur,
            "hl": "tr", "country": "tr", "api_key": anahtar,
        }
        if metin and firma_ile:
            parametre["q"] = metin  # firma + kategori: Lens aramasını doğru ürüne yönlendirir
        sorgu = urllib.parse.urlencode(parametre)
        try:
            with urllib.request.urlopen(f"{SERPAPI_URL}?{sorgu}", timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            try:
                mesaj = json.load(e).get("error")
            except Exception:
                mesaj = None
            return {"error": f"HTTP {e.code}" + (f": {mesaj}" if mesaj else "")}

    eslesmeler, veri, denenen, hatalar = [], {}, [], []
    for tur in ("visual_matches", "exact_matches"):  # Google'ın şu an desteklediği modlar
        try:
            veri = sorgula(tur)
            if metin and (veri.get("error") or not (veri.get("visual_matches") or veri.get("exact_matches"))):
                veri = sorgula(tur, firma_ile=False)  # yazıyla sonuç gelmediyse yalnızca fotoğrafla dene
        except Exception as e:  # ağ hatası
            hatalar.append(f"{tur}: {type(e).__name__}")
            continue
        if veri.get("error"):
            hatalar.append(f"{tur}: {veri['error']}")
            continue
        denenen.append(tur)
        eslesmeler = veri.get("visual_matches") or veri.get("exact_matches") or []
        if eslesmeler:
            break
    if not eslesmeler and hatalar and not denenen:
        return _bos("Arama servisi hata verdi: " + " | ".join(hatalar))

    liste = []
    for e in eslesmeler:
        fiyat = (e.get("price") or {}).get("extracted_value")
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
        durum = f"Google Lens arandı ({denenen[-1]}), {len(eslesmeler)} eşleşme geldi."
    else:
        durum = ("Google Lens arandı (" + ", ".join(denenen) + ") ama eşleşme gelmedi. "
                 "Servisin cevabındaki başlıklar: " + ", ".join(sorted(veri.keys()))
                 + (" | Hatalar: " + " | ".join(hatalar) if hatalar else ""))
    return {
        "sahte": False,
        "durum": durum,
        "birebir_bulundu": False,  # görsel eşleşme birebir model kanıtı değildir
        "benzer_sayisi": len(eslesmeler) if eslesmeler else None,
        "fiyat_min": fiyatlar[0] if fiyatlar else None,
        "fiyat_max": fiyatlar[-1] if fiyatlar else None,
        "fiyat_medyan": fiyatlar[len(fiyatlar) // 2] if fiyatlar else None,
        "ilgi": None,  # bu servis satış/ilgi verisi vermez; yorum sayısı varsa listede gösterilir
        "en_ucuz": en_ucuz,
        "en_yorumlu": en_yorumlu,
    }
