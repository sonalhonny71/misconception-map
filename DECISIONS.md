# Decisions Log

This file records judgment calls made during development where the spec was ambiguous or required trade-offs.

## 2024-01-15: Initial Project Setup

### 1. Backend Language: Python/FastAPI over Node/Express
**Decision**: Use Python 3.12 + FastAPI for backend despite prototype being Next.js/React.
**Reason**: Spec explicitly required "Python backend and database" with FastAPI, SQLAlchemy, Alembic. The diagnostic engine benefits from Python's scientific libraries (sympy for content verification).

### 2. Database: Neon Postgres (Free Tier)
**Decision**: Use Neon serverless Postgres with pooled connection for runtime, direct for migrations.
**Reason**: Spec required Neon free tier. Pooled connection (`pooler` endpoint) for app runtime handles Neon's auto-scaling; direct connection for Alembic migrations avoids transaction pooling issues.

### 3. Anonymous Learners (No Auth)
**Decision**: Token-based anonymous learners with SHA-256 hashed tokens in DB. Token returned once on creation, stored in localStorage.
**Reason**: Spec explicitly required "no accounts, no PII, users are minors". No email, no passwords, no OAuth.

### 4. Evidence Scoring: Half-Points Stored as Integers
**Decision**: Multiply all evidence scores by 2, store as integers (e.g., +1.0 → +2, +0.5 → +1).
**Reason**: Avoids floating-point precision issues in SQL and Python. Thresholds adjusted accordingly (2.0 → 4, 3.0 → 6, 1.5 margin → 3).

### 5. Follow-Up Can Lower Hypothesis Score
**Decision**: A correct follow-up answer contradicts the discriminated hypotheses, applying negative evidence (-1.5 → -3 stored).
**Reason**: This is the core discriminating mechanism specified in the brief: "If the student answers the follow-up correctly, evidence for the first hypothesis decreases."

### 6. Single Follow-Up Per Hypothesis (MVP)
**Decision**: One follow-up question per hypothesis in MVP, though content supports 2+.
**Reason**: Keeps journey short (3-4 diagnostic + 1 follow-up + 3 practice + 3 retest = ~11 questions max). Can expand later.

### 7. Check Understanding Only for All-Correct Diagnostic
**Decision**: Check-understanding phase only triggers when diagnostic has zero misconception signals.
**Reason**: Spec says "Correct on everything? Take the right-hand branch... show one transfer question." If any wrong answer with misconception signal → follow-up branch.

### 8. Practice XP Awarded Server-Side, Idempotent
**Decision**: XP events have unique `event_key` (e.g., `practice:session-uuid`) preventing double awards on retry/refresh.
**Reason**: Spec requires "XP awarded server-side only, idempotently (no double awards on retries/refresh)."

### 9. No "Mastered" Status Ever
**Decision**: Status vocabulary explicitly excludes "mastered". Highest is `consistent_evidence` (two passed retests).
**Reason**: Spec: "Never show 'mastered'. Use the status vocabulary in section 6.4."

### 10. Frontend: React + Vite + Tailwind (Not Next.js)
**Decision**: SPA served by FastAPI (single Docker image) rather than separate Next.js deployment.
**Reason**: Spec: "One Docker image: multi-stage build (Node builds the SPA → Python image serves /api/* and the built SPA with SPA-fallback routing). One service = one public URL, no CORS surprises."

### 11. KaTeX for Math Rendering
**Decision**: Use KaTeX (not MathJax) for client-side math rendering.
**Reason**: KaTeX is faster, smaller bundle, no async loading issues. `trust: false` for security.

### 12. Option Shuffling Server-Side
**Decision**: Option order shuffled per served item on server, stored in `served_items.option_order`.
**Reason**: Spec: "Grade by opaque option ID, not by array index; shuffle option order per served item and store the order." Prevents position bias.

### 13. Idempotent Answer Submission
**Decision**: Unique constraint on `(session_id, served_item_id)` in responses table. Re-submission returns cached result.
**Reason**: Spec: "Idempotent answers: resubmitting the same served item returns the original result (no duplicate rows, no double XP)."

### 14. Cold-Start UX for Free Tier
**Decision**: Frontend shows "Waking up the server — this can take up to ~30 seconds" with automatic retry/backoff on 503/timeout.
**Reason**: Spec: "Free-tier instances sleep → cold-start UX... tell me the optional step of pointing a free uptime pinger at /api/health."

### 15. Content in YAML (Not JSON or DB)
**Decision**: Content authored in YAML files per level, loaded at startup via `ContentLoader`.
**Reason**: Spec: "Content lives in versioned Python/YAML data, not hard-coded in UI." YAML is human-readable, supports comments, version-controlled.

### 16. Sympy for Content Verification
**Decision**: CI runs sympy to verify every correct answer and distractor procedure.
**Reason**: Spec: "Automatic content verification (must run in CI; fail the build on error). Recompute every answer with sympy."

### 17. Retest Pool Exhaustion Handling
**Decision**: If learner exhausts retest pool, reuse oldest items and label "partially repeated" in record.
**Reason**: Spec: "If the retest pool for that learner is exhausted, reuse the oldest-seen retest items and label the retest 'partially repeated'."

### 18. Footer Privacy Copy Updated
**Decision**: Removed prototype's "data stays in this browser" line. New footer: "Anonymous learning prototype. Your progress is saved under a random ID on our server so you can resume; no names or emails are collected. You can delete it any time."
**Reason**: Spec: "Footer/privacy copy must be truthful for the new architecture... The prototype's 'data stays in this browser' line must be removed."

### 19. Render.yaml as Fallback Blueprint
**Decision**: Keep valid `render.yaml` in repo even though deploying via API.
**Reason**: Spec: "Also keep a valid render.yaml in the repo as a fallback Blueprint."

### 20. Secret Scanning in CI
**Decision**: Gitleaks + custom pattern checks (npg_, rnd_, postgresql://) in GitHub Actions before every push.
**Reason**: Spec: "Run a secret scan... before EVERY push and fail loudly if anything is found."

### 21. Local Development with SQLite Option
**Decision**: Support SQLite for local dev via `DATABASE_URL=sqlite:///./dev.db` but production requires Postgres.
**Reason**: Spec: "SQLite for local dev/tests. Never rely on a container's local disk in production."

### 22. Rate Limiting: 60 req/min/IP
**Decision**: SlowAPI with 60 requests/minute/IP on API, stricter on learner creation.
**Reason**: Spec: "Rate limit (e.g., slowapi: 60 req/min/IP on API, stricter on POST /api/learners)."

### 23. CORS Locked to Deployed Origin
**Decision**: `ALLOWED_ORIGINS` env var set to service's public URL in production.
**Reason**: Spec: "CORS locked to the deployed origin (+ localhost in dev)."

### 24. Health Check at /api/health
**Decision**: `/api/health` returns DB connectivity status for Render health checks.
**Reason**: Spec: "health check path /api/health" in Render config.

### 25. Mermaid Architecture Diagram in README
**Decision**: Include text-based architecture diagram in README.
**Reason**: Spec: "README with: architecture diagram (Mermaid)."

---

## Template for Future Decisions

When making a new judgment call, add an entry:

### YYYY-MM-DD: Short Title
**Decision**: What you decided.
**Reason**: Why, referencing spec section or trade-off.
**Alternatives Considered**: What else you evaluated.
**Impact**: Any follow-up work needed.