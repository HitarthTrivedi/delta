import json
from sqlalchemy import Column, String, Float, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class WeeklyBrief(Base):
    __tablename__ = "weekly_briefs"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, default=datetime.date.today)
    delta_score_start = Column(Float, default=0.0)
    delta_score_end = Column(Float, nullable=True)
    recommendations = Column(Text, nullable=True)  # JSON string
    email_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    recommendation_items = relationship("Recommendation", back_populates="brief", lazy="selectin")

    @property
    def phases(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("phases", [])
        except Exception:
            return []

    @property
    def demanded_skills(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            raw = data.get("demanded_skills", [])
            normalized = []
            for item in raw:
                if isinstance(item, dict):
                    skill_name = item.get("skill") or item.get("name")
                    if skill_name:
                        normalized.append(str(skill_name))
                elif isinstance(item, str):
                    normalized.append(item)
                else:
                    normalized.append(str(item))
            return normalized
        except Exception:
            return []

    @property
    def user_skills(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("user_skills", [])
        except Exception:
            return []

    @property
    def proof_projects(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("proof_projects", [])
        except Exception:
            return []

    @property
    def portfolio_assessment(self):
        if not self.recommendations:
            return {}
        try:
            data = json.loads(self.recommendations)
            return data.get("portfolio_assessment", {})
        except Exception:
            return {}

    @property
    def track_status(self):
        if not self.recommendations:
            return "on_track"
        try:
            data = json.loads(self.recommendations)
            return data.get("track_status", "on_track")
        except Exception:
            return "on_track"

    @property
    def market_changes(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("market_changes", [])
        except Exception:
            return []

    @property
    def personal_changes(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("personal_changes", [])
        except Exception:
            return []

    @property
    def roadmap_updates(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("roadmap_updates", [])
        except Exception:
            return []

    @property
    def actions(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("actions", [])
        except Exception:
            return []

    @property
    def opportunities(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("opportunities", [])
        except Exception:
            return []

    @property
    def questions_for_user(self):
        if not self.recommendations:
            return []
        try:
            data = json.loads(self.recommendations)
            return data.get("questions_for_user", [])
        except Exception:
            return []
