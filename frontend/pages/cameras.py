"""Cameras page — add/edit/delete cameras, set ROI, live preview."""
from __future__ import annotations

import base64

import streamlit as st
from api_client import get, post, patch, delete


def render():
    st.header("Cameras")

    # --- Add camera form ---
    with st.expander("Add New Camera", expanded=False):
        with st.form("add_camera"):
            name = st.text_input("Camera Name", value="Cam-1")
            source_type = st.selectbox("Source Type", ["usb", "rtsp"])
            source_uri = st.text_input(
                "Source URI",
                value="0" if source_type == "usb" else "rtsp://",
                help="For USB: device index (0, 1, …).  For RTSP: full URL.",
            )
            st.markdown("**ROI (Region of Interest)** — leave 0,0,0,0 for full frame")
            rc1, rc2, rc3, rc4 = st.columns(4)
            roi_x = rc1.number_input("X", min_value=0, value=0)
            roi_y = rc2.number_input("Y", min_value=0, value=0)
            roi_w = rc3.number_input("W", min_value=0, value=0)
            roi_h = rc4.number_input("H", min_value=0, value=0)

            submitted = st.form_submit_button("Add Camera")
            if submitted:
                result = post("/cameras", json={
                    "name": name,
                    "source_type": source_type,
                    "source_uri": source_uri,
                    "roi_x": roi_x, "roi_y": roi_y,
                    "roi_w": roi_w, "roi_h": roi_h,
                })
                if result:
                    st.success(f"Camera '{name}' added.")
                    st.rerun()

    st.divider()

    # --- List cameras ---
    cameras = get("/cameras")
    if cameras is None:
        return
    if not cameras:
        st.info("No cameras configured. Add one above.")
        return

    for cam in cameras:
        cam_id = cam["id"]
        short_id = cam_id[:8]
        col_info, col_actions = st.columns([3, 1])

        with col_info:
            status_color = "green" if cam["status"] == "active" else "gray"
            st.markdown(
                f"### :{status_color}[{cam['name']}] `{short_id}…`\n"
                f"**Type:** {cam['source_type']}  |  "
                f"**URI:** `{cam['source_uri']}`  |  "
                f"**ROI:** ({cam['roi_x']},{cam['roi_y']},{cam['roi_w']},{cam['roi_h']})"
            )

        with col_actions:
            if st.button("Snapshot", key=f"snap_{cam_id}"):
                snap = get(f"/cameras/{cam_id}/snapshot")
                if snap:
                    img_bytes = base64.b64decode(snap["image_base64"])
                    st.image(img_bytes, caption=f"Live — {cam['name']}", use_container_width=True)

            if st.button("Delete", key=f"del_{cam_id}"):
                delete(f"/cameras/{cam_id}")
                st.rerun()

    # --- ROI Editor ---
    st.divider()
    st.subheader("Edit Camera ROI")
    cam_names = {c["name"]: c["id"] for c in cameras}
    selected_name = st.selectbox("Select Camera", list(cam_names.keys()))
    if selected_name:
        sel_id = cam_names[selected_name]
        sel_cam = next(c for c in cameras if c["id"] == sel_id)
        with st.form("edit_roi"):
            ec1, ec2, ec3, ec4 = st.columns(4)
            new_x = ec1.number_input("ROI X", value=sel_cam["roi_x"], min_value=0)
            new_y = ec2.number_input("ROI Y", value=sel_cam["roi_y"], min_value=0)
            new_w = ec3.number_input("ROI W", value=sel_cam["roi_w"], min_value=0)
            new_h = ec4.number_input("ROI H", value=sel_cam["roi_h"], min_value=0)
            if st.form_submit_button("Update ROI"):
                patch(f"/cameras/{sel_id}", json={
                    "roi_x": new_x, "roi_y": new_y,
                    "roi_w": new_w, "roi_h": new_h,
                })
                st.success("ROI updated.")
                st.rerun()
