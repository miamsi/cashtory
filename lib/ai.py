"""Groq integration: two jobs only, both where an LLM genuinely helps.

1. parse_transaction() - turn a free-text expense description into one or more
   balanced ledger legs for the CURRENT period, following the same
   double-entry pattern already used in the transaction history. The result
   is ALWAYS shown to the user for confirmation before it's written to the
   database — the model proposes, it never commits.

2. chat() - a budget assistant that answers questions grounded in the current
   period's numbers (injected directly as context; the dataset is small
   enough that full-context injection is simpler and more reliable than a
   vector store).

Note: the Groq client IS safe to cache with st.cache_resource — the API key is
an app-level secret (set once by whoever deploys the app), not a per-user
secret like the Supabase session, so there's no cross-user leakage risk here.
"""
from __future__ import annotations

import json
import os

import streamlit as st
from groq import Groq

from . import db, logic


@st.cache_resource(show_spinner=False)
def get_client() -> Groq:
    key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
    if not key:
        st.error("Missing GROQ_API_KEY. Set it in .env (local) or Streamlit secrets (deployed).")
        st.stop()
    return Groq(api_key=key)


def _model() -> str:
    return db.get_settings().get("groq_model", "llama-3.3-70b-versatile")


PARSE_SYSTEM_PROMPT = """You convert a short, casual expense description into one or more \
ledger "legs" for a personal envelope-budgeting system. Output ONLY valid JSON, no prose.

Concepts:
- "allocation" must be one of the provided valid allocation names EXACTLY as given \
(case-sensitive). Never invent a new allocation name.
- "Buffer" is the leftover/overflow account. It is used as the counter-leg when money \
moves INTO or OUT OF an e-wallet (a "top up" or a cash withdrawal), never for a plain \
purchase paid directly from an envelope category.
- cash_basis: the immediate cash effect (negative = money out, positive = money in) on \
that allocation for this leg.
- receivables: money owed back to this allocation later (e.g. someone still owes you \
their share) - usually 0.
- A plain purchase paid from ONE envelope (e.g. "bought coffee 25000") is a SINGLE leg: \
negative cash_basis on that envelope category. Do not invent a Buffer leg for this case.
- A wallet top-up (e.g. "top up gopay 50000" or "isi saldo ovo 100000") is TWO legs: \
Buffer cash_basis = -amount, and the wallet cash_basis = +amount.
- A cash withdrawal / "tarik uang" from an ATM into cash-on-hand is TWO legs: Buffer \
cash_basis = -amount, and the "Cash on hand" wallet cash_basis = +amount (use the exact \
wallet name from the valid list, if present).
- A purchase paid FROM a wallet (e.g. "beli kopi pakai gopay 20000") is TWO legs: the \
wallet cash_basis = -amount, and the spending envelope category cash_basis = -amount \
(both legs are outflows recording where the money left and what it was spent on) — unless \
no matching envelope category exists, in which case emit only the wallet leg.
- If part of an expense will be reimbursed later, split it: cash_basis = the paid amount \
(negative), receivables = the amount owed back (positive), on the paying allocation's leg.
- All amounts are plain positive numbers describing magnitude in the text; you decide sign.
- Always fill "description" with a short cleaned-up version of what the user typed.
- Use today's date unless the user specifies otherwise: {today}

Return JSON of this exact shape:
{{"legs": [{{"allocation": "...", "description": "...", "cash_basis": <number>, \
"receivables": <number>}}], "note": "one short sentence explaining what you did, or a \
warning if something was ambiguous"}}
"""


def parse_transaction(user_text: str, period_id: str, today: str) -> dict:
    valid_allocations = logic.allocation_names(period_id)
    recent = db.get_transactions(period_id, limit=15)
    examples = ""
    if not recent.empty:
        cols = ["date", "description", "allocation", "cash_basis", "receivables"]
        examples = recent[cols].to_json(orient="records", date_format="iso")

    client = get_client()
    resp = client.chat.completions.create(
        model=_model(),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT.format(today=today)},
            {
                "role": "user",
                "content": (
                    f"Valid allocation names: {json.dumps(valid_allocations)}\n\n"
                    f"Recent ledger rows for style reference (may be empty): {examples}\n\n"
                    f"Expense to record: {user_text!r}"
                ),
            },
        ],
    )
    content = resp.choices[0].message.content
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"legs": [], "note": "The model returned invalid JSON. Please try rephrasing."}

    # Guardrail: drop any leg referencing an allocation we don't actually have.
    legs = [leg for leg in parsed.get("legs", []) if leg.get("allocation") in valid_allocations]
    dropped = len(parsed.get("legs", [])) - len(legs)
    note = parsed.get("note", "")
    if dropped:
        note += f" ({dropped} leg(s) were dropped for referencing an unknown allocation.)"
    return {"legs": legs, "note": note}


CHAT_SYSTEM_PROMPT = """You are a plain-spoken personal budgeting assistant for an \
envelope-budgeting system (income split into fixed costs, savings, and per-category \
"envelopes", plus e-wallets and a leftover "Buffer" account). The user tracks one month \
at a time; you are looking at the period labeled "{period_label}" ({start} to {end}). \
Answer using ONLY the financial context provided below — do not invent numbers. If \
something isn't in the context (e.g. a question about a different month), say you don't \
have that data. Keep answers concise and concrete (use the actual numbers). Currency is \
Indonesian Rupiah (Rp); format large numbers with thousand separators.

CURRENT PERIOD FINANCIAL CONTEXT:
{context}
"""


def _build_context(period_id: str) -> str:
    buf = logic.buffer_summary(period_id)
    model = logic.allocation_model(period_id)
    qv = logic.quick_view(period_id)
    cp = logic.consumption_performance(period_id)
    recent = db.get_transactions(period_id, limit=25)

    parts = [
        "Buffer summary: " + json.dumps(buf, default=str),
        "Quick view: " + json.dumps(qv, default=str),
        "Allocation model (fund/realisation/remaining per category & wallet):\n"
        + model.to_string(index=False),
    ]
    if not cp.empty:
        parts.append("Daily consumption performance:\n" + cp.to_string(index=False))
    if not recent.empty:
        parts.append(
            "Most recent 25 ledger rows:\n"
            + recent[["date", "description", "allocation", "cash_basis", "receivables"]].to_string(index=False)
        )
    return "\n\n".join(parts)


def chat(history: list[dict], period: dict) -> str:
    """history: list of {"role": "user"|"assistant", "content": str}
    period: the active period dict (id, label, start_date, end_date)"""
    client = get_client()
    context = _build_context(period["id"])
    system = CHAT_SYSTEM_PROMPT.format(
        period_label=period["label"], start=period["start_date"], end=period["end_date"],
        context=context,
    )
    messages = [{"role": "system", "content": system}] + history
    resp = client.chat.completions.create(model=_model(), temperature=0.3, messages=messages)
    return resp.choices[0].message.content
