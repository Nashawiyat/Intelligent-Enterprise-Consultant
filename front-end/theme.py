"""
Shared theme configuration for ICA dashboard.
Provides colour palettes for light and dark modes.
"""


def get_colors(dark_mode: bool) -> dict:
    """Return the full colour palette for the given mode."""
    if dark_mode:
        BG = "#1e1e2e"
        BG2 = "#2a2a3c"
        CARD = "#2a2a3c"
        CARD_INNER = "#33334a"
        BORDER = "#3e3e56"
        TEXT = "#e0e0e0"
        TEXT2 = "#b0b0c0"
        ACCENT = "#66bb6a"
        ACCENT_BG = "#2e3d2e"
        SIDEBAR_BG = f"linear-gradient(180deg, {BG2} 0%, {BG} 100%)"
        TOPBAR_BG = BG2
        CHAT_ASSIST_BG = "#33334a"
        CHAT_USER_BG = "#2e3d2e"
        INPUT_BG = BG2
        HOVER_BG = "#3e3e56"
        PLOTLY_BG = CARD_INNER
        BORDER_STRONG = BORDER
        CHART_TEXT = "#cccccc"
        CHART_GRID = "#4a4a60"
        PANEL_SHADOW = "0 4px 16px rgba(0,0,0,0.3)"
        TOGGLE_BG = "#4a4a60"
        TOGGLE_CHECKED = "#ef5350"
    else:
        BG = "#f8f9fa"
        BG2 = "#ffffff"
        CARD = "#ffffff"
        CARD_INNER = "#f3f5f7"
        BORDER = "#d0d5da"
        BORDER_STRONG = "#2c2c2c"
        TEXT = "#111111"
        TEXT2 = "#333333"
        CHART_TEXT = "#111111"
        CHART_GRID = "#c0c5cc"
        ACCENT = "#2e7d32"
        ACCENT_BG = "#e8f5e9"
        SIDEBAR_BG = "#ffffff"
        TOPBAR_BG = "#ffffff"
        CHAT_ASSIST_BG = "#f0f2f5"
        CHAT_USER_BG = "#e8f5e9"
        INPUT_BG = "#ffffff"
        HOVER_BG = "#e8f5e9"
        PLOTLY_BG = "#ffffff"
        PANEL_SHADOW = "0 2px 8px rgba(0,0,0,0.08)"
        TOGGLE_BG = "#b0b5bb"
        TOGGLE_CHECKED = "#ef5350"

    return {
        "BG": BG, "BG2": BG2, "CARD": CARD, "CARD_INNER": CARD_INNER,
        "BORDER": BORDER, "BORDER_STRONG": BORDER_STRONG,
        "TEXT": TEXT, "TEXT2": TEXT2,
        "ACCENT": ACCENT, "ACCENT_BG": ACCENT_BG,
        "SIDEBAR_BG": SIDEBAR_BG, "TOPBAR_BG": TOPBAR_BG,
        "CHAT_ASSIST_BG": CHAT_ASSIST_BG, "CHAT_USER_BG": CHAT_USER_BG,
        "INPUT_BG": INPUT_BG, "HOVER_BG": HOVER_BG,
        "PLOTLY_BG": PLOTLY_BG,
        "CHART_TEXT": CHART_TEXT, "CHART_GRID": CHART_GRID,
        "PANEL_SHADOW": PANEL_SHADOW,
        "TOGGLE_BG": TOGGLE_BG, "TOGGLE_CHECKED": TOGGLE_CHECKED,
    }
