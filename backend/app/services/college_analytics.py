"""What a college's placement team (TPO/faculty) sees about its students:
batch readiness, activity, weak skills, an at-risk list, a per-student
drill-down and CSV exports.

Only active members of the college count. The college sees readiness,
coverage, per-skill results, practice counts and scores, integrity notes and
active days; never chats, résumé text, job matches, circles, leagues, XP,
streaks, recruiter opt-in or reminder data (Privacy Policy §6A). Everything
is computed with a fixed number of queries however large the batch is.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io

from sqlalchemy.orm import Session

from app.models.college import Batch, CollegeMember, RosterEntry
from app.models.sandbox_session import SandboxSession
from app.models.user import User
from app.services import cache, integrity
from app.services.engagement_metrics import active_dates_by_user, last_active_by_user
from app.services.readiness import readiness_bulk, readiness_from
from app.services.domain_packs import field_for_user

CACHE_TTL = 300
TREND_WEEKS = 8
INACTIVE_DAYS = 7
NO_PRACTICE_DAYS = 21
LOW_READINESS = 45
WEAK_SKILL = 70
UNASSIGNED = "unassigned"
BUCKETS = ("Interview-ready", "Almost there", "Building up", "Just starting", "Not started")
RISK_TEXT = {
    "inactive_7d": "No learning activity for 7+ days",
    "low_readiness": f"Readiness below {LOW_READINESS}",
    "no_practice_21d": "No test, coding or interview practice for 21+ days",
}
EXPORTS = ("roster_status", "batch_readiness", "outcomes_naac", "test_results")


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole, 1) if whole else None


def _members(db: Session, college_id: str, batch_id: str | None = None) -> list[CollegeMember]:
    q = db.query(CollegeMember).filter(CollegeMember.college_id == college_id, CollegeMember.status == "active")
    if batch_id == UNASSIGNED:
        q = q.filter(CollegeMember.batch_id.is_(None))
    elif batch_id:
        q = q.filter(CollegeMember.batch_id == batch_id)
    return q.all()


def _names(db: Session, members: list[CollegeMember]) -> dict[str, tuple[str, str | None]]:
    """user_id -> (name, roll number), roster name first."""
    entry_ids = [m.roster_entry_id for m in members if m.roster_entry_id]
    entries = {e.id: e for e in db.query(RosterEntry).filter(RosterEntry.id.in_(entry_ids))} if entry_ids else {}
    users = {u.id: u.name for u in db.query(User.id, User.name).filter(User.id.in_([m.user_id for m in members]))} \
        if members else {}
    out = {}
    for m in members:
        e = entries.get(m.roster_entry_id)
        out[m.user_id] = ((e.name if e else None) or users.get(m.user_id) or "Student", e.roll_no if e else None)
    return out


def _last_practice(report: dict) -> datetime.date | None:
    dates = [t["date"] for t in report["timeline"] if t["date"]]
    return datetime.datetime.fromisoformat(max(dates)).date() if dates else None


def risk_reasons(*, today: datetime.date, joined: datetime.date, last_active: datetime.date | None,
                 readiness: int | None, last_practice: datetime.date | None) -> list[str]:
    reasons = []
    since_active = last_active or joined
    if (today - since_active).days >= INACTIVE_DAYS:
        reasons.append("inactive_7d")
    if readiness is not None and readiness < LOW_READINESS:
        reasons.append("low_readiness")
    if (today - (last_practice or joined)).days >= NO_PRACTICE_DAYS:
        reasons.append("no_practice_21d")
    return reasons


def _rows(db: Session, members: list[CollegeMember], today: datetime.date) -> list[dict]:
    """One row per student: readiness, activity and risk (fixed query count)."""
    ids = [m.user_id for m in members]
    reports = readiness_bulk(db, ids)
    last = last_active_by_user(db, ids)
    active = active_dates_by_user(db, ids, today - datetime.timedelta(days=7 * TREND_WEEKS + today.weekday()))
    names = _names(db, members)
    rows = []
    for m in members:
        r = reports[m.user_id]
        joined = m.joined_at.date()
        last_practice = _last_practice(r)
        reasons = risk_reasons(today=today, joined=joined, last_active=last[m.user_id],
                               readiness=r["readiness"], last_practice=last_practice)
        days = active[m.user_id]
        rows.append({
            "member_id": m.id, "user_id": m.user_id, "batch_id": m.batch_id,
            "name": names[m.user_id][0], "roll_no": names[m.user_id][1], "verified": bool(m.verified),
            "joined_on": joined.isoformat(),
            "readiness": r["readiness"], "label": r["label"],
            "coverage": r["coverage"], "coverage_total": r["coverage_total"],
            "tests": r["by_type"]["theory"]["count"], "coding": r["by_type"]["coding"]["count"],
            "interviews": r["by_type"]["interview"]["count"],
            "last_active": last[m.user_id].isoformat() if last[m.user_id] else None,
            "days_inactive": (today - last[m.user_id]).days if last[m.user_id] else None,
            "last_practice": last_practice.isoformat() if last_practice else None,
            "active_7d": any((today - d).days < 7 for d in days),
            "active_30d": any((today - d).days < 30 for d in days),
            "active_dates": sorted(d.isoformat() for d in days),
            "skills": [{"skill": s["skill"], "score": s["score"]} for s in r["skills"] if s["questions"] >= 2],
            "risk": reasons,
        })
    return rows


def _risk_sort(row: dict) -> tuple:
    return (-len(row["risk"]), -(row["days_inactive"] if row["days_inactive"] is not None else 10 ** 6),
            row["name"].lower())


def _summary(rows: list[dict]) -> dict:
    scored = [r["readiness"] for r in rows if r["readiness"] is not None]
    buckets = {b: 0 for b in BUCKETS}
    for r in rows:
        buckets[r["label"]] = buckets.get(r["label"], 0) + 1
    return {
        "students": len(rows),
        "avg_readiness": round(sum(scored) / len(scored)) if scored else None,
        "coverage_pct": _pct(sum(r["coverage"] for r in rows), sum(r["coverage_total"] for r in rows)),
        "buckets": [{"label": b, "students": n} for b, n in buckets.items()],
        "active_7d_pct": _pct(sum(r["active_7d"] for r in rows), len(rows)),
        "active_30d_pct": _pct(sum(r["active_30d"] for r in rows), len(rows)),
        "at_risk": sum(1 for r in rows if r["risk"]),
    }


def _trend(rows: list[dict], today: datetime.date) -> list[dict]:
    """Share of students active in each of the last weeks (Mon-Sun), counting
    each student only from the week they joined."""
    start = today - datetime.timedelta(days=today.weekday() + 7 * (TREND_WEEKS - 1))
    out = []
    for w in range(TREND_WEEKS):
        week_start = start + datetime.timedelta(days=7 * w)
        week_end = week_start + datetime.timedelta(days=6)
        enrolled = [r for r in rows if r["joined_on"] <= week_end.isoformat()]
        active = sum(1 for r in enrolled
                     if any(week_start.isoformat() <= d <= week_end.isoformat() for d in r["active_dates"]))
        out.append({"week_of": week_start.isoformat(), "students": len(enrolled),
                    "active_pct": _pct(active, len(enrolled))})
    return out


def _weak_skills(rows: list[dict], limit: int = 5) -> list[dict]:
    agg: dict[str, list[int]] = {}
    for r in rows:
        for s in r["skills"]:
            agg.setdefault(s["skill"], []).append(s["score"])
    weak = [{"skill": k, "students_weak": sum(1 for v in vals if v < WEAK_SKILL), "students_tested": len(vals),
             "avg_score": round(sum(vals) / len(vals))} for k, vals in agg.items()]
    weak = [w for w in weak if w["students_weak"]]
    weak.sort(key=lambda w: (-w["students_weak"], w["avg_score"], w["skill"]))
    return weak[:limit]


def _public_row(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in ("active_dates", "skills")}


def _cache_key(scope: str, members: list[CollegeMember], today: datetime.date) -> str:
    # Membership changes (join/remove/batch move) change the key, so they show at once.
    ids = ",".join(sorted(f"{m.id}:{m.batch_id}" for m in members))
    return f"{scope}|{today.isoformat()}|{hashlib.sha1(ids.encode()).hexdigest()}"  # noqa: S324


def batch_dashboard(db: Session, college_id: str, batch_id: str, today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()
    if batch_id == UNASSIGNED:
        name = "Unassigned"
    else:
        b = db.query(Batch).filter(Batch.id == batch_id, Batch.college_id == college_id).first()
        if not b:
            raise LookupError("Batch not found.")
        name = b.name
    members = _members(db, college_id, batch_id)
    key = _cache_key(f"{college_id}:{batch_id}", members, today)
    hit = cache.cache_get("college_dashboard", key)
    if hit is not None:
        return hit
    rows = _rows(db, members, today)
    result = {
        "as_of": today.isoformat(), "batch": {"id": batch_id, "name": name},
        **_summary(rows),
        "trend": _trend(rows, today),
        "weak_skills": _weak_skills(rows),
        "at_risk_students": [
            {**_public_row(r), "reasons": [RISK_TEXT[x] for x in r["risk"]]}
            for r in sorted((r for r in rows if r["risk"]), key=_risk_sort)
        ],
        "students_list": [_public_row(r) for r in sorted(rows, key=lambda r: r["name"].lower())],
    }
    cache.cache_set("college_dashboard", key, result, CACHE_TTL)
    return result


def overview(db: Session, college_id: str, today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()
    members = _members(db, college_id)
    key = _cache_key(college_id, members, today)
    hit = cache.cache_get("college_overview", key)
    if hit is not None:
        return hit
    rows = _rows(db, members, today)
    batches = {b.id: b for b in db.query(Batch).filter(Batch.college_id == college_id)}
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["batch_id"] or UNASSIGNED, []).append(r)
    per_batch = []
    for bid, b in sorted(batches.items(), key=lambda kv: (kv[1].grad_year or 0, kv[1].name)):
        if b.archived_at and bid not in groups:
            continue
        per_batch.append({"id": bid, "name": b.name, "program": b.program, "grad_year": b.grad_year,
                          **_summary(groups.get(bid, []))})
    if UNASSIGNED in groups:
        per_batch.append({"id": UNASSIGNED, "name": "Unassigned", "program": "none", "grad_year": None,
                          **_summary(groups[UNASSIGNED])})
    result = {"as_of": today.isoformat(), **_summary(rows), "batches": per_batch,
              "weak_skills": _weak_skills(rows)}
    cache.cache_set("college_overview", key, result, CACHE_TTL)
    return result


def student_view(db: Session, college_id: str, user_id: str, today: datetime.date | None = None) -> dict:
    """One student, limited to what the college may see."""
    today = today or datetime.date.today()
    m = db.query(CollegeMember).filter(CollegeMember.college_id == college_id, CollegeMember.user_id == user_id,
                                       CollegeMember.status == "active").first()
    if not m:
        raise LookupError("Student not found.")
    sessions = db.query(SandboxSession).filter(SandboxSession.user_id == user_id).all()
    r = readiness_from(sessions, field_for_user(user_id, db=db))
    entry = db.get(RosterEntry, m.roster_entry_id) if m.roster_entry_id else None
    batch = db.get(Batch, m.batch_id) if m.batch_id else None
    row = _rows(db, [m], today)[0]
    by_id = {s.id: s for s in sessions}
    weeks = []
    for w in _trend([row], today):
        week_end = (datetime.date.fromisoformat(w["week_of"]) + datetime.timedelta(days=6)).isoformat()
        weeks.append({"week_of": w["week_of"],
                      "active_days": sum(1 for d in row["active_dates"] if w["week_of"] <= d <= week_end)})
    return {
        "as_of": today.isoformat(),
        "student": {"name": row["name"], "roll_no": row["roll_no"], "verified": row["verified"],
                    "joined_on": row["joined_on"], "batch": {"id": batch.id, "name": batch.name} if batch else None,
                    "cgpa": entry.cgpa if entry else None, "backlogs": entry.backlogs if entry else None},
        "readiness": {k: r[k] for k in ("readiness", "label", "coverage", "coverage_total", "applicable_types",
                                        "field_label", "by_type", "skills", "rubric")},
        "activity": {"last_active": row["last_active"], "days_inactive": row["days_inactive"],
                     "last_practice": row["last_practice"],
                     "active_days_30d": sum(1 for d in row["active_dates"]
                                            if (today - datetime.date.fromisoformat(d)).days < 30),
                     "weeks": weeks},
        "risk": [RISK_TEXT[x] for x in row["risk"]],
        "integrity": integrity.summary([s for s in sessions if s.status == "completed"]),
        "practice": [{**t, "notes": integrity.notes(by_id[t["id"]])["flags"]} for t in r["recent"]],
    }


# ── CSV exports ──────────────────────────────────────────────────────────────

def _cell(value) -> str:
    """Spreadsheet-safe text: never let a cell start a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for row in rows:
        w.writerow([_cell(v) for v in row])
    return buf.getvalue()


def export_csv(db: Session, college_id: str, kind: str, batch_id: str | None = None,
               today: datetime.date | None = None, assignment_id: str | None = None) -> str:
    today = today or datetime.date.today()
    if kind not in EXPORTS:
        raise LookupError("Unknown export.")
    if kind == "test_results":
        from app.services.college_assignments import results
        r = results(db, college_id, assignment_id or "")
        return _csv(["roll_no", "name", "test", "status", "score", "completed_at", "notes"],
                    [[s["roll_no"], s["name"], r["test"]["title"], s["status"], s["score"], s["completed_at"],
                      "; ".join(s["notes"])] for s in r["students"]])
    batches = {b.id: b for b in db.query(Batch).filter(Batch.college_id == college_id)}
    if batch_id and batch_id != UNASSIGNED and batch_id not in batches:
        raise LookupError("Batch not found.")

    def batch_name(bid):
        return batches[bid].name if bid in batches else "Unassigned"

    if kind == "batch_readiness":
        rows = sorted(_rows(db, _members(db, college_id, batch_id), today),
                      key=lambda r: (batch_name(r["batch_id"]), r["roll_no"] or "", r["name"].lower()))
        return _csv(["roll_no", "name", "batch", "readiness", "label", "coverage", "tests", "coding_problems",
                     "mock_interviews", "last_active", "days_inactive", "last_practice", "at_risk"],
                    [[r["roll_no"], r["name"], batch_name(r["batch_id"]), r["readiness"], r["label"],
                      f"{r['coverage']}/{r['coverage_total']}", r["tests"], r["coding"], r["interviews"],
                      r["last_active"], r["days_inactive"], r["last_practice"],
                      "; ".join(RISK_TEXT[x] for x in r["risk"])] for r in rows])

    # Roster rows plus students who joined without a roster row.
    q = db.query(RosterEntry).filter(RosterEntry.college_id == college_id)
    mq = db.query(CollegeMember).filter(CollegeMember.college_id == college_id)
    if batch_id == UNASSIGNED:
        q, mq = q.filter(RosterEntry.batch_id.is_(None)), mq.filter(CollegeMember.batch_id.is_(None))
    elif batch_id:
        q, mq = q.filter(RosterEntry.batch_id == batch_id), mq.filter(CollegeMember.batch_id == batch_id)
    entries = q.all()
    members = mq.all()
    by_entry = {m.roster_entry_id: m for m in members if m.roster_entry_id}
    loose = [m for m in members if not m.roster_entry_id]
    names = _names(db, loose)

    if kind == "roster_status":
        out = []
        for e in sorted(entries, key=lambda e: e.roll_no):
            m = by_entry.get(e.id)
            out.append([e.roll_no, e.name, e.email, batch_name(e.batch_id), e.cgpa, e.backlogs,
                         m.status if m else "not joined", "yes" if m and m.verified else "no",
                         m.joined_at.date().isoformat() if m else None])
        for m in loose:
            out.append([None, names[m.user_id][0], None, batch_name(m.batch_id), None, None, m.status, "no",
                        m.joined_at.date().isoformat()])
        return _csv(["roll_no", "name", "email", "batch", "cgpa", "backlogs", "status", "verified", "joined_on"], out)

    # outcomes_naac: one row per student for NAAC 5.2.1 / NIRF; the TPO fills in the outcome columns.
    active_ids = [m.user_id for m in members if m.status == "active"]
    reports = readiness_bulk(db, active_ids)
    out = []

    def outcome_row(roll, name, bid, m):
        b = batches.get(bid)
        r = reports.get(m.user_id) if m and m.status == "active" else None
        return [roll, name, b.course if b else None, b.branch if b else None, b.grad_year if b else None,
                r["readiness"] if r else None, r["label"] if r else None, None, None, None, None, None]

    for e in sorted(entries, key=lambda e: e.roll_no):
        out.append(outcome_row(e.roll_no, e.name, e.batch_id, by_entry.get(e.id)))
    for m in loose:
        if m.status == "active":
            out.append(outcome_row(None, names[m.user_id][0], m.batch_id, m))
    return _csv(["roll_no", "name", "course", "branch", "grad_year", "delta_readiness", "readiness_label",
                 "placed", "employer", "package_lpa", "higher_studies", "institution"], out)
