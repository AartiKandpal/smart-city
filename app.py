import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from functools import wraps

# ---------------- CONFIG ----------------
app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # change in prod
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB upload limit

db = SQLAlchemy(app)
jwt = JWTManager(app)

# ---------------- UTILITIES ----------------
def notify_user(email, subject, message):
    # stub notifications
    print(f"NOTIFY {email} | {subject} | {message}")

def auth_required(roles=[]):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            user = User.query.get(identity)
            if not user or (roles and user.role not in roles):
                return jsonify({"msg": "Unauthorized"}), 403
            return fn(user, *args, **kwargs)
        return wrapper
    return decorator

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # citizen | official | admin
    fullname = db.Column(db.String(120))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default="pending")  # pending | assigned | in_progress | resolved | closed
    priority = db.Column(db.String(10), default="Low")  # Low | Medium | High
    ai_category = db.Column(db.String(50))
    recommended_scheme = db.Column(db.String(200))
    duplicate_count = db.Column(db.Integer, default=0)
    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id"))
    official_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="assigned")  # assigned | accepted | rejected | completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaint.id"))
    official_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    note = db.Column(db.Text)
    file_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- DB INIT ----------------
with app.app_context():
    db.create_all()

# ---------------- AUTH ----------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    if not all(k in data for k in ("username","password","role")):
        return jsonify({"msg":"Missing fields"}), 400
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"msg":"User exists"}), 400
    user = User(
        username=data["username"],
        password_hash=generate_password_hash(data["password"]),
        role=data["role"],
        fullname=data.get("fullname"),
        email=data.get("email")
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"msg":"User created"}), 201

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(username=data.get("username")).first()
    if not user or not user.check_password(data.get("password")):
        return jsonify({"msg":"Bad username or password"}), 401
    token = create_access_token(identity=user.id, expires_delta=timedelta(hours=8))
    return jsonify({"access_token": token, "role": user.role}), 200

# ---------------- COMPLAINTS ----------------
@app.route("/api/complaints", methods=["POST"])
@jwt_required(optional=True)
def create_complaint():
    data = request.json
    if not data.get("title") or not data.get("description"):
        return jsonify({"msg":"Title and description required"}), 400
    reporter_id = get_jwt_identity()
    complaint = Complaint(
        title=data["title"],
        description=data["description"],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        reporter_id=reporter_id
    )
    db.session.add(complaint)
    db.session.commit()
    db.session.add(AuditLog(
        complaint_id=complaint.id,
        user_id=reporter_id,
        action="Complaint Created",
        details=f"Complaint '{complaint.title}' created"
    ))
    db.session.commit()
    return jsonify({"msg":"Complaint created","complaint_id":complaint.id}), 201

@app.route("/api/complaints", methods=["GET"])
@jwt_required(optional=True)
def list_complaints():
    complaints = Complaint.query.all()
    output = []
    for c in complaints:
        output.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "status": c.status,
            "priority": c.priority,
            "resolved_at": c.resolved_at
        })
    return jsonify(output)

@app.route("/api/complaints/<int:cid>", methods=["GET"])
@jwt_required(optional=True)
def get_complaint(cid):
    c = Complaint.query.get_or_404(cid)
    return jsonify({
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "status": c.status,
        "priority": c.priority,
        "resolved_at": c.resolved_at
    })

@app.route("/api/complaints/<int:cid>", methods=["PATCH"])
@auth_required(roles=["admin","official","citizen"])
def update_complaint(current_user, cid):
    c = Complaint.query.get_or_404(cid)
    data = request.json
    changes = []
    if "status" in data and current_user.role in ["admin","official"]:
        changes.append(f"Status: {c.status} -> {data['status']}")
        c.status = data["status"]
    if "priority" in data and current_user.role == "admin":
        changes.append(f"Priority: {c.priority} -> {data['priority']}")
        c.priority = data["priority"]
    if "title" in data:
        changes.append(f"Title changed")
        c.title = data["title"]
    if "description" in data:
        changes.append(f"Description changed")
        c.description = data["description"]
    db.session.add(AuditLog(
        complaint_id=c.id,
        user_id=current_user.id,
        action="Complaint Updated",
        details=", ".join(changes) if changes else "Updated fields"
    ))
    db.session.commit()
    return jsonify({"msg":"Updated"}), 200

@app.route("/api/complaints/<int:cid>", methods=["DELETE"])
@auth_required(roles=["admin"])
def delete_complaint(current_user, cid):
    c = Complaint.query.get_or_404(cid)
    db.session.delete(c)
    db.session.add(AuditLog(
        complaint_id=cid,
        user_id=current_user.id,
        action="Complaint Deleted",
        details=f"Complaint deleted"
    ))
    db.session.commit()
    return jsonify({"msg":"Deleted"}), 200

# ---------------- ASSIGNMENTS ----------------
@app.route("/api/complaints/<int:cid>/assign", methods=["POST"])
@auth_required(roles=["admin"])
def assign_complaint(current_user, cid):
    data = request.json
    official = User.query.get_or_404(data.get("official_id"))
    if official.role != "official":
        return jsonify({"msg":"Cannot assign to non-official"}), 400
    assignment = Assignment(
        complaint_id=cid,
        official_id=official.id,
        assigned_by=current_user.id
    )
    db.session.add(assignment)
    db.session.add(AuditLog(
        complaint_id=cid,
        user_id=current_user.id,
        action="Complaint Assigned",
        details=f"Assigned to {official.username}"
    ))
    db.session.commit()
    notify_user(official.email, "New Assignment", f"You have been assigned complaint {cid}")
    return jsonify({"msg":"Assigned","assignment_id":assignment.id}), 200

@app.route("/api/assignments", methods=["GET"])
@auth_required(roles=["official"])
def list_assignments(current_user):
    assignments = Assignment.query.filter_by(official_id=current_user.id).all()
    output = []
    for a in assignments:
        output.append({
            "id": a.id,
            "complaint_id": a.complaint_id,
            "status": a.status
        })
    return jsonify(output)

@app.route("/api/assignments/<int:aid>/accept", methods=["POST"])
@auth_required(roles=["official"])
def accept_assignment(current_user, aid):
    a = Assignment.query.get_or_404(aid)
    if a.official_id != current_user.id:
        return jsonify({"msg":"Unauthorized"}), 403
    a.status = "accepted"
    db.session.add(AuditLog(
        complaint_id=a.complaint_id,
        user_id=current_user.id,
        action="Assignment Accepted",
        details=f"Assignment {aid} accepted"
    ))
    db.session.commit()
    return jsonify({"msg":"Accepted"}), 200

@app.route("/api/assignments/<int:aid>/report", methods=["POST"])
@auth_required(roles=["official"])
def submit_report(current_user, aid):
    a = Assignment.query.get_or_404(aid)
    if a.official_id != current_user.id:
        return jsonify({"msg":"Unauthorized"}), 403
    note = request.form.get("note")
    file = request.files.get("file")
    if not note and not file:
        return jsonify({"msg":"Provide note or file"}), 400
    filename = None
    if file:
        safe_name = secure_filename(file.filename)
        filename = f"report_{aid}_{safe_name}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
    report = Report(
        complaint_id=a.complaint_id,
        official_id=current_user.id,
        note=note,
        file_url=filename
    )
    a.status = "completed"
    complaint = Complaint.query.get(a.complaint_id)
    complaint.status = "resolved"
    complaint.resolved_at = datetime.utcnow()
    db.session.add(report)
    db.session.add(AuditLog(
        complaint_id=a.complaint_id,
        user_id=current_user.id,
        action="Report Submitted",
        details=f"Report submitted for assignment {aid}"
    ))
    db.session.commit()
    # notify reporter/admin
    reporter = User.query.get(complaint.reporter_id)
    if reporter: notify_user(reporter.email, "Complaint Resolved", f"Complaint {complaint.id} resolved")
    return jsonify({"msg":"Report submitted"}), 200

@app.route("/api/complaints/<int:cid>/reports", methods=["GET"])
@jwt_required()
def list_reports(cid):
    reports = Report.query.filter_by(complaint_id=cid).all()
    output = []
    for r in reports:
        output.append({
            "id": r.id,
            "official_id": r.official_id,
            "note": r.note,
            "file_url": r.file_url,
            "created_at": r.created_at
        })
    return jsonify(output)

@app.route("/api/audit/complaint/<int:cid>", methods=["GET"])
@jwt_required()
def get_audit(cid):
    logs = AuditLog.query.filter_by(complaint_id=cid).all()
    output = []
    for l in logs:
        output.append({
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "details": l.details,
            "created_at": l.created_at
        })
    return jsonify(output)

# ---------------- STATIC FILES ----------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ---------------- GOVT ENDPOINTS (stub) ----------------
@app.route("/govt/analytics", methods=["GET"])
def govt_analytics():
    total = Complaint.query.count()
    resolved = Complaint.query.filter_by(status="resolved").count()
    pending = Complaint.query.filter_by(status="pending").count()
    return jsonify({
        "total_complaints": total,
        "resolved": resolved,
        "pending": pending
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
