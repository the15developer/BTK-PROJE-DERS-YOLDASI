from flask import Flask, render_template
import markdown

from flask import request, jsonify
import json
import google.generativeai as genai

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("models/gemini-2.5-flash")  # Güncel ve desteklenen model

app = Flask(__name__)



@app.route('/')
def Login():
    return render_template('login.html')  # templates/index.html dosyasını gösterir

@app.route('/home')
def home():
    return render_template('index.html')  # diğer sayfalar da aynı şekilde

@app.route('/courses')
def courses():
    return render_template('courses.html')  # diğer sayfalar da aynı şekilde

@app.route('/goals')
def goals():
    return render_template('goals.html')  # diğer sayfalar da aynı şekilde

@app.route('/progress')
def progress():
    return render_template('progress.html')  # diğer sayfalar da aynı şekilde

@app.route('/bookmarks')
def bookmarks():
    return render_template('bookmarks.html')  # diğer sayfalar da aynı şekilde

@app.route('/profile')
def profile():
    return render_template('profile.html')  # diğer sayfalar da aynı şekilde



# JSON dosyasını oku
def load_users():
    with open("data/veriler.json", "r", encoding="utf-8") as f:
        return json.load(f)
    

#LOGIN KODU

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    users = load_users()

    for user in users:
        if user["email"] == email and user["sifre"] == password:
            return jsonify({"success": True, "ad": user["ad"], "email": user["email"]})

    return jsonify({"success": False, "message": "Geçersiz e-posta veya şifre."}), 401


#DERSLERI GOSTERME KODU 

@app.route('/get_courses', methods=['POST'])
def get_courses():
    data = request.get_json()
    email = data.get("email")
    users = load_users()
    
    for user in users:
        if user["email"] == email:
            return jsonify({"success": True, "kurslar": user.get("kurslar", [])})
    
    return jsonify({"success": False, "message": "Kullanıcı bulunamadı."}), 404


#MOTIVASYON SOZU


@app.route('/motivasyon-sozu')
def motivasyon_sozu():
    try:
        response = model.generate_content("orta uzunlukta ve motive edici TEK bir Türkçe başarı sözü üret ve cevabin sadece sozu icersin. Kalin fontla yazma. ")
        #print("Response objesi:", response)
        #print("Response text:", getattr(response, 'text', 'text attribute yok'))
        result_text = response.text.strip() if hasattr(response, 'text') else "Metin bulunamadı."
        print("Sonuç metni:", result_text)
       

        return jsonify({"sozu": result_text})
    except Exception as e:
        print("Hata oluştu:", e)
        return jsonify({"sozu": "Başarı, çabanın meyvesidir."})
    

@app.route('/chat', methods=['POST'])
def gemini_chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        response = model.generate_content(user_message)

        raw_text = response.text.strip() if hasattr(response, 'text') else "Yanıt alınamadı."
        html_text = markdown.markdown(raw_text, extensions=["fenced_code"])

        return jsonify({"response": html_text})
    except Exception as e:
        print("Chatbot hatası:", e)
        return jsonify({"response": "<p>❌ Bir hata oluştu.</p>"}), 500

#gunluk hedef kodu

def gemini_daily_goal_recommendation(unfinished_courses):
    prompt = "Kullanıcının tamamlamadığı kurslar ve modüller:\n"
    for kurs in unfinished_courses:
        prompt += f"- {kurs['ad']}:\n"
        for mod in kurs['moduller']:
            prompt += f"  * {mod['baslik']} (%{mod['tamamlanma']})\n"
    prompt += "\nLütfen kullanıcı için bugün tamamlaması gereken en uygun modülü öner,sadece kurs ismi - modul basligi seklinde yaz\n"

    # Gemini model generate_content kullanımı
    response = model.generate_content(prompt)
    result_text = response.text.strip() if hasattr(response, 'text') else "Öneri alınamadı."
    return result_text




@app.route("/get-daily-goal", methods=["POST"])
def get_daily_goal():
    data = request.get_json()
    email = data.get("email")
    if not email:
        return jsonify({"error": "Email bilgisi gerekli"}), 400

    users = load_users()
    user = next((u for u in users if u.get("email") == email), None)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı"}), 404

    unfinished_courses = []
    for kurs in user.get("kurslar", []):
        if kurs.get("durum") != "Devam Ediyor":
            continue

        unfinished_moduller = [
            mod for mod in kurs.get("moduller", [])
            if int(mod.get("tamamlanma", "0%").replace("%", "")) < 100
        ]

        if unfinished_moduller:
            unfinished_courses.append({
                "ad": kurs["ad"],
                "moduller": unfinished_moduller
            })

    if not unfinished_courses:
        return jsonify({"recommendation": "Tüm modüller tamamlandı! 🎉"})

    try:
        recommendation = gemini_daily_goal_recommendation(unfinished_courses)
        print(recommendation)
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        print("Gemini öneri hatası:", e)
        return jsonify({"error": "Öneri alınırken hata oluştu."}), 500
    


if __name__ == "__main__":
    app.run(debug=True)