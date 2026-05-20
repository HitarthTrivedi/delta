"""Search service — future integration for resource search."""

def search_resources(skill: str, resource_type: str = "course") -> list:
    """Search for learning resources by skill. Returns mock data."""
    resources = {
        "LLMs": [
            {"title": "LangChain Bootcamp", "url": "https://udemy.com/langchain", "type": "course"},
            {"title": "HuggingFace NLP Course", "url": "https://huggingface.co/course", "type": "tutorial"},
        ],
        "Docker": [
            {"title": "Docker Mastery", "url": "https://udemy.com/docker-mastery", "type": "course"},
            {"title": "Docker DCA Cert", "url": "https://training.mirantis.com", "type": "certification"},
        ],
    }
    return resources.get(skill, [{"title": f"Learn {skill}", "url": f"https://google.com/search?q={skill}", "type": resource_type}])
