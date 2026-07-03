---
target: "core product app (weekly loop: Dashboard, CareerChat, WeeklyPlan, Onboarding, Opportunities, ProgressReport, ResumePage, TrophyCabinet, LoginPage)"
total_score: 22
p0_count: 2
p1_count: 4
timestamp: 2026-07-03T09-41-56Z
slug: progressreport-resumepage-trophycabinet-loginpage
---
Method: dual-agent (A: design-review · B: detector+browser)

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | "Request Next Week" progress steps (WeeklyPlan.jsx:364-394) are a client-side timer simulation, not real backend progress. |
| 2 | Match System / Real World | 3 | Unexplained internal jargon ("Delta Score", "dimension_balance") with no inline definitions (Dashboard.jsx:656-671). |
| 3 | User Control and Freedom | 3 | Skip-task dialog is calm and reversible; but destructive "Reset & Retake" is confirmed only via an 8s auto-dismissing toast (Onboarding.jsx:747-767). |
| 4 | Consistency and Standards | 2 | Same "Refresh" action is a rectangle on Dashboard, a pill everywhere else; three incompatible chat-bubble treatments across Onboarding/WeeklyPlan/CareerChat; corner radius inconsistent page to page. |
| 5 | Error Prevention | 2 | Profile reset via timed toast; TrophyCabinet achievement delete has zero confirmation (TrophyCabinet.jsx:206-220). |
| 6 | Recognition Rather Than Recall | 3 | Nav is icon+label; several icon-only buttons ship with no aria-label (title-only). |
| 7 | Flexibility and Efficiency of Use | 1 | No keyboard shortcuts, no bulk actions anywhere; "Request Next Week" hard-gated with no override (WeeklyPlan.jsx:646). |
| 8 | Aesthetic and Minimalist Design | 2 | Dashboard's Focus view stacks 9 modules at once (Dashboard.jsx:407-772) — contradicts the product's own "one week at a time" principle. |
| 9 | Error Recovery | 3 | Warm fallback copy in places; some generic messages remain ("Dashboard sync failed."). |
| 10 | Help and Documentation | 0 | No tooltip/glossary/FAQ anywhere; "Memory Core", "dimension_balance", "Delta Score" go unexplained. |
| **Total** | | **22/40** | **Acceptable — real gaps concentrated in flexibility, error prevention, help, and cross-page consistency; core usability is otherwise sound.** |

## Anti-Patterns Verdict

**Partial yes** — roughly half the surfaces reintroduce tells the design system explicitly rejected.

**LLM assessment**: `LoginPage.jsx` and `CareerChat.jsx` show real craft (zero corner-radius violations, correct type hierarchy, oxblood spent sparingly). The other 7 pages backslide hard:
- Rounded corners despite the system's literal "no rounding anywhere, ever" rule — grep counts: WeeklyPlan.jsx 46, Onboarding.jsx 29, ResumeSection.jsx 26, Dashboard.jsx 17, Opportunities.jsx 14, TrophyCabinet.jsx 11, ProgressReport.jsx 8, vs. 0 in Login/Chat.
- `index.css:162` literally comments "*Editorial surface accents (former cyberpunk classes, re-skinned)*" above `.bg-grid-pattern`, which `Dashboard.jsx:370` uses for its loading screen alongside a spinning `Cpu` icon and tracked-mono "Loading Career OS" — the exact aesthetic DESIGN.md bans resurfacing, on the page's own loading state.
- `shadow-2xl` on Dashboard's roadmap modal (line 786) — the system's one explicit "no shadows" rule, broken.
- A reintroduced multi-hue semantic palette (emerald/amber/rose/blue) across Dashboard, ResumeSection, Opportunities, TrophyCabinet, WeeklyPlan — breaks "The One Accent Rule."
- Three incompatible chat-bubble treatments for the same "Agent 2" signature feature (Onboarding, WeeklyPlan, CareerChat all differ).

**Deterministic scan**: 29 findings, exit code 2. `design-system-radius` (5, all Onboarding.jsx: lines 123×2, 931×2, 1120), `design-system-color` (23, across WeeklyPlan.jsx/Opportunities.jsx/TrophyCabinet.jsx), `bounce-easing` (1, CareerChat.jsx:296, a staggered typing-indicator — arguably a reasonable chat convention, but still outside the documented palette of allowed easings).

**Where the scan and the LLM review diverge**: the detector reported **zero** findings in Dashboard.jsx and ResumeSection.jsx, but the LLM review independently found 17 and 26 rounded-corner instances respectively in those same files, plus hardcoded status colors in both. This is very likely a detector blind spot — its color/radius rules appear to catch inline `style={{ borderRadius: ... }}` and literal hex/rgba more reliably than Tailwind utility classes (`rounded-full`, `rounded-lg`) or Tailwind color tokens (`text-emerald-600`), so Dashboard.jsx and ResumeSection.jsx's violations went unflagged by the scan even though they're real. Treat the LLM's file-by-file counts as the more complete picture; the detector's file:line list is precise but not exhaustive for Tailwind-class-based violations.

**Visual overlays**: not available this run — no browser automation/DOM-mutation tool was exposed in this session, and all product routes require real auth (no test-credential bypass exists), so no screenshots or live overlay could be produced. Findings above are source-level plus one manual WCAG contrast computation, not live-rendered evidence.

## Overall Impression

Login and the Agent-2 chat page are genuinely well-executed and prove the editorial system works when followed. The rest of the app — everything downstream of first login — drifts from it page by page: rounding creeps back in, a banned multi-hue palette returns for "status," and the most important page in the product (WeeklyPlan) carries the heaviest violation count of all. The biggest opportunity is bringing the other 7 pages up to the bar Login/Chat already set, rather than any wholesale redesign.

## What's Working

- **LoginPage.jsx**: the reference implementation of "the weekly memorandum" — correct serif/mono/sans hierarchy, oxblood spent only on the primary CTA and links, zero corner-radius violations.
- **CareerChat.jsx**: a genuinely differentiated, non-generic "flowing Q&A, not chat bubbles" pattern (an explicit, intentional design decision in the code) backed by a real markdown/KaTeX/table renderer — the only chat surface in the app with zero square-corner violations.
- **ResumeSection.jsx's `SuggestionsDiff` flow**: individually toggleable AI-suggested edits with a running count before "Apply" — real user control over AI output, matching "adaptive not rigid." Its collapsible sections are correct, working progressive disclosure.
- **WeeklyPlan's skip-task dialog**: three calm, non-judgmental, reversible-feeling choices with no guilt-tripping copy — exactly the reassurance a student marking something incomplete needs.

## Priority Issues

**[P0] Remember-me checkbox is not keyboard-operable.**
- **Why it matters**: `LoginPage.jsx:151-162` implements it as a plain `<div onClick>` with no `role`, `aria-checked`, `tabIndex`, or keyboard handler. A keyboard-only or screen-reader user cannot reach or toggle it at all — on the very first screen of the product. The team already knows the correct pattern (`WeeklyPlan.jsx:619-630` correctly uses `role="button" tabIndex={0}` with an Enter handler), so this is an inconsistency, not a knowledge gap.
- **Fix**: Apply the same `role="checkbox" aria-checked tabIndex={0}` + keyboard handler pattern already used correctly elsewhere in the codebase.
- **Suggested command**: /impeccable harden

**[P0] Destructive achievement delete has zero confirmation.**
- **Why it matters**: `TrophyCabinet.jsx:206-220` deletes an achievement with no confirmation step of any kind — a single misclick permanently destroys a record the product explicitly frames as a trust-building "honest" trophy cabinet.
- **Fix**: Add a confirm step consistent with the app's existing pattern (WeeklyPlan's skip-task dialog is a good model: calm, explicit, reversible-feeling).
- **Suggested command**: /impeccable harden

**[P1] Square-corner rule is broken on the majority of pages, worst on the single most important page.**
- **Why it matters**: DESIGN.md states this as an absolute rule ("no rounding anywhere, ever... a single rounded button or card breaks the square-corner rule immediately"). WeeklyPlan.jsx — the core weekly loop — has the highest violation count of any page (46 instances: `panelStyle` at line 21, pill buttons at 440/452/879, asymmetric chat-bubble radii at 991-1006).
- **Fix**: Replace every `borderRadius`/`rounded-*` usage in WeeklyPlan.jsx, Onboarding.jsx, ResumeSection.jsx, Dashboard.jsx, Opportunities.jsx, TrophyCabinet.jsx, ProgressReport.jsx with square corners, matching LoginPage.jsx/CareerChat.jsx.
- **Suggested command**: /impeccable polish

**[P1] A reintroduced multi-hue semantic palette breaks "The One Accent Rule."**
- **Why it matters**: emerald/amber/rose/blue tones (some hardcoded hex/rgba) appear across Dashboard, ResumeSection, Opportunities, TrophyCabinet, WeeklyPlan for status/score/difficulty indicators. DESIGN.md requires desaturating any second meaning-bearing color toward the neutral ramp instead. This is precisely the "generic AI palette" tell and undoes the single-accent discipline that makes Login/Chat feel intentional.
- **Fix**: Replace status-tone colors with desaturated neutral-ramp variants + iconography for distinction, or commit to one deliberately desaturated hue applied consistently.
- **Suggested command**: /impeccable colorize

**[P1] Dashboard's loading state and body type resurrect the explicitly-rejected cyberpunk aesthetic.**
- **Why it matters**: `Dashboard.jsx:370` wraps the page in `font-mono` (meaning ordinary prose inherits monospace instead of Manrope, violating "mono reserved entirely for small structural labels") and its loading screen (369-375) uses `.bg-grid-pattern` — a class the codebase's own CSS comment (`index.css:162`) labels "former cyberpunk classes, re-skinned" — plus a spinning `Cpu` icon. This is the first thing a returning student sees every session.
- **Fix**: Remove the root `font-mono` wrap (keep mono only on explicit label spans), replace the grid-pattern/Cpu loading screen with the same warm, plain-sentence loading language used elsewhere in the app.
- **Suggested command**: /impeccable polish

**[P1] "Request Next Week" simulates progress instead of reporting it.**
- **Why it matters**: `WeeklyPlan.jsx:364-394` drives its step-by-step "Agent 2 is curating your next week..." messaging off a client-side `setInterval`, not real backend events. PRODUCT.md's own design principle states "No fake progress, no inflated empty states" — this is a literal instance of the thing that principle exists to prevent, on the app's most important action.
- **Fix**: Drive step text from real backend progress, or replace with one honest indeterminate spinner and a plain status line.
- **Suggested command**: /impeccable harden

**[P1] Placeholder/secondary text fails WCAG AA contrast.**
- **Why it matters**: `text-ink-soft/70` and `/60` (LoginPage.jsx:232,288,291; Dashboard.jsx:745; ResumeSection.jsx:267,386,674,689) computes to roughly 2.95:1 against the bone/paper background — well under the 4.5:1 minimum the product's own PRODUCT.md commits to. This affects footer legal text and placeholder text on the first screen every user sees.
- **Fix**: Drop the opacity modifier and use the full `--ink-soft` token, or a darker step, wherever it's applied to body-sized text.
- **Suggested command**: /impeccable audit (already covered below) → /impeccable harden

## Persona Red Flags

**Jordan (First-Timer)**: Finishes the warm conversational intake and is immediately dropped into a 24-field, ungrouped, HR-form-style profile editor (Onboarding.jsx:570-594, labels like "Inferred Planning Horizon (Months)") with zero section headers. The destructive "Reset & Retake" is confirmed via a toast that auto-dismisses in 8 seconds — Jordan, who reads carefully, may lose the option silently. First Dashboard visit shows "Loading Career OS" / "Dashboard sync in progress" on a technical grid background — not a "welcome back," and once loaded, 9 simultaneous panels with unexplained jargon ("Memory Core", "dimension_balance") give no entry point.

**Sam (Accessibility-Dependent)**: Blocked outright from the Remember-me checkbox (no keyboard path at all, see P0 above). Multiple icon-only close/delete buttons ship with no `aria-label` or `title` (WeeklyPlan.jsx:955-964 chat-drawer close, Dashboard.jsx:795-800 modal close, ResumeSection.jsx:333-335) — a screen reader announces only "button." Computed placeholder-text contrast (~2.95:1) fails AA on the first screen Sam encounters.

**Alex (Power User)**: Zero keyboard shortcuts anywhere in the weekly task loop; no bulk actions despite product register explicitly permitting them; "Request Next Week" is hard-gated behind every single task being checked/skipped with no override for someone who wants to intentionally leave one open and move on.

## Minor Observations

- `GlassPanel.jsx` is implemented flat/compliant (no blur, just a bordered div) but its name is a relic of the rejected glass aesthetic — worth renaming so it doesn't invite a future glass reintroduction.
- Blur usage is inconsistent in intent: Navbar.jsx (`backdrop-blur-xl`), Onboarding.jsx (`blur(10px)`), Dashboard.jsx (`backdrop-blur` + `shadow-2xl` together, the most glass-like of the three).
- `Navbar.jsx`'s avatar circle (`rounded-full`) is likely an acceptable "avatar = circle" convention exception, but technically still violates the literal square-corner rule — worth a documented exception if kept.
- Same "Refresh" action renders as a rectangle on Dashboard vs. a pill everywhere else.
- `Opportunities.jsx:278`'s empty-state icon sits on an unrelated periwinkle-blue tint behind an oxblood icon — a small mismatched-accent detail.
- `animate-bounce` typing indicator (CareerChat.jsx:296) is a reasonable, bounded chat convention, but technically outside the documented motion palette — flag it, don't necessarily fix it.

## Questions to Consider

- What if WeeklyPlan — explicitly the most important page — were rebuilt strictly from the same tokens already used correctly in Login/Chat, rather than carrying ad hoc inline `borderRadius` styles that suggest it predates the square-corner system's finalization?
- Does the manufactured "Agent 2 is curating..." progress sequence actually build more trust than a plain "Agent 2 is thinking" message, once a weekly-returning student notices the identical steps fire in the identical order regardless of actual complexity?
- What if Dashboard's four simultaneous views became a true "one week at a time" surface — Memory/Roadmap pushed into secondary drill-downs from Focus — to actually match the product's own stated design principle?
