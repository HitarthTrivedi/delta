# Delta for College: data notes for the lawyer

Internal working notes, **not legal text**. They describe how the product handles college data so a lawyer can
draft the college agreement (DPA) and confirm the open questions below before launch.

## Roles
- **College roster and the reports a college reads:** the college is the Data Fiduciary; Delta is its Data Processor
  (DPDP Act s.8(2)). The college decides what it uploads (roll no, name, email, branch, section, graduation year,
  CGPA, backlogs, and DOB only for under-18s) and how it uses the reports.
- **Everything a student does on Delta** (plans, practice, chats, résumé, habits): Delta is the Data Fiduciary, on the
  student's own consent (terms + purpose consents recorded in `consent_records`).
- **Recruiters:** each recruiter is a Fiduciary for data it takes away. Students are shown only on their own opt-in,
  and only to their pool: campus recruiters (linked by their college) or off-campus recruiters (solo students).

## What the agreement (DPA) should cover
- Purpose limitation: Delta processes the roster only to give students their seats and to show the college reports.
- Sub-processors: the list in Privacy Policy §7.
- Breach notice to the college without undue delay.
- Deletion at contract end: 30-day export window, then the roster and reports are deleted (`scripts` / operator step).
- Students' rights requests about the roster go through the college; requests about their own Delta data come to Delta.
- What the college sees and never sees (Privacy Policy §6A), and that staff must use reports only for training and placements.

## Under-18 students (feature flag `MINOR_ACCOUNTS_ENABLED`, off)
- Verifiable parental consent: a one-time emailed link (hashed token, 7-day expiry) or the college's attestation, made
  at roster upload with a reference to the consent it holds (stored on the roster row with who attested and when).
- Restrictions: no AI processing of the child's own data, no recruiters, leagues, circles, invite or public links,
  fixed-wording reminders; re-consent at 18.
- **Open questions before switching it on:**
  1. Is the college's attestation "verifiable consent" under the DPDP Rules, and what evidence must the college keep?
  2. Does the educational-institution exemption cover the at-risk dashboard (activity-based) for under-18 students,
     or should minors be excluded from it?
  3. The Gemini API terms on users under 18: confirm topic-only generation (no child data in prompts) is acceptable.

## Other open points
- Supabase email confirmation must be on (college email-domain matching relies on verified emails).
- Professionals were visible to recruiters before this change; they are notified and no longer shown.
