"""
Ideal Frames and Pitfall Detection System for Delta Career OS.

This service defines the "gold standard" Target State Frames for each career
journey type, computes ingestion confidence and gaps, and implements detectors
for common student behavioral traps (e.g. Tutorial Hell, Certification Hoarding).
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("delta.ideal_frames")

# ===========================================================================
# Ideal Target State Frames Definition
# ===========================================================================

IDEAL_FRAMES: Dict[str, Dict[str, Any]] = {
    "software_engineering": {
        "id": "software_engineering",
        "label": "Software Engineering",
        "confidence_threshold": 0.80,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level", "role_focus"]}, # role_focus: backend, frontend, fullstack
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps", "skill_depth", "dsa_comfort"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["projects", "github_presence"]}
        ],
        "optional_nodes": [
            {"type": "preference", "fields": ["mentor_preference", "team_size_preference"]},
            {"type": "evidence", "fields": ["hackathons", "open_source_contributions"]}
        ],
        "critical_gaps": ["current_skills", "dsa_comfort", "github_presence", "projects", "time_limit"],
        "market_search_template": "{role_focus} software engineer entry-level requirements skills 2026 {location}"
    },
    "data_ai": {
        "id": "data_ai",
        "label": "Data Science & AI Engineering",
        "confidence_threshold": 0.82,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level", "ai_subfield"]}, # ai_subfield: data_science, ml_engineering, ai_research
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps", "math_comfort", "llm_rag_familiarity"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits", "gpu_access"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["projects", "github_presence", "kaggle_presence"]}
        ],
        "optional_nodes": [
            {"type": "evidence", "fields": ["papers_published", "huggingface_presence"]}
        ],
        "critical_gaps": ["current_skills", "math_comfort", "llm_rag_familiarity", "projects", "gpu_access"],
        "market_search_template": "{ai_subfield} developer skills hiring trends 2026 {location}"
    },
    "quant_development": {
        "id": "quant_development",
        "label": "Quant Development",
        "confidence_threshold": 0.85,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level"]},
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps", "math_comfort", "cpp_depth", "low_latency_knowledge", "finance_knowledge"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["projects", "github_presence", "competitive_programming_rank"]}
        ],
        "optional_nodes": [
            {"type": "evidence", "fields": ["linux_kernel_contributions", "hardware_experience"]}
        ],
        "critical_gaps": ["cpp_depth", "math_comfort", "low_latency_knowledge", "finance_knowledge", "competitive_programming_rank"],
        "market_search_template": "quant developer c++ low latency mathematical finance job requirements 2026 {location}"
    },
    "product_management": {
        "id": "product_management",
        "label": "Product Management",
        "confidence_threshold": 0.78,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level"]},
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps", "communication_level", "product_sense_level", "analytics_comfort"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["projects", "product_teardowns", "case_study_presence"]}
        ],
        "optional_nodes": [
            {"type": "evidence", "fields": ["internships", "design_portfolio"]}
        ],
        "critical_gaps": ["product_sense_level", "communication_level", "analytics_comfort", "projects", "product_teardowns"],
        "market_search_template": "associate product manager apm requirements entry level 2026 {location}"
    },
    "entrepreneurship": {
        "id": "entrepreneurship",
        "label": "Entrepreneurship & Venture Building",
        "confidence_threshold": 0.80,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level"]},
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps", "risk_tolerance", "market_understanding", "mvp_speed"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["mvps_built", "customer_interviews", "traction_evidence"]}
        ],
        "optional_nodes": [
            {"type": "evidence", "fields": ["pitch_deck", "revenue_generated"]}
        ],
        "critical_gaps": ["mvp_speed", "market_understanding", "risk_tolerance", "mvps_built", "customer_interviews"],
        "market_search_template": "startup founder validation lean MVP models emerging trends 2026"
    },
    "general": {
        "id": "general",
        "label": "General Career OS (Exploratory)",
        "confidence_threshold": 0.70,
        "required_nodes": [
            {"type": "identity", "required_fields": ["education_stage", "location", "language_comfort", "self_awareness_level"]},
            {"type": "ambition", "required_fields": ["long_term_goals", "dream_roles", "preferred_industries", "confidence_level"]},
            {"type": "capability", "required_fields": ["current_skills", "technical_baseline", "identified_gaps"]},
            {"type": "constraint", "required_fields": ["time_limit", "device_access", "college_load", "financial_limits"]},
            {"type": "preference", "required_fields": ["learning_style", "content_type", "communication_tone"]},
            {"type": "motivation", "required_fields": ["motivation_profile", "risk_flags"]},
            {"type": "evidence", "required_fields": ["projects"]}
        ],
        "optional_nodes": [],
        "critical_gaps": ["current_skills", "long_term_goals", "time_limit", "projects"],
        "market_search_template": "entry-level tech career transitions skills demand 2026 {location}"
    }
}


def get_ideal_frame(journey_type: str) -> Dict[str, Any]:
    """Resolves a journey type to its Ideal Frame, falling back to general."""
    return IDEAL_FRAMES.get(journey_type, IDEAL_FRAMES["general"])


def compute_confidence_and_gaps(journey_type: str, user_frame: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates ingestion completion confidence score (0.0 to 1.0) and missing gaps.
    
    Arguments:
        journey_type: Type of journey (e.g., 'software_engineering')
        user_frame: Dict representing the user's populated cognitive profile fields.
                    Expected structure: {node_type: {field_name: value}}
    """
    ideal = get_ideal_frame(journey_type)
    required = ideal["required_nodes"]
    
    total_fields = 0
    filled_fields = 0
    missing_fields = []
    missing_critical = []
    
    critical_gaps = ideal["critical_gaps"]
    
    for node_spec in required:
        node_type = node_spec["type"]
        req_fields = node_spec["required_fields"]
        
        user_node_data = user_frame.get(node_type, {})
        
        for field in req_fields:
            total_fields += 1
            # Check if field exists and has a non-empty, meaningful value
            val = user_node_data.get(field)
            
            # Simple check for meaningful value (not empty string, empty list, etc.)
            is_filled = False
            if val is not None:
                if isinstance(val, str) and val.strip() and val.lower() not in ["", "none", "unknown", "needs discovery"]:
                    is_filled = True
                elif isinstance(val, list) and len(val) > 0:
                    is_filled = True
                elif isinstance(val, (int, float)):
                    is_filled = True
                elif isinstance(val, dict) and len(val) > 0:
                    is_filled = True
                elif isinstance(val, bool):
                    is_filled = True
            
            if is_filled:
                filled_fields += 1
            else:
                missing_fields.append(f"{node_type}.{field}")
                if field in critical_gaps or node_type in critical_gaps:
                    missing_critical.append(f"{node_type}.{field}")
                    
    confidence_score = (filled_fields / max(total_fields, 1))
    
    # Ingestion is complete if we cross the threshold and have no critical missing fields
    is_complete = confidence_score >= ideal["confidence_threshold"] and len(missing_critical) == 0
    
    return {
        "confidence_score": round(confidence_score, 2),
        "is_complete": is_complete,
        "missing_fields": missing_fields,
        "missing_critical": missing_critical,
        "threshold": ideal["confidence_threshold"]
    }


# ===========================================================================
# Pitfall Detector Class
# ===========================================================================

class PitfallDetector:
    """Scans the user's cognitive state and answers to detect behavioral traps."""
    
    def detect_pitfalls(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scans the user's full structured frame for common behavioral traps."""
        pitfalls = []
        pitfalls.extend(self._check_certification_hoarding(user_frame))
        pitfalls.extend(self._check_tutorial_hell(user_frame))
        pitfalls.extend(self._check_skill_hoarding(user_frame))
        pitfalls.extend(self._check_efficiency_over_depth(user_frame))
        pitfalls.extend(self._check_imposter_syndrome(user_frame))
        pitfalls.extend(self._check_shiny_object_syndrome(user_frame))
        return pitfalls

    def _check_certification_hoarding(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """High certificate count but low GitHub/evidence code contributions."""
        evidence = user_frame.get("evidence", {})
        capabilities = user_frame.get("capability", {})
        
        certs = evidence.get("certificates") or evidence.get("certifications") or []
        projects = evidence.get("projects") or []
        git_presence = evidence.get("github_presence") or "needs creation"
        
        cert_count = len(certs) if isinstance(certs, list) else int(certs) if isinstance(certs, (int, float)) else 0
        proj_count = len(projects) if isinstance(projects, list) else 0
        
        # High certifications (e.g. >= 4) but low project proof
        if cert_count >= 4 and (proj_count <= 1 or git_presence == "needs creation" or "minimal" in str(git_presence).lower()):
            severity = min(0.3 + (cert_count - proj_count) * 0.1, 1.0)
            return [{
                "pitfall_type": "certification_hoarding",
                "severity": round(severity, 2),
                "evidence": f"High certification count ({cert_count}) but low project evidence ({proj_count}) and weak GitHub presence.",
                "intervention": "Lock certificate-heavy pathways. Inject a strict Project Sprint to build one deployment from scratch.",
                "challenge_question": f"I notice you have accumulated {cert_count} certifications but haven't deployed many custom projects. Let's shift from collecting credentials to building. Can we design one project that proves you can build without a curriculum?"
            }]
        return []

    def _check_tutorial_hell(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """High learning activity, courses completed, but zero self-directed repos or projects."""
        evidence = user_frame.get("evidence", {})
        preferences = user_frame.get("preference", {})
        
        courses = evidence.get("courses_completed") or []
        projects = evidence.get("projects") or []
        learning_style = preferences.get("learning_style") or ""
        
        course_count = len(courses) if isinstance(courses, list) else 0
        proj_count = len(projects) if isinstance(projects, list) else 0
        
        if (course_count >= 3 or "tutorial" in str(learning_style).lower()) and proj_count == 0:
            return [{
                "pitfall_type": "tutorial_hell",
                "severity": 0.8,
                "evidence": f"User completed {course_count} courses/tutorials but has 0 self-directed projects.",
                "intervention": "Enforce a 'No-Tutorial' project building rule. Create a scaffolded sandbox challenge.",
                "challenge_question": "It's easy to get comfortable watching instructors write perfect code. But the real learning happens when things break. Can you tell me about a time you tried to build something entirely outside of a tutorial, even if it failed?"
            }]
        return []

    def _check_skill_hoarding(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Claiming a massive list of skills but having zero projects or evidence for most of them."""
        capabilities = user_frame.get("capability", {})
        evidence = user_frame.get("evidence", {})
        
        skills = capabilities.get("current_skills") or []
        projects = evidence.get("projects") or []
        
        skill_count = len(skills) if isinstance(skills, list) else 0
        proj_count = len(projects) if isinstance(projects, list) else 0
        
        if skill_count >= 12 and proj_count <= 1:
            severity = min(0.4 + (skill_count - proj_count * 5) * 0.05, 0.95)
            return [{
                "pitfall_type": "skill_hoarding",
                "severity": round(severity, 2),
                "evidence": f"User claims {skill_count} skills but only has {proj_count} project(s) to prove them.",
                "intervention": "Restrict new skill additions. Require a 'Depth Verification Project' that exercises 3 claimed skills at once.",
                "challenge_question": f"You've listed {skill_count} skills, including some heavy technologies. Recruiters are highly skeptical of long skill lists without matching projects. If you had to pick just 3 skills from your list to defend in an interview, which would they be?"
            }]
        return []

    def _check_efficiency_over_depth(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prefers simple short certificates or quizzes over deep capstone projects."""
        preferences = user_frame.get("preference", {})
        motivation = user_frame.get("motivation", {})
        
        content_type = preferences.get("content_type") or []
        motivation_profile = motivation.get("motivation_profile") or ""
        
        if ("short quizzes" in content_type or "quizzes" in content_type) and ("heavy projects" not in content_type and "capstones" not in content_type) and "speed" in str(motivation_profile).lower():
            return [{
                "pitfall_type": "efficiency_over_depth",
                "severity": 0.6,
                "evidence": "Preference indicates small tests/quizzes and fast completion over intensive project building.",
                "intervention": "Gamify a deep building project by breaking it into daily tiny milestones to match their speed preference.",
                "challenge_question": "You mentioned you prefer quick checks and fast progress. That's great for building habits, but high-paying tech roles require deep problem-solving stamina. How would you feel about breaking a massive, impressive project into 15-minute daily challenges?"
            }]
        return []

    def _check_imposter_syndrome(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """High capabilities/achievements but extremely low confidence/ambitions."""
        capabilities = user_frame.get("capability", {})
        ambitions = user_frame.get("ambition", {})
        
        skills = capabilities.get("current_skills") or []
        confidence = ambitions.get("confidence_level") or 1.0 # 0 to 1
        dream_roles = ambitions.get("dream_roles") or []
        
        skill_count = len(skills) if isinstance(skills, list) else 0
        confidence_val = float(confidence) if isinstance(confidence, (int, float)) else 0.5
        
        # High skill count (e.g. >= 6) but extremely low confidence score (e.g. <= 0.4)
        if skill_count >= 6 and confidence_val <= 0.4:
            return [{
                "pitfall_type": "imposter_syndrome",
                "severity": round(1.0 - confidence_val, 2),
                "evidence": f"User possesses {skill_count} core skills but reports a very low career confidence score ({confidence_val}).",
                "intervention": "Surface real market opportunities matching their current skills immediately. Trigger a 'Micro-Win' project.",
                "challenge_question": "You actually have a stronger technical baseline than most students at your stage. Yet, you seem hesitant about what you can achieve. What makes you feel like you aren't ready for elite roles yet?"
            }]
        return []

    def _check_shiny_object_syndrome(self, user_frame: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Frequent shifts across highly disparate domains without completing anything."""
        motivation = user_frame.get("motivation", {})
        capabilities = user_frame.get("capability", {})
        
        history = motivation.get("domain_switch_history") or []
        gaps = capabilities.get("identified_gaps") or []
        
        if len(history) >= 2 or ("web dev" in str(gaps).lower() and "ai" in str(gaps).lower() and "blockchain" in str(gaps).lower()):
            return [{
                "pitfall_type": "shiny_object_syndrome",
                "severity": 0.75,
                "evidence": "User's interest spans multiple unconnected tech fields (Web3, AI, Web Dev) without mastering foundations in any.",
                "intervention": "Implement a 'Focus Lock'. Restrict active tracking to ONE tech track for 4 weeks.",
                "challenge_question": "It's exciting to watch the tech world move fast—one week it's Web3, the next AI. But developers who jump around too quickly end up as perpetual beginners. If you had to commit to mastering just ONE domain for the next 30 days to build a working prototype, which would it be?"
            }]
        return []

    def detect_during_ingestion(self, answers: List[Dict[str, Any]], question_history: List[str]) -> List[Dict[str, Any]]:
        """
        Scans current ingestion conversation responses to catch red flags before 
        the profile is fully structured.
        
        Arguments:
            answers: List of {"role": str, "content": str} representing user messages.
            question_history: List of questions asked by the AI.
        """
        detected = []
        
        # Combine user answers
        all_user_text = " ".join([ans["content"].lower() for ans in answers if ans.get("role") == "user"])
        
        # 1. Check for Tutorial Hell signs during ingestion chat
        tutorial_keywords = ["tutorial hell", "only did courses", "watch video", "youtube tutorials", "udemy courses", "certificate only"]
        if any(kw in all_user_text for kw in tutorial_keywords):
            detected.append({
                "pitfall_type": "tutorial_hell",
                "severity": 0.65,
                "evidence": "User explicitly mentioned reliance on tutorial videos or courses without independent projects.",
                "intervention": "Prompt user for self-guided build interest immediately.",
                "challenge_question": "You mentioned taking several courses/tutorials. It's super common to get stuck in that loop! What's the biggest obstacle you face when trying to start a project completely on your own?"
            })
            
        # 2. Check for Shiny Object Syndrome signs
        switch_keywords = ["everything", "blockchain and ai", "web dev and machine learning", "want to learn all", "learn both web3 and generative ai"]
        if any(kw in all_user_text for kw in switch_keywords):
            detected.append({
                "pitfall_type": "shiny_object_syndrome",
                "severity": 0.7,
                "evidence": "User expressing intent to study highly disparate buzzword domains simultaneously.",
                "intervention": "Focus onboarding on core software foundations first.",
                "challenge_question": "Learning both Web Dev and AI simultaneously is incredibly tough and often leads to burnout. Which of those two holds the highest priority for your next immediate project?"
            })
            
        # 3. Check for Imposter Syndrome signs
        imposter_keywords = ["not good enough", "im not ready", "too beginner", "dont know if i can", "skeptical", "hard for me"]
        if any(kw in all_user_text for kw in imposter_keywords):
            detected.append({
                "pitfall_type": "imposter_syndrome",
                "severity": 0.6,
                "evidence": "User expresses self-doubt or under-confidence regarding baseline engineering skills.",
                "intervention": "Inject validation of their existing experiences in the next prompt.",
                "challenge_question": "It's completely normal to feel like you aren't ready. The tech industry is huge! But remember, every expert started exactly where you are. What is one technical concept you recently struggled with but eventually understood?"
            })

        return detected

    # ===========================================================================
    # Golden Path Benchmark
    # ===========================================================================

    def get_golden_path_benchmark(self, journey_type: str, year: int) -> Dict[str, Any]:
        """
        Returns the benchmark for what a 'top 1%' student achieves in a given year.
        
        Used to perform gap analysis against high-caliber competitors.
        """
        benchmarks = {
            "software_engineering": {
                1: {
                    "year": 1,
                    "phase": "CS Foundations & Scripting",
                    "expected_skills": ["Python or C++", "Git & GitHub", "Basic Data Structures", "Markdown & Linux basics"],
                    "expected_projects": 3,
                    "expected_evidence": ["GitHub profile active with 20+ green days", "1 clean CLI tool with a README", "Solved 50 LeetCode problems"],
                    "common_mistakes": ["Tutorial Hell", "Collecting certificates without coding", "Ignoring version control"],
                    "acceleration_trigger": "If behind benchmark by >30% (no Git or <1 project), trigger Git & CLI Boot Camp Sprint."
                },
                2: {
                    "year": 2,
                    "phase": "Backend Systems & Web Arch",
                    "expected_skills": ["FastAPI or Express", "SQL & Database Design", "Docker", "REST API principles", "DSA Intermediate"],
                    "expected_projects": 2,
                    "expected_evidence": ["1 deployed Fullstack or Backend API", "Dockerized project container", "100+ LeetCode problems solved"],
                    "common_mistakes": ["Copy-pasting database queries", "Building prompt-only simple websites", "Skipping unit tests"],
                    "acceleration_trigger": "If no database experience, inject Relational Database Design sprint."
                },
                3: {
                    "year": 3,
                    "phase": "Distributed Systems & Cloud Production",
                    "expected_skills": ["System Design", "CI/CD pipelines", "AWS or GCP", "Redis / Caching", "NoSQL"],
                    "expected_projects": 2,
                    "expected_evidence": ["System with caching and async queues", "Automated deployment pipeline", "Active open-source contribution"],
                    "common_mistakes": ["Focusing on trivial CSS changes", "No performance benchmarks for their system", "Not testing concurrent load"],
                    "acceleration_trigger": "If system has no load benchmarks, trigger Load-testing & Caching Sprint."
                },
                4: {
                    "year": 4,
                    "phase": "Industry-Ready Capstones & System Scalability",
                    "expected_skills": ["Advanced System Architecture", "Performance Tuning", "Monitoring / Observability", "Production Ops"],
                    "expected_projects": 1,
                    "expected_evidence": ["Production-grade capstone with 100+ active mock/real users", "Full monitoring suite (Prometheus/Grafana)"],
                    "common_mistakes": ["Submitting generic static college projects", "Lack of architectural trade-off justification"],
                    "acceleration_trigger": "If college project is generic, replace with a high-fidelity Career OS Capstone iteration."
                }
            },
            "data_ai": {
                1: {
                    "year": 1,
                    "phase": "Math, Stats & Core Python",
                    "expected_skills": ["Python", "Numpy & Pandas", "Descriptive Statistics", "Linear Algebra Foundations"],
                    "expected_projects": 2,
                    "expected_evidence": ["2 exploratory data analyses (EDA) on Kaggle dataset", "Clean Jupyter notebooks in GitHub"],
                    "common_mistakes": ["Skipping linear algebra", "Copying Kaggle notebooks without understanding"],
                    "acceleration_trigger": "If linear algebra math comfort is low, assign Mathematical Foundations for ML sprint."
                },
                2: {
                    "year": 2,
                    "phase": "Classical ML & Slicing/Feature Engineering",
                    "expected_skills": ["Scikit-Learn", "SQL", "Feature Engineering", "Classical Algorithms (Regression, Trees)", "Matplotlib/Seaborn"],
                    "expected_projects": 2,
                    "expected_evidence": ["1 end-to-end classification/regression project", "Top 20% ranking in a Kaggle playground competition"],
                    "common_mistakes": ["Ignoring data cleaning", "Using default hyperparameters without cross-validation"],
                    "acceleration_trigger": "If no Kaggle presence, assign Kaggle Playground Sprint."
                },
                3: {
                    "year": 3,
                    "phase": "Deep Learning & Generative AI Systems",
                    "expected_skills": ["PyTorch or TensorFlow", "Transformers", "Vector Databases", "LangChain/LlamaIndex", "RAG Pipelines"],
                    "expected_projects": 2,
                    "expected_evidence": ["Deployed RAG app with custom embedding search & evaluation", "Fine-tuned open-source model"],
                    "common_mistakes": ["Building prompt-only apps", "No vector search evaluation metrics", "Tutorial-only ML models"],
                    "acceleration_trigger": "If RAG app lacks validation set and metrics, trigger RAG Evaluation Sprint."
                },
                4: {
                    "year": 4,
                    "phase": "MLOps & AI Scale",
                    "expected_skills": ["MLflow or Weights & Biases", "Triton / FastChat", "Kubeflow / Airflow", "Model Observability"],
                    "expected_projects": 1,
                    "expected_evidence": ["Production ML pipeline with automated drift detection and monitoring", "Published technical research article"],
                    "common_mistakes": ["Notebook-only projects with zero deployment path"],
                    "acceleration_trigger": "If model is offline-only, trigger Dockerized ML Endpoint & Prometheus Monitoring sprint."
                }
            },
            "quant_development": {
                1: {
                    "year": 1,
                    "phase": "Advanced Calculus & Modern C++ Foundations",
                    "expected_skills": ["C++17/20", "Linear Algebra", "Algorithms & Complexity", "Linux Systems"],
                    "expected_projects": 2,
                    "expected_evidence": ["1 terminal C++ matrix math library", "LeetCode 150+ solved (C++)"],
                    "common_mistakes": ["Using raw pointers instead of smart pointers", "Ignoring algorithmic math foundations"],
                    "acceleration_trigger": "If no Linux familiarity or LeetCode presence, trigger Linux CLI & DSA C++ sprint."
                },
                2: {
                    "year": 2,
                    "phase": "Low-Level Optimization & Multi-threading",
                    "expected_skills": ["C++ Smart Pointers", "Multi-threading (std::thread)", "Memory Management", "Concurrency Patterns"],
                    "expected_projects": 2,
                    "expected_evidence": ["1 multi-threaded backtester in C++", "Performance benchmark analysis report"],
                    "common_mistakes": ["Creating race conditions", "Not understanding CPU cache lines"],
                    "acceleration_trigger": "If C++ backtester is single-threaded, assign Concurrent Backtesting sprint."
                },
                3: {
                    "year": 3,
                    "phase": "Low Latency Networking & Market Microstructure",
                    "expected_skills": ["Socket Programming", "TCP/UDP low-latency tuning", "Order Book Design", "Financial Markets Basics"],
                    "expected_projects": 2,
                    "expected_evidence": ["High-frequency limit order book simulator in C++", "UDP market data parser"],
                    "common_mistakes": ["Using heavy high-level libraries that introduce latency", "Ignoring lock-free queues"],
                    "acceleration_trigger": "If order book uses slow std::maps, trigger Lock-Free Order Book Re-architecting sprint."
                },
                4: {
                    "year": 4,
                    "phase": "Real-time Trading Engines",
                    "expected_skills": ["Linux Kernel bypass (Solarflare/DPDK)", "Low-latency systems architecture", "Quant backtesting infrastructure"],
                    "expected_projects": 1,
                    "expected_evidence": ["Ultra-low-latency C++ trading simulator running on mock UDP feed under 5 microseconds latency"],
                    "common_mistakes": ["No latency benchmarks under real load"],
                    "acceleration_trigger": "If latency is unmeasured, trigger Valgrind & Solarflare simulation latency sprint."
                }
            }
        }
        
        # Fall back to software_engineering or general defaults if not specified
        journey_key = journey_type if journey_type in benchmarks else "software_engineering"
        year_key = year if year in benchmarks[journey_key] else 1
        
        return benchmarks[journey_key][year_key]
