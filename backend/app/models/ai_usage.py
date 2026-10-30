"""AI usage: what the platform spends (no personal data) and what each learner
used this month (for caps).

- `ai_usage_daily`: calls and tokens per day, task and model, with an estimated
  cost. Aggregates only, so it says nothing about any one learner.
- `ai_budget_alerts`: which budget thresholds were already emailed this month.
- `ai_feature_uses`: per learner, per AI feature, per month. Has `user_id`, so
  the privacy export and erasure cover it.
"""
import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint

from app.database import Base


class AiUsageDaily(Base):
    __tablename__ = "ai_usage_daily"
    __table_args__ = (UniqueConstraint("day", "task", "model", name="uq_ai_usage_daily"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(Date, nullable=False, index=True)
    task = Column(String, nullable=False)
    model = Column(String, nullable=False)
    calls = Column(Integer, nullable=False, default=0)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    est_cost_usd = Column(Float, nullable=False, default=0.0)


class AiBudgetAlert(Base):
    __tablename__ = "ai_budget_alerts"
    __table_args__ = (UniqueConstraint("month", "threshold", name="uq_ai_budget_alert"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String, nullable=False)  # YYYY-MM
    threshold = Column(Integer, nullable=False)  # % of the budget
    spent_usd = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)


class AiFeatureUse(Base):
    __tablename__ = "ai_feature_uses"
    __table_args__ = (UniqueConstraint("user_id", "feature", "month", name="uq_ai_feature_use"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    feature = Column(String, nullable=False)
    month = Column(String, nullable=False)  # YYYY-MM
    count = Column(Integer, nullable=False, default=0)
