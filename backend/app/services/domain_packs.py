"""Field registry: one pack per career field, so Delta works for every learner,
not just software/CS students.

`resolve_field()` is THE way to decide a user's field. Never assume tech:
- an explicit `profile["field"]` (chosen at intake / in the profile) wins;
- otherwise whole-word keyword matching over the profile's role, goals, major,
  job and exam (target role weighted highest);
- with no signal, the neutral `general` pack (never `cs_ai`).

Pack keys used across the app:
  keywords            whole words / phrases for resolution
  is_tech             coding sandbox, GitHub-style proof, LeetCode habits apply
  phases / phase_guidance   3 roadmap phases and what each means in this field
  skill_taxonomy      core skills (also the fallback roadmap + market skills)
  proof_types / portfolio_hint   what "proof of work" looks like here
  interview_formats   field-specific interview styles (case / scenario round)
  exam_tracks         common exams/licences
  opportunity_queries search terms for competitions, internships, fellowships
  weekly_habit        the field's recurring practice (LeetCode equivalent)
"""
from __future__ import annotations

import re

DOMAIN_PACKS = {
    "cs_ai": {
        "id": "cs_ai",
        "label": "Software & IT",
        "is_tech": True,
        "keywords": [
            "software", "developer", "programmer", "programming", "coding", "sde", "sre", "devops", "cloud", "aws",
            "full stack", "fullstack", "frontend", "front end", "backend", "back end", "web developer", "app developer",
            "android", "ios developer", "ai", "ai engineer", "artificial intelligence", "llm", "computer science",
            "computer engineering", "cse", "bca", "mca", "information technology", "it support", "cybersecurity",
            "cyber security", "network engineer", "blockchain", "game developer", "software testing", "qa engineer",
            "software architect", "solutions architect", "cloud architect", "software engineer", "system design",
        ],
        "target_roles": ["Software Engineer", "Backend Engineer", "Full-stack Developer", "AI Engineer"],
        "skill_taxonomy": ["Python", "Data Structures", "FastAPI", "SQL", "Docker", "System Design", "LLMs", "RAG", "Cloud"],
        "market_sources": ["job_posts", "github_trends", "hackathons", "leetcode", "codeforces", "kaggle"],
        "proof_types": ["GitHub project", "deployed demo", "technical README", "contest rank", "certificate"],
        "portfolio_hint": "GitHub repo or live demo link",
        "starter_projects": ["Career intelligence API with weekly planning", "RAG assistant with citations", "Dockerized full-stack dashboard"],
        "certifications": ["AWS Cloud Practitioner", "Docker Certified Associate", "DeepLearning.AI LLM courses"],
        "competitions": ["Kaggle", "Codeforces", "LeetCode", "Unstop Hackathons"],
        "phases": ["Programming foundations", "Backend and data systems", "AI/cloud production proof"],
        "phase_guidance": [
            "core language syntax, data structures and the basic libraries/tools of the stack",
            "intermediate systems: databases, APIs, workflows, testing, containerization or core frameworks",
            "advanced architecture, scaling, specialisation and deployment patterns",
        ],
        "interview_formats": ["coding and CS fundamentals questions", "system design discussion", "project deep-dive"],
        "exam_tracks": ["GATE"],
        "opportunity_queries": ["hackathon", "software engineering internship", "open source program"],
        "weekly_habit": {"title": "Solve 3 coding problems", "description": "Keep problem-solving sharp with 3 timed DSA problems.", "minutes": 60},
        "rubric": ["Runs locally", "Has tests", "Shows architecture", "Uses real data", "Explains tradeoffs"],
    },
    "data": {
        "id": "data",
        "label": "Data & Analytics",
        "is_tech": True,
        "keywords": [
            "data", "data analyst", "data scientist", "data science", "data engineer", "analytics", "business intelligence",
            "power bi", "tableau", "machine learning", "ml engineer", "statistician", "data analytics",
        ],
        "target_roles": ["Data Analyst", "Data Scientist", "ML Engineer", "BI Analyst"],
        "skill_taxonomy": ["SQL", "Excel", "Statistics", "Python", "Visualization", "Dashboards", "Machine Learning", "Experimentation"],
        "market_sources": ["job_posts", "kaggle", "analytics_case_studies", "company_reports"],
        "proof_types": ["case study", "notebook", "dashboard", "model card", "data story"],
        "portfolio_hint": "dashboard, notebook or case-study link",
        "starter_projects": ["Hiring market analysis dashboard", "End-to-end churn prediction case study", "SQL portfolio with business questions"],
        "certifications": ["Google Data Analytics", "Microsoft PL-300", "TensorFlow Developer"],
        "competitions": ["Kaggle", "Analytics Vidhya", "Unstop case competitions"],
        "phases": ["Data fundamentals", "Modeling and analysis", "Business-facing portfolio proof"],
        "phase_guidance": [
            "spreadsheets, SQL, statistics basics and clean data handling",
            "analysis, visualization, dashboards and (for scientists) modelling",
            "end-to-end case studies answering real business questions",
        ],
        "interview_formats": ["SQL and statistics questions", "a business case to analyse with data", "dashboard or project walkthrough"],
        "exam_tracks": [],
        "opportunity_queries": ["data analytics case competition", "data analyst internship", "kaggle competition"],
        "weekly_habit": {"title": "Solve 2 SQL/analytics problems", "description": "Write two queries or analyses on a public dataset.", "minutes": 45},
        "rubric": ["Clear question", "Clean data", "Correct metrics", "Visual insight", "Business recommendation"],
    },
    "design": {
        "id": "design",
        "label": "Design & Architecture",
        "is_tech": False,
        "keywords": [
            "design", "designer", "ux", "ui", "ui ux", "figma", "graphic", "graphic designer", "product designer",
            "visual designer", "interior design", "interior designer", "fashion", "fashion design", "architect",
            "architecture", "b arch", "animation", "animator", "illustrator", "motion graphics", "industrial design",
        ],
        "target_roles": ["Product Designer", "UX Designer", "Graphic Designer", "Interior Designer", "Architect"],
        "skill_taxonomy": ["Design Fundamentals", "User Research", "Figma", "Prototyping", "Visual Systems", "Usability Testing", "Portfolio Storytelling"],
        "market_sources": ["portfolio reviews", "design job posts", "product teardowns", "design challenges"],
        "proof_types": ["case study", "prototype", "design system", "research notes", "portfolio piece"],
        "portfolio_hint": "Behance, Dribbble or portfolio link",
        "starter_projects": ["Student career app redesign", "Fintech onboarding case study", "Design system for a dashboard"],
        "certifications": ["Google UX Design", "Interaction Design Foundation"],
        "competitions": ["Designathons", "Unstop design challenges"],
        "phases": ["Visual and design foundations", "Research-backed case studies", "Portfolio storytelling"],
        "phase_guidance": [
            "design principles, tools (e.g. Figma/AutoCAD/Illustrator) and fundamentals of the discipline",
            "real briefs: research, iterations, critique and usability or client feedback",
            "a polished portfolio of 3-4 case studies that explain decisions",
        ],
        "interview_formats": ["portfolio walkthrough", "a design critique of an existing product or space", "a whiteboard design challenge"],
        "exam_tracks": ["NID DAT", "UCEED", "CEED", "NATA"],
        "opportunity_queries": ["design challenge", "design internship", "designathon"],
        "weekly_habit": {"title": "One design challenge", "description": "Do one small design exercise and post it to your portfolio.", "minutes": 60},
        "rubric": ["Problem clarity", "Research depth", "Interaction quality", "Visual polish", "Decision rationale"],
    },
    "product": {
        "id": "product",
        "label": "Product Management",
        "is_tech": False,
        "keywords": ["product manager", "associate product manager", "apm", "product management", "product owner", "product analyst"],
        "target_roles": ["Product Manager", "Associate PM", "Product Analyst"],
        "skill_taxonomy": ["User Problems", "Metrics", "Prioritization", "Roadmapping", "Experimentation", "Communication"],
        "market_sources": ["APM job posts", "product teardowns", "startup case studies", "business news"],
        "proof_types": ["product teardown", "PRD", "metric dashboard", "user interview synthesis"],
        "portfolio_hint": "product teardown, PRD or case-study link",
        "starter_projects": ["PRD for a student career OS", "Growth teardown of an edtech app", "Metrics dashboard for a product funnel"],
        "certifications": ["Reforge courses", "Product School certificate"],
        "competitions": ["Case competitions", "Product teardowns", "Unstop PM challenges"],
        "phases": ["Product thinking", "Metrics and experimentation", "Portfolio case studies"],
        "phase_guidance": [
            "user problems, product sense and how products make money",
            "metrics, prioritisation, experiments and writing PRDs",
            "published teardowns and case studies that show judgement",
        ],
        "interview_formats": ["a product design case (improve a product)", "a metrics / root-cause case", "a prioritisation scenario"],
        "exam_tracks": [],
        "opportunity_queries": ["product management case competition", "APM internship", "product teardown challenge"],
        "weekly_habit": {"title": "One product teardown", "description": "Break down one app: users, problem, metrics, what you'd change.", "minutes": 45},
        "rubric": ["Problem framing", "User insight", "Metric logic", "Tradeoff quality", "Execution plan"],
    },
    "finance": {
        "id": "finance",
        "label": "Finance, Accounting & Commerce",
        "is_tech": False,
        "keywords": [
            "finance", "financial", "financial analyst", "investment", "investment banking", "investment analyst",
            "equity research", "accountant", "accounting", "accounts", "ca", "chartered accountant", "cma", "cfa", "cpa",
            "acca", "audit", "auditor", "tax", "taxation", "banking", "banker", "commerce", "b com", "bcom", "m com",
            "economics", "economist", "actuary", "actuarial", "insurance", "credit analyst", "risk analyst",
            "company secretary", "quant", "wealth management", "stock market", "trading",
        ],
        "target_roles": ["Financial Analyst", "Chartered Accountant", "Investment Analyst", "Auditor", "Banker"],
        "skill_taxonomy": ["Accounting", "Excel", "Financial Statements", "Taxation", "Valuation", "Markets", "Audit", "Communication"],
        "market_sources": ["finance job posts", "market news", "company filings", "case competitions"],
        "proof_types": ["valuation model", "market memo", "audit/tax case write-up", "case competition deck"],
        "portfolio_hint": "model, memo or case-study link (Drive/Notion)",
        "starter_projects": ["DCF valuation of an Indian listed company", "Sector market pulse memo", "Tax computation case file"],
        "certifications": ["CA/CMA/CS levels", "CFA Level 1", "NISM certificates", "FMVA"],
        "competitions": ["CFA Research Challenge", "Unstop finance case competitions", "Stock pitch competitions"],
        "phases": ["Accounting and markets", "Modeling and analysis", "Professional proof"],
        "phase_guidance": [
            "accounting principles, financial statements, Excel and how markets/banks work",
            "analysis and modelling: ratios, valuation, tax or audit procedures on real cases",
            "a professional portfolio: models, memos, case competitions and exam progress",
        ],
        "interview_formats": ["accounting and finance concept questions", "a valuation or financial-statement case", "a market or stock pitch discussion"],
        "exam_tracks": ["CA", "CMA", "CS", "CFA", "NISM", "ACCA"],
        "opportunity_queries": ["finance case competition", "stock pitch competition", "finance internship articleship"],
        "weekly_habit": {"title": "Analyse one company", "description": "Read one annual report or results and note 5 key numbers.", "minutes": 45},
        "rubric": ["Assumption quality", "Model correctness", "Market reasoning", "Risk awareness", "Clear memo"],
    },
    "business": {
        "id": "business",
        "label": "Business, Management & HR",
        "is_tech": False,
        "keywords": [
            "management", "manager", "mba", "bba", "business", "business analyst", "consulting", "consultant",
            "operations", "hr", "human resources", "recruiter", "talent acquisition", "supply chain", "logistics",
            "retail", "store manager", "administration", "project manager", "strategy", "procurement", "management trainee",
        ],
        "target_roles": ["Management Trainee", "Business Analyst", "Consultant", "HR Executive", "Operations Manager"],
        "skill_taxonomy": ["Business Fundamentals", "Excel", "Communication", "Problem Structuring", "Stakeholder Management", "Operations", "Presentation"],
        "market_sources": ["business job posts", "case competitions", "business news", "industry reports"],
        "proof_types": ["case study deck", "process improvement report", "business plan", "internship project report"],
        "portfolio_hint": "case-study deck or report link",
        "starter_projects": ["Market-entry case for a D2C brand", "Process improvement report for a local business", "HR policy benchmark study"],
        "certifications": ["Six Sigma Yellow/Green Belt", "Google Project Management", "SHRM / HR analytics courses"],
        "competitions": ["Case competitions (Unstop, B-school fests)", "Business plan contests"],
        "phases": ["Business foundations", "Applied cases and tools", "Professional proof"],
        "phase_guidance": [
            "how businesses work: functions, financial basics, Excel and structured communication",
            "applied cases: frameworks, analysis, presentations, real problems from companies",
            "proof recruiters trust: case competitions, internship projects, certifications",
        ],
        "interview_formats": ["a consulting-style case interview", "a guesstimate", "situational management questions"],
        "exam_tracks": ["CAT", "XAT", "GMAT", "CUET"],
        "opportunity_queries": ["case competition", "management internship", "business plan competition"],
        "weekly_habit": {"title": "Solve one business case", "description": "Structure and solve one case or guesstimate in writing.", "minutes": 45},
        "rubric": ["Structure", "Insight", "Numbers", "Recommendation", "Communication"],
    },
    "marketing": {
        "id": "marketing",
        "label": "Marketing, Sales & PR",
        "is_tech": False,
        "keywords": [
            "marketing", "digital marketing", "marketing manager", "seo", "sem", "sales", "sales executive", "brand",
            "branding", "advertising", "social media", "business development", "pr", "public relations",
            "growth marketing", "performance marketing", "account manager", "customer success", "market research",
        ],
        "target_roles": ["Digital Marketing Executive", "Sales Executive", "Brand Manager", "PR Associate"],
        "skill_taxonomy": ["Marketing Fundamentals", "Consumer Insight", "Content", "Digital Channels", "Analytics", "Sales Skills", "Communication"],
        "market_sources": ["marketing job posts", "campaign case studies", "industry reports", "brand news"],
        "proof_types": ["campaign case study", "content portfolio", "sales pitch recording", "analytics report"],
        "portfolio_hint": "campaign case study or content portfolio link",
        "starter_projects": ["Social media campaign for a local brand", "SEO audit of a website", "Sales pitch deck for a product"],
        "certifications": ["Google Ads / Analytics", "HubSpot Inbound Marketing", "Meta Blueprint"],
        "competitions": ["Marketing case competitions", "Ad-making contests", "Unstop marketing challenges"],
        "phases": ["Marketing foundations", "Channels and campaigns", "Results portfolio"],
        "phase_guidance": [
            "consumers, positioning, the marketing/sales funnel and core channels",
            "running real campaigns or sales outreach and measuring results",
            "a portfolio of campaigns, pitches and numbers you moved",
        ],
        "interview_formats": ["a marketing case (launch or grow a product)", "a sales role-play pitch", "campaign analysis questions"],
        "exam_tracks": [],
        "opportunity_queries": ["marketing case competition", "marketing internship", "ad making competition"],
        "weekly_habit": {"title": "Break down one campaign", "description": "Study one ad or campaign: audience, message, channel, result.", "minutes": 30},
        "rubric": ["Audience clarity", "Creativity", "Channel fit", "Measurement", "Persuasion"],
    },
    "core_engineering": {
        "id": "core_engineering",
        "label": "Core Engineering",
        "is_tech": False,
        "keywords": [
            "mechanical", "mechanical engineer", "civil", "civil engineer", "electrical", "electrical engineer",
            "electronics", "ece", "eee", "chemical engineer", "chemical engineering", "automobile", "aerospace",
            "production engineer", "manufacturing", "site engineer", "structural", "construction", "maintenance engineer",
            "instrumentation", "robotics", "mechatronics", "autocad", "solidworks", "hvac", "quality engineer",
            "design engineer", "power plant", "embedded", "vlsi",
        ],
        "target_roles": ["Mechanical Engineer", "Civil Engineer", "Electrical Engineer", "Site Engineer", "Design Engineer"],
        "skill_taxonomy": ["Engineering Fundamentals", "CAD", "Simulation", "Manufacturing", "Site Practices", "Safety Standards", "Documentation"],
        "market_sources": ["core job posts", "internship boards", "research labs", "hardware competitions"],
        "proof_types": ["CAD model", "simulation report", "prototype", "site/lab report", "technical presentation"],
        "portfolio_hint": "CAD files, report or project video link",
        "starter_projects": ["CAD and simulation portfolio piece", "Site visit and estimation report", "Failure analysis report"],
        "certifications": ["AutoCAD", "SolidWorks", "ANSYS", "STAAD Pro", "NPTEL courses"],
        "competitions": ["SAE BAJA / Supra", "Robotics contests", "Smart India Hackathon hardware tracks"],
        "phases": ["Engineering fundamentals", "Tools and simulation", "Project proof"],
        "phase_guidance": [
            "core subject fundamentals of the branch and engineering drawing",
            "industry tools (CAD, simulation, estimation software), standards and practical work",
            "projects, internships and reports that show you can deliver on site or in a plant",
        ],
        "interview_formats": ["core subject concept questions", "a practical site/plant problem scenario", "project or internship deep-dive"],
        "exam_tracks": ["GATE", "ESE", "State AE/JE exams"],
        "opportunity_queries": ["engineering design competition", "core engineering internship", "SAE competition"],
        "weekly_habit": {"title": "Practise core concepts", "description": "Solve 10 core-subject questions (GATE-style) or one design exercise.", "minutes": 45},
        "rubric": ["Technical correctness", "Documentation", "Safety", "Testing", "Iteration"],
    },
    "healthcare": {
        "id": "healthcare",
        "label": "Healthcare & Medicine",
        "is_tech": False,
        "keywords": [
            "nurse", "nursing", "staff nurse", "gnm", "anm", "doctor", "mbbs", "medical", "medicine", "neet", "neet pg",
            "pharmacy", "pharmacist", "b pharm", "pharma", "physiotherapist", "physiotherapy", "dentist", "bds",
            "healthcare", "hospital", "clinical", "lab technician", "radiology", "nutritionist", "dietitian",
            "public health", "paramedic", "optometrist", "psychologist", "counsellor",
        ],
        "target_roles": ["Staff Nurse", "Junior Doctor", "Pharmacist", "Physiotherapist", "Clinical Research Associate"],
        "skill_taxonomy": ["Clinical Knowledge", "Patient Care", "Pharmacology", "Clinical Procedures", "Documentation", "Communication", "Infection Control"],
        "market_sources": ["hospital job posts", "licensing bodies", "health news", "medical journals"],
        "proof_types": ["clinical logbook", "case presentation", "certification (BLS/ACLS)", "research poster"],
        "portfolio_hint": "certificate, case presentation or logbook link",
        "starter_projects": ["Case presentation on a common condition", "Patient education leaflet", "Infection-control audit summary"],
        "certifications": ["BLS", "ACLS", "Nursing/medical council registration", "GCP (clinical research)"],
        "competitions": ["Medical quizzes", "Case presentation contests", "Research poster sessions"],
        "phases": ["Clinical foundations", "Applied clinical practice", "Professional readiness"],
        "phase_guidance": [
            "core medical/nursing/pharmacy knowledge for the role and its guidelines",
            "applied practice: procedures, case reviews, patient communication, documentation",
            "licensing exams, certifications (BLS/ACLS), case presentations and interview readiness",
        ],
        "interview_formats": ["clinical scenario questions (what would you do)", "patient-communication role-play", "core clinical knowledge questions"],
        "exam_tracks": ["NEET-PG", "NEXT", "Nursing council licensing", "NCLEX", "GPAT"],
        "opportunity_queries": ["medical quiz competition", "hospital internship", "clinical research fellowship"],
        "weekly_habit": {"title": "Review one clinical case", "description": "Study one case: presentation, diagnosis, management and nursing/clinical care.", "minutes": 45},
        "rubric": ["Clinical accuracy", "Patient safety", "Communication", "Documentation", "Ethics"],
    },
    "law": {
        "id": "law",
        "label": "Law",
        "is_tech": False,
        "keywords": [
            "law", "legal", "lawyer", "advocate", "llb", "clat", "aibe", "corporate law", "litigation", "judiciary",
            "paralegal", "legal associate", "legal advisor", "law student", "master of laws",
        ],
        "target_roles": ["Legal Associate", "Litigation Associate", "Corporate Lawyer", "Judiciary Aspirant"],
        "skill_taxonomy": ["Legal Research", "Case Law", "Drafting", "Constitutional Law", "Contract Law", "Argumentation", "Communication"],
        "market_sources": ["law firm openings", "legal news", "moot court circuits", "bar notifications"],
        "proof_types": ["research memo", "moot court memorial", "case comment", "published article"],
        "portfolio_hint": "memo, case comment or publication link",
        "starter_projects": ["Case comment on a recent Supreme Court judgment", "Contract review memo", "Moot court memorial"],
        "certifications": ["AIBE", "Diploma courses (IPR, cyber law)", "Mediation training"],
        "competitions": ["Moot court competitions", "Legal essay competitions", "Client counselling contests"],
        "phases": ["Legal foundations", "Research and drafting", "Professional proof"],
        "phase_guidance": [
            "core subjects and how to read statutes and judgments",
            "legal research, drafting, case comments and moot practice",
            "internships, publications, moots and exam (AIBE/judiciary) readiness",
        ],
        "interview_formats": ["applying the law to a fact pattern", "a recent-judgment discussion", "drafting or negotiation scenario"],
        "exam_tracks": ["CLAT", "AILET", "AIBE", "Judiciary exams"],
        "opportunity_queries": ["moot court competition", "law firm internship", "legal essay competition"],
        "weekly_habit": {"title": "Summarise one judgment", "description": "Read one judgment and write a one-page case summary.", "minutes": 45},
        "rubric": ["Issue spotting", "Legal accuracy", "Use of authority", "Structure", "Advocacy"],
    },
    "education": {
        "id": "education",
        "label": "Teaching & Education",
        "is_tech": False,
        "keywords": [
            "teacher", "teaching", "b ed", "educator", "tutor", "professor", "lecturer", "tet", "ctet", "ugc net",
            "school teacher", "primary teacher", "faculty", "education", "trainer", "instructional design",
        ],
        "target_roles": ["School Teacher", "Lecturer", "Tutor", "Instructional Designer"],
        "skill_taxonomy": ["Subject Mastery", "Lesson Planning", "Classroom Management", "Assessment", "Communication", "Edtech Tools"],
        "market_sources": ["school/college openings", "education policy news", "edtech hiring"],
        "proof_types": ["demo lesson video", "lesson plans", "teaching portfolio", "student results"],
        "portfolio_hint": "demo lesson video or lesson-plan link",
        "starter_projects": ["Recorded 10-minute demo lesson", "Unit lesson plan with assessments", "Worksheet set for one chapter"],
        "certifications": ["CTET / State TET", "UGC-NET", "Google Certified Educator"],
        "competitions": ["Teaching fellowships (e.g. Teach For India)", "Lesson design challenges"],
        "phases": ["Subject and pedagogy foundations", "Teaching practice", "Professional proof"],
        "phase_guidance": [
            "subject depth plus pedagogy basics (how students learn)",
            "lesson planning, demo teaching, classroom management and assessment",
            "a teaching portfolio, demo videos and exam (TET/NET) readiness",
        ],
        "interview_formats": ["a demo lesson explanation", "classroom-management scenarios", "subject knowledge questions"],
        "exam_tracks": ["CTET", "State TET", "UGC-NET", "B.Ed entrance"],
        "opportunity_queries": ["teaching fellowship", "teaching internship", "education volunteering program"],
        "weekly_habit": {"title": "Plan and rehearse one lesson", "description": "Plan a 10-minute lesson and explain it out loud.", "minutes": 40},
        "rubric": ["Clarity", "Engagement", "Subject accuracy", "Assessment", "Inclusiveness"],
    },
    "hospitality": {
        "id": "hospitality",
        "label": "Hospitality, Travel & Aviation",
        "is_tech": False,
        "keywords": [
            "hotel", "hospitality", "hotel management", "tourism", "travel", "aviation", "cabin crew", "air hostess",
            "chef", "culinary", "event management", "front office", "food and beverage", "airline", "ground staff",
        ],
        "target_roles": ["Hotel Management Trainee", "Front Office Executive", "Cabin Crew", "Chef", "Event Coordinator"],
        "skill_taxonomy": ["Guest Service", "Communication", "Operations", "Food and Beverage", "Grooming", "Problem Handling", "Languages"],
        "market_sources": ["hotel and airline hiring", "travel industry news", "event industry"],
        "proof_types": ["internship/training certificate", "service case write-up", "event portfolio", "culinary portfolio"],
        "portfolio_hint": "certificate, event or culinary portfolio link",
        "starter_projects": ["Guest-complaint handling playbook", "Plan and budget a small event", "Signature dish portfolio"],
        "certifications": ["FSSAI food safety", "IATA courses", "Language certificates"],
        "competitions": ["Culinary competitions", "Hospitality case competitions"],
        "phases": ["Service foundations", "Operations practice", "Career readiness"],
        "phase_guidance": [
            "service standards, grooming, communication and how hotels/airlines/events operate",
            "hands-on practice in departments, guest-handling scenarios and operations",
            "internships, certifications, grooming and interview readiness",
        ],
        "interview_formats": ["guest-handling role-play", "situational service questions", "grooming and communication round"],
        "exam_tracks": ["NCHM JEE"],
        "opportunity_queries": ["hotel management internship", "culinary competition", "cabin crew recruitment"],
        "weekly_habit": {"title": "Practise one service scenario", "description": "Role-play one guest-handling scenario and note what you'd improve.", "minutes": 30},
        "rubric": ["Guest focus", "Communication", "Composure", "Standards", "Problem solving"],
    },
    "media": {
        "id": "media",
        "label": "Media, Journalism & Content",
        "is_tech": False,
        "keywords": [
            "journalist", "journalism", "content writer", "copywriter", "editor", "film", "filmmaker", "video editor",
            "photographer", "photography", "mass communication", "media", "content creator", "reporter", "anchor", "writer",
        ],
        "target_roles": ["Journalist", "Content Writer", "Video Editor", "Copywriter"],
        "skill_taxonomy": ["Writing", "Storytelling", "Research", "Editing", "Video", "Audience Growth", "Ethics"],
        "market_sources": ["newsroom openings", "agency hiring", "media news"],
        "proof_types": ["published articles", "video reel", "writing portfolio", "podcast episode"],
        "portfolio_hint": "published work, reel or portfolio link",
        "starter_projects": ["Three published explainer articles", "60-second documentary reel", "Brand copy portfolio"],
        "certifications": ["Google News Initiative", "Editing software certificates"],
        "competitions": ["Short film festivals", "Writing competitions", "Fellowships"],
        "phases": ["Craft foundations", "Publishing practice", "Portfolio and network"],
        "phase_guidance": [
            "writing/editing/visual craft basics and media ethics",
            "regular publishing, pitching and feedback from editors or audiences",
            "a strong portfolio of published work and industry connections",
        ],
        "interview_formats": ["a pitch-a-story exercise", "editing or writing task discussion", "portfolio walkthrough"],
        "exam_tracks": ["IIMC entrance"],
        "opportunity_queries": ["writing competition", "journalism internship", "short film festival"],
        "weekly_habit": {"title": "Publish one piece", "description": "Write, shoot or edit one short piece and publish it.", "minutes": 60},
        "rubric": ["Story", "Accuracy", "Craft", "Audience", "Ethics"],
    },
    "public_service": {
        "id": "public_service",
        "label": "Government & Public Service",
        "is_tech": False,
        "keywords": [
            "upsc", "ias", "ips", "ifs", "civil services", "gpsc", "mpsc", "psc", "ssc", "ssc cgl", "bank po", "ibps",
            "sbi po", "rbi grade b", "railway", "rrb", "government job", "govt job", "government exam", "defence", "nda",
            "cds", "army", "navy", "air force", "police",
        ],
        "target_roles": ["Civil Services (UPSC/State PSC)", "Bank PO", "SSC Officer", "Defence Officer"],
        "skill_taxonomy": ["Current Affairs", "General Studies", "Quantitative Aptitude", "Reasoning", "Answer Writing", "Essay", "Interview Skills"],
        "market_sources": ["exam notifications", "official syllabi", "current affairs"],
        "proof_types": ["mock test scores", "answer-writing practice", "revision notes"],
        "portfolio_hint": "mock test scorecard or answer-writing link",
        "starter_projects": ["30-day current affairs notes", "Weekly answer-writing practice", "Full-length mock test analysis"],
        "certifications": [],
        "competitions": ["All-India mock test series", "Essay competitions", "Quiz competitions"],
        "phases": ["Syllabus foundations", "Practice and revision", "Exam and interview readiness"],
        "phase_guidance": [
            "the official syllabus, standard books and daily current affairs",
            "regular mocks, answer writing, previous-year papers and revision cycles",
            "full-length mocks, weak-area fixes and personality-test/interview preparation",
        ],
        "interview_formats": ["personality-test style questions on current affairs and your background", "situational/ethics questions", "opinion on a policy issue"],
        "exam_tracks": ["UPSC CSE", "State PSC", "SSC CGL", "IBPS PO", "SBI PO", "RBI Grade B", "NDA/CDS"],
        "opportunity_queries": ["free mock test series", "essay competition", "current affairs quiz"],
        "weekly_habit": {"title": "Take one timed mock", "description": "Attempt one timed sectional mock and analyse mistakes.", "minutes": 60},
        "rubric": ["Accuracy", "Speed", "Coverage", "Analysis", "Expression"],
    },
    "research": {
        "id": "research",
        "label": "Science & Research",
        "is_tech": False,
        "keywords": [
            "research", "researcher", "phd", "scientist", "research assistant", "research scientist", "msc", "m sc",
            "physics", "chemistry", "biology", "biotechnology", "microbiology", "mathematics", "academia", "postdoc",
        ],
        "target_roles": ["Research Assistant", "MS/PhD Applicant", "Lab Scientist"],
        "skill_taxonomy": ["Literature Review", "Research Methods", "Experiment Design", "Statistics", "Scientific Writing", "Reproducibility"],
        "market_sources": ["papers", "lab openings", "conference calls", "research internships"],
        "proof_types": ["paper summary", "replication study", "poster", "preprint", "research proposal"],
        "portfolio_hint": "paper, poster or Google Scholar link",
        "starter_projects": ["Replicate a recent paper", "Annotated literature map", "Small experiment with a written report"],
        "certifications": ["Research methods courses", "Statistics courses"],
        "competitions": ["Research internships", "Poster competitions", "Science olympiads"],
        "phases": ["Reading and methods", "Replication", "Original research direction"],
        "phase_guidance": [
            "reading papers, core methods and lab/analysis basics in the subject",
            "replicating results, running small experiments, writing them up",
            "an original question, a proposal or poster, and applications to labs/programs",
        ],
        "interview_formats": ["explaining your research or a paper", "methods and experiment-design questions", "core subject questions"],
        "exam_tracks": ["CSIR-NET", "GATE", "GRE", "JAM"],
        "opportunity_queries": ["research internship", "summer research fellowship", "science poster competition"],
        "weekly_habit": {"title": "Read and summarise one paper", "description": "Read one paper and write a 5-line summary of its method and result.", "minutes": 60},
        "rubric": ["Source quality", "Method clarity", "Reproducibility", "Writing", "Novelty"],
    },
    "entrepreneurship": {
        "id": "entrepreneurship",
        "label": "Entrepreneurship",
        "is_tech": False,
        "keywords": ["founder", "co founder", "startup", "entrepreneur", "entrepreneurship", "own business", "start a business"],
        "target_roles": ["Founder", "Startup Operator", "Growth Builder"],
        "skill_taxonomy": ["Problem Discovery", "MVP", "Sales", "Growth", "Finance", "Pitching", "Operations"],
        "market_sources": ["startup news", "accelerators", "customer forums", "funding reports"],
        "proof_types": ["landing page", "customer interviews", "MVP", "traction dashboard", "pitch deck"],
        "portfolio_hint": "landing page, pitch deck or traction link",
        "starter_projects": ["No-code MVP with 10 customer interviews", "Problem validation memo", "Revenue experiment dashboard"],
        "certifications": ["Y Combinator Startup School", "IIM entrepreneurship programs"],
        "competitions": ["Startup pitch competitions", "E-cell events", "Business plan contests"],
        "phases": ["Problem validation", "MVP and distribution", "Traction proof"],
        "phase_guidance": [
            "finding a real problem and talking to customers",
            "a minimum viable product and the first distribution channel",
            "traction, revenue and a pitch backed by evidence",
        ],
        "interview_formats": ["a pitch of your idea", "a go-to-market case", "questions on unit economics"],
        "exam_tracks": [],
        "opportunity_queries": ["startup pitch competition", "incubator application", "business plan competition"],
        "weekly_habit": {"title": "Talk to 3 potential customers", "description": "Hold three short customer conversations and log what you learned.", "minutes": 60},
        "rubric": ["Customer evidence", "Speed", "Distribution", "Revenue logic", "Learning loops"],
    },
    "general": {
        "id": "general",
        "label": "General / Exploring",
        "is_tech": False,
        "keywords": [],
        "target_roles": [],
        "skill_taxonomy": ["Communication", "Problem Solving", "Digital Literacy", "Domain Knowledge", "Professional Skills", "Self-management"],
        "market_sources": ["job posts", "industry news"],
        "proof_types": ["project report", "certificate", "portfolio piece", "presentation"],
        "portfolio_hint": "link to your work (Drive, portfolio, certificate)",
        "starter_projects": ["A small project in your area of interest", "Informational interviews with 3 professionals", "A short course with a certificate"],
        "certifications": ["Recognised short courses in your chosen field"],
        "competitions": ["Quizzes, case and essay competitions in your area"],
        "phases": ["Foundations", "Applied practice", "Proof and readiness"],
        "phase_guidance": [
            "the fundamentals of the chosen field and the skills employers in it list most",
            "applied practice: projects, internships or volunteering with real feedback",
            "proof employers trust (projects, certificates, results) and interview readiness",
        ],
        "interview_formats": ["situational questions about real work in the role", "questions on your projects and motivation"],
        "exam_tracks": [],
        "opportunity_queries": ["internship", "competition for students", "fellowship"],
        "weekly_habit": {"title": "Weekly skill practice", "description": "Spend one focused session practising the skill your plan targets this week.", "minutes": 45},
        "rubric": ["Clarity", "Effort", "Evidence", "Reflection", "Growth"],
    },
}

# Tie-break order: specific fields before broad ones.
_PRIORITY = [
    "public_service", "healthcare", "law", "education", "hospitality", "media", "design", "data", "product",
    "finance", "marketing", "core_engineering", "cs_ai", "research", "entrepreneurship", "business", "general",
]

# Profile fields used for resolution, with weights (the target role counts most).
_PROFILE_FIELDS = [
    ("target_role", 3), ("goal_direction", 2), ("current_role", 2), ("industry", 2), ("target_exam", 2),
    ("major", 1), ("education_stage", 1), ("career_goals", 1), ("target_industries", 1),
]


def _normalize(text) -> str:
    if isinstance(text, (list, tuple)):
        text = " ".join(str(t) for t in text)
    return " " + re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip() + " "


def _scores(text: str, weight: int = 1) -> dict[str, int]:
    scores: dict[str, int] = {}
    for pid, pack in DOMAIN_PACKS.items():
        s = 0
        for kw in pack["keywords"]:
            if f" {kw} " in text:
                s += len(kw.split())  # phrases are more specific than single words
        if s:
            scores[pid] = s * weight
    return scores


def _best(scores: dict[str, int]) -> dict:
    if not scores:
        return DOMAIN_PACKS["general"]
    top = max(scores.values())
    for pid in _PRIORITY:
        if scores.get(pid) == top:
            return DOMAIN_PACKS[pid]
    return DOMAIN_PACKS["general"]


def resolve_field(profile: dict | None = None, text: str | None = None) -> dict:
    """The user's field pack. Explicit profile["field"] wins; then weighted
    whole-word keyword matching; else the neutral `general` pack."""
    profile = profile or {}
    explicit = profile.get("field")
    if explicit in DOMAIN_PACKS:
        return DOMAIN_PACKS[explicit]
    total: dict[str, int] = {}
    for key, weight in _PROFILE_FIELDS:
        if profile.get(key):
            for pid, s in _scores(_normalize(profile[key]), weight).items():
                total[pid] = total.get(pid, 0) + s
    if text:
        for pid, s in _scores(_normalize(text), 3).items():
            total[pid] = total.get(pid, 0) + s
    return _best(total)


def field_for_user(user_id: str, db=None) -> dict:
    from app.services.profile_store import load_profile
    return resolve_field(load_profile(user_id, db=db) or {})


_AI_AGENT_MARKERS = ["multi-agent", "multi agent", "agentic rag", "adversarial ai", "llm orchestration", "long-term memory", "agent routing", "alpha.kore"]
_ELECTRICAL_MARKERS = [" electrical ", " electronics ", " circuit ", " pcb ", " arduino ", " power systems ", " embedded ", " iot ", " vlsi "]
_MECHANICAL_MARKERS = [" mechanical ", " cad ", " solidworks ", " autocad ", " thermodynamics ", " manufacturing ", " robotics ", " ansys ", " automobile "]


def template_key(pack_id: str, text: str) -> str:
    """Key for the older proof/long-horizon/chat templates
    (ai_agents | commerce | mechanical | electrical | arts | general)."""
    text = f" {(text or '').lower()} "
    if pack_id == "cs_ai":
        return "ai_agents" if any(m in text for m in _AI_AGENT_MARKERS) else "general"
    if pack_id in ("finance", "business", "marketing", "entrepreneurship", "product"):
        return "commerce"
    if pack_id == "core_engineering":
        if any(m in text for m in _ELECTRICAL_MARKERS):
            return "electrical"
        if any(m in text for m in _MECHANICAL_MARKERS):
            return "mechanical"
        return "general"
    if pack_id in ("design", "media"):
        return "arts"
    return "general"


def field_options() -> list[dict]:
    """For the profile form: [{id, label}] in a sensible display order."""
    order = ["cs_ai", "data", "core_engineering", "finance", "business", "marketing", "healthcare", "law", "design",
             "product", "education", "hospitality", "media", "public_service", "research", "entrepreneurship", "general"]
    return [{"id": pid, "label": DOMAIN_PACKS[pid]["label"]} for pid in order]


def list_domain_packs() -> list[dict]:
    return list(DOMAIN_PACKS.values())


def get_domain_pack(domain_id: str) -> dict:
    return DOMAIN_PACKS.get(domain_id, DOMAIN_PACKS["general"])


def infer_domain_pack(target_role: str | None) -> dict:
    """Back-compat: resolve from free text (a role or goal string)."""
    return resolve_field(text=target_role) if target_role else DOMAIN_PACKS["general"]
