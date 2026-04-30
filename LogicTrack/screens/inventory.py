"""Inventory screen — searchable product table with photos and actions."""
from __future__ import annotations

from typing import List

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle

from models import Item
from screens.icons import icon_for


class _RoundedImage(BoxLayout):
    def __init__(self, source: str, size: int = 56, radius: int = 10,
                 bg=(0.95, 0.96, 0.98, 1), **kw) -> None:
        super().__init__(size_hint=(None, None), size=(size, size), **kw)
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[radius])
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(Image(source=source, allow_stretch=True, keep_ratio=True))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class _PillButton(Button):
    """Rounded action button used inside table rows."""

    def __init__(self, text: str, color, **kw) -> None:
        super().__init__(text=text, **kw)
        self.background_normal = ""
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.font_size = 12
        self.bold = True
        self.size_hint_y = None
        self.height = 34
        self._fill = color
        with self.canvas.before:
            Color(*self._fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class _StockBadge(BoxLayout):
    def __init__(self, qty: int, threshold: int, **kw) -> None:
        super().__init__(size_hint=(None, None), size=(74, 28),
                         padding=(10, 4), **kw)
        app = App.get_running_app()
        if qty <= max(1, int(threshold) // 2):
            bg, fg = app.danger_bg, app.danger
        elif qty <= threshold:
            bg, fg = app.warning_bg, app.warning
        else:
            bg, fg = app.success_bg, app.success
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(Label(text=str(qty), color=fg, font_size=13, bold=True))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class InventoryScreen(Screen):
    pending_search: str = ""

    def on_pre_enter(self, *_) -> None:
        if self.pending_search:
            self.ids.search_input.text = self.pending_search
            self.pending_search = ""
        self.refresh()

    def refresh(self) -> None:
        app = App.get_running_app()
        search = self.ids.search_input.text.strip() or None
        category = self.ids.category_input.text.strip() or None
        threshold = int(app.low_stock_threshold)

        table = self.ids.items_table
        table.clear_widgets()

        # ----- Header row -----
        header = BoxLayout(size_hint_y=None, height=42, padding=(16, 0), spacing=12)
        with header.canvas.before:
            Color(*app.input_bg)
            hr = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *_: setattr(hr, "pos", header.pos),
                    size=lambda *_: setattr(hr, "size", header.size))
        header.add_widget(Widget(size_hint_x=None, width=56))  # image column
        col_specs = [("PRODUCT", 1, None), ("SKU", None, 130),
                     ("CATEGORY", None, 130), ("QTY", None, 90),
                     ("PRICE", None, 110), ("ACTIONS", None, 200)]
        for h, sx, w in col_specs:
            kw = dict(text=h, color=app.muted_text_color, font_size=11, bold=True,
                      halign="left", valign="middle")
            if w is not None:
                kw.update(size_hint_x=None, width=w)
                kw["text_size"] = (w, None)
            else:
                kw["size_hint_x"] = sx
            header.add_widget(Label(**kw))
        table.add_widget(header)

        items: List[Item] = app.db.list_items(search, category)
        if not items:
            empty = Label(
                text="No items match your filters.",
                color=app.muted_text_color, size_hint_y=None, height=120,
                halign="center", valign="middle",
            )
            empty.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
            table.add_widget(empty)
            table.add_widget(Widget())
            return

        for i, item in enumerate(items):
            row = BoxLayout(size_hint_y=None, height=84, padding=(16, 0), spacing=12)
            bg = app.row_alt_bg if i % 2 == 1 else app.card_bg
            with row.canvas.before:
                Color(*bg)
                rect = Rectangle(pos=row.pos, size=row.size)
                Color(*app.divider)
                divider = Rectangle(pos=(row.x, row.y), size=(row.width, 1))
            row.bind(
                pos=lambda inst, _v, _r=rect, _d=divider:
                    (setattr(_r, "pos", inst.pos), setattr(_d, "pos", (inst.x, inst.y))),
                size=lambda inst, _v, _r=rect, _d=divider:
                    (setattr(_r, "size", inst.size), setattr(_d, "size", (inst.width, 1))),
            )

            row.add_widget(_RoundedImage(icon_for(item.name, item.image_path),
                                         size=56, radius=10, bg=app.input_bg))

            # Product name + SKU stacked
            name_box = BoxLayout(orientation="vertical", spacing=2)
            name_lbl = Label(text=item.name, color=app.text_color, font_size=15,
                             bold=True, halign="left", valign="middle")
            name_lbl.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            name_box.add_widget(name_lbl)
            sub_lbl = Label(text=item.category or "—", color=app.muted_text_color,
                            font_size=12, halign="left", valign="middle")
            sub_lbl.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            name_box.add_widget(sub_lbl)
            row.add_widget(name_box)

            sku_lbl = Label(text=item.sku, color=app.text_color, font_size=13,
                            halign="left", valign="middle",
                            size_hint_x=None, width=130)
            sku_lbl.text_size = (130, None)
            row.add_widget(sku_lbl)

            cat_lbl = Label(text=item.category or "—", color=app.muted_text_color,
                            font_size=13, halign="left", valign="middle",
                            size_hint_x=None, width=130)
            cat_lbl.text_size = (130, None)
            row.add_widget(cat_lbl)

            qty_col = BoxLayout(size_hint_x=None, width=90, padding=(0, 28))
            qty_col.add_widget(_StockBadge(item.quantity, threshold))
            row.add_widget(qty_col)

            price_lbl = Label(text=f"${item.price:,.2f}", color=app.text_color,
                              font_size=14, bold=True, halign="left",
                              valign="middle", size_hint_x=None, width=110)
            price_lbl.text_size = (110, None)
            row.add_widget(price_lbl)

            actions = BoxLayout(size_hint_x=None, width=200, spacing=8,
                                padding=(0, 25))
            edit_btn = _PillButton("Edit", app.primary)
            edit_btn.bind(on_release=lambda _b, i=item.id: self.edit_item(i))
            del_btn = _PillButton("Delete", app.danger)
            del_btn.bind(on_release=lambda _b, i=item.id, n=item.name: self.confirm_delete(i, n))
            actions.add_widget(edit_btn)
            actions.add_widget(del_btn)
            row.add_widget(actions)

            table.add_widget(row)

        table.add_widget(Widget())

    def edit_item(self, item_id: int) -> None:
        App.get_running_app().editing_item_id = item_id
        self.manager.current = "edit_item"

    def confirm_delete(self, item_id: int, name: str) -> None:
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text=f'Delete "{name}"?\nThis cannot be undone.'))
        btns = BoxLayout(spacing=10, size_hint_y=None, height=40)
        popup = Popup(title="Confirm Delete", content=box,
                      size_hint=(None, None), size=(360, 180), auto_dismiss=False)

        def do_delete(_):
            App.get_running_app().db.delete_item(item_id)
            popup.dismiss()
            self.refresh()

        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_release=lambda _: popup.dismiss())
        delete_btn = Button(text="Delete", background_normal="",
                            background_color=(0.85, 0.10, 0.10, 1),
                            color=(1, 1, 1, 1))
        delete_btn.bind(on_release=do_delete)
        btns.add_widget(cancel_btn)
        btns.add_widget(delete_btn)
        box.add_widget(btns)
        popup.open()
