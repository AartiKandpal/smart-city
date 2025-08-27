import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_file(file, prefix=""):
    """Save uploaded file securely."""
    if file:
        filename = secure_filename(file.filename)
        final_name = f"{prefix}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, final_name)
        file.save(file_path)
        return file_path
    return None

def notify_user(email, subject, message):
    """Stub for notifications (print for now)."""
    print(f"Notify {email} | {subject}:\n{message}")
