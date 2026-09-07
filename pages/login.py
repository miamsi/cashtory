import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import auth  # noqa: E402

st.title("💰 Budget Tracker")
st.caption("Envelope budgeting, e-wallets, and an AI assistant — for you, month over month.")

tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

with tab_login:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)
    if submitted:
        try:
            auth.sign_in(email, password)
            st.rerun()
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't log in: {e}")

with tab_signup:
    with st.form("signup_form"):
        email = st.text_input("Email", key="su_email")
        password = st.text_input("Password", type="password", key="su_password",
                                  help="At least 6 characters.")
        password2 = st.text_input("Confirm password", type="password", key="su_password2")
        submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
    if submitted:
        if password != password2:
            st.error("Passwords don't match.")
        elif len(password) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            try:
                auth.sign_up(email, password)
                st.success(
                    "Account created. If your Supabase project requires email confirmation, "
                    "check your inbox, then log in on the **Log in** tab. Otherwise, log in now."
                )
            except Exception as e:  # noqa: BLE001
                st.error(f"Couldn't sign up: {e}")
