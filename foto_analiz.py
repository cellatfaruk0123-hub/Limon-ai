"""Fotoğrafı yorumlar ve karar önerir (Gemini, ücretsiz anahtar: GEMINI_API_KEY).

Anahtar yoksa ya da servis hata verirse SAHTE örnek döner ("hata" alanında nedeni yazar).
Model adı değişebildiği için sırayla birkaç model denenir; GEMINI_MODEL ile ilki seçilebilir.
"""
import base64
import json
import os
import urllib.error
import urllib.request

MODELLER = ["gemini-2.5-flash", "gemini-flash-latest"]
ZAMAN_ASIMI = 20  # saniye
ADRES = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _sahte(hata=None):
    s = {
        "sahte": True,
        "urun": "Çocuk takımı (örnek)",
        "renkler": ["pembe", "krem"],
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
Beden ve renk önerisini seçilen yaş serisine ve genel çocuk giyim bilgisine dayalı öneri olarak belirt. Zamanlamada Gaziantep iklimini ve bayram/okul dönemlerini hesaba kat.

Yalnızca şu JSON'u döndür:
{{"urun": "takımın kısa tanımı", "renkler": ["görünen renkler"],
 "arama_kelimeleri": ["3 kısa Türkçe arama cümlesi; kategori ve üretici firma yazıldıysa her cümlede ikisi de geçsin"],
 "karar": "Al" | "Az al" | "Alma", "karar_gerekce": "1-2 cümle",
 "ihtimal": "düşük" | "orta" | "yüksek", "ihtimal_gerekce": "1-2 cümle",
 "beden_oneri": "yaş/beden dağılımı", "renk_oneri": "renk dağılımı",
 "zamanlama": "ne zaman satışa çıkmalı"}}"""


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
    modeller = ([os.getenv("GEMINI_MODEL")] if os.getenv("GEMINI_MODEL") else []) + MODELLER
    hatalar = []
    for model in modeller:
        istek = urllib.request.Request(
            ADRES.format(model=model), data=govde, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
        try:
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as r:
                veri = json.load(r)
            metin = veri["candidates"][0]["content"]["parts"][0]["text"]
            s = json.loads(metin)
            s["sahte"] = False
            if s.get("karar") not in ("Al", "Az al", "Alma"):
                s["karar"] = "bulamadım"
            return s
        except urllib.error.HTTPError as e:
            hatalar.append(f"{model}: HTTP {e.code}")
            if e.code not in (400, 404):  # anahtar/kota sorunu: diğer modeller de aynısını verir
                break
        except Exception as e:
            hatalar.append(f"{model}: {type(e).__name__}")
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
    modeller = ([os.getenv("GEMINI_MODEL")] if os.getenv("GEMINI_MODEL") else []) + MODELLER
    for model in modeller:
        istek = urllib.request.Request(
            ADRES.format(model=model), data=govde, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
        try:
            with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI) as r:
                veri = json.load(r)
            o = json.loads(veri["candidates"][0]["content"]["parts"][0]["text"])
            return {"marka": str(o.get("marka") or "").strip()[:40], "model_kodu": str(o.get("model_kodu") or "").strip()[:30]}
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404):
                break
        except Exception:
            continue
    return {}
