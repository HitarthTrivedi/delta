"""Central career engine for Delta's personalized operating system."""
import datetime
import json
import uuid

from sqlalchemy.orm import Session

from app.models import (
    CareerMemoryProfile,
    JourneyEvent,
    MarketSnapshot,
    PersonalizationProfile,
    RoadmapState,
    SkillNode,
    User,
)
from app.services.brief_generator import generate_weekly_brief
from app.services.domain_packs import infer_domain_pack
from app.services.market_pulse import get_market_snapshot
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
            for node_type, details in payload.items():
                if node_type in ["identity", "ambitions", "capabilities", "constraints", "preferences", "evidence"]:
                    if isinstance(details, dict):
                        for k, v in details.items():
                            graph.add_entity_from_ingestion(
                                node_type=node_type if node_type != "ambitions" else "ambition",
                                label=str(k),
                                properties={"value": v, "source": "sync"},
                                source="sync",
                                confidence=0.7,
                                relation_to_user="HAS_SKILL" if node_type == "capabilities" else "STRIVES_FOR" if node_type == "ambitions" else "CONSTRAINED_BY" if node_type == "constraints" else "PREFERS"
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
    roadmap = get_or_create_roadmap_state(db, user, market)
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
    serialized_event = serialize_journey_event(event)
    projects = recommend_proof_projects(serialized_memory, serialized_roadmap, serialized_market)
    portfolio = assess_portfolio(serialized_memory, [serialized_event], projects, serialized_market)

    return {
        "memory": serialized_memory,
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

    memory = refresh_career_memory_from_user_state(db, user)
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

    roadmap = get_or_create_roadmap_state(db, user, market)
    event = log_journey_event(
        db=db,
        user_id=user_id,
        event_type="weekly_cycle_completed",
        summary="Weekly Career OS cycle refreshed market pulse, roadmap, proof projects, and portfolio assessment.",
        evidence={"market_snapshot_id": market.id, "roadmap_id": roadmap.id},
        impact={"market_refreshed": True, "roadmap_replanned": True},
    )
    context = compile_career_context(db, user_id)
    context["weekly_cycle_event"] = serialize_journey_event(event)
    context["memory"] = serialize_memory(memory)
    return context


def compile_career_context(db: Session, user_id: str) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    memory = get_or_create_career_memory(db, user)
    latest_market = _get_or_create_market_snapshot(db, user)
    roadmap = get_or_create_roadmap_state(db, user, latest_market)
    journey = db.query(JourneyEvent).filter(
        JourneyEvent.user_id == user_id
    ).order_by(JourneyEvent.created_at.desc()).limit(20).all()

    serialized_memory = serialize_memory(memory)
    serialized_market = serialize_market(latest_market)
    serialized_roadmap = serialize_roadmap(roadmap)
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

    return {
        "user_id": user_id,
        "memory": serialized_memory,
        "market": serialized_market,
        "roadmap": serialized_roadmap,
        "journey_until_today": serialized_journey,
        "proof_projects": projects,
        "portfolio_assessment": portfolio,
        "opportunities": opportunities,
        "opportunity_signals": opportunity_signals,
        "next_questions": next_questions,
    }


def log_journey_event(
    db: Session,
    user_id: str,
    event_type: str,
    summary: str,
    evidence: dict | None = None,
    impact: dict | None = None,
) -> JourneyEvent:
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


def get_or_create_roadmap_state(db: Session, user: User, market: MarketSnapshot) -> RoadmapState:
    roadmap = db.query(RoadmapState).filter(RoadmapState.user_id == user.id).first()
    skills = db.query(SkillNode).filter(SkillNode.user_id == user.id).all()
    roadmap_payload = generate_weekly_brief(user, skills, market)
    phases = roadmap_payload.get("phases", [])
    active_phase = _select_active_phase(phases)

    destination = {
        "target_role": user.target_role or market.target_role or "Career-ready professional",
        "long_term_projection": "Build capability, proof, and market awareness until the user can compete for real opportunities.",
    }
    weekly_focus = {
        "phase_id": active_phase.get("id") if active_phase else None,
        "phase_name": active_phase.get("name") if active_phase else None,
        "primary_actions": _derive_weekly_actions(active_phase),
    }
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
        questions.append("Which role or domain do you want Delta to optimize your journey for first?")
    if not structured.get("extracted_skills"):
        questions.append("Which skills have you actually used in a project, even at a beginner level?")
    if not structured.get("constraints") and not user.hours_per_week:
        questions.append("What weekly time limit should Delta respect while planning your roadmap?")
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
            actions.append({
                "skill": node.get("label"),
                "action": f"Complete one proof-building milestone for {node.get('label')}.",
                "resource_url": node.get("resource_url"),
                "why_now": node.get("tech_twist"),
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
