import os
import uuid

from dotenv import load_dotenv
from flask import Flask, Response, abort, jsonify, render_template, request

load_dotenv()
import rapor  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

# Fotoğraf, arama servisinin erişebilmesi için yalnızca rapor sürerken bellekte tutulur.
GECICI = {}


@app.get("/")
def anasayfa():
    return render_template("index.html")


def _sayi(deger):
    try:
        return float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        return None


@app.get("/gecici/<kimlik>")
def gecici(kimlik):
    foto = GECICI.get(kimlik)
    if not foto:
        abort(404)
    return Response(foto[0], mimetype=foto[1])


@app.post("/rapor")
def rapor_hazirla():
    foto = request.files.get("foto")
    alis = _sayi(request.form.get("alis"))
    adet = _sayi(request.form.get("adet"))
    satis = _sayi(request.form.get("satis"))
    if not foto or not foto.filename:
        return jsonify(hata="Lütfen takımın fotoğrafını seçin."), 400
    if alis is None or alis <= 0:
        return jsonify(hata="Alış fiyatını yazın."), 400
    if adet is None or adet < 1:
        return jsonify(hata="Planlanan adedi yazın."), 400
    veri = foto.read()
    kimlik = uuid.uuid4().hex
    GECICI[kimlik] = (veri, foto.mimetype or "image/jpeg")
    taban = (os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PUBLIC_URL") or request.url_root).rstrip("/")
    try:
        sonuc = rapor.hazirla(
            veri, alis, request.form.get("kdv") == "dahil",
            int(adet), request.form.get("kumas", "diğer"), satis if satis and satis > 0 else None,
            foto_url=f"{taban}/gecici/{kimlik}",
            firma=(request.form.get("firma") or "").strip()[:60],
        )
    finally:
        GECICI.pop(kimlik, None)
    return jsonify(sonuc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
