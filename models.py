from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Integer, String, Float, Text
from sqlalchemy.types import JSON as _JSON

db = SQLAlchemy()

# Fallback JSON type for SQLite using Text (store as stringified JSON)
import json
class JSONEncodedDict(db.TypeDecorator):
    impl = Text
    cache_ok = True
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

class Complaint(db.Model):
    id = db.Column(Integer, primary_key=True)
    user_name = db.Column(String(80), nullable=False)
    title = db.Column(String(200), nullable=False)
    description = db.Column(Text, default='')
    category = db.Column(String(50), default='General')
    priority = db.Column(String(20), default='Low')
    status = db.Column(String(20), default='pending')  # pending, in_progress, resolved
    lat = db.Column(Float)
    lng = db.Column(Float)
    media_urls = db.Column(JSONEncodedDict)  # list of URLs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user_name,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'lat': self.lat,
            'lng': self.lng,
            'media_urls': self.media_urls or [],
            'created_at': self.created_at.isoformat() + 'Z',
            'updated_at': (self.updated_at.isoformat() + 'Z') if self.updated_at else None
        }
