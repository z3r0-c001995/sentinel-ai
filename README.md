<<<<<<< HEAD
# sentinel-ai
=======
# Sentinel AI (MVP) — ZICTA ICT Innovation Programme 2026

Autonomous Predictive Cyber Defense Platform — MVP scope for the 2026 ZICTA
ICT Innovation Programme.

> This repo implements the narrow, demo-able slice defined in
> [`docs/MVP_SPEC.md`](docs/MVP_SPEC.md). The full long-term architecture
> (Kafka/Spark, Neo4j, LLM reasoning, autonomous remediation, multi-tenancy)
> is documented separately in the project's Master Plan and is **not** part
> of this MVP build.

## Architecture (MVP)

```
[ Rust Agent ] --HTTPS/JSON--> [ FastAPI Backend ] --scores--> [ SQLite ]
  (sysinfo)                     (Isolation Forest)                 |
                                                                     v
                                                         [ Streamlit Dashboard ]
```

## Components

| Folder | What it is |
|---|---|
| `agent/` | Rust endpoint monitoring agent (process/system telemetry) |
| `backend/` | FastAPI ingestion API + Isolation Forest anomaly scoring |
| `dashboard/` | Streamlit live monitoring dashboard |
| `docs/` | MVP spec and supporting docs |

## Running locally

### 1. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. Dashboard
```bash
cd dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard.py
```

### 3. Agent
```bash
cd agent
cargo run -- --endpoint http://127.0.0.1:8000/events --interval 5
```

Then open the Streamlit dashboard URL printed in your terminal — you should
see live telemetry within a few seconds.

## Testing
- Rust: `cd agent && cargo test`
- Python: `cd backend && pytest`
- Both run automatically in CI on every push (`.github/workflows/ci.yml`)

## Roadmap
See `docs/MVP_SPEC.md` for MVP scope and the project Master Plan for the
full platform roadmap (Phases 1–5, per the engineering master plan).

## Programme Context
Built for the ZICTA ICT Innovation Programme 2026 cohort.
Schedule and milestones tracked against the official programme calendar.
>>>>>>> 25315d7 (intial commit)
