"""
CryoGuard — Cold Chain Integrity Monitor
==========================================
Hackathon proof-of-concept: HMI-style dashboard for monitoring
temperature-sensitive medical cargo (Blood / Organ / Vaccine) in
transit, with redundant fail-safe sensor voting, a transparent
predictive-confidence model, route-viability checking, and an
auto-generated PDF compliance report.

Run with:
    streamlit run app.py
"""

import time
import pandas as pd
import streamlit as st

from logic.thresholds import CARGO_PROFILES, DEFAULT_CARGO_MODE, NUM_SENSORS
from logic.voting import median_vote, quorum_vote
from logic.state_engine import evaluate_state, update_critical_lock
from logic.prediction import update_stress, predictive_confidence, estimated_safe_hours, route_viability
from logic.report import build_pdf_report

# ----------------------------------------------------------------------
# Page config + styling
# ----------------------------------------------------------------------
st.set_page_config(page_title="CryoGuard", page_icon="\U0001F9CA", layout="wide")

STATE_COLOR = {"SAFE": "#1f8a44", "WARNING": "#c47d0a", "CRITICAL": "#c0332b", "LOCKED": "#7a1f1f"}

st.markdown("""
<style>
    .stApp { background-color: #0c1117; }
    section[data-testid="stSidebar"] { background-color: #10161d; border-right: 1px solid #232b35; }
    div[data-testid="stMetric"] {
        background-color: #131a22; border: 1px solid #232b35; border-radius: 10px;
        padding: 12px 14px 6px 14px;
    }
    div[data-testid="stMetricLabel"] { color: #8a97a8 !important; font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: #e7edf3 !important; }
    p, li, span, label { color: #c3ccd6; }
    .status-banner {
        border-radius: 10px; padding: 16px 20px; text-align: center;
        font-size: 1.5rem; font-weight: 700; letter-spacing: 2px; color: white;
        font-family: 'Courier New', monospace; margin-bottom: 8px;
    }
    .reason-box {
        background-color: #131a22; border-left: 3px solid #c47d0a; border-radius: 4px;
        padding: 8px 14px; margin-bottom: 4px; font-size: 0.9rem;
    }
    .locked-box {
        background-color: #2b1414; border: 1px solid #7a1f1f; border-radius: 8px;
        padding: 14px 18px; margin-top: 10px;
    }
    .section-card {
        background-color: #131a22; border: 1px solid #232b35; border-radius: 10px;
        padding: 14px 18px; margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Session state initialization
# ----------------------------------------------------------------------
def fresh_state(cargo_mode: str) -> dict:
    return {
        "cargo_mode": cargo_mode,
        "stress": 0.0,
        "critical_streak_minutes": 0.0,
        "locked": False,
        "tick": 0,
        "total_minutes_elapsed": 0.0,
        "log": [],
    }


if "cg" not in st.session_state:
    st.session_state.cg = fresh_state(DEFAULT_CARGO_MODE)


def do_tick(minutes: float, state: str):
    cg = st.session_state.cg
    if not cg["locked"]:
        cg["stress"] = update_stress(cg["stress"], state, minutes)
        cg["critical_streak_minutes"], cg["locked"] = update_critical_lock(
            state, minutes, cg["critical_streak_minutes"],
            CARGO_PROFILES[cg["cargo_mode"]]["critical_lock_minutes"], cg["locked"],
        )
    cg["total_minutes_elapsed"] += minutes
    cg["tick"] += 1


# ----------------------------------------------------------------------
# Sidebar — manual inputs
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("## \U0001F9CA CryoGuard Controls")

    cargo_mode = st.selectbox("Cargo Mode", list(CARGO_PROFILES.keys()),
                               index=list(CARGO_PROFILES.keys()).index(st.session_state.cg["cargo_mode"]))

    if cargo_mode != st.session_state.cg["cargo_mode"]:
        st.session_state.cg = fresh_state(cargo_mode)

    profile = CARGO_PROFILES[cargo_mode]
    st.caption(f"Ref: {profile['reference']}")

    st.divider()
    st.markdown("### Temperature Sensors (\u00b0C)")
    t_mid = round((profile["temp_min"] + profile["temp_max"]) / 2, 1)
    temp_readings = [
        st.slider(f"Temp Sensor {i+1}", profile["temp_min"] - 15.0, profile["temp_max"] + 15.0,
                   t_mid, 0.1, key=f"temp_{i}_{cargo_mode}")
        for i in range(NUM_SENSORS)
    ]

    st.markdown("### Humidity Sensors (%)")
    h_mid = round((profile["humidity_min"] + profile["humidity_max"]) / 2, 1)
    humidity_readings = [
        st.slider(f"Humidity Sensor {i+1}", 0.0, 100.0, h_mid, 0.5, key=f"hum_{i}_{cargo_mode}")
        for i in range(NUM_SENSORS)
    ]

    st.markdown("### Jolt / Shock Sensors")
    jolt_flags = [
        st.checkbox(f"Jolt Sensor {i+1} triggered", key=f"jolt_{i}_{cargo_mode}")
        for i in range(NUM_SENSORS)
    ]

    st.divider()
    battery_pct = st.slider("Battery Level (%)", 0, 100, 85, key=f"batt_{cargo_mode}")
    total_transit_hours = st.number_input("Total planned transit time (hrs)", 0.5, 200.0, 12.0, 0.5,
                                           key=f"transit_{cargo_mode}")

    with st.expander("Advanced: Voting Sensitivity"):
        temp_dev = st.slider("Temp deviation threshold (\u00b0C)", 0.5, 5.0, 1.5, 0.1)
        hum_dev = st.slider("Humidity deviation threshold (%)", 1.0, 20.0, 8.0, 0.5)
        quorum_frac = st.slider("Jolt quorum fraction", 0.34, 1.0, 0.5, 0.01)

    st.divider()
    st.markdown("### Simulated Clock")
    minutes_per_tick = st.number_input("Minutes per tick", 1, 120, 5)
    col_a, col_b = st.columns(2)
    tick_clicked = col_a.button("\u25B6 Advance Tick", use_container_width=True)
    reset_clicked = col_b.button("\u21BA Reset", use_container_width=True)
    auto_tick = st.checkbox("Live auto-tick (demo)", value=False)
    auto_interval = st.number_input("Auto-tick interval (sec)", 1, 30, 3, disabled=not auto_tick)

    if st.session_state.cg["locked"]:
        st.divider()
        st.error("SHIPMENT LOCKED — human intervention required.")
        if st.button("\U0001F513 Human Override / Unlock", use_container_width=True):
            st.session_state.cg["locked"] = False
            st.session_state.cg["critical_streak_minutes"] = 0.0

    if reset_clicked:
        st.session_state.cg = fresh_state(cargo_mode)
        st.rerun()

# ----------------------------------------------------------------------
# Compute this frame's trusted values (voting)
# ----------------------------------------------------------------------
temp_vote = median_vote(temp_readings, temp_dev)
hum_vote = median_vote(humidity_readings, hum_dev)
jolt_vote = quorum_vote(jolt_flags, quorum_frac)

trusted_temp = temp_vote.trusted_value
trusted_humidity = hum_vote.trusted_value

state_result = evaluate_state(trusted_temp, trusted_humidity, jolt_vote.confirmed, battery_pct, profile)
current_state = state_result.state

cg = st.session_state.cg
transit_hours_remaining = max(0.0, total_transit_hours - cg["total_minutes_elapsed"] / 60.0)

if tick_clicked and not cg["locked"]:
    do_tick(minutes_per_tick, current_state)
elif tick_clicked and cg["locked"]:
    st.toast("Shipment is LOCKED. Override required before ticking forward.", icon="\U0001F512")

confidence = predictive_confidence(cg["stress"])
safe_hours_remaining = estimated_safe_hours(cg["stress"], profile["max_safe_hours"])
route = route_viability(safe_hours_remaining, transit_hours_remaining)

display_state = "LOCKED" if cg["locked"] else current_state

# Log this frame's snapshot on every tick (already advanced above)
if tick_clicked and not cg["locked"]:
    cg["log"].append({
        "tick": cg["tick"], "state": current_state, "temp": trusted_temp,
        "humidity": trusted_humidity, "battery": battery_pct, "route_status": route.status,
        "confidence": confidence, "safe_hours": safe_hours_remaining,
    })

# ----------------------------------------------------------------------
# Main layout
# ----------------------------------------------------------------------
st.title("\U0001F9CA CryoGuard — Cold Chain Integrity Monitor")
st.caption(f"Cargo Mode: **{cargo_mode}**  \u2022  Tick {cg['tick']}  \u2022  "
           f"Elapsed {cg['total_minutes_elapsed']:.0f} min  \u2022  {profile['reference']}")

st.markdown(
    f'<div class="status-banner" style="background-color:{STATE_COLOR[display_state]};">'
    f'STATUS: {display_state}</div>', unsafe_allow_html=True,
)

if cg["locked"]:
    st.markdown(
        '<div class="locked-box">\U0001F512 <b>Shipment locked.</b> Critical state persisted beyond the '
        f'{profile["critical_lock_minutes"]}-minute threshold for {cargo_mode.lower()} cargo. '
        'Use the sidebar override to resume monitoring after human review.</div>',
        unsafe_allow_html=True,
    )

# --- Priority metrics row ---
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Temperature", f"{trusted_temp:.1f} \u00b0C",
          delta=f"band {profile['temp_min']}-{profile['temp_max']}", delta_color="off")
m2.metric("Humidity", f"{trusted_humidity:.1f} %",
          delta=f"band {profile['humidity_min']}-{profile['humidity_max']}", delta_color="off")
m3.metric("Battery", f"{battery_pct:.0f} %")
m4.metric("Predictive Confidence", f"{confidence:.0f} %",
          delta=f"{safe_hours_remaining:.1f} hrs safe remaining", delta_color="off")
route_emoji = {"VIABLE": "\U0001F7E2", "AT RISK": "\U0001F7E1", "NOT VIABLE": "\U0001F534", "DELIVERED": "\U0001F3C1"}
m5.metric("Route Feasibility", f"{route_emoji.get(route.status,'')} {route.status}",
          delta=f"{route.margin_hours:+.1f} hrs margin", delta_color="off")

# --- Reasons ---
if state_result.reasons:
    st.markdown("#### Status Detail")
    for r in state_result.reasons:
        st.markdown(f'<div class="reason-box">{r}</div>', unsafe_allow_html=True)

st.write("")

# --- Secondary info: tabs ---
tab_sensors, tab_trends, tab_report = st.tabs(["\U0001F4E1 Sensor Status", "\U0001F4C8 Log & Trends", "\U0001F4C4 Compliance Report"])

with tab_sensors:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Temperature Sensors**")
        df_t = pd.DataFrame({
            "Sensor": [f"S{i+1}" for i in range(NUM_SENSORS)],
            "Reading (\u00b0C)": temp_readings,
            "Status": ["\u26A0\uFE0F Flagged" if i in temp_vote.flagged_indices else "\u2705 Healthy" for i in range(NUM_SENSORS)],
        })
        st.dataframe(df_t, hide_index=True, use_container_width=True)
        st.caption(f"Raw median: {temp_vote.raw_median:.1f}\u00b0C \u2192 Trusted (healthy only): {trusted_temp:.1f}\u00b0C")

        st.markdown("**Humidity Sensors**")
        df_h = pd.DataFrame({
            "Sensor": [f"S{i+1}" for i in range(NUM_SENSORS)],
            "Reading (%)": humidity_readings,
            "Status": ["\u26A0\uFE0F Flagged" if i in hum_vote.flagged_indices else "\u2705 Healthy" for i in range(NUM_SENSORS)],
        })
        st.dataframe(df_h, hide_index=True, use_container_width=True)
        st.caption(f"Raw median: {hum_vote.raw_median:.1f}% \u2192 Trusted (healthy only): {trusted_humidity:.1f}%")

    with c2:
        st.markdown("**Jolt / Shock Sensors (Quorum Vote)**")
        df_j = pd.DataFrame({
            "Sensor": [f"S{i+1}" for i in range(NUM_SENSORS)],
            "Triggered": ["Yes" if f else "No" for f in jolt_flags],
        })
        st.dataframe(df_j, hide_index=True, use_container_width=True)
        st.caption(f"{jolt_vote.votes_for}/{jolt_vote.total_sensors} sensors agree "
                   f"(quorum {quorum_frac:.0%}) \u2192 "
                   f"{'CONFIRMED shock event' if jolt_vote.confirmed else 'No confirmed shock'}")
        st.markdown("**Battery**")
        st.progress(battery_pct / 100, text=f"{battery_pct:.0f}%")

with tab_trends:
    if cg["log"]:
        df_log = pd.DataFrame(cg["log"]).set_index("tick")
        st.markdown("**Temperature over time**")
        st.line_chart(df_log[["temp"]])
        st.markdown("**Humidity over time**")
        st.line_chart(df_log[["humidity"]])
        st.markdown("**Battery over time**")
        st.line_chart(df_log[["battery"]])
        st.markdown("**Event Log**")
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No log entries yet — click **Advance Tick** in the sidebar to start the simulation.")

with tab_report:
    st.markdown("Generate a PDF compliance report summarizing the current shipment status, "
                 "sensor voting detail, and recent event log.")
    snapshot = {
        "cargo_mode": cargo_mode, "profile": profile, "state": current_state, "locked": cg["locked"],
        "reasons": state_result.reasons, "trusted_temp": trusted_temp, "trusted_humidity": trusted_humidity,
        "battery_pct": battery_pct, "confidence": confidence, "safe_hours_remaining": safe_hours_remaining,
        "transit_hours_remaining": transit_hours_remaining, "route_status": route.status,
        "route_margin_hours": route.margin_hours, "temp_readings": temp_readings,
        "temp_flagged": temp_vote.flagged_indices, "humidity_readings": humidity_readings,
        "humidity_flagged": hum_vote.flagged_indices, "jolt_flags": jolt_flags,
        "jolt_confirmed": jolt_vote.confirmed, "jolt_votes": jolt_vote.votes_for, "jolt_total": jolt_vote.total_sensors,
    }
    pdf_bytes = build_pdf_report(snapshot, cg["log"])
    st.download_button("\U0001F4E5 Download Compliance Report (PDF)", data=pdf_bytes,
                        file_name=f"cryoguard_report_{cargo_mode.lower()}_tick{cg['tick']}.pdf",
                        mime="application/pdf", use_container_width=True)

# ----------------------------------------------------------------------
# Optional live auto-tick loop (demo flourish)
# ----------------------------------------------------------------------
if auto_tick and not cg["locked"]:
    time.sleep(auto_interval)
    do_tick(minutes_per_tick, current_state)
    cg["log"].append({
        "tick": cg["tick"], "state": current_state, "temp": trusted_temp,
        "humidity": trusted_humidity, "battery": battery_pct, "route_status": route.status,
        "confidence": confidence, "safe_hours": safe_hours_remaining,
    })
    st.rerun()
