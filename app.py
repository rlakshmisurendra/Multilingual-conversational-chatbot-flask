from langdetect import detect
import google.generativeai as genai

import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth

import os
import json
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template, session, g

# Load environment variables from .env file - FORCE OVERRIDE system variables
load_dotenv(override=True)

# Put your admin e-mail(s) here
ADMIN_EMAILS = {
    "rlsurendra49@gmail.com",
}

# ================== BASIC CONFIG ==================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

print(f"[Config] Loading from .env file...")
print(f"[Config] GEMINI_API_KEY raw: '{GEMINI_API_KEY}'")
print(f"[Config] GEMINI_API_KEY length: {len(GEMINI_API_KEY) if GEMINI_API_KEY else 0}")
print(f"[Config] GEMINI_API_KEY type: {type(GEMINI_API_KEY)}")
print(f"[Config] GEMINI_MODEL: {MODEL_NAME}")

# Strip any whitespace from API key
if GEMINI_API_KEY:
    GEMINI_API_KEY = GEMINI_API_KEY.strip()
    print(f"[Config] GEMINI_API_KEY after strip: '{GEMINI_API_KEY}'")
    print(f"[Config] GEMINI_API_KEY after strip length: {len(GEMINI_API_KEY)}")

SYSTEM_PROMPT = (
    "You are a helpful multilingual conversational AI assistant.\n\n"
    "Rules:\n"
    "1. Detect the user's language.\n"
    "2. Always reply in the SAME language used by the user.\n"
    "3. Be clear, concise and friendly.\n"
    "4. If user mixes languages, reply in the dominant language.\n"
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env file. Please add it: GEMINI_API_KEY=your_api_key")

# ================== INIT FIREBASE ADMIN ==================

def init_firebase_app() -> None:
    if firebase_admin._apps:
        return
    
    gac_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not gac_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set in .env file")
    
    if not os.path.exists(gac_path):
        raise RuntimeError(f"Firebase credentials file not found at: {gac_path}")
    
    print(f"[Firebase] Loading credentials from: {gac_path}")
    cred_obj = credentials.Certificate(gac_path)
    
    # Print project ID to verify correct credentials
    with open(gac_path, 'r') as f:
        creds_data = json.load(f)
        print(f"[Firebase] Project ID: {creds_data.get('project_id', 'unknown')}")
    
    firebase_admin.initialize_app(cred_obj)


init_firebase_app()
db = firestore.client()

# ================== INIT GEMINI ==================

print(f"[Gemini] API Key loaded: {GEMINI_API_KEY[:10]}..." if GEMINI_API_KEY else "[Gemini] ERROR: No API key!")
print(f"[Gemini] Model: {MODEL_NAME}")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=SYSTEM_PROMPT,
)


# ================== HELPERS ==================

def safe_detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"


def lang_label(lang_code: str) -> str:
    mapping = {
        "en": "English",
        "hi": "Hindi",
        "te": "Telugu",
        "ta": "Tamil",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "gu": "Gujarati",
        "bn": "Bengali",
        "ur": "Urdu",
    }
    if lang_code in mapping:
        return f"{mapping[lang_code]} ({lang_code})"
    if lang_code == "unknown":
        return "Unknown"
    return lang_code


def ensure_user_doc(uid: str, name: str, email: str, picture: str = "") -> None:
    users_ref = db.collection("users").document(uid)
    now = datetime.now(timezone.utc).isoformat()
    doc = users_ref.get()
    if doc.exists:
        users_ref.update({
            "name": name,
            "email": email,
            "picture": picture,
            "last_login_at": now,
        })
    else:
        users_ref.set({
            "uid": uid,
            "name": name,
            "email": email,
            "picture": picture,
            "created_at": now,
            "last_login_at": now,
        })


def update_usage_stats(uid: str, session_start_ts: float, total_messages: int) -> None:
    usage_ref = db.collection("usage").document(uid)
    now_ts = time.time()
    session_seconds = int(now_ts - session_start_ts)
    
    # Get current stats to calculate totals
    current_doc = usage_ref.get()
    current_data = current_doc.to_dict() if current_doc.exists else {}
    
    # Calculate totals (cumulative from all time)
    total_all_messages = (current_data.get("total_messages", 0) or 0) + total_messages
    total_all_seconds = (current_data.get("total_session_seconds", 0) or 0) + session_seconds
    
    usage_ref.set(
        {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            # Last session metrics
            "last_session_seconds": session_seconds,
            "last_session_messages": total_messages,
            # All-time totals
            "total_messages": total_all_messages,
            "total_session_seconds": total_all_seconds,
        },
        merge=True,
    )


def to_gemini_history(messages):
    history = []
    for m in messages:
        role = m.get("role")
        if role == "assistant":
            role = "model"
        history.append({"role": role, "parts": [m.get("content", "")]})
    return history


def verify_bearer_token() -> dict:
    auth_header = request.headers.get("Authorization", "")
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]
        try:
            decoded = fb_auth.verify_id_token(token)
            return decoded
        except Exception as e:
            raise PermissionError(f"Invalid Firebase token: {e}")
    raise PermissionError("Missing or invalid Authorization header. Expected 'Bearer <token>'.")


# ================== FLASK APP ==================

def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

    @app.before_request
    def attach_user():
        g.user = None
        
        # Session timeout check (5 minutes of inactivity)
        SESSION_TIMEOUT = 300  # 5 minutes in seconds
        if "last_activity_ts" in session:
            now = time.time()
            time_since_activity = now - session["last_activity_ts"]
            if time_since_activity > SESSION_TIMEOUT:
                print(f"[Session] Timeout after {time_since_activity:.0f}s of inactivity")
                session.clear()
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Session expired", "detail": "Please sign in again"}), 401
        
        if request.path.startswith("/api/"):
            try:
                decoded = verify_bearer_token()
            except PermissionError as e:
                return jsonify({"error": "Unauthorized", "detail": str(e)}), 401

            g.user = {
                "uid": decoded.get("uid") or decoded.get("sub"),
                "email": decoded.get("email", ""),
                "name": decoded.get("name", ""),
                "picture": decoded.get("picture", ""),
            }
            # Log token audience info to help diagnose project mismatch
            try:
                aud = decoded.get("aud")
                iss = decoded.get("iss")
                print(f"[Auth] uid={g.user['uid']} email={g.user['email']} aud={aud} iss={iss}")
            except Exception:
                pass
            ensure_user_doc(g.user["uid"], g.user["name"], g.user["email"], g.user["picture"])

            if "session_start_ts" not in session:
                session["session_start_ts"] = time.time()
                session["total_user_messages"] = 0
                session["messages"] = []
            
            # Update last activity timestamp on every API call
            session["last_activity_ts"] = time.time()

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/chat")
    def chat_page():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    @app.get("/signup")
    def signup_page():
        return render_template("signup.html")

    @app.get("/admin")
    def admin():
        # Static shell; data is fetched via /api/admin-data with Firebase token
        return render_template("admin.html")

    @app.get("/api/admin-data")
    def admin_data():
        if not g.get("user"):
            return jsonify({"error": "Unauthorized"}), 401
        if g.user.get("email") not in ADMIN_EMAILS:
            return jsonify({"error": "Forbidden"}), 403

        user_docs = list(db.collection("users").stream())
        users = []
        for d in user_docs:
            data = d.to_dict()
            users.append({
                "uid": d.id,
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "created_at": data.get("created_at", ""),
                "last_login_at": data.get("last_login_at", ""),
            })

        usage_docs = list(db.collection("usage").stream())
        usage_map = {doc.id: doc.to_dict() for doc in usage_docs}
        for u in users:
            u_usage = usage_map.get(u["uid"], {})
            # Last session metrics
            u["last_session_seconds"] = u_usage.get("last_session_seconds", 0)
            u["last_session_messages"] = u_usage.get("last_session_messages", 0)
            # Total metrics from date created
            u["total_messages"] = u_usage.get("total_messages", 0)
            u["total_session_seconds"] = u_usage.get("total_session_seconds", 0)
            u["usage_last_updated"] = u_usage.get("last_updated", "")

        total_users = len(users)
        # Calculate totals: sum of all total_messages (from date created)
        total_messages = sum(int(u.get("total_messages", 0)) for u in users)
        total_time_sec = sum(int(u.get("total_session_seconds", 0)) for u in users)

        return jsonify({
            "users": users,
            "total_users": total_users,
            "total_messages": total_messages,
            "total_time_min": total_time_sec // 60,
        })

    @app.post("/api/chat")
    def chat_api():
        if not g.get("user"):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        user_input = (data.get("message") or "").strip()
        if not user_input:
            return jsonify({"error": "Empty message"}), 400

        lang = safe_detect_language(user_input)

        # Update session messages
        messages = session.get("messages", [])
        messages.append({"role": "user", "content": user_input, "lang": lang})

        chat_obj = model.start_chat(history=to_gemini_history(messages))
        try:
            response = chat_obj.send_message(user_input)
            bot_reply = response.text
        except Exception as e:
            print(f"[Error] Gemini API error: {str(e)}")
            return jsonify({"error": f"API Error: {str(e)}"}), 500

        messages.append({"role": "assistant", "content": bot_reply, "lang": lang})
        session["messages"] = messages
        session["total_user_messages"] = int(session.get("total_user_messages", 0)) + 1

        # Update usage
        if session.get("session_start_ts"):
            try:
                update_usage_stats(
                    g.user["uid"],
                    session["session_start_ts"],
                    session["total_user_messages"],
                )
            except Exception:
                pass

        return jsonify({
            "reply": bot_reply,
            "lang": lang,
            "lang_label": lang_label(lang),
        })

    @app.post("/api/clear")
    def clear_chat():
        if not g.get("user"):
            return jsonify({"error": "Unauthorized"}), 401
        session["messages"] = []
        session["total_user_messages"] = 0
        return jsonify({"ok": True})

    @app.post("/api/logout")
    def logout():
        if g.get("user") and session.get("session_start_ts"):
            try:
                update_usage_stats(
                    g.user["uid"],
                    session["session_start_ts"],
                    session.get("total_user_messages", 0),
                )
            except Exception:
                pass
        session.clear()
        return jsonify({"ok": True})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
