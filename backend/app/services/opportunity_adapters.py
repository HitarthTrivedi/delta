"""Opportunity adapters normalize contests, hackathons, jobs, and domain events.

The adapters are mock-backed today and intentionally shaped like real fetchers.
When credentials or public feeds are available, each adapter can replace its
`fetch` method without changing calendar, market pulse, or Career OS consumers.
"""
import datetime
import os
import time

from app.services.domain_packs import infer_domain_pack


class OpportunityAdapter:
    source = "generic"
    supports = ("mock",)
    live_notes = "Mock-backed adapter. API/scrape implementation can be added without changing consumers."

    def fetch(self, user_skills: list[str], target_role: str | None, days_ahead: int) -> list[dict]:
        raise NotImplementedError

    @property
    def mode(self) -> str:
        key = f"{self.source.upper()}_SOURCE_MODE".replace(" ", "_")
        configured = os.getenv(key) or os.getenv("OPPORTUNITY_SOURCE_MODE", "mock")
        return configured.lower()

    def status(self) -> dict:
        mode = self.mode
        live_ready = mode in self.supports and mode != "mock"
        fallback = None
        if mode == "mock":
            fallback = "mock"
        elif mode not in self.supports:
            fallback = "mock"
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
            return "mock_adapter_ready_for_live_fetch"
        if self.mode not in self.supports:
            return f"unsupported_mode_{self.mode}_using_mock"
        return f"{self.mode}_mode_ready"

    def _future_date(self, days: int, hour: int = 10, minute: int = 0) -> str:
        target = datetime.datetime.now() + datetime.timedelta(days=days)
        return target.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


class LeetCodeAdapter(OpportunityAdapter):
    source = "LeetCode"
    supports = ("mock", "scrape")
    live_notes = "LeetCode has public contest pages; scrape mode can parse scheduled contests later."

    def fetch(self, user_skills, target_role, days_ahead):
        today = datetime.datetime.now()
        events = []
        for day in range(days_ahead):
            target = today + datetime.timedelta(days=day)
            if target.weekday() == 6:
                events.append(_event(
                    source=self.source,
                    title=f"LeetCode Weekly Contest {380 + day}",
                    opportunity_type="competitive_programming",
                    start_date=target.replace(hour=8, minute=0, second=0, microsecond=0).isoformat(),
                    end_date=target.replace(hour=9, minute=30, second=0, microsecond=0).isoformat(),
                    url="https://leetcode.com/contest/",
                    skills=["Data Structures", "Algorithms", "Python", "C++"],
                    reward="Global CP ranking and contest proof",
                    description="Weekly algorithm benchmark for interview speed and problem solving.",
                ))
            if target.weekday() == 5 and target.day % 2 == 0:
                events.append(_event(
                    source=self.source,
                    title=f"LeetCode Biweekly Contest {120 + day}",
                    opportunity_type="competitive_programming",
                    start_date=target.replace(hour=20, minute=0, second=0, microsecond=0).isoformat(),
                    end_date=target.replace(hour=21, minute=30, second=0, microsecond=0).isoformat(),
                    url="https://leetcode.com/contest/",
                    skills=["Algorithms", "Data Structures", "Java", "Python"],
                    reward="Global CP rating increase",
                    description="Biweekly coding contest useful for public consistency proof.",
                ))
        return events


class CodeforcesAdapter(OpportunityAdapter):
    source = "Codeforces"
    supports = ("mock", "api")
    live_notes = "Codeforces exposes public contest APIs; api mode can be wired without credentials."

    def fetch(self, user_skills, target_role, days_ahead):
        if self.mode == "api":
            live_events = self._fetch_live_contests(days_ahead)
            if live_events:
                return live_events
        return self._mock_contests(days_ahead)

    def _mock_contests(self, days_ahead):
        events = []
        for idx, days in enumerate([3, 8, 12, 17, 22, 28]):
            if days > days_ahead:
                continue
            div_num = 2 if idx % 2 == 0 else 3
            events.append(_event(
                source=self.source,
                title=f"Codeforces Round {950 + idx} (Div. {div_num})",
                opportunity_type="competitive_programming",
                start_date=self._future_date(days, 20, 5),
                end_date=self._future_date(days, 22, 5),
                url="https://codeforces.com/contests",
                skills=["Algorithms", "Number Theory", "Dynamic Programming", "C++"],
                reward="Specialist/Expert rating proof",
                description="Mathematical competitive programming contest with strong public signal.",
                difficulty="Hard" if div_num == 2 else "Medium",
            ))
        return events

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
    supports = ("mock", "api")
    live_notes = "Kaggle API can replace mock challenges when credentials are configured."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        events = [
            _event(
                source=self.source,
                title="Kaggle Tabular Playground Sprint",
                opportunity_type="ml_sprint",
                start_date=self._future_date(1, 0, 0),
                end_date=self._future_date(min(15, days_ahead), 23, 59),
                url="https://www.kaggle.com/competitions",
                skills=["Python", "SQL", "Pandas", "Scikit-Learn", "Statistics"],
                reward="Kaggle ranking, notebook proof, model evaluation signal",
                description="Monthly ML sprint for data modeling and public notebook proof.",
            )
        ]
        if domain["id"] in ("cs_ai", "data", "research"):
            events.append(_event(
                source=self.source,
                title="Kaggle AI Agent Optimization Challenge",
                opportunity_type="ml_sprint",
                start_date=self._future_date(10, 10, 0),
                end_date=self._future_date(min(29, days_ahead), 23, 59),
                url="https://www.kaggle.com/competitions",
                skills=["LLMs", "Vector Databases", "Python", "RAG", "Evaluation"],
                reward="Global AI ranking and agent-building proof",
                description="Agent optimization challenge focused on retrieval, evaluation, and automation.",
                difficulty="Hard",
            ))
        return events


class UnstopAdapter(OpportunityAdapter):
    source = "Unstop"
    supports = ("mock", "scrape")
    live_notes = "Unstop does not provide a simple public API; scrape mode should respect robots and rate limits."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        events = [
            _event(
                source=self.source,
                title=f"{domain['label']} National Challenge",
                opportunity_type="hackathon",
                start_date=self._future_date(5, 10, 0),
                end_date=self._future_date(12, 18, 0),
                url="https://unstop.com/",
                skills=domain["skill_taxonomy"][:5],
                reward="Cash prize, public leaderboard, internship signal",
                description=f"Domain challenge aligned to {domain['label']} proof and recruiter visibility.",
                difficulty="Hard",
            ),
            _event(
                source=self.source,
                title=f"{domain['label']} Case Sprint",
                opportunity_type="case_competition",
                start_date=self._future_date(18, 9, 0),
                end_date=self._future_date(24, 21, 0),
                url="https://unstop.com/",
                skills=domain["skill_taxonomy"][1:6] or domain["skill_taxonomy"][:5],
                reward="Case deck, finalist proof, interview talking point",
                description="Short domain case sprint for structured thinking and portfolio evidence.",
                difficulty="Medium",
            ),
        ]
        return events


class HackathonAdapter(OpportunityAdapter):
    source = "Hackathon"
    supports = ("mock", "api", "scrape")
    live_notes = "Can aggregate Devpost, MLH, and curated hackathon feeds."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        return [
            _event(
                source=self.source,
                title=f"{domain['label']} Build Weekend",
                opportunity_type="hackathon",
                start_date=self._future_date(7, 18, 0),
                end_date=self._future_date(9, 21, 0),
                url="https://devpost.com/hackathons",
                skills=domain["skill_taxonomy"][:4],
                reward="MVP demo and public build log",
                description="Weekend build sprint to turn one roadmap skill into visible proof.",
                difficulty="Medium",
            )
        ]


class JobPostSignalAdapter(OpportunityAdapter):
    source = "JobPosts"
    supports = ("mock", "api", "scrape")
    live_notes = "Can aggregate job APIs or scrape configured boards to extract repeated recruiter language."

    def fetch(self, user_skills, target_role, days_ahead):
        domain = infer_domain_pack(target_role)
        return [
            _event(
                source=self.source,
                title=f"{domain['label']} Internship Signal Review",
                opportunity_type="market_research",
                start_date=self._future_date(2, 19, 0),
                end_date=self._future_date(2, 20, 0),
                url="https://www.linkedin.com/jobs/",
                skills=domain["skill_taxonomy"][:6],
                reward="Weekly role-fit notes and resume keyword updates",
                description="Review current internships and extract repeated skills, tools, and proof expectations.",
                difficulty="Easy",
            )
        ]


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
