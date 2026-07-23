from flask import Flask, render_template, request, redirect, url_for, make_response
import requests
import jwt
import datetime

app = Flask(__name__)

# JWT İmzalamak için gizli anahtarımız
SECRET_KEY = "super_gizli_jwt_anahtari"

# Kullanıcıları geçici olarak hafızada tutacağımız veritabanı (Sözlük)
# Gerçek projelerde burası PostgreSQL veya MongoDB gibi bir veritabanı olur.
kullanicilar_db = {}

# --- YARDIMCI FONKSİYONLAR (JWT BİLETLERİ İÇİN) ---
def token_olustur(kullanici_adi):
    """Kullanıcıya 30 dakika geçerli şifreli bir JWT üretir."""
    payload = {
        "user": kullanici_adi,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30) # 30 dk geçerli
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def token_dogrula(token):
    """Gelen JWT'yi çözer, süresi geçmiş mi veya sahte mi kontrol eder."""
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data["user"]
    except jwt.ExpiredSignatureError:
        return None # Süresi dolmuş
    except jwt.InvalidTokenError:
        return None # Sahte/Geçersiz token


# --- ROUTE'LAR (SAYFALAR) ---

# 1. KAYIT OL (REGISTER)
@app.route("/register", methods=["GET", "POST"])
def register():
    hata = None
    if request.method == "POST":
        kullanici = request.form.get("kullanici_adi").strip()
        sifre = request.form.get("sifre").strip()

        if kullanici in kullanicilar_db:
            hata = "Bu kullanıcı adı zaten alınmış!"
        elif kullanici and sifre:
            # Kullanıcıyı hafızadaki veritabanımıza ekliyoruz
            kullanicilar_db[kullanici] = sifre
            return redirect(url_for("login"))
        else:
            hata = "Lütfen tüm alanları doldurun."

    return render_template("register.html", hata=hata)


# 2. GİRİŞ YAP (LOGIN & JWT ÜRETİMİ)
@app.route("/login", methods=["GET", "POST"])
def login():
    hata = None
    if request.method == "POST":
        kullanici = request.form.get("kullanici_adi").strip()
        sifre = request.form.get("sifre").strip()

        # Doğrulama: Kullanıcı var mı ve şifresi doğru mu?
        if kullanici in kullanicilar_db and kullanicilar_db[kullanici] == sifre:
            # 🎟️ JWT TOKEN ÜRETİLİYOR!
            token = token_olustur(kullanici)
            
            # Token'ı tarayıcının Cookie (Çerez) alanına güvenli bir şekilde yüklüyoruz
            cevap = make_response(redirect(url_for("anasayfa")))
            cevap.set_cookie("jwt_token", token)
            return cevap
        else:
            hata = "Hatalı kullanıcı adı veya şifre!"

    return render_template("login.html", hata=hata)


# 3. ÇIKIŞ YAP (LOGOUT)
@app.route("/logout")
def logout():
    cevap = make_response(redirect(url_for("login")))
    cevap.delete_cookie("jwt_token") # Çerezi/Token'ı siler
    return cevap


# 4. ANA SAYFA (JWT KORUMALI HAVA DURUMU SAYFASI)
@app.route("/", methods=["GET", "POST"])
def anasayfa():
    # Tarayıcıdan JWT Token'ı çekiyoruz
    token = request.cookies.get("jwt_token")
    
    # TOKEN DOĞRULAMA (Authorization)
    aktif_kullanici = token_dogrula(token) if token else None

    # Eğer geçerli bir token yoksa kullanıcıyı Giriş Sayfasına fırlat!
    if not aktif_kullanici:
        return redirect(url_for("login"))

    hava_bilgisi = None
    hata_mesajı = None

    if request.method == "POST":
        girilen_sehir = request.form.get("sehir").strip()

        if girilen_sehir:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={girilen_sehir}&count=1&language=tr&format=json"
            geo_cevap = requests.get(geo_url)
            
            if geo_cevap.status_code == 200 and "results" in geo_cevap.json():
                konum = geo_cevap.json()["results"][0]
                lat = konum["latitude"]
                lon = konum["longitude"]
                sehir_adi = konum["name"]
                ulke = konum.get("country", "")

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
                hata_mesajı = f"'{girilen_sehir}' bulunamadı."

    return render_template("index.html", hava=hava_bilgisi, hata=hata_mesajı, kullanici=aktif_kullanici)

if __name__ == "__main__":
    app.run(debug=True)  