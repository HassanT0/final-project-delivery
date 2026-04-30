"""Add Item screen — create a new product with details and an image.

Adds real-time validation of the SKU field (duplicates are flagged in
the danger tone) and surfaces save failures via a themed Toast notice
instead of writing to the console.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView

from screens.icons import icon_for


log = logging.getLogger("logictrack.add_item")


SKU_RE = re.compile(r"^[A-Za-z0-9_\-]{2,32}$")


class AddItemScreen(Screen):

    def on_pre_enter(self, *_) -> None:
        for k in ("name_input", "sku_input", "price_input",
                  "qty_input", "category_input"):
            self.ids[k].text = ""
        self.ids.image_path_label.text = "No image selected"
        self.ids.preview_image.source = icon_for("", None)
        self.ids.preview_image.reload()
        self.ids.error_label.text = ""
        if "toast" in self.ids:
            self.ids.toast.visible = False

    # -------------------------------------------------------- toast helpers
    def _show_toast(self, message: str, tone: str = "danger") -> None:
        if "toast" not in self.ids:
            log.warning("Toast widget missing; message: %s", message)
            return
        app = App.get_running_app()
        self.ids.toast.message = message
        self.ids.toast.tone = getattr(app, tone, app.danger)
        self.ids.toast.visible = True
        Clock.unschedule(self._hide_toast)
        Clock.schedule_once(self._hide_toast, 4.5)

    def _hide_toast(self, *_) -> None:
        if "toast" in self.ids:
            self.ids.toast.visible = False

    # ----------------------------------------------------- live validation
    def validate_sku(self, value: str) -> None:
        """Hot-loop validator: flag bad format / duplicate SKUs."""
        value = value.strip()
        if not value:
            self._hide_toast()
            return
        if not SKU_RE.match(value):
            self._show_toast(
                "SKU must be 2–32 chars (letters, digits, dash, underscore)."
            )
            return
        try:
            app = App.get_running_app()
            if app.db.sku_exists(value):
                self._show_toast(f"SKU '{value}' is already in use.")
                return
        except Exception:
            log.exception("sku_exists check failed")
        self._hide_toast()

    # ------------------------------------------------------------ image
    def open_image_chooser(self) -> None:
        chooser = FileChooserIconView(filters=["*.png", "*.jpg", "*.jpeg"])
        popup = Popup(title="Select item image", content=chooser,
                      size_hint=(0.9, 0.9))

        def on_select(_inst, selection, _touch=None):
            if selection:
                self.ids.image_path_label.text = selection[0]
                self.ids.preview_image.source = selection[0]
                self.ids.preview_image.reload()
                popup.dismiss()

        chooser.bind(on_submit=on_select)
        popup.open()

    # ------------------------------------------------------------- save
    def save_item(self) -> None:
        ids = self.ids
        name = ids.name_input.text.strip()
        sku = ids.sku_input.text.strip()
        price_text = ids.price_input.text.strip()
        qty_text = ids.qty_input.text.strip()
        category = ids.category_input.text.strip()
        image_path: Optional[str] = ids.image_path_label.text
        if image_path == "No image selected":
            image_path = None

        if not name or not sku or not price_text or not qty_text:
            self._show_toast("All fields except image are required.")
            return

        if not SKU_RE.match(sku):
            self._show_toast("SKU must be 2–32 alphanumeric characters.")
            return

        try:
            price = float(price_text)
            qty = int(qty_text)
        except ValueError:
            self._show_toast("Price must be a number, Quantity an integer.")
            return
        if price < 0 or qty < 0:
            self._show_toast("Price and Quantity must be non-negative.")
            return

        app = App.get_running_app()
        # Final duplicate-SKU check just before insert (covers races where
        # someone added the SKU between live validation and submit).
        if app.db.sku_exists(sku):
            self._show_toast(f"SKU '{sku}' already exists.")
            return

        new_id = app.db.add_item(name, sku, price, qty, category, image_path)
        if new_id is None:
            self._show_toast("Could not save the item — please try again.")
            return

        log.info("Item created: %s (%s, id=%s)", name, sku, new_id)
        self.manager.current = "inventory"
