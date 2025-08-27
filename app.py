import os
import random
import pickle
import json
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_cors import CORS     # ✅ Added CORS
from twilio.rest import Client   # for SMS OTP
import pyttsx3
import speech_recognition as sr
from red_zone_processor import RedZoneDetector# ✅ integrate your Red Zone processor
   
# ================================
# Flask & DB Setup
# ================================
app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all domains

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'hackathon.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER_PHOTOS = os.path.join(BASE_DIR, 'uploads', 'photos')
UPLOAD_FOLDER_VIDEOS = os.path.join(BASE_DIR, 'uploads', 'videos')
UPLOAD_FOLDER_AUDIO = os.path.join(BASE_DIR, 'uploads', 'audio')
os.makedirs(UPLOAD_FOLDER_PHOTOS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VIDEOS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_AUDIO, exist_ok=True)

db = SQLAlchemy(app)

# ================================
# Twilio Setup
# ================================
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_AUTH = os.getenv("TWILIO_AUTH", "")
TWILIO_PHONE = os.getenv("TWILIO_PHONE", "")

twilio_client = None
if TWILIO_SID and TWILIO_AUTH and TWILIO_PHONE:
    try:
        twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
    except Exception as e:
        print("⚠️ Twilio init failed:", e)


def send_otp_via_sms(phone, otp):
    if not twilio_client:
        print("⚠️ Twilio not configured, returning OTP directly.")
        return None
    try:
        message = twilio_client.messages.create(
            body=f"Your OTP is {otp}. It is valid for 5 minutes.",
            from_=TWILIO_PHONE,
            to=f"+91{phone}"
        )
        return message.sid
    except Exception as e:
        print("⚠️ SMS sending failed:", e)
        return None


# ================================
# Models
# ================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    otp = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    gps_lat = db.Column(db.Float, nullable=True)
    gps_lon = db.Column(db.Float, nullable=True)
    photo = db.Column(db.String(200), nullable=True)
    video = db.Column(db.String(200), nullable=True)
    count = db.Column(db.Integer, default=1)
    priority = db.Column(db.String(10), default="Low")
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# ================================
# Voice Utilities
# ================================
def record_voice_to_text():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("🎤 Please speak your complaint...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("✅ Voice recognized:", text)
        return text
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print("⚠️ Voice recognition failed:", e)
        return None


def text_to_speech_file(message, filename):
    engine = pyttsx3.init()
    filepath = os.path.join(UPLOAD_FOLDER_AUDIO, filename)
    engine.save_to_file(message, filepath)
    engine.runAndWait()
    return filepath


# ================================
# Red Zone Setup
# ================================
RED_ZONE_DATA_PATH = os.path.join(BASE_DIR, "red_zone_map_data.json")
red_zone_detector = RedZoneDetector()

if os.path.exists(RED_ZONE_DATA_PATH):
    with open(RED_ZONE_DATA_PATH, "r") as f:
        red_zone_data = json.load(f)
else:
    red_zone_data = {"zones": []}


# ================================
# OTP APIs
# ================================
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get("phone")
    name = data.get("name")

    if not phone or not name:
        return jsonify({"message": "Name and phone number required"}), 400

    user = User.query.filter_by(phone=phone).first()
    if not user:
        user = User(phone=phone, name=name)
        db.session.add(user)

    otp = str(random.randint(1000, 9999))
    user.otp = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()

    sms_id = send_otp_via_sms(phone, otp)

    return jsonify({
        "message": "OTP sent to your mobile number" if sms_id else "OTP generated (Twilio not configured)",
        "phone": phone,
        "name": user.name,
        "otp": "sent_via_sms" if sms_id else otp,
        "expires_at": user.otp_expiry.isoformat()
    })


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get("phone")
    otp = data.get("otp")

    user = User.query.filter_by(phone=phone).first()
    if not user:
        return jsonify({"message": "User not found"}), 404
    if user.otp != otp:
        return jsonify({"message": "Invalid OTP"}), 401
    if datetime.utcnow() > user.otp_expiry:
        return jsonify({"message": "OTP expired"}), 401

    user.otp = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({
        "message": "Login successful",
        "name": user.name,
        "phone": phone,
        "user_id": user.id
    })


# ================================
# Complaint APIs
# ================================
@app.route('/complaints', methods=['POST'])
def add_complaint():
    data = request.form
    user_id = data.get("user_id")
    text = data.get("text", "")
    category = data.get("category", "")
    gps_lat = float(data.get("gps_lat", 0))
    gps_lon = float(data.get("gps_lon", 0))

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    photo_file = request.files.get("photo")
    video_file = request.files.get("video")

    photo_filename = None
    video_filename = None
    if photo_file:
        photo_filename = secure_filename(photo_file.filename)
        photo_file.save(os.path.join(UPLOAD_FOLDER_PHOTOS, photo_filename))
    if video_file:
        video_filename = secure_filename(video_file.filename)
        video_file.save(os.path.join(UPLOAD_FOLDER_VIDEOS, video_filename))

    priority = "Low"
    if "fire" in text.lower() or category.lower() == "fire":
        priority = "High"

    new_complaint = Complaint(
        user_id=user.id,
        text=text,
        category=category,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        photo=photo_filename,
        video=video_filename,
        priority=priority
    )
    db.session.add(new_complaint)
    db.session.commit()

    df_new = pd.DataFrame([{"latitude": gps_lat, "longitude": gps_lon}])
    red_zone_detector.assign_complaints_to_grids(df_new)
    updated_map = red_zone_detector.get_map_data()

    with open(RED_ZONE_DATA_PATH, "w") as f:
        json.dump(updated_map, f, indent=4)

    return jsonify({
        "message": "Complaint added successfully",
        "complaint_id": new_complaint.id,
        "priority": new_complaint.priority,
        "red_zone_update": updated_map
    })


@app.route('/complaints', methods=['GET'])
def list_complaints():
    comps = Complaint.query.order_by(Complaint.created_at.desc()).all()
    results = []
    for c in comps:
        results.append({
            "id": c.id,
            "text": c.text,
            "category": c.category,
            "gps": [c.gps_lat, c.gps_lon],
            "photo": f"/uploads/photos/{c.photo}" if c.photo else None,
            "video": f"/uploads/videos/{c.video}" if c.video else None,
            "priority": c.priority,
            "count": c.count,
            "status": c.status,
            "created_at": c.created_at.isoformat()
        })
    return jsonify(results)


# ================================
# Apply Scheme API
# ================================
@app.route('/apply_scheme', methods=['POST'])
def apply_scheme():
    data = request.get_json()
    user_id = data.get("user_id")
    scheme = data.get("scheme")

    if not user_id or not scheme:
        return jsonify({"message": "user_id and scheme required"}), 400

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({"message": f"User {user.name} applied for {scheme} successfully!"})


# ================================
# Red Zone API
# ================================
@app.route('/red_zones', methods=['GET'])
def get_red_zones():
    if os.path.exists(RED_ZONE_DATA_PATH):
        with open(RED_ZONE_DATA_PATH, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"zones": []})


# ================================
# Text-to-Speech API
# ================================
@app.route('/speak', methods=['POST'])
def speak():
    data = request.json
    message = data.get("message", "")
    if not message:
        return jsonify({"message": "No text provided"}), 400

    filename = f"speak_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.wav"
    filepath = text_to_speech_file(message, filename)

    return jsonify({
        "message": "Audio generated",
        "file": f"/uploads/audio/{filename}"
    })


# ================================
# Static file serving
# ================================
@app.route('/uploads/photos/<filename>')
def get_photo(filename):
    return send_from_directory(UPLOAD_FOLDER_PHOTOS, filename)


@app.route('/uploads/videos/<filename>')
def get_video(filename):
    return send_from_directory(UPLOAD_FOLDER_VIDEOS, filename)


@app.route('/uploads/audio/<filename>')
def get_audio(filename):
    return send_from_directory(UPLOAD_FOLDER_AUDIO, filename)


# ================================
# Run Flask
# ================================
if __name__ == '__main__':
    app.run(debug=True)










