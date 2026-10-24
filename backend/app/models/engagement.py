"""Daily-habit (gamification) state: streaks, XP and per-day activity.

XP and streaks reward the *habit* of learning. They never feed readiness,
sandbox scores or anything recruiters see. Every table has `user_id`, so
privacy export and erasure cover it automatically. Children (Delta for
School) never get rows here (DPDP §9: no behavioural tracking of children).
"""
import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class UserEngagement(Base):
    __tablename__ = "user_engagement"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    timezone = Column(String, nullable=False, default="Asia/Kolkata")
    daily_goal_minutes = Column(Integer, nullable=False, default=10)  # 5 | 10 | 20
    study_time = Column(String, nullable=True)  # "HH:MM" local: the learner's own plan

    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    # Last local date the streak is alive through (active, frozen or on break).
    last_active_date = Column(Date, nullable=True)
    streak_freezes = Column(Integer, nullable=False, default=0)
    # Streak repair: a broken streak can be won back within a short window.
    repair_streak = Column(Integer, nullable=False, default=0)
    repair_deadline = Column(Date, nullable=True)
    repair_progress = Column(Integer, nullable=False, default=0)
    # Break mode (exams, travel): pauses the streak, limited per month.
    break_until = Column(Date, nullable=True)
    break_month = Column(String, nullable=True)  # "YYYY-MM"
    break_days_used = Column(Integer, nullable=False, default=0)

    xp_total = Column(Integer, nullable=False, default=0)

    # Reminders (opt-in, consent recorded in consent_records).
    reminders_opt_in = Column(Boolean, nullable=False, default=False)
    reminder_channel = Column(String, nullable=False, default="email")  # email | push | both
    last_nudged_on = Column(Date, nullable=True)
    ignored_nudges = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class XpEvent(Base):
    """One XP award. (user_id, source_type, source_id) is unique, so the same
    task, test or session can never be rewarded twice."""
    __tablename__ = "xp_events"
    __table_args__ = (UniqueConstraint("user_id", "source_type", "source_id", name="uq_xp_source"),)

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    repeat_key = Column(String, nullable=True)  # e.g. a test topic: repeats the same day earn 0
    xp = Column(Integer, nullable=False, default=0)
    local_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class DailyActivity(Base):
    """One row per learner per local day they were active (or protected)."""
    __tablename__ = "daily_activity"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    local_date = Column(Date, primary_key=True)
    xp = Column(Integer, nullable=False, default=0)
    actions = Column(Integer, nullable=False, default=0)
    goal_met = Column(Boolean, nullable=False, default=False)
    freeze_used = Column(Boolean, nullable=False, default=False)
    on_break = Column(Boolean, nullable=False, default=False)
