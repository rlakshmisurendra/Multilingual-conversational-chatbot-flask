# UniLingo — Multilingual AI Chat Assistant

**UniLingo** is a secure, multilingual chatbot that detects your language and replies in the same language. Built with Flask, Firebase Authentication, Google Gemini AI, and Firestore for scalable, analytics-driven conversations.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Technologies](#technologies)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## Features

✨ **Multilingual Support**: Automatic language detection; replies in the user's language (English, Hindi, Tamil, Telugu, Kannada, etc.)

🔐 **Secure Authentication**: Email/password, Google, and GitHub login via Firebase

📊 **Admin Dashboard**: Real-time user and usage analytics

⏱️ **Session Timeout**: 5-minute inactivity timeout for security

💬 **Optimized Chat UI**: Scrollable messages area with fixed viewport; smooth composer

📱 **Responsive Design**: Works on desktop and mobile devices

🎨 **Modern Design**: Purple gradient theme with Inter font; accessible controls

---

## Architecture

Frontend (HTML/CSS/JS) → Firebase SDK → ID Token → Flask Backend → Firebase Admin + Gemini API + Firestore

---

## Prerequisites

- Python 3.8+
- Firebase Project with Authentication enabled
- Google Gemini API Key
- Firebase Service Account JSON
- Git

---

## Installation

### 1. Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Create `.env` File

```env
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/service-account-key.json
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
FLASK_SECRET_KEY=your_secret_key_here
PORT=8080
```

### 2. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project `mcc2-51b00`
3. Project Settings → Service Accounts → Generate new private key
4. Update path in `.env`

### 3. Configure `static/firebase-init.js`

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "mcc2-51b00.firebaseapp.com",
  projectId: "mcc2-51b00",
  storageBucket: "mcc2-51b00.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### 4. Enable Authentication Providers

In Firebase Console → Authentication:
- ✅ Email/Password
- ✅ Google
- ✅ GitHub (callback: `https://mcc2-51b00.firebaseapp.com/__/auth/handler`)

### 5. Configure Admin Emails

In `app.py`:

```python
ADMIN_EMAILS = {
    "your_email@example.com",
    "admin@example.com",
}
```

---

## Running the Application

```powershell
.venv\Scripts\Activate.ps1
python app.py
```

Visit **http://localhost:8080**

---

## Usage

- **Sign In**: Email, Google, or GitHub
- **Chat**: Type in any language; AI replies in the same language
- **Copy**: Click "Copy" button on any message
- **Admin**: Access dashboard with whitelisted email
- **Logout**: Clears session and records usage

---

## Session Timeout

Sessions expire after **5 minutes of inactivity**:
- Every API call updates `last_activity_ts`
- On timeout: session clears, user redirected to login
- Shows "Session expired" alert

---

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/chat` | Bearer | Send message, get reply |
| POST | `/api/clear` | Bearer | Clear chat history |
| POST | `/api/logout` | Bearer | Logout & record usage |
| GET | `/api/admin-data` | Bearer | Analytics (admin only) |

---

## Project Structure

```
MCC2/
├── app.py                  # Flask backend
├── requirements.txt        # Dependencies
├── .env                    # Config (GITIGNORE)
├── README.md              # This file
├── static/
│   ├── firebase-init.js   # Firebase config
│   └── unilingo-logo.svg  # Logo
└── templates/
    ├── home.html          # Landing page
    ├── index.html         # Chat interface
    ├── login.html         # Login (Email/Google/GitHub)
    ├── signup.html        # Signup (Email/Google/GitHub)
    └── admin.html         # Admin dashboard
```

---

## Technologies

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Auth | Firebase Authentication |
| AI/ML | Google Gemini 2.5 Flash |
| Database | Firestore (NoSQL) |
| Frontend | HTML5, CSS3, Vanilla JS |
| Config | python-dotenv |
| Detection | langdetect |

---

## Security

✅ Bearer token verification on all `/api/*` endpoints
✅ Firebase ID tokens validated server-side
✅ Admin whitelist protects dashboard
✅ 5-minute session timeout
✅ Secrets in `.env` (never hardcoded)
✅ Error messages sanitized

---

## Troubleshooting

### "GEMINI_API_KEY not set"
→ Add `GEMINI_API_KEY=...` to `.env`

### "Firebase credentials file not found"
→ Update `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

### "auth/cancelled-popup-request"
→ Normal if popup closed; try again

### "Session expired"
→ Inactive 5+ mins; sign in again

### GitHub OAuth: "redirect_uri not associated"
→ Callback must be: `https://mcc2-51b00.firebaseapp.com/__/auth/handler`

---

## Support

Made with ❤️ by Department of CSE – AIML
