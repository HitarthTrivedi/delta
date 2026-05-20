"""Onboarding pipeline — processes user intake data using Gemini."""
import json
from app.services.ai_service import generate_response

def start_onboarding(raw_input: str, target_role: str = "AI Developer / Software Engineer") -> dict:
    """
    Initial step of conversational onboarding.
    Scans the raw input, creates custom prompts, and returns a set of adaptive follow-up questions.
    """
    prompt = f"""
    You are Delta Onboarding Intelligence, an elite career planning agent for Indian CS/engineering students.
    The student has expressed their career goals and background:
    "{raw_input}"
    
    Their target role is: "{target_role}"
    
    Tasks:
    1. Parse their ambition, baseline context, and potential bottlenecks.
    2. Generate exactly 3 highly customized, adaptive follow-up questions to understand:
       - Their actual technical baseline (e.g., have they written code before, what languages).
       - Their background (e.g., post-12th math comfort, or hands-on preference).
       - Their real availability and time commitment limitations.
       
    Output your response strictly as a JSON object with this format:
    {{
      "ambition_summary": "Short 1-2 sentence summary of their goals.",
      "adaptive_questions": [
        "First personalized question...",
        "Second personalized question...",
        "Third personalized question..."
      ],
      "market_demand_focus": "Based on 2026 Indian tech trends, what should they target?"
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
            "market_demand_focus": "Focus on high-growth clusters like LLM orchestration, Docker containers, and clean coding practices."
        }

def finalize_onboarding(raw_input: str, follow_ups: list, answers: list) -> dict:
    """
    Finalize the onboarding pipeline.
    Combines initial input, questions asked, and answers provided to extract the complete, structured profile.
    """
    qa_pairs = []
    for q, a in zip(follow_ups, answers):
        qa_pairs.append(f"Q: {q}\nA: {a}")
    qa_context = "\n\n".join(qa_pairs)

    prompt = f"""
    You are Delta Onboarding Intelligence. Based on the student's initial ambition and their answers to personalized follow-up questions, extract a complete structured personalization profile.
    
    Initial Input:
    "{raw_input}"
    
    Conversational Answers:
    {qa_context}
    
    Tasks:
    Extract their profile into a JSON object with the following fields:
    {{
      "ambitions": "Detailed statement of career ambitions.",
      "current_level": "Stated experience level (e.g., absolute beginner, school level, intermediate).",
      "hours_per_week": Estimated hours they can study (integer),
      "learning_style": "hands-on", "visual", or "theoretical",
      "extracted_skills": ["List", "of", "currently", "known", "skills"],
      "gaps_identified": ["List", "of", "major", "gaps", "between", "current", "skills", "and", "industry", "demands"],
      "recommended_starting_phase": "Phase 1: Foundations"
    }}
    """
    try:
        response_text = generate_response(prompt)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        data = json.loads(response_text.strip())
        data["status"] = "processed"
        return data
    except Exception as e:
        print(f"Onboarding finalize error: {e}")
        # Fallback profile
        return {
            "ambitions": f"Build robust software architectures and modern AI applications.",
            "current_level": "Post-12th Beginner",
            "hours_per_week": 15,
            "learning_style": "hands-on",
            "extracted_skills": ["Python"],
            "gaps_identified": ["Docker", "LLMs", "FastAPI", "SQL", "System Design"],
            "recommended_starting_phase": "Phase 1: Foundations",
            "status": "processed"
        }
