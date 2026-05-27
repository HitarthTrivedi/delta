"""Market pulse service — fetches market demand data. Uses mocks for now."""
import json
from app.services.domain_packs import infer_domain_pack
from app.services.opportunity_adapters import collect_opportunities, summarize_opportunity_signals

def get_market_snapshot(target_role: str = "AI Developer / Software Engineer") -> dict:
    """Return current market demand signals for a target role."""
    # Mock data — replace with Adzuna API integration later
    snapshots = {
        "AI Developer / Software Engineer": {
            "top_demanded_skills": ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"],
            "emerging_skills": ["AI Agents", "RAG Pipelines", "Vector Databases", "Fine-tuning"],
            "recruiter_language": [
                "production-grade LLM apps",
                "agentic workflows",
                "Dockerized FastAPI services",
                "RAG evaluation",
            ],
            "project_patterns": [
                "RAG assistant with citations and eval set",
                "AI agent workflow with tool calling and audit logs",
                "Dockerized backend with async jobs and observability",
            ],
            "certifications": [
                "AWS Certified Cloud Practitioner",
                "Docker Certified Associate",
                "DeepLearning.AI short courses for LLM apps",
            ],
            "market_warnings": [
                "Prompt-only projects are weak without retrieval, evaluation, and deployment proof.",
                "Junior AI roles increasingly expect backend and cloud basics, not only notebooks.",
            ],
            "sources": ["job_posts", "startup_requirements", "open_source_trends"],
            "confidence_score": 0.82,
        },
        "Data Scientist": {
            "top_demanded_skills": ["Python", "SQL", "Machine Learning", "Statistics", "Deep Learning"],
            "emerging_skills": ["LLMs", "AutoML", "Feature Stores", "MLOps"],
            "recruiter_language": ["experimentation", "business metrics", "feature engineering", "model monitoring"],
            "project_patterns": ["end-to-end ML pipeline", "dashboard-backed model analysis", "model monitoring notebook"],
            "certifications": ["Google Data Analytics", "TensorFlow Developer", "AWS Machine Learning Specialty"],
            "market_warnings": ["Notebook-only proof is weak unless paired with data story and deployment path."],
            "sources": ["job_posts", "competition_patterns", "analytics_role_descriptions"],
            "confidence_score": 0.78,
        },
    }
    domain_pack = infer_domain_pack(target_role)
    default = {
        "top_demanded_skills": domain_pack["skill_taxonomy"][:6],
        "emerging_skills": domain_pack["skill_taxonomy"][6:10] or domain_pack["skill_taxonomy"][:3],
        "recruiter_language": ["hands-on proof", "clear communication", "ownership", domain_pack["label"]],
        "project_patterns": domain_pack["starter_projects"],
        "certifications": domain_pack["certifications"],
        "market_warnings": ["Generic certificates without domain-relevant proof carry limited weight."],
        "sources": domain_pack["market_sources"],
        "domain_pack": domain_pack,
        "confidence_score": 0.66,
    }
    pulse = snapshots.get(target_role, default)
    pulse["domain_pack"] = pulse.get("domain_pack") or domain_pack
    opportunities = collect_opportunities(domain_pack["skill_taxonomy"][:5], target_role)
    pulse["opportunities"] = opportunities[:8]
    pulse["opportunity_signals"] = summarize_opportunity_signals(opportunities)
    return pulse
