"""Mockup PT5 - Edit Item Page (Author: Hassan Issaka)."""
from __future__ import annotations

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

from models import Item
from screens.icons import icon_for


class EditItemScreen(Screen):

    def on_pre_enter(self, *_) -> None:
        app = App.get_running_app()
        item_id = app.editing_item_id
        if item_id is None:
            self.manager.current = "inventory"
            return
        item: Item | None = app.db.get_item(item_id)
        if not item:
            self.manager.current = "inventory"
            return

        self.ids.title_label.text = item.name
        self.ids.item_image.source = icon_for(item.name, item.image_path)
        self.ids.item_image.reload()
        self.ids.name_input.text = item.name
        self.ids.sku_input.text = item.sku
        self.ids.price_input.text = f"{item.price:.2f}"
        self.ids.qty_input.text = str(item.quantity)
        self.ids.category_input.text = item.category or ""
        self.ids.adjust_qty.text = "0"
        self.ids.reason_input.text = ""
        self.ids.error_label.text = ""

    # -------------------------------------------------------- stock adjustment
    def bump(self, delta: int) -> None:
        try:
            current = int(self.ids.adjust_qty.text or "0")
        except ValueError:
            current = 0
        self.ids.adjust_qty.text = str(current + delta)

    def record_transaction(self) -> None:
        app = App.get_running_app()
        try:
            change = int(self.ids.adjust_qty.text or "0")
        except ValueError:
            self.ids.error_label.text = "Adjustment must be an integer."
            return
        reason = self.ids.reason_input.text.strip()
        if not reason:
            self.ids.error_label.text = "Pick a reason (Sale / Restock / Damaged)."
            return
        if reason in ("Sale", "Damaged") and change > 0:
            change = -change
        app.db.adjust_stock(app.editing_item_id, change, reason)
        self.on_pre_enter()  # refresh shown values

    # ---------------------------------------------------------- save / delete
    def save_changes(self) -> None:
        app = App.get_running_app()
        try:
            price = float(self.ids.price_input.text)
            qty = int(self.ids.qty_input.text)
        except ValueError:
            self.ids.error_label.text = "Price must be a number, Qty an integer."
            return
        ok = app.db.update_item(
            app.editing_item_id,
            self.ids.name_input.text.strip(),
            self.ids.sku_input.text.strip(),
            price, qty,
            self.ids.category_input.text.strip(),
        )
        if not ok:
            self.ids.error_label.text = "Could not save changes (see logs)."
            return
        self.manager.current = "inventory"

    def confirm_delete(self) -> None:
        app = App.get_running_app()
        item: Item | None = app.db.get_item(app.editing_item_id)
        name = item.name if item else "this item"

        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text=f'Delete "{name}"?\nThis cannot be undone.'))
        btns = BoxLayout(spacing=10, size_hint_y=None, height=40)
        popup = Popup(title="Confirm Delete", content=box,
                      size_hint=(None, None), size=(360, 180), auto_dismiss=False)

        def do_delete(_):
            app.db.delete_item(app.editing_item_id)
            popup.dismiss()
            self.manager.current = "inventory"

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
