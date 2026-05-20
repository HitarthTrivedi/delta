"""Market pulse service — fetches market demand data. Uses mocks for now."""
import json

def get_market_snapshot(target_role: str = "AI Developer / Software Engineer") -> dict:
    """Return current market demand signals for a target role."""
    # Mock data — replace with Adzuna API integration later
    snapshots = {
        "AI Developer / Software Engineer": {
            "top_demanded_skills": ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"],
            "emerging_skills": ["AI Agents", "RAG Pipelines", "Vector Databases", "Fine-tuning"],
            "confidence_score": 0.82,
        },
        "Data Scientist": {
            "top_demanded_skills": ["Python", "SQL", "Machine Learning", "Statistics", "Deep Learning"],
            "emerging_skills": ["LLMs", "AutoML", "Feature Stores", "MLOps"],
            "confidence_score": 0.78,
        },
    }
    default = {
        "top_demanded_skills": ["Python", "Git", "SQL", "Docker", "Cloud"],
        "emerging_skills": ["AI/ML", "Kubernetes", "Terraform"],
        "confidence_score": 0.6,
    }
    return snapshots.get(target_role, default)
