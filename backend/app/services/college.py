"""Delta for College: tenants, staff, batches, rosters, seats and joining.

- Delta (platform admin) creates a college with a seat count and licence, and
  invites its first placement officer (TPO) by email. Staff sign in with that
  email; a login that is already a student or recruiter can't be staff.
- The TPO uploads the roster (CSV), creates batches and shares a batch join
  code. Students join by code (or by college email domain): a roll-number
  match makes them verified; a batch with a roster but no match waits for
  the TPO; a batch without a roster lets them in unverified.
- Joining or leaving a college switches recruiter visibility off (the
  student's audience changed: campus recruiters vs open recruiters).
- A college that is suspended or past its licence stops counting: its
  students drop out of the campus pool and dashboards at once, and the daily
  sweep marks their seats expired.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import re
import secrets
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.college import Batch, College, CollegeAdmin, CollegeMember, CollegeRecruiter, RosterEntry
from app.models.compliance import Recruiter
from app.models.user import User
from app.services import compliance

ROLES = ("tpo", "faculty")
PROGRAMS = ("first_year_4y", "placement_6m", "none")
ROSTER_MAX_ROWS = 5000
ROSTER_MAX_BYTES = 2 * 1024 * 1024
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


def _domains(college: College) -> list[str]:
    try:
        return [d.lower() for d in json.loads(college.email_domains or "[]")]
    except ValueError:
        return []


def _norm_email(email: str | None) -> str | None:
    email = (email or "").strip().lower()
    return email or None


def _college(db: Session, college_id: str) -> College:
    c = db.get(College, college_id)
    if not c:
        raise LookupError("College not found.")
    return c


def seats_used(db: Session, college_id: str) -> int:
    return db.query(CollegeMember).filter(CollegeMember.college_id == college_id,
                                          CollegeMember.status.in_(compliance.IN_COLLEGE_STATES)).count()


def college_dict(db: Session, c: College) -> dict:
    return {
        "id": c.id, "name": c.name, "city": c.city, "state": c.state, "email_domains": _domains(c),
        "seat_limit": c.seat_limit, "seats_used": seats_used(db, c.id),
        "licence_valid_until": c.licence_valid_until.isoformat() if c.licence_valid_until else None,
        "status": c.status, "live": compliance.college_is_live(c), "allow_minors": bool(c.allow_minors),
    }


# ── platform admin ───────────────────────────────────────────────────────────

def _check_domains(db: Session, domains: list[str], college_id: str | None = None) -> list[str]:
    clean = sorted({d.strip().lower().lstrip("@") for d in domains if d and d.strip()})
    for d in clean:
        if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", d):
            raise ValueError(f"'{d}' isn't a valid email domain.")
    for other in db.query(College).filter(College.id != (college_id or "")).all():
        clash = set(clean) & set(_domains(other))
        if clash:
            raise ValueError(f"{', '.join(sorted(clash))} already belongs to {other.name}.")
    return clean


def create_college(db: Session, *, name: str, city: str | None, state: str | None, email_domains: list[str],
                   seat_limit: int, licence_valid_until: datetime.date | None, allow_minors: bool,
                   first_tpo_email: str, created_by: str | None) -> dict:
    name = " ".join((name or "").split())
    if not name:
        raise ValueError("Give the college a name.")
    if seat_limit < 1:
        raise ValueError("A college needs at least one seat.")
    email = _norm_email(first_tpo_email)
    if not email or not _EMAIL.match(email):
        raise ValueError("Enter the placement officer's email.")
    c = College(id=str(uuid.uuid4()), name=name, city=city, state=state,
                email_domains=json.dumps(_check_domains(db, email_domains)), seat_limit=seat_limit,
                licence_valid_until=licence_valid_until, allow_minors=allow_minors)
    db.add(c)
    db.add(CollegeAdmin(id=str(uuid.uuid4()), college_id=c.id, email=email, role="tpo", invited_by=created_by))
    db.commit()
    return college_dict(db, c)


def update_college(db: Session, college_id: str, **fields) -> dict:
    c = _college(db, college_id)
    if "email_domains" in fields and fields["email_domains"] is not None:
        c.email_domains = json.dumps(_check_domains(db, fields.pop("email_domains"), c.id))
    for key in ("name", "city", "state", "seat_limit", "licence_valid_until", "allow_minors", "status"):
        if fields.get(key) is not None:
            setattr(c, key, fields[key])
    if fields.get("status") == "ended" and not c.ended_at:
        c.ended_at = _now()
    db.commit()
    return college_dict(db, c)


def list_colleges(db: Session) -> list[dict]:
    return [college_dict(db, c) for c in db.query(College).order_by(College.created_at.desc()).all()]


# ── staff ────────────────────────────────────────────────────────────────────

def staff_of(db: Session, user_id: str) -> list[CollegeAdmin]:
    return db.query(CollegeAdmin).filter(CollegeAdmin.user_id == user_id, CollegeAdmin.status == "active").all()


def is_staff(db: Session, user_id: str) -> bool:
    return bool(db.query(CollegeAdmin).filter(CollegeAdmin.user_id == user_id,
                                              CollegeAdmin.status != "removed").first())


def require_staff(db: Session, user_id: str, email: str | None, college_id: str, write: bool = False) -> str:
    """The caller's role at this college ('tpo'/'faculty'), or 'delta' for platform admins."""
    if compliance.is_admin(email):
        return "delta"
    row = db.query(CollegeAdmin).filter(CollegeAdmin.college_id == college_id, CollegeAdmin.user_id == user_id,
                                        CollegeAdmin.status == "active").first()
    if not row:
        raise PermissionError("You don't have access to this college.")
    if write and row.role != "tpo":
        raise PermissionError("Only the placement officer can change this. Faculty can view.")
    return row.role


def pending_invites(db: Session, email: str | None) -> list[CollegeAdmin]:
    email = _norm_email(email)
    if not email:
        return []
    return db.query(CollegeAdmin).filter(CollegeAdmin.email == email, CollegeAdmin.status == "invited").all()


def accept_invites(db: Session, user_id: str, email: str | None, policy_version: str | None) -> list[dict]:
    """Staff accept their invites (same verified email) and the staff terms."""
    invites = pending_invites(db, email)
    if not invites:
        raise LookupError("There's no college invite for this email.")
    if policy_version != compliance.POLICY_VERSION:
        raise ValueError("The terms were updated. Please review the latest version.")
    if db.get(Recruiter, user_id):
        raise ValueError("This login is a recruiter account. Use a separate email for college work.")
    user = db.get(User, user_id)
    if user and user.profile_data:
        raise ValueError("This login is a student account. Use your college staff email instead.")
    for inv in invites:
        inv.user_id, inv.status, inv.accepted_at = user_id, "active", _now()
    db.commit()
    compliance.record_consent(db, user_id, compliance.TERMS, True)
    compliance.record_consent(db, user_id, compliance.COLLEGE_ADMIN_TERMS, True)
    return my_colleges(db, user_id)


def my_colleges(db: Session, user_id: str) -> list[dict]:
    out = []
    for row in staff_of(db, user_id):
        c = db.get(College, row.college_id)
        if c:
            out.append({**college_dict(db, c), "role": row.role})
    return out


def team(db: Session, college_id: str) -> list[dict]:
    rows = db.query(CollegeAdmin).filter(CollegeAdmin.college_id == college_id,
                                         CollegeAdmin.status != "removed").order_by(CollegeAdmin.created_at).all()
    return [{"id": r.id, "email": r.email, "role": r.role, "status": r.status} for r in rows]


def invite_staff(db: Session, college_id: str, email: str, role: str, by: str) -> list[dict]:
    _college(db, college_id)
    email = _norm_email(email)
    if not email or not _EMAIL.match(email):
        raise ValueError("Enter a valid email.")
    if role not in ROLES:
        raise ValueError("Role must be tpo or faculty.")
    existing = db.query(CollegeAdmin).filter(CollegeAdmin.college_id == college_id, CollegeAdmin.email == email).first()
    if existing and existing.status != "removed":
        existing.role = role
    elif existing:
        existing.status, existing.role, existing.user_id = "invited", role, None
    else:
        db.add(CollegeAdmin(id=str(uuid.uuid4()), college_id=college_id, email=email, role=role, invited_by=by))
    db.commit()
    return team(db, college_id)


def remove_staff(db: Session, college_id: str, admin_id: str) -> list[dict]:
    row = db.query(CollegeAdmin).filter(CollegeAdmin.id == admin_id, CollegeAdmin.college_id == college_id).first()
    if not row:
        raise LookupError("Not found.")
    tpos = db.query(CollegeAdmin).filter(CollegeAdmin.college_id == college_id, CollegeAdmin.role == "tpo",
                                         CollegeAdmin.status != "removed").count()
    if row.role == "tpo" and tpos <= 1:
        raise ValueError("A college needs at least one placement officer.")
    row.status = "removed"
    db.commit()
    return team(db, college_id)


# ── batches ──────────────────────────────────────────────────────────────────

def batch_dict(db: Session, b: Batch) -> dict:
    members = db.query(CollegeMember).filter(CollegeMember.batch_id == b.id,
                                             CollegeMember.status.in_(compliance.IN_COLLEGE_STATES)).count()
    roster = db.query(RosterEntry).filter(RosterEntry.batch_id == b.id).count()
    return {"id": b.id, "name": b.name, "course": b.course, "duration_years": b.duration_years,
            "grad_year": b.grad_year, "branch": b.branch, "section": b.section, "program": b.program,
            "join_code": b.join_code, "join_code_active": b.join_code_active, "members": members,
            "roster": roster, "archived": bool(b.archived_at)}


def _batch_name(grad_year, branch, section, course=None) -> str:
    parts = [course, branch, f"{grad_year}" if grad_year else None, f"Sec {section}" if section else None]
    return " · ".join(p for p in parts if p) or "Batch"


def create_batch(db: Session, college_id: str, *, name: str | None = None, course: str | None = None,
                 grad_year: int | None = None, branch: str | None = None, section: str | None = None,
                 program: str = "none", duration_years: int = 4) -> dict:
    _college(db, college_id)
    if program not in PROGRAMS:
        raise ValueError("Unknown program.")
    b = Batch(id=str(uuid.uuid4()), college_id=college_id, course=course, grad_year=grad_year, branch=branch,
              section=section, program=program, duration_years=duration_years, join_code=_code(),
              name=" ".join((name or "").split()) or _batch_name(grad_year, branch, section, course))
    db.add(b)
    db.commit()
    return batch_dict(db, b)


def _batch(db: Session, college_id: str, batch_id: str) -> Batch:
    b = db.query(Batch).filter(Batch.id == batch_id, Batch.college_id == college_id).first()
    if not b:
        raise LookupError("Batch not found.")
    return b


def update_batch(db: Session, college_id: str, batch_id: str, **fields) -> dict:
    b = _batch(db, college_id, batch_id)
    if fields.get("program") is not None and fields["program"] not in PROGRAMS:
        raise ValueError("Unknown program.")
    for key in ("name", "course", "grad_year", "branch", "section", "program", "join_code_active"):
        if fields.get(key) is not None:
            setattr(b, key, fields[key])
    if fields.get("archived") is not None:
        b.archived_at = _now() if fields["archived"] else None
    db.commit()
    return batch_dict(db, b)


def rotate_code(db: Session, college_id: str, batch_id: str) -> dict:
    b = _batch(db, college_id, batch_id)
    b.join_code = _code()
    b.join_code_active = True
    db.commit()
    return batch_dict(db, b)


def list_batches(db: Session, college_id: str) -> list[dict]:
    rows = db.query(Batch).filter(Batch.college_id == college_id).order_by(Batch.grad_year, Batch.name).all()
    return [batch_dict(db, b) for b in rows]


# ── roster import ────────────────────────────────────────────────────────────

_ALIASES = {
    "roll_no": ("roll_no", "roll", "rollno", "roll_number", "registration_no", "reg_no", "usn", "enrollment_no",
                "enrolment_no", "prn"),
    "name": ("name", "student_name", "full_name"),
    "email": ("email", "email_id", "college_email", "mail"),
    "grad_year": ("grad_year", "batch", "passing_year", "year_of_passing", "graduation_year"),
    "branch": ("branch", "department", "dept", "stream", "specialisation", "specialization"),
    "section": ("section", "sec", "division", "div"),
    "course": ("course", "program", "programme", "degree"),
    "cgpa": ("cgpa", "gpa", "cpi"),
    "backlogs": ("backlogs", "active_backlogs", "arrears", "kt"),
    "dob": ("dob", "date_of_birth", "birth_date"),
}


def _header_map(headers: list[str]) -> dict[str, str]:
    norm = {re.sub(r"[\s\-./]+", "_", (h or "").strip().lower()): h for h in headers}
    found = {}
    for key, names in _ALIASES.items():
        for n in names:
            if n in norm:
                found[key] = norm[n]
                break
    return found


def _parse_date(value: str) -> datetime.date | None:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("use a date like 2008-03-25 or 25/03/2008")


def import_roster(db: Session, college_id: str, raw: bytes, *, dry_run: bool, create_batches: bool,
                  minors_consent_ref: str | None, by: str) -> dict:
    """Validate and upsert roster rows by roll number. Never changes who
    claimed a row. Under-18 rows need the college's parental-consent reference."""
    college = _college(db, college_id)
    if len(raw) > ROSTER_MAX_BYTES:
        raise ValueError("The file is too big (2 MB max). Split it by batch.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    cols = _header_map(reader.fieldnames or [])
    if "roll_no" not in cols or "name" not in cols:
        raise ValueError("The CSV needs at least a roll number column and a name column.")
    today = datetime.date.today()
    rows, errors, seen_roll, seen_email = [], [], set(), set()
    for i, raw_row in enumerate(reader, start=2):  # row 1 is the header
        if i - 1 > ROSTER_MAX_ROWS:
            raise ValueError(f"Too many rows ({ROSTER_MAX_ROWS} max). Split the file by batch.")
        get = lambda k: (raw_row.get(cols[k]) or "").strip() if k in cols else ""  # noqa: E731
        r = {"line": i, "roll_no": get("roll_no").upper(), "name": " ".join(get("name").split()),
             "email": _norm_email(get("email")), "branch": get("branch") or None, "section": get("section") or None,
             "course": get("course") or None, "grad_year": None, "cgpa": None, "backlogs": None, "dob": None}
        if not any(v for k, v in r.items() if k != "line"):
            continue  # blank line
        problems = []
        if not r["roll_no"]:
            problems.append(("roll_no", "missing"))
        elif r["roll_no"] in seen_roll:
            problems.append(("roll_no", "appears twice in this file"))
        if not r["name"]:
            problems.append(("name", "missing"))
        if r["email"]:
            if not _EMAIL.match(r["email"]):
                problems.append(("email", "isn't a valid email"))
            elif r["email"] in seen_email:
                problems.append(("email", "appears twice in this file"))
        for key, conv, lo, hi in (("grad_year", int, today.year - 1, today.year + 6), ("cgpa", float, 0, 10),
                                  ("backlogs", int, 0, 99)):
            v = get(key)
            if v:
                try:
                    r[key] = conv(float(v)) if conv is int else conv(v)
                    if not lo <= r[key] <= hi:
                        problems.append((key, f"should be between {lo} and {hi}"))
                except ValueError:
                    problems.append((key, "isn't a number"))
        if get("dob"):
            try:
                r["dob"] = _parse_date(get("dob"))
            except ValueError as exc:
                problems.append(("dob", str(exc)))
        for field, message in problems:
            errors.append({"row": i, "field": field, "message": message})
        if not problems:
            seen_roll.add(r["roll_no"])
            if r["email"]:
                seen_email.add(r["email"])
            rows.append(r)

    existing = {e.roll_no: e for e in db.query(RosterEntry).filter(RosterEntry.college_id == college_id).all()}
    by_email = {e.email: e.roll_no for e in existing.values() if e.email}
    minors = [r for r in rows if r["dob"] and compliance.age_on(r["dob"], today) < compliance.ADULT_AGE]
    for r in rows:
        if r["email"] and by_email.get(r["email"], r["roll_no"]) != r["roll_no"]:
            errors.append({"row": r["line"], "field": "email", "message": "already used by another roll number"})
    if minors and not college.allow_minors:
        errors += [{"row": r["line"], "field": "dob", "message": "under 18: this college isn't set up for under-18 students"}
                   for r in minors]
    elif minors and not (minors_consent_ref or "").strip():
        errors += [{"row": r["line"], "field": "dob",
                    "message": "under 18: confirm the college holds their parent's consent (add the consent reference)"}
                   for r in minors]
    bad_lines = {e["row"] for e in errors}
    rows = [r for r in rows if r["line"] not in bad_lines]

    batches = {(b.grad_year, (b.branch or "").lower(), (b.section or "").lower()): b
               for b in db.query(Batch).filter(Batch.college_id == college_id, Batch.archived_at.is_(None)).all()}
    created = updated = unchanged = 0
    new_batches = set()
    for r in rows:
        key = (r["grad_year"], (r["branch"] or "").lower(), (r["section"] or "").lower())
        batch = batches.get(key)
        if batch is None and create_batches and (r["grad_year"] or r["branch"]):
            new_batches.add(key)
            if not dry_run:
                batch = Batch(id=str(uuid.uuid4()), college_id=college_id, grad_year=r["grad_year"],
                              branch=r["branch"], section=r["section"], course=r["course"], join_code=_code(),
                              name=_batch_name(r["grad_year"], r["branch"], r["section"], r["course"]))
                db.add(batch)
                batches[key] = batch
        fields = {"name": r["name"], "email": r["email"], "cgpa": r["cgpa"], "backlogs": r["backlogs"],
                  "dob": r["dob"], "batch_id": batch.id if batch else None}
        attest = bool(r["dob"] and compliance.age_on(r["dob"], today) < compliance.ADULT_AGE)
        entry = existing.get(r["roll_no"])
        if entry is None:
            created += 1
            if not dry_run:
                entry = RosterEntry(id=str(uuid.uuid4()), college_id=college_id, roll_no=r["roll_no"], **fields)
                db.add(entry)
        elif any(getattr(entry, k) != v for k, v in fields.items()):
            updated += 1
            if not dry_run:
                for k, v in fields.items():
                    setattr(entry, k, v)
        else:
            unchanged += 1
        if attest and not dry_run and entry is not None:
            entry.minor_consent_ref, entry.attested_by, entry.attested_at = minors_consent_ref.strip(), by, _now()
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return {"dry_run": dry_run, "created": created, "updated": updated, "unchanged": unchanged,
            "new_batches": len(new_batches), "minors": len(minors), "errors": sorted(errors, key=lambda e: e["row"])}


def roster(db: Session, college_id: str, batch_id: str | None = None, joined: bool | None = None) -> list[dict]:
    q = db.query(RosterEntry).filter(RosterEntry.college_id == college_id)
    if batch_id:
        q = q.filter(RosterEntry.batch_id == batch_id)
    if joined is not None:
        q = q.filter(RosterEntry.claimed_user_id.isnot(None) if joined else RosterEntry.claimed_user_id.is_(None))
    return [{"id": e.id, "roll_no": e.roll_no, "name": e.name, "email": e.email, "batch_id": e.batch_id,
             "cgpa": e.cgpa, "backlogs": e.backlogs, "joined": bool(e.claimed_user_id)}
            for e in q.order_by(RosterEntry.roll_no).all()]


# ── members ──────────────────────────────────────────────────────────────────

def _member_dict(db: Session, m: CollegeMember) -> dict:
    user = db.get(User, m.user_id)
    entry = db.get(RosterEntry, m.roster_entry_id) if m.roster_entry_id else None
    return {"id": m.id, "name": (entry.name if entry else None) or (user.name if user else "Student"),
            "roll_no": entry.roll_no if entry else None, "batch_id": m.batch_id, "status": m.status,
            "verified": bool(m.verified), "joined_via": m.joined_via,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None}


def members(db: Session, college_id: str, batch_id: str | None = None, status: str | None = None) -> list[dict]:
    q = db.query(CollegeMember).filter(CollegeMember.college_id == college_id)
    if batch_id:
        q = q.filter(CollegeMember.batch_id == batch_id)
    if status:
        q = q.filter(CollegeMember.status == status)
    return [_member_dict(db, m) for m in q.order_by(CollegeMember.joined_at.desc()).all()]


def _member(db: Session, college_id: str, member_id: str) -> CollegeMember:
    m = db.query(CollegeMember).filter(CollegeMember.id == member_id, CollegeMember.college_id == college_id).first()
    if not m:
        raise LookupError("Student not found.")
    return m


def approve_member(db: Session, college_id: str, member_id: str) -> dict:
    m = _member(db, college_id, member_id)
    if m.status != "pending":
        raise ValueError("Only students waiting for approval can be approved.")
    m.status, m.verified = "active", True
    db.commit()
    return _member_dict(db, m)


def _end_membership(db: Session, m: CollegeMember, status: str) -> None:
    m.status, m.removed_at = status, _now()
    db.commit()
    compliance.record_consent(db, m.user_id, compliance.COLLEGE_ENROLLMENT, False, subject_id=m.college_id)
    compliance.withdraw_recruiter_visibility(db, m.user_id)


def remove_member(db: Session, college_id: str, member_id: str) -> None:
    m = _member(db, college_id, member_id)
    if m.status in compliance.IN_COLLEGE_STATES:
        _end_membership(db, m, "removed")


# ── campus recruiters ────────────────────────────────────────────────────────

def recruiter_links(db: Session, college_id: str) -> list[dict]:
    rows = db.query(CollegeRecruiter).filter(CollegeRecruiter.college_id == college_id,
                                             CollegeRecruiter.status != "revoked").order_by(CollegeRecruiter.created_at).all()
    out = []
    for r in rows:
        rec = db.get(Recruiter, r.recruiter_id) if r.recruiter_id else None
        out.append({"id": r.id, "email": r.invited_email, "status": r.status,
                    "company": rec.company if rec else None, "name": rec.name if rec else None})
    return out


def link_recruiter(db: Session, college_id: str, email: str, linked_by: str = "college") -> list[dict]:
    _college(db, college_id)
    email = _norm_email(email)
    if not email or not _EMAIL.match(email):
        raise ValueError("Enter the recruiter's work email.")
    rec = db.query(Recruiter).filter(Recruiter.email == email).first()
    if rec and (rec.pool or "open") != "campus":
        raise ValueError("That recruiter hires off-campus (open pool), so they can't be linked to a college.")
    link = db.query(CollegeRecruiter).filter(CollegeRecruiter.college_id == college_id,
                                             CollegeRecruiter.invited_email == email).first()
    if not link:
        link = CollegeRecruiter(id=str(uuid.uuid4()), college_id=college_id, invited_email=email, linked_by=linked_by)
        db.add(link)
    link.revoked_at = None
    if rec and rec.status == "approved":
        link.recruiter_id, link.status = rec.id, "active"
    else:
        link.recruiter_id, link.status = (rec.id if rec else None), "invited"
    db.commit()
    return recruiter_links(db, college_id)


def revoke_recruiter(db: Session, college_id: str, link_id: str) -> list[dict]:
    link = db.query(CollegeRecruiter).filter(CollegeRecruiter.id == link_id,
                                             CollegeRecruiter.college_id == college_id).first()
    if not link:
        raise LookupError("Not found.")
    link.status, link.revoked_at = "revoked", _now()
    db.commit()
    return recruiter_links(db, college_id)


def activate_recruiter_links(db: Session, rec: Recruiter) -> None:
    """When Delta approves a campus recruiter, the colleges that invited them take effect."""
    if (rec.pool or "open") != "campus" or not rec.email:
        return
    for link in db.query(CollegeRecruiter).filter(CollegeRecruiter.invited_email == rec.email.lower(),
                                                  CollegeRecruiter.status == "invited").all():
        link.recruiter_id, link.status = rec.id, "active"
    db.commit()


# ── students ─────────────────────────────────────────────────────────────────

def membership(db: Session, user_id: str) -> CollegeMember | None:
    return db.query(CollegeMember).filter(CollegeMember.user_id == user_id,
                                          CollegeMember.status.in_(compliance.IN_COLLEGE_STATES)).first()


def student_state(db: Session, user_id: str, email: str | None) -> dict:
    m = membership(db, user_id)
    if m:
        c = db.get(College, m.college_id)
        b = db.get(Batch, m.batch_id) if m.batch_id else None
        return {"membership": {"college": c.name, "college_id": c.id, "live": compliance.college_is_live(c),
                               "batch": b.name if b else None, "program": b.program if b else "none",
                               "status": m.status, "verified": bool(m.verified),
                               "joined_at": m.joined_at.isoformat() if m.joined_at else None},
                "suggestion": None}
    return {"membership": None, "suggestion": _domain_suggestion(db, email)}


def _domain_college(db: Session, email: str | None) -> College | None:
    email = _norm_email(email)
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[1]
    for c in db.query(College).filter(College.status == "active").all():
        if domain in _domains(c):
            return c
    return None


def _domain_suggestion(db: Session, email: str | None) -> dict | None:
    c = _domain_college(db, email)
    if not c or not compliance.college_is_live(c):
        return None
    entry = db.query(RosterEntry).filter(RosterEntry.college_id == c.id, RosterEntry.email == _norm_email(email),
                                         RosterEntry.claimed_user_id.is_(None)).first()
    return {"college": c.name, "on_roster": bool(entry)}


def preview_code(db: Session, code: str) -> dict | None:
    b = db.query(Batch).filter(Batch.join_code == (code or "").strip().upper(), Batch.join_code_active.is_(True),
                               Batch.archived_at.is_(None)).first()
    if not b:
        return None
    c = db.get(College, b.college_id)
    if not compliance.college_is_live(c):
        return None
    has_roster = db.query(RosterEntry).filter(RosterEntry.batch_id == b.id).first() is not None
    return {"college": c.name, "batch": b.name, "program": b.program, "needs_roll_no": has_roster}


def join(db: Session, user_id: str, email: str | None, *, code: str | None = None, via_domain: bool = False,
         roll_no: str | None = None, joined_via: str | None = None) -> dict:
    """Take a seat. Verified when the roll number (or college email) matches
    the roster; waits for the TPO when the batch has a roster but no match."""
    if db.get(Recruiter, user_id) or is_staff(db, user_id):
        raise ValueError("Staff and recruiter accounts can't join a college as a student.")
    batch, entry = None, None
    if code:
        batch = db.query(Batch).filter(Batch.join_code == code.strip().upper(), Batch.join_code_active.is_(True),
                                       Batch.archived_at.is_(None)).first()
        if not batch:
            raise ValueError("This join code isn't valid any more. Ask your placement office for a new one.")
        college_id = batch.college_id
    elif via_domain:
        c = _domain_college(db, email)
        if not c:
            raise ValueError("Your email isn't from a college on Delta. Ask your placement office for a join code.")
        college_id = c.id
    else:
        raise ValueError("Enter your college's join code.")

    college = db.query(College).filter(College.id == college_id).with_for_update().first()  # seats: one at a time
    if not compliance.college_is_live(college):
        raise ValueError("Your college's Delta access isn't active right now. Please check with your placement office.")
    current = membership(db, user_id)
    if current:
        if current.college_id == college.id:
            db.rollback()
            return student_state(db, user_id, email)
        raise ValueError("You're already in a college on Delta. Leave it first from Privacy settings.")
    if seats_used(db, college.id) >= college.seat_limit:
        raise ValueError("Your college has no free seats right now. Please tell your placement office.")

    unclaimed = db.query(RosterEntry).filter(RosterEntry.college_id == college.id, RosterEntry.claimed_user_id.is_(None))
    if roll_no:
        entry = unclaimed.filter(RosterEntry.roll_no == roll_no.strip().upper()).first()
        if entry and batch and entry.batch_id and entry.batch_id != batch.id:
            entry = None
    if entry is None and email:
        entry = unclaimed.filter(RosterEntry.email == _norm_email(email)).first()
        if entry and batch and entry.batch_id and entry.batch_id != batch.id:
            entry = None
    if via_domain and entry is None:
        raise ValueError("We couldn't find you on your college's list. Ask your placement office for a join code.")
    if entry and entry.dob and compliance.age_on(entry.dob, datetime.date.today()) < compliance.ADULT_AGE \
            and joined_via != "minor":
        raise ValueError("Your college's list says you're under 18. Choose \"I'm under 18\" when you sign up.")

    batch_has_roster = bool(batch and db.query(RosterEntry).filter(RosterEntry.batch_id == batch.id).first())
    if entry:
        status, verified = "active", True
        batch = batch or (db.get(Batch, entry.batch_id) if entry.batch_id else None)
        entry.claimed_user_id, entry.claimed_at = user_id, _now()
    elif batch_has_roster:
        status, verified = "pending", False
    else:
        status, verified = "active", False

    existing = db.query(CollegeMember).filter(CollegeMember.college_id == college.id,
                                              CollegeMember.user_id == user_id).first()
    if existing:  # rejoining after leaving
        existing.status, existing.verified, existing.batch_id = status, verified, batch.id if batch else None
        existing.roster_entry_id, existing.joined_at, existing.removed_at = (entry.id if entry else None), _now(), None
        existing.joined_via = joined_via or ("domain" if via_domain else "code")
    else:
        db.add(CollegeMember(id=str(uuid.uuid4()), college_id=college.id, user_id=user_id,
                             batch_id=batch.id if batch else None, roster_entry_id=entry.id if entry else None,
                             status=status, verified=verified, joined_via=joined_via or ("domain" if via_domain else "code")))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Please try again in a moment.")
    compliance.record_consent(db, user_id, compliance.COLLEGE_ENROLLMENT, True, subject_id=college.id)
    compliance.withdraw_recruiter_visibility(db, user_id)
    _prefill_profile(user_id, college, batch)
    return student_state(db, user_id, email)


def _prefill_profile(user_id: str, college: College, batch: Batch | None) -> None:
    """Convenience only: the trusted values stay on the membership."""
    from app.services.profile_store import save_profile
    data = {"university": college.name}
    if batch and batch.branch:
        data["major"] = batch.branch
    try:
        save_profile(user_id, data)
    except Exception:
        pass


def leave(db: Session, user_id: str) -> dict:
    m = membership(db, user_id)
    if m:
        _end_membership(db, m, "removed")
    return {"membership": None, "suggestion": None}


def expire_ended_licences(db: Session) -> int:
    """Daily: seats at colleges that are no longer live become expired."""
    count = 0
    for c in db.query(College).all():
        if compliance.college_is_live(c):
            continue
        for m in db.query(CollegeMember).filter(CollegeMember.college_id == c.id,
                                                CollegeMember.status.in_(compliance.IN_COLLEGE_STATES)).all():
            _end_membership(db, m, "expired")
            count += 1
    return count
