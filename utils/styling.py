"""
Visual identity, modeled on the Bayantx360 Suite AdminHub look: a dark,
glassy fintech-SaaS theme rather than anything playful - restrained
surfaces, one teal/violet accent pairing, Outfit for headings/UI text,
JetBrains Mono for labels and data-adjacent text. Applied globally via
one injected <style> block so every page picks it up through
inject_css().

Function names (hero_title, graffiti_divider, metric_card, etc.) are
kept stable across the earlier graffiti-themed version so every page
that already imports them keeps working - only the visual output
changed, not the API.
"""

import streamlit as st

TEAL = "#00C2A8"
VIOLET = "#7B6CF6"
AMBER = "#F59E0B"
ROSE = "#F43F5E"
GREEN = "#10B981"
BG = "#080b12"
SURFACE = "#0d1117"
SURFACE2 = "#111827"

# Cycled across metric cards so a grid of them doesn't look monotone,
# without being as loud as a full rainbow.
ACCENT_CYCLE = [TEAL, VIOLET, AMBER]

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

:root {{
    --bg: {BG};
    --surface: {SURFACE};
    --surface2: {SURFACE2};
    --surface3: #1a2332;
    --border: rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.12);
    --text: #f0f4ff;
    --muted: #64748b;
    --teal: {TEAL};
    --violet: {VIOLET};
    --amber: {AMBER};
    --rose: {ROSE};
    --green: {GREEN};
}}

html, body, [class*="css"], .stApp {{
    font-family: 'Outfit', sans-serif !important;
    background: var(--bg) !important;
    color: var(--text) !important;
}}

::-webkit-scrollbar {{ width: 4px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: var(--surface3); border-radius: 4px; }}

[data-testid="stSidebar"] {{
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}}
[data-testid="stSidebar"] * {{ color: var(--text) !important; }}

#MainMenu, footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
header[data-testid="stHeader"] {{ background: transparent !important; }}
header[data-testid="stHeader"] > div:first-child {{ visibility: hidden; }}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[kind="header"],
[data-testid="stHeader"] button {{
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: all !important;
    z-index: 999999 !important;
}}

h1, h2, h3 {{
    font-family: 'Outfit', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    color: var(--text) !important;
}}

/* ---- Hero title (landing + dashboard): gradient-clipped headline ---- */
.hero-title {{
    font-family: 'Outfit', sans-serif;
    font-size: 2.6rem;
    font-weight: 900;
    letter-spacing: -1.2px;
    line-height: 1.1;
    background: linear-gradient(135deg, #f0f4ff 35%, {TEAL});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}}
@media (max-width: 480px) {{
    .hero-title {{ font-size: 1.9rem; }}
}}
.hero-tagline {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: var(--muted);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 4px;
}}
.hero-underline {{ display: none; }}

/* ---- Section divider: thin gradient line instead of default hr ---- */
.graffiti-divider {{
    height: 1px;
    margin: 22px 0;
    background: linear-gradient(90deg, {TEAL}55, {VIOLET}33, transparent);
    border: none;
}}
hr {{ border-color: var(--border) !important; margin: 1rem 0 !important; }}

/* ---- Metric / KPI cards ---- */
.metric-card {{
    background: linear-gradient(135deg, {SURFACE}, {SURFACE2});
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.2rem 1.3rem;
    position: relative;
    overflow: hidden;
}}
.metric-card::before {{
    content: "";
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, {TEAL}, {TEAL}80);
}}
.metrics-grid > .metric-card:nth-child(3n+2)::before {{ background: linear-gradient(90deg, {VIOLET}, {VIOLET}80); }}
.metrics-grid > .metric-card:nth-child(3n+3)::before {{ background: linear-gradient(90deg, {AMBER}, {AMBER}80); }}
.metric-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: var(--text);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
}}
.metric-value {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.6rem;
    font-weight: 800;
    color: {TEAL};
    line-height: 1.1;
}}
.metrics-grid > .metric-card:nth-child(3n+2) .metric-value {{ color: {VIOLET}; }}
.metrics-grid > .metric-card:nth-child(3n+3) .metric-value {{ color: {AMBER}; }}
.metric-sub {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 3px;
}}
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-bottom: 14px;
}}
@media (max-width: 480px) {{
    .metrics-grid {{ gap: 10px; }}
    .metrics-grid .metric-card {{ padding: 1rem 1.1rem; }}
    .metrics-grid .metric-label {{ font-size: 0.62rem; }}
    .metrics-grid .metric-value {{ font-size: 1.25rem; }}
}}

/* ---- Status pills ---- */
.status-pill {{
    display: inline-block;
    padding: 3px 11px;
    border-radius: 999px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border: 1px solid transparent;
}}
.status-paid {{ background: rgba(16,185,129,0.15); color: {GREEN}; border-color: rgba(16,185,129,0.3); }}
.status-partial {{ background: rgba(245,158,11,0.15); color: {AMBER}; border-color: rgba(245,158,11,0.3); }}
.status-unpaid {{ background: rgba(244,63,94,0.15); color: {ROSE}; border-color: rgba(244,63,94,0.3); }}

/* ---- Inputs ---- */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
.stDateInput input {{
    background: var(--surface2) !important;
    border: 1px solid var(--border2) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
    padding: 0.6rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(0,194,168,0.15) !important;
    outline: none !important;
}}
.stTextInput label, .stNumberInput label, .stTextArea label,
.stSelectbox label, .stDateInput label, .stRadio label {{
    color: var(--muted) !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    font-family: 'JetBrains Mono', monospace !important;
}}
div[data-baseweb="select"] > div {{
    background: var(--surface2) !important;
    border: 1px solid var(--border2) !important;
    border-radius: 10px !important;
}}

/* ---- Buttons ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    background: linear-gradient(135deg, var(--teal), #00a896) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(0,194,168,0.2) !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0,194,168,0.35) !important;
    color: #000 !important;
}}
.stButton > button[kind="secondary"] {{
    background: var(--surface2) !important;
    color: var(--text) !important;
    box-shadow: none !important;
    border: 1px solid var(--border2) !important;
}}

/* ---- Tabs ---- */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--border) !important; }}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    background: transparent;
    border-radius: 10px 10px 0 0;
    color: var(--muted) !important;
    padding: 8px 16px !important;
}}
.stTabs [aria-selected="true"] {{
    background: var(--surface2) !important;
    color: var(--teal) !important;
    border-bottom: 2px solid var(--teal) !important;
}}

/* ---- Dataframes / forms ---- */
.stDataFrame {{ border-radius: 12px !important; overflow: hidden !important; }}
[data-testid="stForm"] {{
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
}}
.stSuccess, .stError, .stWarning, .stInfo {{ border-radius: 10px !important; }}

@keyframes fadeSlideUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.fade-in {{ animation: fadeSlideUp 0.45s ease forwards; }}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def hero_title(text: str, tagline: str = "", center: bool = False):
    """Gradient-clipped headline - use for the landing/login screen and
    the main dashboard title. Pass center=True (e.g. on the login
    screen) to center the text instead of the default left alignment."""
    align_style = ' style="text-align:center;"' if center else ""
    tagline_html = f'<div class="hero-tagline"{align_style}>{tagline}</div>' if tagline else ""
    st.markdown(
        f'<div class="fade-in hero-title"{align_style}>{text}</div>{tagline_html}',
        unsafe_allow_html=True,
    )


def graffiti_divider():
    """A thin gradient section divider. (Name kept from the previous
    theme so existing call sites don't need to change.)"""
    st.markdown('<div class="graffiti-divider"></div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = ""):
    """Single card via st.markdown - fine inside st.columns for
    desktop-oriented layouts. On mobile, prefer metrics_grid() below,
    since st.columns always collapses to one-per-row on narrow screens
    no matter how many columns you ask for."""
    st.markdown(_metric_card_html(label, value, sub), unsafe_allow_html=True)


def _metric_card_html(label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="metric-card fade-in">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f'</div>'
    )


def metrics_grid(items, columns: int = 2):
    """Render a list of (label, value, sub) tuples as a real CSS grid in
    a single st.markdown call. Unlike st.columns, this keeps N cards per
    row on phones instead of stacking to one per row - the grid is plain
    CSS, not a Streamlit layout primitive, so the browser's own narrow
    viewport rules never override it."""
    cards_html = "".join(_metric_card_html(label, value, sub) for label, value, sub in items)
    st.markdown(
        f'<div class="metrics-grid" style="grid-template-columns: repeat({columns}, 1fr);">{cards_html}</div>',
        unsafe_allow_html=True,
    )


def status_pill(status: str) -> str:
    cls = {"Paid": "status-paid", "Partial": "status-partial", "Unpaid": "status-unpaid"}.get(status, "status-unpaid")
    return f'<span class="status-pill {cls}">{status}</span>'


CURRENCY_SYMBOLS = {
    "USD": "$",
    "GBP": "£",
    "EUR": "€",
    "NGN": "₦",
}


def fmt_money(value, currency_code="USD"):
    """Format an amount WITH the currency it's actually denominated in.
    Never assume USD - a mislabeled currency here is how NGN 10,000
    ends up looking like $10,000."""
    symbol = CURRENCY_SYMBOLS.get(currency_code)
    try:
        if symbol:
            return f"{symbol}{value:,.2f}"
        return f"{value:,.2f} {currency_code}"
    except (TypeError, ValueError):
        return f"0.00 {currency_code}" if not symbol else f"{symbol}0.00"


def fmt_currency(value, symbol="$"):
    """Legacy formatter - kept only for call sites not yet migrated.
    Prefer fmt_money(value, currency_code) everywhere so the label
    always matches the actual currency of the amount."""
    try:
        return f"{symbol}{value:,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"
