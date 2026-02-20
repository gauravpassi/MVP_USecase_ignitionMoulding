"""Dataset Capture page — bulk capture images for training data collection."""
from __future__ import annotations

import base64

import streamlit as st
from api_client import get, post, patch


def render():
    st.header("Dataset Capture")
    st.write(
        "Capture images rapidly and label them to build a training dataset. "
        "Images are stored on disk and metadata in PostgreSQL."
    )

    cameras = get("/cameras") or []
    if not cameras:
        st.warning("No cameras configured. Go to the Cameras page first.")
        return

    active_cams = [c for c in cameras if c["status"] == "active"]
    if not active_cams:
        st.warning("No active cameras.")
        return

    cam_map = {c["name"]: c for c in active_cams}
    selected = st.selectbox("Camera", list(cam_map.keys()))
    cam = cam_map[selected]
    cam_id = cam["id"]

    st.divider()

    # --- Rapid capture ---
    st.subheader("Rapid Capture")
    n_captures = st.slider("Number of captures", min_value=1, max_value=20, value=1)
    default_label = st.radio("Default label", ["", "ok", "ng"], horizontal=True)

    if st.button("Capture", type="primary"):
        progress = st.progress(0)
        captured_ids = []
        for i in range(n_captures):
            result = post("/inspections", params={
                "camera_id": cam_id,
                "mode": "opencv",
            })
            if result:
                captured_ids.append(result["id"])
                # Apply default label if set
                if default_label:
                    patch(
                        f"/inspections/{result['id']}/label",
                        json={"label": default_label},
                    )
            progress.progress((i + 1) / n_captures)

        st.success(f"Captured {len(captured_ids)} image(s).")
        st.session_state["last_captured"] = captured_ids

    # --- Show last captured ---
    captured_ids = st.session_state.get("last_captured", [])
    if captured_ids:
        st.divider()
        st.subheader("Last Captured")
        cols = st.columns(min(len(captured_ids), 4))
        for idx, insp_id in enumerate(captured_ids):
            col = cols[idx % len(cols)]
            img_resp = get(f"/inspections/{insp_id}/image")
            if img_resp:
                img_bytes = base64.b64decode(img_resp["image_base64"])
                col.image(img_bytes, caption=str(insp_id)[:8], use_container_width=True)

    st.divider()

    # --- Dataset stats ---
    st.subheader("Dataset Summary")
    all_inspections = get("/inspections", params={"limit": 500}) or []
    labeled = [i for i in all_inspections if i.get("label")]
    ok_count = sum(1 for i in labeled if i["label"] == "ok")
    ng_count = sum(1 for i in labeled if i["label"] == "ng")
    unlabeled = len(all_inspections) - len(labeled)

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Total Images", len(all_inspections))
    sc2.metric("Labeled OK", ok_count)
    sc3.metric("Labeled NG", ng_count)
    sc4.metric("Unlabeled", unlabeled)
