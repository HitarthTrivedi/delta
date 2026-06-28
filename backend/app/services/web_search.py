"""
Web Search Service — cognitive search layer for delta Career OS.

Abstracts web search behind a unified interface so downstream services
(Market Pulse, Ingestion Pipeline, Brief Generator) never couple directly to a
search provider.

Provider waterfall:
    1. Serper Google Search API (if SERPER_API_KEY is set)
    2. Tavily Search API (via official Python SDK)
    3. High-fidelity mock that returns role-specific, realistic results

The mock is *not* a stub — it produces carefully crafted, domain-aware results
so the rest of the cognitive pipeline can be developed & tested without an API
key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.services.cache import cached

logger = logging.getLogger("delta.web_search")

# ---------------------------------------------------------------------------
# Type alias for a single search result
# ---------------------------------------------------------------------------
SearchResult = dict[str, Any]
"""
Expected shape:
    {
        "title": str,
        "url": str,
        "snippet": str,
        "relevance_score": float   # 0.0 – 1.0
    }
"""


# ═══════════════════════════════════════════════════════════════════════════
# WebSearchService
# ═══════════════════════════════════════════════════════════════════════════

class WebSearchService:
    """Unified web-search abstraction for the delta Career OS.

    Usage::

        svc = WebSearchService()
        results = svc.search("FastAPI deployment best practices")
        snapshot = svc.search_for_market_pulse("AI Engineer", ["Python", "PyTorch"])
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._serper_api_key: str | None = None
        self._tavily_client: Any | None = None
        self._provider: str = "mock"  # will be upgraded if Tavily is available
        self._init_serper()
        if self._provider != "serper":
            self._init_tavily()

    def _init_serper(self) -> None:
        """Initialise Serper if configured. Uses requests directly, no SDK needed."""
        try:
            from app.config import settings
            api_key = (settings.SERPER_API_KEY or "").strip()
            if not api_key:
                logger.info("SERPER_API_KEY not set — trying next search provider.")
                return
            self._serper_api_key = api_key
            self._provider = "serper"
            logger.info("Serper search provider initialised successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialise Serper provider: %s — trying next provider.", exc)

    def _init_tavily(self) -> None:
        """Attempt to initialise the Tavily client.  Fail silently."""
        try:
            from app.config import settings
            api_key = settings.TAVILY_API_KEY
            if not api_key:
                logger.info("TAVILY_API_KEY not set — web search will use mock provider.")
                return
            from tavily import TavilyClient  # type: ignore[import-untyped]
            self._tavily_client = TavilyClient(api_key=api_key)
            self._provider = "tavily"
            logger.info("Tavily search client initialised successfully.")
        except ImportError:
            logger.warning(
                "tavily-python package not installed. "
                "Install with `pip install tavily-python` for live search. "
                "Falling back to mock provider."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to initialise Tavily client: %s — using mock.", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @cached(
        "web_search",
        ttl=21600,  # 6h — market/search results change slowly
        key_fn=lambda self, query, max_results=10: f"{str(query).strip().lower()}|{max_results}",
    )
    def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Execute a web search and return normalised results.

        Args:
            query: Free-text search query.
            max_results: Maximum number of results to return (1-20).

        Returns:
            List of dicts, each containing *title*, *url*, *snippet*,
            and *relevance_score*.
        """
        max_results = max(1, min(max_results, 20))

        if self._serper_api_key is not None:
            try:
                return self._search_serper(query, max_results)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Serper search failed for query '%s': %s — trying next provider.",
                    query,
                    exc,
                )

        if self._tavily_client is not None:
            try:
                return self._search_tavily(query, max_results)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Tavily search failed for query '%s': %s — falling back to mock.",
                    query,
                    exc,
                )

        return self._search_mock(query, max_results)

    # ------------------------------------------------------------------
    # Market Pulse search orchestrator
    # ------------------------------------------------------------------

    def search_for_market_pulse(
        self,
        target_role: str,
        user_skills: list[str],
        user_location: str = "India",
    ) -> dict[str, Any]:
        """Run multiple targeted searches and synthesise a market snapshot.

        The snapshot is consumed by ``MarketPulseService`` and feeds into
        the Weekly Brief generator.

        Args:
            target_role: The role the user is targeting (e.g. "Backend Engineer").
            user_skills: Current skills the user has declared.
            user_location: User's geography — affects job-market queries.

        Returns:
            A structured dict ready for persistence as a ``MarketSnapshot``::

                {
                    "demanded_skills": [...],
                    "emerging_skills": [...],
                    "recruiter_signals": [...],
                    "project_patterns": [...],
                    "market_warnings": [...],
                    "certification_signals": [...],
                    "salary_signals": [...],
                    "sources": [...],
                    "search_timestamp": "ISO-8601",
                    "confidence_score": 0.0 – 1.0
                }
        """
        ts_start = time.monotonic()

        # --- 1. Build four targeted queries ------------------------------------
        queries = {
            "job_market": (
                f"{target_role} job requirements skills 2026 {user_location}"
            ),
            "skills_demand": (
                f"{target_role} most in-demand skills hiring trends"
            ),
            "project_trends": (
                f"{target_role} portfolio projects that impress recruiters"
            ),
            "industry_shifts": (
                f"{target_role} technology trends industry changes"
            ),
        }

        # --- 2. Execute searches (concurrently — the 4 queries are independent) -
        from app.services.parallel import run_parallel

        results_map = run_parallel(
            {
                category: (lambda q=query: self.search(q, max_results=8))
                for category, query in queries.items()
            },
            timeout=20,
            default=[],
        )

        raw_results: dict[str, list[SearchResult]] = {}
        all_sources: list[dict[str, str]] = []

        for category in queries:
            results = results_map.get(category) or []
            raw_results[category] = results
            for r in results:
                all_sources.append({"url": r["url"], "title": r["title"]})

        # --- 3. Synthesise the snapshot ----------------------------------------
        snapshot = self._synthesise_market_snapshot(
            raw_results=raw_results,
            target_role=target_role,
            user_skills=user_skills,
            sources=all_sources,
        )

        elapsed = time.monotonic() - ts_start
        logger.info(
            "Market pulse search completed in %.2fs (provider=%s, role=%s).",
            elapsed,
            self._provider,
            target_role,
        )
        return snapshot

    # ------------------------------------------------------------------
    # Ingestion-context search
    # ------------------------------------------------------------------

    def search_for_ingestion_context(
        self,
        target_gap: str,
        user_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Search for context relevant to a specific skill gap during ingestion.

        Used by the Ingestion Pipeline to enrich a gap with external market
        data before the AI generates a learning roadmap.

        Args:
            target_gap: The skill gap being addressed (e.g. "Docker", "System Design").
            user_context: Arbitrary dict with ``target_role``, ``current_skills``, etc.

        Returns:
            Dict with *resources*, *market_relevance*, and *learning_paths*.
        """
        target_role = user_context.get("target_role", "Software Engineer")
        current_skills = user_context.get("current_skills", [])

        skills_text = ", ".join(current_skills[:5]) if current_skills else "general"

        query = (
            f"learn {target_gap} for {target_role} coming from {skills_text} "
            f"best resources tutorials 2026"
        )

        results = self.search(query, max_results=6)

        # Classify results into learning-oriented buckets
        resources: list[dict[str, str]] = []
        market_relevance_snippets: list[str] = []

        for r in results:
            resources.append({
                "title": r["title"],
                "url": r["url"],
                "snippet": r["snippet"],
            })
            snippet_lower = r["snippet"].lower()
            if any(kw in snippet_lower for kw in ("demand", "hiring", "salary", "required")):
                market_relevance_snippets.append(r["snippet"])

        return {
            "gap": target_gap,
            "resources": resources,
            "market_relevance": market_relevance_snippets or [
                f"{target_gap} is increasingly required for {target_role} roles."
            ],
            "learning_paths": [r["title"] for r in results[:3]],
            "source_count": len(results),
            "provider": self._provider,
        }

    # ══════════════════════════════════════════════════════════════════
    # Private — Serper provider
    # ══════════════════════════════════════════════════════════════════

    def _search_serper(self, query: str, max_results: int) -> list[SearchResult]:
        """Execute a Google search via Serper and normalise organic results."""
        from app.services.http_client import get_session

        response = get_session().post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": self._serper_api_key or "",
                "Content-Type": "application/json",
            },
            json={"q": query, "num": max_results},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        organic = payload.get("organic") or []

        results: list[SearchResult] = []
        for idx, item in enumerate(organic[:max_results]):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": (item.get("snippet") or "")[:500],
                "relevance_score": round(max(0.55, 0.98 - idx * 0.05), 3),
            })
        return results

    # ══════════════════════════════════════════════════════════════════
    # Private — Tavily provider
    # ══════════════════════════════════════════════════════════════════

    def _search_tavily(self, query: str, max_results: int) -> list[SearchResult]:
        """Execute a search via the Tavily SDK and normalise the response."""
        response = self._tavily_client.search(  # type: ignore[union-attr]
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
        )

        results: list[SearchResult] = []
        for idx, item in enumerate(response.get("results", [])):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:500],
                "relevance_score": round(
                    item.get("score", 1.0 - idx * 0.05), 3
                ),
            })
        return results

    # ══════════════════════════════════════════════════════════════════
    # Private — Mock provider
    # ══════════════════════════════════════════════════════════════════

    def _search_mock(self, query: str, max_results: int) -> list[SearchResult]:
        """Return realistic, role-aware mock search results.

        The mock inspects the query to detect the target role and skill
        keywords, then selects from a curated pool of results so downstream
        consumers receive plausible data.
        """
        query_lower = query.lower()
        role_key = self._detect_role_key(query_lower)

        # Select the best-matching result pool
        pool = self._get_mock_pool(role_key, query_lower)

        # Deterministic shuffle seeded by query hash so repeated calls are stable
        seed = int(hashlib.md5(query.encode()).hexdigest(), 16)  # noqa: S324
        pool_sorted = sorted(pool, key=lambda r: (seed ^ hash(r["title"])) % 10_000)

        results = pool_sorted[:max_results]

        # Assign descending relevance scores
        for idx, r in enumerate(results):
            r["relevance_score"] = round(max(0.55, 0.98 - idx * 0.05), 3)

        return results

    # ------------------------------------------------------------------

    @staticmethod
    def _detect_role_key(query_lower: str) -> str:
        """Map a query string to a canonical role key for mock selection."""
        role_signals: dict[str, list[str]] = {
            "ai_engineer": [
                "ai engineer", "ai developer", "machine learning engineer",
                "ml engineer", "llm", "deep learning",
            ],
            "backend_engineer": [
                "backend engineer", "backend developer", "server-side",
                "fastapi", "django", "spring boot",
            ],
            "frontend_engineer": [
                "frontend engineer", "frontend developer", "react",
                "angular", "vue", "ui engineer",
            ],
            "data_scientist": [
                "data scientist", "data science", "analytics",
                "statistics", "pandas", "machine learning",
            ],
            "devops_engineer": [
                "devops", "sre", "site reliability", "infrastructure",
                "kubernetes", "terraform",
            ],
            "fullstack_engineer": [
                "fullstack", "full stack", "full-stack",
            ],
        }
        for key, signals in role_signals.items():
            if any(s in query_lower for s in signals):
                return key
        return "general"

    # ------------------------------------------------------------------

    @staticmethod
    def _get_mock_pool(role_key: str, query_lower: str) -> list[SearchResult]:
        """Return a curated pool of mock results for *role_key*.

        Each pool contains ≥12 results spanning job-market, skill-demand,
        project-pattern, and industry-shift categories so every market-pulse
        query category gets relevant hits.
        """

        # ── Shared templates ─────────────────────────────────────────
        _base: dict[str, list[SearchResult]] = {
            "ai_engineer": [
                {
                    "title": "AI Engineer Hiring Trends 2026: What Recruiters Actually Want",
                    "url": "https://www.techcrunch.com/ai-engineer-hiring-trends-2026",
                    "snippet": "Recruiters are prioritising candidates who can build production LLM pipelines with retrieval-augmented generation, not just fine-tune notebooks. Docker and Kubernetes experience is now table-stakes for mid-level AI roles.",
                },
                {
                    "title": "Top 10 In-Demand AI Skills for 2026 — LinkedIn Talent Blog",
                    "url": "https://www.linkedin.com/talent/blog/ai-skills-demand-2026",
                    "snippet": "LLM orchestration, RAG pipeline design, vector database management, prompt engineering evaluation, and MLOps remain the five most requested skills in AI engineering job postings worldwide.",
                },
                {
                    "title": "AI Portfolio Projects That Actually Get Interviews",
                    "url": "https://www.towardsdatascience.com/ai-portfolio-projects-interviews-2026",
                    "snippet": "Recruiters report that candidates with RAG assistants featuring citation verification, multi-agent workflows with audit logs, and Dockerized inference endpoints outperform those with toy Jupyter demos.",
                },
                {
                    "title": "Agentic AI Workflows Are Reshaping Software Teams",
                    "url": "https://www.wired.com/story/agentic-ai-workflows-2026",
                    "snippet": "Autonomous agent frameworks (LangGraph, CrewAI, AutoGen) are moving from experiments to production. Companies are hiring AI engineers who can design tool-calling agents with human-in-the-loop guardrails.",
                },
                {
                    "title": "MLOps Best Practices: From Notebook to Production in 2026",
                    "url": "https://mlops.community/best-practices-2026",
                    "snippet": "Feature stores, model registries, and automated evaluation pipelines are becoming mandatory in teams shipping AI products. Engineers who can bridge ML research and production infra are in highest demand.",
                },
                {
                    "title": "AI Engineer Salary Report India 2026 — Glassdoor",
                    "url": "https://www.glassdoor.co.in/ai-engineer-salary-india-2026",
                    "snippet": "Median AI Engineer salary in India rose 18% YoY to ₹24 LPA. Senior roles with MLOps and system design experience command ₹40-60 LPA. Remote roles from US companies pay $120-180K.",
                },
                {
                    "title": "Vector Databases Explained: Pinecone vs Weaviate vs Qdrant",
                    "url": "https://www.pinecone.io/learn/vector-database-comparison",
                    "snippet": "Choosing the right vector database is critical for RAG performance. Pinecone leads in managed simplicity, Weaviate in hybrid search, and Qdrant in open-source flexibility.",
                },
                {
                    "title": "Why Fine-Tuning Alone Won't Get You Hired as an AI Engineer",
                    "url": "https://www.medium.com/ai-career/fine-tuning-alone-wont-get-hired-2026",
                    "snippet": "Hiring managers warn that fine-tuning a base model is now a baseline expectation. Differentiation comes from evaluation frameworks, deployment orchestration, and cost-optimization skills.",
                },
                {
                    "title": "AWS Certified Machine Learning — Is It Worth It in 2026?",
                    "url": "https://www.aws.amazon.com/certification/ml-specialty-value-2026",
                    "snippet": "The AWS ML Specialty certification saw a 32% increase in employer interest. Combined with hands-on project proof, it significantly boosts interview callback rates for AI roles.",
                },
                {
                    "title": "Emerging AI Trends: Multi-Modal Models and Edge Deployment",
                    "url": "https://www.arxiv.org/papers/ai-trends-multimodal-edge-2026",
                    "snippet": "Multi-modal models combining vision, text, and audio are entering production. Edge deployment for on-device inference is creating new roles at the intersection of AI and embedded systems.",
                },
                {
                    "title": "Building Production RAG Systems: Architecture Patterns",
                    "url": "https://www.langchain.com/blog/production-rag-patterns-2026",
                    "snippet": "Chunking strategies, hybrid search, re-ranking, and citation grounding are the four pillars of production RAG. Teams that skip evaluation pipelines ship hallucinating products.",
                },
                {
                    "title": "AI Job Market Warning: Prompt Engineering Roles Are Declining",
                    "url": "https://www.businessinsider.com/prompt-engineering-jobs-declining-2026",
                    "snippet": "Standalone prompt engineering roles dropped 40% in 2026. Companies now expect all AI engineers to be proficient in prompting as a baseline skill, not a specialty.",
                },
            ],
            "backend_engineer": [
                {
                    "title": "Backend Engineer Skills in Demand 2026 — Stack Overflow Survey",
                    "url": "https://survey.stackoverflow.com/2026/backend-skills",
                    "snippet": "Go, Rust, and Python (FastAPI) dominate backend job postings. Microservices architecture, event-driven design, and container orchestration are expected in 85% of senior backend roles.",
                },
                {
                    "title": "System Design Interview Patterns Every Backend Dev Needs",
                    "url": "https://www.systemdesign.one/patterns-2026",
                    "snippet": "Rate limiting, CQRS, event sourcing, and distributed caching are the four patterns most frequently tested in backend system design interviews at top tech companies.",
                },
                {
                    "title": "FastAPI vs Django vs Spring Boot: Backend Framework Showdown",
                    "url": "https://www.realpython.com/fastapi-django-spring-comparison-2026",
                    "snippet": "FastAPI leads in async API performance and developer experience for AI-integrated backends. Django remains king for full-featured web apps. Spring Boot dominates enterprise Java shops.",
                },
                {
                    "title": "Dockerized Backend Projects That Land Interviews",
                    "url": "https://www.devto.com/dockerized-backend-projects-2026",
                    "snippet": "Recruiters love seeing Docker Compose setups with PostgreSQL, Redis, and Celery workers. Add health checks, structured logging, and CI/CD pipelines for maximum impact.",
                },
                {
                    "title": "Backend Developer Salary Trends India 2026",
                    "url": "https://www.glassdoor.co.in/backend-developer-salary-2026",
                    "snippet": "Backend engineers in India earn ₹12-20 LPA at mid-level. Go and Rust specialists command a 25% premium. Full-stack capability adds ₹3-5 LPA on average.",
                },
                {
                    "title": "API Security Best Practices for Production Backend Services",
                    "url": "https://www.owasp.org/api-security-backend-2026",
                    "snippet": "JWT rotation, rate limiting, input validation, and CORS hardening are non-negotiable for production APIs. Recruiters increasingly test security awareness in backend interviews.",
                },
                {
                    "title": "Event-Driven Architecture: Kafka, RabbitMQ, and Beyond",
                    "url": "https://www.confluent.io/learn/event-driven-architecture-2026",
                    "snippet": "Event-driven patterns are replacing synchronous REST calls in high-scale backends. Kafka adoption grew 45% YoY. Engineers with event-streaming experience are highly sought.",
                },
                {
                    "title": "PostgreSQL Advanced Features Every Backend Engineer Should Know",
                    "url": "https://www.postgresql.org/docs/advanced-features-guide-2026",
                    "snippet": "CTEs, window functions, JSONB indexing, and partitioning are the PostgreSQL features most tested in backend interviews. ORM-only knowledge is considered insufficient.",
                },
                {
                    "title": "Observability for Backend Services: Logs, Metrics, Traces",
                    "url": "https://www.datadoghq.com/backend-observability-guide-2026",
                    "snippet": "OpenTelemetry is becoming the standard for backend observability. Companies expect engineers to instrument services with structured logs, custom metrics, and distributed tracing.",
                },
                {
                    "title": "Backend Engineering Career Path: Junior to Staff Engineer",
                    "url": "https://www.levels.fyi/backend-engineer-career-path-2026",
                    "snippet": "Staff backend engineers are expected to design systems serving millions of users, mentor teams, and drive architectural decisions. The path typically takes 6-10 years with deliberate skill building.",
                },
                {
                    "title": "GraphQL vs REST: When to Use What in 2026",
                    "url": "https://www.apollographql.com/graphql-vs-rest-2026",
                    "snippet": "REST remains dominant for microservices communication. GraphQL shines in frontend-heavy apps needing flexible queries. Most companies use both, and backend engineers should know when to apply each.",
                },
                {
                    "title": "Warning: Backend Roles Now Require Cloud Fundamentals",
                    "url": "https://www.infoworld.com/backend-cloud-requirements-2026",
                    "snippet": "73% of backend job postings now list AWS, GCP, or Azure experience as required. Pure localhost development without cloud deployment skills is a red flag for recruiters.",
                },
            ],
            "data_scientist": [
                {
                    "title": "Data Science Hiring Trends 2026: Skills That Matter",
                    "url": "https://www.kdnuggets.com/data-science-hiring-2026",
                    "snippet": "SQL, Python, statistical modeling, and experiment design top the requirements. LLM-augmented analytics and automated feature engineering are the fastest-growing skill areas.",
                },
                {
                    "title": "Data Science Portfolio: Projects Recruiters Actually Review",
                    "url": "https://www.towardsdatascience.com/ds-portfolio-recruiter-review-2026",
                    "snippet": "End-to-end ML projects with business impact narratives, clean EDA notebooks, and deployed model dashboards outperform Kaggle competition entries alone.",
                },
                {
                    "title": "Causal Inference Is the Most Underrated Data Science Skill",
                    "url": "https://www.hbr.org/causal-inference-data-science-2026",
                    "snippet": "Companies are shifting from prediction-only to causal reasoning. A/B testing design, difference-in-differences, and instrumental variables are increasingly valued.",
                },
                {
                    "title": "Data Scientist Salary India 2026 — Ambition Box",
                    "url": "https://www.ambitionbox.com/data-scientist-salary-india-2026",
                    "snippet": "Median data scientist salary in India is ₹16 LPA. Specialisation in NLP or computer vision adds 30-40% premium. Tier-1 product companies offer ₹30-45 LPA for senior roles.",
                },
                {
                    "title": "Feature Stores Explained: Why Every DS Team Needs One",
                    "url": "https://www.feast.dev/feature-store-guide-2026",
                    "snippet": "Feature stores reduce time-to-production for ML models by 60%. Feast and Tecton lead the open-source and managed categories respectively.",
                },
                {
                    "title": "AutoML in 2026: Augmenting, Not Replacing, Data Scientists",
                    "url": "https://www.automl.org/automl-augmenting-data-scientists-2026",
                    "snippet": "AutoML tools handle hyperparameter tuning and model selection. Data scientists who combine AutoML with domain expertise and causal reasoning are irreplaceable.",
                },
                {
                    "title": "Statistical Foundations Every Data Scientist Must Master",
                    "url": "https://www.statisticsbyjim.com/foundations-for-ds-2026",
                    "snippet": "Bayesian inference, hypothesis testing, confidence intervals, and power analysis remain essential. Interviewers increasingly probe statistical intuition, not just coding.",
                },
                {
                    "title": "MLOps for Data Scientists: Bridge the Production Gap",
                    "url": "https://www.mlops.community/ds-production-gap-2026",
                    "snippet": "Data scientists who can containerize models, set up CI/CD for retraining, and monitor data drift are twice as likely to receive senior-level offers.",
                },
                {
                    "title": "Google Data Analytics Certificate: Worth It in 2026?",
                    "url": "https://www.coursera.org/google-data-analytics-review-2026",
                    "snippet": "The Google certificate remains a strong entry point. However, pairing it with original analysis projects is essential — the certificate alone is no longer a differentiator.",
                },
                {
                    "title": "Market Warning: Notebook-Only Data Scientists Are Being Filtered Out",
                    "url": "https://www.datacamp.com/blog/notebook-only-ds-warning-2026",
                    "snippet": "Hiring managers report filtering out candidates whose portfolios consist only of Jupyter notebooks. Deployed dashboards, API endpoints, and reproducible pipelines are expected.",
                },
                {
                    "title": "Deep Learning for Tabular Data: When It Beats XGBoost",
                    "url": "https://www.arxiv.org/deep-learning-tabular-2026",
                    "snippet": "TabNet, FT-Transformer, and regularized deep models now match or beat gradient boosting on large tabular datasets. Data scientists should know when to use each approach.",
                },
                {
                    "title": "Data Science Technology Shifts: LLM-Augmented Analytics",
                    "url": "https://www.gartner.com/llm-augmented-analytics-2026",
                    "snippet": "Natural language querying of databases and LLM-assisted EDA are transforming how data teams work. Analysts who can build and evaluate these tools have a competitive edge.",
                },
            ],
        }

        # ── Role-specific pools ───────────────────────────────────────
        _pools: dict[str, list[SearchResult]] = {
            **_base,
            "frontend_engineer": [
                {
                    "title": "Frontend Engineering in 2026: React, Svelte, or Solid?",
                    "url": "https://www.stateofjs.com/frontend-frameworks-2026",
                    "snippet": "React retains market dominance but Svelte and Solid are growing fast in startups. TypeScript is now mandatory — plain JavaScript submissions are rejected at most companies.",
                },
                {
                    "title": "Frontend Portfolio Projects That Impress Hiring Managers",
                    "url": "https://www.frontendmentor.io/portfolio-guide-2026",
                    "snippet": "Accessible, responsive apps with clean state management, API integration, and performance optimisation demonstrate readiness. Avoid to-do apps and calculator clones.",
                },
                {
                    "title": "Web Performance Optimisation: Core Vitals in 2026",
                    "url": "https://web.dev/performance-vitals-2026",
                    "snippet": "LCP, CLS, and INP are the three Core Web Vitals recruiters ask about. Engineers who can diagnose and fix performance bottlenecks are in premium demand.",
                },
                {
                    "title": "Design Systems and Component Libraries: Frontend Must-Have",
                    "url": "https://www.designsystems.com/component-libraries-2026",
                    "snippet": "Building and maintaining design systems shows architectural maturity. Storybook adoption is near-universal, and Tailwind CSS proficiency is increasingly expected.",
                },
                {
                    "title": "Frontend Developer Salary India 2026",
                    "url": "https://www.glassdoor.co.in/frontend-developer-salary-2026",
                    "snippet": "Mid-level frontend developers earn ₹10-18 LPA. React specialists command the highest salaries. Next.js expertise adds a 15-20% premium.",
                },
                {
                    "title": "Micro-Frontends Architecture: When and Why",
                    "url": "https://www.martinfowler.com/micro-frontends-2026",
                    "snippet": "Large teams are adopting micro-frontends for independent deployment. Module federation in Webpack 5+ and Vite's module system make this practical for mid-size apps.",
                },
                {
                    "title": "Accessibility (a11y) Is Now a Hiring Filter for Frontend Roles",
                    "url": "https://www.deque.com/a11y-hiring-filter-2026",
                    "snippet": "WCAG 2.2 compliance knowledge is tested in 60% of frontend interviews. Screen reader testing and semantic HTML are baseline expectations.",
                },
                {
                    "title": "State Management in 2026: Zustand, Jotai, and React Query",
                    "url": "https://www.tkdodo.eu/state-management-comparison-2026",
                    "snippet": "Redux usage is declining in new projects. Zustand for client state and TanStack Query for server state is the emerging standard pattern.",
                },
                {
                    "title": "TypeScript Advanced Patterns for Frontend Engineers",
                    "url": "https://www.typescriptlang.org/docs/advanced-patterns-2026",
                    "snippet": "Generic constraints, discriminated unions, and template literal types are frequently tested in senior frontend interviews. TypeScript is no longer optional.",
                },
                {
                    "title": "Frontend Testing Strategy: Unit, Integration, E2E",
                    "url": "https://www.testing-library.com/strategy-guide-2026",
                    "snippet": "Vitest for unit tests, Testing Library for integration, and Playwright for E2E form the modern frontend testing pyramid. Code without tests is increasingly rejected in PRs.",
                },
                {
                    "title": "Next.js vs Remix vs Astro: Server-Rendered Frameworks Compared",
                    "url": "https://www.vercel.com/frameworks-comparison-2026",
                    "snippet": "Next.js App Router leads in adoption. Remix offers better progressive enhancement. Astro wins for content-heavy sites. Choose based on use case, not hype.",
                },
                {
                    "title": "Warning: CSS-in-JS Fatigue and the Return to Utility-First Styling",
                    "url": "https://www.css-tricks.com/css-in-js-fatigue-2026",
                    "snippet": "Styled-components and Emotion usage is declining due to runtime performance costs. Tailwind CSS and CSS Modules are the preferred alternatives in 2026.",
                },
            ],
            "devops_engineer": [
                {
                    "title": "DevOps & SRE Skills in Demand 2026",
                    "url": "https://www.puppet.com/devops-survey-2026",
                    "snippet": "Kubernetes, Terraform, GitHub Actions, and observability tooling top the DevOps skills chart. GitOps workflows are becoming the default deployment pattern.",
                },
                {
                    "title": "Platform Engineering: The Evolution of DevOps",
                    "url": "https://www.platformengineering.org/evolution-2026",
                    "snippet": "Internal Developer Platforms (IDPs) are replacing ad-hoc DevOps scripts. Platform engineers who build golden paths for developers are the most sought-after infra hires.",
                },
                {
                    "title": "Infrastructure as Code: Terraform vs Pulumi vs CDK",
                    "url": "https://www.hashicorp.com/iac-comparison-2026",
                    "snippet": "Terraform remains the IaC market leader. Pulumi is gaining traction with teams preferring general-purpose languages. AWS CDK dominates AWS-only shops.",
                },
                {
                    "title": "Kubernetes Certifications: CKA, CKAD, CKS Worth in 2026",
                    "url": "https://www.cncf.io/certification-value-2026",
                    "snippet": "CKA holders earn 22% more than non-certified peers. CKAD is valuable for developer-facing roles. CKS is essential for security-focused infrastructure positions.",
                },
                {
                    "title": "DevOps Engineer Salary India 2026",
                    "url": "https://www.glassdoor.co.in/devops-salary-india-2026",
                    "snippet": "DevOps engineers in India earn ₹14-25 LPA at mid-level. Kubernetes and cloud-native specialists command premium salaries. SRE roles pay 20-30% more than traditional DevOps.",
                },
                {
                    "title": "CI/CD Pipeline Design Patterns for Production Systems",
                    "url": "https://www.github.com/features/ci-cd-patterns-2026",
                    "snippet": "Trunk-based development with feature flags, automated rollbacks, and canary deployments are standard CI/CD patterns. Multi-stage pipelines with security scanning are expected.",
                },
                {
                    "title": "FinOps: Cloud Cost Optimisation Is a DevOps Responsibility Now",
                    "url": "https://www.finops.org/cloud-cost-devops-2026",
                    "snippet": "Companies are making DevOps teams accountable for cloud spend. Engineers who can optimise infrastructure costs while maintaining reliability are in high demand.",
                },
                {
                    "title": "Observability Stack 2026: OpenTelemetry, Grafana, and Beyond",
                    "url": "https://www.grafana.com/observability-stack-2026",
                    "snippet": "OpenTelemetry is the de facto standard for instrumentation. Grafana's LGTM stack (Loki, Grafana, Tempo, Mimir) is replacing legacy monitoring across industries.",
                },
                {
                    "title": "DevOps Portfolio: Infrastructure Projects That Demonstrate Skill",
                    "url": "https://www.devto.com/devops-portfolio-projects-2026",
                    "snippet": "Terraform-provisioned multi-env setups, Helm charts for microservices, and Prometheus-based alerting dashboards are the projects that impress DevOps hiring managers.",
                },
                {
                    "title": "Service Mesh Adoption: Istio vs Linkerd vs Cilium",
                    "url": "https://www.cncf.io/service-mesh-comparison-2026",
                    "snippet": "Cilium's eBPF-based approach is gaining market share over traditional sidecar proxies. Understanding when a service mesh is needed (and when it isn't) is key interview knowledge.",
                },
                {
                    "title": "Security in DevOps: Shift-Left and DevSecOps Practices",
                    "url": "https://www.snyk.io/devsecops-practices-2026",
                    "snippet": "Container scanning, secret detection, and SAST/DAST integration in CI pipelines are now baseline expectations. DevSecOps skills command a 15% salary premium.",
                },
                {
                    "title": "Warning: Manual Infrastructure Management Is a Career Risk",
                    "url": "https://www.infoworld.com/manual-infra-career-risk-2026",
                    "snippet": "ClickOps (manual cloud console management) is being eliminated. Engineers without IaC and automation skills are being passed over for DevOps roles.",
                },
            ],
            "fullstack_engineer": [
                {
                    "title": "Full-Stack Engineer Skills 2026: The Complete Checklist",
                    "url": "https://www.roadmap.sh/full-stack-skills-2026",
                    "snippet": "React/Next.js frontend, FastAPI/Node.js backend, PostgreSQL, Docker, and basic cloud deployment form the modern full-stack baseline. AI integration is the differentiator.",
                },
                {
                    "title": "Full-Stack Portfolio Projects That Win Interviews",
                    "url": "https://www.devto.com/fullstack-portfolio-2026",
                    "snippet": "SaaS clones with auth, payments, and deployment; real-time collaboration apps; and AI-integrated tools demonstrate true full-stack capability to recruiters.",
                },
                {
                    "title": "T-Shaped Full-Stack: Go Deep in One Area",
                    "url": "https://www.medium.com/t-shaped-fullstack-2026",
                    "snippet": "The best full-stack hires have deep expertise in either frontend or backend while maintaining competence across the stack. Pure generalists struggle in senior interviews.",
                },
                {
                    "title": "Full-Stack Developer Salary India 2026",
                    "url": "https://www.glassdoor.co.in/fullstack-salary-india-2026",
                    "snippet": "Full-stack developers earn ₹12-22 LPA at mid-level in India. AI-capable full-stack engineers (with LLM integration experience) earn 20-35% more than traditional web developers.",
                },
                {
                    "title": "Database Choices for Full-Stack Apps: SQL vs NoSQL vs Both",
                    "url": "https://www.prisma.io/database-choices-fullstack-2026",
                    "snippet": "PostgreSQL remains the default for most apps. MongoDB suits document-heavy workloads. Redis for caching and real-time features. Know when to use each.",
                },
                {
                    "title": "Authentication Patterns: OAuth2, JWT, and Passkeys in 2026",
                    "url": "https://www.auth0.com/authentication-patterns-2026",
                    "snippet": "Passkeys are emerging as the passwordless standard. JWT with refresh token rotation remains common. Full-stack engineers must understand the security implications of each pattern.",
                },
                {
                    "title": "Server Components and the Blurring Full-Stack Boundary",
                    "url": "https://www.vercel.com/server-components-fullstack-2026",
                    "snippet": "React Server Components and Next.js App Router are blurring the frontend-backend boundary. Full-stack engineers who understand this paradigm shift have a competitive edge.",
                },
                {
                    "title": "Deployment for Full-Stack Apps: Vercel, Railway, Fly.io",
                    "url": "https://www.railway.app/deployment-comparison-2026",
                    "snippet": "PaaS platforms simplify deployment but understanding the underlying Docker + cloud fundamentals is crucial for debugging production issues and passing interviews.",
                },
                {
                    "title": "Real-Time Features: WebSockets, SSE, and Live Queries",
                    "url": "https://www.supabase.com/real-time-features-guide-2026",
                    "snippet": "Chat, notifications, and collaborative editing require real-time capabilities. WebSockets via Socket.io or native APIs, and Supabase Realtime are the go-to solutions.",
                },
                {
                    "title": "Testing Full-Stack Applications End-to-End",
                    "url": "https://www.playwright.dev/fullstack-testing-guide-2026",
                    "snippet": "Playwright for E2E, pytest for backend, and Vitest for frontend form the full-stack testing trinity. CI pipelines that run all three layers catch bugs before production.",
                },
                {
                    "title": "Monorepo vs Polyrepo for Full-Stack Projects",
                    "url": "https://www.turborepo.org/monorepo-fullstack-2026",
                    "snippet": "Turborepo and Nx make monorepos practical for full-stack apps. Shared types between frontend and backend eliminate integration mismatches.",
                },
                {
                    "title": "Warning: Full-Stack Without DevOps Is Incomplete in 2026",
                    "url": "https://www.infoworld.com/fullstack-devops-requirement-2026",
                    "snippet": "Full-stack engineers who cannot deploy their own applications are being filtered in interviews. Basic Docker, CI/CD, and cloud fundamentals are now part of the full-stack definition.",
                },
            ],
        }

        # Generic fallback for unknown roles
        _pools["general"] = [
            {
                "title": "Most In-Demand Tech Skills 2026 — World Economic Forum",
                "url": "https://www.weforum.org/tech-skills-2026",
                "snippet": "AI literacy, cloud computing, cybersecurity, and data analysis lead the 2026 global skills demand. Continuous learning and adaptability are prized across all tech roles.",
            },
            {
                "title": "How to Build a Tech Portfolio That Gets Interviews",
                "url": "https://www.freecodecamp.org/tech-portfolio-guide-2026",
                "snippet": "Focus on 3-5 projects demonstrating depth, not breadth. Include README documentation, live demos, and explain design decisions. Generic tutorial outputs are filtered.",
            },
            {
                "title": "Tech Salary Report 2026 — Levels.fyi",
                "url": "https://www.levels.fyi/salary-report-2026",
                "snippet": "Software engineer median compensation grew 8% globally. AI-related roles saw the highest growth at 22%. Remote roles from US companies continue to offer premium compensation.",
            },
            {
                "title": "Cloud Certifications Worth Pursuing in 2026",
                "url": "https://www.cloudacademy.com/certifications-worth-pursuing-2026",
                "snippet": "AWS Solutions Architect, Google Cloud Professional, and Azure Fundamentals remain strong credential signals. But without hands-on proof, certificates carry diminishing returns.",
            },
            {
                "title": "GitHub Profile Optimisation for Job Seekers",
                "url": "https://www.github.com/profile-optimization-guide-2026",
                "snippet": "Pinned repos with clear READMEs, contribution graphs showing consistency, and open-source contributions demonstrate collaboration skills that recruiters value.",
            },
            {
                "title": "Tech Interview Trends 2026: What's Changed",
                "url": "https://www.interviewing.io/trends-2026",
                "snippet": "System design rounds are appearing earlier in the process. Take-home projects are replacing whiteboard coding at many companies. Behavioural rounds now assess learning velocity.",
            },
            {
                "title": "Remote Work Trends in Tech 2026",
                "url": "https://www.buffer.com/remote-work-tech-2026",
                "snippet": "Hybrid models dominate, but fully remote roles remain available at 35% of companies. Async communication skills and self-management are critical for remote success.",
            },
            {
                "title": "Open Source Contribution: Career Impact Analysis",
                "url": "https://www.opensource.guide/career-impact-2026",
                "snippet": "Contributors to popular open-source projects receive 40% more recruiter outreach. Even small, consistent contributions signal collaboration ability and code quality awareness.",
            },
            {
                "title": "Soft Skills That Tech Recruiters Actually Evaluate",
                "url": "https://www.hbr.org/tech-soft-skills-2026",
                "snippet": "Written communication, technical documentation, mentoring ability, and ownership mindset are the top soft skills. Technical skills get you interviews; soft skills get you offers.",
            },
            {
                "title": "Warning: Tutorial Hell Is the #1 Career Blocker in 2026",
                "url": "https://www.dev.to/tutorial-hell-career-blocker-2026",
                "snippet": "Endless course completion without building original projects signals inability to apply knowledge. Recruiters and hiring managers actively screen for 'tutorial-only' profiles.",
            },
            {
                "title": "Tech Layoffs and Hiring Freeze Analysis 2026",
                "url": "https://www.layoffs.fyi/analysis-2026",
                "snippet": "While large tech companies stabilized hiring, startups and mid-size companies are actively recruiting. AI and infrastructure roles saw the least impact from layoffs.",
            },
            {
                "title": "Building Technical Writing Skills for Engineers",
                "url": "https://www.writethedocs.org/engineering-writing-2026",
                "snippet": "Engineers who blog about their work, write clear documentation, and maintain ADRs (Architecture Decision Records) are promoted faster and hired more easily.",
            },
        ]

        # If query mentions specific skill keywords, try to match a more
        # specific pool; otherwise use the role pool.
        return _pools.get(role_key, _pools["general"])

    # ══════════════════════════════════════════════════════════════════
    # Private — Market snapshot synthesis
    # ══════════════════════════════════════════════════════════════════

    def _synthesise_market_snapshot(
        self,
        raw_results: dict[str, list[SearchResult]],
        target_role: str,
        user_skills: list[str],
        sources: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Transform raw search results into a structured market snapshot.

        Uses lightweight keyword extraction rather than an LLM call so the
        search service stays fast and doesn't depend on an AI provider.
        """
        # ── Skill extraction heuristics ───────────────────────────────
        skill_mentions: dict[str, int] = {}
        recruiter_signals: list[str] = []
        project_patterns: list[str] = []
        market_warnings: list[str] = []
        certification_signals: list[str] = []
        salary_signals: list[str] = []

        known_skills = {
            "python", "javascript", "typescript", "java", "go", "rust", "c++",
            "react", "angular", "vue", "svelte", "next.js", "node.js",
            "fastapi", "django", "flask", "spring boot", "express",
            "docker", "kubernetes", "terraform", "aws", "gcp", "azure",
            "postgresql", "mysql", "mongodb", "redis", "kafka",
            "llm", "llms", "rag", "langchain", "vector database", "mlops",
            "machine learning", "deep learning", "pytorch", "tensorflow",
            "sql", "nosql", "graphql", "rest", "grpc",
            "git", "ci/cd", "github actions", "jenkins",
            "system design", "microservices", "api design",
            "data analysis", "statistics", "pandas", "numpy",
            "html", "css", "tailwind", "sass",
            "agile", "scrum", "jira",
        }

        for _category, results in raw_results.items():
            for r in results:
                snippet_lower = r["snippet"].lower()
                title_lower = r["title"].lower()
                combined = f"{title_lower} {snippet_lower}"

                # Count skill mentions
                for skill in known_skills:
                    if skill in combined:
                        skill_mentions[skill] = skill_mentions.get(skill, 0) + 1

                # Extract recruiter signals
                if any(kw in combined for kw in ("recruiter", "hiring manager", "interview", "filter")):
                    # Take a meaningful sentence from the snippet
                    recruiter_signals.append(r["snippet"][:200])

                # Extract project patterns
                if any(kw in combined for kw in ("portfolio", "project", "build", "demo")):
                    project_patterns.append(r["snippet"][:200])

                # Extract warnings
                if any(kw in combined for kw in ("warning", "risk", "decline", "filtered", "red flag")):
                    market_warnings.append(r["snippet"][:200])

                # Certifications
                if any(kw in combined for kw in ("certif", "credential", "accredit")):
                    certification_signals.append(r["snippet"][:200])

                # Salary
                if any(kw in combined for kw in ("salary", "compensation", "lpa", "pay", "earn")):
                    salary_signals.append(r["snippet"][:200])

        # ── Rank skills by mention frequency ──────────────────────────
        sorted_skills = sorted(skill_mentions.items(), key=lambda x: x[1], reverse=True)
        all_mentioned = [s for s, _ in sorted_skills]

        # Skills the user already has vs. emerging ones they don't
        user_skills_lower = {s.lower() for s in user_skills}
        demanded = all_mentioned[:12]
        emerging = [s for s in all_mentioned if s not in user_skills_lower][:8]

        # ── Deduplicate signals ───────────────────────────────────────
        recruiter_signals = _deduplicate(recruiter_signals, max_items=6)
        project_patterns = _deduplicate(project_patterns, max_items=5)
        market_warnings = _deduplicate(market_warnings, max_items=4)
        certification_signals = _deduplicate(certification_signals, max_items=4)
        salary_signals = _deduplicate(salary_signals, max_items=3)

        # ── Confidence score ──────────────────────────────────────────
        total_results = sum(len(v) for v in raw_results.values())
        if self._provider == "tavily":
            confidence = min(0.92, 0.60 + total_results * 0.01)
        else:
            confidence = min(0.75, 0.50 + total_results * 0.008)

        # ── Deduplicate sources ───────────────────────────────────────
        seen_urls: set[str] = set()
        unique_sources: list[dict[str, str]] = []
        for src in sources:
            if src["url"] not in seen_urls:
                seen_urls.add(src["url"])
                unique_sources.append(src)

        return {
            "demanded_skills": demanded,
            "emerging_skills": emerging,
            "recruiter_signals": recruiter_signals,
            "project_patterns": project_patterns,
            "market_warnings": market_warnings,
            "certification_signals": certification_signals,
            "salary_signals": salary_signals,
            "sources": unique_sources,
            "search_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence_score": round(confidence, 3),
            "provider": self._provider,
            "result_count": total_results,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Module-level helpers
# ═══════════════════════════════════════════════════════════════════════════

def _deduplicate(items: list[str], max_items: int = 5) -> list[str]:
    """Remove near-duplicate strings and cap the list length.

    Two strings are considered duplicates if their first 80 characters match.
    """
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        key = item[:80].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)
        if len(unique) >= max_items:
            break
    return unique


# ═══════════════════════════════════════════════════════════════════════════
# Convenience singleton
# ═══════════════════════════════════════════════════════════════════════════

_default_service: WebSearchService | None = None


def get_web_search_service() -> WebSearchService:
    """Return a module-level singleton of :class:`WebSearchService`.

    This avoids re-initialising the Tavily client on every call while
    keeping the service easy to import::

        from app.services.web_search import get_web_search_service

        svc = get_web_search_service()
        results = svc.search("FastAPI async patterns")
    """
    global _default_service  # noqa: PLW0603
    if _default_service is None:
        _default_service = WebSearchService()
    return _default_service
