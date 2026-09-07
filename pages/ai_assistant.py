import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from lib import ai, ui  # noqa: E402

ui.sidebar_account()
period = ui.require_period()

st.title("🤖 Ask about your budget")
st.caption(f"Grounded in your **{period['label']}** data — nothing is invented.")

history_key = f"chat_history_{period['id']}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

for msg in st.session_state[history_key]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

suggestions = [
    "How much do I have left this month?",
    "Am I overspending on daily food budget?",
    "Which envelope is running lowest?",
    "Summarize my spending pattern this week.",
]
cols = st.columns(len(suggestions))
for c, s in zip(cols, suggestions):
    if c.button(s, use_container_width=True):
        st.session_state[history_key].append({"role": "user", "content": s})
        st.rerun()

prompt = st.chat_input("Ask a question about your finances...")
if prompt:
    st.session_state[history_key].append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state[history_key] and st.session_state[history_key][-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = ai.chat(st.session_state[history_key], period)
        st.markdown(reply)
    st.session_state[history_key].append({"role": "assistant", "content": reply})

if st.session_state[history_key] and st.button("Clear conversation"):
    st.session_state[history_key] = []
    st.rerun()
