"""Reviews page — browse past inspections, filter, view image evidence."""
from __future__ import annotations

import base64

import streamlit as st
from api_client import get, patch


def render():
    st.header("Inspection Reviews")

    # --- Filters ---
    fc1, fc2, fc3 = st.columns(3)
    cameras = get("/cameras") or []
    cam_options = {"All": None} | {c["name"]: c["id"] for c in cameras}
    sel_cam_name = fc1.selectbox("Camera", list(cam_options.keys()))
    sel_result = fc2.selectbox("Result", ["All", "pass", "fail"])
    limit = fc3.number_input("Limit", min_value=1, max_value=500, value=50)

    params: dict = {"limit": limit}
    if cam_options[sel_cam_name]:
        params["camera_id"] = cam_options[sel_cam_name]
    if sel_result != "All":
        params["result"] = sel_result

    inspections = get("/inspections", params=params)
    if inspections is None:
        return
    if not inspections:
        st.info("No inspections found.")
        return

    st.write(f"Showing **{len(inspections)}** inspection(s).")
    st.divider()

    for insp in inspections:
        with st.container():
            c1, c2 = st.columns([1, 2])

            with c1:
                img_resp = get(f"/inspections/{insp['id']}/image")
                if img_resp:
                    img_bytes = base64.b64decode(img_resp["image_base64"])
                    st.image(img_bytes, use_container_width=True)

            with c2:
                result_color = "green" if insp["result"] == "pass" else "red"
                st.markdown(f"### :{result_color}[{insp['result'].upper()}]")
                st.write(f"**Camera:** `{insp['camera_id'][:8]}…`")
                st.write(f"**Confidence:** {insp['confidence']:.3f}")
                st.write(f"**Mode:** {insp['inference_mode']}")
                st.write(f"**Time:** {insp['created_at']}")

                if insp["defects"]:
                    st.write("**Defects:**")
                    for d in insp["defects"]:
                        st.write(f"- {d['type']} (score {d['score']})")

                # Label buttons
                current_label = insp.get("label", "")
                st.write(f"**Manual Label:** {current_label or '—'}")
                lc1, lc2 = st.columns(2)
                if lc1.button("Label OK", key=f"ok_{insp['id']}"):
                    patch(f"/inspections/{insp['id']}/label", json={"label": "ok"})
                    st.rerun()
                if lc2.button("Label NG", key=f"ng_{insp['id']}"):
                    patch(f"/inspections/{insp['id']}/label", json={"label": "ng"})
                    st.rerun()

            st.divider()
