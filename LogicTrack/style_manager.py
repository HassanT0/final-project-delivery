"""
Theme management for LogicTrack — the *Modern Enterprise* design system.

The palette below favours low-contrast, professional surfaces:

* Light mode uses near-white surfaces (#FAFBFC) on a soft canvas
  (#F5F6F8) and slate-grey ink (#1F2933) — the kind of restrained
  contrast Stripe / Linear / Notion target.
* Dark mode uses a desaturated navy (#0E1117) instead of pure black,
  with surface (#161B22) and border (#22272E) tuned to keep the panels
  feeling "elevated" instead of inky.

`StyleManager` is intentionally *not* a Kivy `App`: it is a plain,
EventDispatcher-backed object that owns the colour tokens. The root
`LogicTrackApp` instantiates one and re-exposes its tokens as
`AliasProperty` shims so KV bindings keep working unchanged.
"""
from __future__ import annotations

from typing import Tuple

from kivy.event import EventDispatcher
from kivy.properties import StringProperty


# Type alias for an RGBA tuple
RGBA = Tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# Brand / accent palette — refined for Modern Enterprise (theme-independent)
# ---------------------------------------------------------------------------
BRAND: dict[str, RGBA] = {
    # Indigo primary, slightly desaturated from the original #3B51E1
    "primary":       (0.345, 0.388, 0.910, 1),   # #5863E8
    "primary_hover": (0.275, 0.318, 0.792, 1),   # #4651CA
    "success":       (0.118, 0.580, 0.376, 1),   # #1E9460
    "warning":       (0.890, 0.557, 0.043, 1),   # #E38E0B
    "danger":        (0.831, 0.231, 0.231, 1),   # #D43B3B
    "info":          (0.122, 0.557, 0.792, 1),   # #1F8ECA
    "neutral_btn_light": (0.949, 0.953, 0.965, 1),
    "neutral_btn_dark":  (0.149, 0.176, 0.220, 1),
}


# ---------------------------------------------------------------------------
# Theme-specific tokens
# ---------------------------------------------------------------------------
LIGHT_TOKENS: dict[str, RGBA] = {
    "page_bg":          (0.961, 0.965, 0.973, 1),  # #F5F6F8
    "card_bg":          (0.980, 0.984, 0.992, 1),  # #FAFBFC
    "card_border":      (0.910, 0.918, 0.937, 1),  # #E8EAEF
    "sidebar_bg":       (0.106, 0.137, 0.196, 1),  # #1B2332 — slate
    "sidebar_active":   (0.345, 0.388, 0.910, 1),  # primary
    "sidebar_hover":    (1, 1, 1, 0.06),
    "sidebar_text":     (0.86, 0.89, 0.94, 1),
    "sidebar_active_text": (1, 1, 1, 1),
    "text_color":       (0.122, 0.149, 0.196, 1),  # #1F2632
    "muted_text_color": (0.435, 0.471, 0.522, 1),  # #6F7885
    "input_bg":         (0.969, 0.973, 0.980, 1),  # #F7F8FA
    "row_alt_bg":       (0.973, 0.976, 0.984, 1),  # #F8FAFC
    "divider":          (0.918, 0.925, 0.941, 1),  # #EAEDF1
    "warning_bg":       (1.000, 0.953, 0.871, 1),
    "danger_bg":        (0.996, 0.918, 0.918, 1),
    "success_bg":       (0.898, 0.965, 0.929, 1),
    "info_bg":          (0.870, 0.937, 0.984, 1),
}

DARK_TOKENS: dict[str, RGBA] = {
    "page_bg":          (0.055, 0.067, 0.090, 1),  # #0E1117
    "card_bg":          (0.086, 0.106, 0.133, 1),  # #161B22
    "card_border":      (0.133, 0.153, 0.180, 1),  # #22272E
    "sidebar_bg":       (0.043, 0.055, 0.078, 1),  # #0B0E14
    "sidebar_active":   (0.345, 0.388, 0.910, 1),
    "sidebar_hover":    (1, 1, 1, 0.05),
    "sidebar_text":     (0.69, 0.73, 0.79, 1),
    "sidebar_active_text": (1, 1, 1, 1),
    "text_color":       (0.918, 0.929, 0.945, 1),  # #EAEDF1
    "muted_text_color": (0.561, 0.604, 0.667, 1),  # #8F9AAA
    "input_bg":         (0.118, 0.137, 0.169, 1),  # #1E232B
    "row_alt_bg":       (0.067, 0.082, 0.106, 1),  # #11151B
    "divider":          (0.133, 0.153, 0.180, 1),
    "warning_bg":       (0.220, 0.169, 0.063, 1),
    "danger_bg":        (0.235, 0.075, 0.090, 1),
    "success_bg":       (0.063, 0.180, 0.137, 1),
    "info_bg":          (0.067, 0.137, 0.196, 1),
}


# ---------------------------------------------------------------------------
# StyleManager
# ---------------------------------------------------------------------------
class StyleManager(EventDispatcher):
    """Owns the active theme and exposes colour tokens as plain attributes.

    Use `.token(name)` to look up the active token, or read the brand
    constants (e.g. ``style.primary``) directly. Bind to ``theme`` to be
    notified when the user toggles light / dark.
    """

    theme: str = StringProperty("Light")

    # Brand constants (theme-independent)
    primary: RGBA = BRAND["primary"]
    primary_hover: RGBA = BRAND["primary_hover"]
    success: RGBA = BRAND["success"]
    warning: RGBA = BRAND["warning"]
    danger: RGBA = BRAND["danger"]
    info: RGBA = BRAND["info"]

    def __init__(self, theme: str = "Light", **kwargs) -> None:
        super().__init__(**kwargs)
        self.theme = theme

    # ----------------------------------------------------------- tokens
    def tokens(self) -> dict[str, RGBA]:
        return DARK_TOKENS if self.theme == "Dark" else LIGHT_TOKENS

    def token(self, name: str) -> RGBA:
        try:
            return self.tokens()[name]
        except KeyError:
            return self.tokens().get("text_color", (0, 0, 0, 1))

    # ----------------------------------------------------------- accents
    @property
    def neutral_btn(self) -> RGBA:
        return BRAND["neutral_btn_dark"] if self.theme == "Dark" \
            else BRAND["neutral_btn_light"]

    # ----------------------------------------------------------- proxies
    # Each property below mirrors the matching token name on the active
    # theme, so KV bindings (e.g. `app.page_bg`) continue to update
    # automatically when the user toggles `theme`.
    @property
    def page_bg(self) -> RGBA: return self.token("page_bg")
    @property
    def card_bg(self) -> RGBA: return self.token("card_bg")
    @property
    def card_border(self) -> RGBA: return self.token("card_border")
    @property
    def sidebar_bg(self) -> RGBA: return self.token("sidebar_bg")
    @property
    def sidebar_active(self) -> RGBA: return self.token("sidebar_active")
    @property
    def sidebar_hover(self) -> RGBA: return self.token("sidebar_hover")
    @property
    def sidebar_text(self) -> RGBA: return self.token("sidebar_text")
    @property
    def sidebar_active_text(self) -> RGBA: return self.token("sidebar_active_text")
    @property
    def text_color(self) -> RGBA: return self.token("text_color")
    @property
    def muted_text_color(self) -> RGBA: return self.token("muted_text_color")
    @property
    def input_bg(self) -> RGBA: return self.token("input_bg")
    @property
    def row_alt_bg(self) -> RGBA: return self.token("row_alt_bg")
    @property
    def divider(self) -> RGBA: return self.token("divider")
    @property
    def warning_bg(self) -> RGBA: return self.token("warning_bg")
    @property
    def danger_bg(self) -> RGBA: return self.token("danger_bg")
    @property
    def success_bg(self) -> RGBA: return self.token("success_bg")
    @property
    def info_bg(self) -> RGBA: return self.token("info_bg")

    def toggle(self) -> None:
        self.theme = "Dark" if self.theme == "Light" else "Light"


# ---------------------------------------------------------------------------
# Material Design icon glyphs used in the redesigned sidebar.
#
# These are PUA codepoints from the Material Symbols Outlined font. They
# render cleanly when the font is loaded (see main.py / fonts/), and fall
# back to the small ASCII labels in `ICON_FALLBACKS` otherwise so the UI
# never shows tofu boxes.
# ---------------------------------------------------------------------------
ICONS: dict[str, str] = {
    "dashboard": "",   # dashboard
    "inventory": "",   # inventory_2
    "suppliers": "",   # local_shipping (truck)
    "reports":   "",   # bar_chart
    "settings":  "",   # settings (gear)
    "logout":    "",   # logout
    "search":    "",   # search
    "add":       "",   # add
    "edit":      "",   # edit
    "delete":    "",   # delete
    "warning":   "",   # warning
    "check":     "",   # done
    "user":      "",   # person
}

# ASCII fallbacks that look reasonable without the icon font installed.
ICON_FALLBACKS: dict[str, str] = {
    "dashboard": "[]",
    "inventory": "[#]",
    "suppliers": ">>",
    "reports":   "II",
    "settings":  "*",
    "logout":    "->",
    "search":    "Q",
    "add":       "+",
    "edit":      "/",
    "delete":    "x",
    "warning":   "!",
    "check":     "v",
    "user":      "@",
}


def icon(name: str, fallback: bool = False) -> str:
    """Return the glyph for the named icon (or a safe fallback)."""
    if fallback:
        return ICON_FALLBACKS.get(name, "•")
    return ICONS.get(name, "•")


__all__ = ["StyleManager", "BRAND", "LIGHT_TOKENS", "DARK_TOKENS",
           "ICONS", "ICON_FALLBACKS", "icon"]
