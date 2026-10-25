"""Daily-habit (gamification) state: streaks, XP and per-day activity.

XP and streaks reward the *habit* of learning. They never feed readiness or
sandbox scores, and recruiters never see XP, streaks or league standing (the
only exception is the separately consented "Consistent learner" yes/no badge).
Every per-learner table has `user_id`, so
privacy export and erasure cover it automatically. Children (Delta for
School) never get rows here (DPDP §9: no behavioural tracking of children).
"""
import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class UserEngagement(Base):
    __tablename__ = "user_engagement"
    __table_args__ = (UniqueConstraint("referral_code", name="uq_user_engagement_referral_code"),)

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

    # Weekly leagues (opt-in, consent recorded in consent_records).
    leagues_opt_in = Column(Boolean, nullable=False, default=False)
    league_tier = Column(Integer, nullable=False, default=0)  # index into leagues.TIERS

    # Personal invite code for referrals (created on first use).
    referral_code = Column(String, nullable=True)

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


class PushSubscription(Base):
    """A browser's Web Push endpoint for study reminders (one per device)."""
    __tablename__ = "push_subscriptions"

    endpoint = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
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


class UserBadge(Base):
    """An earned achievement badge; `tier` rises 1 -> 3 as the learner keeps going."""
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("share_token", name="uq_user_badges_share_token"),)

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    badge_key = Column(String, primary_key=True)
    tier = Column(Integer, nullable=False, default=1)
    earned_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)  # when this tier was reached
    # Public "verify this badge" link, only when the learner shares it (revocable).
    share_token = Column(String, nullable=True)


class LeagueCohort(Base):
    """A weekly league group of up to 20 opted-in learners at the same tier.
    `size` counts claimed places; places are claimed atomically."""
    __tablename__ = "league_cohorts"

    id = Column(String, primary_key=True)
    week_start = Column(Date, nullable=False, index=True)  # Monday
    field = Column(String, nullable=False)  # field pack id of the learner who opened it
    tier = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class LeagueMember(Base):
    """One learner's place in one week's league."""
    __tablename__ = "league_members"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    week_start = Column(Date, primary_key=True)
    cohort_id = Column(String, ForeignKey("league_cohorts.id"), nullable=False, index=True)
    tier = Column(Integer, nullable=False)
    outcome = Column(String, nullable=True)  # promoted | stayed | demoted, settled after the week


class StudyCircle(Base):
    """A private group of up to 6 learners who study "together" (opt-in)."""
    __tablename__ = "study_circles"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    invite_code = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CircleMember(Base):
    """A learner's place in a circle. `id` is the public handle other members
    see (never the user id)."""
    __tablename__ = "circle_members"
    __table_args__ = (UniqueConstraint("circle_id", "user_id", name="uq_circle_member"),)

    id = Column(String, primary_key=True)
    circle_id = Column(String, ForeignKey("study_circles.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False, default="member")  # owner | member
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class Referral(Base):
    """The invited learner (`user_id`) joined with `referrer_id`'s link. Both get
    a streak freeze once the invited learner has studied on 3 days."""
    __tablename__ = "referrals"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    referrer_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    rewarded_at = Column(DateTime, nullable=True)


class NudgeLog(Base):
    """One study reminder sent, which wording it used, and whether the learner
    studied later that day. Feeds the reminder-wording bandit and the metrics."""
    __tablename__ = "nudge_log"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    local_date = Column(Date, nullable=False)
    variant = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    returned = Column(Boolean, nullable=False, default=False)
