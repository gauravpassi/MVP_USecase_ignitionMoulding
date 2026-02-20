"""Inspect page — live preview, capture + run inference, show results."""
from __future__ import annotations

import base64
import time

import streamlit as st
from api_client import get, post


def render():
    st.header("Inspect")

    cameras = get("/cameras")
    if cameras is None:
        return
    if not cameras:
        st.warning("No cameras configured. Go to the Cameras page first.")
        return

    active_cams = [c for c in cameras if c["status"] == "active"]
    if not active_cams:
        st.warning("No active cameras.")
        return

    cam_map = {c["name"]: c for c in active_cams}
    selected = st.selectbox("Select Camera", list(cam_map.keys()))
    cam = cam_map[selected]
    cam_id = cam["id"]

    col_preview, col_result = st.columns(2)

    # --- Live preview (polling) ---
    with col_preview:
        st.subheader("Live Preview")
        preview_placeholder = st.empty()
        auto_refresh = st.checkbox("Auto-refresh preview", value=False)

        snap = get(f"/cameras/{cam_id}/snapshot")
        if snap:
            img_bytes = base64.b64decode(snap["image_base64"])
            preview_placeholder.image(img_bytes, caption="Live", use_container_width=True)
        else:
            preview_placeholder.info("Could not get snapshot.")

        if auto_refresh:
            time.sleep(1)
            st.rerun()

    # --- Inspect ---
    with col_result:
        st.subheader("Run Inspection")
        mode = st.radio("Inference mode", ["opencv", "onnx"], horizontal=True)
        if st.button("Capture & Inspect", type="primary"):
            with st.spinner("Running inspection…"):
                result = post("/inspections", params={
                    "camera_id": cam_id,
                    "mode": mode,
                })
            if result:
                is_pass = result["result"] == "pass"
                if is_pass:
                    st.success("PASS — No defects detected.")
                else:
                    st.error("FAIL — Defects detected!")

                st.write(f"**Confidence:** {result['confidence']:.3f}")
                st.write(f"**Inference mode:** {result['inference_mode']}")

                if result["defects"]:
                    st.write("**Defects found:**")
                    for d in result["defects"]:
                        st.write(
                            f"- **{d['type']}** — bbox {d['bbox']}, "
                            f"score {d['score']}"
                        )

                # Show captured image
                img_resp = get(f"/inspections/{result['id']}/image")
                if img_resp:
                    img_bytes = base64.b64decode(img_resp["image_base64"])
                    st.image(img_bytes, caption="Captured Image", use_container_width=True)
