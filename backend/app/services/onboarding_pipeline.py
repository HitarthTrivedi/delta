"""Onboarding pipeline — processes user intake data using Gemini."""
import json
from app.services.ai_service import generate_response
from app.services.market_pulse import get_market_snapshot

def start_onboarding(raw_input: str, target_role: str = "AI Developer / Software Engineer") -> dict:
    """
    Initial step of conversational onboarding.
    Scans the raw input, fetches current market demand signals, creates custom prompts, 
    and returns a set of highly customized, adaptive follow-up questions targeting gaps.
    """
    # 1. Fetch structured market pulse signals for the target role
    market_pulse = get_market_snapshot(target_role)
    
    market_context = f"""
    Target Role: {target_role}
    Top Demanded Skills: {', '.join(market_pulse.get('top_demanded_skills', []))}
    Emerging Skills: {', '.join(market_pulse.get('emerging_skills', []))}
    Recruiter Language Focus: {', '.join(market_pulse.get('recruiter_language', []))}
    Market Warnings: {', '.join(market_pulse.get('market_warnings', []))}
    Suggested Project Patterns: {', '.join(market_pulse.get('project_patterns', []))}
    """
    
    prompt = f"""
    You are Delta Onboarding Intelligence, an elite career planning agent for Indian CS/engineering students.
    Your mission is to upgrade the onboarding intake into structured career intelligence.
    
    Current Market Expectations for this target role:
    {market_context}
    
    The student has expressed their career goals, aspirations, and background:
    "{raw_input}"
    
    Tasks:
    1. Parse their ambition, baseline context, and potential bottlenecks.
    2. Compare the user's starting capabilities and background against recruiter expectations in the Market Context.
    3. Generate exactly 3 highly customized, adaptive follow-up questions designed to probe specific gaps between their raw input and high-priority recruiter requirements:
       - Question 1: Probe their actual technical baseline with respect to a critical demanded skill (e.g. have they written code in Python/SQL, built backends, etc.).
       - Question 2: Probe their background and capability gaps (e.g. comfort level with logic/math, hands-on building preference, or why they target this role).
       - Question 3: Probe their real-world constraints and evidence proof capabilities (e.g. weekly study time limits, college load, GitHub repo presence).
       
    Output your response strictly as a JSON object with this format:
    {{
      "ambition_summary": "Short 1-2 sentence summary of their goals and how they align with {target_role}.",
      "adaptive_questions": [
        "First personalized question probing a technical baseline gap...",
        "Second personalized question probing a capability or comfort gap...",
        "Third personalized question probing constraints or evidence proof gaps..."
      ],
      "market_demand_focus": "A highly punchy, custom 1-sentence warning or focus alert based on 2026 recruiter pulse (e.g., 'Recruiters are rejecting prompt-only projects; you will need Dockerized API proof.')"
    }}
    """
    try:
        response_text = generate_response(prompt)
        # Parse JSON from response
        # Find json boundaries if markdown code block is returned
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        data = json.loads(response_text.strip())
        data["market_snapshot"] = market_pulse
        return data
    except Exception as e:
        print(f"Onboarding start error: {e}")
        # Return fallback high-quality custom questions matching target role
        return {
            "ambition_summary": f"Aspiring to become a world-class {target_role}.",
            "adaptive_questions": [
                f"What specific programming languages or tools have you experimented with so far?",
                "How comfortable are you with mathematics and logic (e.g., post-12th level, linear algebra)?",
                "How many hours per week can you realistically commit to hands-on building?"
            ],
            "market_demand_focus": "Focus on high-growth clusters like LLM orchestration, Docker containers, and clean coding practices.",
            "market_snapshot": market_pulse
        }

def finalize_onboarding(raw_input: str, follow_ups: list, answers: list) -> dict:
    """
    Finalize the onboarding pipeline.
    Combines initial input, questions asked, and answers provided to extract the complete, structured profile.
    Outputs a highly comprehensive schema to populate the Career Memory Profile.
    """
    qa_pairs = []
    for q, a in zip(follow_ups, answers):
        qa_pairs.append(f"Q: {q}\nA: {a}")
    qa_context = "\n\n".join(qa_pairs)

    prompt = f"""
    You are Delta Onboarding Intelligence. Your mission is to parse the student's initial ambition and their answers to personalized follow-up questions, extracting a complete, highly structured career intelligence profile.
    
    Initial Input:
    "{raw_input}"
    
    Conversational Answers:
    {qa_context}
    
    Tasks:
    Extract their profile into a JSON object. You MUST include exactly the following 10 keys:
    {{
      "identity_context": {{
        "name": "Student's name if mentioned, otherwise leave empty",
        "education_stage": "Stage of education (e.g. 1st year BTech, 2nd year CS, post-12th, absolute beginner)",
        "location": "Location if mentioned or inferred, otherwise 'unknown'",
        "language_comfort": "Preferred coding/comms languages or comfort level (e.g. English, Hinglish, Hindi)",
        "background_summary": "1-2 sentence demographic and educational context background.",
        "self_awareness_level": "Assessment of self-awareness (high, medium, low)"
      }},
      "ambition_map": {{
        "long_term_goals": ["List of long term ambitions/direction"],
        "short_term_targets": ["Immediate target roles or milestones"],
        "dream_roles": ["Dream roles (e.g., ML Engineer, Backend Developer)"],
        "preferred_industries": ["Target sectors/industries"],
        "confidence_level": "Stated or inferred career confidence (high, medium, low)"
      }},
      "capability_map": {{
        "current_skills": ["List of skills they already possess"],
        "skill_depth": {{
          "SkillName": "Proficiency description (e.g., 'Python (basic syntax, simple scripts)', 'HTML/CSS (built static sites)')"
        }},
        "technical_baseline": "Overall baseline evaluation (e.g. basic scripting, beginner web development, logic-only)",
        "industry_readiness_score": 0.35,
        "identified_gaps": ["List of priority skills/tools they must learn for target role based on industry expectations"]
      }},
      "constraint_map": {{
        "time_limit": "Hours per week they can dedicate (e.g. '15 hours per week')",
        "financial_limits": "Financial constraints if mentioned, otherwise 'none'",
        "device_access": "Type of computer/laptop they have (e.g. basic laptop, high-end PC, mobile-only)",
        "internet_access": "Internet situation (e.g. high-speed fiber, limited mobile data)",
        "college_load": "How demanding their academic load is (e.g. high load, exams, free semester)",
        "family_expectations": "Family constraints or expectations if any"
      }},
      "preference_map": {{
        "learning_style": "Learning style ('hands-on', 'visual', or 'theoretical')",
        "content_type": ["Preferred media, e.g. projects, video tutorials, documentation"],
        "project_taste": "Preferences in building (e.g. API structures, frontend visual apps, data pipelines)",
        "communication_tone": "AI communication tone preference (e.g. hyper-direct, encouraging, analytical)"
      }},
      "motivation_and_risk_map": {{
        "motivation_profile": "What drives them (e.g., portfolio weight, immediate job, building apps, research)",
        "procrastination_patterns": ["Expected procrastination risks, e.g., 'drifting due to lack of immediate verification'"],
        "risk_flags": ["Specific risk flags, e.g., 'impulsive skill hoarder', 'math anxiety', 'high college load'"],
        "decision_habits": ["How they make choices, e.g., 'needs explicit step-by-step validation', 'prefers exploration'"]
      }},
      "evidence_map": {{
        "projects": [
          {{
            "name": "Project name",
            "description": "Short description",
            "skills_proved": ["Python", "HTML"],
            "url": "Project URL or 'none'"
          }}
        ],
        "certificates": ["List of existing certificates"],
        "github_presence": "GitHub URL or status (e.g. 'needs creation', 'empty profile', 'active')",
        "resumes": ["Resume status or link"],
        "contests_and_hackathons": ["Competitions or hackathons attended"],
        "writing_and_portfolio": ["Portfolio sites or tech blogs written"]
      }},
      "open_questions": ["List of unresolved queries Delta should ask them in the future to refine their path"],
      "market_search_prompt": "An optimized web search prompt for locating current demand trends aligned with their target profile and constraints.",
      "follow_up_question_strategy": "Conversational strategy to address the open questions sequentially in the future check-ins."
    }}
    """
    try:
        response_text = generate_response(prompt)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        data = json.loads(response_text.strip())
        
        # Defensive self-healing extraction of the 10-key intake intelligence
        identity = data.get("identity_context") or data.get("identity") or {}
        ambition = data.get("ambition_map") or data.get("ambitions") or {}
        capability = data.get("capability_map") or data.get("capabilities") or {}
        constraint = data.get("constraint_map") or data.get("constraints") or {}
        preference = data.get("preference_map") or data.get("preferences") or {}
        behavior = data.get("motivation_and_risk_map") or data.get("behavior") or {}
        evidence = data.get("evidence_map") or data.get("evidence") or {}
        
        open_qs = data.get("open_questions") or []
        market_search = data.get("market_search_prompt") or ""
        follow_up_strat = data.get("follow_up_question_strategy") or ""

        # Normalize ambition goals to string
        long_term_goals = ambition.get("long_term_goals") or []
        ambition_str = ""
        if isinstance(long_term_goals, list) and long_term_goals:
            ambition_str = long_term_goals[0]
        elif isinstance(long_term_goals, str):
            ambition_str = long_term_goals

        # Build a robust backward-compatible profile object
        profile_data = {
            "identity_context": identity,
            "ambition_map": ambition,
            "capability_map": capability,
            "constraint_map": constraint,
            "preference_map": preference,
            "motivation_and_risk_map": behavior,
            "evidence_map": evidence,
            "open_questions": open_qs,
            "market_search_prompt": market_search,
            "follow_up_question_strategy": follow_up_strat,
            
            # Legacy field translations
            "ambitions": ambition_str or ambition.get("long_term_goals") or "",
            "current_level": identity.get("education_stage", "Beginner"),
            "hours_per_week": 15,
            "learning_style": preference.get("learning_style", "hands-on"),
            "extracted_skills": capability.get("current_skills") or capability.get("skills") or [],
            "gaps_identified": capability.get("identified_gaps") or capability.get("gaps") or [],
            "recommended_starting_phase": data.get("recommended_starting_phase") or "Phase 1: Foundations",
            "constraints": [
                f"Time limit: {constraint.get('time_limit', '15 hours per week')}",
                f"Device: {constraint.get('device_access', 'Standard Laptop')}",
                f"Internet: {constraint.get('internet_access', 'Standard Access')}"
            ],
            "content_preferences": preference.get("content_type") or ["hands-on projects"],
            "behavior": {
                "consistency": "medium",
                "risk_flags": behavior.get("risk_flags") or [],
                "decision_patterns": behavior.get("decision_habits") or behavior.get("decision_patterns") or []
            },
            "evidence": {
                "projects": evidence.get("projects") or [],
                "certifications": evidence.get("certificates") or evidence.get("certifications") or [],
                "competitions": evidence.get("contests_and_hackathons") or evidence.get("competitions") or [],
                "portfolio_links": []
            },
            "status": "processed"
        }
        
        # Try to parse hours per week to integer
        try:
            h_str = constraint.get("time_limit", "15")
            # Extract digits
            h_val = int(''.join(c for c in h_str if c.isdigit()))
            profile_data["hours_per_week"] = h_val
        except Exception:
            profile_data["hours_per_week"] = 15
            
        return profile_data
        
    except Exception as e:
        print(f"Onboarding finalize error: {e}")
        # Fallback profile aligned perfectly with the blueprint schema
        fallback = {
            "identity_context": {
                "name": "",
                "education_stage": "Beginner",
                "location": "unknown",
                "language_comfort": "English",
                "background_summary": "Starting computer science and software development roadmap journey.",
                "self_awareness_level": "medium"
            },
            "ambition_map": {
                "long_term_goals": ["Become a world-class AI/Software Engineer"],
                "short_term_targets": ["Build web backend APIs"],
                "dream_roles": ["Software Engineer"],
                "preferred_industries": ["Tech"],
                "confidence_level": "medium"
            },
            "capability_map": {
                "current_skills": ["Python"],
                "skill_depth": {"Python": "basics, syntax"},
                "technical_baseline": "scripting-only",
                "industry_readiness_score": 0.35,
                "identified_gaps": ["Docker", "LLMs", "FastAPI", "SQL", "System Design"]
            },
            "constraint_map": {
                "time_limit": "15 hours per week",
                "financial_limits": "none",
                "device_access": "laptop",
                "internet_access": "broadband",
                "college_load": "medium",
                "family_expectations": "none"
            },
            "preference_map": {
                "learning_style": "hands-on",
                "content_type": ["hands-on projects"],
                "project_taste": "backend APIs",
                "communication_tone": "encouraging"
            },
            "motivation_and_risk_map": {
                "motivation_profile": "portfolio weight",
                "procrastination_patterns": ["drifting due to lack of immediate verification"],
                "risk_flags": [],
                "decision_habits": ["methodical"]
            },
            "evidence_map": {
                "projects": [],
                "certificates": [],
                "github_presence": "needs creation",
                "resumes": [],
                "contests_and_hackathons": [],
                "writing_and_portfolio": []
            },
            "open_questions": [],
            "market_search_prompt": "FastAPI Docker Backend entry level jobs recruiter expectations",
            "follow_up_question_strategy": "First probe github repository structure, then verify docker deployment comfort in week 2",
            
            # Legacy field translations
            "ambitions": "Become a world-class AI/Software Engineer",
            "current_level": "Beginner",
            "hours_per_week": 15,
            "learning_style": "hands-on",
            "extracted_skills": ["Python"],
            "gaps_identified": ["Docker", "LLMs", "FastAPI", "SQL", "System Design"],
            "recommended_starting_phase": "Phase 1: Advanced APIs & Backend Systems",
            "constraints": ["Time limit: 15 hours per week"],
            "content_preferences": ["hands-on projects"],
            "behavior": {"consistency": "medium", "risk_flags": [], "decision_patterns": []},
            "evidence": {"projects": [], "certifications": [], "competitions": [], "portfolio_links": []},
            "status": "processed"
        }
        return fallback

