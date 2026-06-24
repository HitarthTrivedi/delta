"""Market pulse service backed by public live sources."""
from __future__ import annotations

import re
from collections import Counter

import requests

from app.services.domain_packs import infer_domain_pack
from app.services.opportunity_adapters import collect_opportunities, summarize_opportunity_signals
from app.services.web_search import WebSearchService


SKILL_ALIASES = {
    "AI Agents": ["ai agent", "agentic", "autonomous agent"],
    "LLMs": ["llm", "large language model", "gpt", "gemini", "claude"],
    "RAG Pipelines": ["rag", "retrieval augmented generation"],
    "Vector Databases": ["vector database", "pinecone", "weaviate", "qdrant", "chroma"],
    "FastAPI": ["fastapi"],
    "React": ["react", "react.js", "reactjs"],
    "Docker": ["docker", "container"],
    "Kubernetes": ["kubernetes", "k8s"],
    "PostgreSQL": ["postgres", "postgresql"],
    "SQL": ["sql"],
    "Python": ["python"],
    "TypeScript": ["typescript"],
    "JavaScript": ["javascript", "node.js", "nodejs"],
    "System Design": ["system design", "distributed system", "scalability"],
    "MLOps": ["mlops", "model monitoring", "model deployment"],
    "AWS": ["aws", "amazon web services"],
    "C++": ["c++", "cpp"],
    "Rust": ["rust"],
    "Statistics": ["statistics", "statistical"],
    "Machine Learning": ["machine learning", "ml engineer"],
}


def get_market_snapshot(target_role: str = "AI Developer / Software Engineer") -> dict:
    """Return current market demand signals for a target role from public sources."""
    domain_pack = infer_domain_pack(target_role)
    source_documents = []
    source_documents.extend(_fetch_github_signals(target_role, domain_pack["skill_taxonomy"]))
    source_documents.extend(_fetch_stackexchange_signals(domain_pack["skill_taxonomy"]))
    source_documents.extend(_fetch_job_signals(target_role))

    search_snapshot = _fetch_search_market_snapshot(target_role, domain_pack["skill_taxonomy"])
    skill_counts = _count_skills(source_documents, domain_pack["skill_taxonomy"])
    top_demanded = [skill for skill, _ in skill_counts.most_common(8)]
    top_demanded = _merge_unique(top_demanded, search_snapshot.get("demanded_skills", []), domain_pack["skill_taxonomy"])[:8]
    if not top_demanded:
        top_demanded = domain_pack["skill_taxonomy"][:6]

    emerging = _derive_emerging_skills(source_documents, top_demanded, domain_pack["skill_taxonomy"])
    emerging = _merge_unique(emerging, search_snapshot.get("emerging_skills", []))[:6]
    recruiter_language = _merge_unique(_extract_recruiter_phrases(source_documents), search_snapshot.get("recruiter_signals", []))[:6]
    project_patterns = _merge_unique(_derive_project_patterns(target_role, top_demanded), search_snapshot.get("project_patterns", []))[:6]
    certifications = _merge_unique(_derive_certifications(top_demanded, domain_pack["certifications"]), search_snapshot.get("certification_signals", []))[:5]
    market_warnings = _merge_unique(_derive_market_warnings(source_documents, top_demanded), search_snapshot.get("market_warnings", []))[:5]

    opportunities = collect_opportunities(domain_pack["skill_taxonomy"][:5], target_role)
    source_names = sorted({doc["source"] for doc in source_documents})
    search_sources = search_snapshot.get("sources", [])
    confidence = min(0.92, max(
        search_snapshot.get("confidence_score", 0),
        0.35 + 0.08 * len(source_names) + 0.01 * len(source_documents),
    ))

    return {
        "top_demanded_skills": top_demanded,
        "emerging_skills": emerging,
        "recruiter_language": recruiter_language,
        "project_patterns": project_patterns,
        "certifications": certifications,
        "market_warnings": market_warnings,
        "sources": source_names,
        "search_sources": search_sources[:8],
        "domain_pack": domain_pack,
        "confidence_score": round(confidence, 2),
        "opportunities": opportunities[:8],
        "opportunity_signals": summarize_opportunity_signals(opportunities),
        "source_mode": search_snapshot.get("provider") or ("live_public_sources" if source_documents else "live_sources_unavailable"),
    }


def _fetch_search_market_snapshot(target_role: str, taxonomy: list[str]) -> dict:
    try:
        return WebSearchService().search_for_market_pulse(target_role, taxonomy[:8])
    except Exception:
        return {}


def _merge_unique(*groups) -> list:
    merged = []
    seen = set()
    for group in groups:
        if not group:
            continue
        for item in group:
            key = str(item).strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _fetch_github_signals(target_role: str, taxonomy: list[str]) -> list[dict]:
    query_terms = [target_role, *taxonomy[:4]]
    query = " ".join(term for term in query_terms if term)
    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": f"{query} pushed:>2025-01-01",
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            },
            headers={"Accept": "application/vnd.github+json", "User-Agent": "DeltaCareerOS/1.0"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return []

    docs = []
    for repo in response.json().get("items", []):
        docs.append({
            "source": "github_repositories",
            "title": repo.get("full_name") or repo.get("name") or "GitHub repository",
            "url": repo.get("html_url"),
            "text": " ".join([
                repo.get("name") or "",
                repo.get("description") or "",
                repo.get("language") or "",
                " ".join(repo.get("topics") or []),
            ]),
        })
    return docs


def _fetch_stackexchange_signals(taxonomy: list[str]) -> list[dict]:
    tags = [skill.lower().replace(" ", "-").replace("++", "pp") for skill in taxonomy[:6]]
    try:
        response = requests.get(
            "https://api.stackexchange.com/2.3/tags",
            params={
                "order": "desc",
                "sort": "popular",
                "site": "stackoverflow",
                "inname": ";".join(tags[:3]),
                "pagesize": 20,
            },
            headers={"User-Agent": "DeltaCareerOS/1.0"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return []

    return [
        {
            "source": "stackoverflow_tags",
            "title": item.get("name"),
            "url": f"https://stackoverflow.com/questions/tagged/{item.get('name')}",
            "text": f"{item.get('name')} {item.get('count')} questions",
        }
        for item in response.json().get("items", [])
    ]


def _fetch_job_signals(target_role: str) -> list[dict]:
    try:
        response = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            params={"search": target_role},
            headers={"User-Agent": "DeltaCareerOS/1.0"},
            timeout=10,
        )
        response.raise_for_status()
    except Exception:
        return []

    docs = []
    for job in response.json().get("data", [])[:12]:
        docs.append({
            "source": "arbeitnow_jobs",
            "title": job.get("title") or "Job post",
            "url": job.get("url"),
            "text": _strip_html(" ".join([job.get("title") or "", job.get("description") or ""])),
        })
    return docs


def _count_skills(documents: list[dict], taxonomy: list[str]) -> Counter:
    candidates = list(dict.fromkeys([*taxonomy, *SKILL_ALIASES.keys()]))
    counts = Counter()
    all_text = "\n".join(doc.get("text", "") for doc in documents).lower()
    for skill in candidates:
        aliases = SKILL_ALIASES.get(skill, [skill])
        count = sum(all_text.count(alias.lower()) for alias in aliases)
        if count:
            counts[skill] = count
    return counts


def _derive_emerging_skills(documents: list[dict], top_demanded: list[str], taxonomy: list[str]) -> list[str]:
    text = "\n".join(doc.get("text", "") for doc in documents).lower()
    emerging_markers = ["agentic", "rag", "vector", "rust", "serverless", "mlops", "observability"]
    emerging = []
    for marker in emerging_markers:
        if marker in text:
            for skill, aliases in SKILL_ALIASES.items():
                if any(marker in alias for alias in aliases) and skill not in top_demanded:
                    emerging.append(skill)
    for skill in taxonomy:
        if skill not in top_demanded and skill not in emerging:
            emerging.append(skill)
    return emerging[:6]


def _extract_recruiter_phrases(documents: list[dict]) -> list[str]:
    text = _strip_html(" ".join(doc.get("text", "") for doc in documents))
    phrases = []
    patterns = [
        r"production[- ]grade [a-z0-9 +#./-]+",
        r"experience with [a-z0-9 +#./-]+",
        r"hands[- ]on [a-z0-9 +#./-]+",
        r"distributed [a-z0-9 +#./-]+",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            cleaned = match.strip(" .,:;").lower()
            if 8 <= len(cleaned) <= 80 and cleaned not in phrases:
                phrases.append(cleaned)
    return phrases[:6] or ["hands-on proof", "deployment-ready projects", "clear technical ownership"]


def _derive_project_patterns(target_role: str, skills: list[str]) -> list[str]:
    primary = skills[:4]
    if any(skill in primary for skill in ["LLMs", "RAG Pipelines", "Vector Databases", "AI Agents"]):
        return [
            "RAG assistant with citations, evaluation set, and deployment logs",
            "Agent workflow with tool-use audit trail and human override",
            "Private-data document analyzer with local embeddings and access controls",
        ]
    if "Docker" in primary or "Kubernetes" in primary:
        return [
            "Dockerized API service with health checks and observability",
            "CI/CD deployment pipeline with rollback notes",
            "Scalable backend with queue, cache, and database migration proof",
        ]
    return [
        f"{target_role} portfolio project using {', '.join(primary[:3])}",
        "Deployed capstone with README, demo, tests, and metrics",
        "One real-world problem write-up explaining tradeoffs and failure modes",
    ]


def _derive_certifications(skills: list[str], domain_defaults: list[str]) -> list[str]:
    certs = []
    if "AWS" in skills or "Docker" in skills or "Kubernetes" in skills:
        certs.extend(["AWS Certified Cloud Practitioner", "Certified Kubernetes Application Developer"])
    if "Machine Learning" in skills or "MLOps" in skills:
        certs.extend(["Google Professional Machine Learning Engineer", "DeepLearning.AI Machine Learning Specialization"])
    certs.extend(domain_defaults)
    return list(dict.fromkeys(certs))[:5]


def _derive_market_warnings(documents: list[dict], skills: list[str]) -> list[str]:
    warnings = []
    if any(skill in skills for skill in ["LLMs", "AI Agents", "RAG Pipelines"]):
        warnings.append("AI projects need retrieval, evaluation, deployment, and safety proof; prompt-only demos are weak.")
    if "Docker" in skills or "Kubernetes" in skills:
        warnings.append("Backend/cloud roles increasingly expect deployable services, logs, and rollback awareness.")
    if not documents:
        warnings.append("Live public sources were unavailable, so confidence is limited until API access succeeds.")
    return warnings or ["Generic certificates without domain-relevant proof carry limited hiring weight."]


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()
