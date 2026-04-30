"""
Helpers for resolving an item's icon path.

Order of preference:
  1. The image_path stored on the item (uploaded via Add Item).
  2. A built-in icon matching the item's name (apples / milk / rice / bread).
  3. assets/icons/default.png as a final fallback.

All paths are resolved relative to the project root, so they work no
matter what the user's current working directory is.
"""
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
ICON_DIR = os.path.join(PROJECT_ROOT, "assets", "icons")

_NAME_MAP = {
    "apple":  "apples.png",
    "apples": "apples.png",
    "milk":   "milk.png",
    "rice":   "rice.png",
    "bread":  "bread.png",
}


def _abs(rel_or_abs):
    if not rel_or_abs:
        return None
    return rel_or_abs if os.path.isabs(rel_or_abs) \
        else os.path.join(PROJECT_ROOT, rel_or_abs)


def icon_for(item_name, image_path=None):
    """Return an absolute path to a PNG to display for the item.

    item_name : str   - product name, e.g. "Apples".
    image_path: str|None - path saved on the item record (relative or abs).
    """
    p = _abs(image_path)
    if p and os.path.isfile(p):
        return p

    if item_name:
        key = item_name.strip().lower()
        if key in _NAME_MAP:
            cand = os.path.join(ICON_DIR, _NAME_MAP[key])
            if os.path.isfile(cand):
                return cand

    default = os.path.join(ICON_DIR, "default.png")
    return default if os.path.isfile(default) else ""
