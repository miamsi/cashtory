"""Import a monthly spreadsheet (same layout as the original Excel model) into
Supabase, for a specific user and period. Uses the SERVICE ROLE key, which
bypasses RLS — this is an admin/offline tool, never run it inside the app.

Usage:
    python scripts/seed_from_excel.py path/to/model.xlsx user@example.com "October 2026" 2026-10-01 2026-10-31

Requires SUPABASE_URL / SUPABASE_SERVICE_KEY in the environment (.env loaded
automatically). The user must already have signed up in the app once.

Safe-ish to re-run for the SAME period: envelope amounts upsert by name;
wallets upsert by name; income/fixed/savings/transactions are only inserted
if that period currently has none of that table's rows (so re-running won't
duplicate them, but editing values means deleting and re-running).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import openpyxl
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def get_admin_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in your environment (.env).")
        sys.exit(1)
    return create_client(url, key)


def read_two_col(ws, has_date=False):
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if has_date:
            d, desc, amount = row[0], row[1], row[2]
            if desc is None and amount is None:
                continue
            rows.append({"date": str(d.date()) if hasattr(d, "date") else str(d),
                         "description": desc, "amount": float(amount or 0)})
        else:
            name, amount = row[0], row[1]
            if name is None:
                continue
            rows.append({"name": name, "amount": float(amount or 0)})
    return rows


def main(path: str, email: str, label: str, start_date: str, end_date: str):
    wb = openpyxl.load_workbook(path, data_only=True)
    sb = get_admin_client()

    users = sb.auth.admin.list_users()
    user = next((u for u in users if u.email == email), None)
    if not user:
        print(f"No signed-up user found for {email}. Sign up in the app first.")
        sys.exit(1)
    user_id = user.id

    # Deactivate any current active period, create/find the target one.
    existing = sb.table("periods").select("*").eq("user_id", user_id).eq("label", label).execute()
    if existing.data:
        period_id = existing.data[0]["id"]
        print(f"Using existing period '{label}' ({period_id})")
    else:
        sb.table("periods").update({"is_active": False}).eq("user_id", user_id).eq("is_active", True).execute()
        res = sb.table("periods").insert({
            "user_id": user_id, "label": label, "start_date": start_date,
            "end_date": end_date, "is_active": True,
        }).execute()
        period_id = res.data[0]["id"]
        print(f"Created period '{label}' ({period_id})")

    def period_table_empty(table: str) -> bool:
        res = sb.table(table).select("id").eq("period_id", period_id).limit(1).execute()
        return len(res.data) == 0

    if period_table_empty("income"):
        rows = read_two_col(wb["income"], has_date=True)
        if rows:
            sb.table("income").insert(
                [{**r, "user_id": user_id, "period_id": period_id} for r in rows]
            ).execute()
            print(f"Inserted {len(rows)} income rows")

    if period_table_empty("fixed_spending"):
        rows = read_two_col(wb["fix and early spendings"], has_date=True)
        if rows:
            sb.table("fixed_spending").insert(
                [{**r, "user_id": user_id, "period_id": period_id} for r in rows]
            ).execute()
            print(f"Inserted {len(rows)} fixed_spending rows")

    if period_table_empty("savings"):
        rows = read_two_col(wb["savings"], has_date=True)
        if rows:
            sb.table("savings").insert(
                [{**r, "user_id": user_id, "period_id": period_id} for r in rows]
            ).execute()
            print(f"Inserted {len(rows)} savings rows")

    # encumbrance (dedupe by name, keep last), upsert by (period_id, name)
    enc_rows = {}
    for r in read_two_col(wb["encumbrance"], has_date=False):
        enc_rows[r["name"]] = r["amount"]
    for name, amount in enc_rows.items():
        sb.table("encumbrance").upsert(
            {"user_id": user_id, "period_id": period_id, "name": name, "amount": amount},
            on_conflict="period_id,name",
        ).execute()
    print(f"Upserted {len(enc_rows)} encumbrance categories")

    # wallet catalog (persistent) + this period's opening balances
    # NOTE: the original sheet has a duplicate 'Dana' row — deduped here.
    wallet_rows: dict[str, float] = {}
    for r in read_two_col(wb["wallets"], has_date=False):
        wallet_rows.setdefault(r["name"], r["amount"])
    for name, opening_balance in wallet_rows.items():
        sb.table("wallets").upsert(
            {"user_id": user_id, "name": name}, on_conflict="user_id,name"
        ).execute()
        sb.table("period_wallets").upsert(
            {"user_id": user_id, "period_id": period_id, "wallet_name": name,
             "opening_balance": opening_balance},
            on_conflict="period_id,wallet_name",
        ).execute()
    print(f"Upserted {len(wallet_rows)} wallets + opening balances")

    # allocation-name canonicalization (fixes casing drift like the original
    # sheet's 'Jatah Konsumsi Harian' in Records vs 'Jatah konsumsi harian' in
    # encumbrance)
    canonical = {n.lower(): n for n in enc_rows}
    canonical.update({n.lower(): n for n in wallet_rows})
    canonical["buffer"] = "Buffer"

    if period_table_empty("transactions"):
        ws = wb["Records"]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            date, desc, alloc, cash, recv = row[0], row[1], row[2], row[3], row[4]
            if desc is None:
                continue
            alloc_canonical = canonical.get(str(alloc).lower(), alloc)
            rows.append({
                "user_id": user_id, "period_id": period_id,
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "description": desc, "allocation": alloc_canonical,
                "cash_basis": float(cash or 0), "receivables": float(recv or 0),
                "source": "import",
            })
        if rows:
            sb.table("transactions").insert(rows).execute()
            print(f"Inserted {len(rows)} transaction (ledger) rows")

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(__doc__)
        sys.exit(1)
    main(*sys.argv[1:6])
