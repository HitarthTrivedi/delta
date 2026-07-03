# Product

## Register

product

## Users

Students and early-career people (currently: computer engineering, AI/ML, and cloud computing students, with plans to expand to other fields) who need a career plan but can't afford generic advice, expensive counselors, or a chatbot that forgets them every session. They use Delta across a long horizon — years, not weeks — through recurring touchpoints: a one-time intake conversation, a weekly roadmap check-in, a progress report, and an ongoing chat with "Agent 2" for weekly planning. The core workflow is a weekly loop: review this week's tasks, mark progress, talk to the agent about adjustments, request the next week.

## Product Purpose

Delta is an AI career operating system: one intake conversation builds a living model of the student, a weekly planner ("Agent 2") turns that model plus real market signals into one week of concrete tasks at a time, and a progress report turns completed work into an honest, verifiable record. Success looks like a student trusting the weekly plan enough to keep coming back for months/years, and having a resume/portfolio at the end that reflects real completed proof, not aspirational checklists.

## Brand Personality

Warm and approachable — a plan that talks to the student like a good tutor, not a corporate dashboard. Visually the app currently uses an editorial system (bone/paper backgrounds, ink text, oxblood accent, Cormorant Garamond serif headings, Manrope body, IBM Plex Mono for small uppercase labels) modeled after the investor pitch memorandum, but the tone in copy and interaction should stay approachable and encouraging rather than austere or formal — the editorial look is the surface, not the personality.

## Anti-references

No strong anti-reference beyond avoiding generic AI-slop defaults (gradient text, side-stripe card borders, identical icon-grid cards, eyebrow-on-every-section, hero-metric templates). The product previously used a dark cyberpunk/neon dashboard aesthetic; that was intentionally replaced and should not resurface as a default in new work.

## Design Principles

- **One week at a time, not a wall of tasks.** The roadmap should always read as "here's what to do now," never as an overwhelming backlog — this applies to layout density as much as to the underlying planning logic.
- **Honest over decorative.** Progress, stats, and states should reflect what's actually true (real completion, real market data) rather than being smoothed over for a nicer-looking screen. No fake progress, no inflated empty states.
- **Adaptive, not rigid.** The UI should make it easy to see and act on change (skip a task, ask the agent, adjust pace) rather than presenting the plan as fixed.
- **Warm, not corporate.** Approachable language and inviting empty/first-run states — this is a tutor, not enterprise software — even within the more restrained editorial visual system.
- **Read-only feels read-only.** Views that just display state (loading context, viewing progress) must never have destructive side effects on the user's data as a byproduct of merely opening the page.

## Accessibility & Inclusion

Standard WCAG AA: solid text/background contrast (at least 4.5:1 body, 3:1 large text), full keyboard navigation, and a `prefers-reduced-motion` alternative for any animation. No additional formal requirements beyond that at this stage.
