"""
LogicTrack Inventory Management System
Main application entry point.

Run with:  python main.py
Requires:  pip install -r requirements.txt
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty, AliasProperty

from database import Database
from models import Item, User
from style_manager import StyleManager
from screens.login import LoginScreen
from screens.dashboard import DashboardScreen
from screens.inventory import InventoryScreen
from screens.add_item import AddItemScreen
from screens.edit_item import EditItemScreen
from screens.suppliers import SuppliersScreen
from screens.reports import ReportsScreen
from screens.settings import SettingsScreen


# ---------------------------------------------------------------------------
# Logging — quiet but informative; library messages stay at WARNING.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("logictrack")


# ---------------------------------------------------------------------------
# Window — roomier defaults; the redesigned sidebar needs horizontal space.
# ---------------------------------------------------------------------------
Window.size = (1280, 800)
Window.minimum_width, Window.minimum_height = 1100, 720


# ---------------------------------------------------------------------------
# Optional Material Symbols font — registered if present so KV files can
# use the {icon: "..."} glyphs from style_manager.ICONS. Missing font is
# not fatal: the sidebar gracefully falls back to short text labels.
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
ICON_FONT_NAME = "MaterialIcons"
ICON_FONT_FILES = [
    os.path.join(HERE, "assets", "fonts", "MaterialSymbolsOutlined.ttf"),
    os.path.join(HERE, "assets", "fonts", "MaterialIcons-Regular.ttf"),
]
ICON_FONT_AVAILABLE = False
for _path in ICON_FONT_FILES:
    if os.path.isfile(_path):
        from kivy.core.text import LabelBase
        LabelBase.register(name=ICON_FONT_NAME, fn_regular=_path)
        ICON_FONT_AVAILABLE = True
        log.info("Registered Material icon font: %s", _path)
        break


# ---------------------------------------------------------------------------
# Load shared KV files. theme.kv must be first so subsequent screens can
# reference its widget rules.
# ---------------------------------------------------------------------------
KV_DIR = os.path.join(HERE, "kv")
for kv_file in [
    "theme.kv",
    "login.kv",
    "dashboard.kv",
    "inventory.kv",
    "add_item.kv",
    "edit_item.kv",
    "suppliers.kv",
    "reports.kv",
    "settings.kv",
]:
    Builder.load_file(os.path.join(KV_DIR, kv_file))


class LogicTrackApp(App):
    """Root app — owns the database, theme tokens, and global app state.

    Theme management lives in `style_manager.StyleManager`; this class
    just exposes its tokens as `AliasProperty`s so KV bindings update
    instantly when `theme` changes.
    """

    theme = StringProperty("Light")            # "Light" or "Dark"
    low_stock_threshold = NumericProperty(5)

    # ---- brand / accent palette (theme-independent; overwritten in build()
    # with the values from the active StyleManager).
    primary       = (0.345, 0.388, 0.910, 1)
    primary_hover = (0.275, 0.318, 0.792, 1)
    success       = (0.118, 0.580, 0.376, 1)
    warning       = (0.890, 0.557, 0.043, 1)
    danger        = (0.831, 0.231, 0.231, 1)
    info          = (0.122, 0.557, 0.792, 1)
    neutral_btn   = (0.949, 0.953, 0.965, 1)

    # ---- alias properties — read from the active StyleManager -----------
    def _get_page_bg(self):          return self.style.page_bg
    page_bg = AliasProperty(_get_page_bg, bind=("theme",))

    def _get_card_bg(self):          return self.style.card_bg
    card_bg = AliasProperty(_get_card_bg, bind=("theme",))

    def _get_card_border(self):      return self.style.card_border
    card_border = AliasProperty(_get_card_border, bind=("theme",))

    def _get_sidebar_bg(self):       return self.style.sidebar_bg
    sidebar_bg = AliasProperty(_get_sidebar_bg, bind=("theme",))

    def _get_sidebar_active(self):   return self.style.sidebar_active
    sidebar_active = AliasProperty(_get_sidebar_active, bind=("theme",))

    def _get_sidebar_hover(self):    return self.style.sidebar_hover
    sidebar_hover = AliasProperty(_get_sidebar_hover, bind=("theme",))

    def _get_sidebar_text(self):     return self.style.sidebar_text
    sidebar_text = AliasProperty(_get_sidebar_text, bind=("theme",))

    def _get_sidebar_active_text(self): return self.style.sidebar_active_text
    sidebar_active_text = AliasProperty(_get_sidebar_active_text, bind=("theme",))

    def _get_text_color(self):       return self.style.text_color
    text_color = AliasProperty(_get_text_color, bind=("theme",))

    def _get_muted_text_color(self): return self.style.muted_text_color
    muted_text_color = AliasProperty(_get_muted_text_color, bind=("theme",))

    def _get_input_bg(self):         return self.style.input_bg
    input_bg = AliasProperty(_get_input_bg, bind=("theme",))

    def _get_row_alt_bg(self):       return self.style.row_alt_bg
    row_alt_bg = AliasProperty(_get_row_alt_bg, bind=("theme",))

    def _get_divider(self):          return self.style.divider
    divider = AliasProperty(_get_divider, bind=("theme",))

    def _get_warning_bg(self):       return self.style.warning_bg
    warning_bg = AliasProperty(_get_warning_bg, bind=("theme",))

    def _get_danger_bg(self):        return self.style.danger_bg
    danger_bg = AliasProperty(_get_danger_bg, bind=("theme",))

    def _get_success_bg(self):       return self.style.success_bg
    success_bg = AliasProperty(_get_success_bg, bind=("theme",))

    def _get_info_bg(self):          return self.style.info_bg
    info_bg = AliasProperty(_get_info_bg, bind=("theme",))

    # ---- icon-font sentinel — KV reads this to decide between glyph
    # and ASCII fallback so the sidebar always renders something readable.
    def _get_icon_font(self):
        return ICON_FONT_NAME if ICON_FONT_AVAILABLE else "Roboto"
    icon_font = AliasProperty(_get_icon_font, bind=())

    # ----------------------------------------------------------- build
    def build(self):
        self.title = "LogicTrack — Inventory Management"
        self.style = StyleManager(theme=self.theme)
        # Mirror brand constants on the App so KV bindings keep working.
        self.primary       = self.style.primary
        self.primary_hover = self.style.primary_hover
        self.success       = self.style.success
        self.warning       = self.style.warning
        self.danger        = self.style.danger
        self.info          = self.style.info
        self.neutral_btn   = self.style.neutral_btn

        try:
            self.db = Database()
        except Exception:
            log.exception("Could not initialise the database")
            raise

        # Global app state — accessible from any screen via App.get_running_app()
        self.current_user: Optional[User] = None
        self.date_format = "MM/DD/YYYY"
        self.time_format = "12-hour"
        self.editing_item_id: Optional[int] = None

        self.bind(theme=self._on_theme_change)
        self._apply_window_bg()

        sm = ScreenManager(transition=FadeTransition(duration=0.18))
        sm.add_widget(LoginScreen(name="login"))
        sm.add_widget(DashboardScreen(name="dashboard"))
        sm.add_widget(InventoryScreen(name="inventory"))
        sm.add_widget(AddItemScreen(name="add_item"))
        sm.add_widget(EditItemScreen(name="edit_item"))
        sm.add_widget(SuppliersScreen(name="suppliers"))
        sm.add_widget(ReportsScreen(name="reports"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    # ----------------------------------------------------------- theme
    def _apply_window_bg(self) -> None:
        Window.clearcolor = self.style.page_bg

    def _on_theme_change(self, *_):
        # Keep StyleManager and App in sync, then refresh chrome.
        self.style.theme = self.theme
        self.neutral_btn = self.style.neutral_btn
        self._apply_window_bg()
        # Force every alias to recompute by nudging dependent properties.
        # Each AliasProperty above binds on `theme`, so changing it (which
        # we just did) already triggered the recompute.
        if self.root and self.root.current_screen:
            screen = self.root.current_screen
            for fn in ("refresh", "refresh_users"):
                if hasattr(screen, fn):
                    try:
                        getattr(screen, fn)()
                    except Exception:
                        log.exception("Refreshing %s failed", screen.name)


if __name__ == "__main__":
    LogicTrackApp().run()
