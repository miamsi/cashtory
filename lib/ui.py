"""Shared sidebar bits used by every page: who's logged in, which period is
selected, and a logout button. Every data page should call require_period()
at the top to get the active period_id in a consistent way."""
from __future__ import annotations

import streamlit as st

from . import auth, db


def sidebar_account():
    user = auth.current_user()
    with st.sidebar:
        st.caption(f"Signed in as **{user['email']}**")
        if st.button("Log out", use_container_width=True):
            auth.sign_out()
            st.rerun()
        st.divider()


def require_period() -> dict:
    """Ensures a period is selected; shows a switcher in the sidebar; returns
    the selected period dict. Stops the page with a friendly message if the
    user has no periods yet (first-run)."""
    periods_df = db.get_periods()
    if periods_df.empty:
        st.info("👋 You don't have any months set up yet.")
        st.page_link("pages/periods.py", label="Set up your first month", icon="🗓️")
        st.stop()

    options = periods_df.to_dict("records")
    labels = [p["label"] + (" (active)" if p["is_active"] else "") for p in options]

    if "selected_period_id" not in st.session_state:
        active = next((p for p in options if p["is_active"]), options[0])
        st.session_state["selected_period_id"] = active["id"]

    current_index = next(
        (i for i, p in enumerate(options) if p["id"] == st.session_state["selected_period_id"]), 0
    )

    with st.sidebar:
        idx = st.selectbox("Month", range(len(options)), format_func=lambda i: labels[i], index=current_index)
        st.session_state["selected_period_id"] = options[idx]["id"]
        st.page_link("pages/periods.py", label="Manage months", icon="🗓️")
        st.divider()

    return options[idx]
