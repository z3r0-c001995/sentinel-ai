"""
Sentinel AI — Dashboard (MVP)

Live view over the backend's /events/recent endpoint. Auto-refreshes and
highlights flagged (anomalous) events with the reason they were flagged.

Run with: streamlit run dashboard.py
"""

import time

import pandas as pd
import requests
import streamlit as st

BACKEND_URL = "http://127.0.0.1:8000"
REFRESH_SECONDS = 5

st.set_page_config(page_title="Sentinel AI — Live Monitor", layout="wide")
st.title("🛡️ Sentinel AI — Live Endpoint Monitor (MVP)")
st.caption(
    "Real-time view of agent telemetry and anomaly detections. "
    "Refreshes every {}s.".format(REFRESH_SECONDS)
)

placeholder = st.empty()


def fetch_events():
    try:
        resp = requests.get(f"{BACKEND_URL}/events/recent", params={"limit": 100}, timeout=3)
        resp.raise_for_status()
        return pd.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Could not reach backend at {BACKEND_URL}: {e}")
        return pd.DataFrame()


def render(df: pd.DataFrame):
    with placeholder.container():
        if df.empty:
            st.info("No events received yet. Start the agent to begin streaming telemetry.")
            return

        flagged = df[df["is_flagged"] == 1]
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Events", len(df))
        col2.metric("Flagged Anomalies", len(flagged))
        col3.metric("Hosts Monitored", df["host_id"].nunique())

        if not flagged.empty:
            st.subheader("🚨 Flagged Anomalies")
            st.dataframe(
                flagged[
                    ["timestamp", "host_id", "total_processes", "system_cpu_usage",
                     "anomaly_score", "reason"]
                ].sort_values("timestamp", ascending=False),
                use_container_width=True,
            )
        else:
            st.success("No anomalies flagged. All monitored hosts within baseline.")

        st.subheader("System Metrics Over Time")
        chart_df = df.sort_values("id")[["id", "system_cpu_usage", "total_processes"]]
        st.line_chart(chart_df.set_index("id"))

        st.subheader("Raw Event Log")
        st.dataframe(df.sort_values("id", ascending=False), use_container_width=True)


# Simple polling loop (MVP — fine for a demo; swap for websockets/SSE later)
df = fetch_events()
render(df)

if st.button("Refresh now"):
    st.rerun()
