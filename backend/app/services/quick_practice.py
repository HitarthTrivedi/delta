"""Quick 5: the daily habit unit, a 5-question spaced review.

Evidence: spaced retrieval practice beats massed practice (g = 0.74), so the
daily streak is built on recall, not just ticking things off.

- Questions come from a shared bank per topic (generated once, reused by
  everyone: Master Plan "generate once, reuse many times"); bank questions are
  generated WITHOUT any learner's profile, so they hold no personal data.
- Topics: the learner's target role plus their two weakest skills.
- Leitner schedule: a right answer moves the question to the next box
  (back in 1 → 3 → 7 → 14 days); a wrong answer brings it back tomorrow.
- Grading is server-side; the answer key never reaches the browser first.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging

from sqlalchemy.orm import Session

from app.models.practice import PracticeItem, UserPracticeState
from app.models.skill_node import SkillNode
from app.services import engagement
from app.services.profile_store import load_profile
from app.services.theory_test_ai import generate_test

_log = logging.getLogger("delta.quick_practice")

SET_SIZE = 5
BOX_DAYS = {1: 1, 2: 3, 3: 7, 4: 14}
BANK_BATCH = 10           # questions generated per new topic
MIN_BANK_PER_TOPIC = 5


def _topic_key(topic: str) -> str:
    return " ".join(topic.lower().split())[:120]


def learner_topics(db: Session, user_id: str) -> list[str]:
    profile = load_profile(user_id) or {}
    topics = []
    role = (profile.get("target_role") or profile.get("goal_direction") or "").strip()
    if role:
        topics.append(role)
    weak = (db.query(SkillNode).filter(SkillNode.user_id == user_id)
            .order_by(SkillNode.proficiency.asc(), SkillNode.name.asc()).limit(2).all())
    topics += [s.name for s in weak if s.name]
    seen, out = set(), []
    for t in topics:
        k = _topic_key(t)
        if k and k not in seen:
            seen.add(k)
            out.append(t)
    return out or ["General aptitude and reasoning"]


def _ensure_bank(db: Session, topic: str) -> None:
    key = _topic_key(topic)
    if db.query(PracticeItem).filter(PracticeItem.topic_key == key).count() >= MIN_BANK_PER_TOPIC:
        return
    # personalize=False: shared bank questions never contain a learner's profile.
    _, questions = generate_test(None, topic, num_questions=BANK_BATCH, difficulty="easy", personalize=False)
    for q in questions:
        item_id = hashlib.sha1(f"{key}|{q['question']}".encode("utf-8")).hexdigest()[:32]
        if db.get(PracticeItem, item_id):
            continue
        db.add(PracticeItem(id=item_id, topic_key=key, question=q["question"], options=json.dumps(q["options"]),
                            answer_index=q["answer_index"], explanation=q.get("explanation") or "",
                            skill=q.get("skill") or topic))
    db.commit()


def _public(item: PracticeItem) -> dict:
    return {"id": item.id, "question": item.question, "options": json.loads(item.options), "skill": item.skill}


def todays_set(db: Session, user_id: str) -> dict:
    """Due reviews first (lowest box first), then new questions from the learner's topics."""
    eng = engagement.get_or_create(db, user_id)
    today = engagement.local_today(eng)
    answered_today = (db.query(UserPracticeState)
                      .filter(UserPracticeState.user_id == user_id, UserPracticeState.last_answered_date == today).count())

    topics = learner_topics(db, user_id)
    for topic in topics:
        try:
            _ensure_bank(db, topic)
        except ValueError as exc:
            _log.warning("could not fill practice bank for %r: %s", topic, exc)
    keys = [_topic_key(t) for t in topics]

    due = (db.query(PracticeItem).join(UserPracticeState, UserPracticeState.item_id == PracticeItem.id)
           .filter(UserPracticeState.user_id == user_id, UserPracticeState.due_date <= today,
                   (UserPracticeState.last_answered_date.is_(None)) | (UserPracticeState.last_answered_date < today))
           .order_by(UserPracticeState.box.asc(), UserPracticeState.due_date.asc()).limit(SET_SIZE).all())
    items = list(due)
    if len(items) < SET_SIZE and keys:
        seen_ids = {r.item_id for r in db.query(UserPracticeState.item_id).filter(UserPracticeState.user_id == user_id)}
        fresh = (db.query(PracticeItem).filter(PracticeItem.topic_key.in_(keys))
                 .order_by(PracticeItem.created_at.asc(), PracticeItem.id.asc()).all())
        # Round-robin across topics so one topic doesn't take the whole set.
        by_topic: dict[str, list[PracticeItem]] = {k: [] for k in keys}
        for it in fresh:
            if it.id not in seen_ids and it.id not in {i.id for i in items}:
                by_topic.setdefault(it.topic_key, []).append(it)
        while len(items) < SET_SIZE and any(by_topic.values()):
            for k in keys:
                if by_topic.get(k) and len(items) < SET_SIZE:
                    items.append(by_topic[k].pop(0))
    db.commit()
    if not items:
        raise ValueError("No practice questions are available right now. Please try again later.")
    return {
        "date": today.isoformat(),
        "answered_today": answered_today,
        "set_size": SET_SIZE,
        "items": [_public(i) for i in items],
    }


def answer(db: Session, user_id: str, item_id: str, choice: int) -> dict:
    item = db.get(PracticeItem, item_id)
    if item is None:
        raise LookupError("Unknown question.")
    eng = engagement.get_or_create(db, user_id)
    today = engagement.local_today(eng)
    correct = choice == item.answer_index

    state = db.get(UserPracticeState, (user_id, item_id))
    first_time_today = state is None or state.last_answered_date != today
    if state is None:
        state = UserPracticeState(user_id=user_id, item_id=item_id, box=1, due_date=today, times_seen=0)
        db.add(state)
    if first_time_today:
        state.box = min(4, state.box + 1) if correct else 1
        state.due_date = today + datetime.timedelta(days=BOX_DAYS[state.box] if correct else 1)
        state.last_correct = correct
        state.times_seen = (state.times_seen or 0) + 1
        state.last_answered_date = today
    db.commit()

    result = {"correct": correct, "answer_index": item.answer_index, "explanation": item.explanation or ""}
    rows = (db.query(UserPracticeState)
            .filter(UserPracticeState.user_id == user_id, UserPracticeState.last_answered_date == today).all())
    result["answered_today"] = len(rows)
    if first_time_today and len(rows) == SET_SIZE:
        right = sum(1 for r in rows if r.last_correct)
        perfect = right == SET_SIZE
        result["set_complete"] = {"correct": right, "total": SET_SIZE, "perfect": perfect}
        result["engagement"] = engagement.record_activity(
            db, user_id, "quick_review", today.isoformat(),
            bonus_xp=engagement.XP_TABLE["quick_review_perfect"] if perfect else 0)
    return result
