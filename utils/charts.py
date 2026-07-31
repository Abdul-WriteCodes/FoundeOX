"""
Premium chart styling via ECharts (streamlit-echarts), replacing the
default Plotly look with gradient fills, rounded bars, smooth area
curves, and a cohesive color palette.

Every function here returns a plain options dict - pass it straight to
st_echarts(options=..., height=...). No custom JS formatters are used
(keeps this robust across environments); currency/units are communicated
through axis names and chart titles instead, in plain text.
"""

# Matches utils/styling.py's teal/violet/amber accent system so charts
# feel like part of the same dashboard, not a bolted-on default theme.
PALETTE = ["#00C2A8", "#7B6CF6", "#F59E0B", "#F43F5E", "#10B981", "#38bdf8", "#f472b6", "#a3e635"]

TEXT_COLOR = "#94a3b8"
GRID_LINE_COLOR = "rgba(148, 163, 184, 0.12)"
FONT_FAMILY = "'Outfit', 'Inter', system-ui, sans-serif"


def _gradient(color_from, color_to, vertical=True):
    return {
        "type": "linear",
        "x": 0, "y": 0,
        "x2": 0 if vertical else 1,
        "y2": 1 if vertical else 0,
        "colorStops": [
            {"offset": 0, "color": color_from},
            {"offset": 1, "color": color_to},
        ],
    }


def _base_text_style():
    return {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY}


def donut_chart(names, values, unit_label="", height="360px", colors=None):
    """A refined donut with a soft glow border between segments and a
    clean percentage/name label — used for revenue-by-stream/product."""
    palette = colors or PALETTE
    data = [{"name": n, "value": v} for n, v in zip(names, values)]
    tooltip_formatter = "{b}: {c} ({d}%)" if not unit_label else "{b}: {c} " + unit_label + " ({d}%)"
    return {
        "backgroundColor": "transparent",
        "color": palette,
        "tooltip": {
            "trigger": "item",
            "formatter": tooltip_formatter,
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)",
            "borderWidth": 0,
        },
        "legend": {
            "orient": "horizontal", "bottom": 0,
            "textStyle": _base_text_style(),
            "itemGap": 16, "icon": "circle",
        },
        "series": [{
            "type": "pie",
            "radius": ["48%", "76%"],
            "center": ["50%", "45%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 10,
                "borderColor": "rgba(15, 23, 42, 0)",
                "borderWidth": 3,
            },
            "label": {
                "show": True,
                "formatter": "{b}\n{d}%",
                "color": TEXT_COLOR,
                "fontFamily": FONT_FAMILY,
                "fontSize": 12,
            },
            "labelLine": {"length": 10, "length2": 8, "lineStyle": {"color": GRID_LINE_COLOR}},
            "emphasis": {
                "scaleSize": 6,
                "itemStyle": {"shadowBlur": 20, "shadowColor": "rgba(99, 102, 241, 0.5)"},
            },
            "data": data,
        }],
    }


def bar_chart(categories, values, axis_name="", height="340px", color_from=None, color_to=None):
    """A single-series bar chart with a vertical gradient fill and
    rounded top corners."""
    color_from = color_from or PALETTE[0]
    color_to = color_to or PALETTE[1]
    return {
        "backgroundColor": "transparent",
        "grid": {"left": "8%", "right": "5%", "top": "10%", "bottom": "12%", "containLabel": True},
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)",
            "borderWidth": 0,
        },
        "xAxis": {
            "type": "category", "data": categories,
            "axisLine": {"lineStyle": {"color": GRID_LINE_COLOR}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value", "name": axis_name,
            "nameTextStyle": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "splitLine": {"lineStyle": {"color": GRID_LINE_COLOR, "type": "dashed"}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
        },
        "series": [{
            "type": "bar",
            "data": values,
            "barMaxWidth": 42,
            "itemStyle": {
                "borderRadius": [8, 8, 0, 0],
                "color": _gradient(color_from, color_to),
            },
            "emphasis": {"itemStyle": {"color": _gradient(color_to, color_from)}},
        }],
    }


def stacked_bar_chart(categories, series_data: dict, axis_name="", height="380px", colors=None):
    """series_data: {series_name: [values aligned to categories]}. Used
    for revenue-by-stream-by-month."""
    palette = colors or PALETTE
    names = list(series_data.keys())
    series = []
    for i, (name, values) in enumerate(series_data.items()):
        is_top = (i == len(names) - 1)
        c = palette[i % len(palette)]
        item_style = {
            "borderRadius": [6, 6, 0, 0] if is_top else 0,
            "color": _gradient(c, c + "AA") if is_top else c,
        }
        series.append({
            "name": name,
            "type": "bar",
            "stack": "total",
            "data": values,
            "barMaxWidth": 42,
            "itemStyle": item_style,
            "label": {
                "show": True,
                "position": "inside",
                "color": "#0f172a",
                "fontFamily": FONT_FAMILY,
                "fontSize": 11,
                "fontWeight": 600,
                # "{c}" is the raw value for this data point. ECharts
                # auto-hides the label if the segment is too thin to fit
                # the text, so tiny slivers just show nothing rather than
                # overflowing into neighboring segments.
                "formatter": "{c}",
            },
            "labelLayout": {"hideOverlap": True},
        })
    return {
        "backgroundColor": "transparent",
        "color": palette,
        "grid": {"left": "8%", "right": "5%", "top": "18%", "bottom": "14%", "containLabel": True},
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)", "borderWidth": 0,
        },
        "legend": {"top": 0, "textStyle": _base_text_style(), "icon": "circle", "itemGap": 16},
        "xAxis": {
            "type": "category", "data": categories,
            "axisLine": {"lineStyle": {"color": GRID_LINE_COLOR}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value", "name": axis_name,
            "nameTextStyle": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "splitLine": {"lineStyle": {"color": GRID_LINE_COLOR, "type": "dashed"}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
        },
        "series": series,
    }


def multi_line_area_chart(categories, series_data: dict, axis_name="", height="360px", colors=None):
    """series_data: {series_name: [values]}. Smooth lines with a soft
    gradient area fill underneath — used for the profit trend
    (revenue / expense / profit)."""
    palette = colors or PALETTE
    series = []
    for i, (name, values) in enumerate(series_data.items()):
        c = palette[i % len(palette)]
        series.append({
            "name": name,
            "type": "line",
            "smooth": True,
            "symbol": "circle",
            "symbolSize": 6,
            "showSymbol": False,
            "lineStyle": {"width": 3, "color": c},
            "itemStyle": {"color": c},
            "areaStyle": {"color": _gradient(c + "55", c + "00")},
            "emphasis": {"focus": "series"},
            "data": values,
        })
    return {
        "backgroundColor": "transparent",
        "color": palette,
        "grid": {"left": "8%", "right": "5%", "top": "18%", "bottom": "14%", "containLabel": True},
        "tooltip": {
            "trigger": "axis",
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)", "borderWidth": 0,
        },
        "legend": {"top": 0, "textStyle": _base_text_style(), "icon": "circle", "itemGap": 16},
        "xAxis": {
            "type": "category", "data": categories, "boundaryGap": False,
            "axisLine": {"lineStyle": {"color": GRID_LINE_COLOR}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value", "name": axis_name,
            "nameTextStyle": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "splitLine": {"lineStyle": {"color": GRID_LINE_COLOR, "type": "dashed"}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
        },
        "series": series,
    }


def horizontal_bar_chart(categories, values, axis_name="", height="340px", color_from=None, color_to=None):
    """Horizontal bar with rounded right-side corners - used for
    'outstanding receivables by client' style rankings. Categories are
    reversed so the largest value ends up on top."""
    color_from = color_from or PALETTE[2]
    color_to = color_to or PALETTE[3]
    cats = list(reversed(categories))
    vals = list(reversed(values))
    return {
        "backgroundColor": "transparent",
        "grid": {"left": "2%", "right": "8%", "top": "5%", "bottom": "8%", "containLabel": True},
        "tooltip": {
            "trigger": "axis", "axisPointer": {"type": "shadow"},
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)", "borderWidth": 0,
        },
        "xAxis": {
            "type": "value", "name": axis_name,
            "nameTextStyle": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "splitLine": {"lineStyle": {"color": GRID_LINE_COLOR, "type": "dashed"}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
        },
        "yAxis": {
            "type": "category", "data": cats,
            "axisLine": {"lineStyle": {"color": GRID_LINE_COLOR}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "axisTick": {"show": False},
        },
        "series": [{
            "type": "bar",
            "data": vals,
            "barMaxWidth": 24,
            "itemStyle": {
                "borderRadius": [0, 8, 8, 0],
                "color": _gradient(color_from, color_to, vertical=False),
            },
        }],
    }


def area_growth_chart(categories, values, axis_name="", height="320px", color=None):
    """A single smooth cumulative-growth area chart with a strong
    gradient fade - used for the 'Revenue Growth' cumulative chart."""
    c = color or PALETTE[0]
    return {
        "backgroundColor": "transparent",
        "grid": {"left": "8%", "right": "5%", "top": "10%", "bottom": "12%", "containLabel": True},
        "tooltip": {
            "trigger": "axis",
            "textStyle": _base_text_style(),
            "backgroundColor": "rgba(15, 23, 42, 0.92)", "borderWidth": 0,
        },
        "xAxis": {
            "type": "category", "data": categories, "boundaryGap": False,
            "axisLine": {"lineStyle": {"color": GRID_LINE_COLOR}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "value", "name": axis_name,
            "nameTextStyle": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
            "splitLine": {"lineStyle": {"color": GRID_LINE_COLOR, "type": "dashed"}},
            "axisLabel": {"color": TEXT_COLOR, "fontFamily": FONT_FAMILY},
        },
        "series": [{
            "type": "line",
            "smooth": True,
            "showSymbol": False,
            "lineStyle": {"width": 3, "color": c},
            "areaStyle": {"color": _gradient(c + "70", c + "05")},
            "data": values,
        }],
    }
