"""Interview readiness: one report combining the technical/aptitude tests,
the coding sandbox and the AI mock interview.

Used by the student's Test Center and by the recruiter's candidate view, so
both always see the same numbers. Everything here is derived from graded
sessions; nothing is estimated or invented. A test type the student hasn't
taken is reported as missing (lower coverage), not as zero.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.sandbox_session import SandboxSession
from app.services.domain_packs import field_for_user

WEIGHTS = {"theory": 0.35, "coding": 0.35, "interview": 0.30}
# Fields where coding isn't part of the job: readiness is tests + interview only.
NON_CODING_WEIGHTS = {"theory": 0.55, "interview": 0.45}
TYPE_LABELS = {"theory": "Knowledge & aptitude tests", "coding": "Coding", "interview": "AI interview"}
RUBRIC_LABELS = {
    "communication": "Communication", "technical_depth": "Technical depth",
    "problem_solving": "Problem solving", "clarity": "Clarity",
}
# Which interview type best trains each rubric area.
RUBRIC_PRACTICE = {"communication": "behavioral", "clarity": "behavioral", "technical_depth": "technical", "problem_solving": "technical"}
RECENT_WINDOW = 5  # averages use the latest attempts, so improvement shows


def _data(s: SandboxSession) -> dict:
    try:
        return json.loads(s.data or "{}")
    except ValueError:
        return {}


def _session_score(s: SandboxSession, data: dict) -> int | None:
    """Graded score for a session, or None if it hasn't been graded."""
    if s.type == "coding":
        if s.status == "completed":
            return 100
        return data.get("best_pass_pct") if data.get("submissions") else None
    return s.score if s.status == "completed" else None


def _label(score: int | None) -> str:
    if score is None:
        return "Not started"
    if score >= 80:
        return "Interview-ready"
    if score >= 65:
        return "Almost there"
    if score >= 45:
        return "Building up"
    return "Just starting"


def compute_readiness(db: Session, user_id: str) -> dict:
    pack = field_for_user(user_id, db=db)
    sessions = db.query(SandboxSession).filter(SandboxSession.user_id == user_id).all()
    graded = []
    for s in sessions:
        data = _data(s)
        score = _session_score(s, data)
        if score is not None:
            graded.append((s, data, score))
    graded.sort(key=lambda t: (t[0].completed_at or t[0].created_at))

    # Per type
    by_type: dict[str, dict] = {}
    for t in WEIGHTS:
        rows = [(s, d, sc) for s, d, sc in graded if s.type == t]
        scores = [sc for _, _, sc in rows]
        recent = scores[-RECENT_WINDOW:]
        by_type[t] = {
            "label": TYPE_LABELS[t],
            "count": len(scores),
            "average": round(sum(recent) / len(recent)) if recent else None,
            "best": max(scores) if scores else None,
            "latest": scores[-1] if scores else None,
        }

    # Coding counts only for tech fields, or if the student chose to do it anyway.
    weights = WEIGHTS if (pack["is_tech"] or by_type["coding"]["count"] > 0) else NON_CODING_WEIGHTS
    taken = {t: v for t, v in by_type.items() if v["average"] is not None and t in weights}
    readiness = None
    if taken:
        total_w = sum(weights[t] for t in taken)
        readiness = round(sum(weights[t] * v["average"] for t, v in taken.items()) / total_w)

    # Per skill: technical-test accuracy + coding topics
    skill_acc: dict[str, dict] = {}
    for s, d, sc in graded:
        if s.type == "theory":
            for skill, st in ((d.get("result") or {}).get("skill_breakdown") or {}).items():
                agg = skill_acc.setdefault(skill, {"correct": 0, "total": 0, "coding": []})
                agg["correct"] += st.get("correct", 0)
                agg["total"] += st.get("total", 0)
        elif s.type == "coding" and d.get("topic"):
            skill_acc.setdefault(d["topic"], {"correct": 0, "total": 0, "coding": []})["coding"].append(sc)
    skills = []
    for name, agg in skill_acc.items():
        parts = []
        if agg["total"]:
            parts.append(100 * agg["correct"] / agg["total"])
        if agg["coding"]:
            parts.append(sum(agg["coding"]) / len(agg["coding"]))
        evidence = agg["total"] + len(agg["coding"])
        skills.append({"skill": name, "score": round(sum(parts) / len(parts)), "evidence": evidence,
                       "questions": agg["total"], "coding_problems": len(agg["coding"])})
    skills.sort(key=lambda x: (-x["score"], -x["evidence"]))

    # Interview rubric averages
    rubric_sums: dict[str, list[int]] = {}
    for s, d, _ in graded:
        if s.type == "interview":
            for key, item in ((d.get("feedback") or {}).get("rubric") or {}).items():
                if key in RUBRIC_LABELS and isinstance(item, dict):
                    rubric_sums.setdefault(key, []).append(int(item.get("score") or 0))
    rubric = [
        {"key": k, "label": RUBRIC_LABELS[k], "score": round(sum(v) / len(v), 1)}
        for k, v in rubric_sums.items()
    ]

    # Next steps
    steps: list[dict] = []
    for t, label, link in (("theory", "Take a knowledge or aptitude test", "/practice/theory"),
                           ("interview", "Do an AI mock interview", "/practice/interview"),
                           ("coding", "Solve a coding problem", "/practice/coding")):
        if t in weights and by_type[t]["count"] == 0:
            steps.append({"title": label, "reason": "You haven't tried this yet, so part of your readiness picture is missing.", "link": link})
    weak = [x for x in skills if x["questions"] >= 2 and x["score"] < 70]
    if weak:
        w = min(weak, key=lambda x: x["score"])
        steps.append({"title": f"Strengthen {w['skill']}", "reason": f"Your weakest skill so far at {w['score']}%.",
                      "link": f"/practice/theory?topic={w['skill']}"})
    if rubric:
        low = min(rubric, key=lambda x: x["score"])
        if low["score"] < 7:
            steps.append({"title": f"Work on {low['label'].lower()}", "reason": f"Your lowest interview area ({low['score']}/10).",
                          "link": f"/practice/interview?type={RUBRIC_PRACTICE[low['key']]}"})
    if "coding" in weights and by_type["coding"]["average"] is not None and by_type["coding"]["average"] < 70:
        steps.append({"title": "More coding practice", "reason": f"Your recent coding average is {by_type['coding']['average']}%.", "link": "/practice/coding"})

    # Timeline + recent list
    timeline = [
        {"id": s.id, "type": s.type, "title": s.title, "score": sc,
         "date": (s.completed_at or s.created_at).isoformat() if (s.completed_at or s.created_at) else None}
        for s, _, sc in graded
    ]

    return {
        "readiness": readiness,
        "label": _label(readiness),
        "coverage": len(taken),
        "coverage_total": len(weights),
        "weights": weights,
        "applicable_types": list(weights),
        "field": pack["id"],
        "field_label": pack["label"],
        "by_type": by_type,
        "skills": skills,
        "rubric": rubric,
        "next_steps": steps[:3],
        "timeline": timeline,
        "recent": list(reversed(timeline))[:8],
    }
