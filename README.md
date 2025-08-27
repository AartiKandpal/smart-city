# SIH Backend Starter (Flask)

Minimal, hackathon-ready backend for **Awaaz • Tarakki • Samadhan (ATS)** or any civic complaint + schemes app.

## Quick Start
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt

# Run
python app.py
```

Server starts at http://127.0.0.1:5000

## Endpoints
- `POST /api/complaints` – create complaint
- `GET /api/complaints` – list complaints (filters: `status`, `category`)
- `GET /api/complaints/<id>` – get complaint by id
- `PATCH /api/complaints/<id>/status` – update status (`pending`, `in_progress`, `resolved`)
- `GET /api/analytics` – basic stats
- `GET /api/schemes?age=20&income=200000&occupation=student` – rule-based scheme recommendations

## Sample curl
```bash
curl -X POST http://127.0.0.1:5000/api/complaints -H "Content-Type: application/json" -d '{
  "user_name": "Raj",
  "title": "Pothole near bus stop",
  "description": "Large pothole causing traffic",
  "lat": 28.61,
  "lng": 77.20,
  "media_urls": ["https://example.com/pothole.jpg"]
}'

curl http://127.0.0.1:5000/api/complaints
curl http://127.0.0.1:5000/api/analytics
curl "http://127.0.0.1:5000/api/schemes?age=21&income=150000&occupation=student"
```

## Notes
- Uses SQLite by default (`data.db`) for zero-setup storage.
- AI is **dummy** but wired – replace rules in `ai_module.py` later.
- Notifications are simulated via console logs in `notifications.py` to avoid external keys during demo.
