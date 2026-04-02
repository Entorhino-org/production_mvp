# 🎓 Entorhino — AI-Powered Academic Monitoring Platform

Entorhino is a comprehensive school management and academic monitoring platform powered by AI. It provides real-time performance tracking, AI-driven assessments, voice interviews, smart alerts, and gap analysis for students, teachers, parents, and administrators.

---

## 🆕 Recent Updates (Vinaybadnoriya)

- **🎨 Modern Branding & UI Update**: 
  - Replaced text-based logo with a sleek animal icon logo across all authentication (Login, Register, Onboarding, OTP) and dashboard pages.
  - Optimized logo dimensions and professional styling for a premium identity.
- **🏛️ Book-like Mathematical Formatting**: 
  - Integrated **KaTeX** library in the student portal, rendering AI lessons and math formulas in professional, high-quality LaTeX style (identical to academic textbooks).
  - Supports complex formulas in Mathematics, Physics, and Advanced Science.
- **🧠 AI Tutor Optimization**: 
  - Updated the AI system prompt in `app/api/analytics.py` to mandate professional LaTeX formatting and maintain an academic, textbook-like tone for all lessons.
- **🌓 Sidebar & Dark Mode Overhaul**: 
  - Resolved contrast/overlap issues in the sidebar header for dark mode.
  - Implemented automatic logo filtering (sleek white icons in dark mode) for a cohesive and high-end appearance.
  - Enhanced typography on dark backgrounds for crisp readability.
- **🛡️ Security & Integrity**: 
  - Audited the codebase for persistent "Mathematics" typos and fixed them across templates and models.
  - Removed hardcoded test OTP bypasses to ensure secure production-ready authentication.

---

## ✨ Key Features

### 🧑‍🎓 Students
- **AI-Generated Tests** — Take topic-based tests with AI-evaluated answers
- **Voice Interviews** — Real-time voice-based assessments via Gemini Live API
- **Homework Submission** — AI-powered scoring for handwritten (photos) or typed answers
- **Learn with AI** — Specialized AI tutoring with book-like math rendering
- **Gap Analysis** — AI identifies weak concepts and suggests improvement areas
- **Leaderboard** — Real-time gamified rankings across the school

### 👩‍🏫 Teachers
- **Topic & Notes Upload** — Automatic AI text extraction from PDFs and images
- **Test Creation** — Generate custom tests from uploaded topics in seconds
- **Homework Management** — Automated AI evaluation and tracking
- **Class Insights** — Deep analytics on performance trends and section rankings
- **Attendance** — Simplified daily attendance tracking

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (async), Python 3.11+ |
| **Database** | PostgreSQL + SQLAlchemy (asyncpg) |
| **Cache** | Redis (session management, rate limiting) |
| **AI Engine** | OpenRouter (Gemini/GPT for analysis), Gemini Live API (voice) |
| **Math Rendering**| **KaTeX** (LaTeX style high-fidelity math formatting) |
| **Email** | Resend API |
| **Frontend** | Vanilla HTML5/CSS3/JS (No-build system, high performance) |
| **Auth** | JWT (Refresh tokens), OTP verification via Email |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### 1. Installation

```bash
git clone https://github.com/Entorhino-org/production_mvp.git
cd production_mvp
python -m venv venv
# On Windows: venv\Scripts\activate
# On Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Update .env with your local credentials and API keys
```

### 3. Database & Admin Setup

```bash
# Set up your PostgreSQL database (default name: entorhino)
# Run the seed script to create the initial super-admin account
python seed_admin.py
```

### 4. Run Development Server

```bash
# Ensure Redis is running
redis-server

# Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000** to access the dashboard.

---

### 📄 License
This project is proprietary. All rights reserved by Entorhino.
