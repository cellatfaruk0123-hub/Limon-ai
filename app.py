from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
import rapor  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024


@app.get("/")
def anasayfa():
    return render_template("index.html")


def _sayi(deger):
    try:
        return float(str(deger).replace(",", "."))
    except (TypeError, ValueError):
        return None


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
    sonuc = rapor.hazirla(
        foto.read(), alis, request.form.get("kdv") == "dahil",
        int(adet), request.form.get("kumas", "diğer"), satis if satis and satis > 0 else None,
    )
    return jsonify(sonuc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
