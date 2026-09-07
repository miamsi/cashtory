import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import auth, db  # noqa: E402

st.set_page_config(page_title="Budget Tracker", page_icon="💰", layout="wide")

if not auth.is_authenticated():
    login_page = st.Page("pages/login.py", title="Log in", icon="🔐", default=True)
    pg = st.navigation([login_page])
else:
    # First login ever: make sure default settings exist so logic.py has
    # something sane to read (daily budget category/amount, Groq model).
    if not st.session_state.get("_settings_checked"):
        db.ensure_default_settings()
        st.session_state["_settings_checked"] = True

    pages = [
        st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("pages/transactions.py", title="Transactions", icon="💵"),
        st.Page("pages/allocations.py", title="Envelopes & Wallets", icon="🗂️"),
        st.Page("pages/periods.py", title="Months", icon="🗓️"),
        st.Page("pages/ai_assistant.py", title="AI Assistant", icon="🤖"),
        st.Page("pages/setup.py", title="Setup", icon="⚙️"),
    ]
    pg = st.navigation(pages)

pg.run()
