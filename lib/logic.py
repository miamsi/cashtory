"""Reimplements the spreadsheet's formulas in Python, over data pulled from
Supabase — one period (month) at a time.

Sheet -> function map:
    Buffer                   -> buffer_summary(period_id)
    Model                    -> allocation_model(period_id)
    Buffer Flow              -> buffer_flow(period_id)
    Quick View                -> quick_view(period_id)
    Consumption Performance  -> consumption_performance(period_id)
"""
from __future__ import annotations

import pandas as pd

from . import db


def _sum(df: pd.DataFrame, col: str) -> float:
    if df.empty or col not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def buffer_summary(period_id: str) -> dict:
    """Mirrors sheet 'Buffer': Income - Fixed - Savings - Encumbrance = Buffer."""
    income_total = _sum(db.get_income(period_id), "amount")
    fixed_total = _sum(db.get_fixed_spending(period_id), "amount")
    savings_total = _sum(db.get_savings(period_id), "amount")
    encumbrance_total = _sum(db.get_encumbrance(period_id), "amount")

    buffer = income_total - fixed_total - savings_total - encumbrance_total
    total_fund_in_balance = income_total - fixed_total - savings_total

    return {
        "income": income_total,
        "fixed_and_early_spendings": fixed_total,
        "savings": savings_total,
        "encumbrance": encumbrance_total,
        "buffer": buffer,
        "total_fund_in_balance": total_fund_in_balance,
    }


def _realisation_by_allocation(tx: pd.DataFrame) -> pd.Series:
    if tx.empty:
        return pd.Series(dtype=float)
    return tx.groupby("allocation")["cash_basis"].sum()


def allocation_model(period_id: str) -> pd.DataFrame:
    """Mirrors sheet 'Model': one row per allocation with Fund / Realisation / Remaining."""
    buf = buffer_summary(period_id)
    encumbrance = db.get_encumbrance(period_id)
    period_wallets = db.get_period_wallets(period_id)
    tx = db.get_transactions(period_id)
    realisation = _realisation_by_allocation(tx)

    rows = [{"allocation": "Buffer", "fund": buf["buffer"]}]
    for _, r in encumbrance.iterrows():
        rows.append({"allocation": r["name"], "fund": float(r["amount"])})
    for _, r in period_wallets.iterrows():
        rows.append({"allocation": r["wallet_name"], "fund": float(r["opening_balance"])})

    model = pd.DataFrame(rows)
    model["realisation"] = model["allocation"].map(realisation).fillna(0.0)
    model["remaining"] = model["fund"] + model["realisation"]

    total = pd.DataFrame([{
        "allocation": "Total fund in balance",
        "fund": buf["total_fund_in_balance"],
        "realisation": model["realisation"].sum(),
        "remaining": buf["total_fund_in_balance"] + model["realisation"].sum(),
    }])
    return pd.concat([model, total], ignore_index=True)


def buffer_flow(period_id: str) -> pd.DataFrame:
    """Mirrors sheet 'Buffer Flow': per wallet, money in from Buffer (top-ups),
    the wallet's opening threshold, money out, and whether/how much should be
    reversed back to Buffer."""
    period_wallets = db.get_period_wallets(period_id)
    tx = db.get_transactions(period_id)

    rows = []
    for _, w in period_wallets.iterrows():
        name = w["wallet_name"]
        threshold = float(w["opening_balance"])
        wtx = tx[tx["allocation"] == name] if not tx.empty else tx
        buffer_in = _sum(wtx[wtx["cash_basis"] > 0], "cash_basis") if not wtx.empty else 0.0
        buffer_out = _sum(wtx[wtx["cash_basis"] < 0], "cash_basis") if not wtx.empty else 0.0
        reversal = (buffer_in + threshold + buffer_out) if buffer_in > 0 else None
        rows.append({
            "wallet": name, "buffer_in": buffer_in, "threshold": threshold,
            "buffer_out": buffer_out, "buffer_needs_to_reverse": reversal,
        })
    return pd.DataFrame(rows)


def quick_view(period_id: str) -> dict:
    """Mirrors sheet 'Quick View'."""
    tx = db.get_transactions(period_id)
    model = allocation_model(period_id)
    buf = buffer_summary(period_id)

    current_date = tx["date"].max() if not tx.empty else None
    receivables = _sum(tx, "receivables")
    total_remaining_fund = float(model.loc[model["allocation"] == "Total fund in balance", "remaining"].iloc[0])

    model_realisation_total = float(
        model.loc[model["allocation"] != "Total fund in balance", "realisation"].sum()
    )
    fixed = db.get_fixed_spending(period_id)
    savings = db.get_savings(period_id)
    # first 4 fixed-spending rows + first savings row, matching the original
    # hardcoded cell references (fix and early spendings!C2:C5, savings!C2)
    fixed_head = _sum(fixed.head(4), "amount")
    savings_head = _sum(savings.head(1), "amount")

    total_outflow = model_realisation_total - fixed_head - savings_head
    total = total_remaining_fund - total_outflow
    status = "Balance" if abs(total - buf["income"]) < 0.01 else "Inbalance"

    return {
        "current_date": current_date,
        "receivables": receivables,
        "total_remaining_fund": total_remaining_fund,
        "total_outflow": total_outflow,
        "total": total,
        "status": status,
    }


def consumption_performance(period_id: str) -> pd.DataFrame:
    """Mirrors sheet 'Consumption Performance': daily food-budget pacing."""
    settings = db.get_settings()
    category = settings.get("daily_budget_category", "Jatah konsumsi harian")
    daily_budget = float(settings.get("daily_budget_amount", 150000))

    tx = db.get_transactions(period_id)
    if tx.empty:
        return pd.DataFrame(columns=["date", "realisation", "surplus_deficit"])

    day_tx = tx[tx["allocation"].str.lower() == category.lower()]
    if day_tx.empty:
        return pd.DataFrame(columns=["date", "realisation", "surplus_deficit"])

    daily = day_tx.groupby(day_tx["date"].dt.date)["accrual_basis"].sum().reset_index()
    daily.columns = ["date", "realisation"]
    daily["surplus_deficit"] = daily_budget + daily["realisation"]
    return daily.sort_values("date")


def allocation_names(period_id: str) -> list[str]:
    """All valid ledger allocation targets for this period: Buffer + envelope
    categories + wallets."""
    names = ["Buffer"]
    enc = db.get_encumbrance(period_id)
    pw = db.get_period_wallets(period_id)
    if not enc.empty:
        names += enc["name"].tolist()
    if not pw.empty:
        names += pw["wallet_name"].tolist()
    return names


def resolve_allocation(name: str, period_id: str) -> str | None:
    """Case-insensitively match a typed allocation name to its canonical stored
    name, avoiding the casing drift the original spreadsheet had (e.g. 'Jatah
    konsumsi harian' in encumbrance vs 'Jatah Konsumsi Harian' in Records)."""
    for canonical in allocation_names(period_id):
        if canonical.lower() == name.lower():
            return canonical
    return None


# ---------------------------------------------------------------------------
# Roll-forward: closing one period and opening the next
# ---------------------------------------------------------------------------
def propose_rollover(period_id: str) -> dict:
    """Compute what the next period's opening numbers WOULD be, without
    writing anything. Wallet balances always carry forward as-is (it's real
    cash sitting in the wallet); the Buffer + unspent envelope leftovers are
    surfaced as a suggested lump-sum 'carry-over' income line, since that
    money isn't tied to a specific wallet — editable before confirming.
    """
    model = allocation_model(period_id)
    period_wallets = db.get_period_wallets(period_id)

    wallet_names = set(period_wallets["wallet_name"]) if not period_wallets.empty else set()
    wallet_rows = model[model["allocation"].isin(wallet_names)]
    non_wallet_rows = model[
        (~model["allocation"].isin(wallet_names)) & (model["allocation"] != "Total fund in balance")
    ]

    carry_over_amount = float(non_wallet_rows["remaining"].sum())  # Buffer + envelopes leftover
    wallet_opening = {row["allocation"]: float(row["remaining"]) for _, row in wallet_rows.iterrows()}

    return {"carry_over_amount": carry_over_amount, "wallet_opening_balances": wallet_opening}
