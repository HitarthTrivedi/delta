"""Fill a Delta account with realistic demo data for a live demo.

Usage (from backend/):
    python seed_demo.py --user-id <supabase-user-uuid> --yes
    python seed_demo.py --user-id <uuid> --with-candidates --yes      # + 7 opted-in fictional students (incl. nursing and CA) for recruiter search
    python seed_demo.py --approve-recruiter-id <uuid> --yes           # approve a recruiter account
    python seed_demo.py --clear --user-id <uuid> --yes                # erase the demo account's data + all fictional candidates

The demo account must already exist: sign up in the app first, then copy the
user id (Supabase dashboard → Authentication → Users). The roadmap is NOT
seeded; it is generated live, so open /roadmap once before the demo.

Fictional candidates use fixed ids (demo-cand-1..7) and example.com emails.
"""
import argparse
import datetime
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base  # noqa: E402
import app.models  # noqa: F401,E402
from app.models import User, SkillNode, SandboxSession, JourneyEvent, Recruiter  # noqa: E402
from app.services import compliance  # noqa: E402

NOW = datetime.datetime.utcnow()
CANDIDATE_IDS = [f"demo-cand-{i}" for i in range(1, 8)]


def ago(days, hours=0):
    return NOW - datetime.timedelta(days=days, hours=hours)


# ── Technical / aptitude tests (real questions, answer keys checked) ─────────

def q(question, options, answer, explanation, skill):
    return {"question": question, "options": options, "answer_index": answer, "explanation": explanation, "skill": skill}


TESTS = [
    {
        "days": 18, "title": "Theory Test: DBMS", "topic": "DBMS", "difficulty": "medium", "category": "technical",
        "chosen": [0, 0, 1, 0, 3],
        "questions": [
            q("Which normal form removes partial dependencies on a composite primary key?",
              ["Second Normal Form (2NF)", "First Normal Form (1NF)", "Third Normal Form (3NF)", "BCNF"], 0,
              "2NF requires every non-key attribute to depend on the whole composite key, not part of it.", "Normalization"),
            q("A table is in 3NF but not BCNF. What must be true?",
              ["It has no functional dependencies", "It has a multivalued dependency",
               "Some determinant of a functional dependency is not a candidate key", "It is not in 2NF"], 2,
              "BCNF requires every determinant to be a candidate key; 3NF allows exceptions when the dependent attribute is prime.", "Normalization"),
            q("Which JOIN returns all rows from the left table and matching rows from the right?",
              ["INNER JOIN", "LEFT OUTER JOIN", "CROSS JOIN", "SELF JOIN"], 1,
              "A LEFT OUTER JOIN keeps every left-table row, filling NULLs where the right side has no match.", "SQL joins"),
            q("Which ACID property guarantees that a committed transaction survives a crash?",
              ["Atomicity", "Consistency", "Isolation", "Durability"], 3,
              "Durability means committed changes persist even after power loss or crashes, usually via logs.", "Transactions"),
            q("Two transactions read the same row, both update it, and one update is lost. This is called:",
              ["Dirty read", "Phantom read", "Non-repeatable read", "Lost update"], 3,
              "A lost update happens when concurrent writes overwrite each other without coordination.", "Transactions"),
        ],
    },
    {
        "days": 12, "title": "Aptitude Test: Quantitative aptitude", "topic": "Quantitative aptitude", "difficulty": "medium", "category": "aptitude",
        "chosen": [1, 2, 0, 2, 0],
        "questions": [
            q("A shirt marked ₹800 is sold at a 15% discount. What is the selling price?",
              ["₹640", "₹680", "₹700", "₹720"], 1, "15% of 800 is 120, so the price is 800 − 120 = ₹680.", "Percentages"),
            q("A can finish a job in 10 days and B in 15 days. Working together, how many days do they take?",
              ["5", "8", "6", "12.5"], 2, "Together they do 1/10 + 1/15 = 1/6 of the job per day, so 6 days.", "Time and work"),
            q("A train 150 m long passes a pole in 10 seconds. What is its speed in km/h?",
              ["54 km/h", "45 km/h", "60 km/h", "15 km/h"], 0, "150 m / 10 s = 15 m/s = 15 × 18/5 = 54 km/h.", "Speed and distance"),
            q("The ratio of boys to girls in a class is 3:5. If there are 40 students, how many are girls?",
              ["15", "20", "24", "25"], 3, "Girls are 5/8 of 40 = 25.", "Ratios"),
            q("What is the simple interest on ₹5,000 at 8% per annum for 3 years?",
              ["₹1,200", "₹1,000", "₹1,500", "₹1,800"], 0, "SI = 5000 × 8 × 3 / 100 = ₹1,200.", "Interest"),
        ],
    },
    {
        "days": 7, "title": "Theory Test: Operating Systems", "topic": "Operating Systems", "difficulty": "medium", "category": "technical",
        "chosen": [2, 0, 3, 0, 1],
        "questions": [
            q("Which of these is NOT one of the four necessary conditions for deadlock?",
              ["Mutual exclusion", "Hold and wait", "Preemption", "Circular wait"], 2,
              "The four conditions include NO preemption; allowing preemption breaks deadlock.", "Deadlocks"),
            q("Which scheduling algorithm can cause starvation of long jobs?",
              ["Round Robin", "Shortest Job First", "First Come First Served", "None of these"], 1,
              "SJF keeps picking shorter jobs, so a long job may wait indefinitely.", "CPU scheduling"),
            q("What does a TLB cache?",
              ["Disk blocks", "Process control blocks", "Page table entries", "System calls"], 2,
              "The Translation Lookaside Buffer caches recent virtual-to-physical page translations.", "Memory management"),
            q("Thrashing happens when:",
              ["The system spends most of its time paging", "The CPU is idle", "A process has too many threads", "The disk is full"], 0,
              "Thrashing is when processes keep page-faulting, so the system spends most time swapping pages.", "Memory management"),
            q("A semaphore initialised to 1 is typically used as:",
              ["A counting semaphore for N resources", "A mutex lock", "A condition variable", "A scheduler"], 1,
              "A binary semaphore (initial value 1) gives mutual exclusion like a lock.", "Synchronization"),
        ],
    },
    {
        "days": 2, "title": "Theory Test: DBMS", "topic": "DBMS", "difficulty": "hard", "category": "technical",
        "chosen": [1, 0, 1, 3, 0],
        "questions": [
            q("Which isolation level prevents dirty reads but still allows non-repeatable reads?",
              ["Read Uncommitted", "Read Committed", "Repeatable Read", "Serializable"], 1,
              "Read Committed only shows committed data, but a row can change between two reads.", "Transactions"),
            q("A B+ tree index is preferred over a hash index for:",
              ["Range queries", "Exact-match lookups only", "Small tables only", "Write-heavy logs"], 0,
              "B+ tree leaves are linked in order, so range scans are efficient; hash indexes only support equality.", "Indexing"),
            q("What does a covering index allow?",
              ["Faster writes", "Avoiding locks", "Answering a query from the index without reading the table", "Storing NULLs"], 2,
              "If the index holds every column the query needs, the database never touches the base table.", "Indexing"),
            q("In 2-phase locking, a transaction cannot:",
              ["Read after writing", "Lock two rows", "Commit early", "Acquire a lock after releasing any lock"], 3,
              "2PL has a growing phase then a shrinking phase; once a lock is released no new lock may be taken.", "Transactions"),
            q("Decomposing a relation is 'lossless' when:",
              ["Joining the parts gives back exactly the original relation", "No attributes are repeated",
               "Every part is in BCNF", "Functional dependencies are removed"], 0,
              "A lossless-join decomposition reconstructs the original relation exactly, with no spurious rows.", "Normalization"),
        ],
    },
]


def theory_session(user_id, t):
    qs = t["questions"]
    per_q, breakdown, correct = [], {}, 0
    for item, chosen in zip(qs, t["chosen"]):
        ok = chosen == item["answer_index"]
        correct += ok
        b = breakdown.setdefault(item["skill"], {"correct": 0, "total": 0})
        b["total"] += 1
        b["correct"] += ok
        per_q.append({**item, "chosen_index": chosen, "correct": ok})
    score = round(100 * correct / len(qs))
    started = ago(t["days"], 1)
    result = {
        "score": score, "correct": correct, "total": len(qs), "skill_breakdown": breakdown, "questions": per_q,
        "difficulty": t["difficulty"], "category": t["category"], "time_taken_seconds": 210 + 20 * len(qs),
        "time_limit_seconds": 60 * len(qs), "overtime": False,
    }
    data = {"topic": t["topic"], "category": t["category"], "difficulty": t["difficulty"], "questions": qs,
            "time_limit_seconds": 60 * len(qs), "started_at": started.isoformat(), "answers": t["chosen"], "result": result}
    return SandboxSession(id=str(uuid.uuid4()), user_id=user_id, type="theory", title=t["title"], status="completed",
                          data=json.dumps(data), score=score, created_at=started, completed_at=started + datetime.timedelta(minutes=5))


# ── Coding ──────────────────────────────────────────────────────────────────

CODING = [
    {"days": 15, "title": "Two Sum", "topic": "Arrays", "difficulty": "Easy", "solved": True, "submissions": 2, "best": 100},
    {"days": 9, "title": "Group Anagrams", "topic": "Hashing", "difficulty": "Medium", "solved": True, "submissions": 3, "best": 100},
    {"days": 4, "title": "Longest Increasing Subsequence", "topic": "Dynamic Programming", "difficulty": "Medium", "solved": False, "submissions": 4, "best": 60},
]


def coding_session(user_id, c):
    started = ago(c["days"], 2)
    data = {"topic": c["topic"], "difficulty": c["difficulty"], "submissions": c["submissions"], "best_pass_pct": c["best"]}
    return SandboxSession(id=str(uuid.uuid4()), user_id=user_id, type="coding", title=c["title"],
                          status="completed" if c["solved"] else "in_progress", data=json.dumps(data),
                          score=100 if c["solved"] else None, created_at=started,
                          completed_at=started + datetime.timedelta(minutes=35) if c["solved"] else None)


# ── Interviews ──────────────────────────────────────────────────────────────

INTERVIEWS = [
    {
        "days": 10, "role_type": "behavioral", "title": "Behavioral Interview", "difficulty": "entry",
        "transcript": [
            ("interviewer", "Hi, I'm Aria, and I'll be your interviewer today. To start, tell me about yourself and what draws you to backend engineering."),
            ("candidate", "I'm a final year computer engineering student. I like building APIs, I made a college event app backend in FastAPI, and I enjoy figuring out how data flows."),
            ("interviewer", "Nice. Tell me about a time you disagreed with a teammate. What happened and how did you handle it?"),
            ("candidate", "In our project someone wanted to use MongoDB and I wanted Postgres. We argued a bit and then the teacher decided."),
            ("interviewer", "Thanks. Describe a time you missed a deadline. What did you learn from it?"),
            ("candidate", "During my internship I underestimated a feature, so I told my mentor early, split the work into smaller tasks, and delivered two days late but with tests. Now I estimate in smaller pieces."),
        ],
        "feedback": {
            "overall_score": 64, "verdict": "almost",
            "summary": "Friendly and honest, with one strong, well-structured story. The conflict answer lacked your own actions and an outcome, which interviewers look for.",
            "rubric": {
                "communication": {"score": 7, "comment": "Clear and natural; a little brief in places."},
                "technical_depth": {"score": 5, "comment": "Little technical reasoning, which is fine for a behavioral round."},
                "problem_solving": {"score": 6, "comment": "Good recovery plan in the deadline story."},
                "clarity": {"score": 6, "comment": "The conflict story had no clear result."},
            },
            "per_question": [
                {"question": "Tell me about yourself and what draws you to backend engineering.", "answer_excerpt": "Final year student, built a FastAPI backend for a college event app.", "score": 7,
                 "feedback": "Good, relevant hook with a real project. Add one measurable detail about it.",
                 "model_answer": "A 30-second pitch: who you are, one project with a concrete result (users, latency, scale), and why that work excites you about backend roles specifically."},
                {"question": "Tell me about a time you disagreed with a teammate.", "answer_excerpt": "We argued about MongoDB vs Postgres; the teacher decided.", "score": 4,
                 "feedback": "Letting someone else decide doesn't show how you handle conflict. Describe what you did and how it ended.",
                 "model_answer": "Use STAR: the disagreement, how you compared both options against the project's needs (relational data, joins), how you proposed a quick spike to test, and how the team agreed. End with what you'd repeat."},
                {"question": "Describe a time you missed a deadline.", "answer_excerpt": "Told my mentor early, split the work, delivered two days late with tests.", "score": 8,
                 "feedback": "Strong: early communication, a concrete fix and a lesson learned.",
                 "model_answer": "This is already close: situation, early flagging, re-planning into smaller tasks, the outcome, and the changed habit."},
            ],
            "strengths": ["Took ownership in the deadline story and named a concrete lesson.", "Linked your interest to a real project you built."],
            "improvements": ["Use STAR for conflict questions and state your own actions and the outcome.", "Add numbers to project stories (users, response times, team size)."],
        },
    },
    {
        "days": 3, "role_type": "technical", "title": "Technical Interview", "difficulty": "entry",
        "transcript": [
            ("interviewer", "Hi, I'm Aria. Let's begin: what happens, step by step, when you type a URL into the browser and press enter?"),
            ("candidate", "The browser checks its cache, then does a DNS lookup to get the IP, opens a TCP connection and a TLS handshake for HTTPS, sends the HTTP request, the server responds, and the browser parses HTML and loads CSS and JS."),
            ("interviewer", "Good. In your FastAPI project, how would you make an endpoint that lists events fast when the table has a million rows?"),
            ("candidate", "I would add an index on the column we filter on, use pagination with a limit, and maybe cache popular queries in Redis."),
            ("interviewer", "What's the difference between a process and a thread?"),
            ("candidate", "A process has its own memory, threads share memory inside a process, so threads are lighter but you need locks."),
        ],
        "feedback": {
            "overall_score": 76, "verdict": "ready",
            "summary": "Solid fundamentals explained in a clear order. Answers were correct but stayed at the surface; one level of trade-off thinking would lift them to strong.",
            "rubric": {
                "communication": {"score": 8, "comment": "Structured, step-by-step explanations."},
                "technical_depth": {"score": 6, "comment": "Correct, but rarely went beyond the first layer."},
                "problem_solving": {"score": 7, "comment": "Sensible approach to the large-table question."},
                "clarity": {"score": 8, "comment": "Easy to follow throughout."},
            },
            "per_question": [
                {"question": "What happens when you type a URL into the browser and press enter?", "answer_excerpt": "Cache, DNS, TCP and TLS handshake, HTTP request, response, parse HTML/CSS/JS.", "score": 8,
                 "feedback": "Complete, well-ordered answer covering the key steps.",
                 "model_answer": "Add detail where you're strongest: DNS resolution order, TCP 3-way handshake, TLS certificate check, HTTP/2 reuse, then rendering (DOM, CSSOM, layout, paint)."},
                {"question": "How would you make an endpoint listing events fast with a million rows?", "answer_excerpt": "Index the filter column, paginate with a limit, cache in Redis.", "score": 7,
                 "feedback": "Right ideas. Mention keyset pagination vs OFFSET and how you'd invalidate the cache.",
                 "model_answer": "Index the filter/sort columns (composite if needed), use keyset (cursor) pagination since OFFSET gets slow on deep pages, select only needed columns, and cache hot pages with a short TTL or invalidate on writes."},
                {"question": "What's the difference between a process and a thread?", "answer_excerpt": "Process has its own memory, threads share memory, so threads are lighter but need locks.", "score": 7,
                 "feedback": "Correct core difference. Mention context-switch cost and crash isolation.",
                 "model_answer": "Processes have separate address spaces (isolation, costlier switches and IPC); threads share the process's memory (cheap communication, but need synchronization, and one crash can bring down the process). Give an example of when you'd pick each."},
            ],
            "strengths": ["Explained the URL flow in a clear, logical sequence.", "Proposed practical performance fixes (indexing, pagination, caching)."],
            "improvements": ["Go one level deeper: discuss trade-offs, e.g. keyset vs OFFSET pagination.", "Back answers with an example from your own project."],
        },
    },
]


def interview_session(user_id, iv):
    started = ago(iv["days"], 3)
    settings = {"role_type": iv["role_type"], "target_role": "Backend Engineer", "difficulty": iv["difficulty"], "num_questions": 3}
    data = {"role_type": iv["role_type"], "settings": settings,
            "transcript": [{"role": r, "content": c} for r, c in iv["transcript"]], "feedback": iv["feedback"]}
    return SandboxSession(id=str(uuid.uuid4()), user_id=user_id, type="interview", title=iv["title"], status="completed",
                          data=json.dumps(data), score=iv["feedback"]["overall_score"], created_at=started,
                          completed_at=started + datetime.timedelta(minutes=14))


# ── Profiles ────────────────────────────────────────────────────────────────

def demo_profile(name, email=None):
    return {
        "audience": "student", "name": name, "email": email, "current_status": "undergrad",
        "education_stage": "Final year B.E.", "university": "Gujarat Technological University",
        "major": "Computer Engineering", "study_year": "4th year", "target_role": "Backend Engineer",
        "career_goals": ["Land a backend engineering role through campus placements"],
        "skills": ["Python", "SQL", "FastAPI", "Data Structures", "Git"],
        "past_experience": "2-month backend internship; built a FastAPI backend for a college events app.",
        "projects": ["College events app backend (FastAPI + PostgreSQL)", "URL shortener with Redis caching"],
        "learning_style": "practical", "hours_per_week": 12, "joining_reason": "Preparing for placements in December.",
        "personal_introduction": f"I'm {name}, a final year computer engineering student preparing for backend roles.",
        "onboarding_complete": True, "profile_review_pending": False,
        "linkedin_url": "https://www.linkedin.com/in/example", "github_url": "https://github.com/example",
    }


DEMO_SKILLS = [("Python", 7), ("SQL", 6), ("FastAPI", 6), ("Data Structures", 6), ("DBMS", 6),
               ("Operating Systems", 4), ("Git", 6), ("REST APIs", 6), ("Computer Networks", 5)]


def add_skills(db, user_id, skills):
    for name, prof in skills:
        db.add(SkillNode(id=str(uuid.uuid4()), user_id=user_id, name=name, category="core", proficiency=prof,
                         evidence_type="practiced", evidence_weight=0.6))


def add_event(db, user_id, s):
    db.add(JourneyEvent(id=str(uuid.uuid4()), user_id=user_id, event_type="task_completed",
                        summary=f"Completed {s.title}" + (f" — scored {s.score}/100" if s.score is not None else ""),
                        evidence=json.dumps({"sandbox_type": s.type}), impact=json.dumps({"sandbox_session_id": s.id}),
                        event_date=(s.completed_at or s.created_at).date(), created_at=s.completed_at or s.created_at))


def opt_in(db, user_id):
    compliance.record_consent(db, user_id, compliance.TERMS, granted=True)
    compliance.record_consent(db, user_id, compliance.RECRUITER_VISIBILITY, granted=True)


def seed_user(db, user_id, name):
    if db.query(SandboxSession).filter(SandboxSession.user_id == user_id).count():
        print(f"  {user_id} already has sandbox sessions; run --clear first to reseed. Skipping.")
        return
    user = db.query(User).filter(User.id == user_id).first()
    profile = demo_profile(name)
    if not user:
        user = User(id=user_id, name=name)
        db.add(user)
    user.name, user.target_role, user.current_role = name, "Backend Engineer", "Student"
    user.hours_per_week, user.learning_style = 12, "practical"
    existing = json.loads(user.profile_data) if user.profile_data else {}
    user.profile_data = json.dumps({**profile, **{k: v for k, v in existing.items() if k in ("email",) and v}})
    db.commit()
    add_skills(db, user_id, DEMO_SKILLS)
    sessions = [theory_session(user_id, t) for t in TESTS] + [coding_session(user_id, c) for c in CODING] + \
               [interview_session(user_id, iv) for iv in INTERVIEWS]
    for s in sessions:
        db.add(s)
        add_event(db, user_id, s)
    db.commit()
    opt_in(db, user_id)
    print(f"  seeded {name}: {len(sessions)} sessions, {len(DEMO_SKILLS)} skills, consent + recruiter visibility on")


CANDIDATES = [
    ("Ananya Iyer", "Backend Engineer", "IIIT Vadodara", [("Python", 8), ("SQL", 8), ("System Design", 6), ("FastAPI", 7)], 88, 92, 84),
    ("Rohan Patel", "Backend Engineer", "Nirma University", [("Java", 7), ("SQL", 6), ("Spring Boot", 6)], 72, 80, 66),
    ("Sneha Kulkarni", "Data Analyst", "Pune University", [("SQL", 8), ("Python", 6), ("Power BI", 7), ("Statistics", 7)], 81, None, 74),
    ("Kabir Singh", "Frontend Developer", "LD College of Engineering", [("React", 8), ("JavaScript", 8), ("CSS", 7)], 69, 75, 71),
    ("Meera Shah", "Backend Engineer", "DAIICT", [("Go", 6), ("Python", 7), ("PostgreSQL", 7), ("Docker", 6)], 77, 100, 80),
    # Non-tech fields: Delta works for every career, not just software.
    ("Priya Nair", "Staff Nurse", "Government College of Nursing, Ahmedabad",
     [("Patient Care", 8), ("Clinical Knowledge", 7), ("Infection Control", 7), ("Documentation", 6)], 84, None, 79),
    ("Arjun Desai", "Chartered Accountant", "Gujarat University (B.Com)",
     [("Accounting", 8), ("Taxation", 7), ("Audit", 7), ("Excel", 8)], 79, None, 72),
]

# Degree / stream shown for each candidate (defaults to the demo student's).
CANDIDATE_MAJORS = {"Staff Nurse": ("B.Sc Nursing", "Final year B.Sc Nursing"),
                    "Chartered Accountant": ("Commerce", "CA Intermediate, articleship")}


def seed_candidates(db):
    for uid, (name, role, uni, skills, theory, coding, interview) in zip(CANDIDATE_IDS, CANDIDATES):
        if db.query(User).filter(User.id == uid).first():
            print(f"  {uid} exists, skipping")
            continue
        p = demo_profile(name, email=f"{uid}@example.com")
        p.update({"target_role": role, "university": uni, "skills": [s for s, _ in skills], "demo": True,
                  "personal_introduction": f"I'm {name}, aiming for {role} roles."})
        if role in CANDIDATE_MAJORS:
            p["major"], p["education_stage"] = CANDIDATE_MAJORS[role]
            p["projects"], p["past_experience"] = [], f"Internship experience relevant to {role} roles."
        db.add(User(id=uid, name=name, email=f"{uid}@example.com", target_role=role, profile_data=json.dumps(p)))
        db.commit()
        add_skills(db, uid, skills)
        topic = skills[0][0]
        correct = round(theory / 20)
        db.add(SandboxSession(
            id=str(uuid.uuid4()), user_id=uid, type="theory", title=f"Theory Test: {topic}", status="completed", score=theory,
            data=json.dumps({"topic": topic, "category": "technical", "difficulty": "medium",
                             "result": {"score": theory, "correct": correct, "total": 5, "questions": [],
                                        "skill_breakdown": {topic: {"correct": correct, "total": 5}}}}),
            created_at=ago(6), completed_at=ago(6)))
        if coding is not None:
            db.add(SandboxSession(id=str(uuid.uuid4()), user_id=uid, type="coding", title="Two Sum",
                                  status="completed" if coding == 100 else "in_progress", score=100 if coding == 100 else None,
                                  data=json.dumps({"topic": "Arrays", "difficulty": "Easy", "submissions": 2, "best_pass_pct": coding}),
                                  created_at=ago(5), completed_at=ago(5) if coding == 100 else None))
        r = max(3, min(10, round(interview / 10)))
        db.add(SandboxSession(
            id=str(uuid.uuid4()), user_id=uid, type="interview", title="Technical Interview" if coding is not None else "Role Knowledge Interview", status="completed", score=interview,
            data=json.dumps({"role_type": "technical", "transcript": [],
                             "settings": {"role_type": "technical", "target_role": role, "difficulty": "entry", "num_questions": 3},
                             "feedback": {"overall_score": interview, "verdict": "ready" if interview >= 70 else "almost", "summary": "",
                                          "rubric": {k: {"score": r, "comment": ""} for k in ("communication", "technical_depth", "problem_solving", "clarity")},
                                          "per_question": [], "strengths": [], "improvements": []}}),
            created_at=ago(3), completed_at=ago(3)))
        db.commit()
        opt_in(db, uid)
        print(f"  candidate {name} ({uid})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user-id")
    ap.add_argument("--name", default="Aarav Mehta", help="display name for the demo student")
    ap.add_argument("--with-candidates", action="store_true")
    ap.add_argument("--approve-recruiter-id")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm writing to the database shown")
    args = ap.parse_args()

    print(f"Database: {engine.url.render_as_string(hide_password=True)}")
    if not args.yes:
        print("Nothing written. Re-run with --yes to confirm this is the right database.")
        return
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.clear:
            for uid in CANDIDATE_IDS:
                if db.query(User).filter(User.id == uid).first():
                    compliance.erase_student(db, uid)
            if args.user_id:
                compliance.erase_student(db, args.user_id)
            print("Cleared demo data.")
            return
        if args.user_id:
            seed_user(db, args.user_id, args.name)
        if args.with_candidates:
            seed_candidates(db)
        if args.approve_recruiter_id:
            rec = db.query(Recruiter).filter(Recruiter.id == args.approve_recruiter_id).first()
            if not rec:
                print("  No recruiter with that id. Register at /recruiter/login first.")
            else:
                rec.status, rec.reviewed_at = "approved", NOW
                db.commit()
                print(f"  approved recruiter {rec.company}")
        if not (args.user_id or args.with_candidates or args.approve_recruiter_id):
            ap.print_help()
    finally:
        db.close()


if __name__ == "__main__":
    main()
