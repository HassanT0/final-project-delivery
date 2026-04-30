# LogicTrack — Inventory Management System

A polished Kivy desktop application that implements the eight UI mockups
from the team's *Front-End Design Document* on top of a SQLite-backed
domain model. Role-aware login, full inventory CRUD with image uploads,
supplier management, branded PDF reports, and a refined Modern
Enterprise design system with light and dark themes.

---

## Tech stack

| Layer            | Technology                       | Version        |
|------------------|----------------------------------|----------------|
| Language         | Python                           | **3.10+** (3.11 recommended; tested on 3.10 / 3.11 / 3.12) |
| UI framework     | [Kivy](https://kivy.org)         | **>= 2.2.0**   |
| UI markup        | Kv language (ships with Kivy)    | n/a            |
| Database         | SQLite (via stdlib `sqlite3`)    | bundled with Python |
| PDF reports      | [ReportLab](https://www.reportlab.com) | **>= 4.0** |
| Build backend    | setuptools                       | **>= 68**      |
| Packaging spec   | `pyproject.toml` (PEP 621)       | n/a            |
| Dev tooling      | pytest **>= 7.4**, pyflakes **>= 3.1**, ruff **>= 0.4**, mypy **>= 1.7** | see `pyproject.toml` |

Runs on macOS, Linux, and Windows desktops — Kivy is cross-platform.

---

## Getting started

### 1. Prerequisites

* **Python 3.10+** (3.11 recommended) — verify with `python --version`
* `pip` (bundled with Python) and `venv` for isolation
* A C toolchain is **not** required: Kivy and ReportLab ship prebuilt wheels for the supported Python versions on macOS / Linux / Windows
* (Optional) `git` to clone the repo

### 2. Clone and bootstrap

```bash
git clone <repo-url>
cd LogicTrack

# create + activate a virtualenv
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows PowerShell

# install runtime + dev dependencies (preferred — uses pyproject.toml)
pip install -e ".[dev]"

# — or — runtime-only via the pinned legacy file
pip install -r requirements.txt

# scaffold assets/, seed the DB, and download the optional icon font
python scripts/setup_environment.py
```

### 3. Run the app

```bash
python main.py
```

…or, after `pip install -e .`, use the installed console script:

```bash
logictrack
```

The first run creates `logictrack.db` next to `main.py` and seeds it
with the sample users / items / suppliers shown in the mockups.

### 4. Verify the install (optional)

```bash
python -m compileall .             # syntax-check every module
python -m pyflakes .               # quick lint
pytest                             # run the test suite (when present)
```

### Sample logins

| Email                | Password | Role    |
|----------------------|----------|---------|
| admin@logic.com      | admin    | Admin   |
| manager@logic.com    | manager  | Manager |
| staff@logic.com      | staff    | Staff   |

You can also sign in with just the username portion (e.g. `admin` /
`admin`).

---

## Screenshots

> Screenshots live in `docs/screenshots/`. Re-render after major UI
> changes by running the app and using your OS screenshot shortcut on
> each route.

| Screen      | Path                                |
|-------------|-------------------------------------|
| Login       | `docs/screenshots/01-login.png`     |
| Dashboard   | `docs/screenshots/02-dashboard.png` |
| Inventory   | `docs/screenshots/03-inventory.png` |
| Add Item    | `docs/screenshots/04-add-item.png`  |
| Edit Item   | `docs/screenshots/05-edit-item.png` |
| Suppliers   | `docs/screenshots/06-suppliers.png` |
| Reports     | `docs/screenshots/07-reports.png`   |
| Settings    | `docs/screenshots/08-settings.png`  |

*(Image files are placeholders — drop real PNGs in once the redesign is
captured.)*

---

## Project layout

```
LogicTrack/
├── main.py              # App entry point + ScreenManager + theme glue
├── style_manager.py     # Modern Enterprise colour tokens + icon glyphs
├── database.py          # SQLite schema, queries, migrations, logging
├── models.py            # User / Item / Supplier dataclasses
├── pyproject.toml       # Build system + dependencies
├── requirements.txt     # Pinned runtime deps (legacy)
├── README.md
├── scripts/
│   └── setup_environment.py  # asset/db bootstrap helper
├── screens/
│   ├── login.py         # PT1 – Login (Morgan Grant)
│   ├── dashboard.py     # PT2 – Dashboard (Madison Lindsey)
│   ├── inventory.py     # PT3 – Inventory (Raymond Rai)
│   ├── add_item.py      # PT4 – Add Item (Aashish Amgain)
│   ├── edit_item.py     # PT5 – Edit Item (Hassan Issaka)
│   ├── suppliers.py     # PT6 – Suppliers (Morgan Grant)
│   ├── reports.py       # PT7 – Reports (Hassan Issaka)
│   └── settings.py      # PT8 – Settings (Madison Lindsey)
└── kv/
    ├── theme.kv         # Shared widgets: Card, NavButton, Toast …
    ├── login.kv
    ├── dashboard.kv
    ├── inventory.kv
    ├── add_item.kv
    ├── edit_item.kv
    ├── suppliers.kv
    ├── reports.kv
    └── settings.kv
```

Each `screens/<name>.py` defines the `Screen` subclass and behavior; the
matching `kv/<name>.kv` file is the layout. `main.py` loads every kv
file at startup, so you don't need to import them manually.

---

## Architecture highlights

* **Modern Enterprise design system.** Refined low-contrast palette
  (light + dark) lives in `style_manager.py` and is exposed to KV via
  `AliasProperty` shims on the App.
* **Material Design icons in the sidebar.** When the optional font
  (`assets/fonts/MaterialSymbolsOutlined.ttf`) is present, the nav
  buttons render proper glyphs; otherwise they fall back to short
  ASCII labels so the menu always reads cleanly.
* **Subtle FadeTransition** between screens — no jarring snap.
* **Typed domain models.** `models.py` exports `User`, `Item`,
  `Supplier`, and `Transaction` dataclasses; the database returns them
  instead of raw tuples, so screens reference fields by name.
* **Logged DB operations.** Every method in `database.py` is wrapped in
  a `try/except` that pipes failures into the `logictrack.db` logger.
* **Branded reportlab PDF export** (`screens/reports.py`) including a
  logo, summary block, and styled data table.
* **Real-time form validation.** `screens/login.py` and
  `screens/add_item.py` validate emails / SKUs as the user types and
  surface problems via a themed `Toast` using the `danger` token.

---

## Contribution guide

We welcome contributions! Please follow the conventions below so review
stays fast and the codebase stays consistent.

### Workflow

1. **Fork** the repository and create a feature branch from `main`:
   `git checkout -b feature/short-description`.
2. **Install dev dependencies**: `pip install -e ".[dev]"`.
3. **Make focused commits** that compile and pass `python -m compileall .`
   after every change.
4. **Run the test suite** (when present) and the linter:
   `pytest` and `python -m pyflakes .`.
5. **Open a pull request** with a clear summary, screenshots for any UI
   changes, and a link to the issue you're addressing.

### Code style

* **Type hints everywhere.** New functions and dataclass fields must be
  type-hinted. Prefer `from __future__ import annotations`.
* **Docstrings.** One-line summaries for every public function; full
  docstrings for anything non-trivial.
* **Database access** goes through `database.Database`. Don't open
  `sqlite3.connect` directly from a screen.
* **No prints in shipped code.** Use the `logictrack.<module>` logger.
* **KV files** mirror their Python counterparts — keep widget IDs and
  property names aligned across the pair.

### Adding a new screen

1. Create `screens/<name>.py` with a `Screen` subclass.
2. Create `kv/<name>.kv` with the matching `<NameScreen>:` rule.
3. Register the file in `main.py` (both `Builder.load_file` and the
   `ScreenManager.add_widget` block).
4. Add the screen to the sidebar in every other `kv/*.kv` if relevant.
5. Capture a screenshot for `docs/screenshots/`.

### Adding a database column

1. Update the `_init_schema` block in `database.py`.
2. Add a clause to `_migrate_items_schema` (or write a new migration
   helper) so existing installs upgrade safely.
3. Update the `Item` (or relevant) dataclass in `models.py`.
4. Update `_row_to_item` and any affected query.
5. Backfill the seed data in `_seed_if_empty`.

### Reporting bugs

Open an issue with:

* Operating system + Python version
* Steps to reproduce
* Stack trace (if any) and the relevant lines from your terminal
* Screenshot if the bug is visual

---

## License

Released under the MIT License — see `LICENSE` for the full text.
