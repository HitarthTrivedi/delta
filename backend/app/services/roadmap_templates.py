"""Predefined role roadmaps: the engine that turns a template (roadmap_catalog)
into each week's tasks, with no AI call.

How a template "grows with the learner":
- Each phase's milestones are spread over its weeks. Milestones a learner has
  proven in a test (score >= 80 on 5+ questions, or a test on that topic at 80+)
  are skipped and the next one is pulled forward. Self-claimed skills never skip.
- Unfinished milestones from earlier phases come back (up to 2 a week).
- A weak tested skill in the current phase adds one "Revise X" task.
- A phase gate (a test score) holds the plan for at most N weeks, then moves on.
- A target date earlier than the template's length compresses it: optional
  milestones and break weeks drop out and more milestones fall due each week.
- When the template ends the learner goes back to the normal planner (or to
  the template's `then`, e.g. first year -> placement).
"""
from __future__ import annotations

import datetime
import json
import math
import re
import uuid

from sqlalchemy.orm import Session

from app.models.engagement import XpEvent
from app.models.roadmap_template import RoadmapEnrollment
from app.models.sandbox_session import SandboxSession
from app.services.domain_packs import DOMAIN_PACKS
from app.services.roadmap_catalog import TEMPLATES

PROVEN_SCORE = 80
PROVEN_QUESTIONS = 5
WEAK_SCORE = 60
WEAK_QUESTIONS = 3
BACKLOG_PER_WEEK = 2
ON_TRACK_SHARE = 0.7
KINDS = {"learn", "practice", "project", "test", "interview", "career"}
INTERNAL_LINKS = ("/practice", "/resume", "/opportunities", "/jobs", "/weekly-plan", "/today")
TASK_TYPE = {"project": "project", "test": "practice", "interview": "practice", "career": "practice",
             "learn": "learning", "practice": "practice"}


# ── validation (run by the test suite for every template) ───────────────────

def validate(t: dict) -> list[str]:
    errors = []
    tid = t.get("id")
    for key in ("id", "version", "title", "summary", "weeks", "phases"):
        if not t.get(key):
            errors.append(f"{tid}: missing {key}")
    weeks = t.get("weeks") or 0
    for f in t.get("fields") or []:
        if f not in DOMAIN_PACKS:
            errors.append(f"{tid}: unknown field {f}")
    if t.get("then") and t["then"] not in TEMPLATES:
        errors.append(f"{tid}: unknown handover template {t['then']}")
    expected, ids = 1, set()
    for p in t.get("phases") or []:
        first, last = p.get("weeks") or (0, 0)
        if first != expected or last < first:
            errors.append(f"{tid}/{p.get('id')}: weeks must start at {expected} and not go backwards")
        expected = last + 1
        if not p.get("milestones"):
            errors.append(f"{tid}/{p.get('id')}: no milestones")
        gate = p.get("gate")
        if gate and not (gate.get("topic") and 0 < gate.get("min_score", 0) <= 100 and gate.get("max_hold_weeks", 0) >= 1):
            errors.append(f"{tid}/{p.get('id')}: bad gate")
        for m in p.get("milestones") or []:
            mid = m.get("id") or ""
            if not re.fullmatch(r"tpl-[a-z0-9-]+", mid):
                errors.append(f"{tid}: bad milestone id {mid!r}")
            if mid in ids:
                errors.append(f"{tid}: duplicate milestone id {mid}")
            ids.add(mid)
            if not (m.get("title") and m.get("skill") and m.get("detail")):
                errors.append(f"{tid}/{mid}: title, skill and detail are required")
            if str(m.get("title", "")).lower().startswith("start "):
                errors.append(f"{tid}/{mid}: titles starting with 'Start ' are treated as beginner tasks by the planner")
            if m.get("kind") not in KINDS:
                errors.append(f"{tid}/{mid}: unknown kind {m.get('kind')}")
            if m.get("url") and not str(m["url"]).startswith("https://"):
                errors.append(f"{tid}/{mid}: links must be https")
            if m.get("link") and not str(m["link"]).startswith(INTERNAL_LINKS):
                errors.append(f"{tid}/{mid}: unknown Delta link {m['link']}")
    if expected - 1 != weeks:
        errors.append(f"{tid}: phases cover {expected - 1} weeks, template says {weeks}")
    for w in t.get("breaks") or []:
        if not 1 <= w <= weeks:
            errors.append(f"{tid}: break week {w} outside the template")
    return errors


# ── catalog ──────────────────────────────────────────────────────────────────

def _summary(t: dict) -> dict:
    return {"id": t["id"], "version": t["version"], "title": t["title"], "summary": t["summary"], "weeks": t["weeks"],
            "fields": t.get("fields") or [], "programs": t.get("programs") or [], "note": t.get("note"),
            "then": t.get("then"), "phases": len(t["phases"])}


def catalog(field: str | None = None) -> list[dict]:
    """Templates, the ones suited to the learner's field first."""
    items = [_summary(t) for t in TEMPLATES.values()]
    if field:
        items.sort(key=lambda s: 0 if (not s["fields"] or field in s["fields"]) else 1)
    return items


def outline(template_id: str) -> dict:
    t = TEMPLATES.get(template_id)
    if not t:
        raise LookupError("Unknown roadmap.")
    return {**_summary(t), "breaks": t.get("breaks") or [], "phase_list": [
        {"id": p["id"], "name": p["name"], "goal": p["goal"], "weeks": p["weeks"], "gate": p.get("gate"),
         "milestones": [{"title": m["title"], "skill": m["skill"], "optional": m["optional"]} for m in p["milestones"]]}
        for p in t["phases"]]}


# ── enrollment ───────────────────────────────────────────────────────────────

def active_enrollment(db: Session, user_id: str) -> RoadmapEnrollment | None:
    e = db.query(RoadmapEnrollment).filter(RoadmapEnrollment.user_id == user_id).first()
    return e if e and e.status == "active" and e.template_id in TEMPLATES else None


def start(db: Session, user_id: str, template_id: str, target_date: datetime.date | None = None,
          assigned_by_batch_id: str | None = None, today: datetime.date | None = None) -> RoadmapEnrollment:
    t = TEMPLATES.get(template_id)
    if not t:
        raise LookupError("Unknown roadmap.")
    today = today or datetime.date.today()
    if target_date and target_date <= today + datetime.timedelta(days=13):
        raise ValueError("Pick a target date at least two weeks away.")
    e = db.query(RoadmapEnrollment).filter(RoadmapEnrollment.user_id == user_id).first()
    if e and e.status == "active" and e.assigned_by_batch_id and not assigned_by_batch_id:
        raise PermissionError("Your college set this roadmap, so it can't be changed while you're in that batch.")
    if not e:
        e = RoadmapEnrollment(id=str(uuid.uuid4()), user_id=user_id)
        db.add(e)
    e.template_id, e.template_version, e.status = t["id"], t["version"], "active"
    e.started_on, e.target_date, e.week_index, e.held_weeks = today, target_date, 0, 0
    e.assigned_by_batch_id, e.ended_at = assigned_by_batch_id, None
    db.commit()
    return e


def stop(db: Session, user_id: str) -> None:
    e = active_enrollment(db, user_id)
    if not e:
        return
    if e.assigned_by_batch_id:
        raise PermissionError("Your college set this roadmap, so it can't be stopped while you're in that batch.")
    e.status, e.ended_at = "stopped", datetime.datetime.utcnow()
    db.commit()


# ── where the learner is ─────────────────────────────────────────────────────

def _available_weeks(e: RoadmapEnrollment) -> int | None:
    if not e.target_date:
        return None
    return max(1, (e.target_date - e.started_on).days // 7)


def compressed(e: RoadmapEnrollment, t: dict) -> bool:
    available = _available_weeks(e)
    return available is not None and available < t["weeks"]


def template_week(e: RoadmapEnrollment, t: dict) -> int:
    """1-based week inside the template. With a tighter target date the template
    is squeezed onto the learner's real weeks, so it moves faster than 1:1."""
    if compressed(e, t):
        return min(t["weeks"], e.week_index * t["weeks"] // _available_weeks(e) + 1)
    return min(t["weeks"], e.week_index + 1)


def _phase_at(t: dict, week: int) -> dict:
    return next((p for p in t["phases"] if p["weeks"][0] <= week <= p["weeks"][1]), t["phases"][-1])


def _required(p: dict, squeeze: bool) -> list[dict]:
    return [m for m in p["milestones"] if not (squeeze and m["optional"])]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _matches(a: str, b: str) -> bool:
    a, b = _norm(a), _norm(b)
    return bool(a and b) and (a == b or a in b or b in a)


def _evidence(db: Session, user_id: str, since: datetime.date) -> dict:
    """What the learner has proven in tests (never self-claimed skills)."""
    from app.services.readiness import compute_readiness
    skills = compute_readiness(db, user_id)["skills"]
    topic_best: dict[str, int] = {}
    since_dt = datetime.datetime.combine(since, datetime.time())
    for s in db.query(SandboxSession).filter(SandboxSession.user_id == user_id, SandboxSession.type == "theory",
                                             SandboxSession.status == "completed"):
        try:
            topic = json.loads(s.data or "{}").get("topic") or s.title
        except ValueError:
            topic = s.title
        if s.score is not None:
            key = _norm(topic)
            topic_best[key] = max(topic_best.get(key, 0), s.score)
            if (s.completed_at or s.created_at) and (s.completed_at or s.created_at) >= since_dt:
                topic_best["since:" + key] = max(topic_best.get("since:" + key, 0), s.score)
    return {"skills": skills, "topics": topic_best}


def _proven(ev: dict, skill: str) -> bool:
    if any(_matches(s["skill"], skill) and s["score"] >= PROVEN_SCORE and s["questions"] >= PROVEN_QUESTIONS
           for s in ev["skills"]):
        return True
    return any(not k.startswith("since:") and _matches(k, skill) and v >= PROVEN_SCORE for k, v in ev["topics"].items())


def _gate_passed(ev: dict, gate: dict) -> bool:
    return any(k.startswith("since:") and _matches(k[6:], gate["topic"]) and v >= gate["min_score"]
               for k, v in ev["topics"].items())


def _done_ids(db: Session, user_id: str) -> set[str]:
    rows = db.query(XpEvent.source_id).filter(XpEvent.user_id == user_id, XpEvent.source_type == "weekly_task",
                                              XpEvent.source_id.like("tpl-%")).all()
    return {r[0].split("@")[0] for r in rows}


def _plan(db: Session, e: RoadmapEnrollment, t: dict) -> dict:
    """Which milestones are due, done, skipped (proven) and in the backlog."""
    week = template_week(e, t)
    squeeze = compressed(e, t)
    phase = _phase_at(t, week)
    ev = _evidence(db, e.user_id, e.started_on)
    done = _done_ids(db, e.user_id)

    def eligible(p):
        return [m for m in _required(p, squeeze) if not (m["skip"] and m["id"] not in done and _proven(ev, m["skill"]))]

    first, last = phase["weeks"]
    phase_items = eligible(phase)
    quota = math.ceil(len(_required(phase, squeeze)) / (last - first + 1))
    due = phase_items[:quota * (week - first + 1)]
    earlier = [p for p in t["phases"] if p["weeks"][1] < first]
    backlog = [m for p in earlier for m in eligible(p) if m["id"] not in done]
    skipped = [m for p in t["phases"] if p["weeks"][0] <= week for m in _required(p, squeeze)
               if m["skip"] and m["id"] not in done and _proven(ev, m["skill"])]
    # "On track" judges only what fell due before this week, not this week's own tasks.
    overdue_window = [m for p in earlier for m in eligible(p)] + phase_items[:quota * (week - first)]
    return {"week": week, "phase": phase, "squeeze": squeeze, "ev": ev, "done": done,
            "this_week": [m for m in due if m["id"] not in done], "backlog": backlog, "skipped": skipped,
            "due_count": len(overdue_window), "due_done": sum(1 for m in overdue_window if m["id"] in done)}


def is_break_week(e: RoadmapEnrollment) -> bool:
    t = TEMPLATES[e.template_id]
    return not compressed(e, t) and template_week(e, t) in (t.get("breaks") or [])


def _action(m: dict, t: dict, phase: dict, why: str | None = None) -> dict:
    return {
        "id": m["id"], "node_id": f"{phase['id']}-{_norm(m['skill']).replace(' ', '-')}",
        "type": TASK_TYPE[m["kind"]], "title": m["title"], "skill": m["skill"],
        "description": m["detail"], "detail": m["detail"],
        "url": m.get("url") or m.get("link") or "", "resource_url": m.get("url") or "",
        "source": t["title"], "why_now": why or phase["goal"], "difficulty_level": "Intermediate",
        "template_milestone": True,
    }


def weekly_actions(db: Session, e: RoadmapEnrollment, cap: int) -> list[dict]:
    t = TEMPLATES[e.template_id]
    plan = _plan(db, e, t)
    phase = plan["phase"]
    actions = [_action(m, t, phase) for m in plan["this_week"]]
    actions += [_action(m, t, phase, "Carried over from an earlier phase.") for m in plan["backlog"][:BACKLOG_PER_WEEK]]
    phase_skills = {m["skill"] for m in phase["milestones"]}
    weak = sorted((s for s in plan["ev"]["skills"]
                   if s["questions"] >= WEAK_QUESTIONS and s["score"] < WEAK_SCORE
                   and any(_matches(s["skill"], k) for k in phase_skills)), key=lambda s: s["score"])
    if weak:
        w = weak[0]
        slug = _norm(w["skill"]).replace(" ", "-")
        actions.append({
            "id": f"tpl-revise-{slug}-w{plan['week']}", "node_id": f"{phase['id']}-{slug}", "type": "practice",
            "title": f"Revise {w['skill']}", "skill": w["skill"],
            "description": f"Your tests put {w['skill']} at {w['score']}%. Revise the basics, then retake a test on it.",
            "url": f"/practice/theory?topic={w['skill']}", "resource_url": "", "source": t["title"],
            "why_now": "A weak spot in this phase.", "difficulty_level": "Intermediate", "template_milestone": True,
        })
    return actions[:cap + (1 if plan["squeeze"] else 0)]


def phases(db: Session, e: RoadmapEnrollment) -> list[dict]:
    """The template's phases in the planner's phase/node shape (for the roadmap views)."""
    t = TEMPLATES[e.template_id]
    plan = _plan(db, e, t)
    out = []
    for p in t["phases"]:
        nodes: dict[str, dict] = {}
        for m in _required(p, plan["squeeze"]):
            n = nodes.setdefault(m["skill"], {"id": f"{p['id']}-{_norm(m['skill']).replace(' ', '-')}",
                                               "label": m["skill"], "skill_name": m["skill"], "description": m["detail"],
                                               "resource_url": m.get("url") or "", "_ms": []})
            n["_ms"].append(m["id"] in plan["done"] or m in plan["skipped"])
        for n in nodes.values():
            ms = n.pop("_ms")
            n["status"] = "mastered" if all(ms) else ("in_progress" if any(ms) or p is plan["phase"] else "locked")
        out.append({"id": p["id"], "name": p["name"], "description": p["goal"], "nodes": list(nodes.values())})
    return out


def advance(db: Session, user_id: str) -> RoadmapEnrollment | None:
    """Called once per real weekly cycle. Moves a week on, unless the phase's
    gate isn't passed yet (held for at most max_hold_weeks)."""
    e = active_enrollment(db, user_id)
    if not e:
        return None
    t = TEMPLATES[e.template_id]
    week = template_week(e, t)
    phase = _phase_at(t, week)
    gate = phase.get("gate")
    next_week = template_week(_peek(e, 1), t)
    leaving_phase = next_week > phase["weeks"][1]
    if gate and leaving_phase and e.held_weeks < gate["max_hold_weeks"] \
            and not _gate_passed(_evidence(db, user_id, e.started_on), gate):
        e.held_weeks += 1
        db.commit()
        return e
    e.week_index += 1
    e.held_weeks = 0 if leaving_phase else e.held_weeks
    if e.week_index >= (_available_weeks(e) if compressed(e, t) else t["weeks"]):
        if t.get("then") and t["then"] in TEMPLATES:
            nxt = TEMPLATES[t["then"]]
            e.template_id, e.template_version, e.started_on = nxt["id"], nxt["version"], datetime.date.today()
            e.week_index, e.held_weeks, e.target_date = 0, 0, None
        else:
            e.status, e.ended_at = "completed", datetime.datetime.utcnow()
    db.commit()
    return e


def _peek(e: RoadmapEnrollment, step: int) -> RoadmapEnrollment:
    return RoadmapEnrollment(week_index=e.week_index + step, started_on=e.started_on, target_date=e.target_date)


def progress(db: Session, e: RoadmapEnrollment | None) -> dict | None:
    if not e:
        return None
    t = TEMPLATES[e.template_id]
    plan = _plan(db, e, t)
    required = sum(len(_required(p, plan["squeeze"])) for p in t["phases"])
    on_track = plan["due_count"] == 0 or plan["due_done"] / plan["due_count"] >= ON_TRACK_SHARE
    gate = plan["phase"].get("gate")
    return {
        "template_id": t["id"], "title": t["title"], "week": plan["week"], "weeks": t["weeks"],
        "phase": plan["phase"]["name"], "phase_goal": plan["phase"]["goal"],
        "milestones_done": len(plan["done"] & {m["id"] for p in t["phases"] for m in p["milestones"]}),
        "milestones_skipped": len(plan["skipped"]), "milestones_total": required,
        "on_track": on_track, "compressed": plan["squeeze"],
        "target_date": e.target_date.isoformat() if e.target_date else None,
        "held_at_gate": e.held_weeks > 0, "gate": gate,
        "college_assigned": bool(e.assigned_by_batch_id), "then": t.get("then"),
    }
