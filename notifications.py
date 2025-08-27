# For demo: just print messages. Replace with Email/SMS/FCM later.
def notify_user(user_name: str, message: str):
    print(f"[NOTIFY USER] To: {user_name} | {message}")

def notify_department(message: str):
    print(f"[NOTIFY DEPT] {message}")
