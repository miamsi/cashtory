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
- Use Buffer as the counter-leg ONLY when money moves into or out of an
  e-wallet or cash-on-hand account.

- A normal purchase paid directly from ONE envelope category is ONE leg.
  Example:
  "bought coffee 25000"
  -> negative cash_basis on the coffee/food allocation.
  Do NOT create a Buffer leg.

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

- If someone will reimburse part of an expense later:
  cash_basis = total amount paid, negative
  receivables = amount owed back, positive

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

    client = get_client()

    # IMPORTANT:
    # Groq organization OTPM limit = 1000.
    # The old request allowed 2048 output tokens, which caused:
    # RateLimitError 429 - Requested 2048, limit 1000.
    #
    # Transaction parsing only needs a tiny JSON response.
    # 400 tokens is more than enough.

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

    parts = [
        "Buffer summary: "
        + json.dumps(buf, default=str),

        "Quick view: "
        + json.dumps(qv, default=str),

        "Allocation model "
        "(fund/realisation/remaining per category & wallet):\n"
        + model.to_string(index=False),
    ]

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
