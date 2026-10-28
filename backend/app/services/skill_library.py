"""Skill -> milestones library for company roadmaps (human-written; no AI).

A company lists the skills it needs; `milestones_for(skill)` returns the
steps a student takes for each. Skills not in the library get a fixed
three-step pattern (learn, prove, test), which the Delta admin checks when
reviewing the roadmap. Adding a skill is a data change here.

Shape of a step: title, detail, kind (learn | practice | project | test |
interview | career), url (https, external) or link (inside Delta).
"""
from __future__ import annotations

import re

from app.services.roadmap_templates import INTERNAL_LINKS, KINDS


def _step(title: str, detail: str, kind: str = "practice", url: str | None = None, link: str | None = None) -> dict:
    return {"title": title, "detail": detail, "kind": kind, "url": url, "link": link}


def _test(topic: str) -> dict:
    return _step(f"Take a {topic} test", f"Shows the company where you stand in {topic}; retake it after revising.",
                 "test", link=f"/practice/theory?topic={topic.replace(' ', '%20')}")


NEETCODE = "https://neetcode.io/roadmap"
INDIABIX = "https://www.indiabix.com/"
SQLBOLT = "https://sqlbolt.com/"
MDN = "https://developer.mozilla.org/en-US/docs/Learn"
PYTHON = "https://docs.python.org/3/tutorial/"
JAVA = "https://dev.java/learn/"
REACT = "https://react.dev/learn"
GIT = "https://git-scm.com/book/en/v2"
OSTEP = "https://pages.cs.wisc.edu/~remzi/OSTEP/"
POSTGRES = "https://www.postgresql.org/docs/current/tutorial.html"
KAGGLE = "https://www.kaggle.com/learn"
PANDAS = "https://pandas.pydata.org/docs/user_guide/index.html"
POWER_BI = "https://learn.microsoft.com/en-us/training/powerplatform/power-bi"
TABLEAU = "https://public.tableau.com/"
EXCEL = "https://support.microsoft.com/en-us/excel"
SYSTEM_DESIGN = "https://github.com/donnemartin/system-design-primer"
FIGMA = "https://help.figma.com/hc/en-us"
GOOGLE_SKILLSHOP = "https://skillshop.withgoogle.com/"
SEO_GUIDE = "https://developers.google.com/search/docs/fundamentals/seo-starter-guide"

# key: (aliases, steps)
LIBRARY: dict[str, tuple[tuple[str, ...], list[dict]]] = {
    "data structures": (("dsa", "data structures and algorithms", "algorithms"), [
        _step("Solve 15 problems on core patterns", "Arrays, hashing, two pointers, stacks; write the complexity of each.", url=NEETCODE),
        _step("Solve 10 tree and graph problems", "Traversals, BFS/DFS, shortest path in a grid.", url=NEETCODE),
        _test("Data Structures"),
    ]),
    "dynamic programming": (("dp",), [
        _step("Solve 10 dynamic programming problems", "Write the state and recurrence before coding; 1D then 2D.", url=NEETCODE),
        _test("Dynamic Programming"),
    ]),
    "sql": (("mysql", "postgresql", "postgres", "sql queries"), [
        _step("Write 25 SQL queries", "SELECT, joins, GROUP BY with HAVING, subqueries.", url=SQLBOLT),
        _step("Practise window functions on a real dataset", "Running totals, ranks, period-over-period change.", url=POSTGRES),
        _test("SQL"),
    ]),
    "dbms": (("database", "databases", "database management"), [
        _step("Revise keys, normalisation, transactions and indexing", "Normalise one table to 3NF and explain ACID with an example.", "learn", url=POSTGRES),
        _test("DBMS"),
    ]),
    "python": (("python programming", "python 3"), [
        _step("Revise Python end to end", "Types, comprehensions, functions, classes, files, errors; write 10 small scripts.", "learn", url=PYTHON),
        _step("Build a small Python tool", "Something you'd use: a CSV cleaner, a file renamer, an API fetcher. Put it on GitHub.", "project"),
        _test("Python"),
    ]),
    "java": (("core java", "java programming"), [
        _step("Revise core Java", "OOP, collections, exceptions, streams; write 10 small programs.", "learn", url=JAVA),
        _test("Java"),
    ]),
    "javascript": (("js", "es6", "typescript"), [
        _step("Revise modern JavaScript", "Closures, promises and async/await, array methods, modules.", "learn", url=MDN),
        _test("JavaScript"),
    ]),
    "react": (("react.js", "reactjs", "frontend development"), [
        _step("Work through the official React tutorial", "Components, state, effects, forms.", "learn", url=REACT),
        _step("Build a small React app with an API", "Loading and error states, a form, a list; deploy it.", "project"),
    ]),
    "git": (("github", "version control"), [
        _step("Learn Git properly", "Branches, rebase vs merge, resolving conflicts, pull requests.", "learn", url=GIT),
    ]),
    "oop": (("object oriented programming", "object-oriented programming"), [
        _step("Explain the four pillars of OOP with your own code", "One class design you can explain aloud with trade-offs.", "learn"),
        _test("OOP"),
    ]),
    "operating systems": (("os",), [
        _step("Revise operating systems", "Processes vs threads, scheduling, deadlock, paging.", "learn", url=OSTEP),
        _test("Operating Systems"),
    ]),
    "computer networks": (("networking", "cn", "networks"), [
        _step("Revise computer networks", "OSI/TCP-IP layers, TCP vs UDP, HTTP, DNS, what happens when you open a URL.", "learn"),
        _test("Computer Networks"),
    ]),
    "system design": (("low level design", "lld", "high level design"), [
        _step("Learn system design basics", "Caching, load balancing, queues, databases; sketch one system you know.", "learn", url=SYSTEM_DESIGN),
        _step("Design one system end to end", "Requirements, API, data model, scaling; write it up in a page.", "project"),
    ]),
    "excel": (("ms excel", "microsoft excel", "spreadsheets", "advanced excel"), [
        _step("Master spreadsheet essentials", "XLOOKUP/VLOOKUP, pivot tables, conditional formatting, charts on a real dataset.", url=EXCEL),
        _test("Excel"),
    ]),
    "ms office": (("microsoft office", "computer basics", "word", "powerpoint"), [
        _step("Practise Word, Excel and PowerPoint basics", "A formatted letter, a simple sheet with totals, a 5-slide deck.", url=EXCEL),
    ]),
    "statistics": (("stats", "probability"), [
        _step("Revise descriptive statistics and probability", "Mean, spread, distributions, correlation vs causation, sampling.", "learn", url=KAGGLE),
        _test("Statistics"),
    ]),
    "data analysis": (("pandas", "data analytics", "eda"), [
        _step("Clean and analyse a messy dataset", "Missing values, merges, five charts and one page of findings.", "project", url=PANDAS),
        _test("Data Analysis"),
    ]),
    "power bi": (("powerbi", "tableau", "data visualization", "dashboards"), [
        _step("Learn a BI tool", "Data model, measures, filters in Power BI or Tableau.", "learn", url=POWER_BI),
        _step("Build and publish a dashboard", "One audience, three questions it answers.", "project", url=TABLEAU),
    ]),
    "machine learning": (("ml", "ai/ml", "deep learning"), [
        _step("Work through an intro ML course", "Train/test split, overfitting, a baseline model, evaluation metrics.", "learn", url=KAGGLE),
        _step("Train and explain one model on real data", "Compare against a simple baseline; write what you'd try next.", "project"),
        _test("Machine Learning"),
    ]),
    "aptitude": (("quantitative aptitude", "quant", "numerical ability", "maths"), [
        _step("Practise timed aptitude sets", "Percentages, ratios, time-speed-distance, profit and loss: 30 questions.", url=INDIABIX),
        _test("Quantitative Aptitude"),
    ]),
    "logical reasoning": (("reasoning", "logical ability"), [
        _step("Practise logical reasoning sets", "Series, coding-decoding, seating arrangements, syllogisms: 25 questions.", url=INDIABIX),
        _test("Logical Reasoning"),
    ]),
    "communication": (("communication skills", "verbal communication", "spoken english", "english", "verbal ability"), [
        _step("Record a 2-minute introduction and improve it", "Listen back, cut filler words, record it again.", "interview"),
        _step("Do an AI mock HR interview", "Tell me about yourself, strengths, a challenge; under 2 minutes each.", "interview", link="/practice/interview"),
    ]),
    "presentation": (("presentation skills", "public speaking"), [
        _step("Give a 5-minute talk on your best project", "Problem, what you did, result; practise it twice out loud.", "interview"),
    ]),
    "customer service": (("customer support", "customer handling", "client handling"), [
        _step("Practise handling three tricky customer situations", "A complaint, a refund request, an angry caller: write what you'd say.", "practice"),
        _step("Do an AI mock interview for a customer-facing role", "Focus on calm, clear answers.", "interview", link="/practice/interview"),
    ]),
    "sales": (("business development", "telesales", "field sales", "negotiation"), [
        _step("Write and rehearse a 60-second pitch", "For one real product: who it's for, the problem, why it's better.", "practice"),
        _step("Practise handling objections", "Write answers to five common objections and rehearse them aloud.", "interview"),
    ]),
    "accounting": (("tally", "bookkeeping", "gst", "accounts"), [
        _step("Revise accounting basics", "Journal entries, ledgers, trial balance, GST basics.", "learn"),
        _step("Record a month of sample transactions", "In Tally or a spreadsheet; produce a trial balance.", "project"),
        _test("Accounting"),
    ]),
    "financial modelling": (("financial modeling", "valuation", "financial analysis"), [
        _step("Build a three-statement model for a small company", "Revenue drivers, P&L, balance sheet, cash flow.", "project"),
        _test("Financial Analysis"),
    ]),
    "ui design": (("figma", "ux design", "ui/ux", "product design"), [
        _step("Learn Figma basics", "Frames, components, auto layout, prototyping.", "learn", url=FIGMA),
        _step("Redesign one screen of an app you use", "Show before, after, and why.", "project"),
    ]),
    "digital marketing": (("social media marketing", "performance marketing", "google ads"), [
        _step("Complete a free digital marketing course", "Funnels, campaigns, metrics.", "learn", url=GOOGLE_SKILLSHOP),
        _step("Plan a one-month campaign for a small business", "Audience, channels, budget, the metrics you'd track.", "project"),
    ]),
    "seo": (("search engine optimization", "content marketing"), [
        _step("Read the SEO starter guide", "Crawling, titles, structure, content quality.", "learn", url=SEO_GUIDE),
        _step("Audit one website's SEO", "Five issues and how you'd fix them.", "project"),
    ]),
}

_INDEX: dict[str, str] = {}
for _key, (_aliases, _) in LIBRARY.items():
    for _name in (_key, *_aliases):
        _INDEX[re.sub(r"[^a-z0-9+#/.]+", " ", _name.lower()).strip()] = _key


def _norm(skill: str) -> str:
    return re.sub(r"[^a-z0-9+#/.]+", " ", str(skill or "").lower()).strip()


def known(skill: str) -> bool:
    return _norm(skill) in _INDEX


def milestones_for(skill: str) -> list[dict]:
    """The steps for one skill: the library's, or the fixed learn/prove/test pattern."""
    name = " ".join(str(skill or "").split())[:60]
    key = _INDEX.get(_norm(name))
    if key:
        return [{**s, "skill": name} for s in LIBRARY[key][1]]
    return [
        {**_step(f"Learn the essentials of {name}",
                 f"Find the official docs or a well-reviewed free course for {name} and note the ideas every beginner "
                 "must know.", "learn"), "skill": name},
        {**_step(f"Practise {name} with a small proof",
                 f"Make one small, real piece of work that uses {name} and that you could show the company.",
                 "project"), "skill": name},
        {**_test(name), "skill": name},
    ]


def validate_milestones(milestones: list[dict]) -> list[str]:
    errors, ids = [], set()
    for m in milestones:
        mid = m.get("id") or ""
        if not re.fullmatch(r"co-[a-z0-9-]+", mid):
            errors.append(f"bad milestone id {mid!r}")
        if mid in ids:
            errors.append(f"duplicate milestone id {mid}")
        ids.add(mid)
        if not (m.get("title") and m.get("skill") and m.get("detail")):
            errors.append(f"{mid}: title, skill and detail are required")
        if str(m.get("title", "")).lower().startswith("start "):
            errors.append(f"{mid}: titles starting with 'Start ' are treated as beginner tasks by the planner")
        if m.get("kind") not in KINDS:
            errors.append(f"{mid}: unknown kind {m.get('kind')}")
        if m.get("url") and not str(m["url"]).startswith("https://"):
            errors.append(f"{mid}: links must be https")
        if m.get("link") and not str(m["link"]).startswith(INTERNAL_LINKS):
            errors.append(f"{mid}: unknown Delta link {m['link']}")
    return errors
