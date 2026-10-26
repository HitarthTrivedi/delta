"""Delta for College: colleges (tenants), their staff, batches, rosters,
student memberships, campus-recruiter links and under-18 consent requests.

Ownership (see docs/COLLEGE_DATA_NOTES.md):
- The roster is the college's data; Delta processes it for the college.
- What a student creates in Delta is theirs. `college_members`,
  `college_admins` and `parental_consent_requests` carry `user_id`, so the
  privacy export and erasure cover them; a roster row only points at the
  student through `claimed_user_id`, which erasure clears.
"""
import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database import Base


class College(Base):
    __tablename__ = "colleges"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    email_domains = Column(Text, nullable=False, default="[]")  # JSON list, e.g. ["svce.ac.in"]
    seat_limit = Column(Integer, nullable=False, default=0)
    licence_valid_until = Column(Date, nullable=True)
    status = Column(String, nullable=False, default="active")  # active | suspended | ended
    allow_minors = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class CollegeAdmin(Base):
    """A placement officer (TPO) or faculty member. Invited by email; becomes
    active when that person signs in with the same verified email."""
    __tablename__ = "college_admins"

    id = Column(String, primary_key=True)
    college_id = Column(String, ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # set on acceptance (may have no users row)
    email = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, default="tpo")  # tpo | faculty
    status = Column(String, nullable=False, default="invited")  # invited | active | removed
    invited_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)


class Batch(Base):
    __tablename__ = "batches"

    id = Column(String, primary_key=True)
    college_id = Column(String, ForeignKey("colleges.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    course = Column(String, nullable=True)  # B.Tech, MCA...
    duration_years = Column(Integer, nullable=False, default=4)
    grad_year = Column(Integer, nullable=True)
    branch = Column(String, nullable=True)
    section = Column(String, nullable=True)
    program = Column(String, nullable=False, default="none")  # first_year_4y | placement_6m | none
    join_code = Column(String, nullable=False, unique=True, index=True)
    join_code_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)


class RosterEntry(Base):
    """One student on the college's roster (uploaded by the TPO), claimed
    when that student joins."""
    __tablename__ = "roster_entries"
    __table_args__ = (UniqueConstraint("college_id", "roll_no", name="uq_roster_college_roll"),)

    id = Column(String, primary_key=True)
    college_id = Column(String, ForeignKey("colleges.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=True, index=True)
    roll_no = Column(String, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True, index=True)
    cgpa = Column(Float, nullable=True)
    backlogs = Column(Integer, nullable=True)
    dob = Column(Date, nullable=True)
    # College's own record that it holds verifiable parental consent (under-18s).
    minor_consent_ref = Column(String, nullable=True)
    attested_by = Column(String, nullable=True)
    attested_at = Column(DateTime, nullable=True)
    claimed_user_id = Column(String, nullable=True, index=True)
    claimed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class CollegeMember(Base):
    """A student's seat at a college. A student holds at most one pending or
    active membership at a time (checked in code)."""
    __tablename__ = "college_members"
    __table_args__ = (UniqueConstraint("college_id", "user_id", name="uq_college_member"),)

    id = Column(String, primary_key=True)
    college_id = Column(String, ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    batch_id = Column(String, ForeignKey("batches.id"), nullable=True, index=True)
    roster_entry_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")  # pending | active | removed | expired
    joined_via = Column(String, nullable=False, default="code")  # code | domain | minor
    verified = Column(Boolean, nullable=False, default=False)  # matched the college's roster
    joined_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)


class CollegeRecruiter(Base):
    """A campus recruiter allowed to see this college's opted-in students."""
    __tablename__ = "college_recruiters"
    __table_args__ = (UniqueConstraint("college_id", "invited_email", name="uq_college_recruiter_email"),)

    id = Column(String, primary_key=True)
    college_id = Column(String, ForeignKey("colleges.id"), nullable=False, index=True)
    recruiter_id = Column(String, nullable=True, index=True)
    invited_email = Column(String, nullable=False)
    status = Column(String, nullable=False, default="invited")  # invited | active | revoked
    linked_by = Column(String, nullable=False, default="college")  # college | delta
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)


class ParentalConsentRequest(Base):
    """Verifiable parental consent for an under-18 college student: a one-time
    link emailed to the parent (only its hash is stored), or the college's attestation."""
    __tablename__ = "parental_consent_requests"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    college_id = Column(String, nullable=True)
    parent_name = Column(String, nullable=True)
    parent_email = Column(String, nullable=True)
    token_hash = Column(String, nullable=True, index=True)
    method = Column(String, nullable=False, default="parent_link")  # parent_link | college_attestation
    status = Column(String, nullable=False, default="pending")  # pending | granted | declined | expired
    expires_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
