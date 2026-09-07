"""Supabase Auth (email/password) for Streamlit.

IMPORTANT: the authenticated client is stored in st.session_state, NOT
st.cache_resource. st.cache_resource is a process-wide cache shared by every
visitor to the deployed app — caching a logged-in client there would leak one
user's session to another. st.session_state is per-browser-session, which is
what we want.
"""
from __future__ import annotations

import os

import streamlit as st
from supabase import Client, create_client


def _config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
    if not url or not key:
        st.error(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY "
            "in a .env file (local) or in Streamlit secrets (deployed)."
        )
        st.stop()
    return url, key


def _raw_client() -> Client:
    """A plain, unauthenticated client — fine to reuse across sessions since it
    carries no per-user state until .postgrest.auth(token) is called on it,
    which we only ever do on the per-session copy in session_state."""
    if "sb_raw_client" not in st.session_state:
        url, key = _config()
        st.session_state["sb_raw_client"] = create_client(url, key)
    return st.session_state["sb_raw_client"]


def sign_up(email: str, password: str):
    client = _raw_client()
    return client.auth.sign_up({"email": email, "password": password})


def sign_in(email: str, password: str):
    client = _raw_client()
    res = client.auth.sign_in_with_password({"email": email, "password": password})
    st.session_state["sb_session"] = {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
    }
    st.session_state["sb_user"] = {"id": res.user.id, "email": res.user.email}
    return res


def sign_out():
    try:
        _raw_client().auth.sign_out()
    except Exception:  # noqa: BLE001
        pass
    for k in ("sb_session", "sb_user", "sb_raw_client"):
        st.session_state.pop(k, None)


def current_user() -> dict | None:
    return st.session_state.get("sb_user")


def is_authenticated() -> bool:
    return "sb_session" in st.session_state and "sb_user" in st.session_state


def get_authed_client() -> Client:
    """The client every data query should use — carries the logged-in user's JWT
    so Postgres RLS (auth.uid() = user_id) applies automatically."""
    client = _raw_client()
    session = st.session_state.get("sb_session")
    if session:
        client.postgrest.auth(session["access_token"])
    return client
