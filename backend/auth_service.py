import json
import os
import time
import hashlib
import hmac
import secrets

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_db.json")

# Default demo user
DEFAULT_USERS = {
    "aarjoo@surakshax.org": {
        "email": "aarjoo@surakshax.org",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "name": "Aarjoo Dahiya",
        "phone": "9876543210",
        "gender": "Female",
        "blood_group": "O+",
        "token": "token_demo_aarjoo",
        "guardians": []
    }
}

class AuthService:
    def __init__(self):
        self.users = {}
        self.load_db()

    def load_db(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.users = json.load(f)
            except Exception as e:
                print(f"Error loading users DB, using default: {e}")
                self.users = DEFAULT_USERS.copy()
        else:
            self.users = DEFAULT_USERS.copy()
            self.save_db()

    def save_db(self):
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"Error saving users DB: {e}")

    def hash_password(self, password: str, salt: str = None) -> str:
        """Salted PBKDF2-SHA256, stored as 'pbkdf2$<salt>$<hex>'."""
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
        return f"pbkdf2${salt}${digest}"

    def verify_password(self, password: str, stored: str) -> bool:
        stored = stored or ""
        if stored.startswith("pbkdf2$"):
            _, salt, _digest = stored.split("$", 2)
            return hmac.compare_digest(self.hash_password(password, salt), stored)
        # Legacy unsalted SHA-256 records
        return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)

    @staticmethod
    def new_token() -> str:
        return secrets.token_urlsafe(32)

    def register(self, email: str, password: str, name: str, phone: str = "", gender: str = "Female", blood_group: str = "O+"):
        email_clean = email.strip().lower()
        if not email_clean or not password:
            return {"success": False, "error": "Email and password are required"}

        if email_clean in self.users:
            return {"success": False, "error": "An account with this email already exists"}

        if len(password) < 6:
            return {"success": False, "error": "Password must be at least 6 characters"}

        token = self.new_token()
        user_record = {
            "email": email_clean,
            "password_hash": self.hash_password(password),
            "name": name.strip() or "Registered User",
            "phone": phone.strip(),
            "gender": gender,
            "blood_group": blood_group,
            "token": token,
            "guardians": []
        }
        self.users[email_clean] = user_record
        self.save_db()

        return {
            "success": True,
            "token": token,
            "user": self.sanitize_user(user_record)
        }

    def login(self, email: str, password: str):
        email_clean = email.strip().lower()
        user = self.users.get(email_clean)

        if not user:
            # Check demo fallback
            if email_clean == "aarjoo@surakshax.org" and password == "password123":
                self.users[email_clean] = DEFAULT_USERS["aarjoo@surakshax.org"]
                user = self.users[email_clean]
            else:
                return {"success": False, "error": "Invalid email or password"}

        if not self.verify_password(password, user.get("password_hash")):
            return {"success": False, "error": "Invalid email or password"}

        # Upgrade legacy hashes and rotate the session token on every login
        if not user.get("password_hash", "").startswith("pbkdf2$"):
            user["password_hash"] = self.hash_password(password)
        token = self.new_token()
        user["token"] = token
        self.save_db()

        return {
            "success": True,
            "token": token,
            "user": self.sanitize_user(user)
        }

    def get_user_by_token(self, token: str):
        if not token:
            return None
        for u in self.users.values():
            if u.get("token") and hmac.compare_digest(u.get("token"), token):
                return self.sanitize_user(u)
        return None

    def update_guardians(self, token: str, guardians_list: list):
        if not token:
            return {"success": False, "error": "Authentication required"}
        for email, u in self.users.items():
            if u.get("token") and hmac.compare_digest(u.get("token"), token):
                u["guardians"] = guardians_list
                self.save_db()
                return {"success": True, "guardians": guardians_list}
        return {"success": False, "error": "User not found"}

    def sanitize_user(self, user_record: dict) -> dict:
        copy_u = user_record.copy()
        copy_u.pop("password_hash", None)
        copy_u.pop("token", None)
        return copy_u

_auth_service = None
def get_auth_service():
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
