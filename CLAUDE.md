# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 5. AI Model Configuration — DO NOT CHANGE WITHOUT EXPLICIT INSTRUCTION

The model setup is intentional and must never be silently changed:

- **`gemma-4-31b-it`** — default for EVERYTHING: roadmap generation, Agent 2 chat, onboarding pipeline, memory consolidation, market analysis, all general AI calls. Set in `config.py` as `GEMINI_MODEL` default and in `ai_service.py` fallback.
- **`gemini-2.5-flash`** — ONLY for resume analysis. Explicitly pinned in `resume_parser.py` (`parse_resume_llm`) and `resume_service.py` (`generate_suggestions`, `optimize_for_ats`).

**Why:** Gemma-4-31b-it has unlimited calls and 15 RPM on the current Google AI Studio plan. Gemini-2.5-flash has very limited quota. Swapping the default model wastes quota and causes timeouts.

**Rule:** If you are touching anything related to AI model selection — even to "optimize for speed" — stop and ask Hitarth first. Do not introduce any new model string (`gemini-2.0-flash`, `gemini-1.5-flash`, etc.) without explicit approval.

---

## 6. Git Workflow — Collaborative Repo

A collaborator is actively co-developing on this repo alongside Hitarth. Follow this workflow strictly:

1. **Always `git pull origin main` before making any changes.** Do not edit files on a stale local state.
2. **Never push unless Hitarth explicitly says to.** Phrases like "push it", "go ahead and push", or "push" are required. Do not auto-push after commits.
3. **Check `git status` before every session start** to detect uncommitted changes or merge conflicts before touching anything.
4. **If a merge conflict is detected**, stop and surface it to Hitarth — do not auto-resolve or force push.