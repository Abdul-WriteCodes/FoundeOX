"""Shared visual polish: CSS injection and small reusable components."""

import streamlit as st

CUSTOM_CSS = """
<style>
.metric-card {
    background: #ffffff;
    border: 1px solid #e6e8eb;
    border-radius: 14px;
    padding: 18px 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.metric-label {
    font-size: 0.8rem;
    color: #6b7280;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #111827;
}
.metric-sub {
    font-size: 0.78rem;
    color: #9ca3af;
    margin-top: 2px;
}
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 12px;
}
@media (max-width: 480px) {
    .metrics-grid { gap: 8px; }
    .metrics-grid .metric-card { padding: 12px 14px; }
    .metrics-grid .metric-label { font-size: 0.68rem; }
    .metrics-grid .metric-value { font-size: 1.15rem; }
}
.status-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.status-paid { background: #dcfce7; color: #166534; }
.status-partial { background: #fef9c3; color: #854d0e; }
.status-unpaid { background: #fee2e2; color: #991b1b; }
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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
