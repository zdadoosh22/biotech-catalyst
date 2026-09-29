"""BioCatalyst - Interactive Biotech Catalyst & Clinical Trial Intelligence Dashboard.

A local, evidence-first platform bridging molecular biology and financial markets.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json

from core.db import DatabaseManager
from core.models import ClinicalTrial, CompanyFinancials, DilutionRiskLevel, ConsensusVerdict
from core.config import GEMINI_API_KEY, KNOWN_BIOTECH_REGISTRY
from clients.clinical_trials import ClinicalTrialsClient
from clients.market_data import MarketDataClient
from clients.sponsor_matcher import SponsorMatcher
from agents.committee import DiligenceCommittee
from reports.exporter import ReportExporter

# Configure Streamlit page
st.set_page_config(
    page_title="BioCatalyst | Clinical Trial & Financial Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize singletons in session state
if "db" not in st.session_state:
    st.session_state.db = DatabaseManager()
if "ct_client" not in st.session_state:
    st.session_state.ct_client = ClinicalTrialsClient()
if "mkt_client" not in st.session_state:
    st.session_state.mkt_client = MarketDataClient()
if "committee" not in st.session_state:
    st.session_state.committee = DiligenceCommittee()

db: DatabaseManager = st.session_state.db
ct_client: ClinicalTrialsClient = st.session_state.ct_client
mkt_client: MarketDataClient = st.session_state.mkt_client
committee: DiligenceCommittee = st.session_state.committee


# --- Helper Functions ---

def format_currency(val: float) -> str:
    if val is None or np.isnan(val):
        return "N/A"
    if abs(val) >= 1e9:
        return f"${val / 1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:.1f}M"
    return f"${val:,.2f}"


def estimate_months_to_date(date_str: str) -> float:
    if not date_str:
        return 12.0
    now = datetime.utcnow()
    try:
        if len(date_str) >= 7 and "-" in date_str:
            parts = date_str.split("-")
            yr = int(parts[0])
            mo = int(parts[1])
            return max(1.0, (yr - now.year) * 12.0 + (mo - now.month))
    except Exception:
        pass
    return 12.0


# --- Sidebar Navigation ---

st.sidebar.title("🧬 BioCatalyst")
st.sidebar.caption("Biotech Catalyst & Financial Solvency Intelligence")

nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "📅 Catalyst Timeline",
        "🎯 Dilution Radar & Runway",
        "🔬 AI Diligence Committee",
        "🔍 Live Trial Harvester",
        "💼 Watchlist & Solvency"
    ],
    index=0
)

st.sidebar.markdown("---")
# Status indicator
llm_status = "🟢 Gemini Pro Active" if GEMINI_API_KEY else "🔵 Expert Heuristic Active"
st.sidebar.markdown(f"**AI Engine**: `{llm_status}`")
trial_count = db.count_trials()
st.sidebar.markdown(f"**Indexed Trials**: `{trial_count}`")

st.sidebar.markdown("---")
st.sidebar.caption(
    "BioCatalyst decouples clinical risk from balance sheet dilution. "
    "Designed for tracking binary catalyst events in biotech."
)


# ==============================================================================
# Page 1: Catalyst Timeline & Calendar
# ==============================================================================
if nav_choice == "📅 Catalyst Timeline":
    st.header("📅 Clinical Catalyst Timeline & Calendar")
    st.write(
        "Monitor upcoming Phase 1/2/3 trial readouts, expected catalyst quarters, "
        "and sponsor pipeline milestones."
    )

    trials = db.list_trials(limit=500)

    if not trials:
        st.info("No trials found in local database. Go to **Live Trial Harvester** to scan active studies!")
    else:
        # KPI Row
        total_trials = len(trials)
        with_tickers = sum(1 for t in trials if t.matched_ticker)
        phase3_count = sum(1 for t in trials if any("3" in p for p in t.phases))
        phase2_count = sum(1 for t in trials if any("2" in p for p in t.phases))

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Tracked Trials", total_trials)
        kpi2.metric("Public Sponsors (Tickers)", with_tickers)
        kpi3.metric("Pivotal Phase 3 Trials", phase3_count)
        kpi4.metric("Signal Phase 2 Trials", phase2_count)

        st.markdown("---")

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            all_phases = ["All Phases", "Phase 3", "Phase 2", "Phase 1"]
            sel_phase = st.selectbox("Filter Phase", all_phases)
        with f2:
            all_sponsors = ["All Sponsors"] + sorted(list({t.sponsor_name for t in trials}))
            sel_sponsor = st.selectbox("Filter Sponsor", all_sponsors)
        with f3:
            search_text = st.text_input("Search Title or Indication", "")

        filtered_trials = trials
        if sel_phase != "All Phases":
            filtered_trials = [t for t in filtered_trials if any(sel_phase.lower() in p.lower() for p in t.phases)]
        if sel_sponsor != "All Sponsors":
            filtered_trials = [t for t in filtered_trials if t.sponsor_name == sel_sponsor]
        if search_text:
            st_lower = search_text.lower()
            filtered_trials = [
                t for t in filtered_trials
                if st_lower in t.title.lower() or any(st_lower in c.lower() for c in t.conditions)
            ]

        # Catalyst Timeline Chart (Plotly)
        timeline_data = []
        for t in filtered_trials:
            if t.primary_completion_date:
                start = t.start_date or "2024-01-01"
                # Ensure valid start format
                if len(start) == 4:
                    start += "-01-01"
                elif len(start) == 7:
                    start += "-01"

                end = t.primary_completion_date
                if len(end) == 4:
                    end += "-12-31"
                elif len(end) == 7:
                    end += "-28"

                timeline_data.append({
                    "NCT ID": t.nct_id,
                    "Study": t.title[:45] + "...",
                    "Sponsor": t.sponsor_name[:20],
                    "Ticker": t.matched_ticker or "Private",
                    "Phase": ", ".join(t.phases) if t.phases else "N/A",
                    "Catalyst Window": t.estimated_catalyst_window or "TBD",
                    "Start": start,
                    "Completion": end
                })

        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)
            try:
                fig = px.timeline(
                    df_timeline,
                    x_start="Start",
                    x_end="Completion",
                    y="Study",
                    color="Ticker",
                    hover_data=["NCT ID", "Sponsor", "Phase", "Catalyst Window"],
                    title="Clinical Trial Readout Horizon"
                )
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(height=450, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        # Interactive Table
        st.subheader("📋 Tracked Catalysts Matrix")
        table_rows = []
        for t in filtered_trials:
            table_rows.append({
                "NCT ID": t.nct_id,
                "Ticker": f"${t.matched_ticker}" if t.matched_ticker else "-",
                "Sponsor": t.sponsor_name,
                "Phases": ", ".join(t.phases),
                "Catalyst Window": t.estimated_catalyst_window or "TBD",
                "Primary Completion": t.primary_completion_date or "-",
                "Enrollment": t.enrollment or 0,
                "Status": t.status,
                "Primary Indication": t.conditions[0] if t.conditions else "N/A"
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


# ==============================================================================
# Page 2: Dilution Radar & Runway
# ==============================================================================
elif nav_choice == "🎯 Dilution Radar & Runway":
    st.header("🎯 Cash Runway & Dilution Risk Radar")
    st.write(
        "A quantitative assessment of balance sheet solvency. Companies plotted "
        "**below the threshold** will exhaust cash before their clinical readout happens, "
        "creating imminent secondary offering or share dilution risk."
    )

    financials_list = db.list_all_financials()

    col_btn1, col_btn2 = st.columns([2, 5])
    with col_btn1:
        if st.button("🔄 Refresh Market Data for Watchlist"):
            with st.spinner("Fetching latest 10-Q/10-K balance sheet metrics..."):
                for entry in KNOWN_BIOTECH_REGISTRY.values():
                    t_tk = entry["ticker"]
                    fin = mkt_client.get_financials(t_tk)
                    if fin:
                        db.upsert_financials(fin)
                st.success("Financial metrics updated!")
                financials_list = db.list_all_financials()

    if not financials_list:
        st.info("No balance sheet records found yet. Click the button above to seed financial data for top biotechs!")
    else:
        # Build scatter data
        radar_points = []
        trials = db.list_trials(limit=500)

        # Map ticker to closest trial readout months
        ticker_to_months: dict[str, float] = {}
        for t in trials:
            if t.matched_ticker:
                m = estimate_months_to_date(t.primary_completion_date)
                if t.matched_ticker not in ticker_to_months or m < ticker_to_months[t.matched_ticker]:
                    ticker_to_months[t.matched_ticker] = m

        for fin in financials_list:
            readout_mos = ticker_to_months.get(fin.ticker, 18.0)
            runway = fin.cash_runway_months or 12.0
            if runway > 60:
                runway = 60.0  # Cap visual plot at 60 months for scale

            radar_points.append({
                "Ticker": fin.ticker,
                "Company": fin.company_name,
                "Cash (M)": (fin.total_liquid_cash or 0) / 1e6,
                "Quarterly Burn (M)": (fin.quarterly_burn_rate or 0) / 1e6,
                "Runway (Months)": runway,
                "Months to Next Readout": readout_mos,
                "Dilution Risk": fin.dilution_risk_level.value,
                "Market Cap (B)": (fin.market_cap or 0) / 1e9
            })

        df_radar = pd.DataFrame(radar_points)

        # Plotly Scatter Chart
        fig = px.scatter(
            df_radar,
            x="Months to Next Readout",
            y="Runway (Months)",
            color="Dilution Risk",
            size="Market Cap (B)",
            hover_name="Ticker",
            hover_data=["Company", "Cash (M)", "Quarterly Burn (M)", "Runway (Months)"],
            color_discrete_map={
                "LOW": "#00CC96",
                "MODERATE": "#FFA15A",
                "HIGH": "#EF553B",
                "CRITICAL": "#B82E2E"
            },
            title="Solvency Diagonal: Cash Runway vs. Clinical Readout Horizon"
        )

        # Draw diagonal 1:1 line (Runway = Readout)
        fig.add_shape(
            type="line",
            x0=0, y0=0, x1=48, y1=48,
            line=dict(color="Red", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=32, y=28,
            text="⚠️ Danger Zone (Cash Exhausted Before Data)",
            showarrow=False,
            font=dict(color="red", size=11)
        )
        fig.add_annotation(
            x=15, y=35,
            text="✅ Safe Cushion (Funded Past Data)",
            showarrow=False,
            font=dict(color="green", size=11)
        )

        fig.update_layout(
            xaxis_title="Estimated Months Until Catalyst Readout",
            yaxis_title="Cash Runway (Months of Reserves)",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📉 Readout Density vs. Industry Solvency Cliff")
        st.write("Visualizes the concentration of clinical catalysts over time against the median industry cash runway.")
        
        if df_radar["Months to Next Readout"].count() > 0:
            median_runway = df_radar["Runway (Months)"].median()
            
            # Histogram of readouts
            fig_density = px.histogram(
                df_radar,
                x="Months to Next Readout",
                nbins=24,
                color="Dilution Risk",
                color_discrete_map={
                    "LOW": "#00CC96",
                    "MODERATE": "#FFA15A",
                    "HIGH": "#EF553B",
                    "CRITICAL": "#B82E2E"
                },
                marginal="box",
                title="Clinical Readout Density Curve"
            )
            
            # Overlay Median Runway
            fig_density.add_vline(
                x=median_runway, 
                line_width=3, 
                line_dash="dash", 
                line_color="red",
                annotation_text=f"Median Cash Exhaustion ({median_runway:.1f} mos)", 
                annotation_position="top right"
            )
            
            fig_density.update_layout(
                xaxis_title="Estimated Months Until Catalyst Readout",
                yaxis_title="Number of Scheduled Readouts",
                height=400,
                bargap=0.1
            )
            st.plotly_chart(fig_density, use_container_width=True)

        st.subheader("📊 Balance Sheet & Dilution Rankings")
        fin_rows = []
        for fin in financials_list:
            fin_rows.append({
                "Ticker": f"${fin.ticker}",
                "Company": fin.company_name,
                "Stock Price": f"${fin.stock_price:.2f}" if fin.stock_price else "-",
                "Market Cap": format_currency(fin.market_cap),
                "Liquid Cash": format_currency(fin.total_liquid_cash),
                "Quarterly Burn": format_currency(fin.quarterly_burn_rate),
                "Cash Runway": f"{fin.cash_runway_months:.1f} mos" if fin.cash_runway_months and fin.cash_runway_months < 900 else "Indefinite",
                "Dilution Risk": fin.dilution_risk_level.value,
                "Last Updated": fin.fetched_at[:10]
            })
        st.dataframe(pd.DataFrame(fin_rows), use_container_width=True, hide_index=True)


# ==============================================================================
# Page 3: AI Multi-Agent Diligence Committee
# ==============================================================================
elif nav_choice == "🔬 AI Diligence Committee":
    st.header("🔬 AI Multi-Agent Diligence Committee")
    st.write(
        "Convene the three specialized agents to audit a clinical trial: "
        "**Dr. Elena Vance** (Molecular MoA & Target Plausibility), "
        "**Dr. Marcus Thorne** (Biostatistical & Endpoint Rigor), and "
        "**Alexander Vance, CFA** (Cash Runway & Asymmetric Payoff)."
    )

    # Input NCT ID
    existing_trials = db.list_trials(limit=100)
    trial_options = [f"{t.nct_id} - {t.sponsor_name} - {t.title[:50]}..." for t in existing_trials]

    c_in1, c_in2 = st.columns([3, 1])
    with c_in1:
        nct_input = st.text_input("Enter NCT Identifier (or choose from list below):", value="NCT03313778").strip().upper()
    with c_in2:
        st.write("")
        st.write("")
        run_audit_btn = st.button("🚀 Convene Committee", type="primary")

    if trial_options:
        selected_option = st.selectbox("Or select from tracked studies:", [""] + trial_options)
        if selected_option:
            nct_input = selected_option.split(" - ")[0].strip()

    if run_audit_btn and nct_input:
        with st.spinner(f"Harvesting protocol, literature, and running 3-agent audit for {nct_input}..."):
            trial = db.get_trial(nct_input)
            if not trial:
                trial = ct_client.fetch_trial_by_nct(nct_input)
                if trial:
                    db.upsert_trial(trial)

            if not trial:
                st.error(f"Could not locate clinical study protocol for {nct_input}. Please verify the NCT ID.")
            else:
                financials = None
                if trial.matched_ticker:
                    financials = db.get_financials(trial.matched_ticker)
                    if not financials:
                        financials = mkt_client.get_financials(trial.matched_ticker)
                        if financials:
                            db.upsert_financials(financials)

                report = committee.conduct_diligence(trial, financials, include_pubmed=True)
                db.save_report(report)
                st.session_state["active_report"] = report
                st.session_state["active_trial"] = trial
                st.session_state["active_fin"] = financials

    # Display Active Report
    report = st.session_state.get("active_report")
    trial = st.session_state.get("active_trial")
    financials = st.session_state.get("active_fin")

    # If no report in session state, check DB
    if not report and nct_input:
        cached_rep = db.get_latest_report_for_trial(nct_input)
        if cached_rep:
            report = cached_rep
            trial = db.get_trial(nct_input)
            if trial and trial.matched_ticker:
                financials = db.get_financials(trial.matched_ticker)

    if report and trial:
        st.markdown("---")

        # Consensus Banner
        verdict_color = {
            "STRONG_CONVICTION": "green",
            "SPECULATIVE_ASYMMETRIC": "orange",
            "NEUTRAL_WATCH": "blue",
            "HIGH_RISK_AVOID": "red"
        }.get(report.consensus_verdict.value, "gray")

        score_col, summary_col = st.columns([1, 3])
        with score_col:
            st.metric("Consensus Verdict", report.consensus_verdict.value)
            st.metric("Overall Diligence Score", f"{report.overall_score:.1f} / 100")
            st.metric("Catalyst Window", trial.estimated_catalyst_window or "TBD")
        with summary_col:
            st.subheader(f"Diligence Brief: {report.nct_id}")
            st.markdown(f"**Asset**: {report.trial_title}")
            st.markdown(f"**Lead Sponsor**: {report.sponsor} ({'$' + report.ticker if report.ticker else 'Private'}) | **Status**: `{trial.status}`")
            st.info(report.executive_summary)
            if trial.data_integrity_warnings:
                st.warning("⚠️ **Protocol Registration & Consistency Alerts:**\n" + "\n".join(f"- {w}" for w in trial.data_integrity_warnings))

        # Agent Tabs + Dossier + Audit
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🧬 Dr. Elena Vance (Molecular MoA)",
            "📊 Dr. Marcus Thorne (Biostatistics)",
            "📈 Alexander Vance, CFA (Financial Solvency)",
            "⚖️ Scoring Audit Trail",
            "📄 Full Markdown Dossier"
        ])

        with tab1:
            st.subheader("Molecular Biology & Target Validation Audit")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.write(f"**Biological Target**: `{report.molecular_analysis.target_name}`")
                st.write(f"**Modality**: `{report.molecular_analysis.modality}`")
                st.write(f"**Biological Plausibility**: `{report.molecular_analysis.biological_plausibility}`")
            with col_m2:
                st.write(f"**Preclinical Strength**: `{report.molecular_analysis.preclinical_evidence_strength}`")
                st.write(f"**Confidence Score**: `{report.molecular_analysis.confidence_score * 100:.0f}%`")

            st.markdown("**Target Validation Summary:**")
            st.write(report.molecular_analysis.target_validation_summary)

            st.markdown("**Biological Resistance & Escape Pathways:**")
            st.write(report.molecular_analysis.resistance_risk_notes)

        with tab2:
            st.subheader("Clinical Biostatistics & Protocol Rigor Audit")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.write(f"**Trial Design Rigor**: `{report.biostat_audit.trial_design_rigor}`")
                st.write(f"**Endpoint Quality**: `{report.biostat_audit.endpoint_quality}`")
                st.write(f"**Blinding**: `{report.biostat_audit.blinding_rigor}`")
            with col_b2:
                st.write(f"**Control Arm**: `{report.biostat_audit.control_arm_critique}`")
                st.write(f"**Confidence Score**: `{report.biostat_audit.confidence_score * 100:.0f}%`")

            st.markdown("**Primary Endpoint Rigor:**")
            st.write(report.biostat_audit.endpoint_analysis)

            st.markdown("**Statistical Power Assessment:**")
            st.write(report.biostat_audit.power_and_sample_size_assessment)

            if report.biostat_audit.red_flags:
                st.markdown("**⚠️ Critical Methodology Vulnerabilities:**")
                for rf in report.biostat_audit.red_flags:
                    st.markdown(f"- ❌ {rf}")
            else:
                st.success("✅ No critical methodology red flags detected in registered design.")

        with tab3:
            st.subheader("Bio-Financial Solvency & Asymmetry Audit")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.write(f"**Runway vs Readout**: `{report.financial_audit.runway_vs_readout_alignment}`")
                st.write(f"**Binary Exposure**: `{report.financial_audit.binary_risk_exposure}`")
                st.write(f"**Asymmetry Profile**: `{report.financial_audit.asymmetry_ratio}`")
                st.write(f"**Confidence Score**: `{report.financial_audit.confidence_score * 100:.0f}%`")
            with col_f2:
                if financials:
                    st.write(f"**Current Stock Price**: `${financials.stock_price:.2f}`" if financials.stock_price else "-")
                    st.write(f"**Total Liquid Cash**: {format_currency(financials.total_liquid_cash)}")
                    if financials.short_term_debt:
                        st.write(f"**Short-Term Debt (<1yr)**: {format_currency(financials.short_term_debt)}")
                    if financials.short_term_investments:
                        st.write(f"**Short-Term Treasuries**: {format_currency(financials.short_term_investments)}")
                    st.write(f"**Quarterly Burn**: {format_currency(financials.quarterly_burn_rate)}")
                else:
                    st.write("*Public financial metrics not applicable.*")

            if financials and financials.data_freshness_warning:
                st.warning(financials.data_freshness_warning)

            # Probabilistic Timing & Dilution Probability
            st.markdown("---")
            st.markdown("#### ⏳ Probabilistic Readout Horizon & Dilution Risk")
            col_t1, col_t2, col_t3, col_t4 = st.columns(4)
            with col_t1:
                p10_val = f"{report.financial_audit.p10_readout_months:.1f} mos" if report.financial_audit.p10_readout_months is not None else "N/A"
                st.metric("P10 Readout (Optimistic)", p10_val)
            with col_t2:
                p50_val = f"{report.financial_audit.p50_readout_months:.1f} mos" if report.financial_audit.p50_readout_months is not None else "N/A"
                st.metric("P50 Readout (Median Expected)", p50_val)
            with col_t3:
                p90_val = f"{report.financial_audit.p90_readout_months:.1f} mos" if report.financial_audit.p90_readout_months is not None else "N/A"
                st.metric("P90 Readout (Delayed)", p90_val)
            with col_t4:
                dil_prob = f"{report.financial_audit.dilution_probability_before_readout * 100:.0f}%" if report.financial_audit.dilution_probability_before_readout is not None else "N/A"
                st.metric("Pre-Readout Dilution Prob", dil_prob)

            if report.financial_audit.slippage_risk_factors:
                st.markdown("**Timeline & Accrual Slippage Drivers:**")
                for srf in report.financial_audit.slippage_risk_factors:
                    st.markdown(f"- ⏳ {srf}")

            st.markdown("**Commercial Market Opportunity:**")
            st.write(report.financial_audit.commercial_market_opportunity)

            st.markdown("**Projected Secondary Offering / Dilution Timing:**")
            if report.financial_audit.runway_vs_readout_alignment == "DILUTION_IMMINENT":
                st.error(report.financial_audit.projected_dilution_window)
            else:
                st.success(report.financial_audit.projected_dilution_window)

        with tab4:
            st.subheader("Algorithmic Scoring Audit Trail")
            st.write("Transparent breakdown of how the final composite score was calculated, including additive components and multiplicative gating penalties.")
            
            for step in report.scoring_audit_trail:
                if "PENALTY" in step:
                    st.error(step)
                elif "+" in step:
                    st.success(step)
                else:
                    st.info(step)

        with tab5:
            st.subheader("Complete Diligence Dossier (Markdown)")
            md_content = ReportExporter.export_to_markdown(report, trial, financials)
            st.download_button(
                label="📥 Download Dossier (.md)",
                data=md_content,
                file_name=f"{report.nct_id}_diligence_dossier.md",
                mime="text/markdown"
            )
            st.code(md_content, language="markdown")


# ==============================================================================
# Page 4: Live Trial Harvester
# ==============================================================================
elif nav_choice == "🔍 Live Trial Harvester":
    st.header("🔍 Live Clinical Trial Harvester")
    st.write(
        "Directly query the ClinicalTrials.gov v2 REST API for active studies, "
        "auto-resolve sponsor tickers, and import candidate catalysts into your local database."
    )

    with st.form("harvest_form"):
        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            q_term = st.text_input("Intervention / Keyword (e.g. mRNA-4157, VK2735, KRAS)", value="mRNA")
        with h_col2:
            q_cond = st.text_input("Condition (e.g. Melanoma, Obesity, Solid Tumors)", value="Melanoma")
        with h_col3:
            q_spons = st.text_input("Sponsor Name (e.g. Moderna, Merck, Viking)", value="Moderna")

        h_limit = st.slider("Max Studies to Fetch", min_value=5, max_value=30, value=10)
        submitted = st.form_submit_button("🔍 Search Live ClinicalTrials.gov", type="primary")

    if submitted:
        with st.spinner("Connecting to ClinicalTrials.gov API v2..."):
            found_trials = ct_client.search_trials(
                query=q_term,
                condition=q_cond,
                sponsor=q_spons,
                page_size=h_limit
            )

            if not found_trials:
                st.warning("No studies returned matching those criteria. Try broadening your terms.")
            else:
                st.success(f"Discovered {len(found_trials)} clinical studies!")
                st.session_state["harvest_results"] = found_trials

    harvested = st.session_state.get("harvest_results", [])
    if harvested:
        if st.button("💾 Save All Discovered Studies to Local Database"):
            for t in harvested:
                db.upsert_trial(t)
            st.success(f"Successfully saved {len(harvested)} studies into local SQLite!")

        h_table = []
        for t in harvested:
            h_table.append({
                "NCT ID": t.nct_id,
                "Title": t.title[:60] + "...",
                "Sponsor": t.sponsor_name,
                "Resolved Ticker": f"${t.matched_ticker}" if t.matched_ticker else "Unresolved",
                "Phase": ", ".join(t.phases),
                "Catalyst Window": t.estimated_catalyst_window or "TBD",
                "Primary Completion": t.primary_completion_date or "N/A"
            })
        st.dataframe(pd.DataFrame(h_table), use_container_width=True, hide_index=True)


# ==============================================================================
# Page 5: Watchlist & Solvency
# ==============================================================================
elif nav_choice == "💼 Watchlist & Solvency":
    st.header("💼 Catalyst Watchlist & Asset Solvency")
    st.write(
        "Manage your high-priority biotech tickers and specific clinical trial milestones."
    )

    w_col1, w_col2 = st.columns([3, 2])
    with w_col1:
        st.subheader("Add to Watchlist")
        with st.form("add_watch_form"):
            in_ident = st.text_input("Ticker or NCT ID (e.g. MRNA, VKTX, NCT03313778)").strip().upper()
            in_alias = st.text_input("Alias / Label (Optional)")
            in_notes = st.text_area("Investment Thesis / Diligence Notes")
            add_sub = st.form_submit_button("➕ Add to Watchlist")

            if add_sub and in_ident:
                itype = "NCT" if in_ident.startswith("NCT") else "TICKER"
                db.add_to_watchlist(in_ident, itype, alias=in_alias, notes=in_notes)
                st.success(f"Added {in_ident} to Watchlist!")

    with w_col2:
        st.subheader("Pre-Configured Biotechs")
        st.caption("Quickly add high-catalyst biotechs with 1 click:")
        quick_cols = st.columns(3)
        for idx, (spons, meta) in enumerate(list(KNOWN_BIOTECH_REGISTRY.items())[:9]):
            col_target = quick_cols[idx % 3]
            if col_target.button(f"{meta['ticker']} ({meta['name'][:10]})", key=f"quick_{idx}_{meta['ticker']}"):
                db.add_to_watchlist(meta["ticker"], "TICKER", alias=meta["name"], notes=meta["focus"])
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Active Watchlist")
    watchlist = db.get_watchlist()
    if not watchlist:
        st.info("Watchlist is currently empty. Add identifiers above!")
    else:
        for item in watchlist:
            ident = item["identifier"]
            col_info, col_del = st.columns([6, 1])
            with col_info:
                st.markdown(f"### `{ident}` ({item['item_type']}) — {item.get('alias') or 'No label'}")
                if item.get("notes"):
                    st.caption(f"**Notes:** {item['notes']}")
            with col_del:
                st.write("")
                if st.button("🗑️ Remove", key=f"del_{ident}"):
                    db.remove_from_watchlist(ident)
                    st.rerun()
