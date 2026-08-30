import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import streamlit as st
from openai import OpenAI

# 1. Environment & Path Setup
load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import DB_PATH, MODEL_NAME, OPENROUTER_BASE_URL, SUPPLIER_DIR
from app.database.db import (
    get_connection, initialize_database, seed_default_criteria,
    get_active_criteria, criteria_to_text, save_evaluation, get_ranking, get_supplier_detail
)
from app.services.pdf_service import extract_pdf_text
from app.services.scoring_service import calculate_scorecard
from app.agents.evaluation_agent import evaluate_supplier

# 2. Page Configuration
st.set_page_config(page_title="RFP Supplier Evaluation", page_icon="📊", layout="wide")
st.title("📊 RFP Supplier Evaluation")
st.caption("LLM-assisted evaluation • deterministic scoring • PPI • ranking")

# 3. Database Initialization
conn = get_connection(str(DB_PATH))
initialize_database(conn)
seed_default_criteria(conn)

# 4. API Key Resolution (Env variables first, then Streamlit Secrets fallback)
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        api_key = None

# 5. Sidebar Setup
pdfs = sorted(SUPPLIER_DIR.glob("*.pdf"))

with st.sidebar:
    st.header("Run Evaluation")
    selected = st.selectbox("Supplier PDF", pdfs, format_func=lambda p: p.stem) if pdfs else None
    run = st.button("Evaluate supplier", type="primary", disabled=(selected is None or not api_key))
    
    if not api_key:
        st.error("Add OPENROUTER_API_KEY to Streamlit secrets or environment variables.")
    if not pdfs:
        st.info("Put supplier PDFs in data/suppliers/.")

# 6. Evaluation Process Logic
if run:
    try:
        criteria = get_active_criteria(conn)
        text = extract_pdf_text(str(selected))
        client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)
        
        with st.spinner("Evaluating proposal..."):
            evaluation = evaluate_supplier(text, criteria_to_text(criteria), criteria, client, MODEL_NAME)
            scorecard = calculate_scorecard(evaluation, criteria)

        save_evaluation(conn, evaluation, scorecard, 0, 0)
        st.success(f"Successfully evaluated and saved: {evaluation.supplier_name}")

        # Recompute rankings & PPI dynamically
        ranking = get_ranking(conn)
        if not ranking.empty:
            avg = ranking["weighted_score"].mean()
            ranking = ranking.sort_values("weighted_score", ascending=False).reset_index(drop=True)
            ranking["rank"] = ranking.index + 1
            ranking["ppi"] = ranking["weighted_score"] / avg if avg else 0
            
            for _, r in ranking.iterrows():
                sid = conn.execute("SELECT supplier_id FROM suppliers WHERE supplier_name=?",
                                   (r["supplier_name"],)).fetchone()[0]
                conn.execute("UPDATE supplier_results SET rank=?, ppi=? WHERE supplier_id=?",
                             (int(r["rank"]), float(r["ppi"]), sid))
            conn.commit()
            st.rerun()
    except Exception as e:
        st.exception(e)

# 7. Dashboard Visualizations
ranking = get_ranking(conn)

if ranking.empty:
    st.info("💡 Evaluate at least one supplier from the sidebar to view metrics.")
else:
    # Top-Level Executive Banner
    st.subheader("📌 Executive Overview")
    k1, k2, k3, k4 = st.columns(4)
    top_supplier = ranking.iloc[0]
    
    k1.metric("Leading Supplier", top_supplier["supplier_name"], delta="Rank #1")
    k2.metric("Top Score", f"{top_supplier['weighted_score']:.2f} / 10")
    k3.metric("Evaluated Vendors", len(ranking))
    k4.metric("Average PPI", f"{ranking['ppi'].mean():.2f}")

    st.divider()

    # Organized Tab Layout
    tab_rank, tab_compare, tab_details = st.tabs(["🏆 Leaderboard", "📊 Comparison Matrix", "🔍 Vendor Deep Dive"])

    # TAB 1: Leaderboard Matrix
    with tab_rank:
        st.caption("Suppliers ranked by overall weighted score and Proposal Performance Index (PPI).")
        shown = ranking.copy()
        shown["weighted_score"] = shown["weighted_score"].round(2)
        shown["percentage_score"] = shown["percentage_score"].round(1)
        shown["ppi"] = shown["ppi"].round(3)
        
        st.dataframe(
            shown, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "percentage_score": st.column_config.ProgressColumn(
                    "Fulfillment %", format="%.1f%%", min_value=0, max_value=100
                ),
                "rank": st.column_config.NumberColumn("Rank", format="#%d"),
                "weighted_score": st.column_config.NumberColumn("Weighted Score", format="%.2f / 10"),
                "ppi": st.column_config.NumberColumn("PPI Ratio", format="%.3f"),
            }
        )

    # TAB 2: Visual Vendor Comparison
    with tab_compare:
        st.subheader("Comparative Supplier Performance")
        st.bar_chart(
            ranking, 
            x="supplier_name", 
            y="weighted_score", 
            color="supplier_name",
            use_container_width=True
        )

    # TAB 3: Audit & Details
    with tab_details:
        name = st.selectbox("Select Supplier for Full Evaluation Audit", ranking["supplier_name"].tolist())
        result, criteria_df, risks_df = get_supplier_detail(conn, name)
        
        if not result.empty:
            r = result.iloc[0]
            
            # Key Vendor Metrics
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Final Rank", int(r["rank"]))
            c2.metric("Weighted Score", f"{r['weighted_score']:.2f} / 10")
            c3.metric("Fulfillment", f"{r['percentage_score']:.1f}%")
            c4.metric("PPI Index", f"{r['ppi']:.3f}")

            st.divider()

            col_summary, col_risks = st.columns([2, 1])

            with col_summary:
                st.markdown("### 📝 Executive Summary")
                st.info(r["overall_summary"])

            with col_risks:
                st.markdown("### ⚠️ Identified Risks")
                if not risks_df.empty and risks_df.iloc[0]["risks_json"]:
                    try:
                        risks = json.loads(risks_df.iloc[0]["risks_json"])
                        if risks:
                            for risk in risks:
                                st.warning(f"• {risk}")
                        else:
                            st.success("No critical risks detected.")
                    except Exception:
                        st.success("No critical risks detected.")
                else:
                    st.success("No critical risks detected.")

            st.markdown("### 📋 Detailed Criteria Evaluation")
            for _, item in criteria_df.iterrows():
                score_pct = (item['score'] / item['max_score']) * 100 if item['max_score'] > 0 else 0
                status_icon = "🟢" if score_pct >= 75 else ("🟡" if score_pct >= 50 else "🔴")
                
                with st.expander(f"{status_icon} **{item['name']}** — {item['score']:.1f} / {item['max_score']:.1f} (Weight: {item['weight']})"):
                    st.markdown("**Assessment Justification:**")
                    st.write(item["justification"])
                    st.markdown("**Extracted PDF Evidence:**")
                    st.caption(f'"{item["evidence"]}"')

            # PDF/CSV Report Export
            st.divider()
            csv_data = criteria_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 Download {name} Evaluation Report (CSV)",
                data=csv_data,
                file_name=f"{name}_evaluation_report.csv",
                mime="text/csv",
            )

st.caption("Deterministic scoring & PPI calculated dynamically via SQLite.")