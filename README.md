# AI SQL Agent

AI SQL Agent is an end-to-end analytics assistant that converts natural language questions into SQL, executes them on SQLite, and returns business-friendly answers with reasoning traces.

The project uses Uber Eats order data and supports three interfaces:
- React + Tailwind web app (recommended)
- FastAPI backend API
- CLI for terminal usage

## Key Features

- Natural language to SQL using LangChain + Mistral
- Deterministic SQL generation with temperature 0
- SQLite analytics over a single scoped table: orders
- Tool-level reasoning traces (SQL tools and observations)
- Modern chat UI in React + Tailwind with:
  - query history
  - generated SQL display
  - collapsible reasoning steps
  - basic session metrics

## Architecture

1. Frontend sends user questions to FastAPI.
2. FastAPI reuses a cached LangChain agent executor.
3. Agent calls SQL toolkit tools (schema lookup, query checker, query execution).
4. Backend returns structured output:
   - question
   - sql
   - answer
   - steps
   - error
5. Frontend renders answer, SQL, and reasoning trace.

## Project Structure

- agent.py: Core agent pipeline (DB, LLM, tools, executor, query runners)
- api.py: FastAPI API layer for frontend integration
- frontend/: React + Tailwind app (Vite)
- cli.py: Terminal interface
- app.py: Legacy Streamlit UI
- config.py: Runtime configuration and API-key checks
- prompts.py: System prompt and SQL guardrails
- setup_db.py: CSV-to-SQLite loader
- requirements.txt: Python dependencies
- data/ubereats_sales.csv: Source dataset
- orders.db: Generated SQLite database

## Prerequisites

- Python 3.10+
- Node.js 18+
- Mistral API key from https://console.mistral.ai/

## Setup

### 1. Create and activate virtual environment

Windows CMD:

```bat
python -m venv venv
venv\Scripts\activate
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a .env file in project root:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
FRONTEND_ORIGIN=http://localhost:5173
```

### 4. Build local database

```bash
python setup_db.py
```

## Run the App (Recommended)

### Terminal 1: Start API

```bash
uvicorn api:app --reload --port 8000
```

### Terminal 2: Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

If needed, set frontend API base URL:

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## API Endpoints

- GET /api/health
  - Returns backend health and validates agent initialization.
- GET /api/examples
  - Returns default sample analytics prompts.
- POST /api/query
  - Request body:
    - question: string
  - Response body:
    - question: string
    - sql: string | null
    - answer: string
    - steps: list
    - error: boolean

## Other Run Modes

### CLI

```bash
python cli.py
```

### Legacy Streamlit UI

```bash
streamlit run app.py
```

## Configuration

Update config.py to tune behavior:

- DB_PATH: SQLite file path
- MODEL_NAME: Mistral model name
- TEMPERATURE: keep at 0 for SQL reliability
- VERBOSE: enable/disable tool trace logging

## SQL Safety and Reliability

Prompt guardrails in prompts.py enforce:

- only known tables/columns
- SQLite-valid SQL
- no hallucinated schema

These constraints improve consistency and reduce invalid SQL generation.

## Tech Stack

- Python
- LangChain
- Mistral API
- SQLite + SQLAlchemy
- FastAPI
- React (Vite)
- Tailwind CSS

## License

No license file is included yet. Add one before public distribution.
