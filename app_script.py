from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


# ======================================================
# PAGE CONFIG
# ======================================================

st.set_page_config(
    page_title="Investment Decision Dashboard",
    page_icon="◫",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ======================================================
# DESIGN TOKENS
# ======================================================

THEME = {
    "bg": "#F5F7FB",
    "bg_top": "#FBFCFE",
    "surface": "#FFFFFF",
    "surface_soft": "#FAFBFD",
    "surface_alt": "#F3F6FA",
    "surface_tint": "#F7FAFF",
    "text": "#0F172A",
    "text_soft": "#334155",
    "text_muted": "#64748B",
    "border": "#E2E8F0",
    "border_soft": "#EDF2F7",
    "grid": "#E9EEF5",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_soft": "#DBEAFE",
    "accent": "#7C3AED",
    "success": "#0F9F6E",
    "warning": "#B7791F",
    "danger": "#D14343",
    "shadow_sm": "0 1px 2px rgba(15, 23, 42, 0.04)",
    "shadow_md": "0 10px 30px rgba(15, 23, 42, 0.06)",
    "shadow_lg": "0 18px 48px rgba(15, 23, 42, 0.08)",
    "radius_sm": "16px",
    "radius_md": "20px",
    "radius_lg": "24px",
    "chart_main": "#2563EB",
    "chart_main_soft": "#C7DBFF",
    "chart_alt": "#7C3AED",
    "chart_neutral": "#94A3B8",
    "chart_loss": "#F97316",
    "chart_loss_soft": "#FED7AA",
}


# ======================================================
# DATA MODELS
# ======================================================

@dataclass(frozen=True)
class SimulationInputs:
    initial_capital: float
    monthly_contribution: float
    annual_return: float
    duration_years: int
    exit_year: int
    exit_penalty_pct: float
    exit_extra_cost: float
    alternative_return: float
    uncertainty_level: str
    n_simulations: int


@dataclass(frozen=True)
class ExitMetrics:
    final_value_stay: float
    exit_value_gross: float
    contributed_until_exit: float
    exit_penalty_eur: float
    final_value_alternative: float
    opportunity_cost_abs: float
    opportunity_cost_pct: float
    remaining_years: int


@dataclass(frozen=True)
class CompoundingMetrics:
    exit_value_gross: float
    contributed_until_exit: float
    exit_penalty_eur: float
    available_net_capital: float
    final_value_stay: float
    lost_compounding_abs: float
    lost_compounding_pct: float


@dataclass(frozen=True)
class MonteCarloMetrics:
    probability_stay_better: float
    expected_cost_mc: float
    stay_mean: float
    exit_mean: float
    used_volatility_pct: float


# ======================================================
# FORMATTERS
# ======================================================

def format_eur(value: float) -> str:
    formatted = f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} EUR"


def format_pct(value: float) -> str:
    return f"{value:.1f}%"


def format_pct_signed(value: float) -> str:
    return f"{value:+.1f}%"


def delta_class(value: float, positive_is_good: bool = True) -> str:
    if abs(value) < 1e-12:
        return "delta-neutral"
    is_positive = value > 0
    good = is_positive if positive_is_good else not is_positive
    return "delta-positive" if good else "delta-negative"


def outcome_class(value: float) -> str:
    if value > 0:
        return "state-positive"
    if value < 0:
        return "state-negative"
    return "state-neutral"


# ======================================================
# STYLE
# ======================================================

def apply_theme() -> None:
    st.markdown(
        dedent(
            f"""
<style>
:root {{
    --bg: {THEME["bg"]};
    --bg-top: {THEME["bg_top"]};
    --surface: {THEME["surface"]};
    --surface-soft: {THEME["surface_soft"]};
    --surface-alt: {THEME["surface_alt"]};
    --surface-tint: {THEME["surface_tint"]};
    --text: {THEME["text"]};
    --text-soft: {THEME["text_soft"]};
    --text-muted: {THEME["text_muted"]};
    --border: {THEME["border"]};
    --border-soft: {THEME["border_soft"]};
    --grid: {THEME["grid"]};
    --primary: {THEME["primary"]};
    --primary-dark: {THEME["primary_dark"]};
    --primary-soft: {THEME["primary_soft"]};
    --accent: {THEME["accent"]};
    --success: {THEME["success"]};
    --warning: {THEME["warning"]};
    --danger: {THEME["danger"]};
    --shadow-sm: {THEME["shadow_sm"]};
    --shadow-md: {THEME["shadow_md"]};
    --shadow-lg: {THEME["shadow_lg"]};
    --radius-sm: {THEME["radius_sm"]};
    --radius-md: {THEME["radius_md"]};
    --radius-lg: {THEME["radius_lg"]};
}}

.stApp {{
    background:
        radial-gradient(circle at top left, rgba(37,99,235,0.06), transparent 28%),
        linear-gradient(180deg, var(--bg-top) 0%, var(--bg) 40%, var(--bg) 100%);
    color: var(--text);
}}

.block-container {{
    max-width: 1320px;
    padding-top: 1.35rem;
    padding-bottom: 3.4rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
}}

h1, h2, h3, h4 {{
    letter-spacing: -0.03em;
}}

[data-testid="stSidebar"] {{
    background: rgba(255,255,255,0.82);
    border-right: 1px solid var(--border-soft);
    backdrop-filter: blur(18px);
}}

[data-testid="stSidebar"] .block-container {{
    padding-top: 1.1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}}

.app-stack {{
    display: flex;
    flex-direction: column;
    gap: 1.8rem;
}}

.hero {{
    background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(255,255,255,0.91) 100%);
    border: 1px solid rgba(226, 232, 240, 0.9);
    box-shadow: var(--shadow-lg);
    border-radius: var(--radius-lg);
    padding: 1.2rem 1.35rem 1.2rem 1.35rem;
}}

.hero-topline {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.38rem 0.7rem;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.08);
    border: 1px solid rgba(37, 99, 235, 0.12);
    color: var(--primary-dark);
    font-size: 0.76rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.9rem;
}}

.hero-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.9fr);
    gap: 1rem;
    align-items: stretch;
}}

.hero-title {{
    margin: 0 0 0.5rem 0;
    font-size: 2.35rem;
    line-height: 1.02;
    font-weight: 850;
    color: var(--text);
}}

.hero-subtitle {{
    margin: 0;
    max-width: 880px;
    font-size: 0.99rem;
    line-height: 1.7;
    color: var(--text-soft);
}}

.hero-side {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 1rem 1rem 0.95rem 1rem;
}}

.mini-kicker {{
    color: var(--text-muted);
    font-size: 0.74rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.35rem;
}}

.mini-title {{
    color: var(--text);
    font-size: 1.05rem;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 0.45rem;
}}

.mini-copy {{
    color: var(--text-soft);
    font-size: 0.9rem;
    line-height: 1.6;
}}

.decision-banner {{
    display: flex;
    align-items: flex-start;
    gap: 0.8rem;
    margin-top: 1rem;
    padding: 0.95rem 1rem;
    border-radius: 18px;
    border: 1px solid var(--border-soft);
    background: linear-gradient(180deg, rgba(248,250,252,0.95) 0%, rgba(255,255,255,0.95) 100%);
}}

.decision-dot {{
    width: 12px;
    height: 12px;
    border-radius: 999px;
    margin-top: 0.26rem;
    flex: 0 0 12px;
}}

.state-positive .decision-dot {{
    background: var(--success);
    box-shadow: 0 0 0 6px rgba(15, 159, 110, 0.10);
}}

.state-negative .decision-dot {{
    background: var(--danger);
    box-shadow: 0 0 0 6px rgba(209, 67, 67, 0.10);
}}

.state-neutral .decision-dot {{
    background: var(--warning);
    box-shadow: 0 0 0 6px rgba(183, 121, 31, 0.10);
}}

.decision-title {{
    color: var(--text);
    font-size: 0.95rem;
    font-weight: 800;
    margin-bottom: 0.22rem;
}}

.decision-copy {{
    color: var(--text-soft);
    font-size: 0.92rem;
    line-height: 1.6;
}}

/* IMPORTANTE: neutralizza i wrapper vuoti */
.panel-content {{
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}}

/* Header di sezione più elegante e leggero */
.panel-head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1.25rem;
    padding-top: 0.1rem;
}}

.panel-kicker {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.28rem;
}}

.panel-title {{
    margin: 0 0 0.2rem 0;
    color: var(--text);
    font-size: 1.16rem;
    line-height: 1.15;
    font-weight: 850;
}}

.panel-note {{
    margin: 0;
    color: var(--text-soft);
    font-size: 0.92rem;
    line-height: 1.6;
    max-width: 900px;
}}

.metric-card {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F9FBFF 100%);
    border: 1px solid rgba(226,232,240,0.85);
    border-radius: 18px;
    padding: 1rem 1.1rem;
    box-shadow: 0 2px 6px rgba(15,23,42,0.04);
    min-height: 150px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    transition:
        transform 0.18s ease,
        box-shadow 0.18s ease,
        border-color 0.18s ease,
        background 0.18s ease;
}}

.metric-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 10px 26px rgba(15,23,42,0.10);
    border-color: rgba(148,163,184,0.45);
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F8FF 100%);
}}

.metric-card.emphasis {{
    background: linear-gradient(180deg, #F7FAFF 0%, #FFFFFF 100%);
    border: 1px solid rgba(37,99,235,0.18);
    box-shadow: 0 6px 18px rgba(37,99,235,0.08);
}}

.metric-card.emphasis:hover {{
    box-shadow: 0 12px 28px rgba(37,99,235,0.16);
}}

.metric-label {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}}

.metric-value {{
    color: var(--text);
    font-size: 2rem;
    line-height: 1.02;
    font-weight: 860;
    letter-spacing: -0.05em;
    margin-bottom: 0.45rem;
}}

.metric-help {{
    color: var(--text-soft);
    font-size: 0.86rem;
    line-height: 1.6;
    margin-top: auto;
}}


.metric-delta {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    font-size: 0.72rem;
    font-weight: 850;
    margin-bottom: 0.65rem;
}}

.delta-neutral {{
    background: #F1F5F9;
    color: #334155;
}}

.delta-positive {{
    background: rgba(15,159,110,0.10);
    color: var(--success);
}}

.delta-negative {{
    background: rgba(209,67,67,0.10);
    color: var(--danger);
}}

.metric-help {{
    color: var(--text-soft);
    font-size: 0.87rem;
    line-height: 1.52;
}}

.metric-card pre,
.metric-card code {{
    display: none !important;
}}

.insight-card {{
    background: linear-gradient(180deg, rgba(248,250,255,1) 0%, rgba(255,255,255,1) 100%);
    border: 1px solid rgba(37, 99, 235, 0.12);
    border-radius: 18px;
    padding: 1rem;
}}

.insight-title {{
    color: var(--text-muted);
    font-size: 0.76rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.42rem;
}}

.insight-value {{
    color: var(--text);
    font-size: 1.95rem;
    line-height: 1.05;
    font-weight: 850;
    letter-spacing: -0.04em;
    margin-bottom: 0.35rem;
}}

.insight-copy {{
    color: var(--text-soft);
    font-size: 0.9rem;
    line-height: 1.58;
}}

.legend-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid var(--border-soft);
}}

.legend-row:last-child {{
    border-bottom: none;
}}

.legend-left {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    color: var(--text);
    font-size: 0.92rem;
}}

.legend-dot {{
    width: 11px;
    height: 11px;
    border-radius: 50%;
    display: inline-block;
    flex: 0 0 11px;
}}

.legend-value {{
    color: var(--text);
    font-size: 0.92rem;
    font-weight: 800;
    text-align: right;
}}

.divider {{
    height: 1px;
    background: var(--border-soft);
    margin: 1rem 0;
}}

.subtle-note {{
    color: var(--text-muted);
    font-size: 0.83rem;
    line-height: 1.55;
}}

.sidebar-shell {{
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border-soft);
    margin-bottom: 1rem;
}}

.sidebar-kicker {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.32rem;
}}

.sidebar-title {{
    color: var(--text);
    font-size: 1.16rem;
    line-height: 1.16;
    font-weight: 850;
    margin-bottom: 0.4rem;
}}

.sidebar-copy {{
    color: var(--text-soft);
    font-size: 0.89rem;
    line-height: 1.55;
}}

.sidebar-group {{
    margin-top: 0.85rem;
}}

.sidebar-group-title {{
    color: var(--text);
    font-size: 0.92rem;
    font-weight: 800;
    margin: 1rem 0 0.22rem 0;
}}

.sidebar-group-note {{
    color: var(--text-muted);
    font-size: 0.82rem;
    line-height: 1.5;
    margin-bottom: 0.55rem;
}}

label[data-testid="stWidgetLabel"] p {{
    color: var(--text-soft);
    font-size: 0.88rem;
    font-weight: 650;
}}

div[data-testid="stNumberInput"] {{
    background: transparent !important;
}}

div[data-testid="stNumberInput"] div[data-baseweb="input"] {{
    border-radius: 14px !important;
    border: 1px solid var(--border) !important;
    background: #FFFFFF !important;
    min-height: 46px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}}

div[data-testid="stNumberInput"] input {{
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
    opacity: 1 !important;
    background: #FFFFFF !important;
    caret-color: var(--text) !important;
    font-weight: 600 !important;
}}

div[data-testid="stNumberInput"] input:focus {{
    background: #FFFFFF !important;
    outline: none !important;
}}

div[data-testid="stNumberInput"] input::placeholder {{
    color: var(--text-muted) !important;
    opacity: 1 !important;
}}

div[data-testid="stNumberInput"] button {{
    background: #F8FAFC !important;
    color: var(--text) !important;
    border-left: 1px solid var(--border-soft) !important;
    border-radius: 0 !important;
    min-height: 46px !important;
    box-shadow: none !important;
}}

div[data-testid="stNumberInput"] button:hover {{
    background: #EEF2F7 !important;
    color: var(--text) !important;
}}

input, textarea {{
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}}

.stSlider [data-baseweb="slider"] {{
    padding-top: 0.3rem;
    padding-bottom: 0.2rem;
}}

.stSlider [role="slider"] {{
    box-shadow: 0 0 0 6px rgba(37,99,235,0.08);
}}

.stButton button,
.stFormSubmitButton button {{
    border-radius: 14px !important;
    border: none !important;
    min-height: 46px;
    font-weight: 800 !important;
    color: white !important;
    background: linear-gradient(180deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
    box-shadow: 0 10px 24px rgba(37,99,235,0.18);
}}

div[data-testid="stDataFrame"] {{
    background: #FFFFFF !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 16px !important;
    overflow: hidden;
}}

div[data-testid="stDataFrame"] * {{
    color: #111827 !important;
}}

div[data-testid="stDataFrame"] [role="grid"] {{
    background: #FFFFFF !important;
}}

div[data-testid="stDataFrame"] [role="columnheader"] {{
    background: #F8FAFC !important;
    color: #475467 !important;
}}

div[data-testid="stDataFrame"] [role="gridcell"] {{
    background: #FFFFFF !important;
    color: #111827 !important;
}}

.tight-gap {{
    height: 0.25rem;
}}

@media (max-width: 1200px) {{
    .hero-grid {{
        grid-template-columns: 1fr;
    }}

    .hero-title {{
        font-size: 2rem;
    }}
}}
</style>
"""
        ).strip(),
        unsafe_allow_html=True,
    )
# ======================================================
# DOMAIN LOGIC
# ======================================================

@st.cache_data(show_spinner=False)
def calculate_plan(
    initial_capital: float,
    monthly_contribution: float,
    annual_return: float,
    duration_years: int,
) -> pd.DataFrame:
    total_months = duration_years * 12
    monthly_return = (1 + annual_return) ** (1 / 12) - 1

    balances = np.empty(total_months + 1, dtype=np.float64)
    balances[0] = initial_capital

    balance = float(initial_capital)
    for month in range(1, total_months + 1):
        balance = balance * (1 + monthly_return) + monthly_contribution
        balances[month] = balance

    years = np.arange(0, duration_years + 1)
    month_index = years * 12

    total_contributed = initial_capital + monthly_contribution * 12 * years
    total_value = balances[month_index]

    return pd.DataFrame(
        {
            "Year": years,
            "Total Contributed": np.round(total_contributed, 2),
            "Total Value": np.round(total_value, 2),
        }
    )


def contributed_until_exit(
    initial_capital: float,
    monthly_contribution: float,
    exit_year: int,
) -> float:
    return float(initial_capital + monthly_contribution * 12 * exit_year)


def alternative_final_value(
    exit_value_gross: float,
    remaining_years: int,
    exit_penalty_eur: float,
    exit_extra_cost: float,
    alternative_return: float,
) -> float:
    net_capital = max(exit_value_gross - exit_penalty_eur - exit_extra_cost, 0.0)
    return net_capital * ((1 + alternative_return) ** remaining_years)


@st.cache_data(show_spinner=False)
def calculate_exit_metrics(
    base_df: pd.DataFrame,
    initial_capital: float,
    monthly_contribution: float,
    exit_year: int,
    duration_years: int,
    exit_penalty_pct: float,
    exit_extra_cost: float,
    alternative_return: float,
) -> ExitMetrics:
    final_value_stay = float(base_df.iloc[-1]["Total Value"])
    exit_value_gross = float(base_df.iloc[exit_year]["Total Value"])
    remaining_years = max(duration_years - exit_year, 0)

    contributed = contributed_until_exit(
        initial_capital=initial_capital,
        monthly_contribution=monthly_contribution,
        exit_year=exit_year,
    )
    exit_penalty_eur = contributed * exit_penalty_pct

    final_value_alternative = alternative_final_value(
        exit_value_gross=exit_value_gross,
        remaining_years=remaining_years,
        exit_penalty_eur=exit_penalty_eur,
        exit_extra_cost=exit_extra_cost,
        alternative_return=alternative_return,
    )

    opportunity_cost_abs = final_value_stay - final_value_alternative
    opportunity_cost_pct = (
        100 * opportunity_cost_abs / final_value_stay if final_value_stay > 0 else 0.0
    )

    return ExitMetrics(
        final_value_stay=round(final_value_stay, 2),
        exit_value_gross=round(exit_value_gross, 2),
        contributed_until_exit=round(contributed, 2),
        exit_penalty_eur=round(exit_penalty_eur, 2),
        final_value_alternative=round(final_value_alternative, 2),
        opportunity_cost_abs=round(opportunity_cost_abs, 2),
        opportunity_cost_pct=round(opportunity_cost_pct, 2),
        remaining_years=remaining_years,
    )


@st.cache_data(show_spinner=False)
def calculate_compounding_metrics(
    base_df: pd.DataFrame,
    initial_capital: float,
    monthly_contribution: float,
    exit_year: int,
    exit_penalty_pct: float,
    exit_extra_cost: float,
) -> CompoundingMetrics:
    final_value_stay = float(base_df.iloc[-1]["Total Value"])
    exit_value_gross = float(base_df.iloc[exit_year]["Total Value"])

    contributed = contributed_until_exit(
        initial_capital=initial_capital,
        monthly_contribution=monthly_contribution,
        exit_year=exit_year,
    )
    exit_penalty_eur = contributed * exit_penalty_pct
    available_net_capital = max(exit_value_gross - exit_penalty_eur - exit_extra_cost, 0.0)

    lost_compounding_abs = final_value_stay - available_net_capital
    lost_compounding_pct = (
        100 * lost_compounding_abs / final_value_stay if final_value_stay > 0 else 0.0
    )

    return CompoundingMetrics(
        exit_value_gross=round(exit_value_gross, 2),
        contributed_until_exit=round(contributed, 2),
        exit_penalty_eur=round(exit_penalty_eur, 2),
        available_net_capital=round(available_net_capital, 2),
        final_value_stay=round(final_value_stay, 2),
        lost_compounding_abs=round(lost_compounding_abs, 2),
        lost_compounding_pct=round(lost_compounding_pct, 2),
    )


@st.cache_data(show_spinner=False)
def simulate_probability_stay_better(
    initial_capital: float,
    monthly_contribution: float,
    expected_return: float,
    duration_years: int,
    exit_year: int,
    exit_penalty_pct: float,
    exit_extra_cost: float,
    alternative_return: float,
    uncertainty_level: str = "Media",
    n_simulations: int = 3000,
    seed: int = 42,
) -> MonteCarloMetrics:
    rng = np.random.default_rng(seed)

    volatility_map = {
        "Bassa": 0.08,
        "Media": 0.12,
        "Alta": 0.18,
    }

    annual_volatility = volatility_map.get(uncertainty_level, 0.12)
    alternative_annual_volatility = 0.02

    total_months = duration_years * 12
    exit_months = exit_year * 12
    remaining_months = max(total_months - exit_months, 0)

    mu_main = expected_return / 12
    sigma_main = annual_volatility / np.sqrt(12)

    mu_alt = alternative_return / 12
    sigma_alt = alternative_annual_volatility / np.sqrt(12)

    contributed = contributed_until_exit(
        initial_capital=initial_capital,
        monthly_contribution=monthly_contribution,
        exit_year=exit_year,
    )
    exit_penalty_eur = contributed * exit_penalty_pct

    main_returns = rng.normal(mu_main, sigma_main, size=(n_simulations, total_months))

    stay_path = np.full(n_simulations, initial_capital, dtype=np.float64)
    for month in range(total_months):
        stay_path = (stay_path + monthly_contribution) * (1.0 + main_returns[:, month])

    exit_path = np.full(n_simulations, initial_capital, dtype=np.float64)
    for month in range(exit_months):
        exit_path = (exit_path + monthly_contribution) * (1.0 + main_returns[:, month])

    exit_net_capital = np.maximum(
        exit_path - exit_penalty_eur - exit_extra_cost,
        0.0,
    )

    if remaining_months > 0:
        alt_returns = rng.normal(mu_alt, sigma_alt, size=(n_simulations, remaining_months))
        alt_path = exit_net_capital.copy()
        for month in range(remaining_months):
            alt_path *= (1.0 + alt_returns[:, month])
    else:
        alt_path = exit_net_capital

    probability = float(np.mean(stay_path > alt_path)) * 100
    expected_cost = float(np.mean(stay_path - alt_path))

    return MonteCarloMetrics(
        probability_stay_better=round(probability, 1),
        expected_cost_mc=round(expected_cost, 2),
        stay_mean=round(float(np.mean(stay_path)), 2),
        exit_mean=round(float(np.mean(alt_path)), 2),
        used_volatility_pct=round(annual_volatility * 100, 1),
    )


@st.cache_data(show_spinner=False)
def build_compounding_table(
    base_df: pd.DataFrame,
    initial_capital: float,
    monthly_contribution: float,
    duration_years: int,
    exit_penalty_pct: float,
    exit_extra_cost: float,
) -> pd.DataFrame:
    final_value_stay = float(base_df.iloc[-1]["Total Value"])
    years = np.arange(0, duration_years)

    if len(years) == 0:
        return pd.DataFrame(
            columns=[
                "Exit Year",
                "Exit Value Gross",
                "Contributed Capital",
                "Exit Penalty EUR",
                "Available Net Capital",
                "Lost Compounding EUR",
                "Lost Compounding %",
            ]
        )

    exit_values = base_df.iloc[years]["Total Value"].to_numpy(dtype=np.float64)
    contributed_values = initial_capital + monthly_contribution * 12 * years
    penalties = contributed_values * exit_penalty_pct
    net_capital = np.maximum(exit_values - penalties - exit_extra_cost, 0.0)

    lost_compounding = final_value_stay - net_capital
    lost_compounding_pct = np.where(
        final_value_stay > 0,
        100 * lost_compounding / final_value_stay,
        0.0,
    )

    return pd.DataFrame(
        {
            "Exit Year": years,
            "Exit Value Gross": np.round(exit_values, 2),
            "Contributed Capital": np.round(contributed_values, 2),
            "Exit Penalty EUR": np.round(penalties, 2),
            "Available Net Capital": np.round(net_capital, 2),
            "Lost Compounding EUR": np.round(lost_compounding, 2),
            "Lost Compounding %": np.round(lost_compounding_pct, 2),
        }
    )


# ======================================================
# CHARTS
# ======================================================

def chart_theme() -> dict:
    return {
        "config": {
            "axis": {
                "labelColor": THEME["text_muted"],
                "titleColor": THEME["text_soft"],
                "gridColor": THEME["grid"],
                "domain": False,
                "tickColor": "transparent",
                "labelFontSize": 12,
                "titleFontSize": 12,
                "labelPadding": 10,
            },
            "legend": {
                "labelColor": THEME["text_soft"],
                "titleColor": THEME["text"],
            },
            "view": {"stroke": None},
        }
    }


def create_growth_chart(df: pd.DataFrame) -> alt.Chart:
    chart_df = df.copy()
    chart_df["Cumulative Gain"] = chart_df["Total Value"] - chart_df["Total Contributed"]

    tooltip = [
        alt.Tooltip("Year:Q", title="Anno"),
        alt.Tooltip("Total Value:Q", title="Valore totale", format=",.0f"),
        alt.Tooltip("Total Contributed:Q", title="Capitale versato", format=",.0f"),
        alt.Tooltip("Cumulative Gain:Q", title="Crescita cumulata", format=",.0f"),
    ]

    base = alt.Chart(chart_df).encode(
        x=alt.X("Year:Q", title=None, axis=alt.Axis(grid=False, tickCount=min(10, len(chart_df))))
    )

    area = base.mark_area(
        line={"color": THEME["chart_main"], "strokeWidth": 2.5},
        opacity=0.22,
        color=THEME["chart_main"],
    ).encode(
        y=alt.Y("Total Value:Q", title=None, axis=alt.Axis(format="~s")),
        tooltip=tooltip,
    )

    contribution_line = base.mark_line(
        color=THEME["chart_neutral"],
        strokeWidth=2,
        strokeDash=[5, 5],
        interpolate="monotone"
    ).encode(
        y="Total Contributed:Q"
    )

    points = base.mark_circle(
        size=60,
        color=THEME["chart_main"],
        opacity=0.95,
    ).encode(
        y="Total Value:Q",
        tooltip=tooltip,
    )

    last_point = alt.Chart(chart_df.tail(1)).mark_circle(
        size=130,
        color=THEME["chart_main"],
    ).encode(
        x="Year:Q",
        y="Total Value:Q",
        tooltip=tooltip,
    )

    return (area + contribution_line + points + last_point).properties(height=340).configure(
        **chart_theme()["config"]
    )


def create_scenario_comparison_chart(stay_value: float, alternative_value: float) -> alt.Chart:
    comp_df = pd.DataFrame(
        {
            "Scenario": ["Restare investito", "Uscire e reinvestire"],
            "Value": [stay_value, alternative_value],
            "Color": [THEME["chart_main"], THEME["chart_alt"]],
        }
    )

    bars = alt.Chart(comp_df).mark_bar(
        cornerRadiusTopLeft=10,
        cornerRadiusTopRight=10,
        width=92,
    ).encode(
        x=alt.X("Scenario:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Value:Q", title=None, axis=alt.Axis(format="~s")),
        color=alt.Color("Color:N", scale=None, legend=None),
        tooltip=[
            alt.Tooltip("Scenario:N", title="Scenario"),
            alt.Tooltip("Value:Q", title="Valore finale", format=",.0f"),
        ],
    )

    labels = alt.Chart(comp_df).mark_text(
        dy=-12,
        fontSize=12,
        fontWeight="bold",
        color=THEME["text"],
    ).encode(
        x="Scenario:N",
        y="Value:Q",
        text=alt.Text("Value:Q", format=",.0f"),
    )

    return (bars + labels).properties(height=310).configure(**chart_theme()["config"])


def create_lost_compounding_chart(df_compounding: pd.DataFrame, selected_exit_year: int) -> alt.Chart:
    chart_df = df_compounding.copy()
    chart_df["Selection"] = np.where(
        chart_df["Exit Year"] == selected_exit_year,
        "Selected",
        "Other",
    )

    tooltip = [
        alt.Tooltip("Exit Year:Q", title="Anno uscita"),
        alt.Tooltip("Available Net Capital:Q", title="Capitale netto disponibile", format=",.0f"),
        alt.Tooltip("Lost Compounding EUR:Q", title="Compounding perso", format=",.0f"),
        alt.Tooltip("Lost Compounding %:Q", title="% valore finale", format=".2f"),
    ]

    base = alt.Chart(chart_df).encode(
        x=alt.X("Exit Year:O", title="Anno di uscita", axis=alt.Axis(labelAngle=0))
    )

    bars = base.mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8,
        opacity=0.9,
    ).encode(
        y=alt.Y("Lost Compounding EUR:Q", title="Crescita composta persa", axis=alt.Axis(format="~s")),
        color=alt.condition(
            alt.datum.Selection == "Selected",
            alt.value(THEME["primary_dark"]),
            alt.value(THEME["chart_main_soft"]),
        ),
        tooltip=tooltip,
    )

    trend_line = base.mark_line(
        color=THEME["chart_main"],
        strokeWidth=2.2,
    ).encode(
        y="Lost Compounding EUR:Q"
    )

    selected_point = alt.Chart(
        chart_df[chart_df["Exit Year"] == selected_exit_year]
    ).mark_circle(
        size=170,
        color=THEME["danger"],
    ).encode(
        x="Exit Year:O",
        y="Lost Compounding EUR:Q",
        tooltip=tooltip,
    )

    return (bars + trend_line + selected_point).properties(height=320).configure(
        **chart_theme()["config"]
    )


# ======================================================
# UI HELPERS
# ======================================================

def open_panel() -> None:
    st.markdown('<div class="panel-shell">', unsafe_allow_html=True)

def close_panel() -> None:
    st.markdown('</div>', unsafe_allow_html=True)

def render_panel_header(kicker: str, title: str, note: str) -> None:
    html = dedent(
        f"""
        <div class="panel-head">
            <div>
                <div class="panel-kicker">{kicker}</div>
                <div class="panel-title">{title}</div>
                <p class="panel-note">{note}</p>
            </div>
        </div>
        """
    ).strip()
    st.markdown(html, unsafe_allow_html=True)


def section_header(kicker: str, title: str, note: str) -> None:
    html = dedent(
        f"""
        <div class="panel-head">
            <div>
                <div class="panel-kicker">{kicker}</div>
                <div class="panel-title">{title}</div>
                <p class="panel-note">{note}</p>
            </div>
        </div>
        """
    ).strip()
    st.markdown(html, unsafe_allow_html=True)


def render_metric_card(
    label: str,
    value: str,
    help_text: str,
    delta_text: str | None = None,
    delta_css: str = "delta-neutral",
    emphasis: bool = False,
) -> None:
    emphasis_class = " emphasis" if emphasis else ""

    delta_html = ""
    if delta_text is not None:
        delta_html = f'<div class="metric-delta {delta_css}">{delta_text}</div>'

    html = (
        f'<div class="metric-card{emphasis_class}">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'{delta_html}'
        f'<div class="metric-help">{help_text}</div>'
        f'</div>'
    )

    st.markdown(html, unsafe_allow_html=True)


def render_insight_card(title: str, value: str, copy: str) -> None:
    html = dedent(
        f"""
        <div class="insight-card">
            <div class="insight-title">{title}</div>
            <div class="insight-value">{value}</div>
            <div class="insight-copy">{copy}</div>
        </div>
        """
    ).strip()
    st.markdown(html, unsafe_allow_html=True)


def render_legend_item(label: str, value: str, color: str) -> None:
    html = dedent(
        f"""
        <div class="legend-row">
            <div class="legend-left">
                <span class="legend-dot" style="background:{color};"></span>
                <span>{label}</span>
            </div>
            <div class="legend-value">{value}</div>
        </div>
        """
    ).strip()
    st.markdown(html, unsafe_allow_html=True)


def render_hero(compounding: CompoundingMetrics, inputs: SimulationInputs) -> None:
    decision_gap = compounding.final_value_stay - compounding.available_net_capital
    state = outcome_class(decision_gap)

    html = dedent(
        f"""
        <div class="hero">
            <div class="hero-topline">Investment decision dashboard</div>
            <div class="hero-grid">
                <div>
                    <div class="hero-title">Simulatore investimento e uscita anticipata</div>
                    <p class="hero-subtitle">
                        Una dashboard decisionale progettata per misurare il costo economico di un’uscita anticipata.
                        Il focus non è solo la penale. È soprattutto il valore futuro che smette di comporsi nel tempo.
                    </p>
                </div>
                <div class="hero-side">
                    <div class="mini-kicker">Scenario attivo</div>
                    <div class="mini-title">Uscita al {inputs.exit_year}° anno su un piano di {inputs.duration_years} anni</div>
                    <div class="mini-copy">
                        Capitale netto disponibile in uscita <strong>{format_eur(compounding.available_net_capital)}</strong>.
                        Valore finale stimato restando investito <strong>{format_eur(compounding.final_value_stay)}</strong>.
                    </div>
                </div>
            </div>
            <div class="decision-banner {state}">
                <div class="decision-dot"></div>
                <div>
                    <div class="decision-title">Messaggio chiave per la decisione</div>
                    <div class="decision-copy">
                        Uscendo al <strong>{inputs.exit_year}° anno</strong> rinunci a circa
                        <strong>{format_eur(compounding.lost_compounding_abs)}</strong> di crescita futura,
                        pari al <strong>{format_pct(compounding.lost_compounding_pct)}</strong> del valore finale stimato.
                    </div>
                </div>
            </div>
        </div>
        """
    ).strip()
    st.markdown(html, unsafe_allow_html=True)


def render_sidebar() -> SimulationInputs:
    with st.sidebar:
        st.markdown(
            dedent(
                """
                <div class="sidebar-shell">
                    <div class="sidebar-kicker">Scenario setup</div>
                    <div class="sidebar-title">Configura la simulazione</div>
                    <div class="sidebar-copy">
                        Imposta il piano, lo scenario di uscita e il livello di incertezza.
                        L’interfaccia mette al centro il trade-off tra liquidità immediata e valore futuro.
                    </div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

        with st.form("simulation_form", clear_on_submit=False):
            st.markdown('<div class="sidebar-group-title">Piano di investimento</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Definisci capitale iniziale, contributo mensile, rendimento atteso e durata del piano.</div>',
                unsafe_allow_html=True,
            )

            initial_capital = st.number_input(
                "Investimento iniziale (EUR)",
                min_value=0.0,
                value=20000.0,
                step=1000.0,
            )
            monthly_contribution = st.number_input(
                "Versamento mensile (EUR)",
                min_value=0.0,
                value=500.0,
                step=50.0,
            )
            annual_return_pct = st.slider(
                "Rendimento annuo atteso (%)",
                min_value=0,
                max_value=15,
                value=7,
            )
            duration_years = st.slider(
                "Durata del piano (anni)",
                min_value=1,
                max_value=30,
                value=10,
            )

            st.markdown('<div class="sidebar-group-title">Scenario di uscita</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Simula uscita anticipata, penale applicata e nuovo reinvestimento.</div>',
                unsafe_allow_html=True,
            )

            max_exit_year = max(0, duration_years - 1)

            exit_year = st.slider(
                "Anno di uscita",
                min_value=0,
                max_value=max_exit_year,
                value=min(5, max_exit_year),
                help="L’uscita anticipata è disponibile solo prima della scadenza finale.",
            )
            exit_penalty_pct = st.slider(
                "Penale di uscita (% su capitale versato)",
                min_value=0.0,
                max_value=20.0,
                value=2.0,
                step=0.5,
            )
            exit_extra_cost = st.number_input(
                "Altri costi di uscita (EUR)",
                min_value=0.0,
                value=0.0,
                step=100.0,
            )
            alternative_return_pct = st.slider(
                "Rendimento annuo nuovo investimento (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.0,
                step=0.5,
            )

            st.markdown('<div class="sidebar-group-title">Robustezza della stima</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Usa Monte Carlo per stimare quanto spesso restare investito risulta migliore dello scenario di uscita.</div>',
                unsafe_allow_html=True,
            )

            uncertainty_level = st.select_slider(
                "Oscillazione dei rendimenti",
                options=["Bassa", "Media", "Alta"],
                value="Media",
            )
            n_simulations = st.select_slider(
                "Numero simulazioni",
                options=[1000, 3000, 5000, 10000],
                value=3000,
            )

            st.form_submit_button("Aggiorna dashboard", use_container_width=True)

        st.caption("I risultati vengono aggiornati utilizzando i parametri attualmente selezionati.")

    return SimulationInputs(
        initial_capital=initial_capital,
        monthly_contribution=monthly_contribution,
        annual_return=annual_return_pct / 100,
        duration_years=duration_years,
        exit_year=exit_year,
        exit_penalty_pct=exit_penalty_pct / 100,
        exit_extra_cost=exit_extra_cost,
        alternative_return=alternative_return_pct / 100,
        uncertainty_level=uncertainty_level,
        n_simulations=n_simulations,
    )


# ======================================================
# APP
# ======================================================

apply_theme()
inputs = render_sidebar()

plan_df = calculate_plan(
    initial_capital=inputs.initial_capital,
    monthly_contribution=inputs.monthly_contribution,
    annual_return=inputs.annual_return,
    duration_years=inputs.duration_years,
)

final_value = float(plan_df.iloc[-1]["Total Value"])
total_contributed = float(plan_df.iloc[-1]["Total Contributed"])
gain_value = final_value - total_contributed
roi_pct = (gain_value / total_contributed * 100) if total_contributed > 0 else 0.0

exit_metrics = calculate_exit_metrics(
    base_df=plan_df,
    initial_capital=inputs.initial_capital,
    monthly_contribution=inputs.monthly_contribution,
    exit_year=inputs.exit_year,
    duration_years=inputs.duration_years,
    exit_penalty_pct=inputs.exit_penalty_pct,
    exit_extra_cost=inputs.exit_extra_cost,
    alternative_return=inputs.alternative_return,
)

compounding_metrics = calculate_compounding_metrics(
    base_df=plan_df,
    initial_capital=inputs.initial_capital,
    monthly_contribution=inputs.monthly_contribution,
    exit_year=inputs.exit_year,
    exit_penalty_pct=inputs.exit_penalty_pct,
    exit_extra_cost=inputs.exit_extra_cost,
)

mc_metrics = simulate_probability_stay_better(
    initial_capital=inputs.initial_capital,
    monthly_contribution=inputs.monthly_contribution,
    expected_return=inputs.annual_return,
    duration_years=inputs.duration_years,
    exit_year=inputs.exit_year,
    exit_penalty_pct=inputs.exit_penalty_pct,
    exit_extra_cost=inputs.exit_extra_cost,
    alternative_return=inputs.alternative_return,
    uncertainty_level=inputs.uncertainty_level,
    n_simulations=inputs.n_simulations,
    seed=42,
)

compounding_table = build_compounding_table(
    base_df=plan_df,
    initial_capital=inputs.initial_capital,
    monthly_contribution=inputs.monthly_contribution,
    duration_years=inputs.duration_years,
    exit_penalty_pct=inputs.exit_penalty_pct,
    exit_extra_cost=inputs.exit_extra_cost,
)

st.markdown('<div class="app-stack">', unsafe_allow_html=True)

render_hero(compounding_metrics, inputs)

open_panel()
section_header(
    "Executive summary",
    "KPI principali",
    "I numeri più importanti per valutare valore atteso, costo opportunità e robustezza della decisione.",
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    render_metric_card(
        label="Valore finale stimato",
        value=format_eur(final_value),
        help_text="Capitale atteso mantenendo il piano fino alla scadenza selezionata.",
        delta_text=format_pct_signed(roi_pct),
        delta_css=delta_class(roi_pct, positive_is_good=True),
        emphasis=True,
    )
with k2:
    render_metric_card(
        label="Totale investito",
        value=format_eur(total_contributed),
        help_text="Somma di investimento iniziale e versamenti lungo tutta la durata del piano.",
        delta_text=f"{inputs.duration_years} anni",
        delta_css="delta-neutral",
    )
with k3:
    render_metric_card(
        label="Compounding perso",
        value=format_eur(compounding_metrics.lost_compounding_abs),
        help_text="Valore futuro che non catturi se interrompi il piano nel punto selezionato.",
        delta_text=format_pct(compounding_metrics.lost_compounding_pct),
        delta_css="delta-negative",
        emphasis=True,
    )
with k4:
    render_metric_card(
        label="Probabilità che restare sia meglio",
        value=format_pct(mc_metrics.probability_stay_better),
        help_text="Frequenza con cui lo scenario stay supera lo scenario exit nella simulazione Monte Carlo.",
        delta_text=f"vol. {mc_metrics.used_volatility_pct}%",
        delta_css="delta-neutral",
    )
close_panel()

left_col, right_col = st.columns([1.35, 1], gap="large")

with left_col:
    open_panel()
    section_header(
        "Capital trajectory",
        "Evoluzione del capitale nel tempo",
        "La linea tratteggiata mostra il capitale effettivamente versato. La curva principale mostra il valore complessivo stimato del piano.",
    )

    render_legend_item("Valore totale stimato", format_eur(final_value), THEME["chart_main"])
    render_legend_item("Capitale versato", format_eur(total_contributed), THEME["chart_neutral"])
    render_legend_item("Crescita cumulata", format_eur(gain_value), THEME["chart_main_soft"])

    st.altair_chart(create_growth_chart(plan_df), use_container_width=True)
    close_panel()

with right_col:
    open_panel()
    section_header(
        "Decision view",
        "Confronto diretto dei due esiti finali",
        "Una sintesi compatta per leggere il vantaggio economico del mantenere il piano rispetto all’uscita con reinvestimento alternativo.",
    )

    render_insight_card(
        "Valore finale se resti investito",
        format_eur(exit_metrics.final_value_stay),
        "Scenario base mantenendo il piano attivo fino alla scadenza.",
    )
    st.markdown('<div class="tight-gap"></div>', unsafe_allow_html=True)
    render_insight_card(
        "Valore finale se esci e reinvesti",
        format_eur(exit_metrics.final_value_alternative),
        f"Scenario alternativo con uscita al {inputs.exit_year}° anno e reinvestimento al nuovo rendimento atteso.",
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    a, b = st.columns(2)
    with a:
        render_metric_card(
            label="Penale di uscita",
            value=format_eur(exit_metrics.exit_penalty_eur),
            help_text=(
                f"{format_pct(inputs.exit_penalty_pct * 100)} applicato su "
                f"{format_eur(exit_metrics.contributed_until_exit)} versati fino all’uscita."
            ),
        )
    with b:
        render_metric_card(
            label="Costo medio atteso",
            value=format_eur(mc_metrics.expected_cost_mc),
            help_text="Differenza media tra stay ed exit considerando la simulazione Monte Carlo.",
        )

    st.markdown(
        dedent(
            f"""
            <div class="subtle-note">
                Parametri Monte Carlo. Incertezza <strong>{inputs.uncertainty_level}</strong>,
                volatilità usata <strong>{mc_metrics.used_volatility_pct}%</strong>,
                simulazioni <strong>{inputs.n_simulations:,}</strong>.
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )
    close_panel()

bottom_left, bottom_right = st.columns([1, 1.12], gap="large")

with bottom_left:
    open_panel()
    section_header(
        "Scenario comparison",
        "Valore finale dei due scenari",
        "Vista sintetica per confrontare il risultato a scadenza del piano con lo scenario di uscita anticipata.",
    )
    st.altair_chart(
        create_scenario_comparison_chart(
            exit_metrics.final_value_stay,
            exit_metrics.final_value_alternative,
        ),
        use_container_width=True,
    )
    close_panel()

with bottom_right:
    open_panel()
    section_header(
        "Compounding impact",
        f"Quanto valore futuro perdi uscendo dopo {inputs.exit_year} anni",
        "Questa vista mostra il capitale netto disponibile in uscita e il valore complessivo stimato che potresti catturare lasciando lavorare il tempo.",
    )

    r1, r2 = st.columns(2)
    with r1:
        render_metric_card(
            label="Capitale netto disponibile",
            value=format_eur(compounding_metrics.available_net_capital),
            help_text=f"Valore disponibile al {inputs.exit_year}° anno dopo penale e costi extra.",
            delta_text=format_eur(compounding_metrics.exit_penalty_eur),
            delta_css="delta-neutral",
        )
    with r2:
        render_metric_card(
            label="Valore finale a scadenza",
            value=format_eur(compounding_metrics.final_value_stay),
            help_text="Valore finale stimato se il piano resta attivo fino alla durata prevista.",
            delta_text=f"{inputs.duration_years} anni",
            delta_css="delta-neutral",
        )

    r3, r4 = st.columns(2)
    with r3:
        render_metric_card(
            label="Valore futuro non catturato",
            value=format_eur(compounding_metrics.lost_compounding_abs),
            help_text="Differenza tra valore finale a scadenza e capitale netto disponibile in uscita.",
            delta_text="opportunità persa",
            delta_css="delta-negative",
            emphasis=True,
        )
    with r4:
        render_metric_card(
            label="Quota di valore finale persa",
            value=format_pct(compounding_metrics.lost_compounding_pct),
            help_text="Percentuale del valore finale complessivo a cui rinunci uscendo prima della scadenza.",
            delta_text=f"uscita al {inputs.exit_year}° anno",
            delta_css="delta-neutral",
        )

    if not compounding_table.empty:
        st.altair_chart(
            create_lost_compounding_chart(compounding_table, inputs.exit_year),
            use_container_width=True,
        )
        st.markdown(
            dedent(
                f"""
                <div class="subtle-note">
                    Lettura rapida. Se esci al <strong>{inputs.exit_year}° anno</strong> hai disponibile circa
                    <strong>{format_eur(compounding_metrics.available_net_capital)}</strong>.
                    Restando fino alla fine, la stima sale a
                    <strong>{format_eur(compounding_metrics.final_value_stay)}</strong>.
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )
    else:
        st.info("Con una durata di 1 anno non esistono anni di uscita anticipata da confrontare.")

    close_panel()

open_panel()
section_header(
    "Detailed view",
    "Perdita di compounding per anno di uscita",
    "La tabella rende esplicito quanto capitale netto avresti disponibile uscendo in ciascun anno e quanta crescita futura lasceresti sul tavolo.",
)

if not compounding_table.empty:
    table_df = compounding_table.copy().rename(
        columns={
            "Exit Year": "Anno uscita",
            "Exit Value Gross": "Valore uscita lordo",
            "Contributed Capital": "Capitale versato",
            "Exit Penalty EUR": "Penale uscita",
            "Available Net Capital": "Capitale netto disponibile",
            "Lost Compounding EUR": "Crescita composta persa",
            "Lost Compounding %": "Crescita persa %",
        }
    )

    styler = (
    table_df.style
    .hide(axis="index")
    .format({
        "Anno uscita": "{:.0f}",
        "Valore uscita lordo": "{:,.0f} EUR",
        "Capitale versato": "{:,.0f} EUR",
        "Penale uscita": "{:,.0f} EUR",
        "Capitale netto disponibile": "{:,.0f} EUR",
        "Crescita composta persa": "{:,.0f} EUR",
        "Crescita persa %": "{:.2f}%",
    })
        .bar(
            subset=["Crescita persa %"],
            color="#FF5A5F",
            vmin=0,
            vmax=100,
        )
        .set_properties(**{
            "background-color": "#FFFFFF",
            "color": "#111827",
            "border-color": "#E5E7EB",
            "font-size": "13px",
        })
        .set_table_styles([
            {
                "selector": "table",
                "props": [
                    ("border-collapse", "collapse"),
                    ("width", "100%"),
                    ("background-color", "#FFFFFF"),
                    ("color", "#111827"),
                    ("border", "1px solid #E5E7EB"),
                ],
            },
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#F8FAFC"),
                    ("color", "#475467"),
                    ("font-weight", "700"),
                    ("font-size", "12px"),
                    ("border-bottom", "1px solid #E5E7EB"),
                    ("padding", "10px 12px"),
                    ("text-align", "left"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("padding", "10px 12px"),
                    ("border-bottom", "1px solid #EEF2F6"),
                    ("background-color", "#FFFFFF"),
                    ("color", "#111827"),
                ],
            },
        ])
    )

    st.table(styler)

    st.markdown(
        dedent(
            """
            <div class="subtle-note">
                Insight chiave. Più l’uscita è anticipata, più la crescita composta futura viene interrotta.
                Questa vista traduce il costo della pazienza mancata in numeri direttamente leggibili.
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )
else:
    st.info("Nessun confronto disponibile perché il piano dura un solo anno.")

close_panel()
st.markdown("</div>", unsafe_allow_html=True)