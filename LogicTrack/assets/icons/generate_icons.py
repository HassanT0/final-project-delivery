"""
Generate small placeholder PNG icons for seeded inventory items.

Re-run this script any time you want to regenerate or extend the
default icon set:

    python assets/icons/generate_icons.py

Pillow ships with Kivy, so no extra dependency is needed.
"""
from PIL import Image, ImageDraw
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SIZE = 96


def _new_canvas(bg=(245, 245, 247)):
    img = Image.new("RGB", (SIZE, SIZE), bg)
    return img, ImageDraw.Draw(img)


def make_apples():
    img, d = _new_canvas()
    # green stem / leaf
    d.polygon([(46, 8), (60, 4), (54, 22), (46, 18)], fill=(50, 140, 60))
    # red apple body
    d.ellipse((14, 18), (82, 86), outline=None, fill=(210, 45, 50)) \
        if False else d.ellipse([(14, 18), (82, 86)], fill=(210, 45, 50))
    # subtle highlight
    d.ellipse([(28, 30), (44, 46)], fill=(240, 130, 130))
    img.save(os.path.join(OUT_DIR, "apples.png"))


def make_milk():
    img, d = _new_canvas()
    # carton body (white)
    d.rectangle([(24, 18), (72, 86)], fill=(252, 252, 252), outline=(60, 60, 60), width=2)
    # roof
    d.polygon([(24, 18), (48, 6), (72, 18)], fill=(245, 245, 245), outline=(60, 60, 60))
    # blue band
    d.rectangle([(24, 42), (72, 56)], fill=(80, 140, 220))
    img.save(os.path.join(OUT_DIR, "milk.png"))


def make_rice():
    img, d = _new_canvas()
    # bowl
    d.pieslice([(8, 30), (88, 100)], start=0, end=180, fill=(220, 200, 170),
               outline=(120, 100, 70), width=2)
    # rice mound
    d.pieslice([(14, 26), (82, 70)], start=180, end=360, fill=(252, 250, 240),
               outline=(200, 190, 170))
    # tiny grain dots
    for x, y in [(34, 36), (50, 32), (62, 38), (44, 44), (58, 44)]:
        d.ellipse([(x, y), (x + 5, y + 3)], fill=(230, 220, 200))
    img.save(os.path.join(OUT_DIR, "rice.png"))


def make_bread():
    img, d = _new_canvas()
    # loaf
    d.rounded_rectangle([(12, 30), (84, 80)], radius=18, fill=(200, 150, 90),
                        outline=(140, 100, 60), width=2)
    # crust slashes
    for x in (28, 48, 68):
        d.line([(x, 38), (x + 6, 70)], fill=(140, 100, 60), width=2)
    img.save(os.path.join(OUT_DIR, "bread.png"))


def make_default():
    img, d = _new_canvas(bg=(232, 234, 240))
    d.rectangle([(20, 20), (76, 76)], fill=(200, 205, 215),
                outline=(120, 130, 145), width=2)
    d.text((42, 36), "?", fill=(80, 90, 110))
    img.save(os.path.join(OUT_DIR, "default.png"))


if __name__ == "__main__":
    make_apples()
    make_milk()
    make_rice()
    make_bread()
    make_default()
    print(f"Wrote icons to {OUT_DIR}")
