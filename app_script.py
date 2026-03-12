from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

alt.renderers.set_embed_options(theme=None)

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
    "bg": "#F4F7FB",
    "bg_top": "#FBFCFE",
    "surface": "#FFFFFF",
    "surface_soft": "#F8FAFC",
    "surface_tint": "#F6F9FF",
    "text": "#0F172A",
    "text_soft": "#334155",
    "text_muted": "#64748B",
    "border": "#E2E8F0",
    "border_soft": "#EDF2F7",
    "grid": "#E8EEF5",
    "primary": "#2563EB",
    "primary_dark": "#1D4ED8",
    "primary_soft": "#DBEAFE",
    "secondary": "#7C3AED",
    "secondary_soft": "#E9D5FF",
    "success": "#0F9F6E",
    "warning": "#B7791F",
    "danger": "#D14343",
    "danger_soft": "#FEE2E2",
    "shadow_sm": "0 1px 2px rgba(15, 23, 42, 0.04)",
    "shadow_md": "0 12px 28px rgba(15, 23, 42, 0.06)",
    "shadow_lg": "0 18px 48px rgba(15, 23, 42, 0.08)",
    "radius_sm": "16px",
    "radius_md": "20px",
    "radius_lg": "24px",
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
    available_net_capital: float
    final_value_alternative: float
    opportunity_cost_abs: float
    opportunity_cost_pct: float
    remaining_years: int


@dataclass(frozen=True)
class MonteCarloMetrics:
    probability_stay_better: float
    expected_shortfall_exit: float
    stay_mean: float
    exit_mean: float
    used_volatility_pct: float
    stay_p10: float
    stay_p50: float
    stay_p90: float
    exit_p10: float
    exit_p50: float
    exit_p90: float
    break_even_probability: float
    distribution_df: pd.DataFrame


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


def recommendation_state(probability: float) -> str:
    if probability >= 65:
        return "positive"
    if probability <= 35:
        return "negative"
    return "neutral"


# ======================================================
# STYLE
# ======================================================

def apply_theme() -> None:
    st.markdown(
        dedent(
            f"""
<style>
:root {{
    --bg: {THEME['bg']};
    --bg-top: {THEME['bg_top']};
    --surface: {THEME['surface']};
    --surface-soft: {THEME['surface_soft']};
    --surface-tint: {THEME['surface_tint']};
    --text: {THEME['text']};
    --text-soft: {THEME['text_soft']};
    --text-muted: {THEME['text_muted']};
    --border: {THEME['border']};
    --border-soft: {THEME['border_soft']};
    --grid: {THEME['grid']};
    --primary: {THEME['primary']};
    --primary-dark: {THEME['primary_dark']};
    --primary-soft: {THEME['primary_soft']};
    --secondary: {THEME['secondary']};
    --secondary-soft: {THEME['secondary_soft']};
    --success: {THEME['success']};
    --warning: {THEME['warning']};
    --danger: {THEME['danger']};
    --danger-soft: {THEME['danger_soft']};
    --shadow-sm: {THEME['shadow_sm']};
    --shadow-md: {THEME['shadow_md']};
    --shadow-lg: {THEME['shadow_lg']};
    --radius-sm: {THEME['radius_sm']};
    --radius-md: {THEME['radius_md']};
    --radius-lg: {THEME['radius_lg']};
}}

.stApp {{
    background:
        radial-gradient(circle at top left, rgba(37,99,235,0.05), transparent 28%),
        linear-gradient(180deg, var(--bg-top) 0%, var(--bg) 42%, var(--bg) 100%);
    color: var(--text);
}}

.block-container {{
    max-width: 1360px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
    padding-right: 2rem;
}}

h1, h2, h3, h4 {{
    letter-spacing: -0.03em;
}}

[data-testid="stSidebar"] {{
    background: rgba(255,255,255,0.84);
    border-right: 1px solid var(--border-soft);
    backdrop-filter: blur(18px);
}}

[data-testid="stSidebar"] .block-container {{
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}}

.app-stack {{
    display: flex;
    flex-direction: column;
    gap: 1.4rem;
}}

.hero {{
    background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.94) 100%);
    border: 1px solid rgba(226,232,240,0.88);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    padding: 1.2rem 1.25rem 1.25rem 1.25rem;
}}

.hero-topline {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.36rem 0.72rem;
    border-radius: 999px;
    background: rgba(37,99,235,0.08);
    border: 1px solid rgba(37,99,235,0.12);
    color: var(--primary-dark);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.85rem;
}}

.hero-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.35fr) minmax(340px, 0.95fr);
    gap: 1rem;
}}

.hero-title {{
    margin: 0 0 0.45rem 0;
    font-size: 2.15rem;
    line-height: 1.02;
    font-weight: 860;
    color: var(--text);
}}

.hero-subtitle {{
    margin: 0;
    max-width: 860px;
    color: var(--text-soft);
    font-size: 0.96rem;
    line-height: 1.65;
}}

.hero-side {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 0.95rem 1rem;
}}

.kicker {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.3rem;
}}

.side-title {{
    color: var(--text);
    font-size: 1rem;
    font-weight: 820;
    line-height: 1.25;
    margin-bottom: 0.45rem;
}}

.side-copy {{
    color: var(--text-soft);
    font-size: 0.9rem;
    line-height: 1.55;
}}

.decision-hero {{
    margin-top: 1rem;
    padding: 1rem;
    border-radius: 20px;
    border: 1px solid var(--border-soft);
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
}}

.decision-hero.positive {{
    border-color: rgba(15,159,110,0.22);
    background: linear-gradient(180deg, rgba(240,253,248,1) 0%, rgba(255,255,255,1) 100%);
}}

.decision-hero.negative {{
    border-color: rgba(209,67,67,0.18);
    background: linear-gradient(180deg, rgba(254,242,242,1) 0%, rgba(255,255,255,1) 100%);
}}

.decision-grid {{
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) repeat(3, minmax(0, 1fr));
    gap: 0.85rem;
    align-items: stretch;
}}

.decision-main {{
    padding-right: 0.35rem;
}}

.decision-label {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}}

.decision-title {{
    color: var(--text);
    font-size: 1.35rem;
    line-height: 1.12;
    font-weight: 860;
    margin-bottom: 0.42rem;
}}

.decision-copy {{
    color: var(--text-soft);
    font-size: 0.93rem;
    line-height: 1.62;
}}

.pill {{
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.5rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 850;
    margin-top: 0.7rem;
}}

.pill-positive {{
    color: var(--success);
    background: rgba(15,159,110,0.10);
}}

.pill-negative {{
    color: var(--danger);
    background: rgba(209,67,67,0.10);
}}

.pill-neutral {{
    color: var(--warning);
    background: rgba(183,121,31,0.10);
}}

.metric-card {{
    background: linear-gradient(180deg, #FFFFFF 0%, #FAFCFF 100%);
    border: 1px solid rgba(226,232,240,0.9);
    border-radius: 18px;
    padding: 1rem 1.05rem;
    min-height: 148px;
    box-shadow: var(--shadow_sm);
}}

.metric-card.emphasis {{
    border-color: rgba(37,99,235,0.18);
    box-shadow: 0 8px 20px rgba(37,99,235,0.08);
    background: linear-gradient(180deg, #F7FAFF 0%, #FFFFFF 100%);
}}

.metric-label {{
    color: var(--text-muted);
    font-size: 0.71rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.45rem;
}}

.metric-value {{
    color: var(--text);
    font-size: 1.9rem;
    line-height: 1.02;
    font-weight: 860;
    letter-spacing: -0.05em;
    margin-bottom: 0.45rem;
}}

.metric-help {{
    color: var(--text-soft);
    font-size: 0.86rem;
    line-height: 1.55;
}}

.metric-delta {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    border-radius: 999px;
    padding: 0.22rem 0.5rem;
    font-size: 0.72rem;
    font-weight: 850;
    margin-bottom: 0.6rem;
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

.panel-head {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 1rem;
}}

.panel-kicker {{
    color: var(--text-muted);
    font-size: 0.7rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.28rem;
}}

.panel-title {{
    margin: 0 0 0.18rem 0;
    color: var(--text);
    font-size: 1.12rem;
    line-height: 1.14;
    font-weight: 850;
}}

.panel-note {{
    margin: 0;
    color: var(--text-soft);
    font-size: 0.9rem;
    line-height: 1.55;
    max-width: 880px;
}}

.insight-card {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid var(--border-soft);
    border-radius: 18px;
    padding: 1rem;
}}

.insight-title {{
    color: var(--text-muted);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.42rem;
}}

.insight-value {{
    color: var(--text);
    font-size: 1.9rem;
    line-height: 1.02;
    font-weight: 860;
    letter-spacing: -0.04em;
    margin-bottom: 0.38rem;
}}

.insight-copy {{
    color: var(--text-soft);
    font-size: 0.88rem;
    line-height: 1.56;
}}

.legend-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.8rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border_soft);
}}

.legend-row:last-child {{
    border-bottom: none;
}}

.legend-left {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    color: var(--text);
    font-size: 0.9rem;
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
    font-size: 0.9rem;
    font-weight: 800;
}}

.section-shell {{
    background: transparent;
}}

.divider {{
    height: 1px;
    background: var(--border-soft);
    margin: 0.95rem 0;
}}

.subtle-note {{
    color: var(--text-muted);
    font-size: 0.82rem;
    line-height: 1.52;
}}

.sidebar-shell {{
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--border-soft);
    margin-bottom: 1rem;
}}

.sidebar-kicker {{
    color: var(--text-muted);
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.32rem;
}}

.sidebar-title {{
    color: var(--text);
    font-size: 1.14rem;
    line-height: 1.16;
    font-weight: 850;
    margin-bottom: 0.4rem;
}}

.sidebar-copy {{
    color: var(--text-soft);
    font-size: 0.88rem;
    line-height: 1.52;
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
    background: #FFFFFF !important;
    font-weight: 600 !important;
}}

div[data-testid="stNumberInput"] button {{
    background: #F8FAFC !important;
    color: var(--text) !important;
    border-left: 1px solid var(--border-soft) !important;
    min-height: 46px !important;
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

@media (max-width: 1200px) {{
    .hero-grid {{
        grid-template-columns: 1fr;
    }}

    .decision-grid {{
        grid-template-columns: 1fr;
    }}

    .hero-title {{
        font-size: 1.95rem;
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


def contributed_until_exit(initial_capital: float, monthly_contribution: float, exit_year: int) -> float:
    return float(initial_capital + monthly_contribution * 12 * exit_year)


def alternative_final_value(
    exit_value_gross: float,
    remaining_years: int,
    exit_penalty_eur: float,
    exit_extra_cost: float,
    alternative_return: float,
) -> tuple[float, float]:
    net_capital = max(exit_value_gross - exit_penalty_eur - exit_extra_cost, 0.0)
    return net_capital, net_capital * ((1 + alternative_return) ** remaining_years)


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
    available_net_capital, final_value_alternative = alternative_final_value(
        exit_value_gross=exit_value_gross,
        remaining_years=remaining_years,
        exit_penalty_eur=exit_penalty_eur,
        exit_extra_cost=exit_extra_cost,
        alternative_return=alternative_return,
    )

    opportunity_cost_abs = final_value_stay - final_value_alternative
    opportunity_cost_pct = 100 * opportunity_cost_abs / final_value_stay if final_value_stay > 0 else 0.0

    return ExitMetrics(
        final_value_stay=round(final_value_stay, 2),
        exit_value_gross=round(exit_value_gross, 2),
        contributed_until_exit=round(contributed, 2),
        exit_penalty_eur=round(exit_penalty_eur, 2),
        available_net_capital=round(available_net_capital, 2),
        final_value_alternative=round(final_value_alternative, 2),
        opportunity_cost_abs=round(opportunity_cost_abs, 2),
        opportunity_cost_pct=round(opportunity_cost_pct, 2),
        remaining_years=remaining_years,
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

    volatility_map = {"Bassa": 0.08, "Media": 0.12, "Alta": 0.18}
    annual_volatility = volatility_map.get(uncertainty_level, 0.12)
    alternative_annual_volatility = 0.02

    total_months = duration_years * 12
    exit_months = exit_year * 12
    remaining_months = max(total_months - exit_months, 0)

    mu_main = expected_return / 12
    sigma_main = annual_volatility / np.sqrt(12)
    mu_alt = alternative_return / 12
    sigma_alt = alternative_annual_volatility / np.sqrt(12)

    contributed = contributed_until_exit(initial_capital, monthly_contribution, exit_year)
    exit_penalty_eur = contributed * exit_penalty_pct

    main_returns = rng.normal(mu_main, sigma_main, size=(n_simulations, total_months))

    stay_path = np.full(n_simulations, initial_capital, dtype=np.float64)
    for month in range(total_months):
        stay_path = (stay_path + monthly_contribution) * (1.0 + main_returns[:, month])

    exit_path = np.full(n_simulations, initial_capital, dtype=np.float64)
    for month in range(exit_months):
        exit_path = (exit_path + monthly_contribution) * (1.0 + main_returns[:, month])

    exit_net_capital = np.maximum(exit_path - exit_penalty_eur - exit_extra_cost, 0.0)

    if remaining_months > 0:
        alt_returns = rng.normal(mu_alt, sigma_alt, size=(n_simulations, remaining_months))
        alt_path = exit_net_capital.copy()
        for month in range(remaining_months):
            alt_path *= 1.0 + alt_returns[:, month]
    else:
        alt_path = exit_net_capital

    probability = float(np.mean(stay_path > alt_path)) * 100
    shortfall = stay_path - alt_path

    distribution_df = pd.DataFrame(
        {
            "stay": stay_path,
            "exit": alt_path,
            "delta": shortfall,
        }
    )

    return MonteCarloMetrics(
        probability_stay_better=round(probability, 1),
        expected_shortfall_exit=round(float(np.mean(shortfall)), 2),
        stay_mean=round(float(np.mean(stay_path)), 2),
        exit_mean=round(float(np.mean(alt_path)), 2),
        used_volatility_pct=round(annual_volatility * 100, 1),
        stay_p10=round(float(np.percentile(stay_path, 10)), 2),
        stay_p50=round(float(np.percentile(stay_path, 50)), 2),
        stay_p90=round(float(np.percentile(stay_path, 90)), 2),
        exit_p10=round(float(np.percentile(alt_path, 10)), 2),
        exit_p50=round(float(np.percentile(alt_path, 50)), 2),
        exit_p90=round(float(np.percentile(alt_path, 90)), 2),
        break_even_probability=round(float(np.mean(shortfall <= 0)) * 100, 1),
        distribution_df=distribution_df,
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
    lost_compounding_pct = np.where(final_value_stay > 0, 100 * lost_compounding / final_value_stay, 0.0)

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


def build_scenario_paths(plan_df: pd.DataFrame, exit_metrics: ExitMetrics, alternative_return: float, exit_year: int) -> pd.DataFrame:
    years = plan_df["Year"].tolist()
    stay_values = plan_df["Total Value"].tolist()

    alt_values = []
    for year in years:
        if year < exit_year:
            alt_values.append(np.nan)
        elif year == exit_year:
            alt_values.append(exit_metrics.available_net_capital)
        else:
            alt_values.append(exit_metrics.available_net_capital * ((1 + alternative_return) ** (year - exit_year)))

    rows = []
    for year, stay, alt_value in zip(years, stay_values, alt_values):
        rows.append({"Year": year, "Scenario": "Restare investito", "Value": stay})
        if not np.isnan(alt_value):
            rows.append({"Year": year, "Scenario": "Uscire e reinvestire", "Value": alt_value})

    return pd.DataFrame(rows)


# ======================================================
# CHARTS
# ======================================================

def chart_theme() -> dict:
    return {
        "config": {
            "background": "#FFFFFF",
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
            "view": {"stroke": None, "fill": "#FFFFFF"},
        }
    }


def finalize_chart(chart: alt.Chart, height: int) -> alt.Chart:
    return (
        chart.properties(height=height, background="#FFFFFF")
        .configure(**chart_theme()["config"])
        .configure_view(stroke=None, fill="#FFFFFF")
    )


def create_decision_paths_chart(plan_df: pd.DataFrame, exit_metrics: ExitMetrics, alternative_return: float, exit_year: int) -> alt.Chart:
    chart_df = build_scenario_paths(plan_df, exit_metrics, alternative_return, exit_year)

    color_scale = alt.Scale(
        domain=["Restare investito", "Uscire e reinvestire"],
        range=[THEME["primary"], THEME["secondary"]],
    )

    line = alt.Chart(chart_df).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("Year:Q", title=None, axis=alt.Axis(grid=False, tickCount=min(10, len(plan_df)))),
        y=alt.Y("Value:Q", title=None, axis=alt.Axis(format="~s")),
        color=alt.Color("Scenario:N", scale=color_scale, legend=alt.Legend(title=None, orient="top")),
        tooltip=[
            alt.Tooltip("Scenario:N", title="Scenario"),
            alt.Tooltip("Year:Q", title="Anno"),
            alt.Tooltip("Value:Q", title="Valore", format=",.0f"),
        ],
    )

    contrib = alt.Chart(plan_df).mark_line(
        color=THEME["text_muted"],
        strokeDash=[5, 5],
        strokeWidth=1.8,
        opacity=0.9,
    ).encode(
        x="Year:Q",
        y=alt.Y("Total Contributed:Q"),
        tooltip=[
            alt.Tooltip("Year:Q", title="Anno"),
            alt.Tooltip("Total Contributed:Q", title="Capitale versato", format=",.0f"),
        ],
    )

    exit_rule = alt.Chart(pd.DataFrame({"Exit Year": [exit_year]})).mark_rule(
        color=THEME["danger"],
        strokeDash=[4, 4],
        strokeWidth=1.6,
    ).encode(x="Exit Year:Q")

    exit_label = alt.Chart(pd.DataFrame({"Exit Year": [exit_year], "Label": [f"Uscita anno {exit_year}"]})).mark_text(
        align="left",
        dx=6,
        dy=-8,
        color=THEME["danger"],
        fontSize=11,
        fontWeight="bold",
    ).encode(x="Exit Year:Q", y=alt.value(16), text="Label:N")

    return finalize_chart(contrib + line + exit_rule + exit_label, 360)


def create_distribution_chart(mc_metrics: MonteCarloMetrics) -> alt.Chart:
    dist_df = mc_metrics.distribution_df.copy()
    dist_df = pd.concat(
        [
            dist_df[["stay"]].rename(columns={"stay": "Outcome"}).assign(Scenario="Restare investito"),
            dist_df[["exit"]].rename(columns={"exit": "Outcome"}).assign(Scenario="Uscire e reinvestire"),
        ],
        ignore_index=True,
    )

    color_scale = alt.Scale(
        domain=["Restare investito", "Uscire e reinvestire"],
        range=[THEME["primary"], THEME["secondary"]],
    )

    chart = alt.Chart(dist_df).transform_bin(
        as_=["bin_start", "bin_end"],
        field="Outcome",
        bin=alt.Bin(maxbins=30),
    ).mark_bar(opacity=0.55).encode(
        x=alt.X("bin_start:Q", title="Valore finale", axis=alt.Axis(format="~s")),
        x2="bin_end:Q",
        y=alt.Y("count():Q", title="Frequenza"),
        color=alt.Color("Scenario:N", scale=color_scale, legend=alt.Legend(title=None, orient="top")),
        tooltip=[
            alt.Tooltip("Scenario:N", title="Scenario"),
            alt.Tooltip("count():Q", title="Frequenza"),
        ],
    )

    return finalize_chart(chart, 280)


def create_exit_timing_chart(df_compounding: pd.DataFrame, selected_exit_year: int) -> alt.Chart:
    chart_df = df_compounding.copy()
    chart_df["Selection"] = np.where(chart_df["Exit Year"] == selected_exit_year, "Selezionato", "Altri")

    bars = alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8).encode(
        x=alt.X("Exit Year:O", title="Anno di uscita", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Lost Compounding EUR:Q", title="Valore futuro sacrificato", axis=alt.Axis(format="~s")),
        color=alt.condition(
            alt.datum.Selection == "Selezionato",
            alt.value(THEME["primary_dark"]),
            alt.value(THEME["primary_soft"]),
        ),
        tooltip=[
            alt.Tooltip("Exit Year:Q", title="Anno uscita"),
            alt.Tooltip("Available Net Capital:Q", title="Capitale netto disponibile", format=",.0f"),
            alt.Tooltip("Lost Compounding EUR:Q", title="Valore futuro sacrificato", format=",.0f"),
            alt.Tooltip("Lost Compounding %:Q", title="% del valore finale", format=".2f"),
        ],
    )

    trend = alt.Chart(chart_df).mark_line(color=THEME["primary"], strokeWidth=2.2).encode(
        x="Exit Year:O",
        y="Lost Compounding EUR:Q",
    )

    return finalize_chart(bars + trend, 300)


# ======================================================
# UI HELPERS
# ======================================================

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
    delta_html = f'<div class="metric-delta {delta_css}">{delta_text}</div>' if delta_text else ""

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


def render_hero(inputs: SimulationInputs, exit_metrics: ExitMetrics, mc_metrics: MonteCarloMetrics) -> None:
    state = recommendation_state(mc_metrics.probability_stay_better)
    if state == "positive":
        headline = "Restare investito appare economicamente superiore"
        pill_class = "pill pill-positive"
        pill_text = "Scenario preferito"
    elif state == "negative":
        headline = "L'uscita anticipata risulta competitiva"
        pill_class = "pill pill-negative"
        pill_text = "Scenario alternativo forte"
    else:
        headline = "La decisione è meno netta e richiede cautela"
        pill_class = "pill pill-neutral"
        pill_text = "Scenario borderline"

    html = dedent(
        f"""
        <div class="hero">
            <div class="hero-topline">Investment decision dashboard</div>
            <div class="hero-grid">
                <div>
                    <div class="hero-title">Simulatore investimento e uscita anticipata</div>
                    <p class="hero-subtitle">
                        Dashboard decisionale focalizzata sul trade-off tra liquidità immediata e valore futuro.
                        La vista iniziale mette al centro il delta economico tra restare investito e uscire prima.
                    </p>
                </div>
                <div class="hero-side">
                    <div class="kicker">Scenario attivo</div>
                    <div class="side-title">Uscita al {inputs.exit_year}° anno su un piano di {inputs.duration_years} anni</div>
                    <div class="side-copy">
                        Capitale netto disponibile in uscita <strong>{format_eur(exit_metrics.available_net_capital)}</strong>.
                        Valore atteso a scadenza restando investito <strong>{format_eur(exit_metrics.final_value_stay)}</strong>.
                    </div>
                </div>
            </div>
            <div class="decision-hero {state}">
                <div class="decision-grid">
                    <div class="decision-main">
                        <div class="decision-label">Raccomandazione di scenario</div>
                        <div class="decision-title">{headline}</div>
                        <div class="decision-copy">
                            Uscire al <strong>{inputs.exit_year}° anno</strong> riduce il valore atteso finale di
                            <strong>{format_eur(exit_metrics.opportunity_cost_abs)}</strong>, pari al
                            <strong>{format_pct(exit_metrics.opportunity_cost_pct)}</strong> dello scenario di permanenza.
                        </div>
                        <div class="{pill_class}">{pill_text}</div>
                    </div>
                    <div class="metric-card emphasis">
                        <div class="metric-label">Valore netto se esci</div>
                        <div class="metric-value">{format_eur(exit_metrics.available_net_capital)}</div>
                        <div class="metric-help">Capitale immediatamente disponibile dopo penale e costi.</div>
                    </div>
                    <div class="metric-card emphasis">
                        <div class="metric-label">Valore atteso se resti</div>
                        <div class="metric-value">{format_eur(exit_metrics.final_value_stay)}</div>
                        <div class="metric-help">Stima del valore a scadenza mantenendo il piano attivo.</div>
                    </div>
                    <div class="metric-card emphasis">
                        <div class="metric-label">Confidenza statistica</div>
                        <div class="metric-value">{format_pct(mc_metrics.probability_stay_better)}</div>
                        <div class="metric-help">Quota simulazioni Monte Carlo in cui restare investito batte l'uscita.</div>
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
                        Organizza gli input in tre blocchi mentali. Piano attuale, uscita anticipata e ipotesi di rischio.
                    </div>
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

        with st.form("simulation_form", clear_on_submit=False):
            st.markdown('<div class="sidebar-group-title">Piano attuale</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Capitale iniziale, contributi, rendimento atteso e orizzonte del piano.</div>',
                unsafe_allow_html=True,
            )
            initial_capital = st.number_input("Investimento iniziale (EUR)", min_value=0.0, value=20000.0, step=1000.0)
            monthly_contribution = st.number_input("Versamento mensile (EUR)", min_value=0.0, value=500.0, step=50.0)
            annual_return_pct = st.slider("Rendimento annuo atteso (%)", min_value=0, max_value=15, value=7)
            duration_years = st.slider("Durata del piano (anni)", min_value=1, max_value=30, value=10)

            st.markdown('<div class="sidebar-group-title">Scenario di uscita</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Definisci timing di uscita, penale e costi extra.</div>',
                unsafe_allow_html=True,
            )
            max_exit_year = max(0, duration_years - 1)
            exit_year = st.slider(
                "Anno di uscita",
                min_value=0,
                max_value=max_exit_year,
                value=min(5, max_exit_year),
                help="L'uscita anticipata è disponibile solo prima della scadenza finale.",
            )
            exit_penalty_pct = st.slider("Penale di uscita (% su capitale versato)", min_value=0.0, max_value=20.0, value=2.0, step=0.5)
            exit_extra_cost = st.number_input("Altri costi di uscita (EUR)", min_value=0.0, value=0.0, step=100.0)

            st.markdown('<div class="sidebar-group-title">Scenario di reinvestimento e rischio</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sidebar-group-note">Nuovo rendimento ipotizzato e robustezza della simulazione Monte Carlo.</div>',
                unsafe_allow_html=True,
            )
            alternative_return_pct = st.slider("Rendimento annuo nuovo investimento (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)
            uncertainty_level = st.select_slider("Oscillazione dei rendimenti", options=["Bassa", "Media", "Alta"], value="Media")
            n_simulations = st.select_slider("Numero simulazioni", options=[1000, 3000, 5000, 10000], value=3000)

            st.form_submit_button("Aggiorna dashboard", use_container_width=True)

        st.caption("Le metriche vengono aggiornate in base ai parametri attualmente selezionati.")

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

render_hero(inputs, exit_metrics, mc_metrics)

section_header(
    "Decision summary",
    "KPI decisionali primari",
    "I primi numeri devono guidare la scelta. Liquidità disponibile, valore atteso, costo opportunità e robustezza statistica.",
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    render_metric_card(
        label="Valore netto se esci ora",
        value=format_eur(exit_metrics.available_net_capital),
        help_text="Capitale disponibile al momento dell'uscita, al netto di penale e costi extra.",
        delta_text=f"anno {inputs.exit_year}",
        delta_css="delta-neutral",
        emphasis=True,
    )
with k2:
    render_metric_card(
        label="Valore atteso a scadenza",
        value=format_eur(exit_metrics.final_value_stay),
        help_text="Valore finale atteso mantenendo il piano fino alla durata selezionata.",
        delta_text=format_pct_signed(roi_pct),
        delta_css=delta_class(roi_pct, positive_is_good=True),
        emphasis=True,
    )
with k3:
    render_metric_card(
        label="Costo opportunità dell'uscita",
        value=format_eur(exit_metrics.opportunity_cost_abs),
        help_text="Valore finale che rinunci a catturare scegliendo uscita e reinvestimento alternativo.",
        delta_text=format_pct(exit_metrics.opportunity_cost_pct),
        delta_css="delta-negative",
        emphasis=True,
    )
with k4:
    render_metric_card(
        label="Confidenza dello scenario stay",
        value=format_pct(mc_metrics.probability_stay_better),
        help_text="Quota simulazioni in cui restare investito batte lo scenario di uscita anticipata.",
        delta_text=f"vol. {mc_metrics.used_volatility_pct}%",
        delta_css="delta-neutral",
    )

row_a, row_b = st.columns([1.35, 1], gap="large")

with row_a:
    section_header(
        "Scenario path",
        "Confronto dinamico dei due percorsi",
        "La linea blu mostra il piano mantenuto fino a scadenza. La linea viola mostra il valore disponibile dopo l'uscita e la sua evoluzione nel nuovo scenario di reinvestimento.",
    )
    render_legend_item("Restare investito", format_eur(exit_metrics.final_value_stay), THEME["primary"])
    render_legend_item("Uscire e reinvestire", format_eur(exit_metrics.final_value_alternative), THEME["secondary"])
    render_legend_item("Capitale versato", format_eur(total_contributed), THEME["text_muted"])
    st.altair_chart(
        create_decision_paths_chart(plan_df, exit_metrics, inputs.alternative_return, inputs.exit_year),
        use_container_width=True,
    )

with row_b:
    section_header(
        "Scenario comparison",
        "Confronto diretto e range probabilistici",
        "Le due card separano valore atteso e dispersione degli esiti. Questo aumenta la credibilità della decisione rispetto a una singola stima puntuale.",
    )
    render_insight_card(
        "Restare investito",
        format_eur(exit_metrics.final_value_stay),
        f"Range simulato P10-P90: {format_eur(mc_metrics.stay_p10)} - {format_eur(mc_metrics.stay_p90)}.",
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    render_insight_card(
        "Uscire e reinvestire",
        format_eur(exit_metrics.final_value_alternative),
        f"Range simulato P10-P90: {format_eur(mc_metrics.exit_p10)} - {format_eur(mc_metrics.exit_p90)}.",
    )
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        render_metric_card(
            label="Penale di uscita",
            value=format_eur(exit_metrics.exit_penalty_eur),
            help_text=f"{format_pct(inputs.exit_penalty_pct * 100)} applicato su {format_eur(exit_metrics.contributed_until_exit)} versati fino all'uscita.",
        )
    with c2:
        render_metric_card(
            label="Shortfall atteso vs stay",
            value=format_eur(mc_metrics.expected_shortfall_exit),
            help_text="Differenza media tra scenario stay e scenario exit all'interno della simulazione Monte Carlo.",
        )

risk_left, risk_right = st.columns([1, 1], gap="large")

with risk_left:
    section_header(
        "Risk distribution",
        "Distribuzione degli esiti a scadenza",
        "La distribuzione rende visibile la dispersione dei risultati e aiuta a capire se la raccomandazione resta robusta anche fuori dal caso medio.",
    )
    st.altair_chart(create_distribution_chart(mc_metrics), use_container_width=True)

with risk_right:
    section_header(
        "Timing impact",
        "Quanto costa uscire prima",
        "Il costo dell'uscita non è solo la penale. È soprattutto il valore futuro sacrificato scegliendo di interrompere il compounding troppo presto.",
    )
    r1, r2 = st.columns(2)
    with r1:
        render_metric_card(
            label="Capitale disponibile in uscita",
            value=format_eur(exit_metrics.available_net_capital),
            help_text="Valore immediatamente disponibile una volta dedotti penale e costi extra.",
            delta_text=f"anno {inputs.exit_year}",
            delta_css="delta-neutral",
        )
    with r2:
        render_metric_card(
            label="Valore futuro sacrificato",
            value=format_eur(exit_metrics.opportunity_cost_abs),
            help_text="Differenza tra valore finale mantenendo il piano e valore finale dello scenario alternativo.",
            delta_text=format_pct(exit_metrics.opportunity_cost_pct),
            delta_css="delta-negative",
            emphasis=True,
        )
    if not compounding_table.empty:
        st.altair_chart(create_exit_timing_chart(compounding_table, inputs.exit_year), use_container_width=True)
        st.markdown(
            dedent(
                f"""
                <div class="subtle-note">
                    Lettura rapida. Nel punto selezionato hai disponibile <strong>{format_eur(exit_metrics.available_net_capital)}</strong>.
                    Restando investito, il valore atteso finale sale a <strong>{format_eur(exit_metrics.final_value_stay)}</strong>.
                </div>
                """
            ).strip(),
            unsafe_allow_html=True,
        )

section_header(
    "Detailed view",
    "Matrice di uscita per anno",
    "Tabella di supporto per utenti avanzati. Utile per leggere come cambia il costo opportunità al variare del timing di uscita.",
)

if not compounding_table.empty:
    table_df = compounding_table.copy().rename(
        columns={
            "Exit Year": "Anno uscita",
            "Exit Value Gross": "Valore uscita lordo",
            "Contributed Capital": "Capitale versato",
            "Exit Penalty EUR": "Penale uscita",
            "Available Net Capital": "Capitale netto disponibile",
            "Lost Compounding EUR": "Valore futuro sacrificato",
            "Lost Compounding %": "Valore perso %",
        }
    )

    styler = (
        table_df.style.hide(axis="index")
        .format(
            {
                "Anno uscita": "{:.0f}",
                "Valore uscita lordo": "{:,.0f} EUR",
                "Capitale versato": "{:,.0f} EUR",
                "Penale uscita": "{:,.0f} EUR",
                "Capitale netto disponibile": "{:,.0f} EUR",
                "Valore futuro sacrificato": "{:,.0f} EUR",
                "Valore perso %": "{:.2f}%",
            }
        )
        .bar(subset=["Valore perso %"], color="#FF5A5F", vmin=0, vmax=100)
        .set_properties(
            **{
                "background-color": "#FFFFFF",
                "color": "#111827",
                "border-color": "#E5E7EB",
                "font-size": "13px",
            }
        )
        .set_table_styles(
            [
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
            ]
        )
    )

    st.table(styler)
    st.markdown(
        dedent(
            """
            <div class="subtle-note">
                Insight chiave. L'uscita anticipata anticipa la liquidità, ma interrompe il compounding. La tabella rende leggibile questo trade-off lungo tutta la timeline del piano.
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )
else:
    st.info("Nessun confronto disponibile perché il piano dura un solo anno.")

st.markdown("</div>", unsafe_allow_html=True)
