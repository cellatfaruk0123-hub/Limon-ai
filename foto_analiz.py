"""Fotoğrafı yorumlar ve karar önerir (Gemini, ücretsiz anahtar: GEMINI_API_KEY).

Anahtar yoksa ya da servis hata verirse SAHTE örnek döner ("hata" alanında nedeni yazar).
Model adı değişebildiği için sırayla birkaç model denenir; GEMINI_MODEL ile ilki seçilebilir.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request

MODELLER = ["gemini-flash-latest", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash"]
ZAMAN_ASIMI = 20  # saniye, tek istek
GECICI_HATA = (429, 503)  # yoğunluk: 2 sn bekle, aynı modeli 1 kez daha dene
ANAHTAR_HATA = (401, 403)  # geçersiz anahtar: diğer modeller de aynısını verir, dur
# Render isteği 120 sn'de keser; Gemini denemeleri toplamda bu süreyi geçmesin.
SURE_ANALIZ = 55
SURE_ETIKET = 25
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _yanit_oku(veri):
    """Gemini cevabından JSON'u güvenle çıkarır. Okuyamazsa ValueError (anlamlı mesajla) atar."""
    engel = (veri.get("promptFeedback") or {}).get("blockReason")
    if engel:
        raise ValueError(f"Gemini fotoğrafı güvenlik filtresine takıldı ({engel})")
    adaylar = veri.get("candidates") or []
    if not adaylar:
        raise ValueError("Gemini boş cevap verdi")
    aday = adaylar[0]
    parcalar = (aday.get("content") or {}).get("parts") or []
    metin = "".join(p.get("text", "") for p in parcalar if isinstance(p, dict)).strip()
    if not metin:
        neden = aday.get("finishReason") or "bilinmiyor"
        if neden in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"):
            raise ValueError(f"Gemini cevabı güvenlik filtresine takıldı ({neden})")
        raise ValueError(f"Gemini yazı döndürmedi ({neden})")
    if metin.startswith("```"):  # ```json ... ``` bloğunu temizle
        metin = metin.split("\n", 1)[1] if "\n" in metin else metin[3:]
        if metin.rstrip().endswith("```"):
            metin = metin.rstrip()[:-3]
        metin = metin.strip()
    try:
        sonuc = json.loads(metin)
    except json.JSONDecodeError:
        raise ValueError("Gemini cevabı okunamadı (JSON bozuk)")
    if not isinstance(sonuc, dict):
        raise ValueError("Gemini cevabı beklenen biçimde değil")
    return sonuc


def _sahte(hata=None):
    s = {
        "sahte": True,
        "urun": "Çocuk takımı (örnek)",
        "renkler": ["pembe", "krem"],
        "trendyol_sorgu": "Trendyol'da birebir bu ürünü bulacak 1 kısa arama cümlesi",
 "arama_kelimeleri": ["çocuk takım"],
        "karar": "Az al",
        "karar_gerekce": "Örnek karar: benzer ürünler var, ilgi orta.",
        "ihtimal": "orta (örnek)",
        "ihtimal_gerekce": "Örnek gerekçe: fiyat piyasa aralığında, ama birebir model bulunamadı.",
        "beden_oneri": "Örnek: 2-3-4-5 yaş dağılımı eşit",
        "renk_oneri": "Örnek: pembe, krem, gri melanj",
        "zamanlama": "Örnek: Sezon başına 3-4 hafta kala satışa çıkarın.",
    }
    if hata:
        s["hata"] = hata
    return s


def _istem(b):
    return f"""Sen Gaziantep çarşıda çocuk takımı satan Limon Çocuk mağazası için çalışan bir ürün danışmanısın.
Ekteki fotoğraf toptancıda görülen bir çocuk takımı. Bilgiler:
- Alış (KDV hariç): {b['alis_haric']:.2f} TL, planlanan adet: {b['adet']}
- Kumaş (mağaza sahibi söyledi): {b['kumas']}
- Ürün kategorisi (mağaza sahibi seçti, bunu esas al): {b.get('kategori') or 'seçilmedi'}
- Üretici firma (etiketten, mağaza sahibi yazdı): {b.get('firma') or 'yazılmadı'}
- Satış fiyatı (KDV dahil): {b['satis']:.2f} TL, adet başı kâr oranı: %{b['kar_orani']:.0f}
- Seri / yaş aralığı: {b.get('seri') or 'seçilmedi'}
- Şu an ay numarası: {b['ay']}
- Gaziantep bilgisi: havalar geç soğur, kış kısa sürer; ağır kışlık ürünün satış penceresi dardır. Bayram öncesi ve okul açılış dönemleri en yoğun satış zamanlarıdır.
- İnternet (Google Lens) özeti: {b['web_ozet']}

KESİN KURALLAR: Verilmeyen hiçbir rakamı uydurma. İnternet özetinde olmayan satış sayısı, ilgi ya da fiyat için "bulamadım" yaz.
Karar; fotoğraf, kumaş, mevsim, kâr oranı ve internet özetine dayansın, gerekçede hangisine dayandığını söyle.
Takımın üzerindeki baskıyı, figürü ve İngilizce/Türkçe yazıyı (örn. "New York", ayıcık, fiyonk) dikkatle oku.
Bunlarla Trendyol'da birebir bu ürünü bulacak en net 1 kısa arama cümlesi üret (trendyol_sorgu): cinsiyet + ürün tipi + baskı/yazı/figür + belirgin renk, en fazla 6-7 kelime. Görmediğin yazıyı uydurma.
Beden ve renk önerisini seçilen yaş serisine ve genel çocuk giyim bilgisine dayalı öneri olarak belirt. Zamanlamada Gaziantep iklimini ve bayram/okul dönemlerini hesaba kat.

Yalnızca şu JSON'u döndür:
{{"urun": "takımın kısa tanımı", "renkler": ["görünen renkler"],
 "arama_kelimeleri": ["3 kısa Türkçe arama cümlesi; kategori ve üretici firma yazıldıysa her cümlede ikisi de geçsin"],
 "karar": "Al" | "Az al" | "Alma", "karar_gerekce": "1-2 cümle",
 "ihtimal": "düşük" | "orta" | "yüksek", "ihtimal_gerekce": "1-2 cümle",
 "beden_oneri": "yaş/beden dağılımı", "renk_oneri": "renk dağılımı",
 "zamanlama": "ne zaman satışa çıkmalı"}}"""


def _gemini(govde, anahtar, sure):
    """Modelleri sırayla dener; başarılı cevabın JSON'unu döndürür. Hepsi olmazsa (None, hatalar)."""
    modeller = ([os.getenv("GEMINI_MODEL")] if os.getenv("GEMINI_MODEL") else []) + MODELLER
    son = time.monotonic() + sure
    hatalar = []
    for model in modeller:
        for deneme in (1, 2):
            if time.monotonic() > son:
                hatalar.append("süre doldu")
                return None, hatalar
            istek = urllib.request.Request(
                ADRES.format(model=model), data=govde, method="POST",
                headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
            try:
                with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as r:
                    return _yanit_oku(json.load(r)), hatalar
            except urllib.error.HTTPError as e:
                hatalar.append(f"{model}: HTTP {e.code}")
                if e.code in ANAHTAR_HATA:
                    return None, hatalar  # anahtar geçersiz/yetkisiz
                if e.code in GECICI_HATA and deneme == 1:
                    time.sleep(2)
                    continue  # aynı modeli 1 kez daha dene
                break  # sıradaki modele geç
            except ValueError as e:  # güvenlik filtresi / boş / bozuk cevap
                hatalar.append(f"{model}: {e}")
                if "güvenlik" in str(e):
                    return None, hatalar  # başka model de aynı fotoğrafı engeller
                break
            except Exception as e:  # ağ hatası / zaman aşımı
                hatalar.append(f"{model}: {type(e).__name__}")
                break
    return None, hatalar


def analiz_et(foto_bytes, baglam=None):
    anahtar = os.getenv("GEMINI_API_KEY")
    if not anahtar or not baglam:
        return _sahte()
    govde = json.dumps({
        "contents": [{"parts": [
            {"text": _istem(baglam)},
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(foto_bytes).decode()}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }).encode()
    s, hatalar = _gemini(govde, anahtar, SURE_ANALIZ)
    if s is not None:
        s["sahte"] = False
        if s.get("karar") not in ("Al", "Az al", "Alma"):
            s["karar"] = "bulamadım"
        return s
    return _sahte("Fotoğraf yorumu alınamadı (" + " | ".join(hatalar) + ").")


def etiket_oku(foto_bytes):
    """Fotoğraftaki etiket/yazıdan marka ve model kodunu okur. Okuyamazsa boş döner; uydurmaz."""
    anahtar = os.getenv("GEMINI_API_KEY")
    if not anahtar:
        return {}
    istem = ("Fotoğraftaki etiket, askı, katalog yazısı veya logoda GÖRÜNEN marka adını ve model/ürün kodunu oku. "
             "Görmediğini yazma, tahmin etme, boş bırak. Yalnızca şu JSON'u döndür: "
             '{"marka": "", "model_kodu": ""}')
    govde = json.dumps({
        "contents": [{"parts": [
            {"text": istem},
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(foto_bytes).decode()}},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }).encode()
    o, _ = _gemini(govde, anahtar, SURE_ETIKET)
    if o:
        return {"marka": str(o.get("marka") or "").strip()[:40], "model_kodu": str(o.get("model_kodu") or "").strip()[:30]}
    return {}
