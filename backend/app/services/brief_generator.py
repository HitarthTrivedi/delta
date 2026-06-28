"""Brief generator service — compiles role-specific 3-phase roadmaps dynamically."""
import json
import logging
import uuid
import re
from app.services.ai_service import generate_response

logger = logging.getLogger("delta.brief_generator")
RESUME_MODEL = "gemini-2.5-flash"


def _fetch_trend_intel(role: str) -> str:
    """
    Run 3 targeted Serper searches for the user's role and return a compact
    text block ready for injection into the AI roadmap prompt.
    Fails silently — if Serper is down or quota is exhausted, returns "".
    """
    try:
        from app.services.web_search import get_web_search_service
        svc = get_web_search_service()

        def _search(q: str, n: int = 4) -> list[dict]:
            try:
                return svc.search(q, max_results=n) or []
            except Exception as e:
                logger.warning(f"[trend_intel] search failed for '{q}': {e}")
                return []

        skills_results = _search(f'"{role}" skills in demand trending 2025', 5)
        courses_results = _search(f'best free courses "{role}" 2025 trending', 4)
        tools_results = _search(f'"{role}" tools software frameworks trending 2025', 4)

        def _fmt(results: list[dict], label: str) -> str:
            lines = [
                f"  - {r.get('title', '')} | {r.get('url', '')} — {r.get('snippet', '')[:120]}"
                for r in results if r.get("title")
            ]
            return f"{label}:\n" + ("\n".join(lines) if lines else "  (no results)") if lines else ""

        blocks = [
            _fmt(skills_results, "Trending skills & hiring signals"),
            _fmt(courses_results, "Trending courses & learning resources"),
            _fmt(tools_results, "Trending tools & frameworks"),
        ]
        combined = "\n\n".join(b for b in blocks if b)
        return combined
    except Exception as e:
        logger.warning(f"[trend_intel] fetch failed entirely: {e}")
        return ""


def generate_weekly_brief(user, skills, market_snapshot, agent2_memory: dict = None, onboarding_profile: dict = None, recent_events: list = None, completed_task_titles: list = None, cycle_count: int = 0, horizon_months: int = 12) -> dict:
    """
    Generate highly personalized, role-specific Weekly Brief and Phase-Based Dynamic Roadmap.
    Calls OpenAI (gpt-4o-mini) to design a custom 3-phase chronological learning path 
    appropriate for the user's actual target role, then programmatically overrides node status
    to match user's SQLite skill node proficiencies exactly.
    """
    agent2_memory = agent2_memory or {}
    onboarding_profile = onboarding_profile or {}
    recent_events = recent_events or []
    completed_task_titles = completed_task_titles or []

    role = user.target_role or onboarding_profile.get("target_role") or (market_snapshot.target_role if market_snapshot else "AI Developer / Software Engineer")
    hours = user.hours_per_week or onboarding_profile.get("hours_per_week") or 15
    style = user.learning_style or onboarding_profile.get("learning_style") or "hands-on"

    # Normalize demanded skills list
    demanded = []
    if market_snapshot and market_snapshot.top_demanded_skills:
        try:
            raw_demanded = json.loads(market_snapshot.top_demanded_skills) if isinstance(market_snapshot.top_demanded_skills, str) else market_snapshot.top_demanded_skills
            for item in raw_demanded:
                if isinstance(item, dict):
                    name = item.get("skill") or item.get("name") or ""
                    if name:
                        demanded.append(name)
                elif isinstance(item, str):
                    demanded.append(item)
        except Exception:
            demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]
    else:
        demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]

    if not demanded:
        demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]

    # Construct user skill map
    user_skill_map = {s.name.lower(): s.proficiency for s in skills}
    skills_context = []
    for s in skills:
        skills_context.append(f"- {s.name}: proficiency={s.proficiency}/10, evidence_type={s.evidence_type}")
    skills_list_str = "\n".join(skills_context) if skills_context else "No active skills claimed yet."

    # Build Agent 2 memory context (preferences, constraints, notes from chat)
    preferences = agent2_memory.get("preferences") or {}
    chat_notes = agent2_memory.get("chat_notes") or []
    recent_chat = chat_notes[-5:] if chat_notes else []
    recent_chat_str = "\n".join(
        f"  - User said: \"{n.get('user_message', '')}\" → Agent noted: \"{n.get('assistant_response', '')[:120]}\""
        for n in recent_chat if n.get("user_message")
    ) or "No recent Agent 2 conversations."

    # Build onboarding profile context
    constraints = onboarding_profile.get("constraints") or onboarding_profile.get("limitation") or ""
    planning_horizon = onboarding_profile.get("planning_horizon") or onboarding_profile.get("timeline") or ""
    goals = onboarding_profile.get("goals") or onboarding_profile.get("ambitions") or ""
    projects = onboarding_profile.get("projects") or onboarding_profile.get("past_projects") or ""

    # Build recent activity context
    recent_activity_str = "\n".join(
        f"  - [{e.get('type', '')}] {e.get('summary', '')}"
        for e in recent_events[:10]
    ) or "No recent activity logged."

    # Difficulty level from cycle count (54 weeks/year, 3 levels)
    if cycle_count <= 4:
        difficulty_label = "beginner-foundation"
        difficulty_note = "Week 1-4: absolute fundamentals only. Concepts over tools. Small wins."
    elif cycle_count <= 12:
        difficulty_label = "early-intermediate"
        difficulty_note = f"Week {cycle_count}: build on foundation. Introduce one new tool or framework per week."
    elif cycle_count <= 26:
        difficulty_label = "intermediate"
        difficulty_note = f"Week {cycle_count}: full project tasks, integration, debugging, deployment basics."
    elif cycle_count <= 40:
        difficulty_label = "advanced-intermediate"
        difficulty_note = f"Week {cycle_count}: system-level thinking, performance, production patterns, portfolio-grade work."
    else:
        difficulty_label = "advanced"
        difficulty_note = f"Week {cycle_count}: architecture decisions, contributions, leadership-level proofs, deep specialisation."

    completed_block = ""
    if completed_task_titles:
        titles_list = "\n".join(f"  - {t}" for t in completed_task_titles[:40])
        completed_block = f"""
COMPLETED TASKS — NEVER ASSIGN THESE AGAIN (user has already done them):
{titles_list}
These are done. Do not repeat, rephrase, or reframe them as new tasks. Move forward.
"""

    # Live trend intel from Serper — what's actually trending RIGHT NOW for this role
    trend_intel = _fetch_trend_intel(role)
    trend_intel_section = f"""
LIVE MARKET TREND INTELLIGENCE (fetched right now via web search — use this to make tasks unique and timely):
{trend_intel if trend_intel else "  (web search unavailable — use market snapshot data below)"}
""" if trend_intel else ""

    # Dense structural system prompt
    prompt = f"""
    You are delta's Senior Career OS Roadmap Compiler. Generate a highly personalized, production-grade 3-phase curriculum and weekly brief using ALL of the user's context below.

    USER PROFILE:
    - Target Career Role: {role}
    - Commitment: {hours} hours/week
    - Preferred Learning Style: {style}
    - Planning Horizon / Timeline: {planning_horizon or "Not specified"}
    - Goals beyond target role: {goals or "Not specified"}
    - Personal constraints: {constraints or "None mentioned"}
    - Past projects / prior work: {projects or "None mentioned"}
    - Preferences noted by Agent 2: {json.dumps(preferences) if preferences else "None recorded"}

    USER'S CURRENT SKILLS:
    {skills_list_str}

    RECENT ACTIVITY (last completed / skipped tasks and events):
    {recent_activity_str}

    RECENT AGENT 2 CONVERSATIONS (what the user has been asking for, their frustrations, requests):
    {recent_chat_str}

    MARKET DEMAND PULSE:
    - Top Demanded Skills: {json.dumps(demanded)}
    - Emerging Tech Clusters: {market_snapshot.emerging_skills if market_snapshot else '[]'}
{trend_intel_section}
    CURRENT WEEK NUMBER: {cycle_count + 1} (out of ~54 weeks/year)
    DIFFICULTY LEVEL: {difficulty_label.upper()} — {difficulty_note}
{completed_block}
    CURRICULUM INSTRUCTIONS (read LIVE MARKET TREND INTELLIGENCE above before designing tasks):
    CRITICAL ORDERING RULES:
    1. NEVER assign a task that appears in the COMPLETED TASKS list above. Not in any form, not rephrased.
    2. Pick difficulty one step above where the user currently is — not two steps, not the same level. Push gently.
    3. At least 1 task per week must reference a currently trending tool, course, or skill from the live intel above.
    4. Make tasks specific and timely — not generic. "Build a FastAPI endpoint with async SQLAlchemy and test it with pytest" is better than just "Learn FastAPI".
    5. If a trending course was found, reference it by name and URL in the relevant node's resource_url.
    6. Every task must be concrete enough that the student knows exactly what to do and what "done" looks like.
    1. Sequenced Curriculum: Design exactly 3 chronological phases that move this student from their current baseline to job-ready capability for the target role: "{role}".
       Treat resume/current skills as prior exposure. Do not assign beginner repeat tasks for skills they already listed.
       If a skill is already present but not mastered, convert it into a harder proof/project/debugging/deployment milestone.
       - Phase 1: Focuses on core libraries, packages, basic analytical tools, or language syntax foundations.
       - Phase 2: Focuses on intermediate pipelines, workflows, databases, containerization, or core frameworks.
       - Phase 3: Focuses on advanced architectures, microservices, scaling, domain specializations, or deployment patterns.
    2. Nodes per Phase: Each phase must contain exactly 2-3 logical skill nodes.
    3. Node Properties: Each node MUST be a dictionary containing:
       - "id": a unique string ID (e.g. "node-pandas", "node-docker")
       - "label": clear visual name (e.g. "Pandas Data Wrangling")
       - "skill_name": the clean database skill name (e.g. "Pandas", "SQL", "Docker", "Python"). This is critical for matching database skills!
       - "description": practical description of what they will master.
       - "tech_twist": an expert-level micro-instruction or optimization tip.
       - "architect_warning": a security standard, debugging tip, or production pitfall to avoid.
       - "certification": a premium industry certification mapped to this specific node (e.g. "Google Cloud Data Engineer (+15% weight)")
       - "resource_url": a valid roadmap.sh or official documentation link.
    4. Roadmap Status:
       - For each node, match its "skill_name" (case-insensitive) against the user's current skills.
       - Set its "status" to "mastered" if the user has >= 6 proficiency.
       - Set its "status" to "in_progress" if the user has > 0 and < 6 proficiency; this means prior exposure, not zero knowledge.
       - Set its "status" to "locked" otherwise.
       
    BRIEF COMPOSITION INSTRUCTIONS:
    Provide realistic senior-level insights for the following keys:
    - "demanded_skills": a list of the top 5 highly-demanded skills for this role.
    - "track_status": evaluate based on user's current skills: "ahead" if they have >= 3 mastered, "on_track" if >= 1 mastered/in-progress, "drifting" if they have skills but no mastery, "blocked" if no skills.
    - "market_changes": 3 high-impact market changes, job-posting shifts, or hiring trends related to "{role}".
    - "personal_changes": 2-3 custom status messages reviewing user's weekly capability shifts.
    - "roadmap_updates": 2 custom calibration messages explaining why the roadmap prioritize these phases.
    - "actions": 2-3 specific checklist action items for the current weekly sprint.
      These must be based on what the user has NOT already proven.
      For skills already in the resume, ask for an advanced extension, production proof, GitHub proof, deployment, test suite, benchmark, or written reflection.
    - "opportunities": 3 mock or real platform contest events, sprints, hackathons, or learning challenges.
    - "questions_for_user": 2 deep reflection questions to help the AI resolve profile ambiguity.

    Output strictly as a valid, standard, parsable JSON object. Do not wrap in markdown tags like ```json or ```, do not include comments, and do not add trailing commas.
    Your output MUST have the following top-level keys:
    {{
      "phases": [
        {{
          "id": "string",
          "name": "string",
          "description": "string",
          "nodes": [
            {{
              "id": "string",
              "label": "string",
              "skill_name": "string",
              "description": "string",
              "tech_twist": "string",
              "architect_warning": "string",
              "certification": "string",
              "resource_url": "string",
              "status": "locked|in_progress|mastered"
            }}
          ]
        }}
      ],
      "demanded_skills": ["string"],
      "track_status": "ahead|on_track|drifting|blocked",
      "market_changes": ["string"],
      "personal_changes": ["string"],
      "roadmap_updates": ["string"],
      "actions": ["string"],
      "opportunities": ["string"],
      "questions_for_user": ["string"]
    }}

    Remember, the tone of all feedback, warning notes, and checklist items must be like a comforting, friendly, and comforting tutor who supports the student!
    """

    print(f"\n=================== [ROADMAP GENERATOR START - {role}] ===================")
    print(f"Skills context:\n{skills_list_str}")
    print(f"Market context: {demanded}")
    print(f"=========================================================================")

    try:
        response_text = generate_response(prompt).strip()
        
        # Clean potential markdown wrapping
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
            
        data = json.loads(response_text.strip())
        
        # Self-healing: if LLM nested under "curriculum" or "brief", flatten it to top-level!
        if "curriculum" in data and isinstance(data["curriculum"], dict):
            print("🔧 [ROADMAP AUTO-FLATTEN] Found nested 'curriculum' block — flattening...")
            for k, v in data["curriculum"].items():
                if k not in data:
                    data[k] = v
        if "brief" in data and isinstance(data["brief"], dict):
            print("🔧 [ROADMAP AUTO-FLATTEN] Found nested 'brief' block — flattening...")
            for k, v in data["brief"].items():
                if k not in data:
                    data[k] = v
                    
        print(f"✅ [ROADMAP PARSER] Successfully parsed keys: {list(data.keys())}")
        
        # Self-healing programmatical override of node statuses to guarantee perfect database parity
        for phase in data.get("phases", []):
            for node in phase.get("nodes", []):
                s_name = node.get("skill_name") or node.get("label") or ""
                node["status"] = _get_node_status(s_name, user_skill_map)
                
        # Fill in generated timestamp if missing
        if "roadmap_generated_at" not in data:
            data["roadmap_generated_at"] = str(uuid.uuid4())
        if "user_skills" not in data:
            data["user_skills"] = list(user_skill_map.keys())
            
        print(f"✅ [ROADMAP COMPILE SUCCESS]")
        return data

    except Exception as e:
        print(f"❌ [ROADMAP COMPILE ERROR] Failed: {e}. Reverting to static fallback compiler.")
        import traceback
        traceback.print_exc()
        print(f"=========================================================================")
        return _generate_static_fallback(user, skills, market_snapshot, user_skill_map, demanded)

def _get_node_status(skill_name: str, skill_map: dict) -> str:
    """Helper to return active visual node status."""
    proficiency = skill_map.get(skill_name.lower())
    if proficiency is None:
        return "locked"
    elif proficiency >= 6:
        return "mastered"
    else:
        return "in_progress"

def _generate_static_fallback(user, skills, market_snapshot, user_skill_map, demanded) -> dict:
    """Enterprise-grade static fallback compiler to ensure server stability."""
    phases = [
        {
            "id": "phase-1",
            "name": "Phase 1: Advanced APIs & Backend Systems",
            "description": "Master clean, synchronous REST structures, asynchronous task flows, and schema validation.",
            "nodes": [
                {
                    "id": "node-python",
                    "label": "Advanced Python & Pytest",
                    "skill_name": "Python",
                    "status": _get_node_status("python", user_skill_map),
                    "description": "Functional patterns, testing pipelines, and environment isolation.",
                    "tech_twist": "Python 3.11+ speeds up startup times. Stop using heavy virt env packages when 'uv' or 'poetry' compiles packages 10x faster.",
                    "architect_warning": "Writing code without 80%+ unit test coverage means constant refactoring in production. Use pytest-cov immediately.",
                    "certification": "PCAP Certified Associate (Weight +8%)",
                    "resource_url": "https://roadmap.sh/python"
                },
                {
                    "id": "node-fastapi",
                    "label": "FastAPI & Pydantic v2 Models",
                    "skill_name": "FastAPI",
                    "status": _get_node_status("fastapi", user_skill_map),
                    "description": "Strict type-validation, request sanitization, and structured API endpoints.",
                    "tech_twist": "FastAPI is built on Pydantic. Pydantic v2 has native Rust speeds. Do not use old Config classes; inherit Settings and allow extra='ignore' to avoid load breaks.",
                    "architect_warning": "Avoid global db sessions inside routes. Always inject sessions via FastAPI Depends() to prevent thread locks.",
                    "certification": "FastAPI Backend Specialist (Weight +10%)",
                    "resource_url": "https://fastapi.tiangolo.com/"
                },
                {
                    "id": "node-sql",
                    "label": "Relational Databases & SQL Engine",
                    "skill_name": "SQL",
                    "status": _get_node_status("sql", user_skill_map),
                    "description": "SQLite and PostgreSQL architectures, indexes, and eager loading.",
                    "tech_twist": "Using ORM models directly in requests is an anti-pattern. Always declare Pydantic request/response schemas to separate model logic.",
                    "architect_warning": "N+1 query problems kill performance. Always use SQLAlchemy's joinedload() for foreign key relationships.",
                    "certification": "PostgreSQL Professional (Weight +12%)",
                    "resource_url": "https://roadmap.sh/postgresql"
                }
            ]
        },
        {
            "id": "phase-2",
            "name": "Phase 2: Docker Containers & Infrastructure Orchestration",
            "description": "Containerize backend layers, build microservices, and deploy multi-container networks.",
            "nodes": [
                {
                    "id": "node-docker",
                    "label": "Docker Containerization",
                    "skill_name": "Docker",
                    "status": _get_node_status("docker", user_skill_map),
                    "description": "Multi-stage builds, image layers caching, volume mounting.",
                    "tech_twist": "Stop shipping heavy base python images. Use python:3.11-slim and leverage multi-stage builds to cut image size from 1GB to 120MB.",
                    "architect_warning": "Running containers as root inside production is a massive CVE security vulnerability. Always declare USER appuser.",
                    "certification": "Docker Certified Associate (Weight +15%)",
                    "resource_url": "https://roadmap.sh/docker"
                },
                {
                    "id": "node-system-design",
                    "label": "System Design & Distributed Queues",
                    "skill_name": "System Design",
                    "status": _get_node_status("system design", user_skill_map),
                    "description": "Horizontal scaling, load balancing, Redis caching, Celery task workers.",
                    "tech_twist": "For heavy background processes, do not use threads inside FastAPI. Offload everything to Celery workers using Redis as a message broker.",
                    "architect_warning": "Synchronous database queries inside distributed task managers lead to bottleneck crashes. Keep DB connections pooled.",
                    "certification": "AWS Certified Solutions Architect (Weight +18%)",
                    "resource_url": "https://roadmap.sh/system-design"
                }
            ]
        },
        {
            "id": "phase-3",
            "name": "Phase 3: AI Agents, MLOps & Vector Databases",
            "description": "Construct Retrieval-Augmented Generation (RAG) pipelines, integrate LLMs, and manage orchestrators.",
            "nodes": [
                {
                    "id": "node-llms",
                    "label": "LLM Orchestration & RAG Pipelines",
                    "skill_name": "LLMs",
                    "status": _get_node_status("llms", user_skill_map),
                    "description": "LangChain, LlamaIndex, Vector Search (ChromaDB, PGVector), AI Agents logic.",
                    "tech_twist": "Prompting is only the first step. For enterprise RAG, implement hybrid search (semantic + BM25 keyword matching) to achieve high recall.",
                    "architect_warning": "Naive RAG pipelines fail in production. Implement recursive character chunking and reranking models (e.g., Cohere) to keep context dense.",
                    "certification": "DeepLearning.AI AI Agent Specialist (Weight +20%)",
                    "resource_url": "https://roadmap.sh/ai-engineer"
                },
                {
                    "id": "node-mlops",
                    "label": "MLOps & Vector Scale",
                    "skill_name": "MLOps",
                    "status": _get_node_status("mlops", user_skill_map),
                    "description": "Deploying agent workers in Kubernetes, tracking embeddings latency, scaling data pipelines.",
                    "tech_twist": "Kubernetes is the standard for vector pipeline horizontal scaling. Use KEDA (Kubernetes Event-driven Autoscaling) to scale pod workers dynamically.",
                    "architect_warning": "Embeddings calculation is highly compute-intensive. Cache embeddings queries in Redis to bypass redundant model calls.",
                    "certification": "CKA: Certified Kubernetes Administrator (Weight +25%)",
                    "resource_url": "https://roadmap.sh/kubernetes"
                }
            ]
        }
    ]

    mastered_count = sum(1 for s in skills if s.proficiency >= 6)
    in_progress_count = sum(1 for s in skills if 0 < s.proficiency < 6)
    
    if mastered_count >= 3:
        track_status = "ahead"
    elif in_progress_count >= 1 or mastered_count >= 1:
        track_status = "on_track"
    elif not skills:
        track_status = "blocked"
    else:
        track_status = "drifting"

    market_changes = [
        f"Recruiters looking for {user.target_role or 'engineers'} are emphasizing hands-on verification over static resumes.",
        "A surge in multi-agent orchestration demands has pushed LangChain/CrewAI knowledge into core requirements.",
        "Global remote shifts are favoring engineers with verified public proof of building backend APIs."
    ]

    personal_changes = [
        f"You have fully mastered {mastered_count} key skills in your curriculum!" if mastered_count > 0 else "No active learning sprint detected yet.",
        f"You are actively pushing boundaries on {in_progress_count} in-progress modules." if in_progress_count > 0 else "Select a skill module to begin your week."
    ]

    roadmap_updates = [
        f"Roadmap calibrated to prioritize active foundations.",
        "Next certification milestone weight updated based on recent hiring patterns."
    ]

    actions = []
    found_nodes = []
    for phase in phases:
        for node in phase["nodes"]:
            if node["status"] != "mastered":
                found_nodes.append(node)
        if found_nodes:
            break
            
    if not found_nodes:
        actions.append("All roadmap phases mastered! Connect with recruiters or start entrepreneurship track.")
    else:
        for node in found_nodes[:3]:
            actions.append(f"Learn {node['label']}: focus on '{node['description']}' using recommended resources.")
            actions.append(f"Build {node['label']} proof project: avoid the error - '{node['architect_warning']}'.")

    opportunities = [
        "LeetCode Weekly Contest: Compete to benchmark algorithmic speed.",
        "Unstop National Hackathon Sprint: Apply backend patterns to a real case study.",
        "Kaggle AI Agent Sandbox: Build and run agent workers for predictive tasks."
    ]

    questions_for_user = [
        "What specific target domain or career path do you want delta to refine next?",
        "Would you prefer highly visual video tutorials or deep-dive text documentation for your current phase?"
    ]

    return {
        "phases": phases,
        "demanded_skills": demanded,
        "user_skills": list(user_skill_map.keys()),
        "roadmap_generated_at": str(uuid.uuid4()),
        "track_status": track_status,
        "market_changes": market_changes,
        "personal_changes": personal_changes,
        "roadmap_updates": roadmap_updates,
        "actions": actions,
        "opportunities": opportunities,
        "questions_for_user": questions_for_user
    }
