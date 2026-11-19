"""Raporu birleştirir. Kâr hesabı GERÇEK, diğer içerik şimdilik sahte."""
import foto_analiz
import resimle_ara

KDV = 0.10


def _tl(x):
    return f"{x:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")


def kar_hesapla(alis, kdv_dahil, adet, satis):
    """Satış fiyatı KDV dahil etiket fiyatıdır. Alış KDV'si indirilebilir kabul edilir."""
    alis_hariç = alis / (1 + KDV) if kdv_dahil else alis
    onerildi = False
    if satis is None:
        # Basit öneri kuralı: KDV hariç alışın 2 katı + KDV, 5'e yuvarla.
        satis = round(alis_hariç * 2 * (1 + KDV) / 5) * 5
        onerildi = True
    satis_hariç = satis / (1 + KDV)
    adet_kar = satis_hariç - alis_hariç
    return {
        "satis": satis,
        "onerildi": onerildi,
        "alis_hariç": alis_hariç,
        "odenecek_kdv": satis - satis_hariç,
        "adet_kar": adet_kar,
        "toplam_kar": adet_kar * adet,
        "kar_orani": (adet_kar / alis_hariç * 100) if alis_hariç else None,
        "toplam_yatirim": alis_hariç * adet,
    }


def hazirla(foto_bytes, alis, kdv_dahil, adet, kumas, satis, foto_url=None):
    analiz = foto_analiz.analiz_et(foto_bytes)
    web = resimle_ara.ara(foto_bytes, analiz, foto_url)
    kar = kar_hesapla(alis, kdv_dahil, adet, satis)

    uyarilar = []
    if not web.get("birebir_bulundu"):
        uyarilar.append("İnternette birebir aynı modeli bulamadım; aşağıdakiler yalnızca benzer ürünlerdir.")
    if web.get("hata"):
        uyarilar.append(web["hata"])

    if web.get("fiyat_min") is not None:
        fiyat = f"{_tl(web['fiyat_min'])} – {_tl(web['fiyat_max'])}"
    else:
        fiyat = "bulamadım"

    sahte = bool(analiz.get("sahte") or web.get("sahte"))
    if analiz.get("sahte") and web.get("sahte"):
        ust = "Bu örnek sonuçtur, gerçek analiz değildir."
    elif analiz.get("sahte"):
        ust = ("Dikkat: karar, satma ihtimali, beden-renk ve zamanlama hâlâ ÖRNEKTİR. "
               "İnternetteki benzerler ve kâr hesabı gerçektir.")
    else:
        ust = None
    return {
        "sahte": sahte,
        "ust_uyari": ust,
        "uyarilar": uyarilar,
        "karar": {
            "etiket": "Az al",
            "renk": "sari",
            "gerekce": "Örnek karar: benzer ürünler var, ilgi orta.",
        },
        "ihtimal": {
            "yuzde": "%55 (örnek)" if sahte else "bulamadım",
            "gerekce": "Örnek gerekçe: fiyat piyasa aralığında, ama birebir model bulunamadı.",
        },
        "benzerler": {
            "adet": web.get("benzer_sayisi") if web.get("benzer_sayisi") is not None else "bulamadım",
            "fiyat_araligi": fiyat,
            "ilgi": web.get("ilgi") or "bulamadım",
            "ornekler": [
                f"{o.get('site','bulamadım')} – {o.get('baslik','')} – "
                + (_tl(o['fiyat']) if o.get('fiyat') is not None else "fiyat bulamadım")
                for o in web.get("ornekler", [])
            ],
        },
        "kar": {
            "satis": _tl(kar["satis"]) + (" (program önerdi)" if kar["onerildi"] else ""),
            "alis_hariç": _tl(kar["alis_hariç"]),
            "odenecek_kdv": _tl(kar["odenecek_kdv"]),
            "adet_kar": _tl(kar["adet_kar"]),
            "toplam_kar": _tl(kar["toplam_kar"]),
            "kar_orani": f"%{kar['kar_orani']:.0f}" if kar["kar_orani"] is not None else "bulamadım",
            "toplam_yatirim": _tl(kar["toplam_yatirim"]),
            "not": "Gerçek hesap. Alış KDV'si indirilebilir sayıldı; komisyon, kargo ve kira dahil değil.",
        },
        "beden_renk": {
            "bedenler": "Örnek: 2-3-4-5 yaş dağılımı eşit",
            "renkler": "Örnek: " + ", ".join(analiz.get("renkler", [])) if analiz.get("renkler") else "bulamadım",
            "kumas": kumas,
        },
        "zamanlama": "Örnek: Sezon başına 3-4 hafta kala satışa çıkarın.",
    }
