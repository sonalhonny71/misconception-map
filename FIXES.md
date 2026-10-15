# MisconceptionMap – what was broken, what I fixed, how to run it

Project: https://github.com/sonalhonny71/misconception-map (not ours; nothing was pushed there).
Work is on local git branch `fixes` in `/workspace/misconception-map` (4 commits on top of `main`).
Everything below was checked by actually running it (see "Verification").

## How to run (the easy way)

```bash
cd misconception-map
./scripts/start.sh          # needs Python 3.12+ and Node 20+; first run takes ~1-2 minutes
# then open http://localhost:8000
```
It installs everything, builds the web page, makes a local SQLite database, loads the 107 questions and starts the app.
Use `PORT=9000 ./scripts/start.sh` for another port. Stop with Ctrl+C.
API documentation page: http://localhost:8000/api/docs. Quick check of the whole API: `BASE_URL=http://localhost:8000 ./scripts/smoke.sh` (needs `jq`).

Other ways: `docker compose up --build` (Docker + Postgres, app on http://localhost:8000), or the manual steps in README.md.

## What still needs you
- Nothing is required to run it locally. No API keys are used by the app.
- For a real deployment (Render + Neon): create a Neon Postgres database and put its address in `DATABASE_URL` (and `DATABASE_URL_DIRECT`), set `SECRET_KEY` (random text), `ENV=production`, `ALLOWED_ORIGINS=https://your-site`. `RENDER_API_KEY` is optional. See `.env.example`. Never commit your real `.env`.
- Docker was **not available** on the machine used, so the Dockerfile / docker-compose were corrected by reading and are **not test-run**. The same app was tested against a real PostgreSQL 16 (tables created, full smoke test passed) and against SQLite.
- Not run: the Safari/iPhone ("mobile-safari") browser profile of the end-to-end tests (needs Safari engine and system libraries that could not be installed here). Chrome desktop and Chrome phone profiles pass.

## Errors found and fixed

| # | Error (what you would see) | Cause | Fix (files) |
|---|---|---|---|
| 1 | `pytest` fails immediately: `ModuleNotFoundError: No module named 'app'` | Test settings did not tell Python where the app code is | `backend/pyproject.toml` (`pythonpath`) |
| 2 | Every logged-in API call answered 401 "Missing or invalid authorization header" | The login token was read as a URL parameter instead of the `Authorization` header | `backend/app/api/learners.py` |
| 3 | `POST /api/learners` with no body (what smoke.sh and tests do) failed with 422 | Body was required although it carries no data | `backend/app/api/learners.py` |
| 4 | `GET /api/levels` crashed (500) | Wrong name `SessionModel.Status` (should be `SessionStatus`) | `backend/app/api/levels.py` |
| 5 | With no database setting (the README's "local SQLite") the app could not connect and migrations failed | SQLite was given a Postgres-only option (`connect_timeout`); migration used Postgres-only `now()` | `backend/app/db/session.py`, `backend/alembic/versions/001_initial.py` |
| 6 | The questions table was empty in production/Docker, so starting a session crashed | Nothing ever loaded the YAML questions into the database (the seed script was not run or even copied into Docker) | new `backend/app/content/seed.py`, `backend/app/main.py` (seeds at start-up), `backend/scripts/seed_content.py` now uses it |
| 7 | Migrations at start-up failed when the app was started from another folder; logging was silenced after migrations | Alembic folder path was relative; Alembic switched off other loggers | `backend/app/main.py`, `backend/alembic/env.py` |
| 8 | Docker Compose: app could not connect to Postgres | Address used the `postgresql+psycopg://` driver which is not installed | `docker-compose.yml`; `backend/app/core/config.py` now also accepts `postgres://` and `+psycopg` addresses |
| 9 | Answering a question gave 404 "Served item not found", or crashed | The session code in `sessions.py` had many bugs: it used the engine before it was created; handed a different random question/option order than it saved; mixed two formats for the saved option order; passed database rows where plain content was expected; mapped phase "check_understanding" to a non-existing answer kind; never reset the step counter on a new phase; a new progress record crashed on `None + 1`; new hypotheses were not counted; XP shown on every answer though only awarded once | `backend/app/api/sessions.py` (rewritten helpers, same behaviour as designed) |
| 10 | A learner could get stuck (or skip the retest) when fewer than 3 targeted practice questions existed; practice list changed while answering | Practice/retest pool shrank as questions were answered, and had no top-up | `backend/app/content/loader.py`, `backend/app/engine/state_machine.py` |
| 11 | Re-sending the same answer was rejected after the session ended and returned a different result | Idempotency check was after the status check and returned an incomplete result | `backend/app/api/sessions.py` |
| 12 | 3 tests in `test_engine.py` failed | Test bugs: they looked for hidden hints (`misconception_id`) that are deliberately not sent to learners (so several tests silently tested nothing); fast-forward loop consumed the retest; follow-up phase never answered | `backend/tests/test_engine.py` (look hints up in the content; no tests removed) |
| 13 | `test_correct_option_not_biased` failed: correct answer was almost always listed first | Content authoring order (answers are shuffled when shown, but the check looks at the files) | `backend/app/content/level1-5.yaml` (option order only; identical text, ids, hints – verified) |
| 14 | `test_katex_rendering` hung for minutes (called `npx` ~800 times, and crashed on timeouts) and could never fail | Test design | `backend/tests/test_content_verification.py` (one Node run using the frontend's KaTeX; skipped if Node/frontend not installed) |
| 15 | Real content error found by that test: 6 prompts/explanations with a bare `$` (money) showed red KaTeX errors | `$` is special in KaTeX | `backend/app/content/level5.yaml` (`\$`) |
| 16 | `test_cors_headers` failed | Test did not send a real browser "preflight" header | `backend/tests/test_api.py` |
| 17 | Test database had no questions | Tests did not load content | `backend/tests/test_api.py` (seeds content) |
| 18 | `npx tsc --noEmit` failed with ~25 errors | Unused imports/variables, missing `XCircle` import, wrong prop types (`className`), `token_hash` vs `tokenHash`, undefined `correct_option_id`, `global` in test setup | `frontend/src/**` (App, Sidebar, Dashboard, Insights, Journey, Practice, Progress, api/client, MathDisplay, test-setup) |
| 19 | `npm run lint` failed: "ESLint couldn't find a configuration file" | No ESLint config and no TypeScript parser | new `frontend/.eslintrc.cjs`, `frontend/package.json` + lock (adds `@typescript-eslint/*`) |
| 20 | `npm run test` never finished (watch mode) and the only test file used Jest (not installed) with wrong paths | | `frontend/package.json` (`vitest run`, `test:watch`), `frontend/src/App.test.tsx` rewritten for Vitest |
| 21 | Frontend: a new learner was created on every redraw of the dashboard; other pages had no learner (401) if opened first; stale token after DB reset locked the user out | Side effect during render; token created only on dashboard | `frontend/src/App.tsx` (create once, with retry button), `Dashboard.tsx`, `api/client.ts` (forget token on 401) |
| 22 | Error messages from server never shown properly; "session complete" detection by text | Client read `message` but FastAPI sends `detail` | `frontend/src/api/client.ts` (`ApiError` with status), `Journey.tsx` |
| 23 | During a lesson the question changed to the next one before the learner read the feedback; correct answer was never highlighted; page opened by URL could not submit; two sessions started in dev mode | | `frontend/src/pages/Journey.tsx`, backend returns `correct_option_id` in feedback |
| 24 | "Reset my data" did nothing | Request was sent without the token | `frontend/src/pages/Progress.tsx` |
| 25 | Level cards had no description; Insights showed no explanation text; Dashboard "latest retest" showed wrong score; level pill showed wrong name; "0" printed on Insights | Mismatched field names / wrong counting | `LearningMap.tsx`, `backend/app/api/insights.py` + `schemas`, `backend/app/api/learners.py`, `Journey.tsx`, `Insights.tsx` |
| 26 | Sentences in questions ran together ("Whichcomparisoniscorrect?") and stuck out of the screen | KaTeX drops spaces; everything was rendered as maths | new `frontend/src/lib/mathText.ts` (+ tests), `components/MathDisplay.tsx`, `index.css` |
| 27 | Sidebar links unstyled (blue underlined); phone layout scrolled sideways | CSS targeted `button`, but links are used; grid column could grow | `frontend/src/index.css` |
| 28 | Google Fonts were blocked by the app's own security policy (console errors) and contradicted "no third-party" privacy claim | | `frontend/index.html` |
| 29 | End-to-end tests never found any test file, tried to start Docker, used `import('axe-core')` in the browser, wrong selectors, assumed hidden sidebar | | `e2e/playwright.config.ts`, `e2e/app.spec.ts` |
| 30 | CI ignored type-check failures; Render could not reach the app if it assigns its own port | | `.github/workflows/ci.yml`, `Dockerfile` (`$PORT`) |
| 31 | README pointed to a missing `.env.example` (and `.gitignore` would have hidden it) | | new `.env.example`, `.gitignore` |
| 32 | Unknown `/api/...` URLs returned the web page; `/api/docs` link in the root message was wrong; favicon returned the page | | `backend/app/main.py` |

## Enhancements (extra, not bug fixes – each is separate)
1. `scripts/start.sh` – one-command install, build and run.
2. `.env.example` with explanations.
3. "Try again" screen if the server cannot be reached at first load (cold start hint); "Loading your question" status text.
4. Correct answer highlighted after answering; button reads "See my progress →" at the end; double submit prevented.
5. Automatic recovery from an outdated saved token.
6. Sentences + maths rendered properly (wrap on small screens).
7. `/api/docs` and `/api/openapi.json` placed under `/api`; real 404 for unknown API URLs.
8. Insights now include plain-language wording, step and "why it matters" text.
9. New tests: full API journey (both branches), message splitting, dashboard; new browser test `e2e/full-journey.spec.ts` (new learner → all questions → results).
10. Default `.env` Postgres address forms (`postgres://`, `+psycopg`) accepted.

## Verification (all run on the final code)
- Backend: `cd backend && ENV=test pytest` → **42 passed**.
- Frontend: `npx tsc --noEmit` clean; `npm run lint` clean (0 warnings); `npm test` → 7 passed; `npm run build` OK.
- Browser tests (Playwright, headless Chrome): desktop + phone profiles → **14 passed**; plus `full-journey` click-through passed: diagnostic ×4 → follow-up → practice ×3 → retest ×3 → progress page (75 XP shown).
- Real start from a fresh clone with `./scripts/start.sh` → health OK, `scripts/smoke.sh` "All smoke tests passed"; same smoke test against PostgreSQL 16 also passed.
- Run the tests yourself: backend `cd backend && python -m venv venv && . venv/bin/activate && pip install -r requirements.txt && ENV=test pytest`; frontend `cd frontend && npm ci && npm run lint && npx tsc --noEmit && npm test && npm run build`; browser `cd e2e && npm install && npx playwright install chromium && npx playwright test --project=chromium --project=mobile-chrome` (starts the app by itself).

## Known leftovers (not changed, low risk)
- Pydantic/other libraries may print deprecation notices; harmless.
- `python-jose`, `passlib`, `slowapi` are installed but unused (rate limiting mentioned in README is not implemented). Not changed: it would be a new feature.
- Some answer-explanation rules in `sessions.py` keep the original simplified "has follow-up" rule of thumb.
