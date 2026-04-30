"""Dashboard screen — KPI tiles, low-stock alerts, and recent restocks."""
from __future__ import annotations

from typing import List, Optional

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line

from models import Item, RestockSummary, items_total_value
from screens.icons import icon_for


class _RoundedImage(BoxLayout):
    """Square wrapper that clips an image into a rounded card."""

    def __init__(self, source: str, size: int = 72, radius: int = 10,
                 bg=(0.95, 0.96, 0.98, 1), **kw) -> None:
        super().__init__(size_hint=(None, None), size=(size, size), **kw)
        self._radius = radius
        self._bg = bg
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._sync, size=self._sync)
        self._img = Image(source=source, allow_stretch=True, keep_ratio=True)
        self.add_widget(self._img)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class _AlertCard(BoxLayout):
    """Soft-tinted card showing a low-stock product with photo + qty."""

    def __init__(self, name: str, qty: int, level: str, icon_path: str, **kw) -> None:
        super().__init__(orientation="vertical", padding=14, spacing=8, **kw)
        self.size_hint_x = None
        self.size_hint_y = None
        self.width = 220
        self.height = 180

        app = App.get_running_app()
        if level == "critical":
            tint = app.danger_bg
            border = app.danger
            badge_text = "CRITICAL"
            badge_color = app.danger
        else:
            tint = app.warning_bg
            border = app.warning
            badge_text = "LOW"
            badge_color = app.warning

        with self.canvas.before:
            Color(*tint)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[14])
            Color(*border)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, 14), width=1)
        self.bind(pos=self._sync, size=self._sync)

        head = BoxLayout(size_hint_y=None, height=64, spacing=10)
        head.add_widget(_RoundedImage(icon_path, size=64, radius=10, bg=app.card_bg))

        text_col = BoxLayout(orientation="vertical", spacing=2)
        text_col.add_widget(Label(
            text=badge_text, color=badge_color, font_size=11, bold=True,
            size_hint_y=None, height=16, halign="left", valign="middle",
            text_size=(140, None),
        ))
        text_col.add_widget(Label(
            text=name, color=app.text_color, font_size=18,
            bold=True, halign="left", valign="middle",
            text_size=(140, None),
        ))
        head.add_widget(text_col)
        self.add_widget(head)

        self.add_widget(Label(
            text=f"{qty} units left", color=app.muted_text_color,
            font_size=13, halign="left", valign="middle",
            size_hint_y=None, height=22,
            text_size=(self.width - 28, None),
        ))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, 14)


class _RestockRow(BoxLayout):
    """A single row in the recent-restocks table."""

    def __init__(self, name: str, date: Optional[str], qty: int,
                 icon_path: str, alt: bool = False, **kw) -> None:
        super().__init__(size_hint_y=None, height=70, padding=12, spacing=12, **kw)
        app = App.get_running_app()
        bg = app.row_alt_bg if alt else app.card_bg
        with self.canvas.before:
            Color(*bg)
            self._rect = Rectangle(pos=self.pos, size=self.size)
            Color(*app.divider)
            self._line = Rectangle(pos=(self.x, self.y), size=(self.width, 1))
        self.bind(pos=self._sync, size=self._sync)

        self.add_widget(_RoundedImage(icon_path, size=46, radius=8,
                                      bg=app.input_bg))
        self.add_widget(Label(
            text=name, color=app.text_color, font_size=14, bold=True,
            halign="left", valign="middle", text_size=(180, None),
        ))
        self.add_widget(Label(
            text=date or "—", color=app.muted_text_color, font_size=13,
            halign="left", valign="middle", text_size=(120, None),
        ))
        # Quantity pill
        pill = BoxLayout(size_hint_x=None, width=80, padding=(10, 6))
        with pill.canvas.before:
            Color(*app.success_bg)
            pill._rect = RoundedRectangle(pos=pill.pos, size=pill.size, radius=[10])
        pill.bind(pos=lambda *_: setattr(pill._rect, "pos", pill.pos),
                  size=lambda *_: setattr(pill._rect, "size", pill.size))
        pill.add_widget(Label(
            text=f"+{qty}", color=app.success, font_size=13, bold=True,
            halign="center", valign="middle",
        ))
        self.add_widget(pill)
        self.add_widget(Widget())

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.pos = (self.x, self.y)
        self._line.size = (self.width, 1)


class DashboardScreen(Screen):

    def on_pre_enter(self, *_) -> None:
        try:
            self.refresh()
        except Exception:
            import traceback
            traceback.print_exc()
            if "alerts_box" in self.ids:
                self.ids.alerts_box.clear_widgets()

    def refresh(self) -> None:
        app = App.get_running_app()
        threshold = int(app.low_stock_threshold)

        items: List[Item] = app.db.list_items()
        total = len(items)
        total_value = items_total_value(items)
        suppliers = len(app.db.list_suppliers())
        low_items: List[Item] = app.db.low_stock(threshold)

        self.ids.kpi_total.value = str(total)
        self.ids.kpi_low.value = str(len(low_items))
        self.ids.kpi_value.value = f"${total_value:,.2f}"
        self.ids.kpi_suppliers.value = str(suppliers)

        # ----- Alerts banner -----
        alerts_box = self.ids.alerts_box
        alerts_box.clear_widgets()
        self.ids.alerts_subtitle.text = (
            f"{len(low_items)} item(s) at or below {threshold} units"
            if low_items else "All stocked above threshold"
        )
        if not low_items:
            empty = Label(
                text="No low-stock alerts.",
                color=app.muted_text_color,
                size_hint_y=None, height=140,
                size_hint_x=None, width=240,
                halign="left", valign="middle",
            )
            empty.text_size = (240, 140)
            alerts_box.add_widget(empty)
        else:
            for item in low_items:
                level = "critical" if item.is_critical(threshold) else "warning"
                alerts_box.add_widget(
                    _AlertCard(name=item.name, qty=item.quantity, level=level,
                               icon_path=icon_for(item.name, item.image_path)))

        # ----- Recent restocks -----
        restocks = self.ids.restocks_box
        restocks.clear_widgets()

        # Header
        header = BoxLayout(size_hint_y=None, height=36, padding=12, spacing=12)
        with header.canvas.before:
            Color(*app.input_bg)
            r = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *_: setattr(r, "pos", header.pos),
                    size=lambda *_: setattr(r, "size", header.size))
        header.add_widget(Widget(size_hint_x=None, width=46))
        for h, width in (("Item", 180), ("Date", 120), ("Qty", 80)):
            header.add_widget(Label(
                text=h, color=app.muted_text_color, font_size=11, bold=True,
                halign="left", valign="middle", text_size=(width, None),
                size_hint_x=None if width != 180 else 1, width=width,
            ))
        header.add_widget(Widget())
        restocks.add_widget(header)

        rows: List[RestockSummary] = app.db.recent_restocks(limit=6)
        if not rows:
            empty = Label(
                text="No recent restocks recorded.",
                color=app.muted_text_color, size_hint_y=None, height=120,
                halign="center", valign="middle",
            )
            empty.text_size = (400, 120)
            restocks.add_widget(empty)
        else:
            # Build a quick lookup from name → image_path for icon resolution.
            name_to_image = {it.name: it.image_path for it in items}
            for i, summary in enumerate(rows):
                img_path = name_to_image.get(summary.name)
                restocks.add_widget(_RestockRow(
                    name=summary.name, date=summary.last_restock,
                    qty=summary.quantity,
                    icon_path=icon_for(summary.name, img_path), alt=(i % 2 == 1),
                ))

    def search_products(self, query: str) -> None:
        inv = self.manager.get_screen("inventory")
        inv.pending_search = query
        self.manager.current = "inventory"
