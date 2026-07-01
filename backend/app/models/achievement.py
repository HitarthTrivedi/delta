from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import datetime


class Achievement(Base):
    """A user's trophy-cabinet entry: a certificate, project, award, or other
    accomplishment. Manually added by the user to track their achievements."""
    __tablename__ = "achievements"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # 'certificate' | 'project' | 'award' | 'course' | 'other'
    type = Column(String, nullable=False, default="certificate")
    title = Column(String, nullable=False)
    organization = Column(String, nullable=True)  # issuer / org / platform
    date_achieved = Column(String, nullable=True)  # freeform ("2025", "Jun 2025", "2025-06-01")
    url = Column(String, nullable=True)  # link to the certificate or project
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
