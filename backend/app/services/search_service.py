"""Learning resource search backed by public source URLs."""
from __future__ import annotations

from urllib.parse import quote_plus


RESOURCE_PROVIDERS = {
    "docs": [
        ("Official docs search", "https://www.google.com/search?q=site%3A{domain}+{query}"),
    ],
    "course": [
        ("freeCodeCamp", "https://www.freecodecamp.org/news/search/?query={query}"),
        ("Coursera", "https://www.coursera.org/search?query={query}"),
        ("edX", "https://www.edx.org/search?q={query}"),
    ],
    "tutorial": [
        ("MDN", "https://developer.mozilla.org/en-US/search?q={query}"),
        ("Google Developers", "https://developers.google.com/search?q={query}"),
        ("Hugging Face Learn", "https://huggingface.co/learn?query={query}"),
    ],
    "certification": [
        ("AWS Training", "https://aws.amazon.com/search/?searchQuery={query}+certification"),
        ("Microsoft Learn", "https://learn.microsoft.com/en-us/search/?terms={query}+certification"),
        ("Google Cloud Skills Boost", "https://www.cloudskillsboost.google/catalog?keywords={query}"),
    ],
    "project": [
        ("GitHub repositories", "https://github.com/search?q={query}&type=repositories&s=stars&o=desc"),
        ("Devpost projects", "https://devpost.com/software/search?query={query}"),
        ("Kaggle code", "https://www.kaggle.com/code?searchQuery={query}"),
    ],
}

DOC_DOMAINS = {
    "react": "react.dev",
    "python": "docs.python.org",
    "fastapi": "fastapi.tiangolo.com",
    "docker": "docs.docker.com",
    "kubernetes": "kubernetes.io",
    "postgresql": "postgresql.org",
    "sql": "postgresql.org",
    "tensorflow": "tensorflow.org",
    "pytorch": "pytorch.org",
}


def search_resources(skill: str, resource_type: str = "course") -> list:
    """Return real public source links for a skill, not fabricated resources."""
    query = quote_plus(skill.strip())
    if not query:
        return []

    providers = RESOURCE_PROVIDERS.get(resource_type, RESOURCE_PROVIDERS["course"])
    results = []
    for title, template in providers:
        domain = DOC_DOMAINS.get(skill.strip().lower(), "docs.github.com")
        results.append({
            "title": f"{title}: {skill}",
            "url": template.format(query=query, domain=domain),
            "type": resource_type,
            "source_status": "live_public_search_url",
        })

    if resource_type != "project":
        results.append({
            "title": f"GitHub examples: {skill}",
            "url": f"https://github.com/search?q={query}&type=repositories&s=stars&o=desc",
            "type": "project_reference",
            "source_status": "live_public_search_url",
        })
    return results
