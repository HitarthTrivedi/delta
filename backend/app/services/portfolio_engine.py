"""Portfolio assessment engine for proof, resume weight, and readiness."""


def assess_portfolio(memory: dict, journey: list[dict], projects: list[dict], market: dict) -> dict:
    capabilities = memory.get("capabilities", {})
    evidence = memory.get("evidence", {})
    skills = capabilities.get("skills", [])
    verified_skills = [
        skill for skill in skills
        if skill.get("evidence_type") in ("github", "certification", "verified")
    ]
    demanded = _normalize_skill_names(market.get("top_demanded_skills", []))
    skill_names = {skill.get("name", "").lower() for skill in skills}
    missing_market_proof = [
        skill for skill in demanded
        if skill.lower() not in skill_names
        or not any(v.get("name", "").lower() == skill.lower() for v in verified_skills)
    ]
    recent_verified = [
        event for event in journey
        if event.get("event_type") in ("milestone_verified", "project_update")
    ]

    evidence_density = len(verified_skills) / max(len(skills), 1)
    if evidence_density >= 0.6 and len(recent_verified) >= 2:
        readiness = "strong"
    elif evidence_density >= 0.3:
        readiness = "developing"
    else:
        readiness = "thin"

    return {
        "readiness": readiness,
        "evidence_density": round(evidence_density, 2),
        "verified_skills": [skill.get("name") for skill in verified_skills],
        "missing_market_proof": missing_market_proof[:6],
        "current_public_assets": {
            "projects": evidence.get("projects", []),
            "certifications": evidence.get("certifications", []),
            "portfolio_links": evidence.get("portfolio_links", []),
        },
        "what_looks_weak": _weaknesses(readiness, missing_market_proof, projects),
        "resume_updates": _resume_updates(verified_skills, projects),
        "github_updates": _github_updates(projects),
        "linkedin_updates": _linkedin_updates(projects, readiness),
        "next_best_proof": projects[0] if projects else None,
    }


def _normalize_skill_names(items: list) -> list[str]:
    names = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("skill")
        else:
            name = item
        if name:
            names.append(str(name))
    return names


def _weaknesses(readiness: str, missing_market_proof: list[str], projects: list[dict]) -> list[str]:
    issues = []
    if readiness == "thin":
        issues.append("Too many skill claims are still unverified. Add GitHub proof before applying aggressively.")
    if missing_market_proof:
        issues.append(f"Market proof missing for: {', '.join(missing_market_proof[:3])}.")
    if projects:
        issues.append("The next project needs a recruiter-readable README, not only working code.")
    return issues or ["Portfolio has enough proof for the current phase. Keep adding depth."]


def _resume_updates(verified_skills: list[dict], projects: list[dict]) -> list[str]:
    updates = []
    for skill in verified_skills[:3]:
        updates.append(f"Add verified {skill.get('name')} evidence with a link and measurable outcome.")
    for project in projects[:2]:
        updates.append(project.get("resume_headline"))
    return updates or ["Add one proof-backed project before expanding resume claims."]


def _github_updates(projects: list[dict]) -> list[str]:
    if not projects:
        return ["Create one public repository with clean README, setup, and demo proof."]
    return [
        f"Create or improve repo for {project.get('title')} with setup, architecture, and screenshots."
        for project in projects[:3]
    ]


def _linkedin_updates(projects: list[dict], readiness: str) -> list[str]:
    if readiness == "thin":
        return ["Wait until one project milestone is verified, then post a concise build log."]
    return [
        f"Post a short build note for {projects[0].get('title')} explaining the problem, stack, and tradeoff."
    ] if projects else ["Post a weekly learning reflection after the next verified milestone."]
