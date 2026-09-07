import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import db, logic, ui  # noqa: E402

ui.sidebar_account()
period = ui.require_period()
period_id = period["id"]

st.title("🗂️ Envelopes & Wallets")
st.caption(f"Month: **{period['label']}**")

tab_env, tab_wallet, tab_model = st.tabs(["📦 Envelope categories", "👛 Wallets", "📊 Model view"])

with tab_env:
    st.write("Envelope categories are this month's budget buckets (e.g. groceries, transport, entertainment).")
    df = db.get_encumbrance(period_id, active_only=False)
    if not df.empty:
        st.dataframe(df[["name", "amount", "active"]], use_container_width=True, hide_index=True)
    with st.form("add_env", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("Category name")
        amount = c2.number_input("This month's allocation (Rp)", min_value=0.0, step=10000.0, format="%.0f")
        submitted = st.form_submit_button("Add / update", type="primary")
    if submitted and name:
        db.upsert_encumbrance(period_id, name, amount)
        st.success(f"Saved '{name}'.")
        st.rerun()

with tab_wallet:
    st.write(
        "Wallets are e-wallets or cash-on-hand. The wallet **catalog** (names) persists across "
        "months; each month has its own **opening balance** so history stays accurate even as "
        "balances carry forward."
    )
    wallets = db.get_wallets(active_only=False)
    period_wallets = db.get_period_wallets(period_id)
    pw_map = {r["wallet_name"]: r["opening_balance"] for _, r in period_wallets.iterrows()} if not period_wallets.empty else {}

    if not wallets.empty:
        rows = [{"name": w["name"], "opening_balance_this_month": pw_map.get(w["name"], 0.0),
                 "active": w["active"]} for _, w in wallets.iterrows()]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    st.write("**Add a new wallet:**")
    with st.form("add_wallet", clear_on_submit=True):
        name = st.text_input("Wallet name")
        submitted = st.form_submit_button("Add wallet", type="primary")
    if submitted and name:
        db.add_wallet(name)
        st.success(f"Added wallet '{name}'. Set its opening balance below.")
        st.rerun()

    st.write(f"**Set opening balance for {period['label']}:**")
    if wallets.empty:
        st.info("Add a wallet first.")
    else:
        with st.form("set_balance", clear_on_submit=True):
            wallet_name = st.selectbox("Wallet", wallets["name"].tolist())
            balance = st.number_input("Opening balance (Rp)", min_value=0.0, step=5000.0, format="%.0f")
            submitted = st.form_submit_button("Set balance", type="primary")
        if submitted:
            db.set_period_wallet_balance(period_id, wallet_name, balance)
            st.success(f"Set {wallet_name} opening balance to Rp {balance:,.0f} for {period['label']}.")
            st.rerun()

with tab_model:
    st.write("Live fund / realisation / remaining per allocation — mirrors the original 'Model' sheet.")
    model = logic.allocation_model(period_id)
    st.dataframe(
        model.style.format({"fund": "{:,.0f}", "realisation": "{:,.0f}", "remaining": "{:,.0f}"}),
        use_container_width=True, hide_index=True,
    )
    st.write("Per-wallet buffer flow — top-ups in, opening threshold, spend out, and reversal owed to Buffer:")
    bf = logic.buffer_flow(period_id)
    if bf.empty:
        st.info("No wallets set up yet.")
    else:
        st.dataframe(
            bf.style.format({
                "buffer_in": "{:,.0f}", "threshold": "{:,.0f}", "buffer_out": "{:,.0f}",
                "buffer_needs_to_reverse": lambda v: "No reversal" if v is None else f"{v:,.0f}",
            }),
            use_container_width=True, hide_index=True,
        )
