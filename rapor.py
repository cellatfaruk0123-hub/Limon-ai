"""Raporu birleştirir. Kâr hesabı her zaman gerçek; arama ve yorum anahtarlar varsa gerçek, yoksa sahte."""
import datetime
import urllib.parse

import foto_analiz
import resimle_ara

KDV = 0.10
TY_KOMISYON = 0.20  # Trendyol varsayımı: satış fiyatının %20'si
TY_KARGO = 100.0   # Trendyol varsayımı: adet başı kargo (TL)


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
    satis_kdv = satis - satis_hariç
    alis_kdv = alis_hariç * KDV
    ty_kar = satis_hariç - satis * TY_KOMISYON - TY_KARGO - alis_hariç
    return {
        "satis": satis,
        "onerildi": onerildi,
        "alis_hariç": alis_hariç,
        "odenecek_kdv": satis_kdv,
        "net_kdv": satis_kdv - alis_kdv,
        "toptanci_nakit": alis_hariç * (1 + KDV) * adet,
        "ty_adet_kar": ty_kar,
        "adet_kar": adet_kar,
        "toplam_kar": adet_kar * adet,
        "kar_orani": (adet_kar / alis_hariç * 100) if alis_hariç else None,
        "toplam_yatirim": alis_hariç * adet,
    }


def _urun(o):
    return {
        "site": o.get("site") or "bulamadım",
        "baslik": o.get("baslik") or "bulamadım",
        "fiyat": _tl(o["fiyat"]) if o.get("fiyat") is not None else "fiyat bulamadım",
        "yorum": o.get("yorum"),
        "puan": o.get("puan"),
        "link": o.get("link") if str(o.get("link", "")).startswith("http") else None,
        "resim": o.get("resim") if str(o.get("resim", "")).startswith("http") else None,
    }


def _web_ozet(web):
    if web.get("sahte") or not web.get("benzer_sayisi"):
        return "Arama sonucu yok: bulamadım."
    parca = [f"{web['benzer_sayisi']} benzer ürün bulundu"]
    if web.get("fiyat_min") is not None:
        parca.append(f"fiyatlar {web['fiyat_min']:.0f}-{web['fiyat_max']:.0f} TL, ortanca {web['fiyat_medyan']:.0f} TL")
    ylar = [x["yorum"] for x in web.get("en_yorumlu", []) if x.get("yorum")]
    parca.append(f"en çok yorum alan ürünün yorumu: {max(ylar)}" if ylar else "yorum sayısı: bulamadım")
    return "; ".join(parca) + ". Satış sayısı: bulamadım."


def hazirla(foto_bytes, alis, kdv_dahil, adet, kumas, satis, foto_url=None, firma="", kategori="", model_kodu="", seri=""):
    kar = kar_hesapla(alis, kdv_dahil, adet, satis)
    okunan = {}
    if not (firma and model_kodu):  # eksik olanı etiketten oku
        okunan = foto_analiz.etiket_oku(foto_bytes)
    firma_son = firma or okunan.get("marka", "")
    model_son = model_kodu or okunan.get("model_kodu", "")
    web = resimle_ara.ara(foto_bytes, None, foto_url, firma_son, kategori, model_son)
    analiz = foto_analiz.analiz_et(foto_bytes, {
        "alis_haric": kar["alis_hariç"], "adet": adet, "kumas": kumas, "satis": kar["satis"],
        "kar_orani": kar["kar_orani"] or 0, "ay": datetime.date.today().month,
        "web_ozet": _web_ozet(web), "firma": firma_son, "kategori": kategori, "seri": seri,
    })

    uyarilar = []
    if not web.get("benzer_sayisi"):
        uyarilar.append("İnternette bu ürüne benzeyen ürün bulamadım.")
    for h in (web.get("hata"), analiz.get("hata")):
        if h:
            uyarilar.append(h)

    if web.get("fiyat_min") is not None:
        fiyat = f"{_tl(web['fiyat_min'])} – {_tl(web['fiyat_max'])} (ortanca {_tl(web['fiyat_medyan'])})"
    else:
        fiyat = "bulamadım"

    web_yok = bool(web.get("hata") or not web.get("benzer_sayisi"))
    a_sahte, w_sahte = bool(analiz.get("sahte")), bool(web.get("sahte"))
    if a_sahte and w_sahte:
        ust = "Bu örnek sonuçtur, gerçek analiz değildir."
    elif a_sahte and web_yok:
        ust = ("Dikkat: karar, satma ihtimali, beden-renk ve zamanlama ÖRNEKTİR. "
               "İnternet araması sonuç vermedi, kâr hesabı gerçektir.")
    elif a_sahte:
        ust = ("Dikkat: karar, satma ihtimali, beden-renk ve zamanlama ÖRNEKTİR. "
               "İnternetteki benzerler ve kâr hesabı gerçektir.")
    elif w_sahte or web_yok:
        ust = "Dikkat: internet araması sonuç vermedi. Karar yalnızca fotoğraf ve kâra dayanıyor."
    else:
        ust = None

    # Trendyol / Google Alışveriş arama düğmeleri (ücretsiz, yeni sekmede açılır).
    # Önce Gemini'nin baskı/yazı/figürden ürettiği trendyol_sorgu; yoksa marka/model; o da yoksa kategori.
    ty = "" if analiz.get("sahte") else str(analiz.get("trendyol_sorgu") or "").strip()[:100]
    kelimeler = [] if analiz.get("sahte") else (analiz.get("arama_kelimeleri") or [])
    if ty:
        sorgu = ty
    elif firma_son or model_son:
        sorgu = " ".join(x for x in (firma_son, model_son, kategori if kategori != "diğer" else "") if x)
    elif kelimeler:
        sorgu = str(kelimeler[0])
    else:
        sorgu = kategori if kategori and kategori != "diğer" else "çocuk takımı"
    q = urllib.parse.quote_plus(sorgu)
    dugmeler = {
        "sorgu": sorgu,
        "trendyol": f"https://www.trendyol.com/sr?q={q}",
        "google": f"https://www.google.com/search?tbm=shop&hl=tr&gl=tr&q={q}",
    }

    medyan = web.get("fiyat_medyan")
    if medyan:
        fark = (kar["satis"] - medyan) / medyan * 100
        if abs(fark) < 0.5:
            piyasa = "Satış fiyatın piyasa ortancasıyla aynı."
        else:
            piyasa = f"Satış fiyatın piyasa ortancasından %{abs(fark):.0f} {'pahalı' if fark > 0 else 'ucuz'} ({_tl(medyan)})."
    else:
        piyasa = "Piyasa ortancası: bulamadım."

    etiket = analiz.get("karar", "bulamadım")
    renk = {"Al": "yesil", "Az al": "sari", "Alma": "kirmizi"}.get(etiket, "sari")
    return {
        "sahte": a_sahte or w_sahte,
        "ust_uyari": ust,
        "uyarilar": uyarilar,
        "karar": {"etiket": etiket, "renk": renk, "gerekce": analiz.get("karar_gerekce") or "bulamadım"},
        "ihtimal": {"yuzde": analiz.get("ihtimal") or "bulamadım", "gerekce": analiz.get("ihtimal_gerekce") or "bulamadım"},
        "benzerler": {
            "adet": web.get("benzer_sayisi") if web.get("benzer_sayisi") is not None else "bulamadım",
            "fiyat_araligi": fiyat,
            "ilgi": web.get("ilgi") or "bulamadım",
            "durum": web.get("durum", ""),
            "urun": analiz.get("urun") or "bulamadım",
            "arama_kelimeleri": analiz.get("arama_kelimeleri") or [],
            "okunan": {"marka": firma_son, "model_kodu": model_son, "yazidan": bool(okunan.get("marka") or okunan.get("model_kodu"))},
            "dugmeler": dugmeler,
            "en_ucuz": [_urun(o) for o in web.get("en_ucuz", [])],
            "en_yorumlu": [_urun(o) for o in web.get("en_yorumlu", [])],
        },
        "kar": {
            "satis": _tl(kar["satis"]) + (" (program önerdi)" if kar["onerildi"] else ""),
            "alis_hariç": _tl(kar["alis_hariç"]),
            "odenecek_kdv": _tl(kar["odenecek_kdv"]),
            "net_kdv": _tl(kar["net_kdv"]),
            "toptanci_nakit": _tl(kar["toptanci_nakit"]),
            "piyasa": piyasa,
            "trendyol": (f"Trendyol'da satarsak (%{TY_KOMISYON * 100:.0f} komisyon + {TY_KARGO:.0f} TL kargo varsayımıyla) "
                         f"adet başı tahmini net kâr: {_tl(kar['ty_adet_kar'])}"),
            "adet_kar": _tl(kar["adet_kar"]),
            "toplam_kar": _tl(kar["toplam_kar"]),
            "kar_orani": f"%{kar['kar_orani']:.0f}" if kar["kar_orani"] is not None else "bulamadım",
            "toplam_yatirim": _tl(kar["toplam_yatirim"]),
            "not": "Gerçek hesap. Alış KDV'si indirilebilir sayıldı; komisyon, kargo ve kira dahil değil.",
        },
        "beden_renk": {
            "bedenler": analiz.get("beden_oneri") or "bulamadım",
            "renkler": analiz.get("renk_oneri") or "bulamadım",
            "kumas": kumas,
        },
        "zamanlama": analiz.get("zamanlama") or "bulamadım",
    }
