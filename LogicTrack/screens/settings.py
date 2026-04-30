"""Settings screen — users, threshold, theme, formatting."""
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle


_ROLE_COLORS = {
    "Admin":   (0.890, 0.227, 0.227, 1),
    "Manager": (0.231, 0.318, 0.882, 1),
    "Staff":   (0.122, 0.659, 0.412, 1),
}


class _RolePill(BoxLayout):
    def __init__(self, role, **kw):
        super().__init__(size_hint=(None, None), size=(78, 24),
                         padding=(8, 3), **kw)
        color = _ROLE_COLORS.get(role, (0.4, 0.4, 0.4, 1))
        with self.canvas.before:
            Color(color[0], color[1], color[2], 0.15)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(Label(text=role, color=color, font_size=11, bold=True))

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SettingsScreen(Screen):

    def on_pre_enter(self, *_):
        app = App.get_running_app()
        self.ids.threshold_slider.value = app.low_stock_threshold
        self.ids.threshold_label.text = f"Global threshold: {int(app.low_stock_threshold)} units"
        self.ids.notifications_toggle.text = "Enable notifications: ON"
        self.ids.theme_label.text = f"Appearance — currently {app.theme}"
        self.ids.date_format_input.text = app.date_format
        self.ids.time_format_input.text = app.time_format
        self._highlight_theme_button(app.theme)
        self.refresh_users()

    def refresh_users(self):
        app = App.get_running_app()
        box = self.ids.users_box
        box.clear_widgets()
        for user in app.db.list_users():
            row = BoxLayout(size_hint_y=None, height=44, padding=(8, 0), spacing=10)
            row.add_widget(Label(
                text=user.email, color=app.text_color, font_size=14,
                halign="left", valign="middle", text_size=(380, None),
            ))
            pill_box = BoxLayout(size_hint_x=None, width=90, padding=(0, 10))
            pill_box.add_widget(_RolePill(user.role))
            row.add_widget(pill_box)
            box.add_widget(row)

    def open_add_user(self):
        layout = BoxLayout(orientation="vertical", spacing=8, padding=14)
        email_in = TextInput(hint_text="email", multiline=False,
                             size_hint_y=None, height=38)
        password_in = TextInput(hint_text="password", multiline=False,
                                password=True, size_hint_y=None, height=38)
        role_in = TextInput(hint_text="role (Admin / Manager / Staff)",
                            multiline=False, size_hint_y=None, height=38)
        for w in (email_in, password_in, role_in):
            layout.add_widget(w)
        btns = BoxLayout(size_hint_y=None, height=42, spacing=8)
        layout.add_widget(btns)

        popup = Popup(title="Add User", content=layout,
                      size_hint=(None, None), size=(380, 280))

        def save(_):
            app = App.get_running_app()
            email = email_in.text.strip()
            pwd = password_in.text
            role = role_in.text.strip().capitalize()
            if not email or not pwd or role not in ("Admin", "Manager", "Staff"):
                return
            try:
                app.db.add_user(email, pwd, role)
            except Exception:
                return
            popup.dismiss()
            self.refresh_users()

        save_btn = Button(text="Save", background_normal="",
                          background_color=(0.18, 0.66, 0.30, 1),
                          color=(1, 1, 1, 1))
        save_btn.bind(on_release=save)
        cancel_btn = Button(text="Cancel")
        cancel_btn.bind(on_release=lambda _: popup.dismiss())
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        popup.open()

    def update_threshold(self, value):
        v = int(value)
        self.ids.threshold_label.text = f"Global threshold: {v} units"

    def toggle_notifications(self):
        cur = "ON" in self.ids.notifications_toggle.text
        self.ids.notifications_toggle.text = (
            "Enable notifications: OFF" if cur else "Enable notifications: ON"
        )

    def set_theme(self, theme):
        app = App.get_running_app()
        app.theme = theme
        self.ids.theme_label.text = f"Appearance — currently {theme}"
        self._highlight_theme_button(theme)
        self.refresh_users()

    def _highlight_theme_button(self, active):
        light_btn = self.ids.light_btn
        dark_btn = self.ids.dark_btn
        app = App.get_running_app()
        accent = app.primary
        idle = app.neutral_btn
        light_btn.btn_color = accent if active == "Light" else idle
        dark_btn.btn_color = accent if active == "Dark" else idle
        light_btn.color = (1, 1, 1, 1) if active == "Light" else app.text_color
        dark_btn.color = (1, 1, 1, 1) if active == "Dark" else app.text_color

    def save_changes(self):
        app = App.get_running_app()
        app.low_stock_threshold = int(self.ids.threshold_slider.value)
        app.date_format = self.ids.date_format_input.text.strip() or "MM/DD/YYYY"
        app.time_format = self.ids.time_format_input.text.strip() or "12-hour"
        Popup(title="Settings", content=Label(text="Settings saved."),
              size_hint=(None, None), size=(300, 130)).open()
