# Delta Career OS Blueprint

Delta is not just a roadmap generator. It is a personalized career operating system for students and early professionals who need help understanding themselves, the market, and the weekly actions that move them toward a real career outcome.

The core belief is simple: most students are not failing because they lack motivation. They are failing because the world ahead is invisible to them. Delta should make the invisible visible, then turn it into a weekly journey.

## Product Thesis

Delta should behave like a central AI career engine that:

1. Builds a structured understanding of the user once during onboarding.
2. Keeps a living model of the user's behavior, decisions, preferences, habits, and progress.
3. Reads market signals every week from web/API sources.
4. Converts personal context plus market context into a roadmap, calendar, projects, portfolio proof, and weekly assessments.
5. Adapts without losing memory of where the user started and why the journey changed.

This means the system must avoid raw scattered data. Every user signal should become structured career intelligence.

## System Pillars

### 1. Adaptive Ingestion

Ingestion happens mainly once, during onboarding.

The user does not fill a static form. The AI asks adaptive questions based on:

- Current education stage.
- Ambition and target domains.
- Existing skills and proof.
- Preferred learning style.
- Constraints such as time, language comfort, devices, internet access, family expectations, location, and financial limits.
- Confidence level and self-awareness.
- Market signals available at that moment.

The AI should not immediately convert answers into fixed roadmap numbers. First, answers are stored as structured intake intelligence.

The ingestion output should include:

- User identity context.
- Ambition map.
- Current capability map.
- Constraint map.
- Preference map.
- Motivation and risk map.
- Evidence map.
- Open questions the system still needs to resolve.
- Market-search prompt generated from the user's context.
- Follow-up question strategy.

The important part: raw conversation is secondary. The primary object is the structured profile.

### 2. Personal Data Vault

The "place where personal data is stored" is the user's Career Memory Vault.

It should not be one blob. It should be split into durable structured files/tables:

- `identity_profile`: name, education stage, location, language, background.
- `ambition_profile`: long-term goals, short-term targets, dream roles, preferred industries.
- `capability_profile`: skills, depth, proof, confidence, gaps.
- `behavior_profile`: consistency, procrastination patterns, preferred study times, decision habits.
- `constraint_profile`: time, money, device, internet, college load, family limits.
- `preference_profile`: learning style, content type, project taste, communication tone.
- `evidence_profile`: projects, certificates, GitHub, resumes, contests, writing, portfolio.
- `journey_log`: day-one-to-today history.
- `market_context`: external world signals relevant to the user.
- `roadmap_state`: current long-term map and active weekly direction.

The AI assistant reads from these profiles before acting anywhere in the product.

### 3. Central AI Engine

Delta should have one central intelligence layer. Features should not make isolated decisions.

The central engine owns:

- User memory interpretation.
- Roadmap generation.
- Weekly planning.
- Market pulse synthesis.
- Calendar generation.
- Project recommendation.
- Portfolio assessment.
- Resume weight analysis.
- Question asking.
- Course/resource selection.
- Opportunity matching.

Every feature should ask the central engine: "Given this user's memory and today's market, what should happen next?"

This prevents Delta from becoming separate pages that do not know each other.

### 4. Market Pulse

Market pulse runs weekly and also during onboarding.

It should gather structured signals from:

- Job descriptions.
- Internship posts.
- Hackathons.
- Kaggle competitions.
- Codeforces and LeetCode trends.
- Unstop competitions and quizzes.
- GitHub project trends.
- Tech news.
- Certification demand.
- College hiring patterns.
- Indian tech ecosystem behavior.
- Global remote and AI-tooling shifts.

Market pulse should not store only raw links. It should store:

- Skills rising.
- Skills declining.
- Tools appearing repeatedly.
- Common project expectations.
- Recruiter language.
- Proof signals recruiters reward.
- New competitions and deadlines.
- Suggested weekly actions.
- Confidence and source list.

The user's roadmap changes only after combining market pulse with personal context.

### 5. Roadmap

The roadmap should feel like a career map, not a checklist.

It has two views:

- Zoomed-out: long-term projection, phases, destination, milestones, role readiness.
- Zoomed-in: this week, today's tasks, current blockers, next proof to build.

Each roadmap phase should include:

- Why this phase exists.
- What the user must learn.
- What proof must be created.
- What resources are best for this user's style.
- What projects validate the phase.
- What certifications add resume weight.
- What market signal justifies the phase.
- What mistakes students usually make at this stage.
- What a strong candidate would look like after completion.

The roadmap should learn from users' actions. If a user skips tasks, overperforms, changes ambition, or discovers a new interest, the roadmap adapts.

### 6. Journey Until Today

Journey Until Today is the user's career history from day one to now.

It should capture:

- Completed tasks.
- Missed tasks.
- Mood and confidence changes.
- Learning velocity.
- Skill growth.
- Project progress.
- Certifications.
- Competitions attempted.
- Calendar adherence.
- Market shifts that affected the roadmap.
- AI decisions and why they happened.

This log makes Delta feel alive. The system should be able to say, "You changed direction in week 4 because your project evidence showed stronger backend interest than ML interest."

### 7. Weekly Loop

Every week, Delta performs a complete cycle:

1. Read user memory.
2. Read last week's journey.
3. Fetch market pulse.
4. Compare user state against market expectations.
5. Update roadmap if needed.
6. Generate weekly plan and calendar.
7. Recommend opportunities.
8. Recommend one meaningful project or project milestone.
9. Assess portfolio/resume weight.
10. Write a weekly brief.
11. Ask only the questions needed to reduce uncertainty.

Weekly output should include:

- Are you on track?
- What changed in the world?
- What changed in you?
- What to learn.
- What to build.
- What to avoid.
- Which opportunities to try.
- Which resource path to follow.
- Which proof to add to resume/portfolio.

### 8. Projects As Proof

Projects should not be generic.

Delta should recommend projects that create proof for the user's target role and current phase.

A project recommendation should include:

- Resume headline.
- Real-world problem.
- Why it matters.
- Required skills.
- Stretch skills.
- Milestones.
- Evaluation criteria.
- GitHub README expectations.
- Demo expectations.
- Recruiter-facing explanation.
- Possible extensions.

The system should prefer fewer, stronger projects over many weak ones.

### 9. Portfolio Assessment

Each week, Delta creates or updates a portfolio assessment.

It should answer:

- What proof does the user currently have?
- What proof is missing?
- What looks weak or fake?
- What can be shown publicly?
- What should go on resume?
- What should go on GitHub/LinkedIn?
- What should be improved before applying?

The goal is to create career weight, not cosmetic completion.

### 10. Generalization Beyond CS

The first strong use case can be Indian CS/engineering students after 12th, but the architecture should not be hardcoded to CS.

The system should support domain packs:

- Computer science.
- Data/AI.
- Design.
- Product.
- Finance.
- Core engineering.
- Research.
- Entrepreneurship.

Each domain pack can define:

- Skill taxonomy.
- Market sources.
- Proof types.
- Projects.
- Certifications.
- Competitions.
- Roadmap phases.
- Evaluation rubrics.

## Core Data Objects

### Career Memory Profile

The central user model.

```json
{
  "user_id": "string",
  "identity": {},
  "ambitions": {},
  "capabilities": {},
  "constraints": {},
  "preferences": {},
  "behavior": {},
  "evidence": {},
  "open_questions": [],
  "confidence": 0.0,
  "updated_at": "datetime"
}
```

### Market Pulse Snapshot

Weekly external-world context.

```json
{
  "user_id": "string",
  "target_domain": "string",
  "time_window": "weekly",
  "demanded_skills": [],
  "emerging_skills": [],
  "opportunities": [],
  "certifications": [],
  "project_patterns": [],
  "market_warnings": [],
  "sources": [],
  "confidence": 0.0
}
```

### Roadmap State

Long-term and short-term direction.

```json
{
  "user_id": "string",
  "destination": {},
  "phases": [],
  "active_phase_id": "string",
  "weekly_focus": {},
  "resource_graph": [],
  "proof_requirements": [],
  "last_replanned_reason": "string"
}
```

### Journey Event

Atomic career history entry.

```json
{
  "user_id": "string",
  "event_type": "task_completed | missed_task | project_update | market_shift | ai_decision | user_reflection",
  "summary": "string",
  "evidence": {},
  "impact": {},
  "created_at": "datetime"
}
```

### Weekly Career Brief

The user-facing weekly output.

```json
{
  "user_id": "string",
  "week_start": "date",
  "track_status": "ahead | on_track | drifting | blocked",
  "market_changes": [],
  "personal_changes": [],
  "roadmap_updates": [],
  "actions": [],
  "opportunities": [],
  "portfolio_assessment": {},
  "questions_for_user": []
}
```

## First Build Slice

The first real implementation should create the spine:

1. Upgrade onboarding into structured ingestion.
2. Add a Career Memory Profile model/service.
3. Add a Central Engine service that reads memory, market, roadmap, and journey.
4. Add Journey Event logging.
5. Add Roadmap State generation.
6. Connect weekly brief generation to the central engine.

Once this exists, frontend pages can become visual surfaces for the same intelligence instead of separate experiences.

## Non-Negotiables

- Do not store important user understanding only as raw chat.
- Do not generate a roadmap without market context.
- Do not generate weekly advice without reading journey history.
- Do not ask the user static questions when structured uncertainty can decide better questions.
- Do not recommend resources without explaining why they fit the phase.
- Do not recommend projects unless they create visible career proof.
- Do not pretend the user is progressing if evidence says they are not.

Delta should be honest, adaptive, and deeply personal.
