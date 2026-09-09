"""Groq integration: two jobs only, both where an LLM genuinely helps.

1. parse_transaction() - turn a free-text expense description into one or more
   balanced ledger legs for the CURRENT period.

2. chat() - a budget assistant that answers questions grounded in the current
   period's numbers.

The model proposes transactions. It never commits them directly.
"""

from __future__ import annotations

import json
import os

import streamlit as st
from groq import Groq

from . import db, logic


# ---------------------------------------------------------------------------
# Groq client
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_client() -> Groq:
    key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

    if not key:
        st.error(
            "Missing GROQ_API_KEY. Set it in .env (local) "
            "or Streamlit secrets (deployed)."
        )
        st.stop()

    return Groq(api_key=key)


def _model() -> str:
    return db.get_settings().get(
        "groq_model",
        "qwen/qwen3.8-27b",
    )


# ---------------------------------------------------------------------------
# Transaction parser
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You convert a short, casual expense description into
one or more ledger "legs" for a personal envelope-budgeting system.

Output ONLY valid JSON. No prose. No markdown.

Rules:

- "allocation" MUST be one of the provided valid allocation names EXACTLY.
- Never invent an allocation name.

- "Buffer" is the leftover/overflow account.
- Use Buffer as the counter-leg when money moves into or out of an
  e-wallet or cash-on-hand account.
- Buffer is ALSO used directly as the spending allocation itself when an
  expense has no matching envelope category — treat that exactly like a
  normal one-envelope purchase (ONE leg, receivables = 0). Not every
  Buffer transaction is a debt; most are just uncategorized spending.

- A normal purchase paid directly from ONE envelope category (or from
  Buffer, when nothing else fits) is ONE leg.
  Example:
  "bought coffee 25000"
  -> negative cash_basis on the coffee/food allocation.
  Do NOT create a second Buffer leg for this case.

- A wallet top-up is TWO legs:
  Buffer cash_basis = -amount
  wallet cash_basis = +amount

- A cash withdrawal from ATM is TWO legs:
  Buffer cash_basis = -amount
  Cash on hand wallet cash_basis = +amount

- A purchase paid FROM a wallet is TWO legs:
  wallet cash_basis = -amount
  spending envelope cash_basis = -amount

- If no matching spending envelope exists for a wallet purchase,
  emit only the wallet leg.

- If someone will reimburse part of a NEW expense later (a purchase
  happening right now, part of which is owed back to you):
  cash_basis = total amount paid, negative
  receivables = amount owed back, positive

- DEBT REPAYMENT / SETTLEMENT (e.g. "bayar utang", "ganti utang", "dia bayar
  balik", "reimbursed me", "paid me back", "temen saya bayar utang..."):
  this is NOT a new purchase. It reduces an EXISTING open receivable.
  You are given an "Open receivables" list below — allocations that
  currently have a nonzero owed balance. Match the repayment to whichever
  entry in that list the description most plausibly refers to (usually
  there's only one, or the description/date will hint at it). Emit ONE leg
  on that SAME allocation:
    cash_basis = +amount (money coming back in)
    receivables = -amount (the owed balance going down)
  Do not default to a category-sounding allocation (e.g. a food envelope)
  just because the debt happens to be about coffee/food — the money owed
  lives wherever the ORIGINAL purchase was recorded, not wherever the item
  category would normally go.
  If "Open receivables" is empty, or nothing on it plausibly matches, make
  your best guess but say so explicitly in "note" so the user double-checks
  before confirming — do not silently invent a match.

- All amounts in the input are positive magnitudes.
  You decide the correct sign.

- "description" must be a short cleaned-up version of the user's input.

- Use today's date unless the user explicitly specifies another date:
  {today}

Return exactly this JSON shape:

{{
  "legs": [
    {{
      "allocation": "...",
      "description": "...",
      "cash_basis": <number>,
      "receivables": <number>
    }}
  ],
  "note": "short explanation or warning"
}}
"""


def parse_transaction(
    user_text: str,
    period_id: str,
    today: str,
) -> dict:

    valid_allocations = logic.allocation_names(period_id)

    # Only fetch a small number of recent transactions for style/context.
    recent = db.get_transactions(period_id, limit=15)

    examples = ""

    if not recent.empty:
        cols = [
            "date",
            "description",
            "allocation",
            "cash_basis",
            "receivables",
        ]

        examples = recent[cols].to_json(
            orient="records",
            date_format="iso",
        )

    # Allocations with a currently nonzero owed balance, so debt repayments
    # ("bayar utang...") get matched to where the money actually lives
    # instead of being guessed by item category. This is a small list (a
    # handful of rows at most) so it doesn't meaningfully add to the prompt.
    open_recv_df = logic.open_receivables(period_id)
    open_receivables = (
        open_recv_df.to_dict(orient="records") if not open_recv_df.empty else []
    )

    client = get_client()

    # IMPORTANT:
    # Groq organization OTPM limit = 1000.
    # The old request allowed 2048 output tokens, which caused:
    # RateLimitError 429 - Requested 2048, limit 1000.
    #
    # Transaction parsing only needs a tiny JSON response.
    # 400 tokens is more than enough. Adding the open-receivables list only
    # grows the INPUT, not the requested completion size, so it doesn't
    # affect this limit.

    resp = client.chat.completions.create(
        model=_model(),

        # No reasoning is necessary for simple transaction classification.
        reasoning_effort="none",

        temperature=0,

        # Force JSON output.
        response_format={
            "type": "json_object"
        },

        # Keep requested output comfortably below the 1000 OTPM limit.
        max_completion_tokens=400,

        messages=[
            {
                "role": "system",
                "content": PARSE_SYSTEM_PROMPT.format(
                    today=today
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Valid allocation names: "
                    f"{json.dumps(valid_allocations, ensure_ascii=False)}\n\n"

                    f"Open receivables (nonzero owed balance right now — "
                    f"match debt repayments to one of these, not by "
                    f"category keyword): "
                    f"{json.dumps(open_receivables, ensure_ascii=False)}\n\n"

                    f"Recent ledger rows for style reference "
                    f"(may be empty): {examples}\n\n"

                    f"Expense to record: {user_text!r}"
                ),
            },
        ],
    )

    content = resp.choices[0].message.content

    # -----------------------------------------------------------------------
    # Parse JSON safely
    # -----------------------------------------------------------------------

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return {
            "legs": [],
            "note": (
                "The model returned invalid JSON. "
                "Please try rephrasing."
            ),
        }

    # -----------------------------------------------------------------------
    # Guardrail:
    # Never allow the model to create an allocation that does not exist.
    # -----------------------------------------------------------------------

    raw_legs = parsed.get("legs", [])

    if not isinstance(raw_legs, list):
        raw_legs = []

    legs = [
        leg
        for leg in raw_legs
        if isinstance(leg, dict)
        and leg.get("allocation") in valid_allocations
    ]

    dropped = len(raw_legs) - len(legs)

    note = parsed.get("note", "")

    if not isinstance(note, str):
        note = ""

    if dropped:
        note += (
            f" ({dropped} leg(s) were dropped because they "
            f"referenced an unknown allocation.)"
        )

    return {
        "legs": legs,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Budget chat
# ---------------------------------------------------------------------------

CHAT_SYSTEM_PROMPT = """You are a plain-spoken personal budgeting assistant
for an envelope-budgeting system.

The user tracks one month at a time.

You are looking at the period labeled "{period_label}"
({start} to {end}).

Answer using ONLY the financial context provided below.
Do not invent numbers.

If something isn't in the context, say you don't have that data.

Keep answers concise and concrete.
Use actual numbers from the context.

Currency is Indonesian Rupiah (Rp).
Format large numbers with thousand separators.

CURRENT PERIOD FINANCIAL CONTEXT:

{context}
"""


def _build_context(period_id: str) -> str:
    buf = logic.buffer_summary(period_id)
    model = logic.allocation_model(period_id)
    qv = logic.quick_view(period_id)
    cp = logic.consumption_performance(period_id)
    recent = db.get_transactions(period_id, limit=25)
    open_recv_df = logic.open_receivables(period_id)

    parts = [
        "Buffer summary: "
        + json.dumps(buf, default=str),

        "Quick view: "
        + json.dumps(qv, default=str),

        "Allocation model "
        "(fund/realisation/remaining per category & wallet):\n"
        + model.to_string(index=False),
    ]

    if not open_recv_df.empty:
        parts.append(
            "Open receivables (nonzero owed balance per allocation):\n"
            + open_recv_df.to_string(index=False)
        )

    if not cp.empty:
        parts.append(
            "Daily consumption performance:\n"
            + cp.to_string(index=False)
        )

    if not recent.empty:
        parts.append(
            "Most recent 25 ledger rows:\n"
            + recent[
                [
                    "date",
                    "description",
                    "allocation",
                    "cash_basis",
                    "receivables",
                ]
            ].to_string(index=False)
        )

    return "\n\n".join(parts)


def chat(
    history: list[dict],
    period: dict,
) -> str:

    client = get_client()

    context = _build_context(period["id"])

    system = CHAT_SYSTEM_PROMPT.format(
        period_label=period["label"],
        start=period["start_date"],
        end=period["end_date"],
        context=context,
    )

    messages = [
        {
            "role": "system",
            "content": system,
        }
    ] + history

    resp = client.chat.completions.create(
        model=_model(),

        # Prevent unnecessary reasoning-token consumption.
        reasoning_effort="none",

        temperature=0.3,

        # Keep chat output below the current 1000 OTPM ceiling.
        max_completion_tokens=700,

        messages=messages,
    )

    return resp.choices[0].message.content
