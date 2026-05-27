"""Domain packs let Delta generalize beyond a CS-only career path."""

DOMAIN_PACKS = {
    "cs_ai": {
        "id": "cs_ai",
        "label": "CS / AI Engineering",
        "target_roles": ["AI Developer / Software Engineer", "Backend Engineer", "Fullstack Developer", "AI Engineer"],
        "skill_taxonomy": ["Python", "Data Structures", "FastAPI", "SQL", "Docker", "System Design", "LLMs", "RAG", "Cloud"],
        "market_sources": ["job_posts", "github_trends", "hackathons", "leetcode", "codeforces", "kaggle"],
        "proof_types": ["GitHub project", "deployed demo", "technical README", "contest rank", "certificate"],
        "starter_projects": [
            "Career intelligence API with weekly planning",
            "RAG assistant with citations",
            "Dockerized full-stack dashboard",
        ],
        "certifications": ["AWS Cloud Practitioner", "Docker Certified Associate", "DeepLearning.AI LLM courses"],
        "competitions": ["Kaggle", "Codeforces", "LeetCode", "Unstop Hackathons"],
        "phases": ["Programming foundations", "Backend and data systems", "AI/cloud production proof"],
        "rubric": ["Runs locally", "Has tests", "Shows architecture", "Uses real data", "Explains tradeoffs"],
    },
    "data": {
        "id": "data",
        "label": "Data / Analytics",
        "target_roles": ["Data Scientist", "Data Analyst", "ML Engineer", "Business Analyst"],
        "skill_taxonomy": ["Python", "SQL", "Statistics", "Pandas", "Visualization", "ML", "Experimentation", "Dashboards"],
        "market_sources": ["job_posts", "kaggle", "analytics_case_studies", "company_reports"],
        "proof_types": ["case study", "notebook", "dashboard", "model card", "data story"],
        "starter_projects": [
            "Hiring market analysis dashboard",
            "End-to-end churn prediction case study",
            "SQL portfolio with business questions",
        ],
        "certifications": ["Google Data Analytics", "Microsoft PL-300", "TensorFlow Developer"],
        "competitions": ["Kaggle", "Analytics Vidhya", "Unstop case competitions"],
        "phases": ["Data fundamentals", "Modeling and analysis", "Business-facing portfolio proof"],
        "rubric": ["Clear question", "Clean data", "Correct metrics", "Visual insight", "Business recommendation"],
    },
    "design": {
        "id": "design",
        "label": "Design / UX",
        "target_roles": ["Product Designer", "UX Designer", "UI Designer", "Visual Designer"],
        "skill_taxonomy": ["User Research", "Wireframing", "Figma", "Prototyping", "Visual Systems", "Usability Testing"],
        "market_sources": ["portfolio reviews", "design job posts", "product teardowns", "design challenges"],
        "proof_types": ["case study", "prototype", "design system", "research notes", "usability report"],
        "starter_projects": ["Student career app redesign", "Fintech onboarding case study", "Design system for a dashboard"],
        "certifications": ["Google UX Design", "Interaction Design Foundation"],
        "competitions": ["Designathons", "Unstop design challenges"],
        "phases": ["Visual and UX foundations", "Research-backed case studies", "Portfolio storytelling"],
        "rubric": ["Problem clarity", "Research depth", "Interaction quality", "Visual polish", "Decision rationale"],
    },
    "product": {
        "id": "product",
        "label": "Product / PM",
        "target_roles": ["Product Manager", "Associate PM", "Product Analyst"],
        "skill_taxonomy": ["User Problems", "Metrics", "Prioritization", "Roadmapping", "Experimentation", "Communication"],
        "market_sources": ["APM job posts", "product teardowns", "startup case studies", "business news"],
        "proof_types": ["product teardown", "PRD", "metric dashboard", "user interview synthesis"],
        "starter_projects": ["PRD for a student career OS", "Growth teardown of an edtech app", "Metrics dashboard for a product funnel"],
        "certifications": ["Reforge courses", "Product School certificate"],
        "competitions": ["Case competitions", "Product teardowns", "Unstop PM challenges"],
        "phases": ["Product thinking", "Metrics and experimentation", "Portfolio case studies"],
        "rubric": ["Problem framing", "User insight", "Metric logic", "Tradeoff quality", "Execution plan"],
    },
    "finance": {
        "id": "finance",
        "label": "Finance",
        "target_roles": ["Financial Analyst", "Investment Analyst", "Quant Analyst", "Risk Analyst"],
        "skill_taxonomy": ["Accounting", "Excel", "Valuation", "Markets", "Statistics", "Python", "Risk", "Communication"],
        "market_sources": ["finance job posts", "market news", "company filings", "case competitions"],
        "proof_types": ["valuation model", "market memo", "dashboard", "case competition deck"],
        "starter_projects": ["DCF valuation of an Indian listed company", "Sector market pulse memo", "Risk dashboard for a portfolio"],
        "certifications": ["CFA Level 1", "NISM certificates", "FMVA"],
        "competitions": ["CFA Research Challenge", "Unstop finance competitions"],
        "phases": ["Accounting and markets", "Modeling and analysis", "Investment thesis proof"],
        "rubric": ["Assumption quality", "Model correctness", "Market reasoning", "Risk awareness", "Clear memo"],
    },
    "core_engineering": {
        "id": "core_engineering",
        "label": "Core Engineering",
        "target_roles": ["Mechanical Engineer", "Electrical Engineer", "Civil Engineer", "Robotics Engineer"],
        "skill_taxonomy": ["Engineering Mechanics", "CAD", "Simulation", "Electronics", "Manufacturing", "Documentation"],
        "market_sources": ["core job posts", "internship boards", "research labs", "hardware competitions"],
        "proof_types": ["CAD model", "simulation report", "prototype", "lab note", "technical presentation"],
        "starter_projects": ["CAD and simulation portfolio piece", "IoT sensor prototype", "Failure analysis report"],
        "certifications": ["AutoCAD", "SolidWorks", "MATLAB", "Siemens/NPTEL courses"],
        "competitions": ["SAE", "Robotics contests", "Smart India Hackathon hardware tracks"],
        "phases": ["Engineering fundamentals", "Tooling and simulation", "Prototype proof"],
        "rubric": ["Technical correctness", "Documentation", "Safety", "Testing", "Iteration"],
    },
    "research": {
        "id": "research",
        "label": "Research",
        "target_roles": ["Research Assistant", "MS/PhD Applicant", "Research Engineer"],
        "skill_taxonomy": ["Literature Review", "Methods", "Experiment Design", "Statistics", "Writing", "Reproducibility"],
        "market_sources": ["papers", "lab openings", "conference calls", "research internships"],
        "proof_types": ["paper summary", "replication study", "poster", "preprint", "research proposal"],
        "starter_projects": ["Replicate a recent paper", "Annotated literature map", "Small experimental benchmark"],
        "certifications": ["Research methods courses", "Statistics courses"],
        "competitions": ["Research internships", "Poster competitions", "Paper reading groups"],
        "phases": ["Reading and methods", "Replication", "Original research direction"],
        "rubric": ["Source quality", "Method clarity", "Reproducibility", "Writing", "Novelty"],
    },
    "entrepreneurship": {
        "id": "entrepreneurship",
        "label": "Entrepreneurship",
        "target_roles": ["Founder", "Startup Operator", "Growth Builder"],
        "skill_taxonomy": ["Problem Discovery", "MVP", "Sales", "Growth", "Finance", "Pitching", "Operations"],
        "market_sources": ["startup news", "accelerators", "customer forums", "funding reports"],
        "proof_types": ["landing page", "customer interviews", "MVP", "traction dashboard", "pitch deck"],
        "starter_projects": ["No-code MVP with 10 customer interviews", "Problem validation memo", "Revenue experiment dashboard"],
        "certifications": ["Y Combinator Startup School", "IIM entrepreneurship programs"],
        "competitions": ["Startup pitch competitions", "E-cell events", "Hackathons"],
        "phases": ["Problem validation", "MVP and distribution", "Traction proof"],
        "rubric": ["Customer evidence", "Speed", "Distribution", "Revenue logic", "Learning loops"],
    },
}


def list_domain_packs() -> list[dict]:
    return list(DOMAIN_PACKS.values())


def get_domain_pack(domain_id: str) -> dict:
    return DOMAIN_PACKS.get(domain_id, DOMAIN_PACKS["cs_ai"])


def infer_domain_pack(target_role: str | None) -> dict:
    if not target_role:
        return DOMAIN_PACKS["cs_ai"]
    role = target_role.lower()
    keyword_map = {
        "data": ["data", "analyst", "scientist", "ml engineer"],
        "design": ["design", "ux", "ui", "figma"],
        "product": ["product", "pm", "apm"],
        "finance": ["finance", "investment", "quant", "risk", "cfa"],
        "core_engineering": ["mechanical", "electrical", "civil", "robotics", "electronics"],
        "research": ["research", "phd", "paper", "scientist"],
        "entrepreneurship": ["founder", "startup", "entrepreneur", "business"],
        "cs_ai": ["software", "developer", "backend", "fullstack", "ai", "llm", "cloud"],
    }
    for domain_id, keywords in keyword_map.items():
        if any(keyword in role for keyword in keywords):
            return DOMAIN_PACKS[domain_id]
    return DOMAIN_PACKS["cs_ai"]
