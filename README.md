# MisconceptionMap — Beyond Right and Wrong

An educational diagnostic web app for middle-school students learning algebra. It tells a student not just *that* an answer is wrong but investigates *why*, treating each wrong answer as **evidence for a testable hypothesis**, never as a verdict.

## Features

- **Diagnostic Engine**: Server-side state machine that gathers evidence across diagnostic, follow-up, practice, and retest phases
- **Evidence-Based Hypotheses**: Three certainty levels (Insufficient, Possible, Supported) with transparent evidence trails
- **Five Algebra Levels**: Foundations → Expressions → Algebra Essentials → Equation Solver → Challenge Lab
- **Honest Feedback**: Never labels learners; shows "consistent with..." not "you have..."
- **Anonymous Learning**: No accounts, no PII, progress saved under random token
- **Full-Stack**: Python/FastAPI backend, React/TypeScript frontend, PostgreSQL database

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Container                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Nginx      │    │   FastAPI    │    │  PostgreSQL  │  │
│  │  (Static)    │◄───│   (API)      │◄───│  (Neon)      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, KaTeX
- **Database**: PostgreSQL (Neon free tier in production)
- **Hosting**: Render (Docker web service, Singapore region, free tier)
- **CI/CD**: GitHub Actions (tests, type-check, Docker build, secret scan)

## Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node 20+ (for frontend development)
- Python 3.12+ (for backend development)

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/sonalhonny71/misconception-map.git
cd misconception-map

# Create environment file
cp .env.example .env
# Edit .env with your settings (or use defaults for local dev)

# Start everything
docker compose up --build

# App available at http://localhost:8000
```

### Manual Development Setup

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with DATABASE_URL (or use local SQLite)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173 (proxies API to localhost:8000)
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Neon pooled Postgres URL (production) | Yes (prod) |
| `DATABASE_URL_DIRECT` | Neon direct Postgres URL (migrations) | Yes (prod) |
| `SECRET_KEY` | 64-char hex for token signing | Yes |
| `ENV` | `development` or `production` | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | Yes |
| `RENDER_API_KEY` | For deployment automation | No |

Create `.env` from `.env.example`:
```bash
cp .env.example .env
```

## Project Structure

```
misconception-map/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── core/          # Config, security
│   │   ├── db/            # Models, sessions
│   │   ├── engine/        # Diagnostic engine (pure Python)
│   │   ├── content/       # Content loader (YAML)
│   │   ├── schemas/       # Pydantic schemas
│   │   └── main.py        # FastAPI app
│   ├── tests/             # Pytest tests
│   ├── alembic/           # Migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # Route components
│   │   ├── components/    # Shared components
│   │   ├── api/           # API client
│   │   ├── hooks/         # React hooks
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── e2e/                   # Playwright tests
├── Dockerfile
├── docker-compose.yml
├── render.yaml
├── .github/workflows/ci.yml
└── README.md
```

## Content Authoring

Content lives in `backend/app/content/level{1-5}.yaml`. Each item has:

```yaml
- item_id: "unique-id"
  level: 3
  skill: "distributive-inverse"
  kind: "diagnostic"  # or followup, practice, retest, check
  prompt: "LaTeX math: 3(x + 2) = 15"
  options:
    - id: "opt-1"
      text: "3x + 6 = 15"
      misconception_id: null
      note: "Correct"
    - id: "opt-2"
      text: "3x + 2 = 15"
      misconception_id: "DIST_PARTIAL"
      note: "Partial distribution"
  correct_option_id: "opt-1"
  explanation: "LaTeX explanation"
  discriminates: ["DIST_PARTIAL", "LIKE_UNLIKE"]
  targets: ["DIST_PARTIAL"]  # for practice items
```

Run content verification:
```bash
cd backend
pytest tests/test_content_verification.py -v
```

## Testing

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm run test

# E2E tests (requires running app)
cd e2e
npm install
npx playwright install
npx playwright test --base-url=http://localhost:8000
```

## Deployment

### Render (Configured via render.yaml)

1. Connect GitHub repo to Render
2. Create Docker web service from `render.yaml`
3. Add environment variables in Render dashboard:
   - `DATABASE_URL` (Neon pooled)
   - `DATABASE_URL_DIRECT` (Neon direct)
   - `SECRET_KEY` (auto-generated)
   - `ENV=production`
   - `ALLOWED_ORIGINS=https://your-app.onrender.com`
   - `RENDER_API_KEY` (optional)

### Manual Docker Deploy

```bash
docker build -t misconception-map .
docker run -d -p 8000:8000 \
  -e DATABASE_URL=... \
  -e DATABASE_URL_DIRECT=... \
  -e SECRET_KEY=... \
  -e ENV=production \
  -e ALLOWED_ORIGINS=https://your-domain.com \
  misconception-map
```

## Free Tier Resources

- **Neon Postgres**: Free tier (0.5 GB storage, compute sleeps after 5 min idle)
- **Render**: Free Docker web service (sleeps after 15 min idle, 750 hrs/month)
- **GitHub Actions**: Free for public repos, 2000 min/month for private

**Cold starts**: First request after sleep takes ~30 seconds. The UI shows a "Waking up..." message with automatic retry.

**Optional**: Set up a free uptime pinger (e.g., UptimeRobot) to ping `/api/health` every 5 minutes to keep the service warm.

## Security

- No PII collected (anonymous tokens only)
- Tokens hashed with SHA-256 before storage
- CSP, security headers, rate limiting
- No inline scripts, no third-party trackers
- All secrets via environment variables
- Secret scanning in CI (gitleaks + pattern checks)

## Documentation

- `ENGINE.md` — Diagnostic engine rules, evidence thresholds, state machine
- `CONTENT.md` — Misconception catalogue, authoring guide
- `DECISIONS.md` — Judgment calls made during development

## License

MIT License — Educational prototype for demonstration purposes.

## Acknowledgments

Built for the MisconceptionMap project. Based on research about formative assessment and misconception diagnosis in mathematics education.