"""Upload & Inspect page — upload an image, run defect inspection, show tabular results."""
from __future__ import annotations

import base64
import io

import requests
import streamlit as st


def _api_url() -> str:
    return st.session_state.get("api_url", "http://localhost:8000")


# Friendly display names for each defect type
DEFECT_LABELS = {
    "ovality": "Ovality",
    "burr": "Burr",
    "flash": "Flash",
    "hole_shift": "Hole Shift",
    "crack": "Crack",
    "surface_marks": "Surface Marks",
}

ALL_DEFECT_TYPES = list(DEFECT_LABELS.keys())


def render():
    st.header("Upload & Inspect")
    st.write(
        "Upload a part image (JPG / PNG) to check for: "
        "**Ovality**, **Burr**, **Flash**, **Hole Shift**, **Crack**, and **Surface Marks**."
    )

    uploaded_file = st.file_uploader(
        "Choose an image file",
        type=["jpg", "jpeg", "png", "bmp"],
    )

    if uploaded_file is None:
        st.info("Upload an image to begin inspection.")
        return

    # Show uploaded image
    col_img, col_result = st.columns([1, 1])
    with col_img:
        st.subheader("Uploaded Image")
        st.image(uploaded_file, use_container_width=True)

    # Run inspection on button click
    with col_result:
        st.subheader("Inspection")
        if st.button("Run Inspection", type="primary"):
            uploaded_file.seek(0)
            with st.spinner("Analysing image for defects..."):
                try:
                    resp = requests.post(
                        f"{_api_url()}/inspections/upload",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                        params={"mode": "opencv"},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the API server. Is the backend running?")
                    return
                except requests.exceptions.HTTPError as e:
                    st.error(f"API error: {e.response.status_code} — {e.response.text}")
                    return

            st.session_state["upload_result"] = result

    # --- Display results ---
    result = st.session_state.get("upload_result")
    if result is None:
        return

    st.divider()

    # Overall verdict
    is_pass = result["result"] == "pass"
    if is_pass:
        st.success("VERDICT:  PASS  —  No defects detected")
    else:
        st.error("VERDICT:  FAIL  —  Defects detected")

    st.write(f"**Overall Confidence:** {result['confidence']:.3f}")
    st.write(f"**Inference Mode:** {result['inference_mode']}")

    st.divider()

    # --- Build defect summary table (one row per defect type) ---
    st.subheader("Defect Summary")

    defects = result.get("defects", [])

    # Group defects by type
    from collections import Counter
    type_counts = Counter(d["type"] for d in defects)

    # Build table rows — one per defect category
    table_rows = []
    for dtype in ALL_DEFECT_TYPES:
        count = type_counts.get(dtype, 0)
        status = "DETECTED" if count > 0 else "OK"
        # Best (highest) score for this type
        scores = [d["score"] for d in defects if d["type"] == dtype]
        max_score = max(scores) if scores else 0.0
        table_rows.append({
            "Defect Type": DEFECT_LABELS[dtype],
            "Status": status,
            "Count": count,
            "Max Score": f"{max_score:.3f}" if count > 0 else "—",
        })

    # Render as a Streamlit table with colour coding
    import pandas as pd
    df = pd.DataFrame(table_rows)

    def _highlight_status(val):
        if val == "DETECTED":
            return "background-color: #ffcccc; color: #cc0000; font-weight: bold"
        elif val == "OK":
            return "background-color: #ccffcc; color: #007700; font-weight: bold"
        return ""

    styled = df.style.applymap(_highlight_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # --- Detailed defect list ---
    if defects:
        st.divider()
        st.subheader("Detailed Defect List")

        detail_rows = []
        for i, d in enumerate(defects, 1):
            detail_rows.append({
                "#": i,
                "Type": DEFECT_LABELS.get(d["type"], d["type"]),
                "Score": f"{d['score']:.3f}",
                "Bounding Box": f"x={d['bbox'][0]}, y={d['bbox'][1]}, w={d['bbox'][2]}, h={d['bbox'][3]}",
                "Details": ", ".join(f"{k}={v}" for k, v in d.get("meta", {}).items()),
            })

        df_detail = pd.DataFrame(detail_rows)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)

    # Show the saved inspection image from backend
    st.divider()
    st.subheader("Stored Evidence")
    try:
        img_resp = requests.get(f"{_api_url()}/inspections/{result['id']}/image", timeout=10)
        img_resp.raise_for_status()
        img_data = img_resp.json()
        img_bytes = base64.b64decode(img_data["image_base64"])
        st.image(img_bytes, caption=f"Inspection {result['id'][:8]}…", use_container_width=True)
    except Exception:
        st.info("Could not load stored evidence image.")
