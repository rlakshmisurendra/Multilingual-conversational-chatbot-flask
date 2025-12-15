# UniLingo (Flask + Firebase Auth)

This converts the original Streamlit app into a Flask application while preserving the core chatbot logic (Gemini) and replacing Google OIDC with Firebase Authentication. The chatbot is branded as **UniLingo**.

## Setup

1. Create a Firebase project and enable Authentication (e.g., Google provider or email/password).
2. Download a Service Account JSON (Project settings → Service accounts) and either:
   - set `GOOGLE_APPLICATION_CREDENTIALS` to its file path, or
   - set `FIREBASE_SERVICE_ACCOUNT_JSON` to the JSON content (as a single env var).
3. In `static/firebase-init.js`, fill your web app config from Firebase Console → Project settings → General → SDK setup & configuration.
4. Set `GEMINI_API_KEY` (Google Generative AI) as an environment variable.
5. Optionally set `FLASK_SECRET_KEY` for session signing.

## Install & Run

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Environment
$env:GEMINI_API_KEY = "<your_gemini_api_key>"
# Option A
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\\path\\to\\service-account.json"
# Option B
# $env:FIREBASE_SERVICE_ACCOUNT_JSON = (Get-Content -Raw "C:\\path\\to\\service-account.json")
# Optional
# $env:FLASK_SECRET_KEY = "some-long-random-string"

python app.py
```

Visit http://localhost:8080 for the chat UI. Use Firebase login; the browser acquires an ID token and the backend verifies it.

## Admin

- Add your admin emails in `app.py` under `ADMIN_EMAILS`.
- Open http://localhost:8080/admin while logged in as an admin email.

## Notes

- Chat history is stored in the Flask session and sent as context to Gemini on each request.
- Usage stats are recorded in Firestore per user (`usage` collection).
- Users are recorded in Firestore (`users` collection) on first login/update.
