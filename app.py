from flask import Flask, render_template, request
import requests

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def anasayfa():
    hava_bilgisi = None
    hata_mesajı = None

    if request.method == "POST":
        girilen_sehir = request.form.get("sehir").strip()

        if girilen_sehir:
            # 1. ADIM: İsimden Koordinat Bulma (Geocoding API)
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={girilen_sehir}&count=1&language=tr&format=json"
            geo_cevap = requests.get(geo_url)
            
            if geo_cevap.status_code == 200 and "results" in geo_cevap.json():
                konum = geo_cevap.json()["results"][0]
                lat = konum["latitude"]
                lon = konum["longitude"]
                sehir_adi = konum["name"]
                ulke = konum.get("country", "")

                # 2. ADIM: Bulunan Koordinatlarla Hava Durumunu Çekme
                hava_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                hava_cevap = requests.get(hava_url)

                if hava_cevap.status_code == 200:
                    veri = hava_cevap.json()["current_weather"]
                    hava_bilgisi = {
                        "sehir": f"{sehir_adi}, {ulke}",
                        "sicaklik": veri["temperature"],
                        "ruzgar": veri["windspeed"]
                    }
                else:
                    hata_mesajı = "Hava durumu verisi alınamadı."
            else:
                hata_mesajı = f"'{girilen_sehir}' adında bir yer bulunamadı. Lütfen kontrol edip tekrar deneyin."

    return render_template("index.html", hava=hava_bilgisi, hata=hata_mesajı)

if __name__ == "__main__":
    app.run(debug=True)