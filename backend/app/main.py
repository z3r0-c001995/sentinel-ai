"""
Sentinel AI — Backend (MVP)

Receives snapshot events from the Rust agent, extracts features, scores
anomalies with an Isolation Forest, and stores flagged + raw events for the
dashboard to read.

MVP scope: single-process FastAPI + SQLite. Swap SQLite -> Postgres and add
Kafka in front of this when moving past the pitch demo (see MVP_SPEC.md).
"""

from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine, text

app = FastAPI(title="Sentinel AI Backend (MVP)")

DB_PATH = "sqlite:///./sentinel.db"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})


def init_db():
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_id TEXT,
                    timestamp TEXT,
                    total_processes INTEGER,
                    system_cpu_usage REAL,
                    system_memory_used_kb INTEGER,
                    system_memory_total_kb INTEGER,
                    anomaly_score REAL,
                    is_flagged INTEGER,
                    reason TEXT
                )
                """
            )
        )


init_db()

# --- Simple baseline model -------------------------------------------------
# MVP: trained lazily on the first N snapshots seen as a rolling baseline.
# Replace with a model pre-trained on CICIDS2017/UNSW-NB15 before the demo
# for more credible "learned attacker behavior" framing.
_model = IsolationForest(contamination=0.1, random_state=42)
_baseline_buffer: List[List[float]] = []
_MIN_BASELINE_SAMPLES = 10
_model_ready = False


class ProcessEvent(BaseModel):
    pid: int
    parent_pid: Optional[int] = None
    name: str
    exe_path: Optional[str] = None
    cpu_usage: float
    memory_kb: int
    start_time: int


class AgentPayload(BaseModel):
    host_id: str
    timestamp: str
    event_type: str
    processes: List[ProcessEvent]
    total_processes: int
    system_cpu_usage: float
    system_memory_used_kb: int
    system_memory_total_kb: int


def extract_features(payload: AgentPayload) -> List[float]:
    """Turn a raw snapshot into a feature vector for scoring."""
    mem_ratio = (
        payload.system_memory_used_kb / payload.system_memory_total_kb
        if payload.system_memory_total_kb
        else 0.0
    )
    return [
        float(payload.total_processes),
        float(payload.system_cpu_usage),
        float(mem_ratio),
    ]


def score_event(features: List[float]) -> tuple[float, bool, str]:
    """Score a feature vector. Falls back to 'not flagged' until the model
    has enough baseline data to be meaningful."""
    global _model_ready

    _baseline_buffer.append(features)

    if not _model_ready:
        if len(_baseline_buffer) >= _MIN_BASELINE_SAMPLES:
            _model.fit(_baseline_buffer)
            _model_ready = True
        return 0.0, False, "baseline warming up"

    score = _model.decision_function([features])[0]
    is_anomaly = _model.predict([features])[0] == -1

    reason = "within normal range"
    if is_anomaly:
        reason = "deviates from established host baseline (process count / CPU / memory pattern)"

    return float(score), bool(is_anomaly), reason


@app.post("/events")
def ingest_event(payload: AgentPayload):
    features = extract_features(payload)
    score, is_flagged, reason = score_event(features)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO events
                (host_id, timestamp, total_processes, system_cpu_usage,
                 system_memory_used_kb, system_memory_total_kb,
                 anomaly_score, is_flagged, reason)
                VALUES
                (:host_id, :timestamp, :total_processes, :cpu,
                 :mem_used, :mem_total, :score, :flagged, :reason)
                """
            ),
            {
                "host_id": payload.host_id,
                "timestamp": payload.timestamp,
                "total_processes": payload.total_processes,
                "cpu": payload.system_cpu_usage,
                "mem_used": payload.system_memory_used_kb,
                "mem_total": payload.system_memory_total_kb,
                "score": score,
                "flagged": int(is_flagged),
                "reason": reason,
            },
        )

    return {
        "received": True,
        "anomaly_score": score,
        "is_flagged": is_flagged,
        "reason": reason,
    }


@app.get("/events/recent")
def recent_events(limit: int = 50):
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT * FROM events ORDER BY id DESC LIMIT :limit"),
            {"limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
