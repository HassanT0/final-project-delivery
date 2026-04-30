#!/usr/bin/env python3
"""
Bootstrap the LogicTrack workspace.

This script:

    1. Creates the `assets/` directory tree (icons, fonts, screenshots)
       so a fresh clone has every folder the app expects.
    2. Drops a placeholder default product icon into
       `assets/icons/default.png` if one isn't already there.
    3. Initialises (and optionally rebuilds) `logictrack.db` by
       importing `database.Database`, which will run schema migrations
       and seed sample data on first creation.

Run it once after cloning, or at any time you want to reset the local
database:

    python scripts/setup_environment.py            # idempotent setup
    python scripts/setup_environment.py --reset    # wipe & re-seed DB
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

# Make the project root importable when running this script directly.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger("logictrack.setup")


# ---------------------------------------------------------------------------
# Folders the app expects to exist on disk.
# ---------------------------------------------------------------------------
REQUIRED_DIRS = [
    ROOT / "assets",
    ROOT / "assets" / "icons",
    ROOT / "assets" / "fonts",
    ROOT / "docs",
    ROOT / "docs" / "screenshots",
]


def ensure_directories() -> None:
    for d in REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        log.info("ensured directory: %s", d.relative_to(ROOT))


def ensure_default_icon() -> None:
    """If no default product icon exists, drop a tiny solid-colour PNG.

    We avoid bringing in Pillow as a dependency just for this — a 1×1
    placeholder works because the Kivy widget that uses it stretches to
    fill its frame and shows the rounded background tint.
    """
    target = ROOT / "assets" / "icons" / "default.png"
    if target.exists():
        log.info("default icon already present at %s", target.relative_to(ROOT))
        return
    # 1×1 transparent PNG (valid 67-byte file).
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x03\x00\x05\xfe\x02\xfe\xa3\x95\x99\xa6\x00"
        b"\x00\x00\x00IEND\xaeB`\x82"
    )
    target.write_bytes(png)
    log.info("wrote placeholder default icon: %s", target.relative_to(ROOT))


def initialise_database(reset: bool = False) -> None:
    """Import the project's Database class so migrations run + seed data
    is inserted. Optionally wipe an existing DB first."""
    db_path = ROOT / "logictrack.db"
    if reset and db_path.exists():
        backup = db_path.with_suffix(".db.bak")
        if backup.exists():
            backup.unlink()
        shutil.move(str(db_path), str(backup))
        log.info("existing database backed up to %s", backup.relative_to(ROOT))

    try:
        from database import Database  # imported lazily so the script
        # works before the package is installed
    except ImportError as exc:
        log.error("Couldn't import the Database module: %s", exc)
        log.error("Run `pip install -e .` from the project root first.")
        sys.exit(1)

    Database(str(db_path))
    log.info("database ready at %s", db_path.relative_to(ROOT))


def list_optional_assets() -> None:
    """Tell the user what to add for the best visual experience."""
    font_dir = ROOT / "assets" / "fonts"
    fonts = list(font_dir.glob("*.ttf"))
    if not fonts:
        log.info(
            "Tip: drop a Material Symbols font into %s "
            "(e.g. MaterialSymbolsOutlined.ttf) to enable sidebar glyphs.",
            font_dir.relative_to(ROOT),
        )
    logo = ROOT / "assets" / "logo.png"
    if not logo.exists():
        log.info(
            "Tip: drop a 256×256 LogicTrack logo at %s for branded PDFs.",
            logo.relative_to(ROOT),
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true",
                        help="Wipe and re-seed logictrack.db")
    parser.add_argument("--skip-db", action="store_true",
                        help="Don't touch logictrack.db at all")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log.info("LogicTrack workspace setup — root: %s", ROOT)
    ensure_directories()
    ensure_default_icon()
    if not args.skip_db:
        initialise_database(reset=args.reset)
    list_optional_assets()
    log.info("Done. Run `python main.py` to launch the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
