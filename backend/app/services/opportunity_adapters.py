"""Opportunity adapters normalize contests, hackathons, jobs, and domain events."""
import datetime
import os
import re
import time
from html import unescape

from app.services.domain_packs import infer_domain_pack

ALLOW_MOCKS = os.getenv("DELTA_ALLOW_MOCKS", "").lower() in {"1", "true", "yes", "on"}


class OpportunityAdapter:
    source = "generic"
    default_mode = "api"
    supports = ("api",)
    live_notes = "Uses public live sources where available."

    def fetch(self, user_skills: list[str], target_role: str | None, days_ahead: int) -> list[dict]:
        raise NotImplementedError

    @property
    def mode(self) -> str:
        key = f"{self.source.upper()}_SOURCE_MODE".replace(" ", "_")
        configured = os.getenv(key) or os.getenv("OPPORTUNITY_SOURCE_MODE", self.default_mode)
        return configured.lower()

    def status(self) -> dict:
        mode = self.mode
        live_ready = mode in self.supports and mode != "mock"
        fallback = None
        if mode == "mock":
            fallback = "mock"
        elif mode not in self.supports:
            fallback = "none"
        return {
            "source": self.source,
            "mode": mode,
            "supported_modes": list(self.supports),
            "active": True,
            "live_ready": live_ready,
            "fallback": fallback,
            "notes": self.live_notes,
        }

    def _source_status(self) -> str:
        if self.mode == "mock":
            return "mock_enabled_by_DELTA_ALLOW_MOCKS"
        if self.mode not in self.supports:
            return f"unsupported_mode_{self.mode}"
        return f"{self.mode}_mode_ready"

    def _future_date(self, days: int, hour: int = 10, minute: int = 0) -> str:
        target = datetime.datetime.now() + datetime.timedelta(days=days)
        return target.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


class LeetCodeAdapter(OpportunityAdapter):
    source = "LeetCode"
    default_mode = "api"
    supports = ("api",)
    live_notes = "Uses LeetCode's public GraphQL upcoming-contest payload."

    def fetch(self, user_skills, target_role, days_ahead):
        return self._fetch_live_contests(days_ahead)

    def _fetch_live_contests(self, days_ahead):
        try:
            import requests

            response = requests.post(
                "https://leetcode.com/graphql",
                json={
                    "query": """
                    query upcomingContests {
                      contestUpcomingContests {
                        title
                        titleSlug
                        startTime
                        duration
                      }
                    }
                    """
                },
                headers={
                    "Content-Type": "application/json",
                    "Referer": "https://leetcode.com/contest/",
                    "User-Agent": "DeltaCareerOS/1.0",
                },
                timeout=10,
            )
            response.raise_for_status()
            contests = response.json().get("data", {}).get("contestUpcomingContests", [])
        except Exception:
            return []

        now = int(time.time())
        max_start = now + (days_ahead * 24 * 60 * 60)
        events = []
        for contest in contests:
            start = contest.get("startTime")
            duration = contest.get("duration") or 5400
            if not start or start > max_start:
                continue
            start_dt = datetime.datetime.fromtimestamp(start)
            end_dt = datetime.datetime.fromtimestamp(start + duration)
            slug = contest.get("titleSlug") or ""
            events.append(_event(
                source=self.source,
                title=contest.get("title") or "LeetCode Contest",
                opportunity_type="competitive_programming",
                start_date=start_dt.isoformat(),
                end_date=end_dt.isoformat(),
                url=f"https://leetcode.com/contest/{slug}/" if slug else "https://leetcode.com/contest/",
                skills=["Algorithms", "Data Structures", "Python", "C++"],
                reward="Live contest ranking and interview-speed proof",
                description="Upcoming LeetCode contest fetched from LeetCode's public contest data.",
                source_status="live_leetcode_graphql",
                external_id=slug,
            ))
        return events


class CodeforcesAdapter(OpportunityAdapter):
    source = "Codeforces"
    default_mode = "api"
    supports = ("api",)
    live_notes = "Codeforces exposes public contest APIs; api mode can be wired without credentials."

    def fetch(self, user_skills, target_role, days_ahead):
        return self._fetch_live_contests(days_ahead)

    def _fetch_live_contests(self, days_ahead):
        try:
            import requests

            response = requests.get(
                "https://codeforces.com/api/contest.list",
                params={"gym": "false"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("status") != "OK":
                return []
        except Exception:
            return []

        now = int(time.time())
        max_start = now + (days_ahead * 24 * 60 * 60)
        events = []
        for contest in payload.get("result", []):
            start = contest.get("startTimeSeconds")
            duration = contest.get("durationSeconds") or 7200
            phase = contest.get("phase")
            if phase != "BEFORE" or not start or start > max_start:
                continue
            start_dt = datetime.datetime.fromtimestamp(start)
            end_dt = datetime.datetime.fromtimestamp(start + duration)
            name = contest.get("name", "Codeforces Contest")
            difficulty = "Hard" if "Div. 1" in name or "Global" in name else "Medium"
            events.append(_event(
                source=self.source,
                title=name,
                opportunity_type="competitive_programming",
                start_date=start_dt.isoformat(),
                end_date=end_dt.isoformat(),
                url="https://codeforces.com/contests",
                skills=["Algorithms", "Data Structures", "Math", "C++"],
                reward="Live public contest rank and rating proof",
                description="Live Codeforces contest fetched from the public contest.list API.",
                difficulty=difficulty,
                source_status="live_codeforces_api",
                external_id=str(contest.get("id", "")),
            ))
        return events[:12]


class KaggleAdapter(OpportunityAdapter):
    source = "Kaggle"
    default_mode = "scrape"
    supports = ("scrape",)
    live_notes = "Scrapes Kaggle competition listing links when public HTML is available."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        return _scrape_listing_events(
            source=self.source,
            listing_url="https://www.kaggle.com/competitions",
            link_pattern=r'href="(/competitions/[^"#?]+)"',
            opportunity_type="ml_sprint",
            skills=domain["skill_taxonomy"][:5],
            reward="Kaggle notebook, model score, and public ranking proof",
            description="Live Kaggle competition discovered from the public competitions page.",
            days_ahead=days_ahead,
        )


class UnstopAdapter(OpportunityAdapter):
    source = "Unstop"
    default_mode = "scrape"
    supports = ("scrape",)
    live_notes = "Unstop does not provide a simple public API; scrape mode should respect robots and rate limits."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        return _scrape_listing_events(
            source=self.source,
            listing_url="https://unstop.com/hackathons",
            link_pattern=r'href="(https://unstop\.com/[^"#?]+|/[^"#?]+)"',
            opportunity_type="hackathon",
            skills=domain["skill_taxonomy"][:5],
            reward="Leaderboard, prize, and public participation proof",
            description=f"Live Unstop opportunity aligned to {domain['label']}.",
            days_ahead=days_ahead,
        )


class HackathonAdapter(OpportunityAdapter):
    source = "Hackathon"
    default_mode = "scrape"
    supports = ("scrape",)
    live_notes = "Can aggregate Devpost, MLH, and curated hackathon feeds."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        return _scrape_listing_events(
            source=self.source,
            listing_url="https://devpost.com/hackathons",
            link_pattern=r'href="(https://[^"]*devpost\.com/[^"#?]+)"',
            opportunity_type="hackathon",
            skills=domain["skill_taxonomy"][:4],
            reward="MVP demo, team execution proof, and public submission page",
            description="Live hackathon discovered from Devpost.",
            days_ahead=days_ahead,
        )


class JobPostSignalAdapter(OpportunityAdapter):
    source = "JobPosts"
    default_mode = "api"
    supports = ("api",)
    live_notes = "Can aggregate job APIs or scrape configured boards to extract repeated recruiter language."

    def fetch(self, user_skills, target_role, days_ahead):
        try:
            import requests

            role = target_role or "software engineer"
            response = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": role},
                headers={"User-Agent": "DeltaCareerOS/1.0"},
                timeout=10,
            )
            response.raise_for_status()
            jobs = response.json().get("data", [])
        except Exception:
            return []

        domain = infer_domain_pack(target_role)
        events = []
        for job in jobs[:8]:
            title = job.get("title") or "Live job signal"
            url = job.get("url") or "https://www.arbeitnow.com/jobs"
            skills = _infer_skills_from_text(
                " ".join([title, job.get("description") or ""]),
                domain["skill_taxonomy"][:10],
            ) or domain["skill_taxonomy"][:5]
            events.append(_event(
                source=self.source,
                title=title,
                opportunity_type="market_research",
                start_date=self._future_date(2, 19, 0),
                end_date=self._future_date(2, 20, 0),
                url=url,
                skills=skills,
                reward="Live recruiter-language signal and resume keyword update",
                description="Job-market signal fetched from Arbeitnow's public job board API.",
                difficulty="Easy",
                source_status="live_arbeitnow_api",
                external_id=str(job.get("slug") or job.get("url") or title),
            ))
        return events


def collect_opportunities(
    user_skills: list[str],
    target_role: str | None = None,
    days_ahead: int = 30,
    sources: list[str] | None = None,
) -> list[dict]:
    adapters = get_opportunity_adapters()
    if sources:
        wanted = {source.lower() for source in sources}
        adapters = [adapter for adapter in adapters if adapter.source.lower() in wanted]

    user_skill_set = {skill.lower() for skill in user_skills}
    opportunities = []
    for adapter in adapters:
        for event in adapter.fetch(user_skills, target_role, days_ahead):
            event["source_mode"] = adapter.mode
            if event.get("source_status") == "mock_adapter_ready_for_live_fetch":
                event["source_status"] = adapter._source_status()
            opportunities.append(_score_event(event, user_skill_set))

    opportunities.sort(key=lambda item: (item["start_date"], -item["match_percentage"]))
    return opportunities


def get_opportunity_adapters() -> list[OpportunityAdapter]:
    return [
        LeetCodeAdapter(),
        CodeforcesAdapter(),
        KaggleAdapter(),
        UnstopAdapter(),
        HackathonAdapter(),
        JobPostSignalAdapter(),
    ]


def get_source_statuses() -> list[dict]:
    return [adapter.status() for adapter in get_opportunity_adapters()]


def summarize_opportunity_signals(opportunities: list[dict]) -> dict:
    skill_counts = {}
    source_counts = {}
    for opportunity in opportunities:
        source_counts[opportunity["platform"]] = source_counts.get(opportunity["platform"], 0) + 1
        for skill in opportunity.get("recommended_skills", []):
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    return {
        "source_counts": source_counts,
        "repeated_skills": [
            {"skill": skill, "count": count}
            for skill, count in sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:10]
        ],
        "recommended_opportunities": [
            opportunity for opportunity in opportunities if opportunity.get("recommended")
        ][:6],
    }


def _event(
    source: str,
    title: str,
    opportunity_type: str,
    start_date: str,
    end_date: str,
    url: str,
    skills: list[str],
    reward: str,
    description: str,
    difficulty: str = "Medium",
    source_status: str = "mock_adapter_ready_for_live_fetch",
    external_id: str | None = None,
) -> dict:
    stable_id = f"{source.lower()}-{title.lower().replace(' ', '-')[:48]}"
    return {
        "id": stable_id,
        "title": title,
        "platform": source,
        "source": source,
        "type": opportunity_type,
        "difficulty": difficulty,
        "start_date": start_date,
        "end_date": end_date,
        "registration_url": url,
        "url": url,
        "rewards": reward,
        "recommended_skills": skills,
        "description": description,
        "source_status": source_status,
        "external_id": external_id,
    }


def _score_event(event: dict, user_skill_set: set[str]) -> dict:
    required = event.get("recommended_skills", [])
    matches = [skill for skill in required if skill.lower() in user_skill_set]
    event["matching_skills"] = matches
    event["match_percentage"] = int((len(matches) / max(len(required), 1)) * 100)
    event["recommended"] = event["match_percentage"] >= 40 or event["type"] in ("market_research", "hackathon")
    event["proof_value"] = _proof_value(event)
    return event


def _proof_value(event: dict) -> str:
    if event["type"] == "competitive_programming":
        return "Public ranking and consistency signal"
    if event["type"] == "ml_sprint":
        return "Notebook, model, and evaluation proof"
    if event["type"] == "market_research":
        return "Roadmap calibration and resume keyword signal"
    if event["type"] == "case_competition":
        return "Structured thinking and presentation proof"
    return "Build artifact, demo, and team execution proof"


def _scrape_listing_events(
    source: str,
    listing_url: str,
    link_pattern: str,
    opportunity_type: str,
    skills: list[str],
    reward: str,
    description: str,
    days_ahead: int,
) -> list[dict]:
    try:
        import requests

        response = requests.get(
            listing_url,
            headers={"User-Agent": "DeltaCareerOS/1.0"},
            timeout=10,
        )
        response.raise_for_status()
        html = response.text
    except Exception:
        return []

    seen = set()
    events = []
    for idx, href in enumerate(re.findall(link_pattern, html)[:12]):
        href = unescape(href)
        if href.startswith("/"):
            base = listing_url.split("/", 3)[:3]
            href = "/".join(base) + href
        slug = href.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
        if not slug or href in seen:
            continue
        seen.add(href)
        events.append(_event(
            source=source,
            title=slug,
            opportunity_type=opportunity_type,
            start_date=(datetime.datetime.now() + datetime.timedelta(days=min(idx + 1, days_ahead))).isoformat(),
            end_date=(datetime.datetime.now() + datetime.timedelta(days=min(idx + 8, days_ahead))).isoformat(),
            url=href,
            skills=skills,
            reward=reward,
            description=description,
            source_status=f"live_{source.lower()}_scrape",
            external_id=href,
        ))
    return events


def _infer_skills_from_text(text: str, candidate_skills: list[str]) -> list[str]:
    text_lower = (text or "").lower()
    return [skill for skill in candidate_skills if skill.lower() in text_lower][:6]
