import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import time
from simulation.core.engine import SimulationEngine
from simulation.utils.helpers import format_report_summary

def format_large_number(value, is_currency=False):
    prefix = "$" if is_currency else ""
    if value >= 1_000_000_000_000:
        return f"{prefix}{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.2f}M"
    else:
        return f"{prefix}{value:,.0f}"

def render_metric_card(label, value_str, diff_val, is_positive_param):
    # Determine value color based on current value/health
    val_color = "#00FFA3" # Default green
    try:
        if label == "Gini Inequality":
            gini = float(value_str)
            if gini > 0.5:
                val_color = "#FF4B4B" # Red
            elif gini > 0.38:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Unemployment":
            unemp = float(value_str.replace('%', ''))
            if unemp > 12.0:
                val_color = "#FF4B4B" # Red
            elif unemp > 6.0:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Active Infections":
            infects = int(value_str.replace(',', '').replace('M', '').replace('B', '').replace('T', ''))
            if infects > 10:
                val_color = "#FF4B4B" # Red
            elif infects > 0:
                val_color = "#FFA500" # Orange
            else:
                val_color = "#00FFA3" # Green
        elif label == "Alive Population":
            val_color = "#00FFA3"
        elif label == "Gov Treasury":
            val_color = "#00FFA3"
    except Exception:
        pass
        
    # Build delta HTML
    if diff_val is None or diff_val == 0:
        delta_html = '<div style="font-size: 0.85rem; color: #7f7f9f; font-weight: 500; margin-top: 2px;">0 (No change)</div>'
    else:
        is_good = (diff_val > 0) if is_positive_param else (diff_val < 0)
        delta_color = "#00FFA3" if is_good else "#FF4B4B"
        arrow = "▲" if diff_val > 0 else "▼"
        
        # Formatting diff text
        if label == "Alive Population":
            suffix = " Born" if diff_val > 0 else " Dead"
            diff_text = f"{arrow} {format_large_number(abs(diff_val))}{suffix}"
        elif label == "Gini Inequality":
            diff_text = f"{arrow} {abs(diff_val):.4f}"
        elif label == "Unemployment":
            diff_text = f"{arrow} {abs(diff_val):.1f}%"
        elif label == "Gov Treasury":
            diff_text = f"{arrow} {format_large_number(abs(diff_val), is_currency=True)}"
        elif label == "Active Infections":
            diff_text = f"{arrow} {format_large_number(abs(diff_val))}"
        else:
            diff_text = f"{arrow} {abs(diff_val):,.2f}"
            
        delta_html = f'<div style="font-size: 0.85rem; color: {delta_color}; font-weight: 600; display: flex; align-items: center; gap: 3px; margin-top: 2px;">{diff_text}</div>'

    html_content = f"""
    <div style="
        background: linear-gradient(135deg, rgba(30, 30, 56, 0.4) 0%, rgba(13, 13, 26, 0.4) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
        font-family: 'Outfit', sans-serif;
        min-height: 105px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    ">
        <div style="font-size: 0.8rem; color: #a0a0c0; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">{label}</div>
        <div>
            <div style="font-size: 1.8rem; font-weight: 700; color: {val_color}; line-height: 1.1; margin: 0.1rem 0;">{value_str}</div>
            {delta_html}
        </div>
    </div>
    """
    return html_content

st.set_page_config(
    page_title="Anthropolis: Socio-Demographic Digital Twin",
    page_icon="🌆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .block-container {
        padding-top: 4.0rem !important;
        padding-bottom: 1.0rem !important;
    }
    .header-container {
        background: linear-gradient(135deg, #1e1e38 0%, #0d0d1a 100%);
        padding: 0.6rem 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 5px 20px rgba(0,0,0,0.3);
        margin-top: 0rem;
        margin-bottom: 0.8rem;
    }
    .header-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(to right, #00FFA3, #00B8FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .header-subtitle { color: #b0b0d0; font-size: 0.85rem; font-weight: 300; line-height: 1.3; }
    
    /* CSS for better tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    div[data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.85rem; color: #a0a0c0 !important; font-weight: 500; text-transform: uppercase; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">Anthropolis Laboratory (India Calibration) [LIVE]</h1>
        <p class="header-subtitle">
            Socio-Demographic Digital Twin calibrated to India (2024–2026): 1 Agent ≈ 9.78M People, TFR=2.09, Median Age=28.7, GDP Per Capita=$2,813, 1 Month = 1 Tick.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.image("https://img.icons8.com/nolan/128/city.png", width=80)
st.sidebar.title("Digital Twin Setup")

with st.sidebar.expander("Population & Environment", expanded=True):
    pop_size_cr = st.slider("Population Size (Crores)", min_value=130.0, max_value=160.0, value=146.72, step=0.5)
    pop_size = int(pop_size_cr * 10000000)
    
    gov_cap_b = st.slider("Gov Treasury ($ Billions)", min_value=100.0, max_value=5000.0, value=1270.0, step=10.0)
    gov_cap = gov_cap_b * 1000000000.0

with st.sidebar.expander("Economic & Socio-Cultural Policy Levers", expanded=True):
    tax_rate = st.slider("Income Tax Rate (%)", min_value=0, max_value=40, value=5, step=1) / 100.0
    corp_tax = st.slider("Corporate Tax Rate (%)", min_value=15, max_value=35, value=22, step=1) / 100.0
    ubi_val = st.slider("Monthly UBI ($ per citizen)", min_value=0, max_value=500, value=0, step=10)
    interest_rate = st.slider("Debt Interest Rate (Annual %)", min_value=5.0, max_value=15.0, value=9.8, step=0.1) / 100.0

with st.sidebar.expander("Healthcare, Education & Food Subsidies", expanded=False):
    grocery_sub = st.slider("Grocery Subsidy (%)", min_value=0, max_value=100, value=80, step=5) / 100.0
    fast_food_tax = st.slider("Fast Food Tax (%)", min_value=0, max_value=100, value=5, step=1) / 100.0
    education_sub = st.slider("Education Subsidy (%)", min_value=0, max_value=100, value=100, step=5) / 100.0
    healthcare_sub = st.slider("Healthcare Subsidy (%)", min_value=0, max_value=100, value=40, step=5) / 100.0
    emergency_care = st.checkbox("Free Emergency Medical Care", value=True)

st.sidebar.markdown("---")
ticks_to_run = st.sidebar.slider("Months to Simulate", min_value=12, max_value=360, value=180, step=12)
tick_duration = st.sidebar.slider("1 Month Real-time duration (seconds)", min_value=1.0, max_value=30.0, value=1.0, step=1.0)

# Initialize session state variables
if "running" not in st.session_state:
    st.session_state.running = False
if "paused" not in st.session_state:
    st.session_state.paused = False
if "engine" not in st.session_state:
    st.session_state.engine = None

# Controls Layout
btn_col1, btn_col2, btn_col3 = st.sidebar.columns(3)

start_clicked = btn_col1.button("▶️ Start" if not st.session_state.running else "▶️ Resume")
pause_clicked = btn_col2.button("⏸️ Pause")
reset_clicked = btn_col3.button("🔄 Reset")

if reset_clicked:
    st.session_state.running = False
    st.session_state.paused = False
    st.session_state.engine = None
    st.rerun()

if start_clicked:
    if not st.session_state.running:
        st.session_state.running = True
        st.session_state.paused = False
        st.session_state.engine = SimulationEngine(
            population_size=pop_size,
            initial_gov_capital=gov_cap,
            seed=None, # Backend manages random seed automatically if None
        )
    else:
        st.session_state.paused = False

if pause_clicked:
    st.session_state.paused = True

if st.session_state.get("running", False) and st.session_state.engine is not None:
    from plotly.subplots import make_subplots
    engine = st.session_state.engine
    
    # Update active engine policies with current sidebar values seamlessly
    engine.policies["tax_rate"] = tax_rate
    engine.policies["corporate_tax_rate"] = corp_tax
    engine.policies["interest_rate"] = interest_rate
    engine.policies["ubi_amount"] = ubi_val
    engine.policies["grocery_subsidy"] = -grocery_sub # Backend uses negative for subsidy
    engine.policies["fast_food_tax"] = fast_food_tax
    engine.policies["education_subsidy"] = education_sub
    engine.policies["healthcare_subsidy"] = healthcare_sub
    engine.policies["free_emergency_care"] = emergency_care

    # 1. Static Layout Elements (defined ONCE to prevent DOM recreation and scroll jumping)
    progress_placeholder = st.empty()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    metric_pop_placeholder = col1.empty()
    metric_gini_placeholder = col2.empty()
    metric_unemp_placeholder = col3.empty()
    metric_gov_placeholder = col4.empty()
    metric_infect_placeholder = col5.empty()

    st.markdown("---")

    # Tabs for different sections
    tab_econ, tab_health, tab_pop, tab_env = st.tabs([
        "📊 Economics & Wealth", 
        "🏥 Health & Wellbeing", 
        "👥 Populations & Distributions", 
        "🏭 Environmental Nodes"
    ])

    # Economics tab placeholders
    with tab_econ:
        econ_m1, econ_m2, econ_m3 = st.columns(3)
        metric_inherited = econ_m1.empty()
        metric_escheated = econ_m2.empty()
        metric_informal = econ_m3.empty()
        
        econ_col1, econ_col2 = st.columns(2)
        with econ_col1:
            chart_wealth_placeholder = st.empty()
        with econ_col2:
            chart_inequality_placeholder = st.empty()
            
        chart_informal_placeholder = st.empty()

    # Health & Wellbeing tab placeholders
    with tab_health:
        health_m1 = st.columns(1)[0]
        metric_dep_ratio = health_m1.empty()

        health_col1, health_col2 = st.columns(2)
        with health_col1:
            chart_bio_placeholder = st.empty()
        with health_col2:
            chart_seir_placeholder = st.empty()
            
        health_col3, health_col4 = st.columns(2)
        with health_col3:
            chart_hospital_strain_placeholder = st.empty()
        with health_col4:
            chart_infant_mortality_placeholder = st.empty()

    # Populations & Distributions tab placeholders
    with tab_pop:
        pop_col1, pop_col2 = st.columns(2)
        with pop_col1:
            chart_pyramid_placeholder = st.empty()
            hist_wealth_placeholder = st.empty()
            hist_age_placeholder = st.empty()
        with pop_col2:
            # Metrics: Sex Ratio at Birth, current Sex Ratio
            pop_m_col1, pop_m_col2 = st.columns(2)
            metric_birth_ratio = pop_m_col1.empty()
            metric_current_ratio = pop_m_col2.empty()
            
            hist_health_placeholder = st.empty()
            hist_debt_placeholder = st.empty()

    # Environmental Nodes tab placeholders
    with tab_env:
        env_col1, env_col2 = st.columns(2)
        with env_col1:
            chart_business_cap_placeholder = st.empty()
        with env_col2:
            chart_business_staff_placeholder = st.empty()

    # Define function to update dashboard UI with current state
    def update_dashboard_ui(live_engine, target_ticks, is_final=False):
        tick = live_engine.tick_count
        history_df = live_engine.get_history_dataframe()
        latest = history_df.iloc[-1].to_dict()
        dead_count = len(live_engine.dead_citizens) * live_engine.pop_scale
        
        # Calculate active SEIR cases for display
        alive_citizens = [c for c in live_engine.citizens if not c.is_dead]
        infected_count = int(latest.get("seir_infected", 0) * live_engine.pop_scale)
        
        # Real Population Display (Alive citizens * pop_scale)
        real_pop = len(live_engine.citizens) * live_engine.pop_scale
        
        # Get previous tick for delta calculations
        if len(history_df) > 1:
            prev = history_df.iloc[-2].to_dict()
            diff_pop = (latest["population"] - prev["population"]) * live_engine.pop_scale
            diff_gini = latest["gini_coefficient"] - prev["gini_coefficient"]
            diff_unemp = (latest["unemployment_rate"] - prev["unemployment_rate"]) * 100.0
            diff_gov = (latest["government_capital"] - prev["government_capital"]) * live_engine.pop_scale
            diff_infect = int((latest.get("seir_infected", 0) - prev.get("seir_infected", 0)) * live_engine.pop_scale)
        else:
            diff_pop = None
            diff_gini = None
            diff_unemp = None
            diff_gov = None
            diff_infect = None

        # Update Metrics via custom HTML cards
        metric_pop_placeholder.markdown(render_metric_card("Alive Population", format_large_number(real_pop), diff_pop, is_positive_param=True), unsafe_allow_html=True)
        metric_gini_placeholder.markdown(render_metric_card("Gini Inequality", f"{latest['gini_coefficient']:.4f}", diff_gini, is_positive_param=False), unsafe_allow_html=True)
        metric_unemp_placeholder.markdown(render_metric_card("Unemployment", f"{latest['unemployment_rate']*100:.1f}%", diff_unemp, is_positive_param=False), unsafe_allow_html=True)
        metric_gov_placeholder.markdown(render_metric_card("Gov Treasury", format_large_number(latest['government_capital'] * live_engine.pop_scale, is_currency=True), diff_gov, is_positive_param=True), unsafe_allow_html=True)
        metric_infect_placeholder.markdown(render_metric_card("Active Infections", format_large_number(infected_count), diff_infect, is_positive_param=False), unsafe_allow_html=True)

        # Update Economics Tab Metrics & Charts
        metric_inherited.metric("Total Estate Wealth Inherited", format_large_number(latest['total_wealth_inherited'] * live_engine.pop_scale, is_currency=True), help="Total positive wealth transferred to living offspring upon deaths.")
        metric_escheated.metric("Total Estate Wealth Seized (Escheat)", format_large_number(latest['total_wealth_escheated'] * live_engine.pop_scale, is_currency=True), help="Total estate wealth seized by state treasury due to absence of offspring.")
        metric_informal.metric("Informal Sector Employment Share", f"{latest['informal_employment_share']*100:.1f}%", help="Percentage of employed citizens working in the informal/shadow economy.")
        
        plot_config = {'displayModeBar': False}

        fig_wealth = go.Figure()
        fig_wealth.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_bank_balance"], name="Avg Balance", line=dict(color="#00FFA3", width=2.5)))
        fig_wealth.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_debt"], name="Avg Debt", line=dict(color="#FF4B4B", width=2.5)))
        fig_wealth.update_layout(title="Citizen Wealth Dynamics (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_wealth_placeholder.plotly_chart(fig_wealth, width="stretch", key=f"wealth_chart_{tick}", config=plot_config)

        fig_ineq = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["gini_coefficient"], name="Gini Coefficient", line=dict(color="#FFD600", width=2.5)), secondary_y=False)
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["government_capital"] * live_engine.pop_scale, name="Gov Treasury", line=dict(color="#00B8FF", width=2, dash='dash')), secondary_y=True)
        fig_ineq.add_trace(go.Scatter(x=history_df["tick"], y=history_df["private_capital"] * live_engine.pop_scale, name="Private Capital", line=dict(color="#FF00CC", width=2, dash='dot')), secondary_y=True)
        fig_ineq.update_layout(title="Wealth Inequality & City Capital (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=40, t=40, b=40), xaxis_title="Months")
        fig_ineq.update_yaxes(title_text="Gini Coefficient", secondary_y=False)
        fig_ineq.update_yaxes(title_text="Capital ($)", secondary_y=True)
        chart_inequality_placeholder.plotly_chart(fig_ineq, width="stretch", key=f"ineq_chart_{tick}", config=plot_config)

        fig_informal = go.Figure()
        fig_informal.add_trace(go.Scatter(x=history_df["tick"], y=history_df["informal_employment_share"] * 100.0, name="Informal Share (%)", line=dict(color="#FFA500", width=2.5), fill='tozeroy'))
        fig_informal.update_layout(title="Informal / Shadow Economy Employment Share (%) (Live)", template="plotly_dark", height=300, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        fig_informal.update_yaxes(range=[0, 100])
        chart_informal_placeholder.plotly_chart(fig_informal, width="stretch", key=f"informal_chart_{tick}", config=plot_config)

        # Update Health Tab Metrics & Charts
        metric_dep_ratio.metric("Dependency Ratio", f"{latest['dependency_ratio']:.3f}", help="Dependency Ratio = (Infants + Youths + Geriatrics) / Working-Age population.")

        fig_bio = go.Figure()
        fig_bio.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_health"], name="Avg Health", line=dict(color="#00FFA3", width=2.5)))
        fig_bio.add_trace(go.Scatter(x=history_df["tick"], y=history_df["average_stress"], name="Avg Stress", line=dict(color="#FFB800", width=2.5)))
        fig_bio.update_layout(title="Biological Index: Health vs Stress (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_bio_placeholder.plotly_chart(fig_bio, width="stretch", key=f"bio_chart_{tick}", config=plot_config)

        fig_seir = go.Figure()
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_susceptible"] * live_engine.pop_scale, name="Susceptible (S)", line=dict(color="#00B8FF", width=2)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_exposed"] * live_engine.pop_scale, name="Exposed (E)", line=dict(color="#FFD600", width=2)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_infected"] * live_engine.pop_scale, name="Infected (I)", line=dict(color="#FF4B4B", width=2.5)))
        fig_seir.add_trace(go.Scatter(x=history_df["tick"], y=history_df["seir_recovered"] * live_engine.pop_scale, name="Recovered (R)", line=dict(color="#00FFA3", width=2)))
        fig_seir.update_layout(title="SEIR Epidemiological Curve (Live)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        chart_seir_placeholder.plotly_chart(fig_seir, width="stretch", key=f"seir_chart_{tick}", config=plot_config)

        fig_strain = go.Figure()
        fig_strain.add_trace(go.Scatter(x=history_df["tick"], y=history_df["hospital_strain"] * 100.0, name="Hospital Strain (%)", line=dict(color="#FF3366", width=2.5), fill='tozeroy'))
        fig_strain.update_layout(title="Healthcare System Strain (%) (Live)", template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
        fig_strain.update_yaxes(range=[0, 100])
        chart_hospital_strain_placeholder.plotly_chart(fig_strain, width="stretch", key=f"strain_chart_{tick}", config=plot_config)
        
        # Infant Mortality Graph
        fig_imr = go.Figure()
        imr_col = "infant_mortality" if "infant_mortality" in history_df.columns else "dependency_ratio" # Fallback
        if "infant_mortality" in history_df.columns:
            fig_imr.add_trace(go.Scatter(x=history_df["tick"], y=history_df["infant_mortality"], name="Infant Mortality", line=dict(color="#FF8C00", width=2.5), fill='tozeroy'))
            fig_imr.update_layout(title="Infant Mortality Rate (per 1,000 live births)", template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Months")
            chart_infant_mortality_placeholder.plotly_chart(fig_imr, width="stretch", key=f"imr_chart_{tick}", config=plot_config)

        # Update Distributions Tab
        males = [c for c in alive_citizens if c.sex == 'M']
        females = [c for c in alive_citizens if c.sex == 'F']
        born_males = sum(1 for c in live_engine.citizens if c.citizen_id >= 1000 and c.sex == 'M')
        born_females = sum(1 for c in live_engine.citizens if c.citizen_id >= 1000 and c.sex == 'F')
        
        # Sex ratios metrics
        metric_birth_ratio.metric("Sex Ratio at Birth", "929 F / 1000 M (Target)", f"Born: {int(born_males * live_engine.pop_scale):,} M / {int(born_females * live_engine.pop_scale):,} F")
        metric_current_ratio.metric("Current Sex Ratio (M/F)", f"{len(males)/len(females):.2f}" if len(females) > 0 else "N/A")

        # Demographic age-sex pyramid
        bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 120]
        labels = ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35-40", "40-45", "45-50", "50-55", "55-60", "60-65", "65-70", "70-75", "75-80", "80+"]
        
        male_counts = []
        female_counts = []
        for idx in range(len(bins)-1):
            low = bins[idx]
            high = bins[idx+1]
            m_count = sum(1 for c in males if low <= c.age < high)
            f_count = sum(1 for c in females if low <= c.age < high)
            male_counts.append(-m_count * live_engine.pop_scale)
            female_counts.append(f_count * live_engine.pop_scale)
            
        fig_pyr = go.Figure()
        fig_pyr.add_trace(go.Bar(y=labels, x=male_counts, name="Male", orientation='h', marker_color='#00B8FF'))
        fig_pyr.add_trace(go.Bar(y=labels, x=female_counts, name="Female", orientation='h', marker_color='#FF00CC'))
        
        max_abs = int(max(max(abs(x) for x in male_counts) if male_counts else 1, max(female_counts) if female_counts else 1))
        tick_vals = list(range(-max_abs, max_abs + 1, max(1, max_abs // 4)))
        tick_text = [f"{int(abs(v)):,}" for v in tick_vals]
        
        fig_pyr.update_layout(
            title="Demographic Age-Sex Pyramid (Current)",
            barmode='relative',
            template="plotly_dark",
            height=350,
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis=dict(
                tickvals=tick_vals,
                ticktext=tick_text,
                title="Population Count"
            ),
            yaxis=dict(title="Age Cohort")
        )
        chart_pyramid_placeholder.plotly_chart(fig_pyr, width="stretch", key=f"pyramid_chart_{tick}", config=plot_config)

        if alive_citizens:
            healths = [c.health for c in alive_citizens]
            balances = [c.bank_balance for c in alive_citizens]
            debts = [c.debt for c in alive_citizens]

            fig_hist_health = px.histogram(x=healths, nbins=15, title="Health Status Distribution (Current)", color_discrete_sequence=["#00FFA3"])
            fig_hist_health.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Health (0 - 70.8)", yaxis_title="Count")
            hist_health_placeholder.plotly_chart(fig_hist_health, width="stretch", key=f"hist_health_{tick}", config=plot_config)

            fig_hist_wealth = px.histogram(x=balances, nbins=15, title="Bank Balance Distribution (Current)", color_discrete_sequence=["#FF00CC"])
            fig_hist_wealth.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Balance ($)", yaxis_title="Count")
            hist_wealth_placeholder.plotly_chart(fig_hist_wealth, width="stretch", key=f"hist_wealth_{tick}", config=plot_config)

            fig_hist_debt = px.histogram(x=debts, nbins=15, title="Debt Distribution (Current)", color_discrete_sequence=["#FF4B4B"])
            fig_hist_debt.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Debt ($)", yaxis_title="Count")
            hist_debt_placeholder.plotly_chart(fig_hist_debt, width="stretch", key=f"hist_debt_{tick}", config=plot_config)

            # Update age distribution histogram
            ages = [c.age for c in alive_citizens]
            fig_hist_age = px.histogram(x=ages, nbins=15, title="Age Distribution (Current)", color_discrete_sequence=["#00B8FF"])
            fig_hist_age.update_layout(template="plotly_dark", height=250, margin=dict(l=40, r=20, t=40, b=40), xaxis_title="Age (Years)", yaxis_title="Count")
            hist_age_placeholder.plotly_chart(fig_hist_age, width="stretch", key=f"hist_age_{tick}", config=plot_config)

        # Update Environmental Nodes only if final to prevent auto-refreshing during live stream
        if is_final:
            node_names = [n.node_name for n in live_engine.nodes]
            node_capitals = [n.capital for n in live_engine.nodes]
            node_employees = [len(n.employees) for n in live_engine.nodes]
            node_capacities = [n.employee_capacity for n in live_engine.nodes]

            fig_bus_cap = go.Figure(data=[
                go.Bar(x=node_names, y=node_capitals, marker_color="#00FFA3", text=[format_large_number(v, is_currency=True) for v in node_capitals], textposition='auto')
            ])
            fig_bus_cap.update_layout(title="Node Financial Capitals (Final State)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_tickangle=-45)
            chart_business_cap_placeholder.plotly_chart(fig_bus_cap, width="stretch", key=f"bus_cap_chart_{tick}", config=plot_config)

            fig_bus_staff = go.Figure(data=[
                go.Bar(name='Current Employees', x=node_names, y=node_employees, marker_color="#00B8FF"),
                go.Bar(name='Max Staff Capacity', x=node_names, y=node_capacities, marker_color="#555555")
            ])
            fig_bus_staff.update_layout(barmode='group', title="Node Employee Staffing Levels (Final State)", template="plotly_dark", height=350, margin=dict(l=40, r=20, t=40, b=40), xaxis_tickangle=-45)
            chart_business_staff_placeholder.plotly_chart(fig_bus_staff, width="stretch", key=f"bus_staff_chart_{tick}", config=plot_config)

    remaining_ticks = ticks_to_run - engine.tick_count
    
    if remaining_ticks > 0 and not st.session_state.paused:
        # Continuous stream loop: Updates placeholders in-place without redrawing full page
        for live_engine in engine.run_generator(remaining_ticks):
            tick = live_engine.tick_count
            progress_placeholder.progress(tick / ticks_to_run, text=f"Streaming Month {tick}/{ticks_to_run}...")
            update_dashboard_ui(live_engine, ticks_to_run, is_final=False)
            time.sleep(tick_duration)
            
    elif st.session_state.paused:
        progress_placeholder.warning(f"Simulation PAUSED at Month {engine.tick_count}/{ticks_to_run}.")
        update_dashboard_ui(engine, ticks_to_run, is_final=True)
    else:
        progress_placeholder.success("Simulation Complete! Viewing final state.")
        update_dashboard_ui(engine, ticks_to_run, is_final=True)
else:
    st.info("👈 Configure policies and click **▶️ Start** to watch the socio-demographic interactions unfold.")
