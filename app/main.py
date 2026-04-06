"""
Entorhino — FastAPI application entry point.
Sets up middleware, mounts static files, registers all API routers.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.database import engine, Base

# Import all models so they are registered with SQLAlchemy
from app.models import *  # noqa: F401, F403

# Import all API routers
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.admin import router as admin_router
from app.api.topics import router as topics_router
from app.api.tests import router as tests_router
from app.api.attendance import router as attendance_router
from app.api.announcements import router as announcements_router
from app.api.feedback import router as feedback_router
from app.api.alerts import router as alerts_router
from app.api.homework import router as homework_router
from app.api.analytics import router as analytics_router
from app.api.websocket import router as ws_router
from app.api.voice_interview import router as voice_router
from app.api.push import router as push_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (dev mode)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure upload directories exist
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR, "topics").mkdir(parents=True, exist_ok=True)
    Path(settings.UPLOAD_DIR, "homework").mkdir(parents=True, exist_ok=True)

    # Initialize Redis
    from app.core.redis import init_redis, close_redis
    await init_redis()

    yield

    await close_redis()
    await engine.dispose()


# ── Create FastAPI app ────────────────────────────────────────

app = FastAPI(
    title="Entorhino",
    description="AI-driven educational platform for student performance monitoring",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Validation error handler (clean 422 messages) ────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        # Extract the first human-readable message
        msg = errors[0].get("msg", "Validation error")
        # Remove "Value error, " prefix that Pydantic adds
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        return JSONResponse(status_code=422, content={"detail": msg})
    return JSONResponse(status_code=422, content={"detail": "Validation error"})

# ── CORS ──────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files & templates ─────────────────────────────────

static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

uploads_dir = Path(__file__).parent.parent / settings.UPLOAD_DIR
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# ── Register all API routers ─────────────────────────────────

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(topics_router)
app.include_router(tests_router)
app.include_router(attendance_router)
app.include_router(announcements_router)
app.include_router(feedback_router)
app.include_router(alerts_router)
app.include_router(homework_router)
app.include_router(analytics_router)
app.include_router(ws_router)
app.include_router(voice_router)
app.include_router(push_router)


# ── Frontend routes (serve Jinja2 templates) ──────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/verify-otp", response_class=HTMLResponse)
async def verify_otp_page(request: Request):
    return templates.TemplateResponse("verify_otp.html", {"request": request})


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    return templates.TemplateResponse("onboarding.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "config": settings})


# ── Health check ──────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": "Entorhino", "version": "1.0.0"}
