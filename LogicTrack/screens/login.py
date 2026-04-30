"""Mockup PT1 — Login Page (Author: Morgan Grant).

Performs real-time email validation and shows a themed Toast notice
(`danger` token) when authentication fails or input is malformed,
instead of dumping errors to the console.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen

from models import User


log = logging.getLogger("logictrack.login")


# Practical RFC 5322-flavoured pattern. Good enough for the app's needs;
# strict enough to catch typos like "you@.com" and "user@host" without
# the catastrophic regex back-tracking of the textbook RFC version.
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)

# A bare username (no @) is also accepted at the login form, since the
# seed data lets users sign in as "admin" / "manager" / "staff".
USERNAME_RE = re.compile(r"^[A-Za-z0-9._\-]+$")


def looks_like_email(value: str) -> bool:
    return "@" in value


def is_valid_identifier(value: str) -> bool:
    """True if `value` is either a plausible email or a clean username."""
    value = value.strip()
    if not value:
        return False
    if looks_like_email(value):
        return bool(EMAIL_RE.match(value))
    return bool(USERNAME_RE.match(value))


class LoginScreen(Screen):

    # ----------------------------------------------------------- helpers
    def on_pre_enter(self, *_) -> None:
        if "toast" in self.ids:
            self.ids.toast.visible = False
        if "error_label" in self.ids:
            self.ids.error_label.text = ""

    def _show_toast(self, message: str, tone: str = "danger") -> None:
        """Show a themed inline notice using the requested tone token."""
        app = App.get_running_app()
        toast = self.ids.get("toast") if hasattr(self.ids, "get") else None
        if toast is None and "toast" in self.ids:
            toast = self.ids.toast
        if toast is None:
            log.warning("Toast widget not found — message: %s", message)
            return
        toast.message = message
        toast.tone = getattr(app, tone, app.danger)
        toast.visible = True
        # Auto-hide after a few seconds so the toast doesn't linger.
        Clock.unschedule(self._hide_toast)
        Clock.schedule_once(self._hide_toast, 4.0)

    def _hide_toast(self, *_) -> None:
        if "toast" in self.ids:
            self.ids.toast.visible = False

    # --------------------------------------------------- live validation
    def validate_username(self, value: str) -> None:
        """Called from KV via `on_text:` — flags malformed emails inline."""
        value = value.strip()
        if not value:
            # don't nag while the field is still empty
            self._hide_toast()
            return
        if looks_like_email(value) and not EMAIL_RE.match(value):
            self._show_toast("That email address doesn't look right.")
        elif not is_valid_identifier(value):
            self._show_toast("Use letters, numbers, dot, dash, underscore.")
        else:
            self._hide_toast()

    # -------------------------------------------------- login submission
    def do_login(self, username: str, password: str) -> None:
        username = username.strip()
        if not username or not password:
            self._show_toast("Enter your username and password.")
            return
        if not is_valid_identifier(username):
            self._show_toast("That username or email looks malformed.")
            return

        app = App.get_running_app()
        user: Optional[User] = app.db.authenticate(username, password)
        if user is None:
            log.info("Login failed for identifier %r", username)
            self._show_toast("Invalid username or password.")
            return

        log.info("User %s signed in (%s)", user.email, user.role)
        app.current_user = user
        if "error_label" in self.ids:
            self.ids.error_label.text = ""
        if "toast" in self.ids:
            self.ids.toast.visible = False
        self.ids.username_input.text = ""
        self.ids.password_input.text = ""
        self.manager.current = "dashboard"
