"""Dashboard page — KPI cards, charts, recent inspections."""
from __future__ import annotations

import streamlit as st
from api_client import get


def render():
    st.header("Dashboard")

    metrics = get("/dashboard/metrics")
    if metrics is None:
        return

    # --- KPI row ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Inspections", metrics["total_inspections"])
    c2.metric("Pass", metrics["pass_count"])
    c3.metric("Fail", metrics["fail_count"])
    c4.metric("Pass Rate", f"{metrics['pass_rate']:.1f}%")

    st.divider()

    # --- Camera status ---
    cam_col, defect_col = st.columns(2)
    with cam_col:
        st.subheader("Cameras")
        st.write(f"Active: **{metrics['cameras_active']}** / {metrics['cameras_total']}")

    with defect_col:
        st.subheader("Defect Breakdown")
        breakdown = metrics.get("defect_breakdown", {})
        if breakdown:
            for dtype, count in breakdown.items():
                st.write(f"- **{dtype}**: {count}")
        else:
            st.info("No defects recorded yet.")

    st.divider()

    # --- Recent inspections ---
    st.subheader("Recent Inspections")
    recent = metrics.get("recent_inspections", [])
    if not recent:
        st.info("No inspections yet. Go to the Inspect page to run one.")
        return

    for insp in recent:
        result_icon = "PASS" if insp["result"] == "pass" else "FAIL"
        color = "green" if insp["result"] == "pass" else "red"
        defect_types = ", ".join(d["type"] for d in insp.get("defects", [])) or "—"
        st.markdown(
            f":{color}[**{result_icon}**] &nbsp; Camera `{insp['camera_id'][:8]}…` "
            f"| Defects: {defect_types} "
            f"| Confidence: {insp['confidence']:.2f} "
            f"| {insp['created_at']}"
        )
