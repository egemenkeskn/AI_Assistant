from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import openai
from datetime import datetime
import requests

app = Flask(__name__)

# OpenAI API Anahtarını Ayarlayın
openai.api_key = "OPENAI-API-KEY-HERE"

# SQLite veritabanını ayarlayın
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Veritabanında kullanılacak model
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_input = db.Column(db.String(200), nullable=False)
    model_output = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# Konuşma geçmişini saklamak için liste
conversation_history = []

def get_weather(city_name):
    api_key = "OPENWEATHER-API-KEY-HERE"  # OpenWeatherMap API anahtarınızı buraya girin
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    complete_url = f"{base_url}?q={city_name}&appid={api_key}&units=metric"
    response = requests.get(complete_url)
    return response.json()

# Ana sayfa için route
@app.route("/")
def index():
    return render_template("index.html")

# Cevap alma için route
@app.route("/get_response", methods=["POST"])
def get_response():
    global conversation_history
    user_input = request.form["user_input"]
    user_input = request.form["user_input"].lower()

    # Hava durumu ile ilgili bir soru mu?
    if "hava durumu" in user_input:
        city_name = user_input.split()[0]  # Basit bir yöntem, daha gelişmiş metotlar kullanılabilir
        weather_info = get_weather(city_name)
        
        # API'den başarılı bir yanıt geldi mi?
        if 'main' in weather_info and 'wind' in weather_info:
            temperature = weather_info['main']['temp']
            weather_description = weather_info['weather'][0]['description']
            wind_speed = weather_info['wind']['speed']
            humidity = weather_info['main']['humidity']
            weather_descriptions = {
            "broken clouds": "Bulutlu",
            "clear sky": "Açık Hava",
            "light snow": "Hafif Karlı",
            "overcast clouds": "Yoğun Bulutlu",
            "mist": "Sisli",
            "scattered clouds": "Parçalı Bulutlu",
            "light rain": "Hafif Yağmurlu",
            "few clouds": "Az Bulutlu"
        }
            weather_description = weather_descriptions.get(weather_description, "Tanımlanamayan Hava Durumu")
            model_output = f"{city_name.title()} için sıcaklık: {temperature}°C\nDurum: {weather_description}\nRüzgar Hızı:{wind_speed}m/s\nNem Oranı: %{humidity}"
        else:
            model_output ="Hava durumu bilgisi alınamadı. Lütfen şehir adını kontrol edin veya daha sonra tekrar deneyin."
    else: 
        # Geçmiş konuşmaları güncelle
        conversation_history.append({"role": "user", "content": user_input})

        # OpenAI'ye sorguyu gönderin
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history,
            max_tokens=1500,
            temperature=0.5,
            stop=None
        )

        # OpenAI'den gelen yanıtı alın
        model_output = response['choices'][0]['message']['content'].strip()

        # Geçmiş konuşmaları güncelle
        conversation_history.append({"role": "assistant", "content": model_output})

    # Veritabanına kaydet
    with app.app_context():
        chat_entry = Chat(user_input=user_input, model_output=model_output)
        db.session.add(chat_entry)
        db.session.commit()

    return render_template("index.html", user_input=user_input, model_output=model_output)

# Tüm kayıtları görüntülemek için route
@app.route("/view_records")
def view_records():
    with app.app_context():
        all_records = Chat.query.all()
    return render_template("view_records.html", all_records=all_records)

@app.route("/clear_records")
def clear_records():
    with app.app_context():
        # Tüm kayıtları veritabanından sil
        Chat.query.delete()
        db.session.commit()
    return "Sorgu kayıtları temizlendi."

# Uygulamayı çalıştırın
if __name__ == "__main__":
    app.run(debug=True)
