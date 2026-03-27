"""
Gemini Live API — Real-Time Voice Interview

Architecture:
  Browser (PCM16 16kHz) ←→ FastAPI WebSocket ←→ Gemini Live API

  SINGLE receive() loop handles both greeting and conversation.
  greeting_done flag controls when mic starts.
  Transcript text is accumulated and flushed as complete sentences on turn_complete.
"""

import asyncio
import base64
import json
import logging
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from google import genai
from google.genai import types

from app.database import async_session
from app.models.user import User, UserRole, AISettings
from app.models.academic import Test, Topic
from app.core.security import decode_access_token
from app.services.ai import (
    get_next_api_key, get_fallback_api_key, get_cached_setting,
    _ensure_cache, ai_chat_json,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["VoiceInterview"])

GEMINI_LIVE_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"


async def _auth_ws_user(token: str) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise ValueError("Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("Invalid token payload")
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user:
        raise ValueError("User not found")
    return user


def _get_gemini_key() -> str:
    key = get_next_api_key("gemini")
    if key:
        return key
    return get_fallback_api_key("gemini") or get_cached_setting("gemini_api_key", "")


def _build_system_prompt(topic_text: str, total_questions: int) -> str:
    return f"""You are a friendly teacher conducting a real-time voice interview with a student.

TOPIC CONTENT:
{topic_text[:3000]}

CRITICAL REQUIREMENT — YOU MUST ASK EXACTLY {total_questions} QUESTIONS:
- Keep an internal counter: Question 1, Question 2, ... Question {total_questions}.
- After getting the student's response to one question, give brief feedback, then ask the NEXT question.
- Do NOT stop until you have asked all {total_questions} questions.
- Do NOT end the interview early under any circumstances.
- Mention the question number when asking, e.g. "For question 3..." or "Next, question 4...".

INTERVIEW STRUCTURE:
1. Start with a warm greeting: "Hi! We're going to go through {total_questions} questions about this topic. Let's begin!"
2. Ask Question 1 (easy).
3. Wait for answer → give brief feedback → ask Question 2 (moderate).
4. Continue until Question {total_questions} (hardest).
5. After the LAST answer, give a proper closing statement.

CONVERSATION STYLE:
- Keep each response SHORT — 1 to 3 sentences max, then ask the next question.
- Be conversational, warm, and encouraging.
- React naturally: "Good thinking!", "That's close!", "Let me give you a hint..."
- The student CAN interrupt you at any time. If they do, stop and listen to what they say.

HANDLING SILENCE — READ THIS CAREFULLY:
You must distinguish between these types of silence:

1. ANSWER SOUNDS COMPLETE + pause:
   - The student gave what sounds like a finished answer. After a brief pause, give feedback and move on.
   - Do NOT wait long — proceed naturally.

2. ANSWER SOUNDS INCOMPLETE + pause (student trailed off, said "um...", or gave only a partial answer):
   - Wait a bit longer — they might be gathering their thoughts.
   - If still silent, ask: "Would you like a hint?" or give a small nudge.
   - If still stuck after the hint, explain the answer briefly and move on.

3. COMPLETE SILENCE (student never started answering):
   - Prompt them: "Take your time! Any thoughts?"
   - If still nothing, offer a hint.
   - If still nothing after the hint, explain and move on.

- NEVER skip a question without at least offering a hint first.
- The student CAN interrupt you at any time. If they do, stop and listen.
- IGNORE background noise like fans, traffic, typing. Only respond to actual human speech.

WHEN THE STUDENT IS WRONG:
- Briefly explain where they went wrong and give the correct concept.
- Example: "Not quite — actually, photosynthesis happens in the chloroplasts, not the mitochondria. Let's move on to question 3..."

SCORING NOTES (for your internal tracking, the evaluator will use these):
- If you gave a small hint (nudge/clue) → minor deduction.
- If you gave a big hint (almost the full answer) → major deduction.
- If you had to explain the full answer → score near zero for that question.
- Always mention in your response when you're giving a hint, so the evaluator can track it.

ENDING — ONLY after Question {total_questions} has been answered (or attempted):
1. Thank the student: "Excellent work! You've answered all {total_questions} questions."
2. Give a brief overall comment: mention what they did well and what to review.
3. Say a warm goodbye: "That wraps up our interview. Great job, keep studying!"
4. Then, and ONLY then, output exactly: [INTERVIEW_COMPLETE]

ABSOLUTELY DO NOT output [INTERVIEW_COMPLETE] until:
- All {total_questions} questions have been asked AND answered (or attempted with hints).
- You have said a proper goodbye message."""


async def _evaluate_transcript(
    transcript: str, total_q: int, topic_text: str, user_id: str
) -> dict:
    system_prompt = f"""Evaluate this voice interview transcript. Topic: {topic_text[:2000]}

Return JSON:
{{"results": [{{"question": "...", "student_answer": "...", "score": 0-100, "feedback": "...", "understanding": "weak"|"moderate"|"strong"}}], "overall_score": 0-100, "overall_feedback": "2-3 sentence summary"}}

Rules:
- Score based on correctness and understanding.
- If a small hint/nudge was given before the answer, DEDUCT 15-25 points.
- If a big hint (nearly the answer) was given, DEDUCT 30-50 points.
- If the teacher had to explain the full answer, score 0-10 for that question.
- If no answer at all, score 0.
- Note in feedback the hint level (e.g. "Answered after small hint", "Teacher explained answer").
- Ignore filler words, stuttering.
- student_answer should reflect ONLY what the student actually said. Do NOT fabricate answers."""

    try:
        async with async_session() as db:
            result = await ai_chat_json(
                db, user_id, system_prompt,
                f"Transcript:\n{transcript[:4000]}",
                max_tokens=2048,
            )
            return result if "results" in result else {
                "results": [], "overall_score": 0,
                "overall_feedback": "Could not evaluate."
            }
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            "results": [], "overall_score": 0,
            "overall_feedback": f"Evaluation error: {str(e)[:200]}"
        }


# ── Main WebSocket ───────────────────────────────────────────

@router.websocket("/ws/voice-test")
async def voice_test_ws(websocket: WebSocket):
    await websocket.accept()

    token = websocket.query_params.get("token", "")
    test_id = websocket.query_params.get("test_id", "")

    try:
        user = await _auth_ws_user(token)
    except Exception:
        await websocket.send_json({"type": "error", "msg": "Authentication failed"})
        await websocket.close()
        return

    if user.role != UserRole.STUDENT:
        await websocket.send_json({"type": "error", "msg": "Only students"})
        await websocket.close()
        return

    async with async_session() as db:
        await _ensure_cache(db)
        result = await db.execute(
            select(Test, Topic).join(Topic, Test.topic_id == Topic.id).where(Test.id == test_id)
        )
        row = result.one_or_none()

    if not row:
        await websocket.send_json({"type": "error", "msg": "Test not found"})
        await websocket.close()
        return

    test, topic = row
    topic_text = topic.extracted_text or ""
    total_q = getattr(test, "num_questions", 5) or 5

    if not topic_text:
        await websocket.send_json({"type": "error", "msg": "No topic content"})
        await websocket.close()
        return

    gemini_key = _get_gemini_key()
    if not gemini_key:
        await websocket.send_json({"type": "error", "msg": "No Gemini API key"})
        await websocket.close()
        return

    await websocket.send_json({"type": "status", "msg": "Connecting to AI..."})

    transcript_lines: list[str] = []
    interview_complete = False
    session_closed = asyncio.Event()
    user_id_str = str(user.id)

    try:
        client = genai.Client(api_key=gemini_key)

        # Read VAD settings from cached admin config (no DB query)
        from app.services.ai import get_cached_setting
        vad_silence = int(get_cached_setting("vad_silence_ms", 2000) or 2000)
        vad_sensitivity = get_cached_setting("vad_sensitivity", "END_SENSITIVITY_HIGH") or "END_SENSITIVITY_HIGH"
        vad_proactivity = get_cached_setting("vad_proactivity", False)

        config_kwargs = dict(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=_build_system_prompt(topic_text, total_q))]
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    end_of_speech_sensitivity=vad_sensitivity,
                    silence_duration_ms=vad_silence,
                )
            ),
        )
        # Proactivity only if enabled (requires API support)
        if vad_proactivity:
            try:
                config_kwargs["proactivity"] = types.ProactivityConfig(proactive_audio=True)
            except Exception:
                pass  # API doesn't support it yet

        config = types.LiveConnectConfig(**config_kwargs)

        async with client.aio.live.connect(
            model=GEMINI_LIVE_MODEL, config=config
        ) as gemini_session:

            # Send initial text prompt to trigger the greeting
            print("[VOICE] Sending initial prompt...")
            await gemini_session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text="Hello! I'm ready for my interview.")]
                ),
                turn_complete=True,
            )

            await websocket.send_json({
                "type": "status",
                "msg": "🎤 Interview starting..."
            })

            # ── Gemini → Browser ──
            # SDK's receive() yields ONE turn then breaks.
            # We call it in a while loop for multi-turn conversation.
            async def gemini_to_browser():
                nonlocal interview_complete
                turn_count = 0
                ai_transcript_buf: list[str] = []
                user_transcript_buf: list[str] = []
                try:
                    while not session_closed.is_set() and not interview_complete:
                        async for response in gemini_session.receive():
                            if session_closed.is_set():
                                return

                            sc = response.server_content
                            if not sc:
                                continue

                            # Forward audio to browser
                            if sc.model_turn and sc.model_turn.parts:
                                for part in sc.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        b64 = base64.b64encode(
                                            part.inline_data.data
                                        ).decode()
                                        try:
                                            await websocket.send_json({
                                                "type": "audio", "data": b64
                                            })
                                        except Exception:
                                            session_closed.set()
                                            return

                            # Accumulate AI transcript
                            ot = getattr(sc, 'output_transcription', None)
                            if ot and ot.text:
                                ai_transcript_buf.append(ot.text)

                            # Accumulate user transcript
                            it = getattr(sc, 'input_transcription', None)
                            if it and it.text:
                                user_transcript_buf.append(it.text)

                            # Turn complete — flush transcripts
                            if sc.turn_complete:
                                turn_count += 1

                                # Flush user transcript
                                if user_transcript_buf:
                                    user_full = "".join(
                                        user_transcript_buf
                                    ).strip()
                                    user_transcript_buf.clear()
                                    if user_full:
                                        print(f"[VOICE] User: {user_full[:120]}")
                                        transcript_lines.append(
                                            f"Student: {user_full}"
                                        )
                                        try:
                                            await websocket.send_json({
                                                "type": "transcript",
                                                "role": "user",
                                                "text": user_full,
                                            })
                                        except Exception:
                                            session_closed.set()
                                            return

                                # Flush AI transcript
                                if ai_transcript_buf:
                                    ai_full = "".join(
                                        ai_transcript_buf
                                    ).strip()
                                    ai_transcript_buf.clear()
                                    if "[INTERVIEW_COMPLETE]" in ai_full:
                                        interview_complete = True
                                        ai_full = ai_full.replace(
                                            "[INTERVIEW_COMPLETE]", ""
                                        ).strip()
                                    if ai_full:
                                        print(f"[VOICE] AI: {ai_full[:120]}")
                                        transcript_lines.append(
                                            f"Teacher: {ai_full}"
                                        )
                                        try:
                                            await websocket.send_json({
                                                "type": "transcript",
                                                "role": "assistant",
                                                "text": ai_full,
                                            })
                                        except Exception:
                                            session_closed.set()
                                            return

                                print(
                                    f"[VOICE] Turn #{turn_count} complete"
                                    f" (interview_complete="
                                    f"{interview_complete})"
                                )
                                try:
                                    await websocket.send_json({
                                        "type": "turn_complete"
                                    })
                                except Exception:
                                    session_closed.set()
                                    return

                                if interview_complete:
                                    print("[VOICE] Interview complete!")
                                    session_closed.set()
                                    return

                            # Barge-in
                            interrupted = getattr(sc, 'interrupted', False)
                            if interrupted:
                                print("[VOICE] Barge-in")
                                try:
                                    await websocket.send_json({
                                        "type": "interrupted"
                                    })
                                except Exception:
                                    session_closed.set()
                                    return

                        # receive() returned (one turn done) — loop back
                        print(
                            f"[VOICE] receive() returned after turn"
                            f" #{turn_count}, looping..."
                        )

                except Exception as e:
                    print(
                        f"[VOICE] gemini_to_browser ERROR: {e}\n"
                        f"{traceback.format_exc()}"
                    )
                finally:
                    if not session_closed.is_set():
                        session_closed.set()

            # ── Browser → Gemini (forwards all audio immediately) ──
            async def browser_to_gemini():
                nonlocal interview_complete
                audio_count = 0
                try:
                    while not session_closed.is_set():
                        try:
                            msg = await asyncio.wait_for(
                                websocket.receive(), timeout=1.0
                            )
                        except asyncio.TimeoutError:
                            continue
                        except (WebSocketDisconnect, RuntimeError):
                            print("[VOICE] Browser disconnected")
                            session_closed.set()
                            return

                        # Binary = PCM16 audio — forward immediately
                        if "bytes" in msg and msg["bytes"]:
                            audio_count += 1
                            try:
                                await gemini_session.send_realtime_input(
                                    audio=types.Blob(
                                        data=msg["bytes"],
                                        mime_type="audio/pcm;rate=16000",
                                    )
                                )
                            except Exception as e:
                                print(
                                    f"[VOICE] send audio #{audio_count}"
                                    f" failed: {e}"
                                )
                                session_closed.set()
                                return

                        # Text = JSON control
                        elif "text" in msg and msg["text"]:
                            try:
                                data = json.loads(msg["text"])
                            except json.JSONDecodeError:
                                continue

                            if data.get("type") == "end_test":
                                print("[VOICE] User ended test")
                                interview_complete = True
                                try:
                                    await gemini_session.send_client_content(
                                        turns=types.Content(
                                            role="user",
                                            parts=[types.Part(
                                                text="Wrap up now. "
                                                "Say goodbye, then "
                                                "[INTERVIEW_COMPLETE]."
                                            )]
                                        ),
                                        turn_complete=True,
                                    )
                                except Exception:
                                    session_closed.set()
                                    return
                                try:
                                    await asyncio.wait_for(
                                        session_closed.wait(), timeout=15.0
                                    )
                                except asyncio.TimeoutError:
                                    session_closed.set()
                                return

                    print(
                        f"[VOICE] browser_to_gemini done"
                        f" ({audio_count} audio chunks)"
                    )
                except Exception as e:
                    print(
                        f"[VOICE] browser_to_gemini ERROR: {e}\n"
                        f"{traceback.format_exc()}"
                    )
                    if not session_closed.is_set():
                        session_closed.set()

            # Run both tasks concurrently
            await asyncio.gather(
                gemini_to_browser(),
                browser_to_gemini(),
                return_exceptions=True,
            )
            print("[VOICE] Both tasks finished")

    except Exception as e:
        print(f"[VOICE] Session error: {traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "msg": f"AI error: {str(e)[:200]}"
            })
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        return

    # ── Evaluate ──
    # Guard: don't evaluate if no student actually spoke
    student_lines = [l for l in transcript_lines if l.startswith("Student:")]
    if not student_lines:
        print("[VOICE] No student responses — skipping evaluation")
        try:
            await websocket.send_json({
                "type": "done",
                "results": [],
                "overall_score": 0,
                "overall_feedback": "Interview ended before any answers were given.",
            })
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        print("[VOICE] Session ended (no eval)")
        return

    print(f"[VOICE] Evaluating ({len(transcript_lines)} lines)...")
    try:
        await websocket.send_json({
            "type": "status", "msg": "⏳ Evaluating..."
        })
    except Exception:
        pass

    full_transcript = "\n".join(transcript_lines)
    eval_result = await _evaluate_transcript(
        full_transcript, total_q, topic_text, user_id_str
    )

    try:
        from app.api.tests import store_voice_answers
        store_voice_answers(
            user_id_str, test_id, eval_result.get("results", [])
        )
    except Exception as e:
        print(f"[VOICE] store_voice_answers failed: {e}")

    try:
        await websocket.send_json({
            "type": "done",
            "results": eval_result.get("results", []),
            "overall_score": eval_result.get("overall_score", 0),
            "overall_feedback": eval_result.get("overall_feedback", ""),
        })
    except Exception:
        pass

    try:
        await websocket.close()
    except Exception:
        pass
    print("[VOICE] Session ended")
