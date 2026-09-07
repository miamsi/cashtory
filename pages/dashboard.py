import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import logic, ui  # noqa: E402

ui.sidebar_account()
period = ui.require_period()

st.title("💰 Budget Tracker")
st.caption(f"Viewing **{period['label']}** ({period['start_date']} → {period['end_date']})")

try:
    buf = logic.buffer_summary(period["id"])
    model = logic.allocation_model(period["id"])
    qv = logic.quick_view(period["id"])
except Exception as e:  # noqa: BLE001
    st.error(f"Couldn't load data from Supabase: {e}")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Income", f"Rp {buf['income']:,.0f}")
c2.metric("Total fund in balance", f"Rp {buf['total_fund_in_balance']:,.0f}")
c3.metric("Buffer", f"Rp {buf['buffer']:,.0f}")
c4.metric("Remaining fund now", f"Rp {qv['total_remaining_fund']:,.0f}", delta=f"{qv['status']}")

st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("Allocations — fund vs. remaining")
    plot_df = model[model["allocation"] != "Total fund in balance"].copy()
    if plot_df.empty:
        st.info("No envelopes or wallets set up yet for this month.")
    else:
        fig = px.bar(
            plot_df.melt(id_vars="allocation", value_vars=["fund", "remaining"],
                         var_name="type", value_name="amount"),
            x="allocation", y="amount", color="type", barmode="group",
        )
        fig.update_layout(xaxis_title=None, yaxis_title="Rp", legend_title=None, height=420)
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Where you stand")
    st.dataframe(
        model.style.format({"fund": "{:,.0f}", "realisation": "{:,.0f}", "remaining": "{:,.0f}"}),
        use_container_width=True, hide_index=True,
    )

st.divider()

st.subheader("🍜 Daily consumption pacing")
cp = logic.consumption_performance(period["id"])
if cp.empty:
    st.info("No transactions logged yet for the daily-budget category.")
else:
    fig2 = px.bar(cp, x="date", y="surplus_deficit",
                  color=cp["surplus_deficit"] >= 0,
                  color_discrete_map={True: "#2ecc71", False: "#e74c3c"})
    fig2.update_layout(showlegend=False, yaxis_title="Surplus / Deficit (Rp)", xaxis_title=None, height=320)
    st.plotly_chart(fig2, use_container_width=True)

st.caption(
    f"As of {qv['current_date']} · Outstanding receivables: Rp {qv['receivables']:,.0f} · "
    f"Status: **{qv['status']}**"
)

st.divider()
st.page_link("pages/transactions.py", label="➕ Add a transaction", icon="💵")
st.page_link("pages/allocations.py", label="🗂️ Manage envelopes & wallets", icon="🗂️")
st.page_link("pages/ai_assistant.py", label="🤖 Ask the AI assistant", icon="🤖")
st.page_link("pages/periods.py", label="🗓️ Start next month / manage months", icon="🗓️")
