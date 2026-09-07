"""Data-access layer over Supabase. Every query goes through the authenticated,
per-session client (see lib/auth.py) so RLS scopes everything to the logged-in
user automatically — no manual user_id filtering needed here.

Almost every table is period-scoped; callers pass period_id explicitly rather
than relying on hidden global state, so pages can't accidentally mix data
from two different months.
"""
from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import streamlit as st

from . import auth


def get_client():
    return auth.get_authed_client()


def _df(query) -> pd.DataFrame:
    res = query.execute()
    return pd.DataFrame(res.data)


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------
def get_periods() -> pd.DataFrame:
    df = _df(get_client().table("periods").select("*").order("start_date", desc=True))
    return df


def get_active_period() -> dict | None:
    res = get_client().table("periods").select("*").eq("is_active", True).limit(1).execute()
    return res.data[0] if res.data else None


def create_period(label: str, start_date: date, end_date: date, make_active: bool = True) -> dict:
    sb = get_client()
    if make_active:
        # Postgres partial-unique-index requires the old active row cleared first.
        sb.table("periods").update({"is_active": False}).eq("is_active", True).execute()
    res = sb.table("periods").insert({
        "label": label, "start_date": str(start_date), "end_date": str(end_date),
        "is_active": make_active,
    }).execute()
    return res.data[0]


def set_active_period(period_id: str):
    sb = get_client()
    sb.table("periods").update({"is_active": False}).eq("is_active", True).execute()
    sb.table("periods").update({"is_active": True}).eq("id", period_id).execute()


# ---------------------------------------------------------------------------
# Income / fixed spending / savings (period-scoped)
# ---------------------------------------------------------------------------
def get_income(period_id: str) -> pd.DataFrame:
    return _df(get_client().table("income").select("*").eq("period_id", period_id).order("date"))


def get_fixed_spending(period_id: str) -> pd.DataFrame:
    return _df(get_client().table("fixed_spending").select("*").eq("period_id", period_id).order("date"))


def get_savings(period_id: str) -> pd.DataFrame:
    return _df(get_client().table("savings").select("*").eq("period_id", period_id).order("date"))


def add_income(period_id: str, d: date, description: str, amount: float):
    get_client().table("income").insert(
        {"period_id": period_id, "date": str(d), "description": description, "amount": amount}
    ).execute()


def add_fixed_spending(period_id: str, d: date, description: str, amount: float):
    get_client().table("fixed_spending").insert(
        {"period_id": period_id, "date": str(d), "description": description, "amount": amount}
    ).execute()


def add_savings(period_id: str, d: date, description: str, amount: float):
    get_client().table("savings").insert(
        {"period_id": period_id, "date": str(d), "description": description, "amount": amount}
    ).execute()


# ---------------------------------------------------------------------------
# Envelope categories (period-scoped)
# ---------------------------------------------------------------------------
def get_encumbrance(period_id: str, active_only: bool = True) -> pd.DataFrame:
    df = _df(get_client().table("encumbrance").select("*").eq("period_id", period_id).order("name"))
    if active_only and not df.empty:
        df = df[df["active"]]
    return df


def upsert_encumbrance(period_id: str, name: str, amount: float):
    get_client().table("encumbrance").upsert(
        {"period_id": period_id, "name": name, "amount": amount}, on_conflict="period_id,name"
    ).execute()


def copy_encumbrance_to_period(from_period_id: str, to_period_id: str):
    src = get_encumbrance(from_period_id, active_only=False)
    for _, r in src.iterrows():
        upsert_encumbrance(to_period_id, r["name"], float(r["amount"]))


# ---------------------------------------------------------------------------
# Wallets (persistent catalog) + period_wallets (per-period opening balance)
# ---------------------------------------------------------------------------
def get_wallets(active_only: bool = True) -> pd.DataFrame:
    df = _df(get_client().table("wallets").select("*").order("name"))
    if active_only and not df.empty:
        df = df[df["active"]]
    return df


def add_wallet(name: str):
    get_client().table("wallets").upsert({"name": name}, on_conflict="user_id,name").execute()


def get_period_wallets(period_id: str) -> pd.DataFrame:
    return _df(
        get_client().table("period_wallets").select("*").eq("period_id", period_id).order("wallet_name")
    )


def set_period_wallet_balance(period_id: str, wallet_name: str, opening_balance: float):
    get_client().table("period_wallets").upsert(
        {"period_id": period_id, "wallet_name": wallet_name, "opening_balance": opening_balance},
        on_conflict="period_id,wallet_name",
    ).execute()


# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def get_transactions(period_id: str, limit: int | None = None) -> pd.DataFrame:
    q = (
        get_client().table("transactions").select("*")
        .eq("period_id", period_id)
        .order("date", desc=True).order("id", desc=True)
    )
    if limit:
        q = q.limit(limit)
    df = _df(q)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def add_transaction_legs(period_id: str, legs: list[dict], source: str = "manual") -> str:
    """Insert one or more balanced ledger legs sharing a group_id.

    Each leg: {date, description, allocation, cash_basis, receivables}
    """
    group_id = str(uuid.uuid4())
    rows = [{**leg, "period_id": period_id, "group_id": group_id, "source": source} for leg in legs]
    get_client().table("transactions").insert(rows).execute()
    return group_id


def delete_transaction_group(group_id: str):
    get_client().table("transactions").delete().eq("group_id", group_id).execute()


# ---------------------------------------------------------------------------
# Settings (per user, not per period)
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "daily_budget_category": "Jatah konsumsi harian",
    "daily_budget_amount": "150000",
    "groq_model": "llama-3.3-70b-versatile",
}


def get_settings() -> dict:
    res = get_client().table("settings").select("*").execute()
    return {row["key"]: row["value"] for row in res.data}


def set_setting(key: str, value: str):
    get_client().table("settings").upsert({"key": key, "value": value}, on_conflict="user_id,key").execute()


def ensure_default_settings():
    existing = get_settings()
    for k, v in DEFAULT_SETTINGS.items():
        if k not in existing:
            set_setting(k, v)
