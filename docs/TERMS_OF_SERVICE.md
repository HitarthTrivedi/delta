# Terms of Use

The published Terms of Use live in **[frontend/public/legal/terms-of-use.md](../frontend/public/legal/terms-of-use.md)**. That file is the single source of truth: the in-app `/terms` page renders it directly.

When you change it materially:
1. update its "Last updated" / version line, and
2. bump `POLICY_VERSION` in `backend/app/services/compliance.py` to the same date, so every user is asked to accept again.
