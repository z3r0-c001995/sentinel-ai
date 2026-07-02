"""Basic tests for the Sentinel AI backend (MVP)."""

from fastapi.testclient import TestClient

from app.main import app, extract_features, AgentPayload, ProcessEvent

client = TestClient(app)


def sample_payload(total_processes=120, cpu=15.0, mem_used=4_000_000, mem_total=16_000_000):
    return {
        "host_id": "test-host",
        "timestamp": "2026-07-02T12:00:00+00:00",
        "event_type": "snapshot",
        "processes": [
            {
                "pid": 1234,
                "parent_pid": 1,
                "name": "test-proc",
                "exe_path": "/usr/bin/test-proc",
                "cpu_usage": 1.5,
                "memory_kb": 2048,
                "start_time": 1000,
            }
        ],
        "total_processes": total_processes,
        "system_cpu_usage": cpu,
        "system_memory_used_kb": mem_used,
        "system_memory_total_kb": mem_total,
    }


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_event_accepts_valid_payload():
    resp = client.post("/events", json=sample_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["received"] is True
    assert "anomaly_score" in body
    assert "is_flagged" in body


def test_recent_events_returns_list():
    client.post("/events", json=sample_payload())
    resp = client.get("/events/recent?limit=5")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_extract_features_computes_memory_ratio():
    payload = AgentPayload(**sample_payload(mem_used=5000, mem_total=10000))
    features = extract_features(payload)
    assert len(features) == 3
    assert features[2] == 0.5  # mem_used / mem_total
