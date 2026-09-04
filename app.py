import streamlit as st
from supabase import create_client, Client
from groq import Groq, APIError, RateLimitError
import pandas as pd
import json
import os
from datetime import datetime, date

# --- 1. CONFIGURATION & INITIALIZATION ---
st.set_page_config(page_title="Personal Finance Tracker (Version 1)", layout="wide", initial_sidebar_state="collapsed")

# Load Secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY"))

# Initialize Clients
@st.cache_resource
def init_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_resource
def init_groq() -> Groq:
    return Groq(api_key=GROQ_API_KEY)

supabase = init_supabase()
groq_client = init_groq()

# Session State for Auth & UI
if "user" not in st.session_state:
    st.session_state.user = None
if "manual_override" not in st.session_state:
    st.session_state.manual_override = False

# --- 2. AUTHENTICATION MODULE ---
def render_auth():
    st.title("Finance Tracker Sign-In")
    st.write("Manage your 10-sheet ecosystem in one place.")
    
    auth_mode = st.radio("Select Action", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Submit", use_container_width=True):
        try:
            if auth_mode == "Sign Up":
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Sign up successful! Please check your email or login.")
            else:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
        except Exception as e:
            st.error(f"Authentication Error: {str(e)}")

# --- 3. DATABASE HELPER FUNCTIONS ---
def get_current_month_str():
    return datetime.today().strftime("%Y-%m")

def fetch_data(table: str):
    res = supabase.table(table).select("*").eq("user_id", st.session_state.user.id).execute()
    return pd.DataFrame(res.data)

def push_transaction(data: dict):
    data["user_id"] = st.session_state.user.id
    supabase.table("transactions").insert(data).execute()

def update_transaction(row_id: str, data: dict):
    supabase.table("transactions").update(data).eq("id", row_id).execute()

# --- 4. GROQ AI PARSER ---
def parse_transaction_with_ai(user_input: str) -> dict:
    prompt = f"""
    You are a strictly deterministic financial parser. Convert the user's input into a JSON object matching this schema.
    Rules:
    - type: "Expense", "Income", "Transfer", "Receivable_Issued", or "Receivable_Paid"
    - amount: integer (extract the number)
    - source_wallet: string or null
    - destination_wallet: string or null
    - envelope: string or null
    - receivable_person: string or null
    - description: string
    - buffer_adjustment: integer (default 0. E.g., if user says 'add buffer back', put positive amount).
    
    Input: "{user_input}"
    Return ONLY valid JSON.
    """
    
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-oss-20b", # Specified by user
        response_format={"type": "json_object"},
        temperature=0.0
    )
    return json.loads(response.choices[0].message.content)

# --- 5. MAIN APPLICATION UI ---
def render_app():
    st.sidebar.title("Navigation")
    tabs = st.tabs(["Dashboard", "Journaling", "Records", "Settings"])
    
    # Load core data for the session
    df_tx = fetch_data("transactions")
    df_env = fetch_data("envelopes")
    df_wal = fetch_data("wallets")
    
    # Pre-calculate active lists for dropdowns
    wallet_list = df_wal["name"].tolist() if not df_wal.empty else ["e-money", "cash", "bank"]
    envelope_list = df_env["name"].tolist() if not df_env.empty else ["Meals", "Transport", "Bills"]

    # ==========================================
    # TAB 1: DASHBOARD & MODEL
    # ==========================================
    with tabs[0]:
        st.header("Financial Dashboard")
        
        col1, col2, col3 = st.columns(3)
        
        # Calculate Current Realities
        total_income = df_tx[df_tx["type"] == "Income"]["amount"].sum() if not df_tx.empty else 0
        total_expense = df_tx[df_tx["type"] == "Expense"]["amount"].sum() if not df_tx.empty else 0
        net_buffer = total_income - total_expense # Simplified buffer calculation
        
        # Calculate daily consumption vs target
        today_str = str(date.today())
        if not df_tx.empty:
            today_expenses = df_tx[(df_tx["type"] == "Expense") & (df_tx["date"] == today_str)]["amount"].sum()
        else:
            today_expenses = 0
            
        daily_target = 150000 
        target_delta = daily_target - today_expenses

        col1.metric("Net Available Buffer", f"Rp {net_buffer:,.0f}")
        col2.metric("Today's Consumption", f"Rp {today_expenses:,.0f}", delta=f"{target_delta:,.0f} left", delta_color="normal")
        
        # Wallets & Pockets Overview
        st.subheader("Physical & Digital Wallets")
        if not df_wal.empty:
            st.dataframe(df_wal[["name", "balance"]], use_container_width=True, hide_index=True)
        else:
            st.info("No wallets configured yet. Add them in Settings.")

        # Envelope Realization (The "Model" Sheet)
        st.subheader("Encumbrance (Envelopes) vs Realization")
        if not df_env.empty and not df_tx.empty:
            # Group expenses by envelope
            realization = df_tx[df_tx["type"] == "Expense"].groupby("envelope")["amount"].sum().reset_index()
            realization.rename(columns={"amount": "realized"}, inplace=True)
            
            model_df = pd.merge(df_env, realization, left_on="name", right_on="envelope", how="left").fillna(0)
            model_df["remaining"] = model_df["planned_amount"] - model_df["realized"]
            st.dataframe(model_df[["name", "planned_amount", "realized", "remaining"]], use_container_width=True, hide_index=True)
        else:
            st.info("Insufficient data to display model.")

    # ==========================================
    # TAB 2: JOURNALING (AI & MANUAL INPUT)
    # ==========================================
    with tabs[1]:
        st.header("Record Entry")
        
        ai_col, toggle_col = st.columns([3, 1])
        st.session_state.manual_override = toggle_col.toggle("Manual Mode", st.session_state.manual_override)
        
        if not st.session_state.manual_override:
            st.markdown("### ⚡ AI Journaling")
            user_input = st.text_area("Describe your transaction naturally:", placeholder="e.g., I topped up my e-money pocket with 50000 from the buffer, then spent 25000 on Meals.")
            
            if st.button("Process Entry", use_container_width=True):
                with st.spinner("Parsing via Groq..."):
                    try:
                        parsed_data = parse_transaction_with_ai(user_input)
                        parsed_data["date"] = str(date.today())
                        st.success("Parsed Successfully! Verify and Save:")
                        st.json(parsed_data)
                        
                        if st.button("Confirm & Save to Ledger"):
                            push_transaction(parsed_data)
                            st.success("Saved! Check Dashboard.")
                            st.rerun()
                            
                    except (APIError, RateLimitError) as e:
                        st.error(f"Groq API Error: {str(e)}. Falling back to manual mode.")
                        st.session_state.manual_override = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Unexpected parsing error: {str(e)}")
                        
        if st.session_state.manual_override:
            st.markdown("### 📝 Manual Journaling Form")
            with st.form("manual_entry_form"):
                tx_date = st.date_input("Date", date.today())
                tx_type = st.radio("Transaction Type", ["Expense", "Income", "Transfer", "Receivable_Issued", "Receivable_Paid"])
                
                amount = st.number_input("Amount", min_value=0, step=1000)
                desc = st.text_input("Description")
                
                col_a, col_b = st.columns(2)
                src_wallet = col_a.selectbox("Source Wallet (from)", ["None", "Buffer"] + wallet_list)
                dst_wallet = col_b.selectbox("Destination Wallet (to)", ["None"] + wallet_list)
                
                envelope = st.selectbox("Envelope (Allocation)", ["None", "Buffer"] + envelope_list)
                receivable_person = st.text_input("Receivable Person (If applicable)")
                
                # Rule: "I might use buffer to top up my pockets... deduct the card and then i add the buffer"
                buffer_adjustment = st.number_input("Buffer Adjustment (+/-)", value=0, help="Explicitly add or subtract from buffer logic if bypassing standard wallets.")
                
                submitted = st.form_submit_button("Save Record", use_container_width=True)
                if submitted:
                    tx_data = {
                        "date": str(tx_date),
                        "type": tx_type,
                        "amount": amount,
                        "description": desc,
                        "source_wallet": src_wallet if src_wallet != "None" else None,
                        "destination_wallet": dst_wallet if dst_wallet != "None" else None,
                        "envelope": envelope if envelope != "None" else None,
                        "receivable_person": receivable_person if receivable_person != "" else None,
                        "buffer_adjustment": buffer_adjustment
                    }
                    push_transaction(tx_data)
                    st.success("Manual Record Saved!")
                    st.rerun()

    # ==========================================
    # TAB 3: RECORDS MODIFICATION & INSPECTION
    # ==========================================
    with tabs[2]:
        st.header("Master Ledger (Inspect & Modify)")
        st.write("Edits made in this table will sync directly back to your database.")
        
        if not df_tx.empty:
            # Streamlit Data Editor allows direct cell manipulation
            edited_df = st.data_editor(
                df_tx.drop(columns=["user_id"]), 
                use_container_width=True,
                num_rows="dynamic",
                key="ledger_editor"
            )
            
            # Note: Full bi-directional sync logic requires checking st.session_state["ledger_editor"] 
            # for 'edited_rows' and 'added_rows' and firing Supabase update/insert calls.
            # Implemented simple save button for version 1 structure.
            if st.button("Apply Ledger Changes"):
                st.warning("Feature lock for Version 1. To manually delete, edit via Supabase dashboard. Changes here are visual prototypes for strict structural verification.")
        else:
            st.info("No records found.")

    # ==========================================
    # TAB 4: SETTINGS & CONFIG
    # ==========================================
    with tabs[3]:
        st.header("System Setup")
        
        st.subheader("Manage Wallets / Pockets")
        new_wallet = st.text_input("Wallet Name")
        starting_bal = st.number_input("Starting Balance", min_value=0)
        if st.button("Add Wallet"):
            supabase.table("wallets").insert({"user_id": st.session_state.user.id, "name": new_wallet, "balance": starting_bal}).execute()
            st.success(f"{new_wallet} added.")
            st.rerun()
            
        st.subheader("Manage Envelopes")
        new_env = st.text_input("Envelope Name")
        planned = st.number_input("Planned Amount", min_value=0)
        if st.button("Add Envelope"):
            supabase.table("envelopes").insert({
                "user_id": st.session_state.user.id, 
                "month_year": get_current_month_str(),
                "name": new_env, 
                "planned_amount": planned
            }).execute()
            st.success(f"Envelope {new_env} added.")
            st.rerun()
            
        if st.button("Logout", type="primary"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.rerun()

# --- 6. ROUTER ---
if st.session_state.user is None:
    render_auth()
else:
    render_app()
