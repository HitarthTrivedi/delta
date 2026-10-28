"""Company roadmaps: a company states the skills it needs, Delta assembles a
roadmap from the reviewed skill library (no AI writes it), a Delta admin
approves it, and students in that company's recruiter pool can follow it as
an extra track next to their own plan.

- Joining records a `company_roadmap` consent for that one roadmap; the company
  sees a student only while that consent stands and the student is still in
  its pool. Leaving, or a pool change, withdraws it.
- A student follows at most 2 company tracks; each adds up to 2 tasks a week.
- Company tests reuse the college-test rules (services/assigned_tests.py).
- An approved roadmap is locked: members follow exactly what was reviewed.
  To change it, the company duplicates it into a new draft.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import math
import re
import uuid

from sqlalchemy.orm import Session

from app.models.company import CompanyRoadmap, CompanyRoadmapMember, CompanyTest
from app.models.compliance import ConsentRecord, Recruiter
from app.models.user import User
from app.services import compliance, integrity
from app.services.assigned_tests import SECONDS_PER_QUESTION, attempts, check_attempt, is_open, summary
from app.services.roadmap_templates import INTERNAL_LINKS, KINDS, done_ids, evidence, proven
from app.services.skill_library import milestones_for, validate_milestones
from app.services.theory_test_ai import APTITUDE_AREAS, DIFFICULTIES, MAX_QUESTIONS, MIN_QUESTIONS, generate_test

MAX_SKILLS = 12
MIN_WEEKS, MAX_WEEKS = 4, 16
MAX_TRACKS = 2
TASKS_PER_TRACK = 2
ON_TRACK_SHARE = 0.7
EDITABLE = ("draft", "rejected")


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")[:30] or "skill"


def _clean_skills(skills: list[str]) -> list[str]:
    out, seen = [], set()
    for s in skills or []:
        name = " ".join(str(s or "").split())[:60]
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    if not out:
        raise ValueError("Add at least one skill.")
    if len(out) > MAX_SKILLS:
        raise ValueError(f"Keep it to {MAX_SKILLS} skills or fewer.")
    return out


def _weeks(weeks: int) -> int:
    if not MIN_WEEKS <= int(weeks) <= MAX_WEEKS:
        raise ValueError(f"A roadmap runs {MIN_WEEKS} to {MAX_WEEKS} weeks.")
    return int(weeks)


# ── building a roadmap (recruiter) ───────────────────────────────────────────

def build_milestones(skills: list[str]) -> list[dict]:
    """The library's steps for each skill, in the company's order."""
    out, ids = [], set()
    for skill in _clean_skills(skills):
        for i, step in enumerate(milestones_for(skill), 1):
            mid = f"co-{_slug(skill)}-{i}"
            while mid in ids:
                mid += "x"
            ids.add(mid)
            out.append({"id": mid, **step})
    return out


def draft_from_skills(skills: list[str], weeks: int = 8) -> dict:
    skills = _clean_skills(skills)
    return {"skills": skills, "milestones": build_milestones(skills), "weeks": _weeks(weeks)}


def draft_from_text(db: Session, text: str, weeks: int = 8) -> dict:
    """Read a pasted job ad with Job match's shared, cached extraction."""
    from app.services.job_match import get_or_extract
    job = get_or_extract(db, text)
    db.commit()
    skills = [s["name"] for s in json.loads(job.skills)][:MAX_SKILLS]
    return {**draft_from_skills(skills, weeks), "title": job.title, "role": job.title}


def _clean_milestones(milestones: list[dict], roadmap_id: str) -> list[dict]:
    """Keep only the fields we know, within limits, with ids unique to this roadmap."""
    prefix = f"co-{roadmap_id[:8]}-"
    out = []
    for m in milestones or []:
        mid = str(m.get("id") or "").lower()
        if not mid.startswith(prefix):
            mid = prefix + _slug(re.sub(r"^co-", "", mid) or m.get("title"))
        url = str(m.get("url") or "").strip() or None
        link = str(m.get("link") or "").strip() or None
        out.append({"id": mid[:80], "title": " ".join(str(m.get("title") or "").split())[:120],
                    "skill": " ".join(str(m.get("skill") or "").split())[:60],
                    "detail": " ".join(str(m.get("detail") or "").split())[:400],
                    "kind": m.get("kind") if m.get("kind") in KINDS else "practice",
                    "url": url if url and url.startswith("https://") else None,
                    "link": link if link and link.startswith(INTERNAL_LINKS) else None})
    if not out:
        raise ValueError("A roadmap needs at least one step.")
    if len(out) > 60:
        raise ValueError("Keep it to 60 steps or fewer.")
    errors = validate_milestones(out)
    if errors:
        raise ValueError(errors[0])
    return out


def _owned(db: Session, recruiter: Recruiter, roadmap_id: str) -> CompanyRoadmap:
    r = db.query(CompanyRoadmap).filter(CompanyRoadmap.id == roadmap_id,
                                        CompanyRoadmap.recruiter_id == recruiter.id).first()
    if not r:
        raise LookupError("Roadmap not found.")
    return r


def _members(db: Session, roadmap_id: str) -> list[CompanyRoadmapMember]:
    return db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.roadmap_id == roadmap_id,
                                                 CompanyRoadmapMember.status == "active").all()


def roadmap_dict(db: Session, r: CompanyRoadmap, company: str | None = None) -> dict:
    return {"id": r.id, "title": r.title, "role": r.role, "summary": r.summary, "skills": json.loads(r.skills),
            "milestones": json.loads(r.milestones), "weeks": r.weeks, "status": r.status,
            "review_note": r.review_note, "company": company,
            "created_at": r.created_at.isoformat(), "members": len(_members(db, r.id))}


def create(db: Session, recruiter: Recruiter, *, title: str, role: str | None, summary: str | None,
           skills: list[str], milestones: list[dict] | None, weeks: int) -> dict:
    title = " ".join(str(title or "").split())[:120]
    if not title:
        raise ValueError("Give the roadmap a title.")
    r = CompanyRoadmap(id=str(uuid.uuid4()), recruiter_id=recruiter.id, title=title,
                       role=" ".join(str(role or "").split())[:120] or None,
                       summary=" ".join(str(summary or "").split())[:600] or None, weeks=_weeks(weeks))
    skills = _clean_skills(skills)
    r.skills = json.dumps(skills)
    r.milestones = json.dumps(_clean_milestones(milestones or build_milestones(skills), r.id))
    db.add(r)
    db.commit()
    return roadmap_dict(db, r, recruiter.company)


def update(db: Session, recruiter: Recruiter, roadmap_id: str, **fields) -> dict:
    r = _owned(db, recruiter, roadmap_id)
    if r.status not in EDITABLE:
        raise ValueError("Only drafts can be edited. Duplicate an approved roadmap to change it.")
    if fields.get("title") is not None:
        r.title = " ".join(fields["title"].split())[:120] or r.title
    for key in ("role", "summary"):
        if fields.get(key) is not None:
            setattr(r, key, " ".join(fields[key].split())[:600] or None)
    if fields.get("weeks") is not None:
        r.weeks = _weeks(fields["weeks"])
    if fields.get("skills") is not None:
        r.skills = json.dumps(_clean_skills(fields["skills"]))
    if fields.get("milestones") is not None:
        r.milestones = json.dumps(_clean_milestones(fields["milestones"], r.id))
    db.commit()
    return roadmap_dict(db, r, recruiter.company)


def submit(db: Session, recruiter: Recruiter, roadmap_id: str) -> dict:
    r = _owned(db, recruiter, roadmap_id)
    if r.status not in EDITABLE:
        raise ValueError("This roadmap has already been submitted.")
    r.status, r.submitted_at, r.review_note = "pending_review", _now(), None
    db.commit()
    return roadmap_dict(db, r, recruiter.company)


def archive(db: Session, recruiter: Recruiter, roadmap_id: str) -> dict:
    """Hidden from new students and no more weekly tasks; past results stay."""
    r = _owned(db, recruiter, roadmap_id)
    r.status = "archived"
    db.commit()
    return roadmap_dict(db, r, recruiter.company)


def duplicate(db: Session, recruiter: Recruiter, roadmap_id: str) -> dict:
    r = _owned(db, recruiter, roadmap_id)
    milestones = [{**m, "id": re.sub(r"^co-[a-z0-9]{8}-", "co-", m["id"])} for m in json.loads(r.milestones)]
    return create(db, recruiter, title=f"{r.title} (copy)"[:120], role=r.role, summary=r.summary,
                  skills=json.loads(r.skills), milestones=milestones, weeks=r.weeks)


def my_roadmaps(db: Session, recruiter: Recruiter) -> list[dict]:
    rows = (db.query(CompanyRoadmap).filter(CompanyRoadmap.recruiter_id == recruiter.id)
            .order_by(CompanyRoadmap.created_at.desc()).all())
    return [roadmap_dict(db, r, recruiter.company) for r in rows]


def get(db: Session, recruiter: Recruiter, roadmap_id: str) -> dict:
    return roadmap_dict(db, _owned(db, recruiter, roadmap_id), recruiter.company)


# ── Delta admin review ───────────────────────────────────────────────────────

def pending(db: Session) -> list[dict]:
    rows = (db.query(CompanyRoadmap, Recruiter).join(Recruiter, Recruiter.id == CompanyRoadmap.recruiter_id)
            .filter(CompanyRoadmap.status == "pending_review").order_by(CompanyRoadmap.submitted_at).all())
    return [{**roadmap_dict(db, r, rec.company), "recruiter_pool": rec.pool or "open"} for r, rec in rows]


def review(db: Session, roadmap_id: str, approve: bool, note: str | None, by: str) -> dict:
    r = db.get(CompanyRoadmap, roadmap_id)
    if not r or r.status != "pending_review":
        raise LookupError("Nothing to review.")
    if not approve and not (note or "").strip():
        raise ValueError("Tell the company what to change.")
    r.status = "approved" if approve else "rejected"
    r.review_note = " ".join((note or "").split())[:600] or None
    r.reviewed_by, r.approved_at = by, _now() if approve else None
    db.commit()
    return roadmap_dict(db, r)


# ── students ─────────────────────────────────────────────────────────────────

def _in_pool(db: Session, recruiter: Recruiter, user_ids: set[str]) -> set[str]:
    if recruiter.status != "approved":
        return set()
    return compliance.in_recruiter_pool(db, recruiter, user_ids)


def _consented(db: Session, user_id: str, roadmap_id: str) -> bool:
    rec = (db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id,
                                          ConsentRecord.purpose == compliance.COMPANY_ROADMAP,
                                          ConsentRecord.subject_id == roadmap_id)
           .order_by(ConsentRecord.created_at.desc()).first())
    return bool(rec and rec.action == "granted")


def visible_to(db: Session, user_id: str) -> dict:
    """Approved roadmaps from companies whose pool this student is in."""
    pool, reason = compliance.recruiter_pool_for(db, user_id)
    if not pool:
        return {"roadmaps": [], "reason": reason}
    joined = {m.roadmap_id for m in db.query(CompanyRoadmapMember).filter(
        CompanyRoadmapMember.user_id == user_id, CompanyRoadmapMember.status == "active")}
    out = []
    rows = (db.query(CompanyRoadmap, Recruiter).join(Recruiter, Recruiter.id == CompanyRoadmap.recruiter_id)
            .filter(CompanyRoadmap.status == "approved").order_by(CompanyRoadmap.approved_at.desc()).all())
    allowed: dict[str, bool] = {}
    for r, rec in rows:
        if rec.id not in allowed:
            allowed[rec.id] = user_id in _in_pool(db, rec, {user_id})
        if allowed[rec.id]:
            out.append({**roadmap_dict(db, r, rec.company), "joined": r.id in joined})
    return {"roadmaps": out, "reason": reason}


def _approved_visible(db: Session, user_id: str, roadmap_id: str) -> tuple[CompanyRoadmap, Recruiter]:
    r = db.get(CompanyRoadmap, roadmap_id)
    rec = db.get(Recruiter, r.recruiter_id) if r else None
    if not r or r.status != "approved" or not rec or user_id not in _in_pool(db, rec, {user_id}):
        raise LookupError("Roadmap not found.")
    return r, rec


def join(db: Session, user_id: str, roadmap_id: str) -> dict:
    r, rec = _approved_visible(db, user_id, roadmap_id)
    m = db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.roadmap_id == r.id,
                                              CompanyRoadmapMember.user_id == user_id).first()
    if m and m.status == "active":
        return my_tracks(db, user_id)
    active = db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.user_id == user_id,
                                                   CompanyRoadmapMember.status == "active").count()
    if active >= MAX_TRACKS:
        raise ValueError(f"You can follow up to {MAX_TRACKS} company roadmaps. Leave one first.")
    if m:
        m.status, m.joined_at, m.left_at = "active", _now(), None
    else:
        db.add(CompanyRoadmapMember(id=str(uuid.uuid4()), roadmap_id=r.id, user_id=user_id))
    db.commit()
    compliance.record_consent(db, user_id, compliance.COMPANY_ROADMAP, True, subject_id=r.id)
    return my_tracks(db, user_id)


def leave(db: Session, user_id: str, roadmap_id: str) -> dict:
    m = db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.roadmap_id == roadmap_id,
                                              CompanyRoadmapMember.user_id == user_id,
                                              CompanyRoadmapMember.status == "active").first()
    if m:
        m.status, m.left_at = "left", _now()
        db.commit()
        compliance.record_consent(db, user_id, compliance.COMPANY_ROADMAP, False, subject_id=roadmap_id)
    return my_tracks(db, user_id)


def leave_all(db: Session, user_id: str) -> None:
    for m in db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.user_id == user_id,
                                                   CompanyRoadmapMember.status == "active").all():
        leave(db, user_id, m.roadmap_id)


def _plan(r: CompanyRoadmap, m: CompanyRoadmapMember, ev: dict, done: set[str],
          today: datetime.date | None = None) -> dict:
    today = today or datetime.datetime.utcnow().date()  # joined_at is UTC
    milestones = json.loads(r.milestones)
    week = min(r.weeks, (today - m.joined_at.date()).days // 7 + 1)
    eligible = [x for x in milestones if not (x["kind"] != "test" and x["id"] not in done and proven(ev, x["skill"]))]
    quota = math.ceil(len(milestones) / r.weeks)
    due = eligible[:quota * week]
    overdue = eligible[:quota * (week - 1)]
    done_count = sum(1 for x in milestones if x["id"] in done)
    return {"week": week, "weeks": r.weeks, "this_week": [x for x in due if x["id"] not in done],
            "done": done_count, "skipped": len(milestones) - len(eligible), "total": len(milestones),
            "on_track": not overdue or sum(1 for x in overdue if x["id"] in done) / len(overdue) >= ON_TRACK_SHARE}


def _active_tracks(db: Session, user_id: str) -> list[tuple[CompanyRoadmapMember, CompanyRoadmap, Recruiter]]:
    rows = (db.query(CompanyRoadmapMember, CompanyRoadmap, Recruiter)
            .join(CompanyRoadmap, CompanyRoadmap.id == CompanyRoadmapMember.roadmap_id)
            .join(Recruiter, Recruiter.id == CompanyRoadmap.recruiter_id)
            .filter(CompanyRoadmapMember.user_id == user_id, CompanyRoadmapMember.status == "active").all())
    return rows


def _student_tests(db: Session, user_id: str, roadmap_id: str) -> list[dict]:
    out = []
    for t in db.query(CompanyTest).filter(CompanyTest.roadmap_id == roadmap_id).order_by(CompanyTest.created_at.desc()):
        s = attempts(db, t.id, [user_id]).get(user_id)
        out.append({"id": t.id, "title": t.title, "topic": t.topic, "questions": len(json.loads(t.questions)),
                    "timed": bool(t.time_limit_seconds), "due_date": t.due_date.isoformat() if t.due_date else None,
                    "open": is_open(t),
                    "status": "done" if s and s.status == "completed" else ("started" if s else "not started"),
                    "score": s.score if s and s.status == "completed" else None})
    return out


def my_tracks(db: Session, user_id: str) -> dict:
    tracks = []
    rows = _active_tracks(db, user_id)
    if rows:
        ev = evidence(db, user_id, min(m.joined_at.date() for m, _, _ in rows))
        done = done_ids(db, user_id, "co-")
        for m, r, rec in rows:
            p = _plan(r, m, ev, done)
            tracks.append({"roadmap_id": r.id, "title": r.title, "company": rec.company, "status": r.status,
                           "week": p["week"], "weeks": p["weeks"], "done": p["done"], "total": p["total"],
                           "skipped": p["skipped"], "on_track": p["on_track"],
                           "this_week": [x["title"] for x in p["this_week"][:TASKS_PER_TRACK]],
                           "tests": _student_tests(db, user_id, r.id)})
    return {"tracks": tracks, "max_tracks": MAX_TRACKS}


def track_actions(db: Session, user_id: str) -> list[dict]:
    """For the weekly plan: per company track, an open test first, then milestones (2 per track)."""
    out = []
    rows = [(m, r, rec) for m, r, rec in _active_tracks(db, user_id) if r.status == "approved"]
    if not rows:
        return out
    ev = evidence(db, user_id, min(m.joined_at.date() for m, _, _ in rows))
    done = done_ids(db, user_id, "co-")
    for m, r, rec in rows:
        why = f"From {rec.company}'s roadmap: {r.title}."
        picks = []
        for t in _student_tests(db, user_id, r.id):
            if t["open"] and t["status"] != "done":
                picks.append({"id": f"company-test-{t['id'][:8]}", "type": "practice",
                              "title": f"Take {rec.company}'s test: {t['title']}"[:120], "skill": t["topic"],
                              "description": f"{t['questions']} questions set by {rec.company}.",
                              "detail": f"{t['questions']} questions set by {rec.company}.",
                              "url": f"/practice/theory?assignment={t['id']}", "resource_url": "",
                              "source": rec.company, "why_now": why, "difficulty_level": "Intermediate"})
        for x in _plan(r, m, ev, done)["this_week"]:
            picks.append({"id": x["id"], "node_id": f"company-{r.id[:8]}", "type": "project" if x["kind"] == "project" else "practice",
                          "title": x["title"], "skill": x["skill"], "description": x["detail"], "detail": x["detail"],
                          "url": x.get("url") or x.get("link") or "", "resource_url": x.get("url") or "",
                          "source": rec.company, "why_now": why, "difficulty_level": "Intermediate"})
        out.extend(picks[:TASKS_PER_TRACK])
    return out


# ── what the company sees ────────────────────────────────────────────────────

def _sharing_members(db: Session, recruiter: Recruiter, r: CompanyRoadmap) -> list[CompanyRoadmapMember]:
    """Members who still consent and are still in the company's pool."""
    members = [m for m in _members(db, r.id) if _consented(db, m.user_id, r.id)]
    allowed = _in_pool(db, recruiter, {m.user_id for m in members})
    return [m for m in members if m.user_id in allowed]


def members_for(db: Session, recruiter: Recruiter, roadmap_id: str) -> dict:
    from app.routers.recruiter import _campus_education, _public_profile
    from app.services.profile_store import load_profile
    from app.services.readiness import readiness_bulk
    r = _owned(db, recruiter, roadmap_id)
    members = _sharing_members(db, recruiter, r)
    ids = [m.user_id for m in members]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(ids or [""]))}
    campus = _campus_education(db, ids)
    reports = readiness_bulk(db, ids)
    skills = json.loads(r.skills)
    tests = db.query(CompanyTest).filter(CompanyTest.roadmap_id == r.id).order_by(CompanyTest.created_at).all()
    tried = {t.id: attempts(db, t.id, ids) for t in tests}
    out = []
    for m in members:
        u = users[m.user_id]
        prof = _public_profile(u, load_profile(u.id, db=db) or {}, campus.get(u.id))
        ev = {"skills": reports[u.id]["skills"], "topics": {}}
        done = done_ids(db, u.id, f"co-{r.id[:8]}-")
        p = _plan(r, m, ev, done)
        skill_scores = []
        for name in skills:
            hit = next((s for s in reports[u.id]["skills"] if s["skill"].lower() == name.lower()
                        or name.lower() in s["skill"].lower() or s["skill"].lower() in name.lower()), None)
            skill_scores.append({"skill": name, "score": hit["score"] if hit else None,
                                 "evidence": hit["evidence"] if hit else 0})
        test_rows = []
        for t in tests:
            s = tried[t.id].get(u.id)
            finished = bool(s and s.status == "completed")
            test_rows.append({"test_id": t.id, "title": t.title, "score": s.score if finished else None,
                              "status": "done" if finished else ("started" if s else "not started"),
                              "notes": integrity.notes(s)["flags"] if finished else []})
        out.append({"user_id": u.id, "name": prof["name"], "target_role": prof["target_role"],
                    "education": prof["education"], "joined_at": m.joined_at.isoformat(),
                    "week": p["week"], "weeks": p["weeks"], "done": p["done"], "total": p["total"],
                    "on_track": p["on_track"], "readiness": reports[u.id]["readiness"],
                    "readiness_label": reports[u.id]["label"], "skills": skill_scores, "tests": test_rows})
    out.sort(key=lambda x: (-(x["done"]), x["name"].lower()))
    return {"roadmap": roadmap_dict(db, r, recruiter.company), "students": out}


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def members_csv(db: Session, recruiter: Recruiter, roadmap_id: str) -> str:
    data = members_for(db, recruiter, roadmap_id)
    skills = data["roadmap"]["skills"]
    tests = data["students"][0]["tests"] if data["students"] else []
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["name", "institution", "week", "steps_done", "steps_total", "on_track", "readiness",
                *[f"skill: {s}" for s in skills], *[f"test: {t['title']}" for t in tests]])
    for s in data["students"]:
        w.writerow([_cell(v) for v in [
            s["name"], (s["education"] or {}).get("institution"), s["week"], s["done"], s["total"],
            "yes" if s["on_track"] else "no", s["readiness"], *[x["score"] for x in s["skills"]],
            *[t["score"] for t in s["tests"]]]])
    return buf.getvalue()


# ── company tests ────────────────────────────────────────────────────────────

def create_test(db: Session, recruiter: Recruiter, roadmap_id: str, *, topic: str | None, category: str = "technical",
                area: str | None = None, difficulty: str = "medium", num_questions: int = 10, timed: bool = True,
                due_date: datetime.date | None = None, title: str | None = None) -> dict:
    r = _owned(db, recruiter, roadmap_id)
    if r.status != "approved":
        raise ValueError("Tests can be set once the roadmap is approved.")
    category = "aptitude" if category == "aptitude" else "technical"
    if category == "technical" and not (topic or "").strip():
        raise ValueError("Pick a topic for the test.")
    if due_date and due_date < datetime.date.today():
        raise ValueError("The due date is in the past.")
    num_questions = max(MIN_QUESTIONS, min(MAX_QUESTIONS, num_questions))
    difficulty = difficulty if difficulty in DIFFICULTIES else "medium"
    area = area if area in APTITUDE_AREAS else None
    try:  # one model call for everyone on the roadmap; no student data in the prompt
        topic, questions = generate_test(None, (topic or "").strip() or None, num_questions, difficulty, category,
                                         area, personalize=False)
    except ValueError as exc:
        raise RuntimeError("Could not make the test right now. Try again in a moment.") from exc
    t = CompanyTest(id=str(uuid.uuid4()), roadmap_id=r.id, recruiter_id=recruiter.id, topic=topic,
                    category=category, difficulty=difficulty, questions=json.dumps(questions),
                    title=" ".join((title or "").split())[:120] or f"{recruiter.company}: {topic}"[:120],
                    time_limit_seconds=len(questions) * SECONDS_PER_QUESTION if timed else None, due_date=due_date)
    db.add(t)
    db.commit()
    return summary(db, t, len(_sharing_members(db, recruiter, r)))


def list_tests(db: Session, recruiter: Recruiter, roadmap_id: str) -> list[dict]:
    r = _owned(db, recruiter, roadmap_id)
    n = len(_sharing_members(db, recruiter, r))
    return [summary(db, t, n) for t in db.query(CompanyTest).filter(CompanyTest.roadmap_id == r.id)
            .order_by(CompanyTest.created_at.desc())]


def close_test(db: Session, recruiter: Recruiter, test_id: str) -> dict:
    t = db.query(CompanyTest).filter(CompanyTest.id == test_id, CompanyTest.recruiter_id == recruiter.id).first()
    if not t:
        raise LookupError("Test not found.")
    t.closed_at = t.closed_at or _now()
    db.commit()
    return summary(db, t)


def test_for_student(db: Session, user_id: str, test_id: str) -> CompanyTest:
    """The company test, if this student follows that roadmap (and still shares with the company)."""
    t = db.get(CompanyTest, test_id)
    r = db.get(CompanyRoadmap, t.roadmap_id) if t else None
    rec = db.get(Recruiter, r.recruiter_id) if r else None
    member = r and db.query(CompanyRoadmapMember).filter(CompanyRoadmapMember.roadmap_id == r.id,
                                                         CompanyRoadmapMember.user_id == user_id,
                                                         CompanyRoadmapMember.status == "active").first()
    if not (t and member and _consented(db, user_id, r.id) and user_id in _in_pool(db, rec, {user_id})):
        raise LookupError("Test not found.")
    check_attempt(db, t, user_id)
    return t


def student_tests(db: Session, user_id: str) -> list[dict]:
    out = []
    for m, r, rec in _active_tracks(db, user_id):
        out += [{**t, "source": rec.company} for t in _student_tests(db, user_id, r.id)]
    return out
