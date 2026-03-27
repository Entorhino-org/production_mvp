"""
Tests API — teacher creates test from topic, student takes test via AI conversation.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date, time

from app.database import get_db
from app.models.user import User, UserRole, GapAnalysis, AISettings, ParentStudentLink
from app.models.academic import Test, TestResult, Topic, TeacherAssignment, ClassStudent, Subject, Section, Chapter
from app.schemas.academic import TestCreate, SubmitTestRequest
from app.core.dependencies import get_current_user, check_ai_token_limit
from app.services.ai import conduct_test_question, conduct_test_question_text, evaluate_test_answer, analyze_gaps, get_cached_setting
from app.services.analytics import check_and_create_alerts
import threading
import time as _time

router = APIRouter(prefix="/api/tests", tags=["Tests"])

# ── Server-side answer store ─────────────────────────────────────
# Stores evaluated answers keyed by "user_id:test_id"
# This prevents students from modifying scores via browser dev tools.
_pending_answers: dict[str, dict] = {}  # key → {answers: [...], ts: float}
_pending_lock = threading.Lock()

def _store_answer(user_id: str, test_id: str, answer_data: dict):
    """Store an evaluated answer server-side."""
    key = f"{user_id}:{test_id}"
    with _pending_lock:
        if key not in _pending_answers:
            _pending_answers[key] = {"answers": [], "ts": _time.time()}
        _pending_answers[key]["answers"].append(answer_data)
        _pending_answers[key]["ts"] = _time.time()
        # Cleanup stale entries (older than 2 hours)
        cutoff = _time.time() - 7200
        stale = [k for k, v in _pending_answers.items() if v["ts"] < cutoff]
        for k in stale:
            del _pending_answers[k]

def _pop_answers(user_id: str, test_id: str) -> list:
    """Retrieve and remove stored answers for a test."""
    key = f"{user_id}:{test_id}"
    with _pending_lock:
        entry = _pending_answers.pop(key, None)
    return entry["answers"] if entry else []

def store_voice_answers(user_id: str, test_id: str, answers: list):
    """Store voice test answers server-side (called from voice_interview.py)."""
    key = f"{user_id}:{test_id}"
    with _pending_lock:
        _pending_answers[key] = {"answers": answers, "ts": _time.time()}



@router.post("/create", status_code=201)
async def create_test(
    req: TestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher creates a test by selecting a topic. No AI generation here."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can create tests")

    # Get topic
    result = await db.execute(select(Topic).where(Topic.id == req.topic_id))
    topic = result.scalar_one_or_none()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    if not topic.extracted_text:
        raise HTTPException(status_code=400, detail="Topic has no extracted text")

    # Parse due_date — defaults to midnight if only date provided
    due_date = None
    if req.due_date:
        try:
            # If just a date (YYYY-MM-DD), set to 23:59
            if len(req.due_date) == 10:
                d = date.fromisoformat(req.due_date)
                due_date = datetime.combine(d, time(23, 59, 0))
            else:
                due_date = datetime.fromisoformat(req.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid due_date format")

        # Block past due dates
        if due_date < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Due date cannot be in the past")

    test = Test(
        section_id=topic.section_id,
        subject_id=topic.subject_id,
        topic_id=topic.id,
        title=req.title,
        questions=[],  # No pre-generated questions — AI asks during test
        num_questions=req.num_questions,
        input_mode=req.input_mode,
        due_date=due_date,
    )
    db.add(test)
    await db.flush()

    # ── Alert students and parents about new test (bulk) ──
    try:
        from app.models.communication import Alert, AlertType
        enrolled = await db.execute(
            select(ClassStudent.student_id).where(ClassStudent.section_id == topic.section_id)
        )
        student_ids = [r[0] for r in enrolled.all()]

        if student_ids:
            # Bulk: parent links (1 query)
            parent_result = await db.execute(
                select(ParentStudentLink.student_id, ParentStudentLink.parent_id)
                .where(ParentStudentLink.student_id.in_(student_ids))
            )
            student_parents = {}
            for sid, pid in parent_result.all():
                student_parents.setdefault(sid, []).append(pid)

            # Bulk: student names (1 query)
            name_result = await db.execute(
                select(User.id, User.full_name).where(User.id.in_(student_ids))
            )
            student_names = {uid: name for uid, name in name_result.all()}

            due_str = due_date.strftime('%b %d, %Y %I:%M %p') if due_date else 'No deadline'
            push_targets = []

            for student_id in student_ids:
                student_name = student_names.get(student_id, "Your child")
                # Alert the student
                db.add(Alert(
                    student_id=student_id,
                    recipient_id=student_id,
                    alert_type=AlertType.NEW_TEST,
                    message=f"📝 New test assigned: {req.title}. Due: {due_str}.",
                ))
                push_targets.append((student_id, "📝 New Test", f"{req.title} — Due: {due_date.strftime('%b %d') if due_date else 'No deadline'}"))
                # Alert parents
                for parent_id in student_parents.get(student_id, []):
                    db.add(Alert(
                        student_id=student_id,
                        recipient_id=parent_id,
                        alert_type=AlertType.NEW_TEST,
                        message=f"📝 New test for {student_name}: {req.title}. Due: {due_str}.",
                    ))
                    push_targets.append((parent_id, "📝 New Test", f"{student_name}: {req.title}"))

            await db.flush()

            # Push notifications
            try:
                from app.api.push import send_push_to_user
                for rid, ptitle, pbody in push_targets:
                    await send_push_to_user(db, rid, ptitle, pbody, "/dashboard")
            except Exception:
                pass
    except Exception as e:
        print(f"[TEST] Alert creation failed: {e}")

    return {
        "id": str(test.id),
        "title": test.title,
        "num_questions": req.num_questions,
        "section_id": str(test.section_id),
        "subject_id": str(test.subject_id),
        "due_date": due_date.isoformat() if due_date else None,
        "message": f"Test created with {req.num_questions} questions. Students will be tested by AI.",
    }


@router.get("/")
async def list_tests(
    section_id: str = None,
    subject_id: str = None,
    class_id: str = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available tests, paginated."""
    from app.models.academic import Class
    query = (
        select(Test, Subject, Section, Class)
        .join(Subject, Test.subject_id == Subject.id)
        .join(Section, Test.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
    )

    if class_id:
        query = query.where(Section.class_id == class_id)
    if section_id:
        query = query.where(Test.section_id == section_id)
    if subject_id:
        query = query.where(Test.subject_id == subject_id)

    if current_user.role == UserRole.STUDENT:
        enrolled = await db.execute(
            select(ClassStudent.section_id).where(ClassStudent.student_id == current_user.id)
        )
        section_ids = [r[0] for r in enrolled.all()]
        if section_ids:
            query = query.where(Test.section_id.in_(section_ids))
        else:
            return []

    from sqlalchemy import case, literal
    now = datetime.utcnow()

    if current_user.role == UserRole.STUDENT:
        # Students: not-taken first (soonest deadline), then taken (most recent first)
        taken_sq = (
            select(TestResult.test_id)
            .where(TestResult.student_id == current_user.id, TestResult.test_id == Test.id)
            .correlate(Test)
            .exists()
        )
        taken_flag = case((taken_sq, literal(1)), else_=literal(0))
        query = query.order_by(taken_flag.asc(), Test.due_date.asc().nullslast()).offset(offset).limit(limit)
    elif current_user.role == UserRole.TEACHER:
        # Teachers: most recently created first
        query = query.order_by(Test.created_at.desc()).offset(offset).limit(limit)
    else:
        query = query.order_by(Test.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    all_rows = result.all()

    # Bulk check which tests the student has taken (1 query instead of N)
    taken_ids = set()
    if current_user.role == UserRole.STUDENT and all_rows:
        test_ids = [t.id for t, _, _, _ in all_rows]
        taken_result = await db.execute(
            select(TestResult.test_id).where(
                TestResult.student_id == current_user.id,
                TestResult.test_id.in_(test_ids),
            )
        )
        taken_ids = {str(r[0]) for r in taken_result.all()}

    tests = []
    for t, s, sec, cls in all_rows:
        is_overdue = t.due_date < now if t.due_date else False
        tests.append({
            "id": str(t.id),
            "title": t.title,
            "num_questions": getattr(t, 'num_questions', 5) or len(t.questions or []) or 5,
            "section_id": str(t.section_id),
            "subject_id": str(t.subject_id),
            "subject_name": s.name,
            "class_name": cls.name,
            "section_name": sec.name,
            "input_mode": getattr(t, 'input_mode', 'both') or 'both',
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "taken": str(t.id) in taken_ids,
            "is_overdue": is_overdue,
        })

    return tests


@router.get("/{test_id}")
async def get_test(
    test_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific test."""
    result = await db.execute(
        select(Test, Subject, Topic)
        .join(Subject, Test.subject_id == Subject.id)
        .join(Topic, Test.topic_id == Topic.id, isouter=True)
        .where(Test.id == test_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")
    t, s, topic = row
    return {
        "id": str(t.id),
        "title": t.title,
        "num_questions": getattr(t, 'num_questions', 5) or 5,
        "input_mode": getattr(t, 'input_mode', 'both') or 'both',
        "section_id": str(t.section_id),
        "subject_id": str(t.subject_id),
        "subject_name": s.name,
        "topic_text": topic.extracted_text if topic else "",
        "due_date": t.due_date.isoformat() if t.due_date else None,
    }


# ── AI Conversation Endpoints ────────────────────────────────

@router.post("/{test_id}/ask-question")
async def ask_ai_question(
    test_id: str,
    req: dict,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """AI generates a question for the student based on topic text.
    req: { question_number: int, previous_questions: [str] }
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can take tests")

    # Get test and topic
    result = await db.execute(
        select(Test, Topic)
        .join(Topic, Test.topic_id == Topic.id)
        .where(Test.id == test_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    test, topic = row
    if not topic.extracted_text:
        raise HTTPException(status_code=400, detail="No topic content for this test")

    # Block if deadline passed
    if test.due_date and test.due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot take test — deadline has passed")

    question_number = req.get("question_number", 1)
    previous_questions = req.get("previous_questions", [])
    mode = req.get("mode", "voice")  # "text" or "voice"
    total = getattr(test, 'num_questions', 5) or 5

    # Use direct questions for text mode, conversational for voice
    q_func = conduct_test_question_text if mode == "text" else conduct_test_question
    question = await q_func(
        db, current_user.id,
        topic_text=topic.extracted_text,
        question_number=question_number,
        total_questions=total,
        previous_questions=previous_questions,
    )

    return {
        "question": question,
        "question_number": question_number,
        "total_questions": total,
    }


@router.post("/{test_id}/evaluate-answer")
async def evaluate_student_answer(
    test_id: str,
    req: dict,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """AI evaluates student's answer for a test question.
    req: { question: str, answer: str }
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can take tests")

    # Get topic text for context
    result = await db.execute(
        select(Test, Topic)
        .join(Topic, Test.topic_id == Topic.id)
        .where(Test.id == test_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Test not found")

    test, topic = row

    eval_result = await evaluate_test_answer(
        db, current_user.id,
        topic_text=topic.extracted_text or "",
        question=req.get("question", ""),
        student_answer=req.get("answer", ""),
    )

    # Store this answer SERVER-SIDE so it can't be tampered with
    _store_answer(
        str(current_user.id), test_id,
        {
            "question": req.get("question", ""),
            "answer": req.get("answer", ""),
            "score": eval_result.get("score", 0),
            "feedback": eval_result.get("feedback", ""),
            "understanding": eval_result.get("understanding", "moderate"),
        }
    )

    return eval_result


@router.post("/{test_id}/complete")
async def complete_test(
    test_id: str,
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Student completes the AI-conversed test. Saves all Q&A and scores.
    req: { results: [{ question, answer, score, feedback, understanding }] }
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit tests")

    # Check if already submitted
    existing = await db.execute(
        select(TestResult).where(
            TestResult.test_id == test_id,
            TestResult.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already completed this test")

    # Block if deadline passed
    test_obj_check = await db.get(Test, test_id)
    if test_obj_check and test_obj_check.due_date and test_obj_check.due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot submit test — deadline has passed")

    # ── Use SERVER-STORED answers (not client data) ──
    mode = req.get("mode", "text")
    server_results = _pop_answers(str(current_user.id), test_id)
    
    if server_results:
        # Use the server-stored answers (scored server-side, tamper-proof)
        results = server_results
    else:
        # Fallback for voice tests that store answers directly
        # or edge cases — use client data but log a warning
        results = req.get("results", [])
        if results:
            import logging
            logging.getLogger(__name__).warning(
                f"Using client-submitted results for test {test_id} by user {current_user.id} — no server-stored answers found"
            )

    if not results:
        raise HTTPException(status_code=400, detail="No answers provided")

    # Calculate overall score
    scores = [r.get("score", 0) for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Analyze weak/strong areas
    weak = [r for r in results if r.get("score", 0) < 50]
    strong = [r for r in results if r.get("score", 0) >= 70]

    topic_analysis = {
        "weak_areas": [{"question": r.get("question", ""), "score": r.get("score", 0)} for r in weak],
        "strong_areas": [{"question": r.get("question", ""), "score": r.get("score", 0)} for r in strong],
        "overall_understanding": "weak" if avg_score < 40 else "moderate" if avg_score < 70 else "strong",
    }

    test_result = TestResult(
        test_id=test_id,
        student_id=current_user.id,
        answers=results,
        score=round(avg_score, 1),
        mode=req.get("mode", "text"),
        topic_analysis=topic_analysis,
    )
    db.add(test_result)
    await db.flush()

    # Trigger smart alerts
    await check_and_create_alerts(db, current_user.id)

    # Gap analysis — only for below-threshold scores
    gap_threshold = get_cached_setting("gap_test_threshold", 60)
    if avg_score < gap_threshold:
        try:
            test_obj = await db.get(Test, test_id)
            topic_obj = await db.get(Topic, test_obj.topic_id) if test_obj and test_obj.topic_id else None
            qa_summary = "\n".join([
                f"Q: {r.get('question','')} | A: {r.get('answer','')} | Score: {r.get('score',0)} | Feedback: {r.get('feedback','')}"
                for r in results
            ])
            context = f"Test: {test_obj.title if test_obj else 'Unknown'}\nOverall Score: {avg_score}%\n\nQuestions & Answers:\n{qa_summary}"
            gaps = await analyze_gaps(db, current_user.id, context, "test")
            for g in gaps:
                # Get chapter_id from topic if available
                ch_id = topic_obj.chapter_id if topic_obj and hasattr(topic_obj, 'chapter_id') else None
                gap = GapAnalysis(
                    student_id=current_user.id,
                    subject_id=test_obj.subject_id if test_obj else None,
                    topic_id=test_obj.topic_id if test_obj else None,
                    chapter_id=ch_id,
                    concept=g.get("concept", "Unknown"),
                    description=g.get("description", ""),
                    suggestion=g.get("suggestion", ""),
                    severity=g.get("severity", "moderate"),
                    source="test",
                    source_id=test_result.id,
                )
                db.add(gap)
            await db.flush()
        except Exception as e:
            print(f"[GAP ANALYSIS] Test gap detection failed: {e}")

    return {
        "id": str(test_result.id),
        "score": test_result.score,
        "answers": results,
        "topic_analysis": topic_analysis,
        "message": f"Test completed. Score: {test_result.score}%",
    }


@router.get("/{test_id}/results")
async def get_test_results(
    test_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get results summary for a test (paginated, no answers)."""
    from sqlalchemy import func as sql_func
    base = (
        select(TestResult, User)
        .join(User, TestResult.student_id == User.id)
        .where(TestResult.test_id == test_id)
    )

    if current_user.role == UserRole.STUDENT:
        base = base.where(TestResult.student_id == current_user.id)

    # Count
    count_q = select(sql_func.count()).select_from(
        select(TestResult.id).where(TestResult.test_id == test_id).subquery()
    )
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(base.order_by(TestResult.score.desc()).limit(limit).offset(offset))

    items = [
        {
            "id": str(tr.id),
            "test_id": str(tr.test_id),
            "student_id": str(tr.student_id),
            "student_name": u.full_name,
            "score": tr.score,
            "mode": tr.mode or "text",
            "taken_at": tr.taken_at.isoformat() if tr.taken_at else None,
        }
        for tr, u in result.all()
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{test_id}/results/{result_id}")
async def get_test_result_detail(
    test_id: str,
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full answers/details for a single test result."""
    result = await db.execute(
        select(TestResult, User)
        .join(User, TestResult.student_id == User.id)
        .where(TestResult.id == result_id, TestResult.test_id == test_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Result not found")
    tr, u = row

    # Students can only see their own
    if current_user.role == UserRole.STUDENT and str(tr.student_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "id": str(tr.id),
        "test_id": str(tr.test_id),
        "student_id": str(tr.student_id),
        "student_name": u.full_name,
        "score": tr.score,
        "mode": tr.mode or "text",
        "answers": tr.answers,
        "topic_analysis": tr.topic_analysis,
        "taken_at": tr.taken_at.isoformat() if tr.taken_at else None,
    }


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe audio to text using Sarvam AI STT."""
    import httpx
    from app.services.ai import get_cached_setting, _ensure_cache, get_next_api_key, get_fallback_api_key
    await _ensure_cache(db)

    # Get Sarvam API key from cache
    api_key = get_next_api_key("sarvam") or get_cached_setting("sarvam_api_key", "")
    if not api_key:
        api_key = get_fallback_api_key("sarvam")
    stt_model = get_cached_setting("sarvam_stt_model", "saaras:v3")

    contents = await audio.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Audio file too large (max 10MB)")

    # Determine file extension from content type
    ct = audio.content_type or "audio/webm"
    ext_map = {"audio/webm": "webm", "audio/wav": "wav", "audio/mpeg": "mp3", "audio/mp4": "mp4", "audio/ogg": "ogg"}
    ext = ext_map.get(ct, "webm")
    filename = f"audio.{ext}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": api_key},
            files={"file": (filename, contents, ct)},
            data={"model": stt_model, "language_code": "unknown"},
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="Transcription failed")

    data = resp.json()
    return {"text": data.get("transcript", "")}


@router.post("/tts")
async def text_to_speech(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convert text to speech using Sarvam AI TTS. Returns audio/wav."""
    import httpx
    import base64
    from fastapi.responses import Response
    from app.services.ai import get_cached_setting, _ensure_cache, get_next_api_key, get_fallback_api_key
    await _ensure_cache(db)

    text = req.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    api_key = get_next_api_key("sarvam") or get_cached_setting("sarvam_api_key", "")
    if not api_key:
        api_key = get_fallback_api_key("sarvam")
    tts_model = get_cached_setting("sarvam_tts_model", "bulbul:v3")
    tts_voice = req.get("voice", get_cached_setting("sarvam_tts_voice", "priya"))
    tts_lang = get_cached_setting("sarvam_tts_language", "en-IN")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "inputs": [text[:4096]],
                "target_language_code": tts_lang,
                "speaker": tts_voice,
                "model": tts_model,
            },
        )

    if resp.status_code != 200:
        import logging
        logging.error(f"TTS failed: status={resp.status_code} body={resp.text[:500]}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {resp.status_code}")

    data = resp.json()
    audios = data.get("audios", [])
    if not audios:
        raise HTTPException(status_code=500, detail="TTS returned no audio")

    audio_bytes = base64.b64decode(audios[0])
    return Response(content=audio_bytes, media_type="audio/wav")


@router.post("/check-deadlines")
async def check_test_deadlines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check all overdue tests and send TEST_MISSING alerts to parents
    of students who haven't taken them. Uses bulk queries to avoid N+1."""
    from app.models.communication import Alert, AlertType
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins")

    now = datetime.utcnow()

    # 1. Get overdue tests (1 query)
    result = await db.execute(
        select(Test).where(Test.due_date < now).order_by(Test.due_date.desc()).limit(50)
    )
    overdue_tests = result.scalars().all()
    if not overdue_tests:
        return {"message": "0 test-missing alerts sent to parents"}

    test_ids = [t.id for t in overdue_tests]
    section_ids = list({t.section_id for t in overdue_tests})

    # 2. Bulk: all enrolled students per section (1 query)
    enrolled_result = await db.execute(
        select(ClassStudent.section_id, ClassStudent.student_id)
        .where(ClassStudent.section_id.in_(section_ids))
    )
    section_students = {}
    for sec_id, stu_id in enrolled_result.all():
        section_students.setdefault(sec_id, set()).add(stu_id)

    # 3. Bulk: all test-takers (1 query)
    taken_result = await db.execute(
        select(TestResult.test_id, TestResult.student_id)
        .where(TestResult.test_id.in_(test_ids))
    )
    test_taken = {}
    for tid, sid in taken_result.all():
        test_taken.setdefault(tid, set()).add(sid)

    # 4. Collect all missing students, then bulk-fetch parents
    all_missing_students = set()
    test_missing_map = {}
    for test in overdue_tests:
        enrolled = section_students.get(test.section_id, set())
        taken = test_taken.get(test.id, set())
        missing = enrolled - taken
        test_missing_map[test.id] = missing
        all_missing_students.update(missing)

    if not all_missing_students:
        return {"message": "0 test-missing alerts sent to parents"}

    # 5. Bulk: all parent links for missing students (1 query)
    parent_result = await db.execute(
        select(ParentStudentLink.student_id, ParentStudentLink.parent_id)
        .where(ParentStudentLink.student_id.in_(list(all_missing_students)))
    )
    student_parents = {}
    for sid, pid in parent_result.all():
        student_parents.setdefault(sid, []).append(pid)

    # 6. Bulk: existing alerts to avoid duplicates (1 query)
    existing_alerts = await db.execute(
        select(Alert.student_id, Alert.recipient_id, Alert.message)
        .where(
            Alert.alert_type == AlertType.TEST_MISSING,
            Alert.student_id.in_(list(all_missing_students)),
        )
    )
    existing_set = set()
    for sid, rid, msg in existing_alerts.all():
        existing_set.add((sid, rid, msg))

    # 7. Bulk: student names (1 query)
    name_result = await db.execute(
        select(User.id, User.full_name).where(User.id.in_(list(all_missing_students)))
    )
    student_names = {uid: name for uid, name in name_result.all()}

    # Create alerts in memory
    alerts_sent = 0
    push_targets = []
    for test in overdue_tests:
        missing = test_missing_map.get(test.id, set())
        due_str = test.due_date.strftime('%b %d, %Y %I:%M %p') if test.due_date else ''
        for student_id in missing:
            parents = student_parents.get(student_id, [])
            student_name = student_names.get(student_id, "Your child")
            alert_msg = f"{student_name} has not taken test: {test.title} (deadline was {due_str}). [test:{test.id}]"
            for parent_id in parents:
                if (student_id, parent_id, alert_msg) not in existing_set:
                    db.add(Alert(
                        student_id=student_id,
                        recipient_id=parent_id,
                        alert_type=AlertType.TEST_MISSING,
                        message=alert_msg,
                    ))
                    push_targets.append((parent_id, student_name, test.title))
                    alerts_sent += 1

    await db.flush()

    # Send push notifications (batch, non-blocking)
    if push_targets:
        try:
            from app.api.push import send_push_to_user
            for parent_id, sname, ttitle in push_targets:  # Send to all parents
                await send_push_to_user(db, parent_id, "📝 Test Missing", f"{sname} hasn't taken: {ttitle}", "/dashboard")
        except Exception:
            pass

    return {"message": f"{alerts_sent} test-missing alerts sent to parents"}
