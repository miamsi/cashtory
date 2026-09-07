import datetime as dt

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import ai, db, logic, ui  # noqa: E402

ui.sidebar_account()
period = ui.require_period()
period_id = period["id"]

st.title("💵 Transactions")
st.caption(f"Month: **{period['label']}**")

allocations = logic.allocation_names(period_id)
if len(allocations) <= 1:
    st.warning("Add some envelopes and wallets first on the **Envelopes & Wallets** page.")

tab_ai, tab_manual, tab_history = st.tabs(["🤖 Quick add (AI)", "✍️ Manual entry", "📜 History"])

# ---------------------------------------------------------------------------
# AI quick-add
# ---------------------------------------------------------------------------
with tab_ai:
    st.write(
        "Describe the expense in plain language — e.g. *'bought coffee 25000'*, "
        "*'top up gopay 50000'*, *'paid parking with e-money 6000'*. "
        "The AI proposes ledger rows; nothing is saved until you confirm."
    )
    text = st.text_input("What happened?", key="ai_tx_text",
                          placeholder="e.g. beli kopi 25000 pakai gopay")
    if st.button("Parse with AI", type="primary", disabled=not text):
        with st.spinner("Asking Groq..."):
            result = ai.parse_transaction(text, period_id=period_id, today=str(dt.date.today()))
        st.session_state["ai_proposal"] = result

    proposal = st.session_state.get("ai_proposal")
    if proposal:
        if proposal.get("note"):
            st.info(proposal["note"])
        if not proposal["legs"]:
            st.warning("No valid legs were produced. Try rephrasing, or use manual entry.")
        else:
            st.write("**Proposed ledger rows** (edit any cell before confirming):")
            edited = st.data_editor(
                proposal["legs"],
                column_config={
                    "allocation": st.column_config.SelectboxColumn(options=allocations, required=True),
                    "cash_basis": st.column_config.NumberColumn(format="%.0f"),
                    "receivables": st.column_config.NumberColumn(format="%.0f"),
                },
                num_rows="dynamic",
                use_container_width=True,
                key="ai_editor",
            )
            tx_date = st.date_input("Date", value=dt.date.today(), key="ai_date")
            if st.button("✅ Confirm & save"):
                legs = [
                    {
                        "date": str(tx_date),
                        "description": row["description"],
                        "allocation": row["allocation"],
                        "cash_basis": float(row["cash_basis"]),
                        "receivables": float(row.get("receivables") or 0),
                    }
                    for row in edited
                ]
                db.add_transaction_legs(period_id, legs, source="ai")
                st.session_state.pop("ai_proposal", None)
                st.success("Saved.")
                st.rerun()

# ---------------------------------------------------------------------------
# Manual entry
# ---------------------------------------------------------------------------
with tab_manual:
    st.write("For a plain single-envelope spend, or a manual multi-leg entry (e.g. wallet transfers).")

    mode = st.radio("Entry type", ["Simple spend (one allocation)", "Multi-leg (transfer / split)"],
                     horizontal=True)

    if mode == "Simple spend (one allocation)":
        with st.form("simple_form", clear_on_submit=True):
            d = st.date_input("Date", value=dt.date.today())
            desc = st.text_input("Description")
            alloc = st.selectbox("Allocation", allocations)
            amount = st.number_input("Amount (negative = money out)", step=1000.0, format="%.0f")
            receivable = st.number_input("Receivable portion (owed back to you)", step=1000.0,
                                          format="%.0f", value=0.0)
            submitted = st.form_submit_button("Add", type="primary")
        if submitted and desc:
            db.add_transaction_legs(period_id, [{
                "date": str(d), "description": desc, "allocation": alloc,
                "cash_basis": amount, "receivables": receivable,
            }])
            st.success("Added.")
            st.rerun()

    else:
        st.caption("Add each leg of the transaction; the set should usually net to zero.")
        n_legs = st.number_input("Number of legs", min_value=2, max_value=6, value=2)
        with st.form("multi_form", clear_on_submit=True):
            d = st.date_input("Date", value=dt.date.today())
            desc = st.text_input("Shared description", placeholder="e.g. Top up Gopay")
            legs = []
            for i in range(int(n_legs)):
                cols = st.columns([2, 1, 1])
                alloc = cols[0].selectbox(f"Allocation {i+1}", allocations, key=f"m_alloc_{i}")
                cash = cols[1].number_input(f"Cash basis {i+1}", step=1000.0, format="%.0f", key=f"m_cash_{i}")
                recv = cols[2].number_input(f"Receivable {i+1}", step=1000.0, format="%.0f", key=f"m_recv_{i}")
                legs.append({"allocation": alloc, "cash_basis": cash, "receivables": recv})
            submitted = st.form_submit_button("Add all legs", type="primary")
        if submitted and desc:
            net = sum(l["cash_basis"] for l in legs)
            if abs(net) > 0.01:
                st.warning(f"Legs don't net to zero (net = {net:,.0f}) — saved anyway, double check.")
            db.add_transaction_legs(period_id, [{**l, "date": str(d), "description": desc} for l in legs])
            st.success("Added.")
            st.rerun()

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
with tab_history:
    df = db.get_transactions(period_id, limit=500)
    if df.empty:
        st.info("No transactions yet this month.")
    else:
        st.dataframe(
            df[["date", "description", "allocation", "cash_basis", "receivables", "accrual_basis", "source"]],
            use_container_width=True, hide_index=True,
        )
        with st.expander("Delete a transaction group"):
            gid = st.text_input("group_id to delete")
            if st.button("Delete", type="secondary") and gid:
                db.delete_transaction_group(gid)
                st.success("Deleted.")
                st.rerun()
