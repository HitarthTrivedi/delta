# Delta 2.0

Delta 2.0 is a career intelligence web app with a FastAPI backend and a React frontend. The backend exposes career, skills, chat, resume, calendar, dossier, onboarding, and weekly brief APIs. The frontend is a Create React App/CRACO application that talks to the backend at `http://localhost:8000/api`.

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — system architecture: layers, data model, API reference, request lifecycle, frontend structure, and the performance/caching design. Start here to understand or track the codebase.
- **[docs/DELTA_CAREER_OS_BLUEPRINT.md](docs/DELTA_CAREER_OS_BLUEPRINT.md)** — the product vision and the ten system pillars.

## Tech Stack

- Frontend: React 18, Create React App, CRACO, Tailwind CSS, Radix UI, React Router, Axios, Zustand, TanStack React Query, Framer Motion, Recharts
- Backend: Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Pydantic, python-dotenv
- Database: SQLite by default through SQLAlchemy
- AI/search integrations: OpenAI, Google Gemini, Tavily
- Container support: Dockerfile for the backend and `docker-compose.yml`

## Project Structure

```text
.
├── backend/              # FastAPI application
│   ├── app/main.py       # Main API entry point
│   ├── app/routers/      # API routes under /api
│   ├── app/services/     # Business logic and integrations
│   └── requirements.txt  # Python dependencies
├── frontend/             # React application
│   ├── src/              # React source
│   └── package.json      # Frontend dependencies and scripts
├── docker-compose.yml    # Backend container setup
└── README.md
```

## Prerequisites

Install these before running the project:

- Python 3.11 or newer
- Node.js 18 or newer
- npm
- Docker, optional

## Environment Setup

Create backend and frontend environment files from the examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

For local SQLite, set this in `backend/.env`:

```env
DATABASE_URL=sqlite:///./delta.db
```

The checked-in `backend/.env.example` currently shows `sqlite+aiosqlite:///./delta.db`, but this backend uses SQLAlchemy's synchronous `create_engine`, so `sqlite:///./delta.db` is the safer local value.

Optional API keys can be added to `backend/.env`:

```env
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
TAVILY_API_KEY=your_tavily_key_here
RESEND_API_KEY=your_resend_key_here
EMAIL_FROM=onboarding@resend.dev
```

### Caching (optional)

Delta caches deterministic work (market data, web search, embeddings) in Redis with a graceful in-process fallback. Redis is **optional** — if it is unreachable, the app transparently uses a per-process cache and behaves identically.

```env
REDIS_URL=redis://localhost:6379/0   # optional; defaults to this
CACHE_ENABLED=true                   # set false to disable caching entirely
```

See [docs/ARCHITECTURE.md §11](docs/ARCHITECTURE.md#11-performance--caching-architecture) for the full caching design.

The frontend API URL should be:

```env
REACT_APP_API_URL=http://localhost:8000/api
```

## Run Locally

Open two terminal windows from the project root.

### 1. Start the Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check that the backend is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"healthy"}
```

API docs are available at:

```text
http://localhost:8000/docs
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm start
```

The frontend runs at:

```text
http://localhost:3000
```

## Run Backend with Docker

From the project root:

```bash
docker compose up --build
```

This starts the backend on:

```text
http://localhost:8000
```

You still need to run the frontend separately:

```bash
cd frontend
npm install
npm start
```

## Useful Commands

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest
python seed_guest.py
python test_keys.py
```

Frontend:

```bash
cd frontend
npm start
npm test
npm run build
```

## Notes

- Use `backend/app/main.py` as the backend entry point.
- `backend/server.py` appears to be an older MongoDB-based server and is not used by the current Dockerfile or local FastAPI run command.
- The backend creates SQLite tables automatically on startup through `Base.metadata.create_all(bind=engine)`.
- If the frontend cannot reach the backend, confirm `REACT_APP_API_URL=http://localhost:8000/api` in `frontend/.env` and restart `npm start`.
