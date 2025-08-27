from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ----------------------
# Users (phone + name + OTP login)
# ----------------------
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)        # full name of citizen
    phone = db.Column(db.String(15), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    complaints = db.relationship("Complaint", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.name} ({self.phone})>"


# ----------------------
# OTP (separate table)
# ----------------------
class OtpCode(db.Model):
    __tablename__ = "otp_code"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    code = db.Column(db.String(10), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<OTP {self.phone} exp={self.expires_at}>"


# ----------------------
# Complaints
# ----------------------
class Complaint(db.Model):
    __tablename__ = "complaint"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    text = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)   # e.g., Electricity, Water, etc.

    gps_lat = db.Column(db.Float, nullable=True)
    gps_lon = db.Column(db.Float, nullable=True)

    photo = db.Column(db.String(255), nullable=True)  # filesystem path
    video = db.Column(db.String(255), nullable=True)  # filesystem path
    audio = db.Column(db.String(255), nullable=True)  # 🔹 NEW: audio file path for voice complaints

    count = db.Column(db.Integer, default=1)          # duplicate count
    priority = db.Column(db.String(10), default="Low")  # "Low" / "High"

    status = db.Column(db.String(20), default="Pending")  # "Pending" / "Done"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Complaint {self.id} {self.category} {self.priority} x{self.count}>"



