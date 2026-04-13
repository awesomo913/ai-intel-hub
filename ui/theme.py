"""Theme system - dark/light mode colors, fonts, and styling constants."""


def blend_color(hex_color: str, bg_hex: str = "#0f0f0f", alpha: float = 0.2) -> str:
    """Blend a hex color with a background at a given alpha (0-1).
    Replaces CSS-style alpha hex (#RRGGBBAA) which tkinter doesn't support."""
    hex_color = hex_color.lstrip("#")[:6]
    bg_hex = bg_hex.lstrip("#")[:6]
    r1, g1, b1 = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r2, g2, b2 = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
    r = int(r1 * alpha + r2 * (1 - alpha))
    g = int(g1 * alpha + g2 * (1 - alpha))
    b = int(b1 * alpha + b2 * (1 - alpha))
    return f"#{r:02x}{g:02x}{b:02x}"


def _cat_blend(color: str, bg: str = "#0f0f0f", alpha: float = 0.2) -> str:
    return blend_color(color, bg, alpha)


DARK = {
    "bg": "#0f0f0f",
    "bg_secondary": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_card_hover": "#1a2745",
    "bg_input": "#1e1e2e",
    "fg": "#e0e0e0",
    "fg_secondary": "#a0a0b0",
    "fg_muted": "#666680",
    "accent": "#6c63ff",
    "accent_hover": "#7c73ff",
    "accent_light": blend_color("#6c63ff", "#0f0f0f", 0.15),
    "success": "#00c853",
    "warning": "#ffa726",
    "error": "#ef5350",
    "info": "#42a5f5",
    "border": "#2a2a40",
    "sidebar_bg": "#0d0d1a",
    "sidebar_active": blend_color("#6c63ff", "#0d0d1a", 0.2),
    "tag_bg": blend_color("#6c63ff", "#0f0f0f", 0.2),
    "tag_fg": "#a8a0ff",
    "scrollbar": "#333350",
    "selection": blend_color("#6c63ff", "#0f0f0f", 0.25),
}

LIGHT = {
    "bg": "#f5f5f8",
    "bg_secondary": "#ffffff",
    "bg_card": "#ffffff",
    "bg_card_hover": "#f0f0f5",
    "bg_input": "#ffffff",
    "fg": "#1a1a2e",
    "fg_secondary": "#555570",
    "fg_muted": "#999999",
    "accent": "#6c63ff",
    "accent_hover": "#5b52ee",
    "accent_light": blend_color("#6c63ff", "#f5f5f8", 0.1),
    "success": "#2e7d32",
    "warning": "#ef6c00",
    "error": "#c62828",
    "info": "#1565c0",
    "border": "#e0e0e8",
    "sidebar_bg": "#eeeef5",
    "sidebar_active": blend_color("#6c63ff", "#eeeef5", 0.15),
    "tag_bg": blend_color("#6c63ff", "#f5f5f8", 0.15),
    "tag_fg": "#6c63ff",
    "scrollbar": "#ccccdd",
    "selection": blend_color("#6c63ff", "#f5f5f8", 0.2),
}

FONTS = {
    "heading_lg": ("Segoe UI", 22, "bold"),
    "heading": ("Segoe UI", 16, "bold"),
    "heading_sm": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", 13),
    "body_sm": ("Segoe UI", 11),
    "mono": ("Consolas", 12),
    "mono_sm": ("Consolas", 10),
    "button": ("Segoe UI", 12, "bold"),
    "tag": ("Segoe UI", 10, "bold"),
    "stat_number": ("Segoe UI", 28, "bold"),
    "stat_label": ("Segoe UI", 11),
}

# Category colors
CATEGORY_COLORS = {
    "AI Agents": "#6c63ff",
    "Vibe Coding": "#ff6b6b",
    "Local AI": "#51cf66",
    "AI Models": "#fcc419",
    "Breakthroughs": "#ff922b",
    "AI Business": "#20c997",
    "AI Tools": "#339af0",
    "Open Source AI": "#cc5de8",
    "AI News": "#868e96",
    "AI Research": "#f06595",
    "AI Companies": "#22b8cf",
    "General AI": "#adb5bd",
}


def get_theme(mode: str = "dark") -> dict:
    return DARK if mode == "dark" else LIGHT


def get_category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#6c63ff")
