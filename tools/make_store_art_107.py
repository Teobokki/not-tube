"""Hero / capsule for the store, built from the real 1.0.7 screenshot (shot0)."""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont
D = "/workspace/not-tube/store_art"
shot = Image.open(os.path.join(D, "shot0.jpg")).convert("RGB")
icon = Image.open(os.path.join(D, "icon512.png")).convert("RGBA")
fb = "/usr/share/fonts/truetype/sand-box/google/Roboto/Roboto-VariableFont_wdth,wght.ttf"
def bg(w, h):
    b = shot.resize((w, int(w * shot.height / shot.width))).crop((0, 0, w, h)) if w / h > shot.width / shot.height else shot.resize((int(h * shot.width / shot.height), h)).crop((0, 0, w, h))
    b = b.filter(ImageFilter.GaussianBlur(28))
    return Image.blend(b, Image.new("RGB", (w, h), (12, 12, 14)), 0.72)
def framed(im, w):
    h = int(w * im.height / im.width)
    s = im.resize((w, h), Image.Resampling.LANCZOS)
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 14, fill=255)
    return s, m
def compose(W, H, ic, fs, tx, ty, sw, sx, sy):
    c = bg(W, H)
    if W == 1600:
        c.save(os.path.join(D, "hero_bg.jpg"), quality=92)
    i = icon.resize((ic, ic), Image.Resampling.LANCZOS)
    c.paste(i, (tx, ty), i)
    d = ImageDraw.Draw(c)
    f = ImageFont.truetype(fb, fs)
    try:
        f.set_variation_by_axes([800, 100])
    except Exception:
        pass
    d.text((tx + ic + int(ic * 0.18), ty + ic // 2), "NOT TUBE", font=f, fill=(255, 255, 255), anchor="lm")
    s, m = framed(shot, sw)
    c.paste(s, (sx, sy if sy is not None else (H - s.height) // 2), m)
    return c
hero = compose(1600, 600, 150, 80, 50, 225, 880, 680, None)
hero.save(os.path.join(D, "hero.jpg"), quality=92)
cap = compose(616, 353, 64, 40, 22, 22, 520, 48, 110)
cap.save(os.path.join(D, "capsule.jpg"), quality=92)
print(hero.size, cap.size)
