"""
Ingestion Engine v2 — Clean, reliable intake agent for Delta Career OS.

Architecture:
  - Uses google-genai (gemma-4-31b-it) via ai_service.generate_response / generate_json
  - Writes extracted profile to profile_store (data/profiles/<user_id>.json)
  - Downstream agents (roadmap, brief) read from the same profile store
  - Keeps conversation log in IngestionSession DB row for audit

Intake covers:
  personal introduction, backstory, transitions, exam goals, name, email,
  target_role, current_role, education, university, location, hours_per_week,
  learning_style, skills, career_goals, short_term_targets, constraints,
  resume_text, projects, certificates, study_pattern, timeline_months
"""

import json
import uuid
import datetime
import logging
import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.services.ai_service import generate_response, generate_json
from app.services.profile_store import load_profile, save_profile, profile_as_context_string
from app.services.web_search import WebSearchService

logger = logging.getLogger("delta.ingestion_v2")

# ── DB model import (lazy to avoid circular imports) ──────────────────────────
def _get_session_model():
    from app.models.semantic_memory import IngestionSession
    return IngestionSession


# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PERSONA = """You are Delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.
Your goal is to make the student feel encouraged, understood, and supported, like a caring mentor who is excited about their growth.
Your job is to gather a complete career profile through a natural, comforting conversation. The student's backstory matters as much as the resume.
Rules:
- Ask ONE clear question at a time in a comforting, friendly tutor tone.
- Keep replies concise (2-4 sentences max).
- Do NOT use emojis.
- Do NOT repeat information the user already gave.
- If the user pastes a resume or uploads one, extract facts silently, confirm receipt in a supportive tutor-like way, and ask what's still missing.
- Start from the person's story: what they studied, why they are here, what changed, what they want, and what constraints or exams are real.
- Do not force them to choose a planning horizon if it can be inferred from their education year, target exam, intake, graduation, or goal.
- Only say "Profile complete" when all required details are gathered.
"""

EXTRACT_PROMPT = """You are a structured data extractor. Given a conversation between a user and an AI intake advisor,
extract all career profile fields you can identify.

Conversation:
{conversation}

Return ONLY valid JSON with any of these fields you can extract (omit fields you cannot determine):
{{
  "personal_introduction": "string (the user's short self-introduction/backstory in their own context)",
  "backstory": "string (education/career/life context that explains why this roadmap is needed)",
  "transition_reason": "string (why they are changing direction, if any, e.g. engineering to UPSC)",
  "name": "string",
  "email": "string",
  "target_role": "string",
  "target_exam": "string (GATE|CAT|UPSC|GPSC|GRE|IELTS|TOEFL|college exams|other, if applicable)",
  "target_attempt": "string (attempt year/intake/date if mentioned or inferable)",
  "exam_goal_detail": "string (rank, college, branch, service, MBA, masters, state service, etc.)",
  "known_exam_dates": ["string"],
  "major": "string (degree major, e.g. Computer Science)",
  "university": "string (college or university name)",
  "study_year": "string (what year are they studying in, e.g. 1st year, 2nd year, graduated)",
  "gpa": "string (current GPA, e.g. 3.8/4.0)",
  "past_experience": "string (description of past projects, internships, or work history)",
  "career_goals": ["string"],
  "skills": ["string"],
  "experience_level": "beginner|intermediate|advanced",
  "target_industries": ["string"],
  "learning_style": "practical|theoretical|mixed",
  "preferred_content_types": ["string"],
  "hours_per_week": number,
  "relocation": "yes|no|maybe",
  "extracurricular_interests": ["string"],
  "planning_horizon_years": number,
  "planning_horizon_months": number,
  "inferred_planning_reason": "string (why this timeline was chosen)",
  "phone_number": "string",
  "linkedin_url": "string",
  "github_url": "string",
  "portfolio_url": "string",
  "resume_text": "extracted resume content if user pasted it"
}}

Return ONLY the JSON object, no markdown, no explanation.
"""

NEXT_QUESTION_PROMPT = """You are Delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.

Current student profile (already collected):
{profile_context}

Missing fields: {missing_fields}

Conversation so far:
{conversation}

Write a single natural follow-up question to collect the most important missing field.
Keep the tone encouraging, comforting, and supportive, like a caring tutor guiding a student.
Reference what they've already shared to make them feel heard.
If the user has an exam/career track like UPSC, GPSC, GATE, CAT, GRE, IELTS, placements, masters abroad, or MBA, ask the most useful cross-question about attempt date/intake, target outcome, current preparation level, syllabus comfort, or available weekly time.
If planning horizon can be inferred from education year, exam cycle, graduation, or intake, do not ask "how many years plan do you want"; ask for the missing date/intake or target outcome instead.
Do NOT ask for something already answered. Do NOT use emojis.
Reply with just the question text, nothing else."""

COMPLETION_PROMPT = """You are Delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.

The student's profile is now complete. Here is what was collected:
{profile_context}

Write a warm, comforting, and encouraging completion message (3-4 sentences) that:
1. Confirms their profile is successfully saved.
2. Highlights their target role and key strengths in a comforting, encouraging way.
3. Tells them their custom learning roadmap is being compiled and you are excited to help them grow.

Do NOT use emojis. Be warm, supportive, and comforting."""

# ── Fields required for a "complete" profile ─────────────────────────────────
REQUIRED_FIELDS = [
    "personal_introduction", "name", "target_role", "study_year",
    "past_experience", "career_goals", "skills", "learning_style", "hours_per_week"
]

OPTIONAL_FIELDS = [
    "email", "major", "university", "gpa", "experience_level", "target_industries",
    "preferred_content_types", "relocation", "extracurricular_interests",
    "planning_horizon_years", "planning_horizon_months", "phone_number",
    "linkedin_url", "github_url", "portfolio_url", "target_exam", "target_attempt",
    "exam_goal_detail", "known_exam_dates", "backstory", "transition_reason",
]


class IngestionEngineV2:
    """Lean, AI-powered intake agent."""

    def __init__(self):
        self.web_search = WebSearchService()

    def _profile_text(self, profile: dict) -> str:
        parts = []
        for value in profile.values():
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif isinstance(value, dict):
                parts.append(json.dumps(value, ensure_ascii=False))
            else:
                parts.append(str(value))
        return " ".join(parts).lower()

    def _detect_exam_or_goal_track(self, profile: dict) -> dict:
        text = self._profile_text(profile)
        tracks = [
            ("UPSC", ["upsc", "civil services", "ias", "ips", "ifs"]),
            ("GPSC", ["gpsc", "gujarat public service", "class 1", "class i"]),
            ("GATE", ["gate", "mtech", "psu", "iit mtech"]),
            ("CAT", ["cat", "mba", "iim", "business school", "b-school"]),
            ("GRE", ["gre", "masters abroad", "ms abroad", "masters in germany", "masters in usa"]),
            ("IELTS/TOEFL", ["ielts", "toefl", "english proficiency"]),
            ("Placements", ["placement", "campus interview", "internship season"]),
        ]
        for name, markers in tracks:
            if any(marker in text for marker in markers):
                return {"track": name, "markers": [marker for marker in markers if marker in text]}
        return {"track": "", "markers": []}

    def _infer_planning_horizon(self, profile: dict, track: str) -> dict:
        text = self._profile_text(profile)
        year_match = re.search(r"\b(1st|first|2nd|second|3rd|third|4th|fourth)\s+year\b", text)
        study_year = year_match.group(1) if year_match else str(profile.get("study_year", "")).lower()

        if track in {"UPSC", "GPSC"}:
            months = 18
            reason = f"{track} preparation usually needs a long exam-cycle plan, so Delta should plan around attempt/intake and syllabus phases."
        elif track in {"GATE", "CAT"}:
            if "2nd" in study_year or "second" in study_year:
                months = 24
            elif "3rd" in study_year or "third" in study_year:
                months = 14
            elif "4th" in study_year or "fourth" in study_year:
                months = 8
            else:
                months = 12
            reason = f"{track} is exam-cycle driven, so Delta inferred a timeline from study year and likely attempt window."
        elif track in {"GRE", "IELTS/TOEFL"}:
            months = 12
            reason = "Masters-abroad goals need intake, language tests, SOP/LOR, projects, and application deadlines, so Delta inferred a 12 month planning base."
        elif track == "Placements":
            months = 6
            reason = "Placement or internship preparation is usually near-term, so Delta inferred a shorter proof-and-interview planning base."
        else:
            months = 12
            reason = "No fixed exam cycle was identified, so Delta inferred a flexible 12 month planning base."

        return {
            "planning_horizon_months": months,
            "planning_horizon_years": max(1, round(months / 12)),
            "inferred_planning_reason": reason,
        }

    def _enrich_profile_context(self, user_id: str, profile: dict) -> dict:
        track_info = self._detect_exam_or_goal_track(profile)
        track = track_info["track"]
        horizon = self._infer_planning_horizon(profile, track)

        search_query = ""
        search_results = []
        if track:
            target_attempt = profile.get("target_attempt") or "next attempt"
            location = profile.get("location") or "India"
            search_query = f"{track} {target_attempt} exam date syllabus eligibility preparation timeline {location}"
            try:
                search_results = self.web_search.search(search_query, max_results=5)
            except Exception as exc:
                logger.warning(f"Agent 1 search enrichment failed: {exc}")
                search_results = []

        enrichment = {
            **horizon,
            "detected_goal_track": track,
            "detected_goal_markers": track_info["markers"],
            "agent1_search_query": search_query,
            "agent1_search_sources": search_results[:5],
            "roadmap_basis": "student_story + resume + constraints + inferred exam/goal timeline + search enrichment",
        }
        return save_profile(user_id, enrichment)

    def start_session(self, db: Session, user_id: str, journey_type: str = "general"):
        """
        Start or resume an intake session.
        Returns the IngestionSession DB row.
        """
        IngestionSession = _get_session_model()

        # Resume existing active session if any
        existing = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id,
            IngestionSession.status == "active"
        ).order_by(IngestionSession.created_at.desc()).first()

        if existing:
            conv = json.loads(existing.conversation_log or "[]")
            # Regenerate opening if conversation is empty
            if not conv:
                conv = [{"role": "assistant", "content": self._opening_message(user_id), "round": 0}]
                existing.conversation_log = json.dumps(conv)
                db.commit()
            return existing

        # Generate personalized opening message
        opening = self._opening_message(user_id)
        conversation = [{"role": "assistant", "content": opening, "round": 0}]

        session = IngestionSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            status="active",
            current_round=0,
            confidence_score=0.0,
            gaps_total=len(REQUIRED_FIELDS),
            gaps_filled=0,
            tensions_total=0,
            tensions_resolved=0,
            journey_type=journey_type,
            conversation_log=json.dumps(conversation),
            market_context_used=json.dumps({}),
            created_at=datetime.datetime.utcnow()
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def _opening_message(self, user_id: str) -> str:
        """Generate opening — skip fields already in profile if resuming."""
        existing = load_profile(user_id)
        if existing.get("name"):
            return (
                f"Welcome back, {existing['name']}! I have some of your details. "
                "Before I finalize the roadmap, tell me the short backstory behind your goal: "
                "what changed, what you are aiming for now, and whether any exam, intake, or deadline is coming up."
            )
        return (
            "Hi, I am Delta's intake advisor. Before the resume, give me a small introduction in your own words: "
            "who you are, what you have studied or worked on, why you are here, what goal or exam you are aiming for, "
            "and any deadline, intake, family constraint, or weekly time limit I should know. After that, attach your resume if you have one."
        )

    def process_answer(self, db: Session, user_id: str, session_id: str, answer: str) -> Dict[str, Any]:
        """
        Process one user reply:
        1. Append to conversation log
        2. Extract profile fields from full conversation → merge into profile_store
        3. Check completion
        4. Generate next question OR completion message
        Returns API response dict.
        """
        IngestionSession = _get_session_model()
        session = db.query(IngestionSession).filter(IngestionSession.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # ── 1. Append user message ────────────────────────────────────────────
        conversation = json.loads(session.conversation_log or "[]")
        conversation.append({"role": "user", "content": answer, "round": session.current_round + 1})
        session.current_round += 1

        # ── 2. Extract structured fields from full conversation ───────────────
        conv_text = "\n".join(
            f"{'Advisor' if m['role'] == 'assistant' else 'User'}: {m['content']}"
            for m in conversation
        )
        extracted = generate_json(EXTRACT_PROMPT.format(conversation=conv_text))
        if isinstance(extracted, dict) and extracted:
            if not extracted.get("personal_introduction"):
                first_user = next((m["content"] for m in conversation if m.get("role") == "user"), "")
                if first_user:
                    extracted["personal_introduction"] = first_user[:1200]
            profile_after_save = save_profile(user_id, extracted)
            self._enrich_profile_context(user_id, profile_after_save)
            logger.info(f"Extracted {list(extracted.keys())} for user {user_id}")

        # ── 3. Check completion ───────────────────────────────────────────────
        profile = load_profile(user_id)
        filled_required = [f for f in REQUIRED_FIELDS if profile.get(f)]
        missing_required = [f for f in REQUIRED_FIELDS if not profile.get(f)]

        confidence = len(filled_required) / len(REQUIRED_FIELDS)
        session.confidence_score = confidence
        session.gaps_filled = len(filled_required)
        session.gaps_total = len(REQUIRED_FIELDS)

        is_complete = (
            confidence >= 1.0
            or (confidence >= 0.85 and session.current_round >= 6)
            or session.current_round >= 10
        )

        # ── 4a. Completion path ───────────────────────────────────────────────
        if is_complete:
            session.status = "completed"
            session.completed_at = datetime.datetime.utcnow()

            # Save final profile flags
            save_profile(user_id, {
                "onboarding_complete": True,
                "confidence_score": confidence,
            })

            profile_ctx = profile_as_context_string(user_id)
            completion_msg = generate_response(
                COMPLETION_PROMPT.format(profile_context=profile_ctx),
                temperature=0.6,
                max_tokens=2000
            )
            conversation.append({"role": "assistant", "content": completion_msg, "round": session.current_round})
            session.conversation_log = json.dumps(conversation)

            # Sync to DB user record
            self._sync_profile_to_db(db, user_id, profile)
            db.commit()

            return {
                "status": "completed",
                "completed": True,
                "confidence_score": confidence,
                "message": completion_msg,
                "next_question": None,
                "profile": profile,
            }

        # ── 4b. Ask next question ─────────────────────────────────────────────
        profile_ctx = profile_as_context_string(user_id) or "No profile data yet."
        next_q = generate_response(
            NEXT_QUESTION_PROMPT.format(
                profile_context=profile_ctx,
                missing_fields=", ".join(missing_required) or "none critical",
                conversation=conv_text[-3000:]  # last 3000 chars
            ),
            temperature=0.7,
            max_tokens=2000
        )
        conversation.append({"role": "assistant", "content": next_q, "round": session.current_round})
        session.conversation_log = json.dumps(conversation)
        db.commit()

        return {
            "status": "active",
            "completed": False,
            "confidence_score": confidence,
            "next_question": next_q,
            "message": next_q,
            "missing_fields": missing_required,
            "profile": profile,
        }

    def _sync_profile_to_db(self, db: Session, user_id: str, profile: dict):
        """Sync key profile fields back to the User DB row."""
        try:
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if profile.get("name"):
                    user.name = profile["name"]
                if profile.get("target_role"):
                    user.target_role = profile["target_role"]
                if profile.get("current_role"):
                    user.current_role = profile["current_role"]
                if profile.get("hours_per_week"):
                    user.hours_per_week = int(profile["hours_per_week"])
                if profile.get("learning_style"):
                    user.learning_style = profile["learning_style"]
                db.commit()
                logger.info(f"Synced profile to DB for user {user_id}")
        except Exception as e:
            logger.warning(f"Could not sync profile to DB: {e}")

    def ingest_resume(self, db: Session, user_id: str, session_id: str, resume_text: str) -> Dict[str, Any]:
        """
        Dedicated resume ingestion — called when user uploads a file.
        Extracts everything from the resume and returns a summary + follow-up question.
        """
        if not resume_text or len(resume_text.strip()) < 50:
            return {"success": False, "message": "Resume text too short to analyze."}

        prompt = f"""You are an expert resume parser.

Extract ALL career profile information from this resume and return valid JSON.

Resume:
\"\"\"
{resume_text[:6000]}
\"\"\"

Return ONLY valid JSON with as many of these fields as you can extract:
{{
  "personal_introduction": "string (short self-introduction/backstory if present in the resume)",
  "backstory": "string (education/career context behind the roadmap)",
  "transition_reason": "string (why they are changing direction, if present)",
  "name": "string",
  "email": "string",
  "target_role": "string (infer from resume objective/title)",
  "target_exam": "string (GATE|CAT|UPSC|GPSC|GRE|IELTS|TOEFL|college exams|other, if applicable)",
  "target_attempt": "string (attempt year/intake/date if mentioned)",
  "exam_goal_detail": "string (rank, college, branch, service, MBA, masters, state service, etc.)",
  "known_exam_dates": ["string"],
  "major": "string (degree major, e.g. Computer Science)",
  "university": "string",
  "study_year": "string (what year are they studying in, e.g. 1st year, 2nd year, graduated)",
  "gpa": "string (current GPA, e.g. 3.8/4.0)",
  "past_experience": "string (description of past projects, internships, or work history)",
  "skills": ["list of technical and soft skills"],
  "experience_level": "beginner|intermediate|advanced",
  "target_industries": ["list of target industries"],
  "learning_style": "practical|theoretical|mixed (infer if possible)",
  "preferred_content_types": ["videos|articles|projects"],
  "hours_per_week": number,
  "relocation": "yes|no|maybe",
  "extracurricular_interests": ["list of interests"],
  "planning_horizon_years": number,
  "planning_horizon_months": number,
  "inferred_planning_reason": "string",
  "phone_number": "string",
  "linkedin_url": "string",
  "github_url": "string",
  "portfolio_url": "string",
  "career_goals": ["inferred from objective/summary section"],
  "resume_text": "first 2000 chars of raw resume for context"
}}

Return ONLY the JSON object."""

        extracted = generate_json(prompt, temperature=0.1)
        if isinstance(extracted, dict) and extracted:
            extracted["resume_text"] = resume_text[:3000]
            profile_after_save = save_profile(user_id, extracted)
            self._enrich_profile_context(user_id, profile_after_save)

            # Update session conversation
            IngestionSession = _get_session_model()
            session = db.query(IngestionSession).filter(IngestionSession.id == session_id).first()
            if session:
                conv = json.loads(session.conversation_log or "[]")
                summary_fields = [k for k in extracted if k != "resume_text"]
                system_note = f"[Resume analyzed — extracted: {', '.join(summary_fields)}]"
                conv.append({"role": "system_note", "content": system_note})

                # Calculate confidence score and completion status
                profile = load_profile(user_id)
                filled_required = [f for f in REQUIRED_FIELDS if profile.get(f)]
                missing = [f for f in REQUIRED_FIELDS if not profile.get(f)]
                confidence = len(filled_required) / len(REQUIRED_FIELDS)
                
                session.confidence_score = confidence
                session.gaps_filled = len(filled_required)
                session.gaps_total = len(REQUIRED_FIELDS)

                is_complete = confidence >= 1.0

                if is_complete:
                    session.status = "completed"
                    session.completed_at = datetime.datetime.utcnow()

                    save_profile(user_id, {
                        "onboarding_complete": True,
                        "confidence_score": confidence,
                    })

                    profile_ctx = profile_as_context_string(user_id)
                    completion_msg = generate_response(
                        COMPLETION_PROMPT.format(profile_context=profile_ctx),
                        temperature=0.6,
                        max_tokens=2000
                    )
                    conv.append({"role": "assistant", "content": completion_msg})
                    session.conversation_log = json.dumps(conv)

                    self._sync_profile_to_db(db, user_id, profile)
                    db.commit()

                    return {
                        "success": True,
                        "status": "completed",
                        "completed": True,
                        "extracted_fields": summary_fields,
                        "follow_up": None,
                        "message": completion_msg,
                        "confidence_score": confidence,
                        "filled_fields": filled_required,
                        "missing_fields": [],
                        "profile": profile,
                    }
                else:
                    # Generate follow-up after resume
                    profile_ctx = profile_as_context_string(user_id)
                    follow_up = generate_response(
                        NEXT_QUESTION_PROMPT.format(
                            profile_context=profile_ctx,
                            missing_fields=", ".join(missing) or "none",
                            conversation="\n".join(
                                f"{'Advisor' if m['role'] == 'assistant' else 'User'}: {m['content']}"
                                for m in conv if m["role"] in ("assistant", "user")
                            )[-2000:]
                        ),
                        temperature=0.6,
                        max_tokens=2000
                    )
                    conv.append({"role": "assistant", "content": follow_up})
                    session.conversation_log = json.dumps(conv)
                    db.commit()

                    return {
                        "success": True,
                        "status": "active",
                        "completed": False,
                        "extracted_fields": summary_fields,
                        "follow_up": follow_up,
                        "message": follow_up,
                        "confidence_score": confidence,
                        "filled_fields": filled_required,
                        "missing_fields": missing,
                        "profile": profile,
                    }

        return {"success": False, "message": "Could not extract meaningful data from resume."}

    def get_state(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Return current session state and profile summary."""
        IngestionSession = _get_session_model()
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id
        ).order_by(IngestionSession.created_at.desc()).first()

        profile = load_profile(user_id)
        filled = [f for f in REQUIRED_FIELDS if profile.get(f)]

        return {
            "has_active_session": session is not None and session.status == "active",
            "onboarding_complete": profile.get("onboarding_complete", False),
            "confidence_score": profile.get("confidence_score", len(filled) / len(REQUIRED_FIELDS)),
            "filled_fields": filled,
            "missing_fields": [f for f in REQUIRED_FIELDS if not profile.get(f)],
            "profile": profile,
            "session": {
                "id": session.id if session else None,
                "status": session.status if session else "none",
                "current_round": session.current_round if session else 0,
                "journey_type": session.journey_type if session else "general"
            } if session else None,
        }

    def force_complete(self, db: Session, user_id: str) -> Dict[str, Any]:
        """Force-complete the active session, writing whatever is collected."""
        IngestionSession = _get_session_model()
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id,
            IngestionSession.status == "active"
        ).order_by(IngestionSession.created_at.desc()).first()

        if session:
            session.status = "completed"
            session.completed_at = datetime.datetime.utcnow()
            db.commit()

        profile = load_profile(user_id)
        save_profile(user_id, {"onboarding_complete": True})
        self._sync_profile_to_db(db, user_id, profile)

        return {"status": "completed", "profile": profile}


# ── Singleton instance ────────────────────────────────────────────────────────
engine = IngestionEngineV2()
