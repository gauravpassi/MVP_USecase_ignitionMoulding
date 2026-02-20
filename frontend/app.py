"""
Streamlit multi-page app entry point.

Run: streamlit run frontend/app.py
"""
import os
import streamlit as st

st.set_page_config(
    page_title="Visual Inspection MVP",
    page_icon=":mag:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- sidebar navigation ----------
PAGES = {
    "Upload & Inspect": "pages.upload_inspect",
    "Dashboard": "pages.dashboard",
    "Cameras": "pages.cameras",
    "Inspect": "pages.inspect",
    "Reviews": "pages.reviews",
    "Dataset Capture": "pages.dataset",
}

st.sidebar.title("Visual Inspection")
selection = st.sidebar.radio("Navigate", list(PAGES.keys()))

# ---------- API base URL ----------
# Read from env var (set on Streamlit Cloud), fallback to sidebar input for local dev
_default_api_url = os.environ.get("API_URL", "https://mvpusecaseignitionmoulding-production.up.railway.app")
API_URL = st.sidebar.text_input("API URL", value=_default_api_url)
st.session_state["api_url"] = API_URL

# ---------- render selected page ----------
if selection == "Upload & Inspect":
    from frontend.pages import upload_inspect
    upload_inspect.render()
elif selection == "Dashboard":
    from frontend.pages import dashboard
    dashboard.render()
elif selection == "Cameras":
    from frontend.pages import cameras
    cameras.render()
elif selection == "Inspect":
    from frontend.pages import inspect
    inspect.render()
elif selection == "Reviews":
    from frontend.pages import reviews
    reviews.render()
elif selection == "Dataset Capture":
    from frontend.pages import dataset
    dataset.render()
