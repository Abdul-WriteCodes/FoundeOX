"""
Visual identity: a full graffiti/street-art theme, applied globally via
one injected <style> block so every page (dashboard + all pages/) picks
it up automatically through inject_css().

Design choices, so future edits stay consistent:
- Display font "Bangers" for titles/headers (bold, spray-paint energy).
- "Permanent Marker" for labels/accents (handwritten marker feel).
- A dark "wall" background with soft neon overspray blobs in the
  corners, not a busy repeating texture - keeps numbers legible.
- One consistent neon palette (hot pink / electric cyan / acid yellow /
  orange) reused across cards, tabs, buttons, and status pills so it
  reads as one deliberate style, not random color noise.
- CSS targets only stable, well-documented Streamlit hooks (.stApp,
  .stButton>button, [data-baseweb="tab"], plain h1/h2/h3, and our own
  custom classes) rather than deep internal testids that change between
  Streamlit versions.
"""

import streamlit as st

NEON_PINK = "#ff2e88"
NEON_CYAN = "#00e5ff"
NEON_YELLOW = "#d4ff00"
NEON_ORANGE = "#ff6a00"
INK = "#0b0b12"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Permanent+Marker&family=Inter:wght@400;600;700&display=swap');

/* ---- Wall background: dark base + soft neon overspray in corners ---- */
.stApp {{
    background-color: {INK};
    background-image:
        radial-gradient(circle at 8% 12%, rgba(255,46,136,0.20), transparent 40%),
        radial-gradient(circle at 92% 18%, rgba(0,229,255,0.16), transparent 38%),
        radial-gradient(circle at 15% 90%, rgba(212,255,0,0.10), transparent 35%),
        radial-gradient(circle at 88% 85%, rgba(255,106,0,0.14), transparent 38%),
        repeating-linear-gradient(135deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 2px, transparent 2px, transparent 6px);
}}

h1, h2, h3 {{
    font-family: 'Bangers', 'Inter', sans-serif !important;
    letter-spacing: 0.03em;
    color: #f5f5f7 !important;
}}

/* ---- Hero title (landing + dashboard) ---- */
.hero-title {{
    font-family: 'Bangers', sans-serif;
    font-size: 3.2rem;
    line-height: 1.05;
    color: {NEON_YELLOW};
    text-shadow:
        3px 3px 0 {NEON_PINK},
        6px 6px 0 rgba(0,0,0,0.55),
        0 0 30px rgba(212,255,0,0.35);
    transform: rotate(-1.5deg);
    margin-bottom: 0;
}}
@media (max-width: 480px) {{
    .hero-title {{ font-size: 2.1rem; }}
}}
.hero-tagline {{
    font-family: 'Permanent Marker', cursive;
    color: {NEON_CYAN};
    font-size: 1.05rem;
    margin-top: 6px;
    transform: rotate(-0.5deg);
}}
.hero-underline {{ margin: 6px 0 18px 0; }}

/* ---- Spray-stroke divider (use graffiti_divider() instead of st.divider) ---- */
.graffiti-divider {{ margin: 22px 0; }}

/* ---- Metric / sticker cards ---- */
.metric-card {{
    background: linear-gradient(160deg, #1b1225 0%, #120b18 100%);
    border: 2.5px solid {NEON_PINK};
    border-radius: 14px 5px 16px 6px;
    padding: 16px 18px;
    box-shadow: 4px 4px 0 rgba(0,0,0,0.55), 0 0 18px rgba(255,46,136,0.15);
    transform: rotate(-0.6deg);
    transition: transform 0.15s ease;
}}
.metrics-grid > .metric-card:nth-child(3n+2) {{
    border-color: {NEON_CYAN};
    box-shadow: 4px 4px 0 rgba(0,0,0,0.55), 0 0 18px rgba(0,229,255,0.15);
    transform: rotate(0.7deg);
}}
.metrics-grid > .metric-card:nth-child(3n+3) {{
    border-color: {NEON_YELLOW};
    box-shadow: 4px 4px 0 rgba(0,0,0,0.55), 0 0 18px rgba(212,255,0,0.15);
    transform: rotate(-0.3deg);
}}
.metric-label {{
    font-family: 'Permanent Marker', cursive;
    font-size: 0.72rem;
    color: #c9c9d6;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 6px;
}}
.metric-value {{
    font-family: 'Bangers', sans-serif;
    font-size: 1.7rem;
    color: #ffffff;
    letter-spacing: 0.02em;
}}
.metric-sub {{
    font-size: 0.76rem;
    color: #9ca3af;
    margin-top: 2px;
}}
.metrics-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-bottom: 14px;
}}
@media (max-width: 480px) {{
    .metrics-grid {{ gap: 10px; }}
    .metrics-grid .metric-card {{ padding: 12px 14px; }}
    .metrics-grid .metric-label {{ font-size: 0.65rem; }}
    .metrics-grid .metric-value {{ font-size: 1.3rem; }}
}}

/* ---- Status pills as spray-stamped tags ---- */
.status-pill {{
    display: inline-block;
    padding: 3px 12px;
    border-radius: 999px 6px 999px 6px;
    font-family: 'Permanent Marker', cursive;
    font-size: 0.72rem;
    letter-spacing: 0.02em;
    border: 2px solid #000;
    transform: rotate(-2deg);
}}
.status-paid {{ background: {NEON_YELLOW}; color: #12310c; }}
.status-partial {{ background: {NEON_ORANGE}; color: #2a1400; }}
.status-unpaid {{ background: {NEON_PINK}; color: #2a0016; }}

/* ---- Buttons: stencil / sticker style ---- */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    font-family: 'Bangers', sans-serif !important;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    background: linear-gradient(135deg, {NEON_PINK}, {NEON_ORANGE}) !important;
    color: #0b0b12 !important;
    border: 2.5px solid #000 !important;
    border-radius: 10px 3px 10px 3px !important;
    box-shadow: 3px 3px 0 rgba(0,0,0,0.7) !important;
    transition: transform 0.1s ease, box-shadow 0.1s ease !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    transform: translate(-1px, -1px);
    box-shadow: 5px 5px 0 rgba(0,0,0,0.7) !important;
    color: #0b0b12 !important;
}}
.stButton > button:active, .stFormSubmitButton > button:active {{
    transform: translate(2px, 2px);
    box-shadow: 1px 1px 0 rgba(0,0,0,0.7) !important;
}}

/* ---- Tabs: sticker tags ---- */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: none !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'Permanent Marker', cursive;
    background: #1b1225;
    border: 2px solid {NEON_CYAN};
    border-radius: 10px 10px 0 0;
    color: #d8d8e2 !important;
    padding: 8px 16px !important;
}}
.stTabs [aria-selected="true"] {{
    background: {NEON_CYAN} !important;
    color: #0b0b12 !important;
    box-shadow: 0 0 16px rgba(0,229,255,0.5);
}}

/* ---- Inputs ---- */
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {{
    background-color: #17101f !important;
    color: #f0f0f5 !important;
    border: 2px solid #3a2f45 !important;
    border-radius: 8px !important;
}}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {{
    border-color: {NEON_CYAN} !important;
    box-shadow: 0 0 10px rgba(0,229,255,0.35) !important;
}}
div[data-baseweb="select"] > div {{
    background-color: #17101f !important;
    border: 2px solid #3a2f45 !important;
    border-radius: 8px !important;
}}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


_SPRAY_UNDERLINE_SVG = f"""
<svg viewBox="0 0 400 26" preserveAspectRatio="none" style="width:100%; max-width:420px; height:22px; display:block;">
    <path d="M0,14 Q50,4 100,13 T200,12 T300,14 T400,11" stroke="{NEON_PINK}" stroke-width="5" fill="none" stroke-linecap="round"/>
    <circle cx="55" cy="20" r="3.5" fill="{NEON_PINK}"/>
    <circle cx="170" cy="21" r="2.5" fill="{NEON_CYAN}"/>
    <circle cx="240" cy="19" r="4" fill="{NEON_YELLOW}"/>
    <circle cx="330" cy="20" r="3" fill="{NEON_ORANGE}"/>
</svg>
"""


def hero_title(text: str, tagline: str = ""):
    """Big spray-paint style title with a drip/spray underline - use for
    the landing/login screen and the main dashboard title."""
    tagline_html = f'<div class="hero-tagline">{tagline}</div>' if tagline else ""
    st.markdown(
        f'<div class="hero-title">{text}</div>'
        f'<div class="hero-underline">{_SPRAY_UNDERLINE_SVG}</div>'
        f'{tagline_html}',
        unsafe_allow_html=True,
    )


def graffiti_divider():
    """A spray-stroke divider - use instead of st.divider() for a
    consistent graffiti feel between sections."""
    st.markdown(f'<div class="graffiti-divider">{_SPRAY_UNDERLINE_SVG}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, sub: str = ""):
    """Single card via st.markdown - fine inside st.columns for
    desktop-oriented layouts. On mobile, prefer metrics_grid() below,
    since st.columns always collapses to one-per-row on narrow screens
    no matter how many columns you ask for."""
    st.markdown(_metric_card_html(label, value, sub), unsafe_allow_html=True)


def _metric_card_html(label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="metric-card">'
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
