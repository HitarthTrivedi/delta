"""Predefined role roadmaps, as data (human-written; no AI at runtime).

Adding or changing a roadmap is a data change here, not a code change.
`roadmap_templates.validate()` checks every template in the test suite.

Shape:
  template: id, version, title, summary, weeks, fields ([] = any field),
            programs (college programs it suits), breaks (template weeks),
            then (optional template to hand over to when this one ends),
            note (optional caveat shown with the outline), phases.
  phase:    id, name, goal, weeks [first, last], gate (optional), milestones.
  gate:     topic (a Practice > Tests topic), min_score, max_hold_weeks.
            If the learner hasn't scored min_score on that topic by the end of
            the phase, the plan holds for up to max_hold_weeks, then moves on.
  milestone: id ("tpl-..."), title, skill, detail, kind, url (external) or
            link (inside Delta), optional, skip (skippable once the skill is
            proven in a test, never on a self-claimed skill).

⚠ Verify before each placement season: company test patterns (TCS NQT,
Infosys, Wipro, Accenture) change year to year. Templates marked
`verify=True` need a human check of those milestones. Delta is not affiliated
with any company named here; names describe the hiring process a plan
prepares for.
"""
from __future__ import annotations


def _m(mid: str, title: str, skill: str, detail: str, *, kind: str = "practice", url: str | None = None,
       link: str | None = None, optional: bool = False, skip: bool = True) -> dict:
    return {"id": mid, "title": title, "skill": skill, "detail": detail, "kind": kind, "url": url,
            "link": link, "optional": optional, "skip": skip}


def _test(mid: str, topic: str, detail: str) -> dict:
    return _m(mid, f"Take a {topic} test", topic, detail, kind="test",
              link=f"/practice/theory?topic={topic.replace(' ', '%20')}", skip=False)


NEETCODE = "https://neetcode.io/roadmap"
LEETCODE_EXPLORE = "https://leetcode.com/explore/"
CP_ALGORITHMS = "https://cp-algorithms.com/"
INDIABIX = "https://www.indiabix.com/"
SQLBOLT = "https://sqlbolt.com/"
POSTGRES_TUTORIAL = "https://www.postgresql.org/docs/current/tutorial.html"
OSTEP = "https://pages.cs.wisc.edu/~remzi/OSTEP/"
PYTHON_TUTORIAL = "https://docs.python.org/3/tutorial/"
GIT_BOOK = "https://git-scm.com/book/en/v2"
MDN_LEARN = "https://developer.mozilla.org/en-US/docs/Learn"
CS50 = "https://cs50.harvard.edu/x/"
SYSTEM_DESIGN_PRIMER = "https://github.com/donnemartin/system-design-primer"
GOOGLE_HOW_WE_HIRE = "https://www.google.com/about/careers/applications/how-we-hire/"
KAGGLE_LEARN = "https://www.kaggle.com/learn"
POWER_BI_LEARN = "https://learn.microsoft.com/en-us/training/powerplatform/power-bi"
TABLEAU_PUBLIC = "https://public.tableau.com/"
PANDAS_GUIDE = "https://pandas.pydata.org/docs/user_guide/index.html"
CODEFORCES = "https://codeforces.com/"
LEETCODE_CONTESTS = "https://leetcode.com/contest/"
GITHUB_FIRST_CONTRIBUTION = "https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project"

INTERVIEW = "/practice/interview"
CODING = "/practice/coding"


PLACEMENT_6M = {
    "id": "placement_6m", "version": 1, "verify": True,
    "title": "Placement-ready in 6 months",
    "summary": "For final-year students: aptitude, DSA, CS fundamentals and company-style mocks for campus placements, "
               "with tracks for service and product companies.",
    "weeks": 26, "fields": [], "programs": ["placement_6m"], "breaks": [],
    "note": "Company test patterns change every season; your placement cell's latest pattern wins over this plan.",
    "phases": [
        {"id": "p6-foundations", "name": "Foundations and a baseline", "weeks": [1, 4],
         "goal": "Find where you stand and rebuild the basics every placement test checks.", "milestones": [
            _test("tpl-p6-baseline-aptitude", "Quantitative Aptitude", "A baseline so the plan knows what to skip and what to revise."),
            _m("tpl-p6-quant-basics", "Revise percentages, ratios, profit and loss", "Quantitative Aptitude",
               "Do 30 timed questions across these three topics and note the formulas you had to look up.", url=INDIABIX),
            _m("tpl-p6-logical-basics", "Practise logical reasoning sets", "Logical Reasoning",
               "Do 25 questions on series, coding-decoding, blood relations and seating arrangements.", url=INDIABIX),
            _m("tpl-p6-language", "Pick one language and revise it end to end", "Programming",
               "C++, Java or Python: syntax, loops, functions, arrays, strings and time complexity. Write 5 small programs.",
               skip=False),
            _m("tpl-p6-arrays-strings", "Solve 15 array and string problems", "Arrays",
               "Easy to medium. Write the time and space complexity next to each solution.", url=NEETCODE),
            _m("tpl-p6-verbal", "Practise reading comprehension and sentence correction", "Verbal Ability",
               "20 questions, timed. Note the error types you miss most.", url=INDIABIX),
            _m("tpl-p6-resume-v1", "Write version 1 of your resume", "Resume",
               "One page: education, 2 projects with what you built and the result, skills you can be tested on.",
               kind="career", link="/resume", skip=False),
        ]},
        {"id": "p6-core-dsa", "name": "Core data structures and algorithms", "weeks": [5, 10],
         "goal": "The patterns that most campus coding rounds draw from.",
         "gate": {"topic": "Data Structures", "min_score": 60, "max_hold_weeks": 1}, "milestones": [
            _m("tpl-p6-hashing", "Solve 8 hashing problems", "Hashing", "Frequency counts, two-sum style lookups, grouping.", url=NEETCODE),
            _m("tpl-p6-two-pointers", "Solve 8 two-pointer and sliding-window problems", "Two Pointers",
               "Include at least 3 sliding-window problems with a variable window.", url=NEETCODE),
            _m("tpl-p6-recursion", "Practise recursion and backtracking", "Recursion",
               "Subsets, permutations and one N-Queens style problem. Draw the recursion tree for one of them.", url=NEETCODE),
            _m("tpl-p6-linked-lists", "Solve linked list, stack and queue problems", "Linked Lists",
               "Reverse, merge, detect a cycle; valid parentheses; next greater element.", url=NEETCODE),
            _m("tpl-p6-binary-search", "Practise sorting and binary search", "Binary Search",
               "Know merge sort and quick sort by heart; solve 6 binary-search problems including search on the answer.",
               url=NEETCODE),
            _m("tpl-p6-trees", "Solve tree and BST problems", "Trees",
               "Traversals, height, lowest common ancestor, validate a BST, level order.", url=NEETCODE),
            _test("tpl-p6-dsa-test", "Data Structures", "Checks this phase. Score 60 or more to move on."),
        ]},
        {"id": "p6-cs-fundamentals", "name": "CS fundamentals", "weeks": [11, 15],
         "goal": "OOP, DBMS, SQL, operating systems and networks: the technical interview basics.",
         "gate": {"topic": "DBMS", "min_score": 60, "max_hold_weeks": 1}, "milestones": [
            _m("tpl-p6-oop", "Explain the four pillars of OOP with your own code", "OOP",
               "Encapsulation, inheritance, polymorphism, abstraction, with one class design you can explain aloud."),
            _m("tpl-p6-dbms", "Revise DBMS: keys, normalisation, transactions, indexing", "DBMS",
               "Be able to normalise a table to 3NF and explain ACID with an example.", url=POSTGRES_TUTORIAL),
            _m("tpl-p6-sql", "Write 30 SQL queries", "SQL", "Joins, GROUP BY with HAVING, subqueries, window functions basics.",
               url=SQLBOLT),
            _m("tpl-p6-os", "Revise operating systems", "Operating Systems",
               "Processes vs threads, scheduling, deadlock conditions, paging and virtual memory.", url=OSTEP),
            _m("tpl-p6-cn", "Revise computer networks", "Computer Networks",
               "OSI and TCP/IP layers, TCP vs UDP, what happens when you type a URL, DNS, HTTP status codes."),
            _test("tpl-p6-dbms-test", "DBMS", "Checks this phase. Score 60 or more to move on."),
        ]},
        {"id": "p6-advanced", "name": "Advanced DSA and a project you can defend", "weeks": [16, 20],
         "goal": "The harder rounds at product companies, and a project interviewers can dig into.", "milestones": [
            _m("tpl-p6-graphs", "Solve BFS and DFS graph problems", "Graphs", "Islands, shortest path in a grid, cycle detection.",
               url=NEETCODE),
            _m("tpl-p6-dp", "Solve 10 dynamic programming problems", "Dynamic Programming",
               "1D (climbing stairs, house robber) then 2D (LCS, knapsack). Write the recurrence first.", url=NEETCODE),
            _m("tpl-p6-heaps", "Practise heaps and greedy problems", "Heaps", "Top K, merge K lists, interval scheduling.",
               url=NEETCODE, optional=True),
            _m("tpl-p6-project", "Polish one project for interviews", "Projects",
               "Clean README, a live link or demo video, and three decisions you can explain with trade-offs.", kind="project",
               skip=False),
            _m("tpl-p6-timed-coding", "Do a timed coding round", "Problem Solving",
               "Two medium problems in 60 minutes in the coding sandbox, no hints.", link=CODING, skip=False),
        ]},
        {"id": "p6-company-mocks", "name": "Company-style tests and interviews", "weeks": [21, 24],
         "goal": "Rehearse the actual formats you will face.", "milestones": [
            _m("tpl-p6-mock-tcs", "Take a TCS NQT-style mock", "Company Tests",
               "Numerical ability, verbal, reasoning and a coding section under time. Check your placement cell for this "
               "season's pattern.", kind="test", skip=False),
            _m("tpl-p6-mock-infosys", "Take an Infosys-style mock", "Company Tests",
               "Aptitude, logical reasoning, verbal and pseudo-code questions, timed.", kind="test", skip=False),
            _m("tpl-p6-mock-wipro-accenture", "Take a Wipro or Accenture-style mock", "Company Tests",
               "Cognitive and technical assessment plus coding; practise a short written communication task too.",
               kind="test", skip=False),
            _m("tpl-p6-tech-interview", "Do an AI mock technical interview", "Technical Interview",
               "Explain one project and two DSA solutions aloud. Read the feedback and redo your weakest answer.",
               kind="interview", link=INTERVIEW, skip=False),
            _m("tpl-p6-hr-interview", "Do an AI mock HR interview", "HR Interview",
               "Tell me about yourself, strengths, a failure, why this company. Keep each answer under 2 minutes.",
               kind="interview", link=INTERVIEW, skip=False),
            _m("tpl-p6-resume-final", "Finalise your resume", "Resume",
               "Add numbers to every bullet, cut anything you can't defend in an interview.", kind="career", link="/resume",
               skip=False),
        ]},
        {"id": "p6-final", "name": "Final revision", "weeks": [25, 26],
         "goal": "Sharpen, rest well, and walk in prepared.", "milestones": [
            _m("tpl-p6-full-mock", "Take two full-length mocks", "Company Tests",
               "One service-company style, one product-company style. Review every wrong answer.", kind="test", skip=False),
            _m("tpl-p6-company-research", "Research the companies coming to campus", "Interview Prep",
               "For each: what they build, the role, the test pattern, and two questions you will ask them.", kind="career",
               skip=False),
        ]},
    ],
}


def _dsa_track(prefix: str) -> list[dict]:
    """The core DSA order shared by the 12-month product-company plans."""
    return [
        _m(f"tpl-{prefix}-complexity", "Master Big-O and your interview language", "Programming",
           "Pick one language for interviews and know its standard library collections by heart.", skip=False),
        _m(f"tpl-{prefix}-arrays", "Solve 20 array and hashing problems", "Arrays", "Easy then medium; time yourself.", url=NEETCODE),
        _m(f"tpl-{prefix}-two-pointers", "Solve 12 two-pointer and sliding-window problems", "Two Pointers", "Pairs in sorted arrays, partitioning, and fixed and variable windows.", url=NEETCODE),
        _m(f"tpl-{prefix}-stack", "Solve 10 stack problems", "Stacks", "Including monotonic stack.", url=NEETCODE),
        _m(f"tpl-{prefix}-binary-search", "Solve 10 binary search problems", "Binary Search",
           "Including search on the answer space.", url=NEETCODE),
        _m(f"tpl-{prefix}-linked-list", "Solve 10 linked list problems", "Linked Lists", "Reverse, merge, cycle detection, and the fast/slow pointer trick.", url=NEETCODE),
        _m(f"tpl-{prefix}-trees", "Solve 15 tree problems", "Trees", "DFS and BFS, BST operations, serialisation.", url=NEETCODE),
        _m(f"tpl-{prefix}-heaps", "Solve 8 heap and priority-queue problems", "Heaps", "Top K elements, merge K sorted lists, running median.", url=NEETCODE),
        _m(f"tpl-{prefix}-backtracking", "Solve 8 backtracking problems", "Recursion", "Subsets, permutations, combination sum; draw the recursion tree for one.", url=NEETCODE),
        _m(f"tpl-{prefix}-graphs", "Solve 12 graph problems", "Graphs",
           "BFS, DFS, topological sort, union-find, Dijkstra.", url=CP_ALGORITHMS),
        _test(f"tpl-{prefix}-dsa-test", "Data Structures", "Checks the core patterns before the harder phase."),
    ]


SWE_GOOGLE_12M = {
    "id": "swe_google_12m", "version": 1,
    "title": "Software engineer at Google-style companies in 12 months",
    "summary": "For students and early-career engineers aiming at Google or companies with a similar interview loop: "
               "deep DSA, contests, interviews written in a plain doc, and behavioural stories.",
    "weeks": 52, "fields": ["cs_ai"], "programs": [], "breaks": [13, 26, 39],
    "note": "Covers entry-level loops (coding rounds plus a behavioural round); senior loops add system design. "
            "Not affiliated with Google.",
    "phases": [
        {"id": "g-foundations", "name": "Foundations", "weeks": [1, 12],
         "goal": "One interview language, complexity, and the first DSA patterns.",
         "milestones": _dsa_track("g")[:6]},
        {"id": "g-core", "name": "Core patterns", "weeks": [13, 24],
         "goal": "Trees, heaps, backtracking and graphs until they feel routine.",
         "gate": {"topic": "Data Structures", "min_score": 70, "max_hold_weeks": 2},
         "milestones": _dsa_track("g")[6:] + [
            _m("tpl-g-first-contest", "Take part in a weekly contest", "Competitive Programming",
               "LeetCode weekly or Codeforces Div. 3. Upsolve one problem you couldn't finish.", url=LEETCODE_CONTESTS),
        ]},
        {"id": "g-advanced", "name": "Advanced topics", "weeks": [25, 36],
         "goal": "The problems that separate a pass from a strong hire.", "milestones": [
            _m("tpl-g-dp-1d", "Solve 12 one-dimensional DP problems", "Dynamic Programming",
               "Write the state and recurrence before coding.", url=NEETCODE),
            _m("tpl-g-dp-2d", "Solve 12 two-dimensional DP problems", "Dynamic Programming",
               "Grids, strings (LCS, edit distance), knapsack.", url=NEETCODE),
            _m("tpl-g-greedy-intervals", "Solve 10 greedy and interval problems", "Greedy", "Merge intervals, meeting rooms, jump game; say why the greedy choice is safe.", url=NEETCODE),
            _m("tpl-g-tries", "Solve 6 trie problems", "Tries", "Implement a trie, then word search and autocomplete problems.", url=NEETCODE),
            _m("tpl-g-advanced-graphs", "Solve 8 advanced graph problems", "Graphs",
               "Shortest paths, minimum spanning tree, strongly connected components.", url=CP_ALGORITHMS),
            _m("tpl-g-contests", "Do 4 contests and upsolve each", "Competitive Programming", "Treat each as a timed round; afterwards upsolve the first problem you missed.", url=CODEFORCES,
               skip=False),
            _m("tpl-g-math-bits", "Practise math and bit manipulation problems", "Math", "GCD, modular arithmetic, bit tricks (XOR, masks).", url=NEETCODE, optional=True),
        ]},
        {"id": "g-simulation", "name": "Interview simulation", "weeks": [37, 46],
         "goal": "Perform under interview conditions, out loud, without an IDE.", "milestones": [
            _m("tpl-g-plain-doc", "Solve 10 problems in a plain doc", "Problem Solving",
               "No autocomplete, no running the code. Talk through the approach first, then write clean code and test it "
               "by hand.", skip=False),
            _m("tpl-g-45min", "Do 6 timed 45-minute sessions", "Problem Solving",
               "One medium-hard problem each: clarify, brute force, optimise, code, test.", link=CODING, skip=False),
            _m("tpl-g-ai-mock", "Do 3 AI mock technical interviews", "Technical Interview",
               "Focus on explaining trade-offs; redo your lowest-scoring area.", kind="interview", link=INTERVIEW, skip=False),
            _m("tpl-g-peer-mock", "Do 2 mock interviews with a peer", "Technical Interview",
               "Swap roles; the interviewer writes feedback on communication, not just correctness.", kind="interview",
               skip=False),
            _m("tpl-g-behavioural", "Write 6 behavioural stories", "Behavioural",
               "Leadership, conflict, failure, ambiguity, helping others, a decision with data. STAR format, under 2 "
               "minutes each.", kind="career", skip=False),
            _m("tpl-g-behavioural-mock", "Do an AI mock behavioural interview", "Behavioural",
               "Use your stories; tighten the ones that ran long.", kind="interview", link=INTERVIEW, skip=False),
        ]},
        {"id": "g-apply", "name": "Applications and the loop", "weeks": [47, 52],
         "goal": "Get the interview and walk in ready.", "milestones": [
            _m("tpl-g-resume", "Rewrite your resume for impact", "Resume",
               "Every bullet: what you did, how, and a measurable result.", kind="career", link="/resume", skip=False),
            _m("tpl-g-process", "Read how the hiring process works", "Interview Prep",
               "Know the stages so nothing surprises you.", kind="career", url=GOOGLE_HOW_WE_HIRE, skip=False),
            _m("tpl-g-referrals", "Ask for referrals", "Career",
               "Reach out to 5 engineers with a short note and your resume; apply on the careers site either way.",
               kind="career", skip=False),
            _m("tpl-g-oa", "Practise online assessments", "Problem Solving",
               "Two 90-minute sessions with two problems each, as a mock online assessment.", link=CODING, skip=False),
            _m("tpl-g-final-revision", "Revise your weakest 3 patterns", "Problem Solving",
               "Pick them from your Test Center; solve 5 problems each.", link="/practice", skip=False),
        ]},
    ],
}

PRODUCT_SDE_12M = {
    "id": "product_sde_12m", "version": 1,
    "title": "SDE at a product company in 12 months",
    "summary": "DSA plus real development: a full-stack project, low-level design and interview practice for product "
               "companies and startups.",
    "weeks": 52, "fields": ["cs_ai"], "programs": [], "breaks": [13, 26, 39],
    "phases": [
        {"id": "sde-foundations", "name": "Foundations", "weeks": [1, 8],
         "goal": "Language, complexity, Git and the first DSA patterns.",
         "milestones": _dsa_track("sde")[:4] + [
            _m("tpl-sde-git", "Learn Git properly", "Git", "Branches, rebase vs merge, pull requests.", url=GIT_BOOK),
        ]},
        {"id": "sde-dsa", "name": "Core DSA", "weeks": [9, 20],
         "goal": "The patterns product-company rounds expect.",
         "gate": {"topic": "Data Structures", "min_score": 65, "max_hold_weeks": 1},
         "milestones": _dsa_track("sde")[4:]},
        {"id": "sde-build", "name": "Build a real project", "weeks": [21, 30],
         "goal": "A deployed project with an API and a database that you can defend.", "milestones": [
            _m("tpl-sde-web-basics", "Learn the web basics", "Web Development", "HTTP, REST, HTML/CSS/JS fundamentals.",
               url=MDN_LEARN),
            _m("tpl-sde-api", "Build a REST API with a database", "Backend",
               "Auth, CRUD, validation, pagination; SQL with proper indexes.", kind="project", skip=False),
            _m("tpl-sde-frontend", "Build a frontend for it", "Frontend", "Forms, lists, error and loading states.",
               kind="project", skip=False),
            _m("tpl-sde-deploy", "Deploy it and write the README", "Deployment",
               "A live link, setup steps, and the three decisions you made with trade-offs.", kind="project", skip=False),
            _m("tpl-sde-sql", "Write 25 SQL queries", "SQL", "Joins, aggregates, window functions.", url=SQLBOLT),
        ]},
        {"id": "sde-advanced", "name": "Advanced DSA and design", "weeks": [31, 40],
         "goal": "Harder problems and object-oriented design rounds.", "milestones": [
            _m("tpl-sde-dp", "Solve 15 dynamic programming problems", "Dynamic Programming", "Write the state and recurrence first; 1D, then grids and strings.", url=NEETCODE),
            _m("tpl-sde-greedy", "Solve 8 greedy and interval problems", "Greedy", "Intervals and scheduling; explain why the greedy choice is safe.", url=NEETCODE),
            _m("tpl-sde-oop-design", "Learn the common design patterns", "Low-Level Design",
               "Strategy, factory, observer, singleton: when each helps and when it hurts."),
            _m("tpl-sde-lld", "Design 3 classic low-level systems", "Low-Level Design",
               "Parking lot, library system, rate limiter: classes, relationships, and one tricky edge case each.",
               kind="project", skip=False),
            _m("tpl-sde-system-basics", "Learn system design basics", "System Design",
               "Caching, load balancing, databases vs queues: enough to discuss your own project at scale.",
               url=SYSTEM_DESIGN_PRIMER, optional=True),
        ]},
        {"id": "sde-interviews", "name": "Interview preparation", "weeks": [41, 48],
         "goal": "Online assessments, technical and behavioural rounds.", "milestones": [
            _m("tpl-sde-oa", "Practise 4 online assessments", "Problem Solving", "Two problems in 90 minutes each.",
               link=CODING, skip=False),
            _m("tpl-sde-ai-mock", "Do 3 AI mock technical interviews", "Technical Interview", "Explain trade-offs aloud; redo your lowest-scoring area each time.", kind="interview",
               link=INTERVIEW, skip=False),
            _m("tpl-sde-project-deep-dive", "Rehearse a 10-minute project deep dive", "Projects",
               "Architecture, the hardest bug, what you'd change. Record yourself once.", kind="interview", skip=False),
            _m("tpl-sde-behavioural", "Write 5 behavioural stories", "Behavioural", "STAR format, under 2 minutes each.",
               kind="career", skip=False),
        ]},
        {"id": "sde-apply", "name": "Apply", "weeks": [49, 52],
         "goal": "Turn the preparation into interviews.", "milestones": [
            _m("tpl-sde-resume", "Finalise your resume", "Resume", "Numbers on every bullet; link the deployed project.",
               kind="career", link="/resume", skip=False),
            _m("tpl-sde-applications", "Apply to 15 roles and ask for 5 referrals", "Career",
               "Track each application and follow up after a week.", kind="career", link="/opportunities", skip=False),
        ]},
    ],
}

DATA_ANALYST_6M = {
    "id": "data_analyst_6m", "version": 1,
    "title": "Data analyst in 6 months",
    "summary": "Excel, statistics, SQL, Python and dashboards, ending with a portfolio of case studies and interview "
               "practice.",
    "weeks": 26, "fields": ["data", "business", "finance", "marketing", "general"], "programs": ["placement_6m"],
    "breaks": [],
    "phases": [
        {"id": "da-excel-stats", "name": "Spreadsheets and statistics", "weeks": [1, 5],
         "goal": "The everyday tools of an analyst.", "milestones": [
            _m("tpl-da-excel", "Master spreadsheet essentials", "Excel",
               "Lookups (XLOOKUP/VLOOKUP), pivot tables, conditional formatting, charts, on a real dataset."),
            _m("tpl-da-stats", "Revise descriptive statistics", "Statistics",
               "Mean, median, spread, distributions, correlation vs causation.", url=KAGGLE_LEARN),
            _m("tpl-da-probability", "Practise probability and sampling", "Statistics",
               "Conditional probability, sampling bias, confidence intervals in plain words."),
            _test("tpl-da-stats-test", "Statistics", "A baseline before SQL."),
        ]},
        {"id": "da-sql", "name": "SQL", "weeks": [6, 10],
         "goal": "Answer business questions straight from a database.",
         "gate": {"topic": "SQL", "min_score": 60, "max_hold_weeks": 1}, "milestones": [
            _m("tpl-da-sql-basics", "Write 25 basic SQL queries", "SQL", "SELECT, WHERE, ORDER BY, GROUP BY, HAVING.",
               url=SQLBOLT),
            _m("tpl-da-sql-joins", "Write 20 join queries", "SQL", "Inner, left, self joins; spot duplicated rows.",
               url=POSTGRES_TUTORIAL),
            _m("tpl-da-sql-windows", "Practise window functions", "SQL", "Running totals, ranks, period-over-period change."),
            _test("tpl-da-sql-test", "SQL", "Checks this phase. Score 60 or more to move on."),
        ]},
        {"id": "da-python", "name": "Python for analysis", "weeks": [11, 15],
         "goal": "Clean and analyse data that doesn't fit in a spreadsheet.", "milestones": [
            _m("tpl-da-python-basics", "Learn the Python basics", "Python", "Types, loops, functions, reading files.",
               url=PYTHON_TUTORIAL),
            _m("tpl-da-pandas", "Clean a messy dataset with pandas", "Pandas",
               "Missing values, types, duplicates, merges; write down every cleaning decision.", url=PANDAS_GUIDE),
            _m("tpl-da-eda", "Do an exploratory analysis", "Data Analysis",
               "Five questions, five charts, one page of findings.", kind="project", skip=False),
        ]},
        {"id": "da-bi", "name": "Dashboards", "weeks": [16, 19],
         "goal": "Show the numbers so a manager can act on them.", "milestones": [
            _m("tpl-da-bi-tool", "Learn Power BI or Tableau", "Data Visualization", "Data model, measures, filters.",
               url=POWER_BI_LEARN),
            _m("tpl-da-dashboard", "Build and publish a dashboard", "Data Visualization",
               "One audience, three questions it answers, published publicly.", kind="project", url=TABLEAU_PUBLIC,
               skip=False),
        ]},
        {"id": "da-portfolio", "name": "Case studies and portfolio", "weeks": [20, 23],
         "goal": "Proof an employer can inspect.", "milestones": [
            _m("tpl-da-case-1", "Write case study 1: a business question end to end", "Data Analysis",
               "Question, data, method, result, recommendation, limitations.", kind="project", skip=False),
            _m("tpl-da-case-2", "Write case study 2 in a different domain", "Data Analysis", "Same structure as case study 1, on retail, finance or public data.", kind="project",
               skip=False),
            _m("tpl-da-portfolio", "Put your portfolio online", "Portfolio", "GitHub or a simple site linking all work.",
               kind="career", skip=False),
        ]},
        {"id": "da-interviews", "name": "Interview preparation", "weeks": [24, 26],
         "goal": "SQL rounds, case rounds and the HR round.", "milestones": [
            _m("tpl-da-sql-timed", "Do a timed SQL interview round", "SQL", "Five questions in 45 minutes.", kind="test",
               skip=False),
            _m("tpl-da-case-interview", "Do an AI mock case interview", "Case Interview",
               "Walk through how you'd investigate a drop in a key metric.", kind="interview", link=INTERVIEW, skip=False),
            _m("tpl-da-resume", "Finalise your resume", "Resume", "Link your dashboard and case studies.", kind="career",
               link="/resume", skip=False),
        ]},
    ],
}

FIRST_YEAR_4Y = {
    "id": "first_year_4y", "version": 1,
    "title": "From first year: 3 years of foundations, then placement prep",
    "summary": "Semester by semester from the first year: programming, DSA, projects, internships and a specialisation. "
               "In the final year it hands over to the 6-month placement plan.",
    "weeks": 156, "fields": [], "programs": ["first_year_4y"], "then": "placement_6m",
    "breaks": [22, 23, 48, 49, 74, 75, 100, 101, 126, 127, 152, 153],
    "note": "Break weeks sit where end-semester exams usually fall; your college calendar may differ.",
    "phases": [
        {"id": "fy-sem1", "name": "Semester 1: learn to program", "weeks": [1, 26],
         "goal": "Write small programs confidently and build study habits.", "milestones": [
            _m("tpl-fy-intro-cs", "Follow an intro to computer science course", "Programming",
               "Work through the first weeks of CS50 or your college course and do every problem set.", url=CS50,
               skip=False),
            _m("tpl-fy-first-language", "Learn your first language well", "Programming",
               "C or Python: variables, loops, functions, arrays, strings. Write 20 small programs.", url=PYTHON_TUTORIAL),
            _m("tpl-fy-easy-problems", "Solve 30 easy problems", "Problem Solving",
               "Patterns, number problems, strings. Consistency matters more than difficulty.", url=LEETCODE_EXPLORE),
            _m("tpl-fy-git", "Put your code on GitHub", "Git", "Commit every program; write a short README.",
               url=GIT_BOOK),
            _m("tpl-fy-math", "Revise discrete maths basics", "Discrete Mathematics",
               "Sets, logic, counting, simple proofs: the maths behind algorithms.", optional=True),
        ]},
        {"id": "fy-sem2", "name": "Semester 2: OOP and a first project", "weeks": [27, 52],
         "goal": "Think in objects and build something people can use.", "milestones": [
            _m("tpl-fy-oop", "Learn object-oriented programming", "OOP",
               "Classes, inheritance, interfaces, with Java, C++ or Python.", skip=False),
            _m("tpl-fy-intro-ds", "Learn arrays, linked lists, stacks and queues", "Data Structures",
               "Implement each one yourself before using the library version."),
            _m("tpl-fy-mini-project", "Build a mini project", "Projects",
               "A small app that solves a real problem for you or your friends.", kind="project", skip=False),
            _m("tpl-fy-hackathon", "Join a hackathon or coding club event", "Teamwork",
               "Ship something in a team, however small.", kind="career", skip=False, optional=True),
        ]},
        {"id": "fy-sem3", "name": "Semester 3: DSA and databases", "weeks": [53, 78],
         "goal": "Core data structures, SQL and web basics.",
         "gate": {"topic": "Data Structures", "min_score": 55, "max_hold_weeks": 2}, "milestones": [
            _m("tpl-fy-dsa-core", "Solve 40 problems on core patterns", "Data Structures",
               "Hashing, two pointers, recursion, sorting, binary search.", url=NEETCODE),
            _m("tpl-fy-sql", "Learn SQL", "SQL", "Write 30 queries on a sample database.", url=SQLBOLT),
            _m("tpl-fy-web", "Learn web basics", "Web Development", "HTML, CSS, JavaScript; build a personal page.",
               url=MDN_LEARN),
            _m("tpl-fy-open-source", "Make a first open-source contribution", "Open Source",
               "Docs fixes count. Learn the pull-request workflow.", kind="career", url=GITHUB_FIRST_CONTRIBUTION,
               skip=False, optional=True),
            _test("tpl-fy-dsa-test", "Data Structures", "Checks this semester's DSA."),
        ]},
        {"id": "fy-sem4", "name": "Semester 4: deeper DSA and the first internship", "weeks": [79, 104],
         "goal": "Trees, graphs, operating systems, and a resume for summer internships.", "milestones": [
            _m("tpl-fy-trees-graphs", "Solve 30 tree and graph problems", "Trees", "Traversals, BST operations, BFS on graphs, shortest paths in a grid.", url=NEETCODE),
            _m("tpl-fy-os", "Learn operating systems basics", "Operating Systems", "Processes, threads, memory.",
               url=OSTEP),
            _m("tpl-fy-resume", "Write an internship resume", "Resume", "Projects first; keep it to one page.",
               kind="career", link="/resume", skip=False),
            _m("tpl-fy-internship-apply", "Apply for 15 summer internships", "Career",
               "Track every application; ask seniors for referrals.", kind="career", link="/opportunities", skip=False),
        ]},
        {"id": "fy-sem5", "name": "Semester 5: specialise and build", "weeks": [105, 130],
         "goal": "Pick a direction and build a substantial project in it.", "milestones": [
            _m("tpl-fy-specialise", "Choose a specialisation", "Career",
               "Web, data, ML, cloud or systems: read two job ads for each and pick one.", kind="career",
               link="/jobs", skip=False),
            _m("tpl-fy-major-project", "Build a major project in your specialisation", "Projects",
               "Deployed, documented, with a problem statement and results.", kind="project", skip=False),
            _m("tpl-fy-cn", "Learn computer networks basics", "Computer Networks", "TCP/IP, HTTP, DNS."),
            _m("tpl-fy-contests", "Take part in 4 coding contests", "Competitive Programming", "Beginner divisions are fine; upsolve one problem after each.", url=CODEFORCES,
               optional=True),
        ]},
        {"id": "fy-sem6", "name": "Semester 6: internship and placement groundwork", "weeks": [131, 156],
         "goal": "Get internship experience and start the placement basics early.", "milestones": [
            _m("tpl-fy-dp", "Solve 20 dynamic programming problems", "Dynamic Programming", "Write the state and recurrence before coding.", url=NEETCODE),
            _m("tpl-fy-aptitude", "Build an aptitude practice habit", "Quantitative Aptitude",
               "Two short timed sets a week from now until placements.", url=INDIABIX),
            _m("tpl-fy-dbms", "Revise DBMS concepts", "DBMS", "Normalisation, transactions, indexing.",
               url=POSTGRES_TUTORIAL),
            _m("tpl-fy-internship-story", "Turn your internship or project into resume bullets", "Resume",
               "What you did, how, and the result, with numbers.", kind="career", link="/resume", skip=False),
            _m("tpl-fy-mock-interview", "Do your first AI mock interview", "Technical Interview",
               "Get a baseline before the placement plan starts.", kind="interview", link=INTERVIEW, skip=False),
        ]},
    ],
}

TEMPLATES: dict[str, dict] = {t["id"]: t for t in (PLACEMENT_6M, SWE_GOOGLE_12M, PRODUCT_SDE_12M, DATA_ANALYST_6M,
                                                   FIRST_YEAR_4Y)}
