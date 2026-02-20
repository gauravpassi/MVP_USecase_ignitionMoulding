"""
Thin HTTP helper shared by all Streamlit pages.
"""
from __future__ import annotations

import streamlit as st
import requests


def api_url() -> str:
    return st.session_state.get("api_url", "http://localhost:8000")


def get(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{api_url()}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Is the backend running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def post(path: str, json: dict | None = None, params: dict | None = None):
    try:
        r = requests.post(f"{api_url()}{path}", json=json, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Is the backend running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def patch(path: str, json: dict | None = None):
    try:
        r = requests.patch(f"{api_url()}{path}", json=json, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Is the backend running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def delete(path: str):
    try:
        r = requests.delete(f"{api_url()}{path}", timeout=10)
        r.raise_for_status()
        return True
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Is the backend running?")
        return False
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return False
