import calendar
import datetime as dt

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import db, logic, ui  # noqa: E402

ui.sidebar_account()

st.title("🗓️ Months")

periods_df = db.get_periods()

if not periods_df.empty:
    st.subheader("Your months")
    show = periods_df[["label", "start_date", "end_date", "is_active"]].copy()
    st.dataframe(show, use_container_width=True, hide_index=True)

    active = periods_df[periods_df["is_active"]]
    if not active.empty:
        st.caption(f"Active month: **{active.iloc[0]['label']}**")

    with st.expander("Switch active month manually"):
        opts = periods_df.to_dict("records")
        pick = st.selectbox("Month", opts, format_func=lambda p: p["label"])
        if st.button("Make active"):
            db.set_active_period(pick["id"])
            st.session_state["selected_period_id"] = pick["id"]
            st.success(f"'{pick['label']}' is now active.")
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Roll forward from the active month -> next month
# ---------------------------------------------------------------------------
active_row = None
if not periods_df.empty:
    active_matches = periods_df[periods_df["is_active"]]
    if not active_matches.empty:
        active_row = active_matches.iloc[0].to_dict()

if active_row:
    st.subheader("➡️ Start next month")
    st.write(
        f"Roll forward from **{active_row['label']}**: wallet balances carry over as next month's "
        "opening balance (it's real cash sitting in the wallet), envelope categories are copied "
        "over so you don't retype them, and any Buffer/envelope leftover is suggested as a single "
        "carry-over income line — all editable before you confirm."
    )

    default_start = (dt.date.fromisoformat(str(active_row["end_date"])) + dt.timedelta(days=1))
    default_end = default_start.replace(
        day=calendar.monthrange(default_start.year, default_start.month)[1]
    )
    default_label = default_start.strftime("%B %Y")

    c1, c2, c3 = st.columns(3)
    new_label = c1.text_input("New month label", value=default_label)
    new_start = c2.date_input("Start date", value=default_start)
    new_end = c3.date_input("End date", value=default_end)

    if st.button("Preview roll-forward", type="secondary"):
        st.session_state["rollover_preview"] = logic.propose_rollover(active_row["id"])

    preview = st.session_state.get("rollover_preview")
    if preview:
        st.write("**Wallets — proposed opening balances for next month:**")
        wallet_rows = [{"wallet": k, "opening_balance": v} for k, v in preview["wallet_opening_balances"].items()]
        st.dataframe(wallet_rows, use_container_width=True, hide_index=True)

        carry_over = st.number_input(
            "Carry-over income line (Buffer + unspent envelopes → next month's income)",
            value=float(preview["carry_over_amount"]), step=10000.0, format="%.0f",
        )
        include_carry_over = st.checkbox("Add this as an income entry next month", value=True)

        copy_envelopes = st.checkbox("Copy this month's envelope categories & amounts forward", value=True)

        if st.button("✅ Confirm & start new month", type="primary"):
            new_period = db.create_period(new_label, new_start, new_end, make_active=True)

            for wallet_name, opening_balance in preview["wallet_opening_balances"].items():
                db.set_period_wallet_balance(new_period["id"], wallet_name, opening_balance)

            if copy_envelopes:
                db.copy_encumbrance_to_period(active_row["id"], new_period["id"])

            if include_carry_over and abs(carry_over) > 0.01:
                db.add_income(
                    new_period["id"], new_start,
                    f"Carry-over from {active_row['label']}", carry_over,
                )

            st.session_state.pop("rollover_preview", None)
            st.session_state["selected_period_id"] = new_period["id"]
            st.success(f"'{new_label}' created and set as active. Head to the Dashboard.")
            st.rerun()
else:
    st.subheader("Set up your first month")
    st.write("No active month yet — create one to get started.")
    today = dt.date.today()
    default_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    default_label = today.strftime("%B %Y")

    c1, c2, c3 = st.columns(3)
    label = c1.text_input("Month label", value=default_label)
    start = c2.date_input("Start date", value=today.replace(day=1))
    end = c3.date_input("End date", value=default_end)
    if st.button("Create month", type="primary"):
        new_period = db.create_period(label, start, end, make_active=True)
        st.session_state["selected_period_id"] = new_period["id"]
        st.success(f"'{label}' created. Head to Setup to add income, then Envelopes & Wallets.")
        st.rerun()
