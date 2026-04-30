"""Suppliers screen — vendor management with polished rows."""
from __future__ import annotations

from typing import List

from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle

from models import Supplier


class _PillButton(Button):
    def __init__(self, text, color, **kw):
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


class _Avatar(BoxLayout):
    """Initial-letter avatar circle."""

    def __init__(self, name, **kw):
        super().__init__(size_hint=(None, None), size=(44, 44), **kw)
        seed = sum(ord(c) for c in (name or "?")) % 360
        # convert HSV-ish hue to a soft color
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(seed / 360.0, 0.45, 0.92)
        with self.canvas.before:
            Color(r, g, b, 1)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[22])
        self.bind(pos=self._sync, size=self._sync)
        initial = (name[:1] or "?").upper()
        self.add_widget(Label(text=initial, color=(0.18, 0.22, 0.30, 1),
                              bold=True, font_size=18))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SuppliersScreen(Screen):

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        app = App.get_running_app()
        search = self.ids.search_input.text.strip() or None
        table = self.ids.suppliers_table
        table.clear_widgets()

        # ----- header row -----
        header = BoxLayout(size_hint_y=None, height=42, padding=(16, 0), spacing=12)
        with header.canvas.before:
            Color(*app.input_bg)
            hr = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda *_: setattr(hr, "pos", header.pos),
                    size=lambda *_: setattr(hr, "size", header.size))
        header.add_widget(Widget(size_hint_x=None, width=46))
        col_specs = [("NAME", 1, None), ("CONTACT", None, 160),
                     ("PHONE", None, 140), ("EMAIL", 1, None),
                     ("ACTIONS", None, 200)]
        for h, sx, w in col_specs:
            kw = dict(text=h, color=app.muted_text_color, font_size=11, bold=True,
                      halign="left", valign="middle")
            if w is not None:
                kw.update(size_hint_x=None, width=w, text_size=(w, None))
            else:
                kw["size_hint_x"] = sx
            header.add_widget(Label(**kw))
        table.add_widget(header)

        suppliers: List[Supplier] = app.db.list_suppliers(search)
        if not suppliers:
            empty = Label(text="No suppliers found.", color=app.muted_text_color,
                          size_hint_y=None, height=120,
                          halign="center", valign="middle")
            empty.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            table.add_widget(empty)
            table.add_widget(Widget())
            return

        for i, supplier in enumerate(suppliers):
            row = BoxLayout(size_hint_y=None, height=68, padding=(16, 0), spacing=12)
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

            avatar_col = BoxLayout(size_hint_x=None, width=46, padding=(0, 12))
            avatar_col.add_widget(_Avatar(supplier.name))
            row.add_widget(avatar_col)

            name_lbl = Label(text=supplier.name, color=app.text_color, font_size=14,
                             bold=True, halign="left", valign="middle")
            name_lbl.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            row.add_widget(name_lbl)

            for value, w in (
                (supplier.contact or "—", 160),
                (supplier.phone or "—", 140),
            ):
                lbl = Label(text=value, color=app.text_color, font_size=13,
                            halign="left", valign="middle",
                            size_hint_x=None, width=w)
                lbl.text_size = (w, None)
                row.add_widget(lbl)

            email_lbl = Label(text=supplier.email or "—", color=app.muted_text_color,
                              font_size=13, halign="left", valign="middle")
            email_lbl.bind(size=lambda i, *_: setattr(i, "text_size", i.size))
            row.add_widget(email_lbl)

            actions = BoxLayout(size_hint_x=None, width=200, spacing=8, padding=(0, 17))
            edit_btn = _PillButton("Edit", app.primary)
            edit_btn.bind(on_release=lambda _b, s=supplier: self.open_form(s))
            del_btn = _PillButton("Delete", app.danger)
            del_btn.bind(on_release=lambda _b, i=supplier.id, n=supplier.name:
                         self.confirm_delete(i, n))
            actions.add_widget(edit_btn)
            actions.add_widget(del_btn)
            row.add_widget(actions)

            table.add_widget(row)

        table.add_widget(Widget())

    # -------------------------------------------------------- add / edit form
    def open_form(self, existing: Supplier | None = None) -> None:
        layout = BoxLayout(orientation="vertical", spacing=8, padding=14)
        name_in    = TextInput(hint_text="Name",    multiline=False, size_hint_y=None, height=38)
        contact_in = TextInput(hint_text="Contact", multiline=False, size_hint_y=None, height=38)
        phone_in   = TextInput(hint_text="Phone",   multiline=False, size_hint_y=None, height=38)
        email_in   = TextInput(hint_text="Email",   multiline=False, size_hint_y=None, height=38)
        address_in = TextInput(hint_text="Address", multiline=False, size_hint_y=None, height=38)
        for w in (name_in, contact_in, phone_in, email_in, address_in):
            layout.add_widget(w)

        if existing:
            name_in.text    = existing.name
            contact_in.text = existing.contact or ""
            phone_in.text   = existing.phone or ""
            email_in.text   = existing.email or ""
            address_in.text = existing.address or ""

        btns = BoxLayout(size_hint_y=None, height=42, spacing=8)
        layout.add_widget(btns)

        popup = Popup(title="Edit Supplier" if existing else "Add Supplier",
                      content=layout, size_hint=(None, None), size=(440, 380))

        def save(_):
            app = App.get_running_app()
            args = (name_in.text.strip(), contact_in.text.strip(),
                    phone_in.text.strip(), email_in.text.strip(),
                    address_in.text.strip())
            if not args[0]:
                return
            if existing:
                app.db.update_supplier(existing.id, *args)
            else:
                app.db.add_supplier(*args)
            popup.dismiss()
            self.refresh()

        save_btn = Button(text="Save", background_normal="",
                          background_color=(0.18, 0.66, 0.30, 1),
                          color=(1, 1, 1, 1))
        save_btn.bind(on_release=save)
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_release=lambda _: popup.dismiss())
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        popup.open()

    def confirm_delete(self, supplier_id, name):
        box = BoxLayout(orientation="vertical", spacing=10, padding=10)
        box.add_widget(Label(text=f'Delete supplier "{name}"?\nThis cannot be undone.'))
        btns = BoxLayout(spacing=10, size_hint_y=None, height=40)
        popup = Popup(title="Confirm Delete", content=box,
                      size_hint=(None, None), size=(360, 180), auto_dismiss=False)

        def do_delete(_):
            App.get_running_app().db.delete_supplier(supplier_id)
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
