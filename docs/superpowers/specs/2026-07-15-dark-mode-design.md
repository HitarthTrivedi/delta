# Dark Mode — Design

**Date:** 2026-07-15
**Status:** Approved

## Goal

Let users switch the Delta app between the existing light editorial theme and the
already-defined dark "Ink variant" palette. First visit follows the OS preference;
an explicit choice via a toggle is remembered in localStorage.

## Current state

- `tailwind.config.js` already has `darkMode: ["class"]`.
- `frontend/src/index.css` already defines the complete dark token set under `.dark`
  (lines ~73–115): bone/paper/ink/oxblood/rule plus all shadcn HSL variables.
- Pages and components consume theme via token classes (`bg-bone`, `text-ink`,
  `border-rule`, `oxblood`, shadcn `bg-background` etc.) almost everywhere.
- `next-themes` v0.4.x is installed but unused. Nothing ever applies the `.dark` class.
- `App.js` hardcodes `<Toaster theme="dark">`.
- A handful of stray non-token colors exist: 1 hex in `LoginPage.jsx`, a few `rgba()`
  literals in `WeeklyPlan.jsx`, `TrophyCabinet.jsx`, `Onboarding.jsx`,
  `Testimonials.jsx`, and canvas colors in `FloatingShapes.jsx` /
  `ParticleBackground.jsx`.

## Design

1. **ThemeProvider** — wrap the app in `next-themes` `ThemeProvider` in `App.js`
   with `attribute="class"`, `defaultTheme="system"`, `enableSystem`,
   `disableTransitionOnChange`. Handles class application, localStorage
   persistence, and system-preference fallback.
2. **ThemeToggle component** — new `frontend/src/components/ui/ThemeToggle.jsx`:
   a Sun/Moon (lucide) icon button in the app's mono/editorial idiom. It flips
   `light` ↔ `dark` based on `resolvedTheme`. Rendered in:
   - `components/ui/Navbar.jsx` — right-side control group (app pages).
   - `components/Header.jsx` — desktop actions group and mobile menu (landing).
3. **Theme-aware Toaster** — replace `theme="dark"` with `resolvedTheme` from
   `useTheme()` (requires the Toaster to render inside the provider).
4. **Stray color patches** — convert the hardcoded colors listed above to
   CSS-variable-driven or dark-aware values so dark mode has no light leftovers.

## Out of scope (YAGNI)

- No three-way auto/light/dark selector; the toggle flips light↔dark, system
  preference is only the initial default.
- No per-page theme overrides, no new dependencies, no dark-mode-specific
  redesign of any page.

## Verification

- `yarn build` passes.
- Run the app: toggle on landing page and in-app Navbar; confirm persistence
  across reload and system-preference default in a fresh profile.
- Visually check landing, Dashboard, WeeklyPlan, LoginPage in both themes;
  toasts match the active theme.
