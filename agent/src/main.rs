// Sentinel AI — Lightweight Endpoint Agent (MVP)
//
// Polls local system state (processes, resource usage) on an interval and
// ships structured JSON events to the Sentinel backend for scoring.
//
// MVP scope: userspace polling via `sysinfo`. Kernel-level probes (eBPF via
// `aya`) are a Phase 4 upgrade — see docs/MVP_SPEC.md for rationale.

use anyhow::Result;
use chrono::Utc;
use clap::Parser;
use serde::Serialize;
use std::time::Duration;
use sysinfo::System;

#[derive(Parser, Debug)]
#[command(name = "sentinel-agent")]
#[command(about = "Sentinel AI endpoint monitoring agent (MVP)")]
struct Args {
    /// Backend ingestion endpoint
    #[arg(long, default_value = "http://127.0.0.1:8000/events")]
    endpoint: String,

    /// Polling interval in seconds
    #[arg(long, default_value_t = 5)]
    interval: u64,

    /// Unique identifier for this host (defaults to system hostname)
    #[arg(long)]
    host_id: Option<String>,
}

#[derive(Serialize, Debug)]
struct ProcessEvent {
    pid: u32,
    parent_pid: Option<u32>,
    name: String,
    exe_path: Option<String>,
    cpu_usage: f32,
    memory_kb: u64,
    start_time: u64,
}

#[derive(Serialize, Debug)]
struct AgentPayload {
    host_id: String,
    timestamp: String,
    event_type: String,
    processes: Vec<ProcessEvent>,
    total_processes: usize,
    system_cpu_usage: f32,
    system_memory_used_kb: u64,
    system_memory_total_kb: u64,
}

fn collect_snapshot(sys: &mut System, host_id: &str) -> AgentPayload {
    sys.refresh_all();

    let processes: Vec<ProcessEvent> = sys
        .processes()
        .values()
        .map(|p| ProcessEvent {
            pid: p.pid().as_u32(),
            parent_pid: p.parent().map(|pp| pp.as_u32()),
            name: p.name().to_string_lossy().to_string(),
            exe_path: p.exe().map(|e| e.to_string_lossy().to_string()),
            cpu_usage: p.cpu_usage(),
            memory_kb: p.memory(),
            start_time: p.start_time(),
        })
        .collect();

    AgentPayload {
        host_id: host_id.to_string(),
        timestamp: Utc::now().to_rfc3339(),
        event_type: "snapshot".to_string(),
        total_processes: processes.len(),
        processes,
        system_cpu_usage: sys.global_cpu_usage(),
        system_memory_used_kb: sys.used_memory(),
        system_memory_total_kb: sys.total_memory(),
    }
}

fn main() -> Result<()> {
    let args = Args::parse();
    let host_id = args
        .host_id
        .unwrap_or_else(|| System::host_name().unwrap_or_else(|| "unknown-host".to_string()));

    println!(
        "[sentinel-agent] starting. host_id={} endpoint={} interval={}s",
        host_id, args.endpoint, args.interval
    );

    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()?;

    let mut sys = System::new_all();

    loop {
        let payload = collect_snapshot(&mut sys, &host_id);

        match client.post(&args.endpoint).json(&payload).send() {
            Ok(resp) => {
                println!(
                    "[sentinel-agent] sent snapshot ({} processes) -> {}",
                    payload.total_processes,
                    resp.status()
                );
            }
            Err(e) => {
                eprintln!("[sentinel-agent] failed to send snapshot: {e}");
            }
        }

        std::thread::sleep(Duration::from_secs(args.interval));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn snapshot_contains_at_least_one_process() {
        let mut sys = System::new_all();
        let payload = collect_snapshot(&mut sys, "test-host");
        assert!(payload.total_processes > 0);
        assert_eq!(payload.host_id, "test-host");
    }

    #[test]
    fn snapshot_has_valid_timestamp_format() {
        let mut sys = System::new_all();
        let payload = collect_snapshot(&mut sys, "test-host");
        assert!(chrono::DateTime::parse_from_rfc3339(&payload.timestamp).is_ok());
    }
}
