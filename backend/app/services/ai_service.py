import os

def generate_response(prompt: str) -> str:
    """Generate response using Gemini API. Falls back to mock if no key."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return _mock_response(prompt)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API error: {e}")
        return _mock_response(prompt)


def _mock_response(prompt: str) -> str:
    """Fallback response when Gemini is unavailable."""
    if "career" in prompt.lower() or "skill" in prompt.lower():
        return ("Based on current market trends for AI/Software roles, I recommend focusing on: "
                "1) Building LLM projects on GitHub for evidence-based skill verification, "
                "2) Completing the Docker certification path, and "
                "3) Contributing to open-source ML repositories. "
                "These actions would boost your Delta Score by approximately +5.2 points this week.")
    return "I'm here to help with your career journey! Ask me about skills, market trends, or your learning path."
