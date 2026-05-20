"""Competitive opportunities calendar service — dynamically generates Indian & global student tech events."""
import datetime
import random

def generate_upcoming_events(user_skills: list, days_ahead: int = 30) -> list:
    """
    Generates a schedule of upcoming coding sprints, hackathons, and ML competitions.
    Calculates dates dynamically relative to the current day to ensure a live, active feed.
    """
    today = datetime.datetime.now()
    events = []
    
    user_skills_lower = {s.lower() for s in user_skills}

    # Helper to format dates
    def get_future_date(days: int, hour: int = 10, minute: int = 0):
        target_date = today + datetime.timedelta(days=days)
        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()

    # 1. LeetCode contests (Every Sunday Weekly, Every Second Saturday Biweekly)
    for i in range(days_ahead):
        target_day = today + datetime.timedelta(days=i)
        
        # Sundays: LeetCode Weekly Contest
        if target_day.weekday() == 6: # Sunday
            events.append({
                "id": f"leetcode-weekly-{target_day.strftime('%Y%m%d')}",
                "title": f"LeetCode Weekly Contest {380 + i}",
                "platform": "LeetCode",
                "type": "competitive_programming",
                "difficulty": "Medium",
                "start_date": target_day.replace(hour=8, minute=0, second=0, microsecond=0).isoformat(),
                "end_date": target_day.replace(hour=9, minute=30, second=0, microsecond=0).isoformat(),
                "registration_url": "https://leetcode.com/contest/",
                "rewards": "LeetCode Coins, Premium Badges, Global CP Ranking Profile",
                "recommended_skills": ["Data Structures", "Algorithms", "Python", "C++"],
                "description": "The weekly global benchmark for algorithmic problem solving. Solve 4 complex problems in 90 minutes."
            })
            
        # Saturdays (Every alternate Saturday): LeetCode Biweekly Contest
        if target_day.weekday() == 5 and (target_day.day % 2 == 0): # Saturday
            events.append({
                "id": f"leetcode-biweekly-{target_day.strftime('%Y%m%d')}",
                "title": f"LeetCode Biweekly Contest {120 + i}",
                "platform": "LeetCode",
                "type": "competitive_programming",
                "difficulty": "Medium",
                "start_date": target_day.replace(hour=20, minute=0, second=0, microsecond=0).isoformat(),
                "end_date": target_day.replace(hour=21, minute=30, second=0, microsecond=0).isoformat(),
                "registration_url": "https://leetcode.com/contest/",
                "rewards": "LeetCode Coins, Global CP Rating Increase",
                "recommended_skills": ["Algorithms", "Data Structures", "Java", "Python"],
                "description": "Global biweekly coding sprint. Solve 4 programming challenges in 90 minutes."
            })

    # 2. Codeforces Rounds (Dynamically generated every 4-5 days)
    cf_schedules = [3, 8, 12, 17, 22, 28]
    for idx, days in enumerate(cf_schedules):
        div_num = 2 if idx % 2 == 0 else 3
        events.append({
            "id": f"codeforces-round-{idx}",
            "title": f"Codeforces Round {950 + idx} (Div. {div_num})",
            "platform": "Codeforces",
            "type": "competitive_programming",
            "difficulty": "Hard" if div_num == 2 else "Medium",
            "start_date": get_future_date(days, hour=20, minute=5),
            "end_date": get_future_date(days, hour=22, minute=5),
            "registration_url": "https://codeforces.com/contests",
            "rewards": "Global Rating Badges, Specialist/Expert Titles",
            "recommended_skills": ["Algorithms", "Number Theory", "Dynamic Programming", "C++"],
            "description": "Highly competitive, mathematical algorithmic contest. Direct rating boost for Division solvers."
        })

    # 3. Unstop Hackathons (Targeted specifically for Indian Engineering Students)
    # A few premium hackathons occurring at fixed days ahead
    events.append({
        "id": "unstop-flipkart-grid",
        "title": "Flipkart GRiD 8.0 - Software Development Track",
        "platform": "Unstop",
        "type": "hackathon",
        "difficulty": "Hard",
        "start_date": get_future_date(5, hour=10, minute=0),
        "end_date": get_future_date(12, hour=18, minute=0),
        "registration_url": "https://unstop.com/",
        "rewards": "₹3,00,000 INR Cash Prize & Direct PPI Interview Calls for Software Engineer Intern roles at Flipkart",
        "recommended_skills": ["FastAPI", "SQL", "Docker", "System Design", "React"],
        "description": "Flipkart's flagship national engineering challenge. Compete against top CS minds in India across quiz, online code sprint, and full-stack prototype presentation."
    })

    events.append({
        "id": "unstop-google-girl",
        "title": "Google Girl Hackathon 2026",
        "platform": "Unstop",
        "type": "hackathon",
        "difficulty": "Hard",
        "start_date": get_future_date(14, hour=9, minute=0),
        "end_date": get_future_date(20, hour=21, minute=0),
        "registration_url": "https://unstop.com/",
        "rewards": "Direct placement interview loops at Google India & Cool Google Tech Goodies",
        "recommended_skills": ["Algorithms", "Data Structures", "System Design", "Python"],
        "description": "A national coding competition designed to encourage and provide female engineering students in India an avenue to showcase their technical prowess."
    })

    events.append({
        "id": "unstop-tata-imagination",
        "title": "Tata Imagination Challenge 2026",
        "platform": "Unstop",
        "type": "hackathon",
        "difficulty": "Medium",
        "start_date": get_future_date(21, hour=12, minute=0),
        "end_date": get_future_date(25, hour=18, minute=0),
        "registration_url": "https://unstop.com/",
        "rewards": "₹2,00,000 INR Cash Prize & Direct entry into Tata Administrative Services (TAS) internship track",
        "recommended_skills": ["Python", "Product Management", "System Design"],
        "description": "National level product design and technological implementation challenge testing innovative solutions for real-world industries."
    })

    # 4. Kaggle Sprints (ML Ops / AI Engineering focus)
    events.append({
        "id": "kaggle-tabular-playground",
        "title": "Kaggle Tabular Playground Series - May 2026",
        "platform": "Kaggle",
        "type": "ml_sprint",
        "difficulty": "Medium",
        "start_date": get_future_date(1, hour=0, minute=0),
        "end_date": get_future_date(15, hour=23, minute=59),
        "registration_url": "https://www.kaggle.com/competitions",
        "rewards": "Kaggle Swag, Ranking points, Contribution Medals",
        "recommended_skills": ["Python", "LLMs", "MLOps", "Pandas", "Scikit-Learn"],
        "description": "Monthly machine learning competition designed to build core data modeling, model architecture, and embeddings parsing confidence."
    })

    events.append({
        "id": "kaggle-ai-agents",
        "title": "Kaggle AI Agent Optimization Challenge",
        "platform": "Kaggle",
        "type": "ml_sprint",
        "difficulty": "Hard",
        "start_date": get_future_date(10, hour=10, minute=0),
        "end_date": get_future_date(29, hour=23, minute=59),
        "registration_url": "https://www.kaggle.com/competitions",
        "rewards": "$15,000 USD Prize Pool & Global AI Ranking Badges",
        "recommended_skills": ["LLMs", "Vector Databases", "Python", "Docker", "RAG Pipelines"],
        "description": "Design an autonomous coding agent capable of resolving complex software bugs. Test embeddings recall and context-size efficiency."
    })

    # Sort events by start date
    events.sort(key=lambda x: x["start_date"])

    # Score alignments: Add an dynamic match percentage based on user's active skills
    for ev in events:
        reqs = ev["recommended_skills"]
        matches = [r for r in reqs if r.lower() in user_skills_lower]
        match_ratio = len(matches) / max(len(reqs), 1)
        ev["match_percentage"] = int(match_ratio * 100)
        ev["matching_skills"] = matches
        
        # High matching events get recommended tag
        ev["recommended"] = ev["match_percentage"] >= 50

    return events
