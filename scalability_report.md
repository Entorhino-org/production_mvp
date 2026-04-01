# 📊 Entorhino — System Scalability & Production Readiness Report

> **System**: Entorhino — AI-driven educational platform (FastAPI + PostgreSQL + Redis)
> **Date**: April 2026  
> **Scope**: Codebase at [production_mvp]

---

## 1. Current System Capacity

### 1.1 Architecture Snapshot

| Layer | Technology | Current Config |
|-------|-----------|---------------|
| Runtime | Python 3.12 + FastAPI 0.115.6 | Single Uvicorn worker, no Gunicorn |
| Database | PostgreSQL via asyncpg + SQLAlchemy 2.0 (async) | `pool_size=50`, `max_overflow=20` |
| Cache | Redis 5.x (async, with in-memory fallback) | Single instance, no cluster |
| AI/LLM | OpenRouter (OpenAI SDK), Gemini Live API | Semaphore capped at 50 concurrent |
| Deployment | Single Docker container on VM | `docker run` via GitHub Actions SSH |
| WebSockets | 2 endpoints (notifications + voice interview) | In-process connection manager |

### 1.2 Estimated Concurrent User Capacity

| Scenario | Concurrent Users | req/sec | Bottleneck |
|----------|-----------------|---------|------------|
| **Current (1 Uvicorn worker)** | 50–150 | ~200–400 | Single event loop, no worker scaling |
| **With Gunicorn (4 workers)** | 200–600 | ~800–1,500 | DB pool saturation (50×4 = 200 conns) |
| **Optimized (8 workers + read replicas)** | 1,000–3,000 | ~2,000–4,000 | AI API rate limits, WebSocket memory |
| **Horizontally scaled (K8s, 4 pods)** | 5,000–10,000+ | ~8,000–15,000 | External API limits, Redis throughput |

### 1.3 Factors Affecting Current Capacity

**CPU-bound operations in the hot path:**

- `bcrypt.hashpw()` / `bcrypt.checkpw()` in [security.py] — these are **synchronous and CPU-intensive**. A single bcrypt hash takes ~200ms, blocking the async event loop.
- `resend.Emails.send()` in [email.py] — **synchronous HTTP call** blocking the event loop.

**I/O operations:**

- Every authenticated request triggers a DB query (`SELECT * FROM users WHERE id = ...`) in [dependencies.py].
- AI token limit check runs 2 additional DB queries per AI-gated endpoint ([dependencies.py:98-126]).
- Analytics endpoints issue 3–5 bulk SQL queries per call ([analytics.py]).

**Network latency:**

- OpenRouter API calls: 500ms–3s per AI completion.
- Gemini Live API WebSocket: persistent, bandwidth-heavy (PCM16 audio at 16kHz).

---

## 2. Bottleneck Analysis

### 2.1 Critical Bottlenecks Found in Codebase

#### 🔴 P0 — Blocking Synchronous Calls on Async Event Loop

| File | Line(s) | Issue | Impact |
|------|---------|-------|--------|
| [security.py] | 16–27 | `bcrypt.hashpw()` and `bcrypt.checkpw()` are **sync CPU-bound operations** running in the async event loop | Blocks ALL concurrent requests for ~200ms per login/register |
| [email.py] | 80–85 | `resend.Emails.send()` is **synchronous HTTP** | Blocks event loop for 200–1000ms per OTP send |
| [rate_limit.py] | 8–9 | In-memory fallback uses `threading.Lock` | Thread lock in async context can cause deadlocks under load |

**Fix — Offload to threadpool:**

```python
# security.py — wrap blocking calls
import asyncio

async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)

async def verify_password_async(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(verify_password, plain, hashed)
```

```python
# email.py — wrap Resend call
await asyncio.to_thread(resend.Emails.send, {...})
```

#### 🟡 P1 — Database Query Amplification

| Endpoint | Queries/Request | Issue |
|----------|----------------|-------|
| `/api/analytics/student/{id}/gap-chapters` | N+1 queries | Loop at [analytics.py] does `db.get(Chapter)` + `db.get(Class)` per row |
| `/api/analytics/my-children` | N × (5 queries) | Loop at [analytics.py] calls `get_student_performance()` per child |
| `check_ai_token_limit` dependency | 2 queries per call | Fetches `AISettings` + `SUM(tokens)` on every AI-guarded request |

**Fix:**

```python
# gap-chapters: batch-load chapters and classes with a JOIN
result = await db.execute(
    select(GapAnalysis.chapter_id, func.count(GapAnalysis.id),
           Chapter.name, Class.name)
    .outerjoin(Chapter, GapAnalysis.chapter_id == Chapter.id)
    .outerjoin(Class, Chapter.class_id == Class.id)
    .where(...)
    .group_by(GapAnalysis.chapter_id, Chapter.name, Class.name)
)
```

#### 🟡 P2 — In-Memory State Not Cluster-Safe

| Component | File | Issue |
|-----------|------|-------|
| WebSocket `ConnectionManager` | [websocket.py] | In-process `dict` of connections — lost on restart, can't scale horizontally |
| `_weak_areas_cache` | [analytics.py] | In-memory dict with 1hr TTL — not shared across workers/pods |
| `_cached_settings` / `_api_keys` | [ai.py] | Module-level globals — diverge between workers |
| Voice interview `transcript_lines` | [voice_interview.py] | Per-connection state (fine), but no persistence if connection drops |

#### 🟡 P3 — Missing Database Indexes

The current models are missing indexes on frequently queried columns:

```python
# These columns are filtered/joined heavily but lack explicit indexes:
# - TestResult.student_id (used in leaderboard, analytics)
# - TestResult.test_id
# - Attendance.student_id + date
# - GapAnalysis.student_id + status
# - HomeworkSubmission.student_id
# - ClassStudent.section_id + student_id
```

#### 🟢 P4 — Potential Memory Leaks

- `_InMemoryLimiter._store` in [rate_limit.py] grows unbounded. The `cleanup()` method exists but is **never called** — no periodic task invokes it.
- `_weak_areas_cache` in [analytics.py] grows without eviction limit. 1000 section×chapter combinations = unbounded memory.

---

## 3. Scalability Strategy

### 3.1 Phase 1 — Vertical Scaling (0–1,000 users)

Target: **Single VM, optimized configuration**

```
┌─────────────────────────────────────┐
│            NGINX (reverse proxy)    │
│    SSL termination, static files    │
│    WebSocket upgrade, rate limit    │
├─────────────────────────────────────┤
│     Gunicorn (4 Uvicorn workers)    │
│     FastAPI app × 4 processes       │
├──────────┬──────────────────────────┤
│ PostgreSQL│        Redis            │
│ (same VM) │     (same VM)           │
└──────────┴──────────────────────────┘
```

**Actions:**

1. Add Gunicorn with 4 Uvicorn workers (see Section 4)
2. Add NGINX reverse proxy for SSL, static files, and connection buffering
3. Fix all blocking sync calls (Section 2.1)
4. Add missing database indexes (Section 5)
5. Move `_weak_areas_cache` to Redis

### 3.2 Phase 2 — Horizontal Scaling (1,000–5,000 users)

Target: **Separate DB, load balancer, stateless app**

```
              ┌──── ALB / NGINX LB ────┐
              │                         │
        ┌─────┴─────┐           ┌──────┴────┐
        │  App Pod 1 │           │ App Pod 2  │
        │  (4 workers)│          │ (4 workers) │
        └─────┬─────┘           └──────┬────┘
              │                         │
     ┌────────┴─────────────────────────┴────────┐
     │                                            │
┌────┴────┐  ┌──────────┐  ┌──────────────────┐  │
│ PG Primary│ │ PG Replica│ │  Redis (Cluster)  │  │
│  (writes) │ │  (reads)  │ │  sessions+cache   │  │
└──────────┘ └──────────┘  └──────────────────┘  │
                                                  │
                           ┌──────────────────┐   │
                           │  Celery Worker(s) │───┘
                           │  (AI, email, OCR) │
                           └──────────────────┘
```

**Actions:**

1. Make app fully stateless — move ALL in-memory state to Redis
2. Replace in-process `ConnectionManager` with Redis Pub/Sub for WebSocket fan-out
3. Split read-heavy analytics queries to read replica
4. Add Celery for background AI evaluation and email
5. Deploy behind AWS ALB or managed load balancer

### 3.3 Phase 3 — Full Scale (5,000+ users)

Target: **Kubernetes, auto-scaling, managed services**

- **Kubernetes**: HPA based on CPU/memory + custom metrics (request latency)
- **Managed PostgreSQL**: AWS RDS / Azure Flexible Server with auto-failover
- **Managed Redis**: AWS ElastiCache / Azure Cache for Redis
- **CDN**: CloudFront/Cloudflare for static files and upload delivery
- **Object Storage**: S3/Azure Blob for uploads (replace local `uploads/` volume)

### 3.4 Stateless Architecture Checklist

| State | Current Location | Target |
|-------|-----------------|--------|
| User sessions | JWT (already stateless) | ✅ No change needed |
| WebSocket connections | In-process dict | Redis Pub/Sub + sticky sessions |
| AI settings cache | Module-level global | Redis hash with TTL |
| Weak areas cache | Module-level global | Redis with TTL |
| Rate limiter fallback | In-memory dict | Redis only (remove fallback) |
| File uploads | Local `uploads/` dir | S3/Azure Blob + signed URLs |

---

## 4. FastAPI Optimization

### 4.1 Gunicorn + Uvicorn Configuration

Current [Dockerfile CMD]:

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
# ❌ Single worker, no process management
```

**Production configuration:**

```dockerfile
# Dockerfile — replace CMD
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:4000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

Add `gunicorn` to [requirements.txt]:

```
gunicorn==22.0.0
```

**Worker count formula:**

```python
# CPU-bound: 2 × CPU cores + 1
# I/O-bound (your case): 4 × CPU cores + 1
# For a 2-core VM: 4 workers. For 4-core: 9 workers.
```

### 4.2 Async/Await Best Practices

**Current violations found:**

```python
# ❌ WRONG — sync bcrypt blocks event loop (security.py)
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

# ✅ FIX — offload to threadpool
async def hash_password(password: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_hash, password)
```

```python
# ❌ WRONG — sync Resend HTTP call (email.py:80)
resend.Emails.send({...})

# ✅ FIX — offload or use async HTTP client
await asyncio.to_thread(resend.Emails.send, {...})
# OR better: use httpx async client directly
```

### 4.3 Connection Pooling

Current pool config in [database.py]:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=50,      # ← Too high for single worker
    max_overflow=20,   # ← 70 total per worker
    pool_pre_ping=True,
)
```

**Issue**: With 4 Gunicorn workers, this creates 4 × 70 = **280 connections** — likely exceeds PostgreSQL's `max_connections` (default 100).

**Fix:**

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,          # 10 per worker × 4 workers = 40
    max_overflow=5,        # 15 per worker × 4 workers = 60 max
    pool_pre_ping=True,
    pool_recycle=1800,     # Recycle stale connections every 30 min
    pool_timeout=30,       # Error if no conn available in 30s
)
```

And set PostgreSQL `max_connections = 100` minimum (or use PgBouncer for connection multiplexing).

---

## 5. Database Optimization

### 5.1 Missing Indexes (Critical)

Create an Alembic migration with these indexes:

```python
# alembic/versions/xxx_add_performance_indexes.py
from alembic import op

def upgrade():
    # Most-queried columns identified from API routes
    op.create_index('ix_test_results_student_id', 'test_results', ['student_id'])
    op.create_index('ix_test_results_test_id', 'test_results', ['test_id'])
    op.create_index('ix_attendance_student_date', 'attendance', ['student_id', 'date'])
    op.create_index('ix_attendance_section_date', 'attendance', ['section_id', 'date'])
    op.create_index('ix_gap_analysis_student_status', 'gap_analysis', ['student_id', 'status'])
    op.create_index('ix_gap_analysis_chapter_id', 'gap_analysis', ['chapter_id'])
    op.create_index('ix_homework_submissions_student', 'homework_submissions', ['student_id'])
    op.create_index('ix_class_students_section', 'class_students', ['section_id'])
    op.create_index('ix_class_students_student', 'class_students', ['student_id'])
    op.create_index('ix_tests_section_id', 'tests', ['section_id'])
    op.create_index('ix_topics_section_subject', 'topics', ['section_id', 'subject_id'])
    op.create_index('ix_otp_codes_email_used', 'otp_codes', ['email', 'used'])
    op.create_index('ix_ai_token_usage_user_date', 'ai_token_usage', ['user_id', 'date'])
```

**Estimated impact**: 3–10x faster on analytics endpoints (leaderboard, class insights, gap chapters).

### 5.2 Query Optimization

**N+1 in student_gap_chapters ([analytics.py:762-778]):**

```python
# ❌ Current: N+1 loop
for chapter_id, count in result.all():
    ch = await db.get(Chapter, chapter_id)         # ← DB hit per row
    cls = await db.get(Class, ch.class_id)          # ← Another DB hit

# ✅ Fix: Single JOIN query
result = await db.execute(
    select(
        GapAnalysis.chapter_id,
        func.count(GapAnalysis.id),
        Chapter.name,
        Class.name,
    )
    .outerjoin(Chapter, GapAnalysis.chapter_id == Chapter.id)
    .outerjoin(Class, Chapter.class_id == Class.id)
    .where(GapAnalysis.student_id == student_id, GapAnalysis.status == "open")
    .group_by(GapAnalysis.chapter_id, Chapter.name, Class.name)
)
```

**Leaderboard query optimization** — already well-optimized with bulk queries and Redis cache in [analytics.py]. ✅ Good pattern.

### 5.3 Read Replicas

When PostgreSQL becomes the bottleneck (>500 concurrent users):

```python
# database.py — add read replica engine
read_engine = create_async_engine(
    settings.DATABASE_READ_URL,   # Points to replica
    pool_size=15,
    max_overflow=5,
    pool_pre_ping=True,
)

read_session = async_sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False)

async def get_read_db():
    """Read-only DB session for analytics/reporting."""
    async with read_session() as session:
        yield session
```

Route read-heavy endpoints to the replica:

```python
@router.get("/api/analytics/leaderboard")
async def get_leaderboard(db: AsyncSession = Depends(get_read_db)):  # ← read replica
    ...
```

### 5.4 PgBouncer (Connection Multiplexer)

When running multiple workers/pods, add PgBouncer between app and PostgreSQL:

```ini
# pgbouncer.ini
[databases]
entorhino = host=pg-primary port=5432 dbname=entorhino

[pgbouncer]
pool_mode = transaction      # Best for async apps
max_client_conn = 400
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
```

---

## 6. Caching Strategy

### 6.1 Current Redis Usage

| Feature | Key Pattern | TTL | Status |
|---------|------------|-----|--------|
| Rate limiting | `rl:{key}` | Dynamic (window) | ✅ Working |
| Leaderboard | `leaderboard:v1` | 300s (5 min) | ✅ Working |
| Weak areas cache | In-memory dict | 3600s (1hr) | ⚠️ Not in Redis |
| AI settings cache | Module-level dict | No TTL | ⚠️ Not in Redis |
| User session | JWT (no server state) | Token expiry | ✅ Stateless |

### 6.2 Recommended Redis Cache Additions

```python
# 1. AI Settings — cache in Redis for cross-worker consistency
async def reload_cached_settings(db: AsyncSession):
    # ... existing DB query ...
    r = get_redis()
    if r:
        await r.hset("ai:settings", mapping=_cached_settings)
        await r.expire("ai:settings", 600)  # 10 min TTL

# 2. Student performance — cache hot queries
cache_key = f"student:perf:{student_id}"
cached = await r.get(cache_key)
if cached:
    return json.loads(cached)
# ... compute ... 
await r.set(cache_key, json.dumps(result), ex=180)  # 3 min

# 3. Current user lookup — avoid DB hit on EVERY request
cache_key = f"user:{user_id}"
cached = await r.hgetall(cache_key)
if cached:
    return User(**cached)  # Reconstruct from cache
# ... DB query ...
await r.hset(cache_key, mapping={...})
await r.expire(cache_key, 300)  # 5 min
```

### 6.3 Cache Invalidation Strategy

```
User updated    → DELETE user:{id}
Test submitted  → DELETE student:perf:{student_id}, leaderboard:v1
Settings saved  → DELETE ai:settings (already calls reload_cached_settings)
Gap created     → DELETE student:gaps:{student_id}
```

### 6.4 CDN Caching

For the static files currently served by FastAPI:

```nginx
# NGINX config — cache static assets at CDN/proxy level
location /static/ {
    alias /app/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
    add_header X-Content-Type-Options nosniff;
}

location /uploads/ {
    alias /app/uploads/;
    expires 7d;
    add_header Cache-Control "public";
}
```

**Better**: Move uploads to S3/Azure Blob with CloudFront/Cloudflare CDN for global delivery and no local disk dependency.

---

## 7. Queue & Background Jobs

### 7.1 Current State — No Background Processing

All heavy operations run **inline during the HTTP request**:

| Operation | File | Duration | Should Be Background? |
|-----------|------|----------|----------------------|
| AI question generation | [ai.py] | 2–5s | ✅ Yes |
| AI answer evaluation | [ai.py] | 2–5s | ✅ Yes |
| Homework AI check | [ai.py] | 3–8s | ✅ Yes |
| Gap analysis | [ai.py] | 2–5s | ✅ Yes |
| OTP email send | [email.py] | 200ms–1s | ✅ Yes |
| OCR processing | [ocr.py] | 1–5s | ✅ Yes |

### 7.2 Recommended Architecture — Celery + Redis

```
requirements.txt:
+ celery[redis]==5.4.0
```

```python
# app/worker.py — Celery app
from celery import Celery

celery_app = Celery(
    "entorhino",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_soft_time_limit=120,
    task_time_limit=180,
    worker_max_tasks_per_child=500,  # Prevent memory leaks
    worker_prefetch_multiplier=2,
)
```

```python
# app/tasks/ai_tasks.py
from app.worker import celery_app

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def evaluate_homework_task(self, submission_id: str, homework_desc: str, extracted_text: str):
    """Background: AI homework evaluation."""
    # Run async code in sync celery task
    import asyncio
    result = asyncio.run(_async_evaluate(submission_id, homework_desc, extracted_text))
    return result

@celery_app.task
def send_email_task(email: str, subject: str, body: str):
    """Background: Send email via Resend."""
    resend.Emails.send({"from": ..., "to": [email], "subject": subject, "html": body})
```

**API endpoint change pattern:**

```python
# Before (blocking):
ai_result = await check_homework(db, user_id, description, text)

# After (async via queue):
task = evaluate_homework_task.delay(str(submission.id), description, text)
return {"status": "processing", "task_id": task.id}

# Client polls GET /api/homework/status/{task_id} or gets WebSocket push
```

### 7.3 Alternative: FastAPI BackgroundTasks (Quick Win)

For simpler cases (emails), use FastAPI's built-in background tasks:

```python
from fastapi import BackgroundTasks

@router.post("/register")
async def register(req: RegisterRequest, background_tasks: BackgroundTasks, ...):
    # ... create user ...
    background_tasks.add_task(send_otp_email_sync, db, req.email, OTPPurpose.EMAIL_VERIFY)
    return {"message": "Registration successful..."}
```

> [!WARNING]
> `BackgroundTasks` runs in the same process — it doesn't survive restarts and doesn't scale. Use Celery for anything critical (AI evaluation, analytics).

---

## 8. Security Enhancements

### 8.1 Current Security Posture

| Feature | Status | File |
|---------|--------|------|
| JWT auth (access + refresh) | ✅ Implemented | [security.py] |
| Role-based access control | ✅ 5 roles with guards | [dependencies.py] |
| Redis-backed rate limiting | ✅ With fallback | [rate_limit.py] |
| Password hashing (bcrypt) | ✅ | [security.py] |
| Input validation (Pydantic) | ✅ | Schemas directory |
| CORS | ⚠️ **`allow_origins=["*"]`** | [main.py] |
| HTTPS | ❌ Not configured | No SSL in Docker/NGINX |
| Helmet-style headers | ❌ Missing | No security headers middleware |
| CSRF protection | ❌ N/A (API-only JWT) | Acceptable for SPA+API |
| WAF | ❌ Not configured | No cloud WAF |

### 8.2 Critical Fixes

**1. Lock down CORS** ([main.py]):

```python
# ❌ Current — allows ANY origin
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# ✅ Fix — restrict to known origins
ALLOWED_ORIGINS = [
    "https://entorhino.co",
    "https://www.entorhino.co",
    "https://app.entorhino.co",
]
if settings.ENVIRONMENT == "development":
    ALLOWED_ORIGINS.append("http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**2. Add security headers middleware:**

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

**3. Secrets exposure** — [`.env.example`] contains a real-looking admin password. Ensure `.env` is in `.gitignore` (it is ✅), but also:

- Rotate the VAPID keys in [config.py] — these are hardcoded defaults
- Use `secrets.token_urlsafe(32)` for JWT keys in production

**4. API key storage** — API keys are stored in **plaintext** in the `api_keys` table ([user.py]). Encrypt at rest using Fernet or a KMS.

**5. WebSocket auth** — JWT token passed via query param (`?token=`) in [websocket.py] and [voice_interview.py] is visible in server logs and browser history. Consider:

- Short-lived tokens (60s) specifically for WebSocket upgrade
- Or pass token in first WebSocket message after connect

---

## 9. Monitoring & Logging

### 9.1 Current State — No Monitoring

- Logging: Basic Python `logging` with `logger.info/warning` — no structured format
- No APM (Application Performance Monitoring)
- No error tracking (no Sentry)
- Health check exists: `/api/health` in [main.py] — but only returns `{"status": "healthy"}`, doesn't check DB or Redis

### 9.2 Enhanced Health Check

```python
@app.get("/api/health")
async def health_check():
    checks = {"app": "healthy", "version": "1.0.0"}
    
    # DB check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:100]}"
    
    # Redis check
    r = get_redis()
    if r:
        try:
            await r.ping()
            checks["redis"] = "healthy"
        except Exception:
            checks["redis"] = "unhealthy"
    else:
        checks["redis"] = "unavailable"
    
    status = "healthy" if all(v == "healthy" for v in checks.values() if v != "unavailable") else "degraded"
    return {"status": status, **checks}
```

### 9.3 Recommended Monitoring Stack

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: changeme
```

**Add Prometheus metrics to FastAPI:**

```
# requirements.txt
+ prometheus-fastapi-instrumentator==7.0.0
+ sentry-sdk[fastapi]==2.0.0
```

```python
# main.py
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator(
    should_group_status_codes=True,
    excluded_handlers=["/api/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics")
```

**Sentry integration:**

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    traces_sample_rate=0.1,  # 10% of requests traced
    profiles_sample_rate=0.05,
    environment=settings.ENVIRONMENT,
)
```

### 9.4 Structured Logging

```python
import logging
import json
import sys

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        })

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)
```

### 9.5 Key Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Request latency (p95) | Prometheus | > 2s |
| Error rate (5xx) | Prometheus | > 1% |
| DB connection pool usage | SQLAlchemy events | > 80% |
| Redis memory usage | Redis INFO | > 80% of maxmemory |
| AI API errors | Custom counter | > 5/min |
| Active WebSocket connections | Custom gauge | > 500 |
| Background task queue depth | Celery/Redis | > 100 pending |

---

## 10. CI/CD Pipeline

### 10.1 Current Pipeline

The current [deploy.yml] does:

1. ✅ Build Docker image with multi-stage build
2. ✅ Push to GHCR with versioned tags
3. ✅ SSH deploy to VM with `docker run`
4. ❌ **No tests** — no test step at all
5. ❌ **No linting** — no code quality checks
6. ❌ **Zero-downtime deployment** — `docker stop` → `docker rm` → `docker run` = **downtime**
7. ❌ **No health check** — no verification that the new container is healthy
8. ❌ **No rollback** — if new version fails, manual intervention required

### 10.2 Enhanced CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml — enhanced
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ── Stage 1: Lint & Type Check ──
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff mypy
      - run: ruff check app/
      - run: ruff format --check app/

  # ── Stage 2: Tests ──
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: entorhino_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt pytest pytest-asyncio httpx
      - run: pytest tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/entorhino_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test-secret
          JWT_REFRESH_SECRET_KEY: test-refresh-secret

  # ── Stage 3: Build & Push (only on main) ──
  build:
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    # ... existing build step ...

  # ── Stage 4: Deploy with zero-downtime ──
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy with health check
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.VM_HOST }}
          username: ${{ secrets.VM_USERNAME }}
          key: ${{ secrets.VM_SSH_KEY }}
          script: |
            set -euo pipefail
            
            # Pull new image
            docker pull $IMAGE:latest
            
            # Start new container alongside old one
            docker run -d --name ent-mvp-new \
              -p 6001:4000 \
              ... (same env vars) ...
              $IMAGE:latest
            
            # Wait for health check
            for i in $(seq 1 30); do
              if curl -sf http://localhost:6001/api/health | grep -q healthy; then
                echo "New container is healthy!"
                break
              fi
              if [ $i -eq 30 ]; then
                echo "Health check failed — rolling back"
                docker stop ent-mvp-new && docker rm ent-mvp-new
                exit 1
              fi
              sleep 2
            done
            
            # Swap traffic
            docker stop ent-mvp || true
            docker rm ent-mvp || true
            docker rename ent-mvp-new ent-mvp
            # Update port mapping via nginx reload
            
            docker image prune -f
```

---

## 11. Infrastructure Setup

### 11.1 Docker Improvements

Current [Dockerfile] is already good ✅:

- Multi-stage build
- Non-root user (`appuser`)
- Minimal runtime image (`slim-bookworm`)
- Proper COPY ordering for cache efficiency

**Improvements needed:**

```dockerfile
# Add health check to Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4000/api/health')"]

# Use Gunicorn in CMD (as specified in Section 4)
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:4000", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]
```

### 11.2 Docker Compose (Full Local Stack)

```yaml
# docker-compose.yml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "4000:4000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - uploads:/app/uploads

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: entorhino
      POSTGRES_USER: entorhino
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U entorhino"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app

  # Optional: Celery worker
  celery-worker:
    build: .
    command: celery -A app.worker worker --loglevel=info --concurrency=4
    env_file: .env
    depends_on:
      - redis
      - postgres

volumes:
  pgdata:
  redisdata:
  uploads:
```

### 11.3 NGINX Configuration

```nginx
# nginx.conf
upstream fastapi {
    server app:4000;
}

server {
    listen 80;
    server_name entorhino.co www.entorhino.co;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name entorhino.co;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    client_max_body_size 10m;

    # Static files — served directly by NGINX
    location /static/ {
        alias /app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket upgrade
    location /ws/ {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # API and all other routes
    location / {
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for AI endpoints
        proxy_read_timeout 120s;
    }
}
```

### 11.4 Kubernetes (Phase 3)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: entorhino-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: entorhino-api
  template:
    spec:
      containers:
        - name: api
          image: ghcr.io/entorhino-org/ent_mvp:latest
          ports:
            - containerPort: 4000
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          readinessProbe:
            httpGet:
              path: /api/health
              port: 4000
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /api/health
              port: 4000
            initialDelaySeconds: 30
            periodSeconds: 30
          envFrom:
            - secretRef:
                name: entorhino-secrets

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: entorhino-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: entorhino-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 12. Production Checklist

### Pre-Launch (Must-Have)

- [ ] **Fix blocking calls**: Offload bcrypt and Resend to threadpool (Section 2.1)
- [ ] **Lock CORS origins**: Replace `allow_origins=["*"]` with explicit domains (Section 8.2)
- [ ] **Add Gunicorn**: Switch from single Uvicorn to Gunicorn + 4 workers (Section 4.1)
- [ ] **Add NGINX**: SSL termination, static file serving, WebSocket proxy (Section 11.3)
- [ ] **Add DB indexes**: Create Alembic migration for 12 critical indexes (Section 5.1)
- [ ] **Fix pool size**: Reduce to 10 per worker to avoid PG connection exhaustion (Section 4.3)
- [ ] **Enhance health check**: Check DB + Redis connectivity (Section 9.2)
- [ ] **Add security headers**: X-Frame-Options, HSTS, CSP (Section 8.2)
- [ ] **Rotate hardcoded secrets**: VAPID keys, JWT secrets for production
- [ ] **Add Sentry**: Error tracking with FastAPI + SQLAlchemy integrations (Section 9.3)
- [ ] **Add structured logging**: JSON format for log aggregation (Section 9.4)
- [ ] **Create `tests/` directory**: At minimum, auth + CRUD integration tests
- [ ] **Add linting to CI**: ruff check + format (Section 10.2)

### Post-Launch (Should-Have)

- [ ] **Background jobs**: Move AI evaluation and email to Celery (Section 7)
- [ ] **Redis cache expansion**: Student performance, AI settings (Section 6.2)
- [ ] **Fix N+1 queries**: gap_chapters, my_children endpoints (Section 5.2)
- [ ] **In-memory rate limiter cleanup**: Add periodic `cleanup()` call or remove fallback
- [ ] **WebSocket to Redis Pub/Sub**: For multi-worker/pod support
- [ ] **Prometheus + Grafana**: Request metrics, DB pool, AI errors (Section 9.3)
- [ ] **Zero-downtime deploy**: Blue-green or rolling update (Section 10.2)
- [ ] **Upload migration**: Local disk → S3/Azure Blob with signed URLs
- [ ] **API key encryption**: Encrypt at rest in `api_keys` table
- [ ] **PgBouncer**: Connection pooling for multi-pod deployments

### Scale Phase (Nice-to-Have)

- [ ] **Read replicas**: Route analytics queries to replica
- [ ] **CDN**: CloudFront/Cloudflare for static + uploads
- [ ] **Kubernetes**: Auto-scaling with HPA
- [ ] **Managed services**: RDS/Cloud SQL, ElastiCache/Redis Cluster

---

## 13. Estimated Scalability Tiers

### Small Setup — Current Deployment
>
> 1 VM (2 CPU, 4GB RAM), single Uvicorn worker, co-located PG + Redis

| Metric | Value |
|--------|-------|
| **Concurrent users** | 50–150 |
| **Requests/sec** | ~200–400 |
| **AI concurrent calls** | ~10 (limited by single event loop + blocking) |
| **WebSocket connections** | ~100 |
| **Monthly cost** | ~$20–40 (single VM) |
| **Risk** | Single point of failure. Blocking calls cause cascade slowdowns. |

### Optimized Setup — Phase 1 Fixes Applied
>
> 1 VM (4 CPU, 8GB RAM), Gunicorn 4 workers, NGINX, fixes from Section 2

| Metric | Value |
|--------|-------|
| **Concurrent users** | 500–1,500 |
| **Requests/sec** | ~1,000–3,000 |
| **AI concurrent calls** | ~50 (semaphore limit, non-blocking) |
| **WebSocket connections** | ~500 |
| **Monthly cost** | ~$60–100 (beefier VM) |
| **What changed** | Blocking calls fixed, DB indexed, Gunicorn multi-worker, NGINX proxy, Sentry |

### Scaled Infrastructure — Phase 2 + Phase 3
>
> 2–4 app pods, managed PG with replica, Redis cluster, Celery workers, ALB, CDN

| Metric | Value |
|--------|-------|
| **Concurrent users** | 5,000–15,000+ |
| **Requests/sec** | ~8,000–15,000 |
| **AI concurrent calls** | ~200 (across 4 pods, distributed via Celery) |
| **WebSocket connections** | ~5,000 (Redis Pub/Sub fan-out) |
| **Monthly cost** | ~$300–800 (managed services + compute) |
| **What changed** | Stateless app, Celery workers, Redis Pub/Sub, read replica, CDN, K8s HPA |

---

> [!IMPORTANT]
> **Highest-ROI actions** (do these first for maximum impact with minimum effort):
>
> 1. Add Gunicorn with 4 workers (~10 min change, 4× throughput)
> 2. Fix blocking bcrypt/email calls (~30 min, eliminates cascade slowdowns)
> 3. Add database indexes via Alembic migration (~20 min, 3–10× faster analytics)
> 4. Lock CORS + add security headers (~15 min, closes critical security gap)
> 5. Add Sentry (~10 min, immediate visibility into production errors)
