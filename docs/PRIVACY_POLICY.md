# Privacy Policy

The published Privacy Policy lives in **[frontend/public/legal/privacy-policy.md](../frontend/public/legal/privacy-policy.md)**. That file is the single source of truth: the in-app `/privacy` page renders it directly.

When you change it materially:
1. update its "Last updated" / version line, and
2. bump `POLICY_VERSION` in `backend/app/services/compliance.py` to the same date, so every user is asked to accept again.
