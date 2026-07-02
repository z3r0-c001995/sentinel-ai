# Sentinel AI — MVP Specification
**ZICTA ICT Innovation Programme 2026 | Phase 0 Draft**

## 1. Problem
SMEs, MSSPs, and mid-sized institutions in Zambia lack affordable, proactive
endpoint monitoring. Existing tools are either enterprise-priced (CrowdStrike,
SentinelOne) or purely reactive (basic antivirus, manual log review). Threats
are detected only after damage occurs.

## 2. MVP Scope (what we are building for the pitch — not the full platform)
A lightweight Rust endpoint agent that monitors a single host for behavioral
anomalies, ships events to a backend, scores them with a simple ML model, and
surfaces flagged events with an explanation on a live dashboard.

**Explicitly out of scope for MVP:** Kafka/Spark streaming, Kubernetes,
Neo4j graph analytics, LLM reasoning, autonomous remediation, multi-tenancy.
These remain on the long-term roadmap (see Master Plan) and are referenced in
the pitch as "where this goes," not what's demoed.

## 3. Data Collected
- Running processes (name, PID, parent PID, CPU/memory, start time)
- Active network connections (local/remote IP, port, protocol, process owner)
- File system events on a small set of watched paths (create/modify/delete)
- Login/auth attempts (success/failure count, source)

## 4. What It Detects (MVP detection logic)
- **Process anomalies**: unrecognized process spawning from sensitive paths,
  unusual parent-child process chains
- **Network anomalies**: connections to unexpected ports/IPs, beaconing-like
  regular-interval outbound traffic
- **Auth anomalies**: repeated failed logins (brute-force pattern)
- Scoring via Isolation Forest (unsupervised) trained on a public IDS dataset
  (CICIDS2017 or UNSW-NB15) plus live baseline of the demo host, so the model
  has real behavior to compare against rather than synthetic-only data.

## 5. The Demo (what judges will see)
1. Dashboard shows a live "all clear" baseline of a monitored host.
2. A simulated attack scenario runs (e.g., port scan + brute-force login
   attempt + suspicious process spawn).
3. Dashboard flags the anomaly in near real-time with:
   - What was detected
   - Why it was flagged (contributing features/score)
   - A suggested response action (manual-approval stage — no auto-remediation
     in MVP, by design, for safety and judge trust)

## 6. Target Customer (initial wedge)
Zambian SMEs and mid-sized institutions (fintech/digital financial services
first — high risk exposure, some budget, no dedicated SOC). Long-term
expansion path: MSSPs reselling Sentinel as a monitoring layer, then
government/critical infrastructure per the full Master Plan.

## 7. Tech Stack (MVP)
| Layer | Choice | Why |
|---|---|---|
| Agent | Rust (`sysinfo`, `procfs`, `serde`, `reqwest`) | Kernel-adjacent visibility, low resource footprint, credible "real agent" for judges |
| Transport | HTTPS + JSON to backend REST API | Simple, fast to build, upgradeable to Kafka later |
| Backend | Python (FastAPI) | Fast iteration, strong ML ecosystem |
| ML | scikit-learn Isolation Forest | Explainable enough for MVP, fast to train |
| Storage | SQLite (dev) → Postgres (demo-hardened) | Zero-ops for dev, easy upgrade |
| Dashboard | Streamlit | Fastest path to a live, real-time-feeling UI |

## 8. Success Criteria for This MVP
- Agent runs on a Linux VM and streams real telemetry for 10+ minutes without crashing
- At least 3 distinct anomaly types correctly flagged in a scripted demo scenario
- Dashboard updates within ~5 seconds of an event being flagged
- End-to-end demo is repeatable and doesn't depend on live internet/luck
