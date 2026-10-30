"""Verified readiness re-check (Master Plan backlog #9).

A student re-checks their readiness score under strict conditions:
- 12 questions from a shared verified bank (made once per topic with no
  learner data, never practised in advance, never repeated for a learner),
  with a hard time limit on the server;
- for tech fields, one coding problem: 25 minutes, at most 3 submits, and
  submits report only how many tests passed.
The re-check score uses the same readiness weights over the parts taken. It
is "verified" when it's within VERIFY_TOLERANCE of the student's practice
score on those parts, with no serious integrity flags. Recruiters see only
passes; a miss stays private and can be retried after VERIFY_RETRY_DAYS.

This is a strict, timed re-check with fresh questions, not camera proctoring.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import random
import re
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.compliance import Recruiter
from app.models.sandbox_session import SandboxSession
from app.models.user import User
from app.models.verification import ReadinessCheck, VerificationRequest, VerifiedItem, VerifiedSeen
from app.services import compliance, integrity
from app.services.integrity import IntegrityPayload

QUESTIONS_PER_TOPIC = 4
TOPICS = 3
SECONDS_PER_QUESTION = 60
CODING_SECONDS = 25 * 60
GRACE_SECONDS = 15
MAX_SUBMITS = 3
BANK_BATCH = 12
FALLBACK_TOPIC = "General aptitude and reasoning"


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _topic_key(topic: str) -> str:
    return re.sub(r"\s+", " ", str(topic or "").strip().lower())[:120]


def _iso(dt: datetime.datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse(dt: str | None) -> datetime.datetime | None:
    return datetime.datetime.fromisoformat(dt) if dt else None


# ── which topics and which problem ──────────────────────────────────────────

def _topics(report: dict, pack: dict) -> list[str]:
    """The student's two strongest tested skills plus core skills of their field."""
    chosen: list[str] = []
    for s in report["skills"]:
        if s["questions"] >= 2 and _topic_key(s["skill"]) not in {_topic_key(c) for c in chosen}:
            chosen.append(s["skill"])
        if len(chosen) == 2:
            break
    for skill in pack.get("skill_taxonomy") or []:
        if len(chosen) >= TOPICS:
            break
        if _topic_key(skill) not in {_topic_key(c) for c in chosen}:
            chosen.append(skill)
    while len(chosen) < TOPICS:
        chosen.append(FALLBACK_TOPIC if FALLBACK_TOPIC not in chosen else f"{FALLBACK_TOPIC} {len(chosen)}")
    return chosen[:TOPICS]


def _unseen(db: Session, user_id: str, topic: str) -> list[VerifiedItem]:
    seen = db.query(VerifiedSeen.item_id).filter(VerifiedSeen.user_id == user_id)
    return (db.query(VerifiedItem)
            .filter(VerifiedItem.topic_key == _topic_key(topic), ~VerifiedItem.id.in_(seen)).all())


def _pick_problem(db: Session, user_id: str, coding_average: float | None) -> dict:
    """A catalog problem at the student's level they haven't done, preferring
    ones whose package is already stored (no model call)."""
    from app.models.verification import CodingPackage
    from app.services.central_engine import LEETCODE_PROBLEMS
    level = "Medium" if (coding_average or 0) >= 70 else "Easy"
    done = {s.title for s in db.query(SandboxSession.title).filter(SandboxSession.user_id == user_id,
                                                                    SandboxSession.type == "coding")}
    candidates = [{"topic": topic, **p} for topic, problems in LEETCODE_PROBLEMS.items() for p in problems
                  if p["difficulty"] == level and p["title"] not in done]
    if not candidates:
        candidates = [{"topic": topic, **p} for topic, problems in LEETCODE_PROBLEMS.items() for p in problems
                      if p["difficulty"] == level]
    stored = {r[0] for r in db.query(CodingPackage.problem_key)}
    ready = [c for c in candidates if f"{c['topic']}::{c['title']}" in stored]
    return random.choice(ready or candidates)


# ── the shared bank (filled by a background job) ─────────────────────────────

def fill(db: Session, payload: dict) -> None:
    """Background job `verified_bank`: add questions for the topics that ran
    low, and make sure the chosen coding problem's package is stored."""
    from app.services.sandbox_problems import generate_problem_package
    from app.services.theory_test_ai import generate_test
    for topic in payload.get("topics") or []:
        try:
            _, questions = generate_test(None, topic, BANK_BATCH, "medium", personalize=False)
        except ValueError as exc:
            raise ValueError("We couldn't prepare your re-check questions. Please try again.") from exc
        key = _topic_key(topic)
        for q in questions:
            item_id = hashlib.sha1(f"{key}|{q['question']}".encode()).hexdigest()[:32]
            if db.get(VerifiedItem, item_id):
                continue
            db.add(VerifiedItem(id=item_id, topic_key=key, difficulty="medium", question=q["question"],
                                options=json.dumps(q["options"]), answer_index=q["answer_index"],
                                explanation=q.get("explanation"), skill=q.get("skill") or topic))
        db.commit()
    problem = payload.get("problem")
    if problem:
        package = generate_problem_package(problem["topic"], problem["title"], problem["difficulty"])
        if package.get("fallback"):
            raise ValueError("We couldn't prepare your coding problem. Please try again.")


# ── state ───────────────────────────────────────────────────────────────────

def _check(db: Session, user_id: str, check_id: str) -> ReadinessCheck:
    c = db.query(ReadinessCheck).filter(ReadinessCheck.id == check_id, ReadinessCheck.user_id == user_id).first()
    if not c:
        raise LookupError("Re-check not found.")
    return c


def _parts(c: ReadinessCheck) -> dict:
    return json.loads(c.parts or "{}")


def _last_deadline(c: ReadinessCheck) -> datetime.datetime:
    parts = _parts(c)
    return max(_parse(p["deadline"]) for p in parts.values())


def _settle(db: Session, c: ReadinessCheck) -> ReadinessCheck:
    """Resolve a re-check whose time has run out (e.g. the student left)."""
    if c.status == "in_progress" and _now() > _last_deadline(c) + datetime.timedelta(seconds=GRACE_SECONDS):
        finish(db, c)
    return c


def _current(db: Session, user_id: str) -> ReadinessCheck | None:
    c = (db.query(ReadinessCheck).filter(ReadinessCheck.user_id == user_id, ReadinessCheck.status == "in_progress")
         .order_by(ReadinessCheck.started_at.desc()).first())
    if c:
        _settle(db, c)
    return c if c and c.status == "in_progress" else None


def _latest_done(db: Session, user_id: str) -> ReadinessCheck | None:
    return (db.query(ReadinessCheck).filter(ReadinessCheck.user_id == user_id,
                                            ReadinessCheck.status.in_(("verified", "not_verified")))
            .order_by(ReadinessCheck.completed_at.desc()).first())


def _valid_pass(db: Session, user_id: str) -> ReadinessCheck | None:
    """The latest finished re-check, if it passed and is in date: a later miss replaces an earlier pass."""
    last = _latest_done(db, user_id)
    return last if last and last.status == "verified" and last.valid_until > _now() else None


def _retry_on(db: Session, user_id: str) -> datetime.datetime | None:
    last = _latest_done(db, user_id)
    if last and last.status == "not_verified":
        when = last.completed_at + datetime.timedelta(days=settings.VERIFY_RETRY_DAYS)
        return when if when > _now() else None
    return None


def _baseline_parts(report: dict) -> dict[str, float]:
    """Practice averages for the parts a re-check covers (theory, and coding when it counts)."""
    parts = {"theory": report["by_type"]["theory"]["average"]}
    if "coding" in report["weights"] and report["by_type"]["coding"]["average"] is not None:
        parts["coding"] = report["by_type"]["coding"]["average"]
    return parts


def _weighted(report_weights: dict, scores: dict[str, float]) -> float:
    total = sum(report_weights[t] for t in scores)
    return sum(report_weights[t] * scores[t] for t in scores) / total


def check_dict(db: Session, c: ReadinessCheck, with_questions: bool = False) -> dict:
    parts = _parts(c)
    out = {"id": c.id, "status": c.status, "started_at": _iso(c.started_at), "completed_at": _iso(c.completed_at),
           "valid_until": _iso(c.valid_until), "baseline": round(c.baseline) if c.baseline is not None else None,
           "score": round(c.check_score) if c.check_score is not None else None,
           "flags": json.loads(c.flags or "[]"), "parts": {}}
    for name, p in parts.items():
        s = db.get(SandboxSession, p["session_id"])
        data = json.loads(s.data or "{}") if s else {}
        part = {"deadline": p["deadline"], "done": bool(p.get("done"))}
        if name == "theory" and with_questions and c.status == "in_progress" and not p.get("done"):
            part["questions"] = [{"question": q["question"], "options": q["options"], "skill": q["skill"]}
                                 for q in data.get("questions") or []]
        if name == "coding":
            part.update({"title": s.title.replace("Verified re-check: ", "") if s else None,
                         "submits_left": MAX_SUBMITS - int(data.get("submissions") or 0)})
            if with_questions and c.status == "in_progress":
                part.update({"statement": data.get("statement"), "examples": data.get("examples"),
                             "starter_code": data.get("starter_code")})
        out["parts"][name] = part
    return out


def status(db: Session, user_id: str) -> dict:
    from app.services.readiness import compute_readiness
    current = _current(db, user_id)
    passed = _valid_pass(db, user_id)
    retry = _retry_on(db, user_id)
    user = db.get(User, user_id)
    reason = None
    if compliance.is_minor(user):
        reason = "minor"
    elif compute_readiness(db, user_id)["by_type"]["theory"]["average"] is None:
        reason = "no_tests"
    elif retry:
        reason = "cooldown"
    return {
        "current": check_dict(db, current, with_questions=True) if current else None,
        "verified": ({"score": round(passed.check_score), "on": _iso(passed.completed_at),
                      "valid_until": _iso(passed.valid_until)} if passed else None),
        "last": check_dict(db, _latest_done(db, user_id)) if _latest_done(db, user_id) else None,
        "retry_on": _iso(retry), "can_start": reason is None, "reason": reason,
        "requests": open_requests(db, user_id),
        "rules": {"questions": QUESTIONS_PER_TOPIC * TOPICS, "seconds_per_question": SECONDS_PER_QUESTION,
                  "coding_minutes": CODING_SECONDS // 60, "max_submits": MAX_SUBMITS,
                  "tolerance": settings.VERIFY_TOLERANCE, "max_tab_switches": settings.VERIFY_MAX_TAB_SWITCHES,
                  "valid_days": settings.VERIFY_VALID_DAYS, "retry_days": settings.VERIFY_RETRY_DAYS},
    }


# ── starting ────────────────────────────────────────────────────────────────

def start(db: Session, user_id: str) -> dict:
    """Begin (or resume) a re-check. Returns {"check": …}, or {"preparing": job}
    while the shared bank is being filled in the background."""
    from app.services import jobs, usage_caps
    from app.services.domain_packs import field_for_user
    from app.services.readiness import compute_readiness
    from app.services.sandbox_problems import generate_problem_package
    user = db.get(User, user_id)
    if not user:
        raise LookupError("User not found.")
    if compliance.is_minor(user):
        raise PermissionError("Verified re-checks open when you turn 18.")
    current = _current(db, user_id)
    if current:
        return {"check": check_dict(db, current, with_questions=True)}
    retry = _retry_on(db, user_id)
    if retry:
        raise ValueError(f"You can try again on {retry.strftime('%d %b')}.")
    usage_caps.ensure_room(db, user_id, "readiness_check")  # before preparing anything
    report = compute_readiness(db, user_id)
    if report["by_type"]["theory"]["average"] is None:
        raise ValueError("Take at least one practice test first: there is no score to verify yet.")
    baseline_parts = _baseline_parts(report)
    topics = _topics(report, field_for_user(user_id, db=db))
    low = [t for t in topics if len(_unseen(db, user_id, t)) < QUESTIONS_PER_TOPIC]
    problem = None
    package = None
    if "coding" in baseline_parts:
        problem = _pick_problem(db, user_id, baseline_parts["coding"])
        from app.models.verification import CodingPackage
        stored = db.get(CodingPackage, f"{problem['topic']}::{problem['title']}")
        if stored:
            package = generate_problem_package(problem["topic"], problem["title"], problem["difficulty"])
    if low or (problem and package is None):
        payload = {"topics": low, "problem": ({k: problem[k] for k in ("topic", "title", "difficulty")}
                                              if problem and package is None else None)}
        return {"preparing": jobs.job_dict(jobs.enqueue(db, user_id, "verified_bank", payload))}

    with usage_caps.using(db, user_id, "readiness_check"):
        now = _now()
        questions = []
        for topic in topics:
            for item in random.sample(_unseen(db, user_id, topic), QUESTIONS_PER_TOPIC):
                questions.append({"question": item.question, "options": json.loads(item.options),
                                  "answer_index": item.answer_index, "skill": item.skill or topic,
                                  "item_id": item.id})
                db.add(VerifiedSeen(user_id=user_id, item_id=item.id, seen_at=now))
        theory_limit = len(questions) * SECONDS_PER_QUESTION
        c = ReadinessCheck(id=str(uuid.uuid4()), user_id=user_id, status="in_progress", started_at=now,
                           baseline=_weighted(report["weights"], baseline_parts), request_id=None)
        theory = SandboxSession(
            id=str(uuid.uuid4()), user_id=user_id, type="theory", title="Verified re-check: questions",
            status="in_progress", created_at=now,
            data=json.dumps({"topic": "Verified re-check", "category": "technical", "difficulty": "medium",
                             "questions": questions, "time_limit_seconds": theory_limit,
                             "started_at": now.isoformat(), "verified_check_id": c.id}))
        db.add(theory)
        parts = {"theory": {"session_id": theory.id,
                            "deadline": (now + datetime.timedelta(seconds=theory_limit)).isoformat()}}
        if problem:
            coding = SandboxSession(
                id=str(uuid.uuid4()), user_id=user_id, type="coding", title=f"Verified re-check: {problem['title']}",
                status="in_progress", created_at=now,
                data=json.dumps({"topic": problem["topic"], "difficulty": problem["difficulty"],
                                 "statement": package["statement"], "examples": package["examples"],
                                 "starter_code": package["starter_code"], "test_cases": package["test_cases"],
                                 "started_at": now.isoformat(), "verified_check_id": c.id}))
            db.add(coding)
            parts["coding"] = {"session_id": coding.id, "deadline": (
                now + datetime.timedelta(seconds=theory_limit + CODING_SECONDS)).isoformat()}
        c.parts = json.dumps(parts)
        db.add(c)
        db.commit()
    return {"check": check_dict(db, c, with_questions=True)}


# ── answering ───────────────────────────────────────────────────────────────

def _open_part(db: Session, user_id: str, check_id: str, name: str) -> tuple[ReadinessCheck, dict, SandboxSession]:
    c = _check(db, user_id, check_id)
    if c.status != "in_progress":
        raise ValueError("This re-check is finished.")
    parts = _parts(c)
    if name not in parts:
        raise LookupError("This re-check has no such part.")
    if parts[name].get("done"):
        raise ValueError("You've already finished this part.")
    return c, parts, db.get(SandboxSession, parts[name]["session_id"])


def _late(parts: dict, name: str) -> bool:
    return _now() > _parse(parts[name]["deadline"]) + datetime.timedelta(seconds=GRACE_SECONDS)


def submit_theory(db: Session, user_id: str, check_id: str, answers: list, report: IntegrityPayload | None) -> dict:
    c, parts, s = _open_part(db, user_id, check_id, "theory")
    data = json.loads(s.data)
    questions = data["questions"]
    if len(answers) != len(questions):
        raise ValueError(f"Expected {len(questions)} answers.")
    late = _late(parts, "theory")
    if late:
        answers = [None] * len(questions)  # after the time limit, answers don't count
    breakdown: dict[str, dict] = {}
    correct = 0
    for q, chosen in zip(questions, answers):
        ok = chosen == q["answer_index"]
        correct += ok
        stats = breakdown.setdefault(q["skill"], {"correct": 0, "total": 0})
        stats["total"] += 1
        stats["correct"] += ok
    score = round(100 * correct / len(questions))
    taken = int((_now() - _parse(data["started_at"])).total_seconds())
    data["answers"] = answers
    data["result"] = {"score": score, "correct": correct, "total": len(questions), "skill_breakdown": breakdown,
                      "time_taken_seconds": taken, "time_limit_seconds": data["time_limit_seconds"],
                      "overtime": late}
    integrity.record(data, report)
    s.data, s.status, s.score, s.completed_at = json.dumps(data), "completed", score, _now()
    parts["theory"]["done"] = True
    c.parts = json.dumps(parts)
    db.commit()
    if all(p.get("done") for p in parts.values()):
        finish(db, c)
    return check_dict(db, c, with_questions=True)


def run_code(db: Session, user_id: str, check_id: str, language: str, code: str, stdin: str) -> dict:
    from app.services.code_runner import run_code as runner
    _, parts, _ = _open_part(db, user_id, check_id, "coding")
    if _late(parts, "coding"):
        raise ValueError("Time is up for the coding part.")
    return runner(language, code, stdin or "")


def submit_coding(db: Session, user_id: str, check_id: str, language: str, code: str,
                  report: IntegrityPayload | None) -> dict:
    """Grade against the hidden tests. Only the pass count comes back."""
    from app.services.code_runner import outputs_match, run_code as runner
    c, parts, s = _open_part(db, user_id, check_id, "coding")
    if _late(parts, "coding"):
        raise ValueError("Time is up for the coding part.")
    data = json.loads(s.data)
    if int(data.get("submissions") or 0) >= MAX_SUBMITS:
        raise ValueError("You've used all your submits.")
    cases = data["test_cases"]
    passed = 0
    for case in cases:
        run = runner(language, code, case.get("input", ""))
        if run.get("error"):
            raise RuntimeError(run["error"])
        passed += outputs_match(run.get("stdout", ""), case.get("expected_output", ""))
    data["submissions"] = int(data.get("submissions") or 0) + 1
    data["best_pass_pct"] = max(int(data.get("best_pass_pct") or 0), round(100 * passed / len(cases)))
    integrity.record(data, report)
    s.data = json.dumps(data)
    if passed == len(cases):
        s.status, s.score, s.completed_at = "completed", 100, _now()
    if passed == len(cases) or data["submissions"] >= MAX_SUBMITS:
        parts["coding"]["done"] = True
        c.parts = json.dumps(parts)
    db.commit()
    if all(p.get("done") for p in parts.values()):
        finish(db, c)
    return {"passed": passed, "total": len(cases), "submits_left": MAX_SUBMITS - data["submissions"],
            "check": check_dict(db, c, with_questions=True)}


# ── the result ──────────────────────────────────────────────────────────────

def _serious_flags(session: SandboxSession | None) -> list[str]:
    if not session:
        return []
    data = json.loads(session.data or "{}")
    seen = data.get("integrity") or {}
    flags = []
    if int(seen.get("tab_switches") or 0) > settings.VERIFY_MAX_TAB_SWITCHES:
        flags.append(f"Left the tab {seen['tab_switches']} times")
    if int(seen.get("pasted_chars") or 0) >= integrity.PASTE_NOTE_CHARS:
        flags.append("Pasted text into answers")
    if (data.get("result") or {}).get("overtime"):
        flags.append("Went past the time limit")
    return flags


def finish(db: Session, c: ReadinessCheck) -> ReadinessCheck:
    """Score the re-check and decide whether it verifies the practice score."""
    from app.services.readiness import WEIGHTS
    if c.status != "in_progress":
        return c
    parts = _parts(c)
    scores: dict[str, float] = {}
    flags: list[str] = []
    theory = db.get(SandboxSession, parts["theory"]["session_id"])
    scores["theory"] = float(theory.score or 0) if theory and theory.status == "completed" else 0.0
    flags += _serious_flags(theory)
    if "coding" in parts:
        coding = db.get(SandboxSession, parts["coding"]["session_id"])
        data = json.loads(coding.data or "{}") if coding else {}
        scores["coding"] = 100.0 if coding and coding.status == "completed" else float(data.get("best_pass_pct") or 0)
        flags += _serious_flags(coding)
    c.check_score = _weighted(WEIGHTS, scores)
    c.flags = json.dumps(flags)
    verified = not flags and c.baseline is not None and c.check_score >= c.baseline - settings.VERIFY_TOLERANCE
    c.status = "verified" if verified else "not_verified"
    c.completed_at = _now()
    c.valid_until = c.completed_at + datetime.timedelta(days=settings.VERIFY_VALID_DAYS) if verified else None
    for name in parts:
        parts[name]["done"] = True
    c.parts = json.dumps(parts)
    # Any open recruiter requests are answered by this re-check, whatever the result.
    for r in db.query(VerificationRequest).filter(VerificationRequest.user_id == c.user_id,
                                                  VerificationRequest.status == "open"):
        r.status, r.completed_at = "done", c.completed_at
    db.commit()
    return c


def finish_now(db: Session, user_id: str, check_id: str) -> dict:
    c = _check(db, user_id, check_id)
    finish(db, c)
    return check_dict(db, c)


# ── what recruiters see, and their requests ─────────────────────────────────

def recruiter_view(db: Session, user_id: str) -> dict:
    """Passes only: a miss or an expired pass reads as not verified."""
    passed = _valid_pass(db, user_id)
    if not passed:
        return {"verified": False}
    return {"verified": True, "score": round(passed.check_score), "on": _iso(passed.completed_at),
            "valid_until": _iso(passed.valid_until)}


def verified_ids(db: Session, user_ids) -> set[str]:
    ids = list(user_ids)
    if not ids:
        return set()
    latest = {}  # user -> their latest finished check, as in _valid_pass
    for c in (db.query(ReadinessCheck).filter(ReadinessCheck.user_id.in_(ids),
                                              ReadinessCheck.status.in_(("verified", "not_verified")))
              .order_by(ReadinessCheck.completed_at)):
        latest[c.user_id] = c
    now = _now()
    return {uid for uid, c in latest.items() if c.status == "verified" and c.valid_until > now}


def request(db: Session, recruiter: Recruiter, user_id: str) -> dict:
    if not compliance.can_recruiter_see(db, recruiter, user_id):
        raise LookupError("Candidate not found.")
    open_one = db.query(VerificationRequest).filter(VerificationRequest.recruiter_id == recruiter.id,
                                                    VerificationRequest.user_id == user_id,
                                                    VerificationRequest.status == "open").first()
    if not open_one:
        open_one = VerificationRequest(id=str(uuid.uuid4()), recruiter_id=recruiter.id, user_id=user_id)
        db.add(open_one)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        try:  # a nudge if the student turned on push; the Today card shows it either way
            from app.services import push_service
            push_service.send_to_user(db, user_id, "A recruiter asked you to verify",
                                      f"{recruiter.company} would like you to verify your readiness score.",
                                      f"{settings.FRONTEND_URL.rstrip('/')}/practice/verify")
        except Exception:  # noqa: BLE001
            pass
    return request_status(db, recruiter, user_id)


def request_status(db: Session, recruiter: Recruiter, user_id: str) -> dict | None:
    r = (db.query(VerificationRequest).filter(VerificationRequest.recruiter_id == recruiter.id,
                                              VerificationRequest.user_id == user_id)
         .order_by(VerificationRequest.created_at.desc()).first())
    return {"status": r.status, "requested_at": _iso(r.created_at), "completed_at": _iso(r.completed_at)} if r else None


def open_requests(db: Session, user_id: str) -> list[dict]:
    rows = (db.query(VerificationRequest, Recruiter).join(Recruiter, Recruiter.id == VerificationRequest.recruiter_id)
            .filter(VerificationRequest.user_id == user_id, VerificationRequest.status == "open")
            .order_by(VerificationRequest.created_at.desc()).all())
    return [{"id": r.id, "company": rec.company, "requested_at": _iso(r.created_at)} for r, rec in rows]


def decline(db: Session, user_id: str, request_id: str) -> None:
    r = db.query(VerificationRequest).filter(VerificationRequest.id == request_id,
                                             VerificationRequest.user_id == user_id).first()
    if not r:
        raise LookupError("Request not found.")
    if r.status == "open":
        r.status, r.completed_at = "declined", _now()
        db.commit()
