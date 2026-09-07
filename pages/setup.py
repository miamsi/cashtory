import datetime as dt

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import db, ui  # noqa: E402

ui.sidebar_account()
period = ui.require_period()
period_id = period["id"]

st.title("⚙️ Month Setup")
st.caption(f"Month: **{period['label']}** — set this month's income, fixed obligations, and savings target.")

tab_income, tab_fixed, tab_savings, tab_settings = st.tabs(
    ["💰 Income", "🧾 Fixed & early spendings", "🏦 Savings", "⚙️ App settings"]
)


def _list_and_form(tab, table_label, df, add_fn, key_prefix):
    with tab:
        if not df.empty:
            st.dataframe(df[["date", "description", "amount"]], use_container_width=True, hide_index=True)
        else:
            st.info(f"No {table_label} entries yet this month.")
        with st.form(f"{key_prefix}_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            d = c1.date_input("Date", value=dt.date.today(), key=f"{key_prefix}_date")
            desc = c2.text_input("Description", key=f"{key_prefix}_desc")
            amount = c3.number_input("Amount (Rp)", step=10000.0, format="%.0f", key=f"{key_prefix}_amount")
            submitted = st.form_submit_button("Add", type="primary")
        if submitted and desc:
            add_fn(period_id, d, desc, amount)
            st.success("Added.")
            st.rerun()


_list_and_form(tab_income, "income", db.get_income(period_id), db.add_income, "income")
_list_and_form(tab_fixed, "fixed spending", db.get_fixed_spending(period_id), db.add_fixed_spending, "fixed")
_list_and_form(tab_savings, "savings", db.get_savings(period_id), db.add_savings, "savings")

with tab_settings:
    st.caption("These apply to your account, across all months.")
    settings = db.get_settings()
    with st.form("settings_form"):
        cat = st.text_input("Daily-budget envelope name", value=settings.get("daily_budget_category", ""))
        amt = st.number_input(
            "Daily budget amount (Rp)", value=float(settings.get("daily_budget_amount", 150000)), step=5000.0
        )
        model = st.text_input("Groq model", value=settings.get("groq_model", "llama-3.3-70b-versatile"))
        submitted = st.form_submit_button("Save settings", type="primary")
    if submitted:
        db.set_setting("daily_budget_category", cat)
        db.set_setting("daily_budget_amount", str(amt))
        db.set_setting("groq_model", model)
        st.success("Settings saved.")
        st.rerun()
