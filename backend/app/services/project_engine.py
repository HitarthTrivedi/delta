"""Project recommendation engine for proof-focused career growth."""


def recommend_proof_projects(memory: dict, roadmap: dict, market: dict, limit: int = 3) -> list[dict]:
    ambitions = memory.get("ambitions", {})
    capabilities = memory.get("capabilities", {})
    target_role = ambitions.get("target_role") or market.get("target_role") or "Software Engineer"
    known_skills = {skill.get("name", "").lower() for skill in capabilities.get("skills", [])}
    demanded = market.get("top_demanded_skills", []) or []
    active_phase_id = roadmap.get("active_phase_id")
    active_phase = next(
        (phase for phase in roadmap.get("phases", []) if phase.get("id") == active_phase_id),
        (roadmap.get("phases") or [{}])[0],
    )

    candidate_nodes = [
        node
        for node in active_phase.get("nodes", [])
        if node.get("status") != "mastered"
    ]
    if not candidate_nodes:
        candidate_nodes = [
            node
            for phase in roadmap.get("phases", [])
            for node in phase.get("nodes", [])
            if node.get("status") != "mastered"
        ]
    if not candidate_nodes:
        candidate_nodes = [
            {
                "id": f"node-{str(skill).lower().replace(' ', '-')}",
                "label": str(skill),
                "status": "locked",
                "tech_twist": f"{skill} is showing up in current market expectations for {target_role}.",
                "architect_warning": "A claim without visible proof will not carry resume weight.",
            }
            for skill in demanded[:limit]
        ]

    projects = []
    for node in candidate_nodes[:limit]:
        skill = node.get("label", "Core skill")
        projects.append({
            "id": f"proof-{node.get('id', skill).replace('node-', '')}",
            "title": f"{skill} Proof Project",
            "resume_headline": f"Built a production-style {skill} project aligned with {target_role} expectations.",
            "real_world_problem": _problem_for_skill(skill, target_role),
            "why_it_matters": node.get("tech_twist") or f"{skill} appears in current role expectations for {target_role}.",
            "required_skills": [skill],
            "stretch_skills": _stretch_skills(skill, demanded, known_skills),
            "milestones": [
                "Define the problem and expected user outcome.",
                "Build the smallest working version with clean folder structure.",
                "Add persistence, error handling, and at least one automated check.",
                "Write a recruiter-readable README with screenshots, setup, and tradeoffs.",
            ],
            "evaluation_criteria": [
                "Can a reviewer run it from README instructions?",
                "Does it prove the named skill without exaggerated claims?",
                "Does the code show structure, testing, and decision clarity?",
            ],
            "github_readme_expectations": [
                "Problem statement",
                "Architecture overview",
                "Setup commands",
                "Demo screenshots or video link",
                "Known tradeoffs and next improvements",
            ],
            "demo_expectations": "A 2-4 minute walkthrough showing the problem, the working flow, and one technical decision.",
            "recruiter_pitch": f"This project proves practical {skill} ability through visible implementation, not only course completion.",
            "extensions": _extensions_for_skill(skill),
            "market_signal": node.get("architect_warning") or "Market expects proof-backed skill claims.",
        })

    return projects


def _problem_for_skill(skill: str, target_role: str) -> str:
    lower = skill.lower()
    if "fastapi" in lower or "api" in lower:
        return "Create a career intelligence API that stores user skills, weekly actions, and verified proof links."
    if "docker" in lower:
        return "Containerize a full-stack student portfolio tracker with repeatable local setup and slim production images."
    if "llm" in lower or "rag" in lower:
        return "Build a retrieval assistant that answers questions from a student's own notes, roadmap, and project history."
    if "sql" in lower or "database" in lower:
        return "Design a relational progress tracker that can query skill gaps, weekly consistency, and evidence density."
    if "system design" in lower:
        return "Design and prototype a scalable weekly brief system with background jobs and retry-safe processing."
    return f"Solve a practical {target_role} problem that demonstrates {skill} through a usable artifact."


def _stretch_skills(skill: str, demanded: list, known_skills: set[str]) -> list[str]:
    extras = []
    for item in demanded:
        name = item.get("name") if isinstance(item, dict) else item
        if name and name.lower() not in skill.lower() and name.lower() not in known_skills:
            extras.append(name)
        if len(extras) >= 3:
            break
    return extras or ["GitHub documentation", "Testing", "Deployment"]


def _extensions_for_skill(skill: str) -> list[str]:
    lower = skill.lower()
    if "llm" in lower or "rag" in lower:
        return ["Add source citations", "Add hybrid search", "Add evaluation prompts"]
    if "docker" in lower:
        return ["Add multi-stage build", "Add non-root user", "Add compose health checks"]
    if "fastapi" in lower:
        return ["Add auth", "Add background jobs", "Add OpenAPI examples"]
    return ["Add tests", "Deploy a demo", "Write a technical blog post"]
