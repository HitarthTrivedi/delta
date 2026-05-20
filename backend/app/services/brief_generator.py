"""Brief generator service — generates structured, phase-based dynamic roadmaps."""
import json
import uuid

def generate_weekly_brief(user, skills, market_snapshot) -> dict:
    """
    Generate highly personalized Weekly Brief and Phase-Based Dynamic Roadmap.
    Matches user's current skills against market snapshots, groups them into 3 distinct chronological phases,
    and infuses each with senior-level tech twists, resume certification weights, and custom resource URLs.
    """
    demanded = []
    if market_snapshot and market_snapshot.top_demanded_skills:
        try:
            raw_demanded = json.loads(market_snapshot.top_demanded_skills) if isinstance(market_snapshot.top_demanded_skills, str) else market_snapshot.top_demanded_skills
            # Normalize dictionary objects to plain skill names
            for item in raw_demanded:
                if isinstance(item, dict):
                    name = item.get("skill") or item.get("name") or ""
                    if name:
                        demanded.append(name)
                elif isinstance(item, str):
                    demanded.append(item)
        except (json.JSONDecodeError, TypeError):
            demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]
    else:
        demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]

    # Fallback if list is empty
    if not demanded:
        demanded = ["LLMs", "Docker", "System Design", "Kubernetes", "MLOps"]

    user_skill_map = {s.name.lower(): s.proficiency for s in skills}
    
    # ── PHASE definitions ──
    # Phase 1: Core System & APIs
    # Phase 2: DevOps & Containers
    # Phase 3: AI Agents & Scale
    
    phases = [
        {
            "id": "phase-1",
            "name": "Phase 1: Advanced APIs & Backend Systems",
            "description": "Master clean, synchronous REST structures, asynchronous task flows, and schema validation.",
            "nodes": [
                {
                    "id": "node-python",
                    "label": "Advanced Python & Pytest",
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

    return {
        "phases": phases,
        "demanded_skills": demanded,
        "user_skills": list(user_skill_map.keys()),
        "roadmap_generated_at": str(uuid.uuid4())
    }

def _get_node_status(skill_name: str, skill_map: dict) -> str:
    """Helper to return active visual node status."""
    proficiency = skill_map.get(skill_name.lower())
    if proficiency is None:
        return "locked"
    elif proficiency >= 6:
        return "mastered"
    else:
        return "in_progress"
