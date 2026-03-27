"""
AI service — OpenRouter client wrapper with token tracking.
"""

import json
import threading
from datetime import date
from typing import Optional
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.user import AITokenUsage, AISettings

settings = get_settings()

# OpenRouter client using OpenAI SDK with base_url swap
client = AsyncOpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
    default_headers={
        "HTTP-Referer": "https://entorhino.co",
        "X-Title": "Entorhino",
    },
)


# ── In-memory settings cache ─────────────────────────────────
# Loaded once on first AI call, refreshed only when admin saves.
_cached_settings: dict = {}
_cache_loaded: bool = False

# ── Multi-key round-robin state ──────────────────────────────
_api_keys: dict = {"openrouter": [], "openai": [], "sarvam": [], "gemini": []}  # provider -> list of {id, key}
_rr_counters: dict = {"openrouter": 0, "openai": 0, "sarvam": 0, "gemini": 0}
_rr_lock = threading.Lock()


def get_next_api_key(provider: str) -> str:
    """Get next API key using round-robin. Default key is NOT in rotation."""
    keys = _api_keys.get(provider, [])
    if not keys:
        # No round-robin keys — use default as fallback
        return _get_fallback_key(provider)
    with _rr_lock:
        idx = _rr_counters.get(provider, 0) % len(keys)
        _rr_counters[provider] = idx + 1
    return keys[idx]["key"]


def _get_fallback_key(provider: str) -> str:
    """Get the default (fallback) key for a provider."""
    if provider == "sarvam":
        return _cached_settings.get("sarvam_api_key", "")
    if provider == "gemini":
        return _cached_settings.get("gemini_api_key", "")
    return _cached_settings.get("openrouter_api_key", settings.OPENROUTER_API_KEY)


def get_fallback_api_key(provider: str) -> str:
    """Public: get fallback key when round-robin key fails."""
    return _get_fallback_key(provider)


async def record_api_key_error(api_key_value: str, error_msg: str):
    """Record an error for a specific API key in the DB."""
    try:
        from app.models.user import ApiKey
        async with _get_session() as db:
            result = await db.execute(select(ApiKey).where(ApiKey.api_key == api_key_value))
            key_obj = result.scalar_one_or_none()
            if key_obj:
                key_obj.error_count = (key_obj.error_count or 0) + 1
                key_obj.last_error = str(error_msg)[:500]
                await db.commit()
    except Exception:
        pass


def _get_session():
    """Get async DB session."""
    from app.database import async_session
    return async_session()


async def reload_cached_settings(db: AsyncSession):
    """Reload settings from DB into memory. Called on admin save."""
    global _cached_settings, _cache_loaded, _api_keys
    result = await db.execute(select(AISettings).limit(1))
    s = result.scalar_one_or_none()
    if s:
        _cached_settings = {
            "ai_model": s.ai_model or settings.OPENROUTER_MODEL,
            "ocr_model": s.ocr_model or settings.OPENROUTER_MODEL,
            "evaluation_model": s.evaluation_model or settings.OPENROUTER_MODEL,
            "openrouter_api_key": s.openrouter_api_key or settings.OPENROUTER_API_KEY,
            "gemini_api_key": getattr(s, 'gemini_api_key', '') or '',
            "gap_test_threshold": s.gap_test_threshold if s.gap_test_threshold is not None else 60,
            "gap_homework_threshold": s.gap_homework_threshold if s.gap_homework_threshold is not None else 50,
            "sarvam_api_key": getattr(s, 'sarvam_api_key', '') or '',
            "sarvam_stt_model": getattr(s, 'sarvam_stt_model', '') or 'saaras:v3',
            "otp_sender_email": getattr(s, 'otp_sender_email', '') or '',
            "otp_sender_password": getattr(s, 'otp_sender_password', '') or '',
            "smtp_host": getattr(s, 'smtp_host', '') or 'smtp.gmail.com',
            "smtp_port": getattr(s, 'smtp_port', 587),
            "school_name": getattr(s, 'school_name', '') or 'My School',
            "resend_api_key": getattr(s, 'resend_api_key', '') or '',
            "resend_from_email": getattr(s, 'resend_from_email', '') or '',
            "daily_student_token_limit": getattr(s, 'daily_student_token_limit', 5000),
            "daily_teacher_token_limit": getattr(s, 'daily_teacher_token_limit', 15000),
        }
    else:
        _cached_settings = {
            "ai_model": settings.OPENROUTER_MODEL,
            "ocr_model": settings.OPENROUTER_MODEL,
            "evaluation_model": settings.OPENROUTER_MODEL,
            "openrouter_api_key": settings.OPENROUTER_API_KEY,
            "gemini_api_key": "",
            "gap_test_threshold": 60,
            "gap_homework_threshold": 50,
            "sarvam_api_key": "",
            "sarvam_stt_model": "saaras:v3",
            "otp_sender_email": "",
            "otp_sender_password": "",
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "school_name": "My School",
            "resend_api_key": "",
            "resend_from_email": "",
            "daily_student_token_limit": 5000,
            "daily_teacher_token_limit": 15000,
        }
    _cache_loaded = True
    # Also update the client API key in place
    client.api_key = _cached_settings["openrouter_api_key"]

    # Load multi-keys from api_keys table
    try:
        from app.models.user import ApiKey
        result = await db.execute(select(ApiKey))
        all_keys = result.scalars().all()
        new_keys = {"openrouter": [], "openai": [], "sarvam": [], "gemini": []}
        for k in all_keys:
            if k.provider in new_keys:
                new_keys[k.provider].append({"id": str(k.id), "key": k.api_key})
        _api_keys = new_keys
    except Exception:
        pass  # Table may not exist yet


async def _ensure_cache(db: AsyncSession):
    """Lazy-load cache on first call."""
    global _cache_loaded
    if not _cache_loaded:
        await reload_cached_settings(db)


def get_cached_setting(key: str, default=None):
    """Get a cached setting value. For use by other modules (tests, homework)."""
    if not _cache_loaded:
        return default
    return _cached_settings.get(key, default)


async def _track_tokens(db: AsyncSession, user_id, tokens: int):
    """Record token usage for the user today."""
    today = date.today()
    result = await db.execute(
        select(AITokenUsage).where(
            AITokenUsage.user_id == user_id,
            AITokenUsage.date == today,
        )
    )
    usage = result.scalar_one_or_none()
    if usage:
        usage.tokens_used += tokens
    else:
        db.add(AITokenUsage(user_id=user_id, date=today, tokens_used=tokens))
    await db.flush()


async def ai_chat(
    db: AsyncSession,
    user_id,
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """Send a chat completion request to OpenRouter and track tokens."""
    await _ensure_cache(db)
    use_model = model or _cached_settings.get("ai_model", settings.OPENROUTER_MODEL)

    # Use round-robin key
    rr_key = get_next_api_key("openrouter")
    client.api_key = rr_key

    try:
        response = await client.chat.completions.create(
            model=use_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
    except Exception as e:
        # Record error for this key, retry with fallback
        await record_api_key_error(rr_key, str(e))
        fallback = get_fallback_api_key("openrouter")
        if fallback and fallback != rr_key:
            client.api_key = fallback
            response = await client.chat.completions.create(
                model=use_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=max_tokens,
            )
        else:
            raise

    content = response.choices[0].message.content or ""
    total_tokens = response.usage.total_tokens if response.usage else 0
    await _track_tokens(db, user_id, total_tokens)
    return content


async def ai_chat_json(
    db: AsyncSession,
    user_id,
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> dict:
    """Same as ai_chat but parses the response as JSON."""
    raw = await ai_chat(db, user_id, system_prompt + "\n\nRespond ONLY with valid JSON, no markdown.", user_message, model, max_tokens=max_tokens)
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse AI response", "raw": raw}


async def generate_questions(
    db: AsyncSession,
    user_id,
    topic_text: str,
    num_questions: int = 5,
) -> list[dict]:
    """Generate test questions from topic text using AI."""
    system_prompt = """You are an expert teacher creating questions for students.
Given a topic text, generate questions that test understanding.
Return a JSON array of objects with: question, expected_answer, marks (1-5), difficulty (easy/medium/hard).
Questions should range from recall to application level."""

    user_msg = f"Generate {num_questions} questions from this topic:\n\n{topic_text}"
    result = await ai_chat_json(db, user_id, system_prompt, user_msg)
    return result if isinstance(result, list) else result.get("questions", [result])


async def evaluate_answer(
    db: AsyncSession,
    user_id,
    question: str,
    expected_answer: str,
    student_answer: str,
) -> dict:
    """Evaluate a student's answer using AI."""
    system_prompt = """You are an expert teacher evaluating student answers.
Evaluate the student's answer against the expected answer.
Return JSON with: score (0-100), feedback (brief), understanding_level (weak/moderate/strong), confidence (low/medium/high)."""

    user_msg = f"""Question: {question}
Expected Answer: {expected_answer}
Student's Answer: {student_answer}"""

    return await ai_chat_json(db, user_id, system_prompt, user_msg)


async def check_homework(
    db: AsyncSession,
    user_id,
    homework_description: str,
    extracted_text: str,
) -> dict:
    """AI-check homework submission quality with detailed feedback."""
    system_prompt = """You are a kind and thorough teacher checking a student's homework.
Read the homework assignment and the student's submitted work carefully.

Evaluate:
1. Did the student complete the assignment correctly?
2. What parts are correct? What parts have errors?
3. For any wrong answers, explain what the correct answer should be and WHY.
4. Give specific suggestions for improvement.

Return JSON with:
- score: 0-100 (overall quality)
- feedback: detailed feedback (3-5 sentences) explaining what's right, what's wrong, correct answers, and suggestions
- completion_quality: "incomplete" or "partial" or "complete"
- accuracy: "poor" or "fair" or "good" or "excellent"
- encouragement: a warm, encouraging message for the student"""

    user_msg = f"""Homework Assignment: {homework_description}

Student's Submitted Work (extracted from image):
{extracted_text[:2000]}"""

    try:
        return await ai_chat_json(db, user_id, system_prompt, user_msg)
    except Exception as e:
        return {"score": None, "feedback": f"AI evaluation failed: {str(e)}",
                "completion_quality": "unknown", "accuracy": "unknown",
                "encouragement": "Your homework has been received!"}


async def analyze_class_performance(
    db: AsyncSession,
    user_id,
    performance_data: str,
) -> dict:
    """Analyze class-wide performance data to identify common weak areas."""
    system_prompt = """You are an educational data analyst.
Analyze the class performance data and identify patterns.
Return JSON with: weak_topics (list of topics most students struggle with), recommendations (list of teaching suggestions), overall_assessment (brief summary)."""

    return await ai_chat_json(db, user_id, system_prompt, performance_data)


async def analyze_gaps(
    db: AsyncSession,
    user_id,
    context: str,
    source_type: str,
) -> list[dict]:
    """AI analyzes test/homework results to detect concept gaps.
    Returns list of {concept, description, suggestion, severity} or empty list if no gaps."""
    system_prompt = """You are an expert educational analyst. Analyze the student's performance data below.
Identify SPECIFIC CONCEPTS or SKILLS where the student is struggling or has knowledge gaps.

Rules:
- ONLY report gaps where the student clearly shows misunderstanding or lack of knowledge.
- If the student scored above 60% overall, return an EMPTY list — no gaps needed.
- Each gap should be a distinct concept, not a repeat.
- severity: "critical" if student scored <30% on this concept, "moderate" if 30-50%, "minor" if 50-60%.

Return JSON with:
- gaps: array of objects, each with:
  - concept: short concept/skill name (2-5 words, e.g. "Adding Fractions", "Newton's Third Law")
  - description: 1-2 sentences about what the student got wrong or misunderstands
  - suggestion: 1-2 sentences on how the student can improve (specific practice, topics to review)
  - severity: "minor" or "moderate" or "critical"

If no significant gaps found, return: {"gaps": []}"""

    user_msg = f"Source: {source_type}\n\n{context[:3000]}"

    try:
        result = await ai_chat_json(db, user_id, system_prompt, user_msg)
        return result.get("gaps", [])
    except Exception:
        return []


# ── AI Test Conversation Functions ───────────────────────────

async def conduct_test_question(
    db: AsyncSession,
    user_id,
    topic_text: str,
    question_number: int,
    total_questions: int,
    previous_questions: list[str] = None,
) -> str:
    """AI reads topic notes and generates a test question for the student.
    Returns a single question string. Avoids repeating previous questions."""
    # Trim topic text to avoid exceeding token limits
    trimmed_topic = topic_text[:2000] if topic_text else "No topic provided"
    previous = "\n".join(f"- {q}" for q in (previous_questions or []))
    avoid_section = f"\n\nDo NOT repeat these questions already asked:\n{previous}" if previous else ""

    system_prompt = f"""You are a friendly, encouraging teacher conducting a casual verbal test with a student.
You are warm and conversational. First greet or chat briefly, then ask your question naturally.

Topic content you taught:
{trimmed_topic}

Ask question {question_number} of {total_questions}. Vary difficulty:
- Q1-2: Easy (basic facts, definitions)
- Q3-4: Medium (explain concepts, make connections)
- Q5+: Hard (apply knowledge, analyze)

Be conversational — like a real teacher talking to a student.
Return ONLY your spoken words (greeting + question), nothing else.{avoid_section}"""

    try:
        question = await ai_chat(db, user_id, system_prompt,
            f"Ask question {question_number} of {total_questions} in a friendly conversational way.",
            max_tokens=512)
        return question.strip()
    except Exception as e:
        return f"Question {question_number}: Can you explain what you learned about this topic in your own words?"


async def conduct_test_question_text(
    db: AsyncSession,
    user_id,
    topic_text: str,
    question_number: int,
    total_questions: int,
    previous_questions: list[str] = None,
) -> str:
    """Generate a direct test question without greetings — for text mode."""
    trimmed_topic = topic_text[:2000] if topic_text else "No topic provided"
    previous = "\n".join(f"- {q}" for q in (previous_questions or []))
    avoid_section = f"\n\nDo NOT repeat these questions already asked:\n{previous}" if previous else ""

    system_prompt = f"""You are a teacher giving a written test.
Ask questions directly without any greetings, small talk, or encouragement.
Just state the question clearly and concisely.

Topic content:
{trimmed_topic}

Ask question {question_number} of {total_questions}. Vary difficulty:
- Q1-2: Easy (basic facts, definitions)
- Q3-4: Medium (explain concepts, make connections)
- Q5+: Hard (apply knowledge, analyze)

Return ONLY the question — no greetings, no "here's your question", no numbering.
Just the question itself.{avoid_section}"""

    try:
        question = await ai_chat(db, user_id, system_prompt,
            f"Ask question {question_number} of {total_questions} directly.",
            max_tokens=256)
        return question.strip()
    except Exception as e:
        return f"Explain what you learned about this topic in your own words."


async def evaluate_test_answer(
    db: AsyncSession,
    user_id,
    topic_text: str,
    question: str,
    student_answer: str,
) -> dict:
    """AI evaluates a student's answer for a test question based on topic content."""
    trimmed_topic = topic_text[:2000] if topic_text else "No topic provided"

    system_prompt = f"""You are a friendly teacher evaluating a student's answer during a verbal test.

Reference material:
{trimmed_topic}

Evaluate the student's answer. Be encouraging but honest. If wrong, explain the correct answer briefly.

Return JSON with:
- score: 0-100
- feedback: constructive feedback explaining what was right/wrong and the correct answer (2-3 sentences)
- understanding: "weak" or "moderate" or "strong"
- encouragement: a warm encouraging message for the student"""

    user_msg = f"""Question: {question}
Student's Answer: {student_answer}"""

    try:
        return await ai_chat_json(db, user_id, system_prompt, user_msg)
    except Exception as e:
        return {"score": 50, "feedback": "Could not evaluate automatically. Your answer has been recorded.",
                "understanding": "moderate", "encouragement": "Keep trying! Every attempt is a step forward."}
