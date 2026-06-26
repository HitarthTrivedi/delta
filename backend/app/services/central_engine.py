"""Central career engine for delta's personalized operating system."""
import datetime
import json
import uuid

from sqlalchemy.orm import Session

from app.models import (
    CareerMemoryProfile,
    IngestionSession,
    JourneyEvent,
    MarketSnapshot,
    PersonalizationProfile,
    RoadmapState,
    SemanticNodeModel,
    SkillNode,
    TensionNodeModel,
    User,
)
from app.services.brief_generator import generate_weekly_brief
from app.services.domain_packs import infer_domain_pack
from app.services.market_pulse import get_market_snapshot
from app.services.memory_graph import MemoryGraph
from app.services.memory_consolidation import consolidate_user_memory
from app.services.opportunity_adapters import collect_opportunities, summarize_opportunity_signals
from app.services.portfolio_engine import assess_portfolio
from app.services.project_engine import recommend_proof_projects


def _as_json(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _dump(value):
    return json.dumps(value, ensure_ascii=True)


def _event_json(event: JourneyEvent, field: str, fallback):
    return _as_json(getattr(event, field, None), fallback)


def _valid_weekly_cycle_events(db: Session, user_id: str) -> list[JourneyEvent]:
    """Only count explicit, validated week advances. Old refresh-created cycles are ignored."""
    events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type == "weekly_cycle_completed"
    ).order_by(JourneyEvent.created_at.asc()).all()
    valid_events = []
    for event in events:
        impact = _event_json(event, "impact", {})
        evidence = _event_json(event, "evidence", {})
        if impact.get("advance_approved") is True or evidence.get("completed_task_count"):
            valid_events.append(event)
    return valid_events


def _norm_skill(value: str) -> str:
    return " ".join(str(value or "").lower().replace("&", " ").replace("/", " ").replace("-", " ").split())


def _profile_skills(profile: dict) -> list[str]:
    skills = profile.get("skills") or []
    if isinstance(skills, str):
        skills = [part.strip() for part in skills.split(",") if part.strip()]
    return [str(skill).strip() for skill in skills if str(skill).strip()]


def _sync_profile_skills_to_db(db: Session, user: User) -> list[SkillNode]:
    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
    existing = {_norm_skill(skill.name): skill for skill in skills}
    try:
        from app.services.profile_store import load_profile
        profile = load_profile(user.id)
    except Exception:
        profile = {}

    profile_skills = _profile_skills(profile)
    if not profile_skills:
        return skills

    experience = _norm_skill(profile.get("experience_level") or "")
    base_proficiency = 6 if experience in {"intermediate", "advanced"} else 4
    changed = False
    for skill_name in profile_skills[:40]:
        key = _norm_skill(skill_name)
        if not key:
            continue
        existing_skill = existing.get(key)
        if existing_skill:
            if existing_skill.proficiency < base_proficiency:
                existing_skill.proficiency = base_proficiency
                existing_skill.evidence_type = existing_skill.evidence_type or "resume_profile"
                existing_skill.evidence_weight = max(existing_skill.evidence_weight or 0, 0.65)
                changed = True
            continue
        new_skill = SkillNode(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=skill_name,
            category="resume",
            proficiency=base_proficiency,
            evidence_type="resume_profile",
            evidence_weight=0.65,
        )
        db.add(new_skill)
        skills.append(new_skill)
        existing[key] = new_skill
        changed = True

    if changed:
        db.commit()
        skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
    return skills


def _profile_text(profile: dict, skills: list[SkillNode], user: User) -> str:
    return " ".join([
        str(profile.get("target_role", "")),
        str(profile.get("major", "")),
        str(profile.get("past_experience", "")),
        str(profile.get("projects", "")),
        str(profile.get("resume_text", "")),
        str(profile.get("career_goals", "")),
        " ".join(_profile_skills(profile)),
        " ".join(skill.name for skill in skills),
        str(user.target_role or ""),
    ]).lower()


def _profile_domain(profile: dict, skills: list[SkillNode], user: User) -> str:
    text = _profile_text(profile, skills, user)
    domains = [
        ("ai_agents", ["multi-agent", "multi agent", "agentic rag", "adversarial ai", "llm orchestration", "long-term memory", "agent routing", "alpha.kore"]),
        ("commerce", ["commerce", "finance", "accounting", "business", "marketing", "economics", "stock", "tax", "audit", "sales"]),
        ("mechanical", ["mechanical", "cad", "solidworks", "autocad", "thermodynamics", "manufacturing", "robotics", "ansys"]),
        ("electrical", ["electrical", "electronics", "circuit", "pcb", "arduino", "matlab", "power systems", "embedded", "iot"]),
        ("arts", ["arts", "design", "fine arts", "illustration", "animation", "writing", "music", "film", "portfolio"]),
    ]
    scores = {
        domain: sum(1 for marker in markers if marker in text)
        for domain, markers in domains
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def _has_prior_profile_depth(profile: dict, skills: list[SkillNode], user: User) -> bool:
    profile_text = _profile_text(profile, skills, user)
    advanced_markers = [
        "advanced", "intermediate", "production", "deployed", "published", "pypi",
        "downloads", "multi-agent", "multi agent", "agentic rag", "llm orchestration",
        "long-term memory", "weighted scoring", "benchmark", "evaluation", "alpha.kore",
        "lazycook", "github", "open source",
    ]
    return any(marker in profile_text for marker in advanced_markers) or len(_profile_skills(profile)) >= 5


def _profile_project_label(profile: dict) -> str:
    text = " ".join([
        str(profile.get("past_experience", "")),
        str(profile.get("projects", "")),
        str(profile.get("resume_text", "")),
    ]).lower()
    if "alpha.kore" in text or "alpha kore" in text:
        return "Alpha.Kore"
    if "lazycook" in text or "lazy cook" in text:
        return "LazyCook"
    if "agentic" in text or "multi-agent" in text or "multi agent" in text:
        return "your agentic AI system"
    if "pypi" in text or "package" in text:
        return "your shipped package"
    return "your strongest existing project"


def _planning_horizon_months(profile: dict) -> int:
    try:
        months = int(profile.get("planning_horizon_months") or 0)
    except Exception:
        months = 0
    if months <= 0:
        try:
            months = int(profile.get("timeline_months") or 0)
        except Exception:
            months = 0
    return months or 12


def _monthly_progress_counts(db: Session, user_id: str) -> dict:
    today = datetime.date.today()
    month_start = datetime.datetime(today.year, today.month, 1)
    events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type.in_(["weekly_task_completed", "weekly_task_skipped"]),
        JourneyEvent.created_at >= month_start,
    ).all()
    return {
        "completed": len([event for event in events if event.event_type == "weekly_task_completed"]),
        "skipped": len([event for event in events if event.event_type == "weekly_task_skipped"]),
        "accepted": len(events),
    }


def _should_assign_break_week(db: Session, user: User, profile: dict, roadmap: "RoadmapState | None" = None) -> bool:
    # In DEV_MODE the pacing guards are off so the plan can be iterated freely while testing.
    import os as _os
    if _os.getenv("DEV_MODE", "false").lower() in {"true", "1", "yes"}:
        return False
    # Never stack break weeks. If the current week is already a break week, or one was
    # assigned in the last 21 days, do not assign another — otherwise the monthly counter
    # (which keeps counting completed break-week tasks) traps the user in an endless loop.
    if roadmap:
        weekly_focus = _as_json(roadmap.weekly_focus, {})
        if (weekly_focus.get("phase_name") or "") == "Break week" or weekly_focus.get("is_break_week"):
            return False
        destination = _as_json(roadmap.destination, {})
        last_break = destination.get("last_break_week_at")
        if last_break:
            try:
                last_dt = datetime.datetime.fromisoformat(last_break)
                if (datetime.datetime.utcnow() - last_dt).days < 21:
                    return False
            except Exception:
                pass

    progress = _monthly_progress_counts(db, user.id)
    accepted = progress["accepted"]
    hours = user.hours_per_week or profile.get("hours_per_week") or 10
    try:
        hours = int(hours)
    except Exception:
        hours = 10
    monthly_target = 4 if hours <= 6 else 6 if hours <= 12 else 8
    return accepted >= monthly_target and progress["completed"] >= max(2, monthly_target // 2)


def _break_week_actions(profile: dict, user: User, reason: str = "") -> list[dict]:
    project_label = _profile_project_label(profile)
    return [{
        "id": "break-week-maintenance",
        "node_id": "recovery-and-review",
        "type": "practice",
        "title": "Break week: review and recover",
        "skill": "Sustainable execution",
        "description": (
            f"No new heavy project this week. Spend one short 60-90 minute block reviewing {project_label}, "
            "write what you finished this month, clean one README or task note, and then rest. "
            "Ask Agent 2 to add work only if you genuinely want a challenge."
        ),
        "why_now": reason or "You have already accepted enough work this month, so delta is protecting your pace.",
        "source": "delta monthly pacing guard",
        "url": "",
        "prior_exposure": True,
    }]


LEETCODE_SEQUENCE = [
    ("Arrays and Hashing", "Solve 4 problems: 2 easy + 2 medium. Focus on frequency maps, sets, and duplicate detection."),
    ("Two Pointers", "Solve 3 problems: valid palindrome style, sorted two-sum style, and container/window boundary reasoning."),
    ("Sliding Window", "Solve 3 problems: fixed window, variable window, and longest substring/pattern tracking."),
    ("Stack", "Solve 3 problems: valid parentheses, monotonic stack, and expression/min-stack style reasoning."),
    ("Binary Search", "Solve 4 problems: classic search, lower/upper bound, search rotated array, and answer-space binary search."),
    ("Linked List", "Solve 3 problems: reverse, fast/slow pointer, and merge/reorder style."),
    ("Trees", "Solve 4 problems: DFS traversal, BFS level order, path/depth, and lowest common ancestor style."),
    ("Heap / Priority Queue", "Solve 3 problems: top-k, streaming median/kth, and scheduling/merge pattern."),
    ("Backtracking", "Solve 3 problems: subsets, permutations/combinations, and constraint pruning."),
    ("Graphs", "Solve 4 problems: BFS/DFS traversal, connected components, topological sort, and shortest path basics."),
    ("Dynamic Programming 1D", "Solve 3 problems: climbing/house-robber, coin/change style, and LIS-style recurrence."),
    ("Dynamic Programming 2D", "Solve 3 problems: grid path, LCS/edit-distance style, and knapsack-style state design."),
]


def _week_number_from_user(user: User) -> int:
    if not user.created_at:
        return 1
    elapsed_days = (datetime.datetime.utcnow() - user.created_at).days
    return max(1, (elapsed_days // 7) + 1)


def _recurring_habit_actions(profile: dict, skills: list[SkillNode], user: User) -> list[dict]:
    domain = _profile_domain(profile, skills, user)
    week_number = _week_number_from_user(user)
    actions = []
    if domain in {"ai_agents", "general"} or "software" in str(user.target_role or "").lower() or "engineer" in str(user.target_role or "").lower():
        topic, detail = LEETCODE_SEQUENCE[(week_number - 1) % len(LEETCODE_SEQUENCE)]
        actions.append({
            "id": f"recurring-leetcode-week-{week_number}-{topic.lower().replace(' ', '-').replace('/', '-')}",
            "node_id": "recurring-leetcode",
            "type": "practice",
            "title": f"LeetCode habit: {topic}",
            "skill": "DSA interview consistency",
            "description": (
                f"This is a recurring weekly habit, not a one-time course. {detail} "
                "Write down the pattern, the mistake you made, and one reusable template."
            ),
            "why_now": "Interview readiness compounds through small weekly practice, not short bursts.",
            "source": "LeetCode topic rotation",
            "url": "https://leetcode.com/problemset/",
            "cadence": "weekly",
            "recurring": True,
        })
    return actions


def _trend_response_actions(profile: dict, skills: list[SkillNode], user: User, market: MarketSnapshot) -> list[dict]:
    raw = _as_json(market.raw_data, {})
    emerging = _as_json(market.emerging_skills, [])
    demanded = _as_json(market.top_demanded_skills, [])
    project_patterns = raw.get("project_patterns") or []
    market_warnings = raw.get("market_warnings") or []
    trend = (emerging or demanded or ["market-backed proof"])[0]
    pattern = project_patterns[0] if project_patterns else f"Build a small proof using {trend} and explain the tradeoffs."
    warning = market_warnings[0] if market_warnings else "Make the proof measurable, deployed or documented, and easy for a recruiter to inspect."
    return [{
        "id": f"trend-proof-{str(trend).lower().replace(' ', '-').replace('/', '-')[:40]}",
        "node_id": "market-trend-response",
        "type": "project",
        "title": f"Trend proof: {trend}",
        "skill": str(trend).title(),
        "description": (
            f"Create one small resume-visible proof responding to this market signal: {pattern} "
            f"Add a README section explaining why it matters now. Hiring warning to address: {warning}"
        ),
        "why_now": "delta uses live/search-backed market signals so your roadmap keeps adapting to future demand.",
        "source": raw.get("source") or market.target_role or "delta market pulse",
        "url": "",
        "cadence": "trend",
    }]


def _long_horizon_plan(profile: dict, skills: list[SkillNode], user: User, market: MarketSnapshot) -> dict:
    months = _planning_horizon_months(profile)
    domain = _profile_domain(profile, skills, user)
    raw = _as_json(market.raw_data, {})
    demanded = _as_json(market.top_demanded_skills, [])[:6]
    emerging = _as_json(market.emerging_skills, [])[:5]
    if domain == "ai_agents":
        lanes = [
            {"name": "Interview consistency", "cadence": "Every week", "rule": "3-4 LeetCode problems from the current topic rotation."},
            {"name": "AI engineering proof", "cadence": "Every 2-3 weeks", "rule": "Ship or upgrade one eval, RAG, agent, deployment, or observability artifact."},
            {"name": "Market trend response", "cadence": "Monthly", "rule": f"Pick one emerging signal from {', '.join(emerging or demanded or ['current hiring trends'])} and turn it into proof."},
            {"name": "Resume/story polish", "cadence": "Monthly", "rule": "Convert completed work into one strong resume bullet, README section, or portfolio note."},
        ]
    else:
        lanes = [
            {"name": "Core skill practice", "cadence": "Every week", "rule": "Do one repeated practice block matched to the target domain."},
            {"name": "Portfolio proof", "cadence": "Every 2-3 weeks", "rule": "Create or improve one inspectable project/case study/simulation/report."},
            {"name": "Market trend response", "cadence": "Monthly", "rule": f"Use one trend from {', '.join(emerging or demanded or ['current market signals'])}."},
            {"name": "Communication polish", "cadence": "Monthly", "rule": "Write a clear proof note showing problem, method, result, and tradeoff."},
        ]
    return {
        "horizon_months": months,
        "intent": "Long-scale career improvement plan with recurring habits, market tracking, and proof-building.",
        "lanes": lanes,
        "market_signals": {
            "demanded_skills": demanded,
            "emerging_skills": emerging,
            "project_patterns": (raw.get("project_patterns") or [])[:4],
            "sources": (raw.get("search_sources") or raw.get("sources") or [])[:6],
        },
    }


def _domain_proof_actions(profile: dict, skills: list[SkillNode], user: User, db: Session) -> list[dict]:
    domain = _profile_domain(profile, skills, user)
    project_context = profile.get("past_experience") or "your existing work"
    project_label = _profile_project_label(profile)
    templates = {
        "ai_agents": [
            {
                "id": "task-agent-eval-harness",
                "node_id": "advanced-agent-evaluation",
                "type": "project",
                "title": f"Build an eval harness for {project_label}",
                "skill": "Agent Evaluation Engineering",
                "description": (
                    f"Use {project_label}. Create 12 realistic prompts across normal use, ambiguity, missing context, and adversarial input. "
                    "Score each run on task success, factual grounding, tool choice, memory use, and formatting. Ship a README table with pass/fail results and one code or prompt fix."
                ),
                "why_now": "Your resume already shows advanced AI work, so the proof should measure reliability like an engineer, not teach basics.",
                "source": "Your existing resume/project evidence",
                "url": "",
                "prior_exposure": True,
            },
            {
                "id": "task-agent-redteam-regression",
                "node_id": "advanced-adversarial-ai",
                "type": "project",
                "title": f"Create a red-team regression suite for {project_label}",
                "skill": "Adversarial AI Architecture",
                "description": (
                    "Write 8 attack or edge-case prompts: prompt injection, conflicting instructions, fake tool output, private-data request, hallucinated citation, malformed JSON, vague user goal, and impossible deadline. "
                    "Record the failure mode, add one guardrail/scoring rule, and rerun the suite to show before/after behavior."
                ),
                "why_now": "This turns your existing agent work into a security and reliability signal.",
                "source": "OWASP LLM risk style practice",
                "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
                "prior_exposure": True,
            },
            {
                "id": "task-agent-observability",
                "node_id": "advanced-agent-observability",
                "type": "project",
                "title": f"Add an observability note to {project_label}",
                "skill": "AI System Observability",
                "description": (
                    "Instrument one workflow with a simple trace log: user intent, retrieved context, tool decision, model response, validation result, and final status. "
                    "Publish a short architecture note explaining two failures the trace makes easier to debug."
                ),
                "why_now": "Advanced projects become stronger when you can explain and debug their behavior.",
                "source": "Your existing codebase or project notes",
                "url": "",
                "prior_exposure": True,
            },
        ],
        "commerce": [
            {
                "id": "task-commerce-dashboard",
                "node_id": "commerce-analysis-proof",
                "type": "project",
                "title": "Build a financial decision dashboard from a real dataset",
                "skill": "Financial Analysis",
                "description": f"Use {project_context}. Create a spreadsheet or BI dashboard with revenue, cost, margin, and one recommendation backed by numbers.",
                "source": "Your existing commerce/accounting context",
                "url": "",
                "prior_exposure": True,
            },
            {
                "id": "task-commerce-case-study",
                "node_id": "commerce-case-proof",
                "type": "project",
                "title": "Write a one-page business case study",
                "skill": "Business Strategy",
                "description": "Pick one company, identify a problem, show 3 data points, and write a clear recommendation with risks.",
                "source": "Public annual reports / company filings",
                "url": "",
                "prior_exposure": True,
            },
        ],
        "mechanical": [
            {
                "id": "task-mech-cad-redesign",
                "node_id": "mechanical-cad-proof",
                "type": "project",
                "title": "Redesign one mechanical part with a trade-off note",
                "skill": "CAD / Mechanical Design",
                "description": f"Use {project_context}. Model or sketch one part, improve weight/strength/manufacturability, and explain the trade-off.",
                "source": "Your existing mechanical/CAD work",
                "url": "",
                "prior_exposure": True,
            },
            {
                "id": "task-mech-analysis",
                "node_id": "mechanical-analysis-proof",
                "type": "project",
                "title": "Create a simple analysis report for a mechanism",
                "skill": "Mechanical Analysis",
                "description": "Pick a mechanism, calculate one load/speed/thermal constraint, and write what design choice follows from it.",
                "source": "Engineering notes / CAD model",
                "url": "",
                "prior_exposure": True,
            },
        ],
        "electrical": [
            {
                "id": "task-electrical-sim",
                "node_id": "electrical-simulation-proof",
                "type": "project",
                "title": "Simulate and explain one circuit behavior",
                "skill": "Circuit Analysis",
                "description": f"Use {project_context}. Simulate one circuit, capture input/output behavior, and explain one failure or limit.",
                "source": "Falstad / LTspice / existing lab work",
                "url": "https://www.falstad.com/circuit/",
                "prior_exposure": True,
            },
            {
                "id": "task-electrical-test-plan",
                "node_id": "electrical-test-proof",
                "type": "project",
                "title": "Write a test plan for one electrical/IoT system",
                "skill": "Testing and Debugging",
                "description": "List 6 tests, expected readings, possible faults, and how you would debug one failed test.",
                "source": "Your existing electronics/IoT work",
                "url": "",
                "prior_exposure": True,
            },
        ],
        "arts": [
            {
                "id": "task-arts-portfolio-case",
                "node_id": "arts-portfolio-proof",
                "type": "project",
                "title": "Turn one artwork into a portfolio case study",
                "skill": "Portfolio Development",
                "description": f"Use {project_context}. Show goal, references, drafts, final piece, and what you changed after critique.",
                "source": "Your existing arts/design work",
                "url": "",
                "prior_exposure": True,
            },
            {
                "id": "task-arts-style-study",
                "node_id": "arts-style-proof",
                "type": "project",
                "title": "Create a focused style study with critique notes",
                "skill": "Creative Direction",
                "description": "Choose one style, make a small piece, then write 5 critique notes and 3 improvements for the next version.",
                "source": "Portfolio/reference study",
                "url": "",
                "prior_exposure": True,
            },
        ],
    }

    # Fetch completed/skipped tasks from journey events
    completed_or_skipped = set()
    try:
        events = db.query(JourneyEvent).filter(
            JourneyEvent.user_id == user.id,
            JourneyEvent.event_type.in_(["weekly_task_completed", "weekly_task_skipped"])
        ).all()
        for e in events:
            evidence = _as_json(e.evidence, {})
            e_id = evidence.get("id") or evidence.get("title")
            if e_id:
                completed_or_skipped.add(str(e_id).strip().lower())
    except Exception as exc:
        print(f"Error querying task progress for proof sprint: {exc}")

    domain_templates = templates.get(domain)
    if domain_templates is None:
        domain_templates = [
            {
                "id": "task-domain-proof",
                "node_id": "general-proof",
                "type": "project",
                "title": "Build one proof that is beyond your resume",
                "skill": "Applied Proof",
                "description": f"Use {project_context}. Pick one prior skill, make a stronger example, and write what is better than your old work.",
                "source": "Your existing profile/resume work",
                "url": "",
                "prior_exposure": True,
            },
            {
                "id": "task-domain-review",
                "node_id": "general-review",
                "type": "project",
                "title": "Write a short improvement report on your previous work",
                "skill": "Reflection and Upgrade",
                "description": "Choose one old project/work sample, list 3 weaknesses, and implement or describe one concrete improvement.",
                "source": "Your existing profile/resume work",
                "url": "",
                "prior_exposure": True,
            },
        ]

    filtered_actions = []
    for action in domain_templates:
        action_id = action.get("id") or action.get("title")
        if str(action_id).strip().lower() not in completed_or_skipped:
            filtered_actions.append(action)
    return filtered_actions


def _event_block_actions(events: list[dict]) -> list[dict]:
    event = events[0] if events else {}
    kind = str(event.get("kind") or "").lower()
    is_exam = kind == "exam" or "exam" in str(event.get("title", "")).lower()
    title = "Exam-only study week" if is_exam else "Blocked-event light week"
    description = (
        "Pause delta projects and courses for this week. Study for the examination: list syllabus topics, revise weak areas, solve past questions, and keep a mistake log."
        if is_exam
        else "Do not assign heavy delta work this week. Keep only a light check-in or review task because the user has a blocked personal event."
    )
    return [{
        "id": f"event-block-{event.get('id', 'active')}",
        "node_id": "active-event-block",
        "type": "practice",
        "title": title,
        "skill": "Schedule-aware planning",
        "description": description,
        "source": f"Agent 2 upcoming event: {event.get('title', 'blocked event')}",
        "url": "",
        "due_date": event.get("end_date") or event.get("date"),
        "event_context": event,
    }]


def get_or_create_career_memory(db: Session, user: User) -> CareerMemoryProfile:
    memory = db.query(CareerMemoryProfile).filter(CareerMemoryProfile.user_id == user.id).first()
    if memory:
        return memory

    personalization = db.query(PersonalizationProfile).filter(
        PersonalizationProfile.user_id == user.id
    ).first()
    structured = _as_json(personalization.structured_profile if personalization else None, {})
    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()

    memory_payload = build_memory_payload(user, structured, skills)
    memory = CareerMemoryProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        identity=_dump(memory_payload["identity"]),
        ambitions=_dump(memory_payload["ambitions"]),
        capabilities=_dump(memory_payload["capabilities"]),
        constraints=_dump(memory_payload["constraints"]),
        preferences=_dump(memory_payload["preferences"]),
        behavior=_dump(memory_payload["behavior"]),
        evidence=_dump(memory_payload["evidence"]),
        open_questions=_dump(memory_payload["open_questions"]),
        confidence_score=0.62 if structured else 0.45,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def build_memory_payload(user: User, structured: dict, skills: list[SkillNode]) -> dict:
    domain_pack = infer_domain_pack(
        structured.get("target_domain")
        or structured.get("domain")
        or structured.get("ambitions")
        or user.target_role
    )
    # Check if we have the new ingestion maps structure
    identity_ctx = structured.get("identity_context")
    ambition_map = structured.get("ambition_map")
    capability_map = structured.get("capability_map")
    constraint_map = structured.get("constraint_map")
    preference_map = structured.get("preference_map")
    behavior_map = structured.get("motivation_and_risk_map")
    evidence_map = structured.get("evidence_map")

    # 1. Identity context self-healing
    if isinstance(identity_ctx, dict):
        identity_payload = {
            "name": identity_ctx.get("name") or user.name,
            "education_stage": identity_ctx.get("education_stage") or structured.get("current_level") or "Beginner",
            "location": identity_ctx.get("location") or "unknown",
            "language_comfort": identity_ctx.get("language_comfort") or "English",
            "background_summary": identity_ctx.get("background_summary") or f"Early career roadmap targeting {user.target_role or 'software engineering'}.",
            "self_awareness_level": identity_ctx.get("self_awareness_level") or "medium",
            "name_legacy": user.name,
            "email": user.email,
            "current_role": user.current_role,
        }
    else:
        identity_payload = {
            "name": user.name,
            "education_stage": structured.get("current_level") or user.current_role or "Beginner",
            "location": "unknown",
            "language_comfort": "English",
            "background_summary": f"Self-healed profile context for guest user targeting {user.target_role or 'software engineering'}.",
            "self_awareness_level": "medium",
            "name_legacy": user.name,
            "email": user.email,
            "current_role": user.current_role,
        }

    # 2. Ambition map self-healing
    if isinstance(ambition_map, dict):
        ambitions_payload = {
            "long_term_goals": ambition_map.get("long_term_goals") or [structured.get("ambitions") or user.target_role or "Career-ready software professional"],
            "short_term_targets": ambition_map.get("short_term_targets") or ["Master core APIs and build verified portfolio projects"],
            "dream_roles": ambition_map.get("dream_roles") or [user.target_role] if user.target_role else ["Software Engineer"],
            "preferred_industries": ambition_map.get("preferred_industries") or ["Technology"],
            "confidence_level": ambition_map.get("confidence_level") or "medium",
            "target_role": user.target_role,
            "target_domain": domain_pack["id"],
            "domain_label": domain_pack["label"],
            "domain_pack": domain_pack,
            "recommended_starting_phase": structured.get("recommended_starting_phase") or "Phase 1: Foundations",
        }
    else:
        ambitions_payload = {
            "long_term_goals": [structured.get("ambitions") or user.target_role or "Career-ready software professional"],
            "short_term_targets": ["Master core APIs and build verified portfolio projects"],
            "dream_roles": [user.target_role] if user.target_role else ["Software Engineer"],
            "preferred_industries": ["Technology"],
            "confidence_level": "medium",
            "target_role": user.target_role,
            "target_domain": domain_pack["id"],
            "domain_label": domain_pack["label"],
            "domain_pack": domain_pack,
            "recommended_starting_phase": structured.get("recommended_starting_phase") or "Phase 1: Foundations",
        }

    # 3. Capability map self-healing
    tracked_skills = [
        {
            "name": skill.name,
            "category": skill.category,
            "proficiency": skill.proficiency,
            "evidence_type": skill.evidence_type,
            "evidence_url": skill.evidence_url,
            "evidence_weight": skill.evidence_weight,
        }
        for skill in skills
    ]
    if isinstance(capability_map, dict):
        capabilities_payload = {
            "current_skills": capability_map.get("current_skills") or structured.get("extracted_skills") or [s.name for s in skills],
            "skill_depth": capability_map.get("skill_depth") or {s.name: f"Proficiency level {s.proficiency}/10" for s in skills},
            "technical_baseline": capability_map.get("technical_baseline") or "scripting-and-claimed",
            "industry_readiness_score": capability_map.get("industry_readiness_score") or 0.35,
            "identified_gaps": capability_map.get("identified_gaps") or structured.get("gaps_identified") or ["FastAPI", "Docker", "System Design"],
            "domain_skill_taxonomy": domain_pack["skill_taxonomy"],
            "skills": tracked_skills,
        }
    else:
        capabilities_payload = {
            "current_skills": structured.get("extracted_skills") or [s.name for s in skills] or ["Python"],
            "skill_depth": {s.name: f"Proficiency level {s.proficiency}/10" for s in skills} or {"Python": "basics, syntax"},
            "technical_baseline": "scripting-and-claimed",
            "industry_readiness_score": 0.35,
            "identified_gaps": structured.get("gaps_identified") or ["FastAPI", "Docker", "System Design"],
            "domain_skill_taxonomy": domain_pack["skill_taxonomy"],
            "skills": tracked_skills,
        }

    # 4. Constraint map self-healing
    if isinstance(constraint_map, dict):
        constraints_payload = {
            "time_limit": constraint_map.get("time_limit") or f"{user.hours_per_week or 15} hours per week",
            "financial_limits": constraint_map.get("financial_limits") or "none",
            "device_access": constraint_map.get("device_access") or "Standard Laptop",
            "internet_access": constraint_map.get("internet_access") or "Standard Broadband",
            "college_load": constraint_map.get("college_load") or "medium",
            "family_expectations": constraint_map.get("family_expectations") or "none",
            "hours_per_week": user.hours_per_week or 15,
            "known_limits": constraint_map.get("known_limits") or structured.get("constraints") or [f"{user.hours_per_week or 15} hours/week time limit"],
        }
    else:
        constraints_payload = {
            "time_limit": f"{user.hours_per_week or 15} hours per week",
            "financial_limits": "none",
            "device_access": "Standard Laptop",
            "internet_access": "Standard Broadband",
            "college_load": "medium",
            "family_expectations": "none",
            "hours_per_week": user.hours_per_week or 15,
            "known_limits": structured.get("constraints") or [f"{user.hours_per_week or 15} hours/week time limit"],
        }

    # 5. Preference map self-healing
    if isinstance(preference_map, dict):
        preferences_payload = {
            "learning_style": preference_map.get("learning_style") or user.learning_style or structured.get("learning_style") or "hands-on",
            "content_type": preference_map.get("content_type") or structured.get("content_preferences") or ["hands-on projects"],
            "project_taste": preference_map.get("project_taste") or "Backend API systems",
            "communication_tone": preference_map.get("communication_tone") or "encouraging",
            "preferred_proof_types": domain_pack["proof_types"],
        }
    else:
        preferences_payload = {
            "learning_style": user.learning_style or structured.get("learning_style") or "hands-on",
            "content_type": structured.get("content_preferences") or ["hands-on projects"],
            "project_taste": "Backend API systems",
            "communication_tone": "encouraging",
            "preferred_proof_types": domain_pack["proof_types"],
        }

    # 6. Motivation and risk map self-healing
    legacy_behavior = structured.get("behavior") or {}
    if isinstance(behavior_map, dict):
        behavior_payload = {
            "motivation_profile": behavior_map.get("motivation_profile") or "career weight & portfolio proof",
            "procrastination_patterns": behavior_map.get("procrastination_patterns") or ["expected consistency drops during college exams"],
            "risk_flags": behavior_map.get("risk_flags") or legacy_behavior.get("risk_flags") or [],
            "decision_habits": behavior_map.get("decision_habits") or legacy_behavior.get("decision_patterns") or ["methodical planner"],
            "consistency": legacy_behavior.get("consistency", "medium"),
        }
    else:
        behavior_payload = {
            "motivation_profile": "career weight & portfolio proof",
            "procrastination_patterns": ["expected consistency drops during college exams"],
            "risk_flags": legacy_behavior.get("risk_flags") or [],
            "decision_habits": legacy_behavior.get("decision_patterns") or ["methodical planner"],
            "consistency": legacy_behavior.get("consistency", "medium"),
        }

    # 7. Evidence map self-healing
    legacy_evidence = structured.get("evidence") or {}
    if isinstance(evidence_map, dict):
        evidence_payload = {
            "projects": evidence_map.get("projects") or legacy_evidence.get("projects") or [],
            "certificates": evidence_map.get("certificates") or legacy_evidence.get("certifications") or [],
            "github_presence": evidence_map.get("github_presence") or "needs creation",
            "resumes": evidence_map.get("resumes") or [],
            "contests_and_hackathons": evidence_map.get("contests_and_hackathons") or legacy_evidence.get("competitions") or [],
            "writing_and_portfolio": evidence_map.get("writing_and_portfolio") or legacy_evidence.get("portfolio_links") or [],
        }
    else:
        evidence_payload = {
            "projects": legacy_evidence.get("projects") or [],
            "certificates": legacy_evidence.get("certifications") or [],
            "github_presence": "needs creation",
            "resumes": [],
            "contests_and_hackathons": legacy_evidence.get("competitions") or [],
            "writing_and_portfolio": legacy_evidence.get("portfolio_links") or [],
        }

    # 8. Open questions & strategy self-healing
    open_qs = structured.get("open_questions") or _derive_open_questions(user, structured)
    market_search_prompt = structured.get("market_search_prompt") or f"{user.target_role or 'software engineer'} entry level skill demands recruiter trends"
    follow_up_strategy = structured.get("follow_up_question_strategy") or "First probe github repository structure, then verify docker deployment comfort in week 2"

    open_questions_payload = {
        "open_questions": open_qs if isinstance(open_qs, list) else (open_qs.get("open_questions", []) if isinstance(open_qs, dict) else []),
        "market_search_prompt": market_search_prompt,
        "follow_up_question_strategy": follow_up_strategy,
    }

    return {
        "identity": identity_payload,
        "ambitions": ambitions_payload,
        "capabilities": capabilities_payload,
        "constraints": constraints_payload,
        "preferences": preferences_payload,
        "behavior": behavior_payload,
        "evidence": evidence_payload,
        "open_questions": open_questions_payload,
    }


def refresh_career_memory_from_user_state(
    db: Session,
    user: User,
    structured: dict | None = None,
) -> CareerMemoryProfile:
    personalization = db.query(PersonalizationProfile).filter(
        PersonalizationProfile.user_id == user.id
    ).first()
    if structured is None:
        structured = _as_json(personalization.structured_profile if personalization else None, {})

    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
    payload = build_memory_payload(user, structured or {}, skills)
    memory = db.query(CareerMemoryProfile).filter(CareerMemoryProfile.user_id == user.id).first()

    if not memory:
        memory = CareerMemoryProfile(
            id=str(uuid.uuid4()),
            user_id=user.id,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(memory)

    memory.identity = _dump(payload["identity"])
    memory.ambitions = _dump(payload["ambitions"])
    memory.capabilities = _dump(payload["capabilities"])
    memory.constraints = _dump(payload["constraints"])
    memory.preferences = _dump(payload["preferences"])
    memory.behavior = _dump(payload["behavior"])
    memory.evidence = _dump(payload["evidence"])
    memory.open_questions = _dump(payload["open_questions"])
    memory.confidence_score = 0.72 if structured else 0.52
    memory.updated_at = datetime.datetime.utcnow()

    # Synchronize to Semantic Memory Graph to keep the graph in sync
    try:
        from app.services.memory_graph import MemoryGraph
        graph = MemoryGraph.load_from_db(db, user.id)
        if not graph.get_user_root():
            graph.create_user_root_node(user.name, user.email)
        
        # Load from structured/skills updates
        if structured:
            node_type_map = {
                "identity": "identity",
                "ambitions": "ambition",
                "capabilities": "capability",
                "constraints": "constraint",
                "preferences": "preference",
                "behavior": "motivation",
                "evidence": "evidence",
            }
            relation_map = {
                "identity": "INFERRED_AS",
                "ambitions": "STRIVES_FOR",
                "capabilities": "HAS_SKILL",
                "constraints": "CONSTRAINED_BY",
                "preferences": "PREFERS",
                "behavior": "MOTIVATED_BY",
                "evidence": "EVIDENCED_BY",
            }
            for node_type, details in payload.items():
                graph_node_type = node_type_map.get(node_type)
                if graph_node_type:
                    if isinstance(details, dict):
                        for k, v in details.items():
                            graph.add_entity_from_ingestion(
                                node_type=graph_node_type,
                                label=str(k),
                                properties={"value": v, "source": "sync"},
                                source="sync",
                                confidence=0.7,
                                relation_to_user=relation_map[node_type],
                            )
        graph.save_to_db(db)
    except Exception as graph_err:
        print(f"[WARN] Memory graph synchronization failed during central engine refresh: {graph_err}")

    db.commit()
    db.refresh(memory)
    return memory


def initialize_career_os_for_user(
    db: Session,
    user_id: str,
    source: str = "manual_onboarding",
    structured: dict | None = None,
) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    memory = refresh_career_memory_from_user_state(db, user, structured)
    market = _get_or_create_market_snapshot(db, user)
    roadmap = get_or_create_roadmap_state(db, user, market, regenerate=True)
    event = log_journey_event(
        db=db,
        user_id=user_id,
        event_type="onboarding_completed",
        summary="Career OS initialized from onboarding intake and current capability profile.",
        evidence={"source": source, "memory_id": memory.id, "roadmap_id": roadmap.id},
        impact={
            "created_career_memory": True,
            "generated_initial_roadmap": True,
            "market_context_attached": True,
        },
    )

    serialized_memory = serialize_memory(memory)
    serialized_market = serialize_market(market)
    serialized_roadmap = serialize_roadmap(roadmap)
    semantic_memory = serialize_semantic_memory(db, user_id)
    serialized_event = serialize_journey_event(event)
    projects = recommend_proof_projects(serialized_memory, serialized_roadmap, serialized_market)
    portfolio = assess_portfolio(serialized_memory, [serialized_event], projects, serialized_market)

    return {
        "memory": serialized_memory,
        "semantic_memory": semantic_memory,
        "market": serialized_market,
        "roadmap": serialized_roadmap,
        "proof_projects": projects,
        "portfolio_assessment": portfolio,
        "journey_event": serialized_event,
    }


def run_weekly_career_cycle(db: Session, user_id: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    roadmap_before = db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first()
    valid_cycles = _valid_weekly_cycle_events(db, user_id)
    if user.created_at:
        now = datetime.datetime.utcnow()
        elapsed_days = (now - user.created_at).days
        week_number = max(1, (elapsed_days // 7) + 1)
        current_week_start = user.created_at + datetime.timedelta(days=(week_number - 1) * 7)
    else:
        # Treat account as started yesterday so the time gate doesn't permanently block
        current_week_start = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    current_actions = []
    if roadmap_before:
        current_actions = (_as_json(roadmap_before.weekly_focus, {}) or {}).get("primary_actions") or []
    def _normalize(s: str) -> str:
        return str(s).strip().lower()

    expected_ids = {
        _normalize(action.get("id") or action.get("title"))
        for action in current_actions
        if action.get("id") or action.get("title")
    }
    task_events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type.in_(["weekly_task_completed", "weekly_task_reopened", "weekly_task_skipped"]),
        JourneyEvent.created_at >= current_week_start
    ).order_by(JourneyEvent.created_at.asc()).all()
    latest_task_state = {}
    for event in task_events:
        evidence = _event_json(event, "evidence", {})
        task_id = _normalize(evidence.get("id") or evidence.get("title") or str(event.id))
        latest_task_state[task_id] = event.event_type
    accepted_ids = {
        task_id
        for task_id, event_type in latest_task_state.items()
        if event_type in {"weekly_task_completed", "weekly_task_skipped"}
    }

    import os as _os
    dev_mode = _os.getenv("DEV_MODE", "false").lower() in {"true", "1", "yes"}

    # Completion gate: require the current tasks to be finished/skipped before advancing.
    # Skipped in DEV_MODE so the plan can be iterated freely during testing.
    if not dev_mode and expected_ids and not expected_ids.issubset(accepted_ids):
        remaining = len(expected_ids - accepted_ids)
        raise ValueError(f"Complete or skip the remaining {remaining} task(s) before requesting next week's plan.")

    elapsed_seconds = (datetime.datetime.utcnow() - current_week_start).total_seconds()
    minimum_seconds = max(30, len(expected_ids or accepted_ids or [1]) * 60)
    if not dev_mode and elapsed_seconds < minimum_seconds:
        minutes = max(1, round((minimum_seconds - elapsed_seconds) / 60))
        raise ValueError(f"Please wait about {minutes} more minute(s) before requesting the next week.")

    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()

    # Reuse the most recent market snapshot — skips web scraping (30+ seconds)
    # which was the primary cause of the 120s timeout on Render free tier.
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user.id,
    ).order_by(MarketSnapshot.created_at.desc()).first()

    if not market:
        # No snapshot at all — do a fresh fetch just this once
        pulse = get_market_snapshot(user.target_role or "AI Developer / Software Engineer")
        opportunity_feed = collect_opportunities([skill.name for skill in skills], user.target_role)
        opportunity_signals = summarize_opportunity_signals(opportunity_feed)
        market = MarketSnapshot(
            id=str(uuid.uuid4()),
            user_id=user.id,
            target_role=user.target_role or "AI Developer / Software Engineer",
            snapshot_date=datetime.date.today(),
            top_demanded_skills=_dump(pulse.get("top_demanded_skills", [])),
            emerging_skills=_dump(pulse.get("emerging_skills", [])),
            raw_data=_dump({
                "recruiter_language": pulse.get("recruiter_language", []),
                "project_patterns": pulse.get("project_patterns", []),
                "certifications": pulse.get("certifications", []),
                "market_warnings": pulse.get("market_warnings", []),
                "sources": pulse.get("sources", []),
                "domain_pack": pulse.get("domain_pack", {}),
                "opportunities": opportunity_feed[:8],
                "opportunity_signals": opportunity_signals,
            }),
            confidence_score=pulse.get("confidence_score", 0.6),
        )
        db.add(market)
        db.commit()
        db.refresh(market)

    # Advance weekly focus without an AI call.
    # The roadmap phases are already in the DB from initial generation.
    # Weekly advancement just picks the next batch of tasks using rule-based
    # logic — AI only ran once (at onboarding) to build the phase structure.
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user.id).first()

    if not roadmap:
        # First ever cycle — no roadmap exists yet, must generate with AI
        roadmap = get_or_create_roadmap_state(db, user, market, regenerate=True)
    else:
        # Roadmap exists — build next week's tasks from rule-based functions
        try:
            from app.services.profile_store import load_profile
            profile = load_profile(user_id)
        except Exception:
            profile = {}

        week_number = _week_number_from_user(user)
        recurring = _recurring_habit_actions(profile, skills, user)
        trend = _trend_response_actions(profile, skills, user, market)

        # Pull next unfinished nodes from existing roadmap phases
        phases = _as_json(roadmap.phases, [])
        phase_nodes = []
        for phase in phases:
            for node in phase.get("nodes", []):
                node_id = _normalize(node.get("id") or node.get("label") or "")
                if node_id not in accepted_ids and node.get("status") != "mastered":
                    phase_nodes.append({
                        "id": node.get("id") or node_id,
                        "node_id": node.get("id") or node_id,
                        "type": "course",
                        "title": node.get("label") or node.get("title") or node_id,
                        "skill": node.get("skill_name") or node.get("label") or node_id,
                        "description": node.get("description") or node.get("label") or "",
                        "why_now": node.get("tech_twist") or "Next step in your learning roadmap.",
                        "url": node.get("resource_url") or "",
                        "source": "roadmap",
                    })
                    if len(phase_nodes) >= 2:
                        break
            if len(phase_nodes) >= 2:
                break

        primary_actions = recurring + phase_nodes + trend[:1]
        if not primary_actions:
            primary_actions = recurring + trend

        existing_focus = _as_json(roadmap.weekly_focus, {})
        new_focus = {
            "phase_id": existing_focus.get("phase_id"),
            "phase_name": existing_focus.get("phase_name"),
            "primary_actions": primary_actions[:4],
            "long_horizon_lanes": existing_focus.get("long_horizon_lanes") or _long_horizon_plan(profile, skills, user, market).get("lanes"),
            "selection_reason": f"Week {week_number}: rule-based advancement using recurring habits, roadmap nodes, and market trend.",
        }
        roadmap.weekly_focus = _dump(new_focus)
        roadmap.last_replanned_reason = f"Advanced to week {week_number} task set."
        roadmap.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(roadmap)
    event = log_journey_event(
        db=db,
        user_id=user_id,
        event_type="weekly_cycle_completed",
        summary="Advanced to the next weekly plan after the current tasks were completed.",
        evidence={
            "market_snapshot_id": market.id,
            "roadmap_id": roadmap.id,
            "completed_task_count": len([event_type for event_type in latest_task_state.values() if event_type == "weekly_task_completed"]),
            "skipped_task_count": len([event_type for event_type in latest_task_state.values() if event_type == "weekly_task_skipped"]),
            "previous_week_started_at": current_week_start.isoformat() if current_week_start else None,
        },
        impact={"market_refreshed": True, "roadmap_replanned": True, "advance_approved": True},
    )
    context = compile_career_context(db, user_id)
    context["weekly_cycle_event"] = serialize_journey_event(event)
    return context


def refresh_roadmap_with_ai(user_id: str) -> None:
    """
    Background task: regenerate the roadmap phases with AI so the NEXT weekly
    advancement gets genuinely personalised tasks rather than rule-based ones.
    Runs after the response is already sent — user never waits for this.
    Failures are logged but silently swallowed so they don't affect the user.
    """
    import logging as _logging
    _bg_log = _logging.getLogger("delta.central_engine.bg")
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return
            market = db.query(MarketSnapshot).filter(
                MarketSnapshot.user_id == user_id,
            ).order_by(MarketSnapshot.created_at.desc()).first()
            if not market:
                return
            roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user_id).first()
            if not roadmap:
                return
            skills = db.query(SkillNode).filter(SkillNode.user_id == user_id).all()
            _bg_log.info("BG: regenerating roadmap phases for user %s", user_id)
            roadmap_payload = generate_weekly_brief(user, skills, market)
            phases = roadmap_payload.get("phases", [])
            if phases:
                roadmap.phases = _dump(phases)
                roadmap.active_phase_id = _select_active_phase(phases).get("id") if phases else None
                roadmap.updated_at = datetime.datetime.utcnow()
                roadmap.last_replanned_reason = "AI phase refresh after weekly advancement."
                db.commit()
                _bg_log.info("BG: roadmap phases refreshed for user %s", user_id)
        finally:
            db.close()
    except Exception as exc:
        _bg_log.error("BG roadmap refresh failed for %s: %s", user_id, exc, exc_info=True)


def run_memory_consolidation_cycle(db: Session, user_id: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    report = consolidate_user_memory(db, user_id)
    event = log_journey_event(
        db=db,
        user_id=user_id,
        event_type="memory_consolidated",
        summary="Semantic memory sleep cycle applied temporal decay and merged duplicate graph nodes.",
        evidence={"memory_consolidation": report},
        impact={"memory_consolidated": True},
    )
    context = compile_career_context(db, user_id)
    context["memory_consolidation"] = report
    context["memory_consolidation_event"] = serialize_journey_event(event)
    return context


def compile_career_context(db: Session, user_id: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    # ── Hydrate user from profile_store JSON (real intake data) ──────────────
    try:
        from app.services.profile_store import load_profile
        profile = load_profile(user_id)
        if profile:
            changed = False
            if profile.get("name") and not user.name:
                user.name = profile["name"]; changed = True
            if profile.get("target_role") and not user.target_role:
                user.target_role = profile["target_role"]; changed = True
            if profile.get("hours_per_week") and not user.hours_per_week:
                user.hours_per_week = int(profile["hours_per_week"]); changed = True
            if profile.get("learning_style") and not user.learning_style:
                user.learning_style = profile["learning_style"]; changed = True
            if changed:
                db.commit()
                db.refresh(user)
    except Exception as _ph_err:
        pass

    memory = get_or_create_career_memory(db, user)
    latest_market = _get_or_create_market_snapshot(db, user)
    roadmap = get_or_create_roadmap_state(db, user, latest_market, regenerate=False)
    valid_cycles = _valid_weekly_cycle_events(db, user_id)
    valid_cycle_ids = {event.id for event in valid_cycles}
    journey = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id
    ).order_by(JourneyEvent.created_at.desc()).limit(20).all()
    journey = [
        event for event in journey
        if event.event_type != "weekly_cycle_completed" or event.id in valid_cycle_ids
    ]

    serialized_memory = serialize_memory(memory)
    serialized_market = serialize_market(latest_market)
    serialized_roadmap = serialize_roadmap(roadmap)
    semantic_memory = serialize_semantic_memory(db, user_id)
    serialized_journey = [serialize_journey_event(event) for event in journey]
    projects = recommend_proof_projects(serialized_memory, serialized_roadmap, serialized_market)
    portfolio = assess_portfolio(serialized_memory, serialized_journey, projects, serialized_market)
    user_skill_names = [
        skill.get("name")
        for skill in serialized_memory.get("capabilities", {}).get("skills", [])
        if skill.get("name")
    ]
    opportunities = collect_opportunities(user_skill_names, user.target_role)
    opportunity_signals = summarize_opportunity_signals(opportunities)

    open_questions_data = _as_json(memory.open_questions, [])
    if isinstance(open_questions_data, dict):
        next_questions = open_questions_data.get("open_questions", [])
    else:
        next_questions = open_questions_data

    # ── Also attach raw profile so frontend can display intake completeness ──
    profile_data = {}
    try:
        from app.services.profile_store import load_profile as _lp
        profile_data = _lp(user_id)
    except Exception:
        pass

    # ── Calculate active week number and start time solely based on user start time ──
    if user.created_at:
        now = datetime.datetime.utcnow()
        elapsed_days = (now - user.created_at).days
        week_number = max(1, (elapsed_days // 7) + 1)
        current_week_start = user.created_at + datetime.timedelta(days=(week_number - 1) * 7)
    else:
        week_number = 1
        current_week_start = datetime.datetime.utcnow() - datetime.timedelta(days=1)

    progress_summary = build_progress_summary(db, user_id, valid_cycles, current_week_start)
    context = {
        "user_id": user_id,
        "memory": serialized_memory,
        "semantic_memory": semantic_memory,
        "market": serialized_market,
        "roadmap": serialized_roadmap,
        "journey_until_today": serialized_journey,
        "proof_projects": projects,
        "portfolio_assessment": portfolio,
        "opportunities": opportunities,
        "opportunity_signals": opportunity_signals,
        "next_questions": next_questions,
        "profile": profile_data,
        "week_number": week_number,
        "current_week_started_at": current_week_start,
        "progress_summary": progress_summary,
    }
    try:
        from app.services.agent2_memory import sync_current_week, sync_user_context
        sync_user_context(user_id, profile_data, context)
        sync_current_week(user_id, context, reason="Career context compiled.")
    except Exception:
        pass
    return context



def serialize_semantic_memory(db: Session, user_id: str) -> dict:
    """Expose the graph memory layer as first-class Career OS context."""
    graph = MemoryGraph.load_from_db(db, user_id)
    summary = graph.to_summary()
    frame = graph.get_frame()

    active_tensions = db.query(TensionNodeModel).filter(
        TensionNodeModel.user_id == user_id,
        TensionNodeModel.status.in_(["active", "challenged"]),
    ).order_by(TensionNodeModel.severity.desc(), TensionNodeModel.created_at.desc()).limit(8).all()

    latest_session = db.query(IngestionSession).filter(
        IngestionSession.user_id == user_id
    ).order_by(IngestionSession.created_at.desc()).first()

    recent_nodes = db.query(SemanticNodeModel).filter(
        SemanticNodeModel.user_id == user_id,
        SemanticNodeModel.node_type != "user",
    ).order_by(
        SemanticNodeModel.last_accessed.desc(),
        SemanticNodeModel.created_at.desc(),
    ).limit(12).all()

    dimensions = frame.get("dimensions", {})
    total_nodes = max(summary.get("total_nodes", 0), 1)
    dimension_balance = {
        dimension: round((count / total_nodes) * 100)
        for dimension, count in dimensions.items()
    }

    return {
        "summary": summary,
        "dimensions": dimensions,
        "dimension_balance": dimension_balance,
        "active_tensions": [
            {
                "id": tension.id,
                "type": tension.tension_type,
                "claim": tension.user_claim,
                "market_reality": tension.market_reality,
                "severity": tension.severity,
                "challenge_question": tension.challenge_question,
                "status": tension.status,
                "created_at": tension.created_at.isoformat() if tension.created_at else None,
            }
            for tension in active_tensions
        ],
        "recent_nodes": [
            {
                "id": node.id,
                "type": node.node_type,
                "label": node.label,
                "dimension": node.dimension,
                "source": node.source,
                "confidence": node.confidence,
                "activation_weight": node.activation_weight,
            }
            for node in recent_nodes
        ],
        "latest_ingestion_session": {
            "id": latest_session.id,
            "status": latest_session.status,
            "journey_type": latest_session.journey_type,
            "current_round": latest_session.current_round,
            "confidence_score": latest_session.confidence_score,
            "gaps_total": latest_session.gaps_total,
            "gaps_filled": latest_session.gaps_filled,
            "tensions_total": latest_session.tensions_total,
            "tensions_resolved": latest_session.tensions_resolved,
            "created_at": latest_session.created_at.isoformat() if latest_session.created_at else None,
            "completed_at": latest_session.completed_at.isoformat() if latest_session.completed_at else None,
        } if latest_session else None,
    }


def log_journey_event(
    db: Session,
    user_id: str,
    event_type: str,
    summary: str,
    evidence: dict | None = None,
    impact: dict | None = None,
) -> JourneyEvent:
    # Update skill node proficiency based on task completion/reopen
    if evidence:
        skill_name = evidence.get("skill") or evidence.get("skill_name") or evidence.get("label")
        if skill_name:
            skill_node = db.query(SkillNode).filter(
                SkillNode.user_id == user_id,
                SkillNode.name.ilike(skill_name.strip())
            ).first()
            
            if event_type == "weekly_task_completed":
                if skill_node:
                    skill_node.proficiency = min(10, (skill_node.proficiency or 0) + 2)
                else:
                    new_node = SkillNode(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        name=skill_name.strip(),
                        proficiency=6,  # Mastered threshold is >= 6
                        evidence_type="claimed",
                        evidence_weight=0.5
                    )
                    db.add(new_node)
                db.commit()
            elif event_type == "weekly_task_reopened":
                if skill_node:
                    skill_node.proficiency = max(1, (skill_node.proficiency or 4) - 2)
                    db.commit()

    event = JourneyEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_type=event_type,
        summary=summary,
        evidence=_dump(evidence or {}),
        impact=_dump(impact or {}),
        event_date=datetime.date.today(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_or_create_roadmap_state(db: Session, user: User, market: MarketSnapshot, regenerate: bool = False) -> RoadmapState:
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user.id).first()
    try:
        from app.services.profile_store import load_profile
        profile = load_profile(user.id)
    except Exception:
        profile = {}
    try:
        from app.services.agent2_memory import active_blocking_events
        blocking_events = active_blocking_events(user.id)
    except Exception:
        blocking_events = []
    if roadmap and not regenerate:
        weekly_focus = _as_json(roadmap.weekly_focus, {})
        actions = weekly_focus.get("primary_actions") or []
        has_stable_actions = actions and all(action.get("id") and action.get("title") for action in actions)
        # If Agent 2 (or the user) explicitly set this week, it is the source of truth.
        # Return it untouched — never auto-regenerate over an explicit decision.
        if has_stable_actions and weekly_focus.get("manual"):
            return roadmap
        low_level_start = any(str(action.get("title", "")).lower().startswith("start ") for action in actions)
        skills_for_profile = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
        profile_says_advanced = _has_prior_profile_depth(profile, skills_for_profile, user)
        if has_stable_actions:
            if blocking_events:
                weekly_focus["primary_actions"] = _event_block_actions(blocking_events)
                weekly_focus["phase_name"] = "Event-focused week"
                roadmap.weekly_focus = _dump(weekly_focus)
                roadmap.last_replanned_reason = "Adjusted for active event in Agent 2 upcoming-events memory."
                db.commit()
                db.refresh(roadmap)
            elif profile_says_advanced and low_level_start:
                proof_actions = _domain_proof_actions(profile, skills_for_profile, user, db)
                if proof_actions:
                    recurring_actions = _recurring_habit_actions(profile, skills_for_profile, user)
                    trend_actions = _trend_response_actions(profile, skills_for_profile, user, market)
                    long_plan = _long_horizon_plan(profile, skills_for_profile, user, market)
                    weekly_focus["primary_actions"] = recurring_actions + proof_actions[:2] + trend_actions[:1]
                    weekly_focus["long_horizon_lanes"] = long_plan["lanes"]
                    weekly_focus["phase_name"] = "Profile-based proof sprint"
                    weekly_focus["selection_reason"] = "Adjusted away from beginner tasks using resume/profile experience and market trends."
                    destination = _as_json(roadmap.destination, {})
                    destination["planning_horizon_months"] = _planning_horizon_months(profile)
                    destination["long_horizon_plan"] = long_plan
                    roadmap.destination = _dump(destination)
                    roadmap.weekly_focus = _dump(weekly_focus)
                    roadmap.last_replanned_reason = "Adjusted away from beginner tasks using resume/profile experience."
                    db.commit()
                    db.refresh(roadmap)
            elif not weekly_focus.get("long_horizon_lanes"):
                recurring_actions = _recurring_habit_actions(profile, skills_for_profile, user)
                trend_actions = _trend_response_actions(profile, skills_for_profile, user, market)
                existing_ids = {str(action.get("id")) for action in actions}
                durable_actions = [
                    action for action in [*recurring_actions, *trend_actions[:1]]
                    if str(action.get("id")) not in existing_ids
                ]
                if durable_actions:
                    weekly_focus["primary_actions"] = durable_actions + actions[:3]
                long_plan = _long_horizon_plan(profile, skills_for_profile, user, market)
                weekly_focus["long_horizon_lanes"] = long_plan["lanes"]
                weekly_focus["selection_reason"] = "Upgraded existing week with durable habit and trend lanes."
                destination = _as_json(roadmap.destination, {})
                destination["planning_horizon_months"] = _planning_horizon_months(profile)
                destination["long_horizon_plan"] = long_plan
                roadmap.destination = _dump(destination)
                roadmap.weekly_focus = _dump(weekly_focus)
                roadmap.last_replanned_reason = "Added long-scale habit, trend, and proof planning to existing roadmap."
                db.commit()
                db.refresh(roadmap)
            return roadmap
    skills = _sync_profile_skills_to_db(db, user)

    roadmap_payload = generate_weekly_brief(user, skills, market)

    phases = roadmap_payload.get("phases", [])
    active_phase = _select_active_phase(phases)

    destination = {
        "target_role": user.target_role or market.target_role or "Career-ready professional",
        "long_term_projection": "Build capability, proof, and market awareness until the user can compete for real opportunities.",
        "planning_horizon_months": _planning_horizon_months(profile),
        "timeline_basis": profile.get("inferred_planning_reason") or "delta inferred a flexible planning horizon from the current profile.",
    }
    long_plan = _long_horizon_plan(profile, skills, user, market)
    destination["long_horizon_plan"] = long_plan
    weekly_focus = {
        "phase_id": active_phase.get("id") if active_phase else None,
        "phase_name": active_phase.get("name") if active_phase else None,
        "primary_actions": _derive_weekly_actions(active_phase),
        "planning_horizon_months": destination["planning_horizon_months"],
        "long_horizon_lanes": long_plan["lanes"],
    }
    recurring_actions = _recurring_habit_actions(profile, skills, user)
    trend_actions = _trend_response_actions(profile, skills, user, market)
    if recurring_actions:
        weekly_focus["primary_actions"] = recurring_actions + weekly_focus["primary_actions"][:2]
        weekly_focus["selection_reason"] = "Includes recurring long-term habit work plus the current roadmap slice."
    if _has_prior_profile_depth(profile, skills, user):
        proof_actions = _domain_proof_actions(profile, skills, user, db)
        if proof_actions:
            weekly_focus["phase_name"] = "Profile-based proof sprint"
            weekly_focus["primary_actions"] = recurring_actions + proof_actions[:2] + trend_actions[:1]
            weekly_focus["selection_reason"] = "Matched against resume/project evidence and current skill depth."
    if regenerate and not blocking_events and _should_assign_break_week(db, user, profile, roadmap):
        weekly_focus["phase_name"] = "Break week"
        weekly_focus["is_break_week"] = True
        weekly_focus["primary_actions"] = _break_week_actions(
            profile,
            user,
            "You have already completed or skipped enough tasks this month."
        )
        weekly_focus["selection_reason"] = "Monthly pacing guard assigned recovery instead of extra work."
        # Record when this break was given so we don't re-trigger another one for ~3 weeks.
        destination["last_break_week_at"] = datetime.datetime.utcnow().isoformat()
    if blocking_events:
        weekly_focus["phase_name"] = "Event-focused week"
        weekly_focus["primary_actions"] = _event_block_actions(blocking_events)
    # A freshly generated week is also authoritative — lock it so a later context-load
    # does not silently regenerate different tasks over it.
    weekly_focus["manual"] = True
    proof_requirements = _derive_proof_requirements(phases)

    if roadmap:
        roadmap.destination = _dump(destination)
        roadmap.phases = _dump(phases)
        roadmap.active_phase_id = weekly_focus["phase_id"]
        roadmap.weekly_focus = _dump(weekly_focus)
        roadmap.resource_graph = _dump(_derive_resource_graph(phases))
        roadmap.proof_requirements = _dump(proof_requirements)
        roadmap.last_replanned_reason = "Refreshed from central engine using latest user memory and market pulse."
    else:
        roadmap = RoadmapState(
            id=str(uuid.uuid4()),
            user_id=user.id,
            destination=_dump(destination),
            phases=_dump(phases),
            active_phase_id=weekly_focus["phase_id"],
            weekly_focus=_dump(weekly_focus),
            resource_graph=_dump(_derive_resource_graph(phases)),
            proof_requirements=_dump(proof_requirements),
            last_replanned_reason="Initial roadmap generated from central career context.",
        )
        db.add(roadmap)

    db.commit()
    db.refresh(roadmap)
    return roadmap


def serialize_memory(memory: CareerMemoryProfile) -> dict:
    open_questions_data = _as_json(memory.open_questions, [])
    if isinstance(open_questions_data, dict):
        open_questions_list = open_questions_data.get("open_questions", [])
        market_search_prompt = open_questions_data.get("market_search_prompt", "")
        follow_up_question_strategy = open_questions_data.get("follow_up_question_strategy", "")
    else:
        open_questions_list = open_questions_data
        market_search_prompt = ""
        follow_up_question_strategy = ""

    return {
        "id": memory.id,
        "user_id": memory.user_id,
        "identity_context": _as_json(memory.identity, {}),
        "identity": _as_json(memory.identity, {}),
        "ambition_map": _as_json(memory.ambitions, {}),
        "ambitions": _as_json(memory.ambitions, {}),
        "capability_map": _as_json(memory.capabilities, {}),
        "capabilities": _as_json(memory.capabilities, {}),
        "constraint_map": _as_json(memory.constraints, {}),
        "constraints": _as_json(memory.constraints, {}),
        "preference_map": _as_json(memory.preferences, {}),
        "preferences": _as_json(memory.preferences, {}),
        "motivation_and_risk_map": _as_json(memory.behavior, {}),
        "behavior": _as_json(memory.behavior, {}),
        "evidence_map": _as_json(memory.evidence, {}),
        "evidence": _as_json(memory.evidence, {}),
        "open_questions": open_questions_list,
        "market_search_prompt": market_search_prompt,
        "follow_up_question_strategy": follow_up_question_strategy,
        "confidence": memory.confidence_score,
        "confidence_score": memory.confidence_score,
        "updated_at": memory.updated_at,
    }


def serialize_market(market: MarketSnapshot) -> dict:
    raw_data = _as_json(market.raw_data, {})
    return {
        "id": market.id,
        "user_id": market.user_id,
        "target_domain": market.target_role,
        "time_window": "weekly",
        "demanded_skills": _as_json(market.top_demanded_skills, []),
        "emerging_skills": _as_json(market.emerging_skills, []),
        "opportunities": raw_data.get("opportunities", []),
        "certifications": raw_data.get("certifications", []),
        "project_patterns": raw_data.get("project_patterns", []),
        "market_warnings": raw_data.get("market_warnings", []),
        "sources": raw_data.get("sources", []),
        "domain_pack": raw_data.get("domain_pack", {}),
        "confidence": market.confidence_score,
        "target_role": market.target_role,
        "snapshot_date": market.snapshot_date,
        "top_demanded_skills": _as_json(market.top_demanded_skills, []),
        "raw_data": raw_data,
        "confidence_score": market.confidence_score,
    }


def serialize_roadmap(roadmap: RoadmapState) -> dict:
    return {
        "id": roadmap.id,
        "user_id": roadmap.user_id,
        "destination": _as_json(roadmap.destination, {}),
        "phases": _as_json(roadmap.phases, []),
        "active_phase_id": roadmap.active_phase_id,
        "weekly_focus": _as_json(roadmap.weekly_focus, {}),
        "resource_graph": _as_json(roadmap.resource_graph, []),
        "proof_requirements": _as_json(roadmap.proof_requirements, []),
        "last_replanned_reason": roadmap.last_replanned_reason,
        "updated_at": roadmap.updated_at,
    }


def serialize_journey_event(event: JourneyEvent) -> dict:
    return {
        "id": event.id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "summary": event.summary,
        "evidence": _as_json(event.evidence, {}),
        "impact": _as_json(event.impact, {}),
        "event_date": event.event_date,
        "created_at": event.created_at,
    }


def build_progress_summary(db: Session, user_id: str, valid_cycles: list[JourneyEvent], current_week_start) -> dict:
    events = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id,
        JourneyEvent.event_type.in_(["weekly_task_completed", "weekly_task_reopened", "weekly_task_skipped"]),
    ).order_by(JourneyEvent.created_at.asc()).all()

    latest_lifetime = {}
    latest_week = {}
    learned_skills = {}
    skipped_lifetime = 0

    for event in events:
        evidence = _as_json(event.evidence, {})
        task_id = str(evidence.get("id") or evidence.get("node_id") or evidence.get("skill") or evidence.get("title") or event.id)
        latest_lifetime[task_id] = event.event_type
        if event.event_type == "weekly_task_skipped":
            skipped_lifetime += 1
        if event.event_type == "weekly_task_completed":
            skill = evidence.get("skill") or evidence.get("title")
            if skill:
                learned_skills[str(skill)] = learned_skills.get(str(skill), 0) + 1
        if current_week_start and event.created_at and event.created_at >= current_week_start:
            latest_week[task_id] = event.event_type

    total_completed = len([state for state in latest_lifetime.values() if state == "weekly_task_completed"])
    total_skipped = len([state for state in latest_lifetime.values() if state == "weekly_task_skipped"])
    current_week_completed = len([state for state in latest_week.values() if state == "weekly_task_completed"])
    current_week_skipped = len([state for state in latest_week.values() if state == "weekly_task_skipped"])
    current_week_reopened = len([state for state in latest_week.values() if state == "weekly_task_reopened"])

    return {
        "weeks_completed": len(valid_cycles),
        "total_tasks_completed": total_completed,
        "total_tasks_skipped": total_skipped,
        "current_week_completed": current_week_completed,
        "current_week_skipped": current_week_skipped,
        "current_week_reopened": current_week_reopened,
        "knowledge_gained": [
            {"skill": skill, "completed_tasks": count}
            for skill, count in sorted(learned_skills.items(), key=lambda item: item[1], reverse=True)[:8]
        ],
    }


def _get_or_create_market_snapshot(db: Session, user: User) -> MarketSnapshot:
    market = db.query(MarketSnapshot).filter(
        MarketSnapshot.user_id == user.id
    ).order_by(MarketSnapshot.snapshot_date.desc()).first()
    if market:
        return market

    pulse = get_market_snapshot(user.target_role or "AI Developer / Software Engineer")
    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
    opportunity_feed = collect_opportunities([skill.name for skill in skills], user.target_role)
    opportunity_signals = summarize_opportunity_signals(opportunity_feed)
    market = MarketSnapshot(
        id=str(uuid.uuid4()),
        user_id=user.id,
        target_role=user.target_role or "AI Developer / Software Engineer",
        snapshot_date=datetime.date.today(),
        top_demanded_skills=_dump(pulse.get("top_demanded_skills", [])),
        emerging_skills=_dump(pulse.get("emerging_skills", [])),
        raw_data=_dump({
            "source": "central_engine_fallback",
            "recruiter_language": pulse.get("recruiter_language", []),
            "project_patterns": pulse.get("project_patterns", []),
            "certifications": pulse.get("certifications", []),
            "market_warnings": pulse.get("market_warnings", []),
            "sources": pulse.get("sources", []),
            "domain_pack": pulse.get("domain_pack", {}),
            "opportunities": opportunity_feed[:8],
            "opportunity_signals": opportunity_signals,
            "pulse": pulse,
        }),
        confidence_score=pulse.get("confidence_score", 0.6),
    )
    db.add(market)
    db.commit()
    db.refresh(market)
    return market


def _derive_open_questions(user: User, structured: dict) -> list[str]:
    questions = []
    if not user.target_role:
        questions.append("Which role or domain do you want delta to optimize your journey for first?")
    if not structured.get("extracted_skills"):
        questions.append("Which skills have you actually used in a project, even at a beginner level?")
    if not structured.get("constraints") and not user.hours_per_week:
        questions.append("What weekly time limit should delta respect while planning your roadmap?")
    if not structured.get("learning_style") and not user.learning_style:
        questions.append("Do you learn faster by videos, docs, building projects, or guided practice?")
    return questions[:4]


def _select_active_phase(phases: list[dict]) -> dict:
    for phase in phases:
        nodes = phase.get("nodes", [])
        if any(node.get("status") != "mastered" for node in nodes):
            return phase
    return phases[-1] if phases else {}


def _derive_weekly_actions(active_phase: dict) -> list[dict]:
    actions = []
    for node in active_phase.get("nodes", [])[:3]:
        if node.get("status") != "mastered":
            node_id = node.get("id") or node.get("skill_name") or node.get("label")
            label = node.get("label") or node.get("skill_name") or "Current skill"
            has_prior_exposure = node.get("status") == "in_progress"
            if has_prior_exposure:
                title = f"Upgrade your {label} proof"
                description = (
                    f"You already have some {label} background. Build something slightly stronger than your resume proof, "
                    "write what changed, and keep the proof small enough for this week."
                )
            else:
                title = f"Start {label} with one small proof"
                description = f"Learn the minimum needed for {label}, then create one small proof instead of only watching content."
            actions.append({
                "id": f"task-{node_id}",
                "node_id": node_id,
                "type": "project",
                "title": title,
                "skill": label,
                "description": description,
                "resource_url": node.get("resource_url"),
                "source": "Official docs or roadmap resource",
                "url": node.get("resource_url"),
                "why_now": node.get("tech_twist"),
                "prior_exposure": has_prior_exposure,
            })
    return actions


def _derive_resource_graph(phases: list[dict]) -> list[dict]:
    resources = []
    for phase in phases:
        for node in phase.get("nodes", []):
            resources.append({
                "phase_id": phase.get("id"),
                "skill": node.get("label"),
                "resource_url": node.get("resource_url"),
                "certification": node.get("certification"),
            })
    return resources


def _derive_proof_requirements(phases: list[dict]) -> list[dict]:
    requirements = []
    for phase in phases:
        for node in phase.get("nodes", []):
            if node.get("status") != "mastered":
                requirements.append({
                    "skill": node.get("label"),
                    "expected_proof": f"GitHub project, write-up, or verified certificate proving {node.get('label')}.",
                    "resume_weight": node.get("certification"),
                    "warning": node.get("architect_warning"),
                })
    return requirements[:6]
