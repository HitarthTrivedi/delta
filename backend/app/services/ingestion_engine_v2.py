"""
Ingestion Engine v2 — Clean, reliable intake agent for delta Career OS.

Architecture:
  - Uses google-genai via ai_service.generate_response / generate_json: the resume
    parse runs on gemini-2.5-flash (accuracy) and the Q&A round on gemma-4-31b-it (quota)
  - Writes extracted profile to profile_store (data/profiles/<user_id>.json)
  - Downstream agents (roadmap, brief) read from the same profile store
  - Keeps conversation log in IngestionSession DB row for audit

Intake covers:
  personal introduction, backstory, transitions, exam goals, name, email,
  target_role, current_role, education_stage, education, university, location, hours_per_week,
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

# Model assignment for the intake agent:
#  - Resume parsing is a single, accuracy-critical, infrequent call → use the
#    stronger gemini-2.5-flash so skills/facts are extracted correctly without guessing.
#  - The conversational Q&A round is many back-and-forth calls → use gemma-4-31b-it
#    to stay within the free Gemini quota (gemini-2.5-flash free tier is call-limited).
# Everything else in the app (roadmap/progress/resume feature) keeps the globally
# configured GEMINI_MODEL.
INTAKE_RESUME_MODEL = "gemini-2.5-flash"
INTAKE_CHAT_MODEL = "gemma-4-31b-it"

# Minimum number of genuine user answers required before the intake can finish —
# guarantees a real goals/ambitions conversation even when a resume already fills
# most factual fields.
MIN_INTAKE_ROUNDS = 3

from app.models.semantic_memory import IngestionSession
from app.models.user import User


# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PERSONA = """You are delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.
Your goal is to make the student feel encouraged, understood, and supported, like a caring mentor who is excited about their growth.
Your job is to gather a complete career profile through a natural, comforting conversation. The student's backstory matters as much as the resume.
Rules:
- Ask ONE clear question at a time in a comforting, friendly tutor tone.
- Keep replies concise (2-4 sentences max).
- Do NOT use emojis.
- Do NOT repeat information the user already gave.
- If the user pastes a resume or uploads one, extract facts silently, confirm receipt in a supportive tutor-like way, and ask what's still missing.
- A resume is optional. Many users may be school students, dropouts, undergrads, exam aspirants, freshers, or career switchers with no resume yet.
- Start from the person's story: what they studied, why they are here, what changed, what they want, and what constraints or exams are real.
- ALWAYS ask the story behind why they joined delta and how urgent their goal is — are they just sharpening skills with no rush, or racing a real deadline? This story decides their whole pace.
- Do NOT force the user to state weekly hours. If they have not said how much time they have, delta will SUGGEST a sensible weekly-hours and pace from their story and deadline; only ask for hours if their story is genuinely unclear.
- Accept "no projects yet", "no resume", "not sure", or "still exploring" as valid profile facts. Do not force professional fields on school/no-resume users.
- Do not force them to choose a planning horizon if it can be inferred from their education year, target exam, intake, graduation, or goal.
- When enough details are gathered, send the user to review/edit their profile before roadmap generation.
"""

EXTRACT_PROMPT = """You are a structured data extractor. Given a conversation between a user and an AI intake advisor,
extract all career profile fields you can identify.

Conversation:
{conversation}

Return ONLY valid JSON with any of these fields you can extract (omit fields you cannot determine):
{{
  "personal_introduction": "string (the user's short self-introduction/backstory in their own context)",
  "backstory": "string (education/career/life context that explains why this roadmap is needed)",
  "joining_reason": "string — the STORY behind why they came to delta and what they want to change (e.g. 'just want to sharpen skills', 'need a job fast', 'switching careers', 'preparing for placements').",
  "urgency_level": "relaxed|moderate|urgent — how time-pressured they are about reaching the goal. Only set if it is clear from what they said.",
  "time_to_goal": "string — any deadline or timeframe to reach the goal (e.g. '3 months', 'placements in December', 'no fixed deadline'). Only if stated.",
  "transition_reason": "string (why they are changing direction, if any)",
  "name": "string",
  "email": "string",
  "current_status": "school|dropped_out|undergrad|graduate|working|career_switcher|exam_aspirant|other",
  "education_stage": "string (school class, undergrad year, dropout, graduate, working, etc.)",
  "has_resume": true,
  "target_role": "string",
  "goal_direction": "string (if exact role is unclear, describe the direction or aspiration)",
  "target_exam": "string — ONLY if the student EXPLICITLY named an exam (GATE, CAT, UPSC, GPSC, GRE, IELTS, TOEFL). NEVER guess or infer one. Omit otherwise.",
  "target_attempt": "string (attempt year/intake/date — only if explicitly stated)",
  "exam_goal_detail": "string (rank, college, branch, service, MBA, masters, etc. — only if explicitly stated)",
  "known_exam_dates": ["string"],
  "major": "string (degree major, e.g. Computer Science)",
  "university": "string (college or university name)",
  "study_year": "string (what year are they studying in, e.g. 1st year, 2nd year, graduated)",
  "gpa": "string (current GPA, e.g. 3.8/4.0)",
  "past_experience": "string (description of past projects, internships, or work history)",
  "projects": ["string"],
  "no_experience_yet": true,
  "career_goals": ["string"],
  "skills": ["string"],
  "experience_level": "beginner|intermediate|advanced",
  "target_industries": ["string"],
  "learning_style": "practical|theoretical|mixed",
  "preferred_content_types": ["string"],
  "hours_per_week": "number — ONLY if the student states how much time they have. If they do not say, OMIT it; delta will suggest a pace from their story.",
  "relocation": "yes|no|maybe",
  "extracurricular_interests": ["string"],
  "phone_number": "string",
  "linkedin_url": "string",
  "github_url": "string",
  "portfolio_url": "string",
  "resume_text": "extracted resume content if user pasted it"
}}

Return ONLY the JSON object, no markdown, no explanation.
"""

NEXT_QUESTION_PROMPT = """You are delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.

Current student profile (already collected):
{profile_context}

Missing fields: {missing_fields}

Conversation so far:
{conversation}

Write ONE short, precise follow-up question to collect the single most important missing field.

Hard rules:
- Keep it to ONE sentence. Be simple, warm, and direct. No long preambles.
- Do NOT ask anything already answered.
- This student could be anyone: a school student, a dropout, an undergrad, a master's student, a fresher, or a career switcher. Adapt the wording to their stage; never assume a level of background they have not shown.
- Only ask about a competitive exam (UPSC, GATE, CAT, GRE, etc.) if the student has EXPLICITLY mentioned one. Never bring up an exam on your own.
- If they have no resume or no projects yet, that is fine — ask about their interests, current level, or how much time they have, not resume details.
- Do NOT use emojis.

What to ask about, in priority order:
1. The STORY behind joining delta and the time pressure — if you do not yet know WHY they came (just improving skills? chasing a job? a deadline?) or HOW urgent it is, ask that first. It decides their pace.
2. If a real field is still missing, ask for that field.
3. Otherwise (e.g. a resume already covers the facts), ask about the things a resume CANNOT tell you — the student's actual goals, ambitions, motivation ("why this path"), what success looks like for them, or the kind of role/work they truly want.

Never ask "how many hours per week can you give" unless their story gives no clue about their time pressure — delta suggests the hours itself.

Reply with just the question text, nothing else."""

COMPLETION_PROMPT = """You are delta's AI career intake advisor. Your persona is a comforting, friendly, and supportive tutor interacting with a student.

The student's profile is ready for review. Here is what was collected:
{profile_context}

Write a warm, comforting, and encouraging completion message (3-4 sentences) that:
1. Confirms their profile is successfully saved.
2. Highlights their target role and key strengths in a comforting, encouraging way.
3. States the weekly pace and hours delta is suggesting for them based on their story and time pressure (use the 'pace' and 'recommended_hours_per_week' from the profile), and tell them they can change it.
4. Tells them to review and edit anything before delta builds the roadmap.

Do NOT use emojis. Be warm, supportive, and comforting."""

# ── Fields required for a "complete" profile ─────────────────────────────────
REQUIRED_FIELDS = [
    "personal_introduction", "name", "target_role", "study_year",
    "past_experience", "career_goals", "skills", "learning_style", "hours_per_week"
]

# hours_per_week is intentionally NOT required — delta suggests it from the joining
# story. The joining story (why they came + how urgent) is what must be captured.
CORE_REQUIRED_FIELDS = [
    "personal_introduction", "name", "joining_reason", "learning_style"
]

PROFILE_REVIEW_FIELDS = [
    "name", "current_status", "education_stage", "study_year", "target_role",
    "goal_direction", "joining_reason", "career_goals", "skills", "past_experience",
    "projects", "hours_per_week", "learning_style", "constraints",
]

OPTIONAL_FIELDS = [
    "email", "major", "university", "gpa", "experience_level", "target_industries",
    "preferred_content_types", "relocation", "extracurricular_interests",
    "planning_horizon_years", "planning_horizon_months", "phone_number",
    "linkedin_url", "github_url", "portfolio_url", "target_exam", "target_attempt",
    "exam_goal_detail", "known_exam_dates", "backstory", "transition_reason",
    "urgency_level", "time_to_goal", "recommended_hours_per_week", "pace", "pace_reason",
    "current_status", "education_stage", "goal_direction", "projects",
    "no_experience_yet", "has_resume",
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
        # Only scan fields where a user would actually state an exam/goal track.
        # Scanning the whole profile caused incidental words (e.g. inside skills or
        # role descriptions) to falsely trigger an exam track.
        scan_fields = (
            "target_exam", "exam_goal_detail", "backstory", "personal_introduction",
            "transition_reason", "goal_direction", "career_goals", "resume_text",
        )
        parts = []
        for field in scan_fields:
            value = profile.get(field)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif value:
                parts.append(str(value))
        text = " ".join(parts).lower()
        tracks = [
            ("UPSC", [r"\bupsc\b", r"\bcivil\s+services\b", r"\bias\b", r"\bips\b", r"\bifs\b"]),
            ("GPSC", [r"\bgpsc\b", r"\bgujarat\s+public\s+service\b", r"\bclass\s+1\b", r"\bclass\s+i\b"]),
            ("GATE", [r"\bgate\b", r"\bmtech\b", r"\bpsu\b", r"\biit\s+mtech\b"]),
            ("CAT", [r"\bcat\b", r"\bmba\b", r"\biim\b", r"\bbusiness\s+school\b", r"\bb-school\b"]),
            ("GRE", [r"\bgre\b", r"\bmasters\s+abroad\b", r"\bms\s+abroad\b", r"\bmasters\s+in\s+germany\b", r"\bmasters\s+in\s+usa\b"]),
            ("IELTS/TOEFL", [r"\bielts\b", r"\btoefl\b", r"\benglish\s+proficiency\b"]),
            ("Placements", [r"\bplacement\b", r"\bcampus\s+interview\b", r"\binternship\s+season\b"]),
        ]
        for name, markers in tracks:
            matched_markers = []
            for marker in markers:
                if re.search(marker, text):
                    matched_markers.append(marker.replace(r"\b", "").replace(r"\s+", " "))
            if matched_markers:
                return {"track": name, "markers": matched_markers}
        return {"track": "", "markers": []}


    def _infer_planning_horizon(self, profile: dict, track: str) -> dict:
        text = self._profile_text(profile)
        year_match = re.search(r"\b(1st|first|2nd|second|3rd|third|4th|fourth)\s+year\b", text)
        study_year = year_match.group(1) if year_match else str(profile.get("study_year", "")).lower()

        if track in {"UPSC", "GPSC"}:
            months = 18
            reason = f"{track} preparation usually needs a long exam-cycle plan, so delta should plan around attempt/intake and syllabus phases."
        elif track in {"GATE", "CAT"}:
            if "2nd" in study_year or "second" in study_year:
                months = 24
            elif "3rd" in study_year or "third" in study_year:
                months = 14
            elif "4th" in study_year or "fourth" in study_year:
                months = 8
            else:
                months = 12
            reason = f"{track} is exam-cycle driven, so delta inferred a timeline from study year and likely attempt window."
        elif track in {"GRE", "IELTS/TOEFL"}:
            months = 12
            reason = "Masters-abroad goals need intake, language tests, SOP/LOR, projects, and application deadlines, so delta inferred a 12 month planning base."
        elif track == "Placements":
            months = 6
            reason = "Placement or internship preparation is usually near-term, so delta inferred a shorter proof-and-interview planning base."
        else:
            # No exam/track and no explicit timeline from the user — use a soft default
            # for internal planning but do NOT fabricate a confident-sounding reason.
            months = 12
            reason = ""

        return {
            "planning_horizon_months": months,
            "planning_horizon_years": max(1, round(months / 12)),
            "inferred_planning_reason": reason,
        }

    def _has_goal_signal(self, profile: dict) -> bool:
        return bool(
            profile.get("target_role")
            or profile.get("goal_direction")
            or profile.get("target_exam")
            or profile.get("career_goals")
        )

    def _has_stage_signal(self, profile: dict) -> bool:
        return bool(
            profile.get("current_status")
            or profile.get("education_stage")
            or profile.get("study_year")
            or profile.get("current_role")
        )

    def _profile_review_missing_fields(self, profile: dict) -> list[str]:
        missing = [field for field in CORE_REQUIRED_FIELDS if not profile.get(field)]
        if not self._has_goal_signal(profile):
            missing.append("goal_direction")
        if not self._has_stage_signal(profile):
            missing.append("education_stage")
        return list(dict.fromkeys(missing))

    def _review_readiness(self, profile: dict, round_count: int) -> tuple[bool, float, list[str]]:
        missing = self._profile_review_missing_fields(profile)
        filled = len(PROFILE_REVIEW_FIELDS) - len([field for field in PROFILE_REVIEW_FIELDS if not profile.get(field)])
        confidence = min(0.98, max(0.0, filled / max(len(PROFILE_REVIEW_FIELDS), 1)))
        has_substance = (
            round_count >= 4
            or bool(profile.get("has_resume"))
            or bool(profile.get("no_experience_yet"))
            or bool(profile.get("projects"))
            or bool(profile.get("skills"))
        )
        # Always require a minimum number of real answers so delta actually asks about
        # the student's goals/ambitions, even when a resume already fills the facts.
        ready = (not missing) and (round_count >= MIN_INTAKE_ROUNDS) and has_substance
        return ready, confidence, missing

    def _suggest_pace(self, profile: dict) -> dict:
        """
        Recommend weekly hours + pace from the user's joining story and time pressure.
        This is the core of "tell me your story and delta sets your pace".
        """
        urgency = (profile.get("urgency_level") or "").lower().strip()
        story = " ".join(
            str(profile.get(field, "") or "")
            for field in (
                "joining_reason", "time_to_goal", "backstory", "personal_introduction",
                "transition_reason", "goal_direction", "career_goals",
            )
        ).lower()

        urgent_markers = [
            "urgent", "asap", "as soon as", "few weeks", "next month", "this month",
            "1 month", "2 month", "3 month", "placement", "deadline", "interview soon",
            "very less time", "less time", "running out of time", "quickly", "fast",
            "immediately", "right away", "need a job", "need job", "soon",
        ]
        relaxed_markers = [
            "just improve", "improve my skill", "improve skill", "sharpen", "no rush",
            "no hurry", "explore", "exploring", "hobby", "long term", "long-term",
            "whenever", "casually", "on the side", "curious", "slowly", "no deadline",
            "no fixed deadline",
        ]

        if urgency not in ("relaxed", "moderate", "urgent"):
            if any(marker in story for marker in urgent_markers):
                urgency = "urgent"
            elif any(marker in story for marker in relaxed_markers):
                urgency = "relaxed"
            else:
                urgency = "moderate"

        # A short planning horizon always means urgency, whatever the wording.
        months = profile.get("planning_horizon_months")
        if isinstance(months, (int, float)) and 0 < months <= 3:
            urgency = "urgent"

        if urgency == "urgent":
            hours, pace = 14, "intensive"
            reason = "You have a short runway to your goal, so delta suggests an intensive pace to make every week count."
        elif urgency == "relaxed":
            hours, pace = 5, "light"
            reason = "You are here to steadily build skills with no hard deadline, so delta suggests a light, sustainable pace you can keep without burnout."
        else:
            hours, pace = 9, "steady"
            reason = "delta suggests a steady pace that balances real progress with your other commitments."

        return {
            "urgency_level": urgency,
            "recommended_hours_per_week": hours,
            "pace": pace,
            "pace_reason": reason,
        }

    def _fill_flexible_defaults(self, user_id: str, profile: dict) -> dict:
        updates = {}
        if not profile.get("target_role") and profile.get("goal_direction"):
            updates["target_role"] = profile["goal_direction"]
        if not profile.get("past_experience"):
            if profile.get("no_experience_yet") or str(profile.get("has_resume", "")).lower() == "false":
                updates["past_experience"] = "No formal projects or work experience yet. delta should begin with beginner-friendly proof building."
            elif profile.get("projects"):
                updates["past_experience"] = "; ".join(str(item) for item in profile.get("projects", [])[:5])
        if not profile.get("skills"):
            updates["skills"] = ["Exploring"]
        if not profile.get("career_goals") and profile.get("goal_direction"):
            updates["career_goals"] = [profile["goal_direction"]]

        # delta suggests pace + weekly hours from the joining story. If the user never
        # stated their own hours, adopt the suggestion as their working hours_per_week.
        suggestion = self._suggest_pace(profile)
        updates["recommended_hours_per_week"] = suggestion["recommended_hours_per_week"]
        updates["pace"] = suggestion["pace"]
        updates["pace_reason"] = suggestion["pace_reason"]
        if not profile.get("urgency_level"):
            updates["urgency_level"] = suggestion["urgency_level"]
        if not profile.get("hours_per_week"):
            updates["hours_per_week"] = suggestion["recommended_hours_per_week"]

        if updates:
            return save_profile(user_id, updates)
        return profile

    def _heuristic_extract_from_conversation(self, conversation: list[dict]) -> dict:
        text = "\n".join(m.get("content", "") for m in conversation if m.get("role") == "user")
        lowered = text.lower()
        extracted: dict[str, Any] = {}

        first_user = next((m.get("content", "") for m in conversation if m.get("role") == "user"), "")
        if first_user:
            extracted["personal_introduction"] = first_user[:1200]

        if "no resume" in lowered or "dont have any resume" in lowered or "don't have any resume" in lowered:
            extracted["has_resume"] = False
        if "drop" in lowered and "college" in lowered:
            extracted["current_status"] = "dropped_out"
            extracted["education_stage"] = "Dropped out of college"
            extracted["study_year"] = "Dropped out of college"
        elif "school" in lowered:
            extracted["current_status"] = "school"
            extracted["education_stage"] = "School student"

        if "video edit" in lowered or "video editing" in lowered or "davinci" in lowered or "resolve" in lowered:
            extracted["target_role"] = "Video Editor"
            extracted["goal_direction"] = "Build a future in video editing"
            extracted["target_industries"] = ["Content creation", "Social media", "Video production"]
            extracted["skills"] = ["Instagram content editing", "DaVinci Resolve"]
            extracted["career_goals"] = ["Build a future in video editing"]
            extracted["learning_style"] = "practical"
            extracted["preferred_content_types"] = ["projects", "videos"]

        if "instagram" in lowered or "posts" in lowered:
            extracted["past_experience"] = "Created Instagram posts for personal or random Instagram pages."
            extracted["projects"] = ["Instagram post edits"]
            extracted["no_experience_yet"] = False
        elif extracted.get("has_resume") is False:
            extracted["no_experience_yet"] = True

        hours_match = re.search(r"\b(\d{1,2})\s*(?:hours|hrs|h)\b", lowered)
        if hours_match:
            extracted["hours_per_week"] = int(hours_match.group(1))
        elif "full time" in lowered:
            extracted["hours_per_week"] = 25
        elif "part time" in lowered:
            extracted["hours_per_week"] = 10

        return {key: value for key, value in extracted.items() if value not in ("", [], None)}

    def _safe_generate_json(self, prompt: str, conversation: list[dict]) -> dict:
        try:
            extracted = generate_json(prompt, model=INTAKE_CHAT_MODEL)
            if isinstance(extracted, dict) and extracted:
                return extracted
        except Exception as exc:
            logger.warning(f"AI extraction failed; using heuristic intake extraction: {exc}")
        return self._heuristic_extract_from_conversation(conversation)

    def _safe_generate_text(self, prompt: str, fallback: str, temperature: float = 0.6, max_tokens: int = 2000) -> str:
        try:
            text = generate_response(prompt, temperature=temperature, max_tokens=max_tokens, model=INTAKE_CHAT_MODEL)
            return text.strip() or fallback
        except Exception as exc:
            logger.warning(f"AI text generation failed; using fallback text: {exc}")
            return fallback

    def _fallback_next_question(self, missing_fields: list[str], profile: dict) -> str:
        missing = set(missing_fields or [])
        if "name" in missing:
            return "What should I call you?"
        if "education_stage" in missing:
            return "What is your current stage right now: school, college, dropped out, graduated, working, or something else?"
        if "goal_direction" in missing:
            return "What direction do you want delta to help you build toward, even if you do not know the exact job title yet?"
        if "hours_per_week" in missing:
            return "How many hours per week can you realistically give to this plan?"
        if "learning_style" in missing:
            return "Do you learn better by watching, reading, building, practicing, or a mix?"
        if not profile.get("skills") and not profile.get("projects"):
            return "What have you tried so far, even casually, and what tool or skill are you learning right now?"
        # Facts are covered — ask about genuine goals/ambitions, which a resume can't capture.
        if not profile.get("career_goals"):
            return "In your own words, what is the main goal you want delta to help you reach?"
        return "What is driving you toward this, and what would success look like for you a year from now?"

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
            "Hi, I am delta's intake advisor. Before the resume, give me a small introduction in your own words: "
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
        extracted = self._safe_generate_json(EXTRACT_PROMPT.format(conversation=conv_text), conversation)
        if isinstance(extracted, dict) and extracted:
            if not extracted.get("personal_introduction"):
                first_user = next((m["content"] for m in conversation if m.get("role") == "user"), "")
                if first_user:
                    extracted["personal_introduction"] = first_user[:1200]
            profile_after_save = save_profile(user_id, extracted)
            self._enrich_profile_context(user_id, profile_after_save)
            logger.info(f"Extracted {list(extracted.keys())} for user {user_id}")

        # ── 3. Check review readiness ─────────────────────────────────────────
        profile = load_profile(user_id)
        profile = self._fill_flexible_defaults(user_id, profile)
        filled_required = [f for f in PROFILE_REVIEW_FIELDS if profile.get(f)]
        ready_for_review, confidence, missing_required = self._review_readiness(profile, session.current_round)

        session.confidence_score = confidence
        session.gaps_filled = len(filled_required)
        session.gaps_total = len(PROFILE_REVIEW_FIELDS)

        is_complete = ready_for_review or session.current_round >= 10

        # ── 4a. Review path ───────────────────────────────────────────────────
        if is_complete:
            session.status = "review"

            save_profile(user_id, {
                "profile_review_pending": True,
                "onboarding_complete": False,
                "confidence_score": confidence,
            })

            profile_ctx = profile_as_context_string(user_id)
            completion_msg = self._safe_generate_text(
                COMPLETION_PROMPT.format(profile_context=profile_ctx),
                "Your profile draft is ready. Review the details once, edit anything that feels wrong, and then delta can build your roadmap from this.",
                temperature=0.6,
                max_tokens=2000
            )
            conversation.append({"role": "assistant", "content": completion_msg, "round": session.current_round})
            session.conversation_log = json.dumps(conversation)

            # Sync to DB user record
            self._sync_profile_to_db(db, user_id, profile)
            db.commit()

            return {
                "status": "review_required",
                "completed": False,
                "review_required": True,
                "confidence_score": confidence,
                "message": completion_msg,
                "next_question": None,
                "filled_fields": filled_required,
                "missing_fields": missing_required,
                "profile": profile,
            }

        # ── 4b. Ask next question ─────────────────────────────────────────────
        profile_ctx = profile_as_context_string(user_id) or "No profile data yet."
        next_q = self._safe_generate_text(
            NEXT_QUESTION_PROMPT.format(
                profile_context=profile_ctx,
                missing_fields=", ".join(missing_required) or "none critical",
                conversation=conv_text[-3000:]  # last 3000 chars
            ),
            self._fallback_next_question(missing_required, profile),
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
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                if profile.get("name"):
                    user.name = profile["name"]
                if profile.get("target_role"):
                    user.target_role = profile["target_role"]
                elif profile.get("goal_direction"):
                    user.target_role = profile["goal_direction"]
                if profile.get("current_role"):
                    user.current_role = profile["current_role"]
                elif profile.get("current_status") or profile.get("education_stage"):
                    user.current_role = profile.get("education_stage") or profile.get("current_status")
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

Extract career profile information from this resume and return valid JSON.

CRITICAL RULES:
- Only extract facts that are ACTUALLY written in the resume text below.
- NEVER guess, infer, or invent an exam, a timeline, a career goal, or an industry that is not clearly stated.
- If a field is not present in the resume, OMIT it entirely (do not output a placeholder or a guess).
- Resumes do not contain competitive exams (UPSC, GATE, etc.) or planning timelines — never add these.

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
  "phone_number": "string",
  "linkedin_url": "string",
  "github_url": "string",
  "portfolio_url": "string",
  "career_goals": ["inferred from objective/summary section"],
  "resume_text": "first 2000 chars of raw resume for context"
}}

Return ONLY the JSON object."""

        extracted = {}
        try:
            generated = generate_json(prompt, temperature=0.1, model=INTAKE_RESUME_MODEL)
            if isinstance(generated, dict):
                extracted = generated
        except Exception as exc:
            logger.warning(f"Resume AI extraction failed; using empty fallback: {exc}")
        if isinstance(extracted, dict) and extracted:
            # The user literally uploaded a resume — record that fact.
            extracted["has_resume"] = True
            # Guard against hallucinated exam / planning-horizon fields: a resume never
            # contains a competitive exam or a planning timeline, so drop any the model
            # invented unless the keyword genuinely appears in the resume text.
            resume_lower = resume_text.lower()
            exam_keywords = ("upsc", "gpsc", "gate", "cat", "gre", "ielts", "toefl", "civil services")
            if extracted.get("target_exam") and not any(k in resume_lower for k in exam_keywords):
                for fld in ("target_exam", "target_attempt", "exam_goal_detail", "known_exam_dates"):
                    extracted.pop(fld, None)
            for fld in ("planning_horizon_years", "planning_horizon_months", "inferred_planning_reason"):
                extracted.pop(fld, None)
            extracted["resume_text"] = resume_text[:3000]
            profile_after_save = save_profile(user_id, extracted)
            self._enrich_profile_context(user_id, profile_after_save)

            # Update session conversation
            session = db.query(IngestionSession).filter(IngestionSession.id == session_id).first()
            if session:
                conv = json.loads(session.conversation_log or "[]")
                summary_fields = [k for k in extracted if k != "resume_text"]
                system_note = f"[Resume analyzed — extracted: {', '.join(summary_fields)}]"
                conv.append({"role": "system_note", "content": system_note})

                profile = load_profile(user_id)
                profile = self._fill_flexible_defaults(user_id, profile)
                filled_required = [f for f in PROFILE_REVIEW_FIELDS if profile.get(f)]
                ready_for_review, confidence, missing = self._review_readiness(profile, session.current_round)
                session.confidence_score = confidence
                session.gaps_filled = len(filled_required)
                session.gaps_total = len(PROFILE_REVIEW_FIELDS)
                # Do not let a rich resume skip the goals/ambitions conversation —
                # require the minimum answer rounds enforced by _review_readiness.
                is_complete = ready_for_review

                if is_complete:
                    session.status = "review"

                    save_profile(user_id, {
                        "profile_review_pending": True,
                        "onboarding_complete": False,
                        "confidence_score": confidence,
                    })

                    profile_ctx = profile_as_context_string(user_id)
                    completion_msg = self._safe_generate_text(
                        COMPLETION_PROMPT.format(profile_context=profile_ctx),
                        "Your profile draft is ready. Review the details once, edit anything that feels wrong, and then delta can build your roadmap from this.",
                        temperature=0.6,
                        max_tokens=2000
                    )
                    conv.append({"role": "assistant", "content": completion_msg})
                    session.conversation_log = json.dumps(conv)

                    self._sync_profile_to_db(db, user_id, profile)
                    db.commit()

                    return {
                        "success": True,
                        "status": "review_required",
                        "completed": False,
                        "review_required": True,
                        "extracted_fields": summary_fields,
                        "follow_up": None,
                        "message": completion_msg,
                        "confidence_score": confidence,
                        "filled_fields": filled_required,
                        "missing_fields": missing,
                        "profile": profile,
                    }
                else:
                    # Generate follow-up after resume
                    profile_ctx = profile_as_context_string(user_id)
                    follow_up = self._safe_generate_text(
                        NEXT_QUESTION_PROMPT.format(
                            profile_context=profile_ctx,
                            missing_fields=", ".join(missing) or "none",
                            conversation="\n".join(
                                f"{'Advisor' if m['role'] == 'assistant' else 'User'}: {m['content']}"
                                for m in conv if m["role"] in ("assistant", "user")
                            )[-2000:]
                        ),
                        self._fallback_next_question(missing, profile),
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
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id
        ).order_by(IngestionSession.created_at.desc()).first()

        profile = load_profile(user_id)
        filled = [f for f in PROFILE_REVIEW_FIELDS if profile.get(f)]

        return {
            "has_active_session": session is not None and session.status in {"active", "review"},
            "onboarding_complete": profile.get("onboarding_complete", False),
            "profile_review_pending": profile.get("profile_review_pending", False),
            "confidence_score": profile.get("confidence_score", len(filled) / len(PROFILE_REVIEW_FIELDS)),
            "filled_fields": filled,
            "missing_fields": self._profile_review_missing_fields(profile),
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
        session = db.query(IngestionSession).filter(
            IngestionSession.user_id == user_id,
            IngestionSession.status.in_(["active", "review"])
        ).order_by(IngestionSession.created_at.desc()).first()

        if session:
            session.status = "completed"
            session.completed_at = datetime.datetime.utcnow()
            db.commit()

        profile = load_profile(user_id)
        save_profile(user_id, {"onboarding_complete": True, "profile_review_pending": False})
        self._sync_profile_to_db(db, user_id, profile)

        return {"status": "completed", "profile": profile}


# ── Singleton instance ────────────────────────────────────────────────────────
engine = IngestionEngineV2()
