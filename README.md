# 🎓 Entorhino — AI-Powered Academic Monitoring Platform

Entorhino is a comprehensive school management and academic monitoring platform powered by AI. It provides real-time performance tracking, AI-driven assessments, voice interviews, smart alerts, and gap analysis for students, teachers, parents, and administrators.

---

## ✨ Key Features

### 🧑‍🎓 Students
- **AI-Generated Tests** — Take topic-based tests with AI-evaluated answers
- **Voice Interviews** — Real-time voice-based assessments via Gemini Live API
- **Homework Submission** — Upload photos or type answers; AI checks and scores instantly
- **Gap Analysis** — AI identifies weak concepts and suggests improvement areas
- **Leaderboard** — Gamified rankings across sections

### 👩‍🏫 Teachers
- **Topic & Notes Upload** — Upload PDFs / images; AI extracts text automatically
- **Test Creation** — Generate tests from uploaded topics with configurable question counts
- **Homework Management** — Assign, track submissions, and review AI-evaluated results
- **Class Insights** — Subject-scoped analytics: averages, rankings, and performance trends
- **Attendance** — Mark daily attendance (class teacher only)

### 👪 Parents
- **Performance Dashboard** — View linked student's scores, attendance, and homework
- **Smart Alerts** — Automatic notifications for poor test/homework performance (<50%)
- **Push Notifications** — Real-time web push alerts for important events

### 🛡️ Administrators
- **School Management** — Classes, sections, subjects, teacher assignments
- **Join Request Approval** — Approve/reject student and teacher registrations
- **System Config** — Manage AI API keys, models, VAD settings, and rate limits
- **Server Logs** — View recent application logs from the dashboard
- **Announcements** — Broadcast to all users or specific roles

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (async), Python 3.11+ |
| **Database** | PostgreSQL + SQLAlchemy (asyncpg) |
| **Cache** | Redis (session management, rate limiting) |
| **AI** | OpenRouter (GPT/Gemini), Gemini Live API (voice) |
| **Email** | Resend API |
| **Frontend** | Vanilla HTML/CSS/JS (server-rendered templates) |
| **Auth** | JWT (access + refresh tokens), OTP email verification |
| **Push** | Web Push Notifications (VAPID) |

---

## 📁 Project Structure

```
ent_mvp/
├── app/
│   ├── api/              # FastAPI route handlers
│   │   ├── auth.py       # Login, register, OTP, token refresh
│   │   ├── tests.py      # Test CRUD, AI evaluation, voice answers
│   │   ├── homework.py   # Homework assign, submit, AI check
│   │   ├── analytics.py  # Class insights, student performance
│   │   ├── topics.py     # Topic upload, text extraction
│   │   ├── announcements.py
│   │   ├── push.py       # Web push notifications
│   │   ├── voice_interview.py  # Gemini Live WebSocket
│   │   └── websocket.py  # Real-time WebSocket manager
│   ├── core/             # Dependencies, security, rate limiting
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # AI, email, analytics business logic
│   ├── templates/        # Jinja2 HTML templates
│   ├── config.py         # App settings (env vars)
│   ├── database.py       # Async DB session factory
│   └── main.py           # FastAPI app entrypoint
├── static/
│   ├── css/style.css     # Design system + dark mode
│   └── js/app.js         # Frontend client (auth, API, UI)
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── seed_admin.py         # Create initial admin user
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### 1. Clone & Install

```bash
git clone https://github.com/Entorhino-org/production_mvp.git
cd production_mvp
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database URL, JWT secrets, and API keys
```

Generate JWT secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Setup Database

```bash
# Create PostgreSQL database
createdb entorhino

# Seed the admin user
python seed_admin.py
```

### 4. Start Redis

```bash
redis-server
```

### 5. Run the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000** to access the application.

---

## ⚙️ Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `JWT_SECRET_KEY` | Secret for access token signing |
| `JWT_REFRESH_SECRET_KEY` | Secret for refresh token signing |
| `OPENROUTER_API_KEY` | Bootstrap AI API key (overridable via UI) |
| `REDIS_URL` | Redis connection URL |
| `UPLOAD_DIR` | Directory for file uploads |
| `MAX_UPLOAD_SIZE_MB` | Max upload file size |

Additional AI keys (Gemini, Resend, VAPID) are configured via the **System Config** panel in the admin dashboard.

---

## 🌙 Dark Mode

All pages include a toggle button (🌙/☀️) for switching between light and dark (neon) themes. The preference is persisted in `localStorage`.

---

## 📱 Mobile Support

The UI is fully responsive with:
- Collapsible sidebar with backdrop overlay
- Touch-friendly navigation and form elements
- Scrollable tables for data-heavy views
- Optimized modals, toasts, and cards for small screens

---

## 🔒 Security

- JWT-based authentication with automatic token refresh
- OTP email verification for new accounts
- Role-based access control (Student, Teacher, Parent, Admin, School Admin)
- Rate limiting via Redis
- CORS protection

---

## 📄 License

This project is proprietary. All rights reserved by Entorhino.
