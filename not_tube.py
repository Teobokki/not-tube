# -*- coding: utf-8 -*-
"""NOT TUBE — local video library with a dark desktop layout.
©2026 EX Inc./HYPERION DIGITAL ©2026
"""
from __future__ import annotations

import hashlib, json, os, random, re, shutil, subprocess, sys, tempfile, threading, time, urllib.request, webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont

APP = "NOT TUBE"
APP_VERSION = "1.0.6"
COPYRIGHT = "\u00a92026 EX Inc./HYPERION DIGITAL \u00a92026"
REPO = "Teobokki/not-tube"
UPDATE_URL = "https://raw.githubusercontent.com/%s/main/latest.json" % REPO

BG = "#0f0f0f"
CARD = "#272727"
HOVER = "#3f3f3f"
CHIP = "#272727"
TXT = "#ffffff"
MUT = "#aaaaaa"
DIM = "#717171"
BORDER = "#303030"
SEARCH_BG = "#121212"
SEARCH_BTN = "#222222"
BAR = "#0f0f0f"
SCRIM = "#1a1a1a"
WHITE = "#ffffff"
BLACK = "#0f0f0f"

FPS = 24
PLAY_W, PLAY_H = 960, 540
NO_WINDOW = 0x08000000 if os.name == "nt" else 0
VID_EXT = (".mp4", ".mov", ".mkv", ".webm", ".avi")
VID_TYPES = [("Video files", "*.mp4;*.mov;*.mkv;*.webm;*.avi"), ("All files", "*.*")]

INTENSITY_VPM = {"low": (40, 90), "medium": (280, 560), "rocket": (4000, 9500)}
INTENSITY_RANK = {"low": 1, "medium": 2, "rocket": 3}
INTENSITY_SUB_PM = {"low": 2, "medium": 10, "rocket": 45}
INTENSITY_CMT_S = {"low": 180, "medium": 90, "rocket": 24}
BOOST_CATCHUP_CAP = 6 * 3600
BOT_TARGET = 2000

BOT_COMMENTS = [
    "great video",
    "this is so good",
    "need more of this",
    "watched the whole thing",
    "nice work",
    "saved this one",
    "the pacing is perfect",
    "came back for a second watch",
    "clean work",
    "more like this please",
    "really well put together",
    "this made my evening",
]

if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter, ImageOps


def res_path(*n):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *n)


def app_data_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    d = os.path.join(base, APP)
    for sub in ("videos", "thumbs", "avatars", "banners"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    return d


def library_path():
    return os.path.join(app_data_dir(), "library.json")


def downloads_dir():
    d = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD),
                            ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
            g = GUID(0x374DE290, 0x123F, 0x4565,
                     (ctypes.c_ubyte * 8)(0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(p)) == 0 and p.value:
                d = p.value
        except Exception:
            pass
    os.makedirs(d, exist_ok=True)
    return d


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def run_hidden(cmd, timeout=120, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW, **kw)


def probe_duration(path):
    try:
        p = run_hidden([ffmpeg_exe(), "-i", path], timeout=20)
        text = (p.stderr or b"").decode("utf-8", "replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def grab_thumb(src, dest, dur=0.0, vertical=False):
    t = max(0.05, (dur * 0.10) if dur and dur > 0.4 else 0.4)
    if vertical:
        vf = "scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2:black"
    else:
        vf = "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:black"
    cmd = [
        ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
        "-ss", "%.3f" % t, "-i", src, "-frames:v", "1",
        "-vf", vf,
        dest,
    ]
    try:
        p = run_hidden(cmd, timeout=30)
        return p.returncode == 0 and os.path.isfile(dest) and os.path.getsize(dest) > 100
    except Exception:
        return False


def probe_media(path):
    """Return duration, width, height via ffmpeg -i stderr."""
    dur, w, h = 0.0, 0, 0
    try:
        proc = run_hidden([ffmpeg_exe(), "-i", path], timeout=20)
        text = (proc.stderr or b"").decode("utf-8", "replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
        if m:
            dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        m = re.search(r"Stream.*Video:.*?(\d{2,5})x(\d{2,5})", text)
        if m:
            w, h = int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return {"duration": dur, "width": w, "height": h}


def looks_like_short(path, info=None):
    info = info or probe_media(path)
    dur = float(info.get("duration") or 0)
    w, h = int(info.get("width") or 0), int(info.get("height") or 0)
    return bool(h > w and 0 < dur <= 60.5)


def vtuple(v):
    out = []
    for p in re.split(r"\D+", str(v).strip()):
        if p:
            try:
                out.append(int(p))
            except Exception:
                pass
    return tuple(out or [0])


def check_update():
    try:
        req = urllib.request.Request(
            UPDATE_URL + "?t=%d" % time.time(),
            headers={"User-Agent": "NOT-TUBE/" + APP_VERSION},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            m = json.loads(r.read(65536).decode("utf-8"))
        ver = str(m["version"])
    except Exception as e:
        return "error", "Could not check for updates (%s)." % (getattr(e, "reason", None) or e)
    if vtuple(ver) > vtuple(APP_VERSION):
        return "newer", {"version": ver, "notes": str(m.get("notes", "")),
                         "link": str(m.get("installer_url") or m.get("url", ""))}
    return "latest", "You are on the latest version (%s)." % APP_VERSION


def fmt_views(n, word="views"):
    n = int(n or 0)
    if n < 1000:
        if word == "views":
            return "1 view" if n == 1 else "%d views" % n
        if word == "notscribers":
            return "1 notscriber" if n == 1 else "%d notscribers" % n
        return "1 %s" % word[:-1] if n == 1 and word.endswith("s") else "%d %s" % (n, word)
    if n < 10000:
        return "%.1fK %s" % (n / 1000.0, word)
    if n < 1000000:
        return "%dK %s" % (int(round(n / 1000.0)), word)
    if n < 10000000:
        return "%.1fM %s" % (n / 1000000.0, word)
    return "%dM %s" % (int(round(n / 1000000.0)), word)


def fmt_count(n):
    n = int(n or 0)
    if n < 1000:
        return str(n)
    if n < 10000:
        return "%.1fK" % (n / 1000.0)
    if n < 1000000:
        return "%dK" % int(round(n / 1000.0))
    if n < 10000000:
        return "%.1fM" % (n / 1000000.0)
    return "%dM" % int(round(n / 1000000.0))


def fmt_dur(s):
    s = max(0, int(s or 0))
    if s >= 3600:
        return "%d:%02d:%02d" % (s // 3600, (s % 3600) // 60, s % 60)
    return "%d:%02d" % (s // 60, s % 60)


def fmt_ago(iso):
    try:
        # stored as epoch or iso
        if isinstance(iso, (int, float)):
            t = float(iso)
        else:
            t = time.mktime(time.strptime(str(iso)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return ""
    sec = max(0, int(time.time() - t))
    if sec < 45:
        return "just now"
    if sec < 90:
        return "1 minute ago"
    if sec < 3600:
        return "%d minutes ago" % (sec // 60)
    if sec < 5400:
        return "1 hour ago"
    if sec < 86400:
        return "%d hours ago" % (sec // 3600)
    if sec < 172800:
        return "1 day ago"
    if sec < 86400 * 30:
        return "%d days ago" % (sec // 86400)
    if sec < 86400 * 60:
        return "1 month ago"
    if sec < 86400 * 365:
        return "%d months ago" % (sec // (86400 * 30))
    if sec < 86400 * 365 * 2:
        return "1 year ago"
    return "%d years ago" % (sec // (86400 * 365))


def fmt_date(iso):
    try:
        if isinstance(iso, (int, float)):
            return time.strftime("%d %b %Y", time.localtime(float(iso)))
        return time.strftime("%d %b %Y", time.strptime(str(iso)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return ""


def new_id(prefix="id"):
    return "%s-%d-%04d" % (prefix, int(time.time() * 1000), random.randint(0, 9999))


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "", (name or "").lower())
    return s[:24] or "channel"


def normalize_handle(h, name=""):
    h = (h or "").strip()
    if not h:
        h = slugify(name)
    if not h.startswith("@"):
        h = "@" + h
    h = "@" + re.sub(r"[^A-Za-z0-9_]", "", h[1:])
    return h[:32] or "@channel"


def bot_name():
    return "ntbot_%04d" % random.randint(0, 9999)


def _is_kim_miyoyazu_channel(ch):
    """True for the user's Kim Miyoyazu channel (handle or name, case-insensitive)."""
    if not ch:
        return False
    raw = (ch.get("handle") or "").strip()
    if raw and normalize_handle(raw, "").lower() == "@kimmiyoyazu":
        return True
    return (ch.get("name") or "").strip().lower() == "kim miyoyazu"


def ensure_kim_miyoyazu_featured(lib):
    """Idempotently feature the user's Kim Miyoyazu channel and keep it owned.
    Does not touch its videos, description, or avatar."""
    if lib is None:
        return
    changed = False
    for ch in lib.channels():
        if not _is_kim_miyoyazu_channel(ch):
            continue
        if not ch.get("featured"):
            ch["featured"] = True
            changed = True
        if not ch.get("owned"):
            ch["owned"] = True
            changed = True
    if changed:
        lib.save()


OWNER_USERNAME = "kimi"


def is_owner_pc():
    """Owner tools are automatic on the owner's Windows account (username Kimi)."""
    names = []
    for key in ("USERNAME", "USER", "LOGNAME"):
        v = os.environ.get(key) or ""
        if v:
            names.append(v)
    try:
        names.append(os.getlogin())
    except Exception:
        pass
    try:
        import getpass
        names.append(getpass.getuser())
    except Exception:
        pass
    return any((n or "").strip().lower() == OWNER_USERNAME for n in names)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


FONT_UI = "Roboto"
FONT_FALLBACK = ("Noto Sans", "Tahoma", "Segoe UI", "Arial")


def pick_family(preferred, families):
    fl = {f.lower(): f for f in families}
    for name in (preferred,) + (FONT_FALLBACK if isinstance(FONT_FALLBACK, tuple) else ()):
        if name.lower() in fl:
            return fl[name.lower()]
    return preferred


def init_fonts(root):
    global FONT_UI
    try:
        fams = list(tkfont.families(root))
        FONT_UI = pick_family("Roboto", fams)
    except Exception:
        FONT_UI = "Tahoma"
    return FONT_UI


# -------------------- images / icons --------------------
_ROUND_CACHE = {}
_ICON_CACHE = {}


def rounded_fill(w, h, r, fill, outline=None, ow=1):
    key = (int(w), int(h), int(r), fill, outline, ow)
    im = _ROUND_CACHE.get(key)
    if im is None:
        im = Image.new("RGBA", (max(1, int(w)), max(1, int(h))), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        box = (0, 0, im.width - 1, im.height - 1)
        if outline:
            d.rounded_rectangle(box, r, fill=fill, outline=outline, width=ow)
        else:
            d.rounded_rectangle(box, r, fill=fill)
        _ROUND_CACHE[key] = im
    return im


def photo_of(im):
    return ImageTk.PhotoImage(im)


def cover_fit(im, tw, th):
    im = im.convert("RGB")
    scale = max(tw / im.width, th / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return im.crop((x, y, x + tw, y + th))


def circle_avatar(im, size, border=None):
    im = cover_fit(im.convert("RGB"), size, size)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0))
    out.putalpha(mask)
    if border:
        d = ImageDraw.Draw(out)
        d.ellipse((0, 0, size - 1, size - 1), outline=border, width=1)
    return out


def initials_avatar(name, size, colors=None):
    name = (name or "?").strip() or "?"
    parts = name.split()
    ini = (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")).upper()
    if colors is None:
        h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16)
        pal = [
            (70, 130, 180), (60, 140, 120), (140, 120, 70), (100, 110, 160),
            (80, 140, 160), (130, 100, 70), (90, 90, 140), (70, 120, 90),
            (120, 90, 110), (50, 90, 120),
        ]
        colors = pal[h % len(pal)]
    im = Image.new("RGB", (size, size), colors)
    d = ImageDraw.Draw(im)
    font = get_pil_font(max(12, int(size * 0.38)))
    bbox = d.textbbox((0, 0), ini, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), ini, font=font, fill=(255, 255, 255))
    return im


def rounded_thumb(path, tw, th, radius=12, duration=None, bg=BG):
    try:
        im = Image.open(path).convert("RGB")
        im = cover_fit(im, tw, th)
    except Exception:
        im = Image.new("RGB", (tw, th), (30, 30, 30))
    if duration is not None and duration >= 0:
        d = ImageDraw.Draw(im, "RGBA")
        label = fmt_dur(duration)
        font = get_pil_font(13)
        bbox = d.textbbox((0, 0), label, font=font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 6, 3
        x2, y2 = tw - 8, th - 8
        x1, y1 = x2 - lw - pad_x * 2, y2 - lh - pad_y * 2
        d.rounded_rectangle((x1, y1, x2, y2), 4, fill=(0, 0, 0, 210))
        d.text((x1 + pad_x - bbox[0], y1 + pad_y - bbox[1]), label, font=font, fill=(255, 255, 255, 255))
    bg_rgb = hex_rgb(bg)
    base = Image.new("RGB", (tw, th), bg_rgb)
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, th - 1), radius, fill=255)
    base.paste(im, (0, 0), mask)
    return base


def _icon_im(kind, size=24, color="#ffffff"):
    key = (kind, size, color)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = hex_rgb(color) + (255,)
    s = size
    m = s * 0.18
    w = max(2, int(round(s * 0.09)))
    if kind == "menu":
        for i in range(3):
            y = s * (0.28 + i * 0.22)
            d.rounded_rectangle((m, y, s - m, y + w), w / 2, fill=c)
    elif kind == "search":
        r = s * 0.28
        cx, cy = s * 0.44, s * 0.44
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=w)
        d.line((cx + r * 0.62, cy + r * 0.62, s - m * 0.7, s - m * 0.7), fill=c, width=w)
    elif kind == "home":
        d.polygon([(s * 0.5, m), (s - m, s * 0.48), (s - m, s - m), (m, s - m), (m, s * 0.48)], outline=c)
        d.line([(s * 0.5, m), (s - m, s * 0.48), (s - m, s - m), (m, s - m), (m, s * 0.48), (s * 0.5, m)], fill=c, width=w)
        d.rectangle((s * 0.40, s * 0.58, s * 0.60, s - m), outline=c, width=w)
    elif kind == "notscriptions":
        d.rectangle((m, m * 1.2, s - m, s - m), outline=c, width=w)
        d.polygon([(s * 0.40, s * 0.38), (s * 0.40, s * 0.72), (s * 0.70, s * 0.55)], fill=c)
    elif kind == "history":
        d.ellipse((m, m, s - m, s - m), outline=c, width=w)
        d.line((s * 0.5, s * 0.5, s * 0.5, s * 0.32), fill=c, width=w)
        d.line((s * 0.5, s * 0.5, s * 0.68, s * 0.58), fill=c, width=w)
    elif kind == "videos":
        d.rounded_rectangle((m, s * 0.28, s - m, s * 0.72), 3, outline=c, width=w)
        d.line((m, s * 0.22, s - m, s * 0.22), fill=c, width=max(1, w - 1))
        d.line((m + 2, s * 0.16, s - m - 2, s * 0.16), fill=c, width=max(1, w - 1))
    elif kind == "later":
        d.ellipse((m, m, s - m, s - m), outline=c, width=w)
        d.polygon([(s * 0.46, s * 0.34), (s * 0.46, s * 0.68), (s * 0.72, s * 0.51)], fill=c)
    elif kind == "liked":
        # thumbs up
        d.rounded_rectangle((m, s * 0.48, m + s * 0.18, s - m), 2, outline=c, width=w)
        d.polygon([
            (m + s * 0.18, s * 0.48), (s * 0.46, s * 0.48), (s * 0.50, m + 2),
            (s * 0.66, m + 2), (s * 0.70, s * 0.48), (s - m, s * 0.48),
            (s - m, s - m), (m + s * 0.18, s - m),
        ], outline=c)
        d.line([
            (m + s * 0.18, s * 0.48), (s * 0.46, s * 0.48), (s * 0.50, m + 2),
            (s * 0.66, m + 2), (s * 0.70, s * 0.48), (s - m, s * 0.48),
            (s - m, s - m), (m + s * 0.18, s - m),
        ], fill=c, width=w)
    elif kind == "create":
        # plus in a rounded square
        d.rounded_rectangle((m, m, s - m, s - m), 4, outline=c, width=w)
        d.line((s * 0.5, m + 5, s * 0.5, s - m - 5), fill=c, width=w)
        d.line((m + 5, s * 0.5, s - m - 5, s * 0.5), fill=c, width=w)
    elif kind == "updates":
        d.arc((m, m, s - m, s - m), 40, 300, fill=c, width=w)
        d.polygon([(s - m, s * 0.28), (s - m - 1, s * 0.52), (s * 0.62, s * 0.38)], fill=c)
    elif kind == "play":
        d.polygon([(s * 0.32, m), (s * 0.32, s - m), (s - m, s * 0.5)], fill=c)
    elif kind == "pause":
        d.rounded_rectangle((s * 0.28, m, s * 0.44, s - m), 2, fill=c)
        d.rounded_rectangle((s * 0.56, m, s * 0.72, s - m), 2, fill=c)
    elif kind == "next":
        d.polygon([(s * 0.22, m), (s * 0.22, s - m), (s * 0.62, s * 0.5)], fill=c)
        d.rectangle((s * 0.68, m, s * 0.80, s - m), fill=c)
    elif kind == "vol":
        d.polygon([(m, s * 0.38), (s * 0.36, s * 0.38), (s * 0.58, m), (s * 0.58, s - m),
                   (s * 0.36, s * 0.62), (m, s * 0.62)], fill=c)
        d.arc((s * 0.58, s * 0.28, s - m, s * 0.72), -70, 70, fill=c, width=w)
    elif kind == "mute":
        d.polygon([(m, s * 0.38), (s * 0.36, s * 0.38), (s * 0.58, m), (s * 0.58, s - m),
                   (s * 0.36, s * 0.62), (m, s * 0.62)], fill=c)
        d.line((s * 0.68, s * 0.32, s - m, s * 0.68), fill=c, width=w)
        d.line((s * 0.68, s * 0.68, s - m, s * 0.32), fill=c, width=w)
    elif kind == "full":
        d.line((m, s * 0.38, m, m, s * 0.38, m), fill=c, width=w)
        d.line((s - s * 0.38, m, s - m, m, s - m, s * 0.38), fill=c, width=w)
        d.line((m, s - s * 0.38, m, s - m, s * 0.38, s - m), fill=c, width=w)
        d.line((s - s * 0.38, s - m, s - m, s - m, s - m, s - s * 0.38), fill=c, width=w)
    elif kind == "share":
        d.ellipse((m, s * 0.38, m + s * 0.28, s * 0.38 + s * 0.28), outline=c, width=w)
        d.ellipse((s * 0.62, m, s * 0.62 + s * 0.28, m + s * 0.28), outline=c, width=w)
        d.ellipse((s * 0.62, s * 0.58, s * 0.62 + s * 0.28, s * 0.58 + s * 0.28), outline=c, width=w)
        d.line((m + s * 0.22, s * 0.48, s * 0.66, m + s * 0.18), fill=c, width=w)
        d.line((m + s * 0.22, s * 0.56, s * 0.66, s * 0.70), fill=c, width=w)
    elif kind == "save":
        d.polygon([(m + 2, m), (s - m - 2, m), (s - m - 2, s - m), (s * 0.5, s * 0.68), (m + 2, s - m)], outline=c)
        d.line([(m + 2, m), (s - m - 2, m), (s - m - 2, s - m), (s * 0.5, s * 0.68), (m + 2, s - m), (m + 2, m)], fill=c, width=w)
    elif kind == "studio":
        d.rectangle((m, s * 0.30, s * 0.40, s - m), outline=c, width=w)
        d.rectangle((s * 0.48, m, s - m, s * 0.55), outline=c, width=w)
        d.rectangle((s * 0.48, s * 0.63, s - m, s - m), outline=c, width=w)
    elif kind == "edit":
        d.line((m, s - m, s * 0.62, s * 0.30), fill=c, width=w)
        d.polygon([(s * 0.62, s * 0.30), (s - m, m), (s * 0.72, s * 0.42)], fill=c)
    elif kind == "trash":
        d.line((m, s * 0.30, s - m, s * 0.30), fill=c, width=w)
        d.line((s * 0.38, m + 2, s * 0.62, m + 2), fill=c, width=w)
        d.polygon([(m + 3, s * 0.30), (s - m - 3, s * 0.30), (s - m - 6, s - m), (m + 6, s - m)], outline=c)
        d.line([(m + 3, s * 0.30), (s - m - 3, s * 0.30), (s - m - 6, s - m), (m + 6, s - m), (m + 3, s * 0.30)], fill=c, width=w)
    elif kind == "check":
        d.line((m, s * 0.52, s * 0.42, s - m - 2, s - m, s * 0.28), fill=c, width=w + 1)
    elif kind == "chevron":
        d.line((s * 0.32, s * 0.38, s * 0.5, s * 0.62, s * 0.68, s * 0.38), fill=c, width=w)
    elif kind == "back":
        d.line((s * 0.62, m, s * 0.30, s * 0.5, s * 0.62, s - m), fill=c, width=w)
    elif kind == "thumbdown":
        d.rounded_rectangle((s - m - s * 0.18, m, s - m, s * 0.52), 2, outline=c, width=w)
        d.line([
            (s - m - s * 0.18, s * 0.52), (s * 0.54, s * 0.52), (s * 0.50, s - m - 2),
            (s * 0.34, s - m - 2), (s * 0.30, s * 0.52), (m, s * 0.52),
            (m, m), (s - m - s * 0.18, m),
        ], fill=c, width=w)
    elif kind == "person":
        d.ellipse((s * 0.32, m, s * 0.68, s * 0.50), outline=c, width=w)
        d.arc((m, s * 0.48, s - m, s + s * 0.4), 200, 340, fill=c, width=w)
    else:
        d.ellipse((m, m, s - m, s - m), outline=c, width=w)
    _ICON_CACHE[key] = im
    return im


def icon_photo(kind, size=24, color="#ffffff"):
    return ImageTk.PhotoImage(_icon_im(kind, size, color))


# -------------------- library --------------------
class Library:
    def __init__(self):
        self.data = self._empty()
        self.load()

    def _empty(self):
        return {
            "version": 1,
            "profile": {"name": "You"},
            "current_channel_id": "",
            "channels": [],
            "subscriptions": [],
            "videos": [],
            "history": [],
            "watch_later": [],
            "comments": {},
            "boost_all": {},
            "boost_stats": {"bot_views": 0, "bot_likes": 0, "bot_comments": 0, "bot_subs": 0},
        }

    def load(self):
        p = library_path()
        if not os.path.isfile(p):
            self.data = self._empty()
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                base = self._empty()
                base.update(raw)
                for k, v in self._empty().items():
                    if k not in base:
                        base[k] = v
                self.data = base
            else:
                self.data = self._empty()
        except Exception:
            self.data = self._empty()

    def save(self):
        tmp = library_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, library_path())

    # --- channels ---
    def channels(self):
        return list(self.data.get("channels") or [])

    def owned_channels(self):
        return [c for c in self.channels() if c.get("owned", True)]

    def get_channel(self, cid):
        for c in self.channels():
            if c.get("id") == cid:
                return c
        return None

    def get_channel_by_name(self, name):
        name = (name or "").strip().lower()
        for c in self.channels():
            if (c.get("name") or "").strip().lower() == name:
                return c
        return None

    def get_channel_by_handle(self, handle, name=""):
        h = normalize_handle(handle, name).lower()
        for c in self.channels():
            if normalize_handle(c.get("handle") or "", c.get("name") or "").lower() == h:
                return c
        return None

    def featured_channels(self):
        chs = [c for c in self.channels() if c.get("featured")]
        bundled = {}
        for i, spec in enumerate(FEATURED_CHANNELS):
            bundled[(spec.get("handle") or "").strip().lower()] = i
            bundled[(spec.get("name") or "").strip().lower()] = i

        def sort_key(c):
            if _is_kim_miyoyazu_channel(c):
                return (0, 0)
            h = normalize_handle(c.get("handle") or "", "").lower()
            n = (c.get("name") or "").strip().lower()
            rank = bundled.get(h)
            if rank is None:
                rank = bundled.get(n, 100)
            return (1, rank)

        chs.sort(key=sort_key)
        return chs

    def kim_miyoyazu_channel(self):
        """The user's owned Kim Miyoyazu channel, if present."""
        for c in self.channels():
            if _is_kim_miyoyazu_channel(c) and c.get("owned"):
                return c
        return None

    def haul_videos(self):
        out = []
        for v in self.videos():
            if v.get("is_short"):
                continue
            if v.get("category") == "haul" or (v.get("seed_file") or "").endswith("-haul.mp4"):
                out.append(v)
        return out

    def owner_added_videos(self, cid=None):
        out = []
        for v in self.videos():
            if not v.get("owner_added"):
                continue
            if cid and v.get("channel_id") != cid:
                continue
            out.append(v)
        return out

    def current_channel(self):
        cid = self.data.get("current_channel_id") or ""
        c = self.get_channel(cid)
        if c:
            return c
        owned = self.owned_channels()
        if owned:
            self.data["current_channel_id"] = owned[0]["id"]
            return owned[0]
        return None

    def switch_channel(self, cid):
        if self.get_channel(cid):
            self.data["current_channel_id"] = cid
            self.save()
            return True
        return False

    def add_channel(self, name, handle="", description="", avatar="", banner="",
                    owned=True, subscribers=0, created=None, featured=False):
        cid = new_id("ch")
        ch = {
            "id": cid,
            "name": (name or "My channel").strip()[:80],
            "handle": normalize_handle(handle, name),
            "description": (description or "").strip(),
            "avatar": avatar or "",
            "banner": banner or "",
            "subscribers": int(subscribers or 0),
            "bot_subscribers": 0,
            "created": created or time.strftime("%Y-%m-%dT%H:%M:%S"),
            "owned": bool(owned),
            "featured": bool(featured),
        }
        self.data.setdefault("channels", []).append(ch)
        if owned and not self.data.get("current_channel_id"):
            self.data["current_channel_id"] = cid
        self.save()
        return ch

    def update_channel(self, cid, **kw):
        ch = self.get_channel(cid)
        if not ch:
            return None
        for k in ("name", "handle", "description", "avatar", "banner"):
            if k in kw and kw[k] is not None:
                if k == "handle":
                    ch[k] = normalize_handle(kw[k], ch.get("name"))
                else:
                    ch[k] = kw[k]
        self.save()
        return ch

    def is_notscribed(self, cid):
        return cid in (self.data.get("subscriptions") or [])

    def toggle_notscribe(self, cid):
        ch = self.get_channel(cid)
        if not ch:
            return False
        subs = self.data.setdefault("subscriptions", [])
        if cid in subs:
            subs.remove(cid)
            ch["subscribers"] = max(0, int(ch.get("subscribers") or 0) - 1)
            on = False
        else:
            subs.insert(0, cid)
            ch["subscribers"] = int(ch.get("subscribers") or 0) + 1
            on = True
        self.save()
        return on

    # --- videos ---
    def videos(self):
        return list(self.data.get("videos") or [])

    def get_video(self, vid):
        for v in self.data.get("videos") or []:
            if v.get("id") == vid:
                return v
        return None

    def channel_videos(self, cid):
        return [v for v in self.videos() if v.get("channel_id") == cid]

    def owned_videos(self, cid=None):
        if cid:
            return self.channel_videos(cid)
        owned = {c["id"] for c in self.owned_channels()}
        return [v for v in self.videos() if v.get("channel_id") in owned]

    def shorts(self, cid=None):
        vids = self.channel_videos(cid) if cid else self.videos()
        return [v for v in vids if v.get("is_short")]

    def long_videos(self, cid=None):
        vids = self.channel_videos(cid) if cid else self.videos()
        return [v for v in vids if not v.get("is_short")]

    def import_video(self, src, title, description, channel_id, thumb_src=None, uploaded=None,
                     views=0, likes=0, is_short=None, seed_file=None, category="",
                     seed_id="", owner_added=False):
        if not src or not os.path.isfile(src):
            raise FileNotFoundError(src)
        ch = self.get_channel(channel_id)
        if not ch:
            raise ValueError("No channel")
        vid = new_id("v")
        ext = os.path.splitext(src)[1].lower() or ".mp4"
        dest = os.path.join(app_data_dir(), "videos", vid + ext)
        shutil.copy2(src, dest)
        info = probe_media(dest)
        dur = info["duration"] or probe_duration(dest)
        if is_short is None:
            is_short = looks_like_short(dest, info)
        is_short = bool(is_short)
        thumb = os.path.join(app_data_dir(), "thumbs", vid + ".jpg")
        custom = False
        tw, th = (360, 640) if is_short else (640, 360)
        if thumb_src and os.path.isfile(thumb_src):
            try:
                im = Image.open(thumb_src).convert("RGB")
                cover_fit(im, tw, th).save(thumb, "JPEG", quality=90)
                custom = True
            except Exception:
                custom = False
        if not custom:
            if not grab_thumb(dest, thumb, dur, vertical=is_short):
                Image.new("RGB", (tw, th), (30, 30, 30)).save(thumb, "JPEG")
        entry = {
            "id": vid,
            "title": (title or os.path.splitext(os.path.basename(src))[0]).strip()[:200],
            "description": (description or "").strip(),
            "channel_id": channel_id,
            "path": dest,
            "thumb": thumb,
            "duration": dur,
            "views": int(views or 0),
            "likes": int(likes or 0),
            "dislikes": 0,
            "liked_by_me": False,
            "disliked_by_me": False,
            "uploaded": uploaded or time.strftime("%Y-%m-%dT%H:%M:%S"),
            "custom_thumb": custom,
            "bot_views": 0,
            "is_short": is_short,
            "boost": {"on": False, "intensity": "medium", "last_tick": time.time()},
            "category": (category or "").strip(),
        }
        if seed_file:
            entry["seed_file"] = seed_file
        if seed_id:
            entry["seed_id"] = seed_id
        if owner_added:
            entry["owner_added"] = True
        self.data.setdefault("videos", []).insert(0, entry)
        self.save()
        return entry

    def update_video(self, vid, **kw):
        v = self.get_video(vid)
        if not v:
            return None
        for k in ("title", "description"):
            if k in kw and kw[k] is not None:
                v[k] = kw[k]
        if kw.get("thumb_src") and os.path.isfile(kw["thumb_src"]):
            try:
                im = Image.open(kw["thumb_src"]).convert("RGB")
                cover_fit(im, 640, 360).save(v["thumb"], "JPEG", quality=90)
                v["custom_thumb"] = True
            except Exception:
                pass
        self.save()
        return v

    def delete_video(self, vid):
        v = self.get_video(vid)
        if not v:
            return False
        self.data["videos"] = [x for x in self.data.get("videos") or [] if x.get("id") != vid]
        self.data["history"] = [h for h in self.data.get("history") or [] if (h.get("id") if isinstance(h, dict) else h) != vid]
        self.data["watch_later"] = [x for x in self.data.get("watch_later") or [] if x != vid]
        (self.data.get("comments") or {}).pop(vid, None)
        for p in (v.get("path"), v.get("thumb")):
            try:
                if p and os.path.isfile(p) and os.path.abspath(p).startswith(os.path.abspath(app_data_dir())):
                    os.remove(p)
            except Exception:
                pass
        self.save()
        return True

    def increment_views(self, vid):
        v = self.get_video(vid)
        if not v:
            return
        v["views"] = int(v.get("views") or 0) + 1
        hist = self.data.setdefault("history", [])
        hist[:] = [h for h in hist if (h.get("id") if isinstance(h, dict) else h) != vid]
        hist.insert(0, {"id": vid, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self.save()

    def toggle_like(self, vid, up=True):
        v = self.get_video(vid)
        if not v:
            return
        if up:
            if v.get("liked_by_me"):
                v["liked_by_me"] = False
                v["likes"] = max(0, int(v.get("likes") or 0) - 1)
            else:
                v["liked_by_me"] = True
                v["likes"] = int(v.get("likes") or 0) + 1
                if v.get("disliked_by_me"):
                    v["disliked_by_me"] = False
                    v["dislikes"] = max(0, int(v.get("dislikes") or 0) - 1)
        else:
            if v.get("disliked_by_me"):
                v["disliked_by_me"] = False
                v["dislikes"] = max(0, int(v.get("dislikes") or 0) - 1)
            else:
                v["disliked_by_me"] = True
                v["dislikes"] = int(v.get("dislikes") or 0) + 1
                if v.get("liked_by_me"):
                    v["liked_by_me"] = False
                    v["likes"] = max(0, int(v.get("likes") or 0) - 1)
        self.save()

    def toggle_watch_later(self, vid):
        wl = self.data.setdefault("watch_later", [])
        if vid in wl:
            wl.remove(vid)
            on = False
        else:
            wl.insert(0, vid)
            on = True
        self.save()
        return on

    def in_watch_later(self, vid):
        return vid in (self.data.get("watch_later") or [])

    def add_comment(self, vid, text, author="You", bot=False):
        text = (text or "").strip()
        if not text:
            return None
        c = {
            "id": new_id("c"),
            "author": author,
            "text": text,
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "bot": bool(bot),
        }
        self.data.setdefault("comments", {}).setdefault(vid, []).insert(0, c)
        self.save()
        return c

    def comments_for(self, vid):
        return list(self.data.get("comments", {}).get(vid) or [])

    def search(self, q):
        q = (q or "").strip().lower()
        if not q:
            return self.videos()
        out = []
        for v in self.videos():
            ch = self.get_channel(v.get("channel_id")) or {}
            blob = " ".join([
                v.get("title") or "",
                v.get("description") or "",
                ch.get("name") or "",
                ch.get("handle") or "",
            ]).lower()
            if q in blob:
                out.append(v)
        return out

    def history_videos(self):
        found = []
        for h in self.data.get("history") or []:
            vid = h.get("id") if isinstance(h, dict) else h
            v = self.get_video(vid)
            if v:
                found.append(v)
        return found

    def liked_videos(self):
        return [v for v in self.videos() if v.get("liked_by_me")]

    def watch_later_videos(self):
        out = []
        for vid in self.data.get("watch_later") or []:
            v = self.get_video(vid)
            if v:
                out.append(v)
        return out

    def notscription_videos(self):
        subs = set(self.data.get("subscriptions") or [])
        vids = [v for v in self.videos() if v.get("channel_id") in subs]
        vids.sort(key=lambda v: v.get("uploaded") or "", reverse=True)
        return vids

    def channel_stats(self, cid):
        vids = self.channel_videos(cid)
        views = sum(int(v.get("views") or 0) for v in vids)
        likes = sum(int(v.get("likes") or 0) for v in vids)
        comments = sum(len(self.comments_for(v["id"])) for v in vids)
        bot_views = sum(int(v.get("bot_views") or 0) for v in vids)
        ch = self.get_channel(cid) or {}
        return {
            "videos": len(vids),
            "views": views,
            "likes": likes,
            "comments": comments,
            "notscribers": int(ch.get("subscribers") or 0),
            "bot_views": bot_views,
        }

    def total_bot_views(self):
        n = sum(int(v.get("bot_views") or 0) for v in self.videos())
        return n

    # --- bot booster ---
    def _video_intensity(self, v):
        # NOT TUBE BOT ACCOUNTS are automated and always on, at Rocket speed,
        # until the video reaches BOT_TARGET bot views.
        if int(v.get("bot_views") or 0) >= BOT_TARGET:
            return None
        return "rocket"

    def set_boost_all(self, cid, on, intensity="medium"):
        ba = self.data.setdefault("boost_all", {})
        prev = ba.get(cid) or {}
        ba[cid] = {
            "on": bool(on),
            "intensity": intensity if intensity in INTENSITY_VPM else "medium",
            "last_tick": time.time() if on else prev.get("last_tick", time.time()),
        }
        self.save()

    def set_boost_video(self, vid, on, intensity=None):
        v = self.get_video(vid)
        if not v:
            return
        b = v.get("boost") or {"on": False, "intensity": "medium", "last_tick": time.time()}
        b["on"] = bool(on)
        if intensity in INTENSITY_VPM:
            b["intensity"] = intensity
        if on:
            b["last_tick"] = time.time()
        v["boost"] = b
        self.save()

    def apply_boosts(self, now=None):
        now = time.time() if now is None else now
        added = {"views": 0, "likes": 0, "subs": 0, "comments": 0}
        touched_all = set()
        any_change = False
        for v in list(self.data.get("videos") or []):
            inten = self._video_intensity(v)
            if not inten:
                continue
            vb = v.setdefault("boost", {"on": True, "intensity": "rocket", "last_tick": now})
            vb["on"] = True; vb["intensity"] = "rocket"
            last = float(vb.get("last_tick") or now)
            elapsed = min(BOOST_CATCHUP_CAP, max(0.0, now - last))
            if elapsed < 0.25:
                continue
            vmin, vmax = INTENSITY_VPM[inten]
            rate = random.uniform(vmin, vmax)
            views_add = int(round(rate * elapsed / 60.0 * random.uniform(0.85, 1.18)))
            if views_add <= 0 and elapsed >= 0.8:
                if inten == "rocket":
                    views_add = random.randint(50, 170)
                elif inten == "medium":
                    views_add = random.randint(3, 12)
                else:
                    views_add = 1 if random.random() < 0.8 else 0
            views_add = max(0, min(views_add, BOT_TARGET - int(v.get("bot_views") or 0)))
            likes_add = int(round(views_add * random.uniform(0.015, 0.04)))
            if views_add and likes_add == 0 and random.random() < 0.25:
                likes_add = 1
            sub_pm = INTENSITY_SUB_PM[inten]
            subs_add = int(round(sub_pm * elapsed / 60.0 * random.uniform(0.7, 1.3)))
            if subs_add == 0 and inten == "rocket" and elapsed >= 0.8 and random.random() < 0.6:
                subs_add = random.randint(1, 2)
            elif subs_add == 0 and elapsed >= 2 and random.random() < 0.15:
                subs_add = 1
            cmt_s = INTENSITY_CMT_S[inten]
            n_cmt = min(8, int(elapsed / cmt_s))
            if n_cmt == 0 and elapsed >= 1 and random.random() < min(0.85, elapsed / cmt_s):
                n_cmt = 1
            if views_add:
                v["views"] = int(v.get("views") or 0) + views_add
                v["bot_views"] = int(v.get("bot_views") or 0) + views_add
                added["views"] += views_add
                any_change = True
            if likes_add:
                v["likes"] = int(v.get("likes") or 0) + likes_add
                added["likes"] += likes_add
                any_change = True
            if subs_add:
                ch = self.get_channel(v.get("channel_id"))
                if ch:
                    ch["subscribers"] = int(ch.get("subscribers") or 0) + subs_add
                    ch["bot_subscribers"] = int(ch.get("bot_subscribers") or 0) + subs_add
                    added["subs"] += subs_add
                    any_change = True
            for _ in range(n_cmt):
                self.add_comment(v["id"], random.choice(BOT_COMMENTS), author=bot_name(), bot=True)
                added["comments"] += 1
                any_change = True
            vb["last_tick"] = now
            v["boost"] = vb
            touched_all.add(v.get("channel_id"))
        ba = self.data.setdefault("boost_all", {})
        for cid in list(ba.keys()):
            if ba[cid].get("on"):
                ba[cid]["last_tick"] = now
        if any_change:
            st = self.data.setdefault("boost_stats", {"bot_views": 0, "bot_likes": 0, "bot_comments": 0, "bot_subs": 0})
            st["bot_views"] = int(st.get("bot_views") or 0) + added["views"]
            st["bot_likes"] = int(st.get("bot_likes") or 0) + added["likes"]
            st["bot_comments"] = int(st.get("bot_comments") or 0) + added["comments"]
            st["bot_subs"] = int(st.get("bot_subs") or 0) + added["subs"]
            self.save()
        return added

    def copy_image_asset(self, src, kind, cid):
        if not src or not os.path.isfile(src):
            return ""
        ext = os.path.splitext(src)[1].lower() or (".png" if kind == "avatars" else ".jpg")
        dest = os.path.join(app_data_dir(), kind, cid + ext)
        try:
            im = Image.open(src).convert("RGB")
            if kind == "avatars":
                cover_fit(im, 512, 512).save(dest if dest.lower().endswith(".jpg") or dest.lower().endswith(".jpeg") else dest.replace(ext, ".png"),
                                               "JPEG" if dest.lower().endswith((".jpg", ".jpeg")) else "PNG", quality=92)
                if not dest.lower().endswith((".jpg", ".jpeg")):
                    dest = dest if dest.lower().endswith(".png") else os.path.splitext(dest)[0] + ".png"
                    cover_fit(im, 512, 512).save(dest, "PNG")
            else:
                cover_fit(im, 1280, 360).save(os.path.splitext(dest)[0] + ".jpg", "JPEG", quality=90)
                dest = os.path.splitext(dest)[0] + ".jpg"
            return dest
        except Exception:
            try:
                shutil.copy2(src, dest)
                return dest
            except Exception:
                return ""


# -------------------- widgets --------------------
class VScroll(tk.Frame):
    def __init__(self, master, bg=BG, **kw):
        super().__init__(master, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self._set_bar)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._inner)
        self.canvas.bind("<Configure>", self._outer)
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))
        self.inner.bind("<Enter>", lambda e: self._bind_wheel(True))
        self._wheel_on = False
        self._bar_visible = False

    def _set_bar(self, first, last):
        self.bar.set(first, last)
        need = float(first) > 0.0 or float(last) < 1.0
        if need and not self._bar_visible:
            self.bar.pack(side="right", fill="y")
            self._bar_visible = True
        elif not need and self._bar_visible:
            self.bar.pack_forget()
            self._bar_visible = False

    def _inner(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _outer(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def _bind_wheel(self, on):
        self._wheel_on = on
        if on:
            self.canvas.bind_all("<MouseWheel>", self._wheel)
        else:
            try:
                self.canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass

    def _wheel(self, e):
        if not self._wheel_on:
            return
        delta = int(-1 * (e.delta / 120)) if e.delta else 0
        self.canvas.yview_scroll(delta, "units")

    def to_top(self):
        self.canvas.yview_moveto(0)

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()


class Pill(tk.Label):
    """Rounded pill button."""

    def __init__(self, master, text, cmd=None, fill=CARD, fg=TXT, hover=HOVER,
                 radius=16, padx=14, pady=7, font=None, outline=None, **kw):
        self._cmd = cmd
        self._fill = fill
        self._hover = hover or fill
        self._fg = fg
        self._radius = radius
        self._padx = padx
        self._pady = pady
        self._outline = outline
        self._font = font or (FONT_UI, 10)
        self._photos = {}
        super().__init__(master, text=text, fg=fg, bg=getattr(master, "cget", lambda a: BG)("bg") if hasattr(master, "cget") else BG,
                         font=self._font, cursor="hand2" if cmd else "arrow", bd=0, padx=padx, pady=pady)
        try:
            self.configure(bg=master.cget("bg"))
        except Exception:
            self.configure(bg=BG)
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._paint(True))
        self.bind("<Leave>", lambda e: self._paint(False))
        self.after_idle(lambda: self._paint(False))

    def _click(self, _e=None):
        if self._cmd:
            self._cmd()

    def set_text(self, text):
        self.configure(text=text)
        self._paint(False)

    def set_style(self, fill=None, fg=None, outline=None):
        if fill is not None:
            self._fill = fill
        if fg is not None:
            self._fg = fg
            self.configure(fg=fg)
        if outline is not None:
            self._outline = outline
        self._paint(False)

    def _paint(self, hover):
        try:
            f = tkfont.Font(font=self._font)
            tw = f.measure(self.cget("text") or "") + int(self._padx) * 2 + 4
            th = f.metrics("linespace") + int(self._pady) * 2
        except Exception:
            tw, th = 80, 32
        tw = max(28, min(int(tw), 420))
        th = max(24, min(int(th), 48))
        fill = self._hover if hover else self._fill
        im = rounded_fill(tw, th, min(self._radius, th // 2), fill, self._outline)
        ph = photo_of(im)
        self._photos["bg"] = ph
        self.configure(image=ph, compound="center", fg=self._fg, text=self.cget("text"),
                       width=tw, height=th)


class IconBtn(tk.Label):
    def __init__(self, master, kind, cmd=None, size=24, color=TXT, bg=BG, hover=CARD, pad=8):
        self._cmd = cmd
        self._bg = bg
        self._hover = hover
        self._photos = {
            "n": icon_photo(kind, size, color),
        }
        super().__init__(master, image=self._photos["n"], bg=bg, cursor="hand2" if cmd else "arrow",
                         bd=0, padx=pad, pady=pad)
        self.bind("<Button-1>", lambda e: self._cmd and self._cmd())
        self.bind("<Enter>", lambda e: self.configure(bg=self._hover))
        self.bind("<Leave>", lambda e: self.configure(bg=self._bg))

    def set_bg(self, bg, hover=None):
        self._bg = bg
        if hover:
            self._hover = hover
        self.configure(bg=bg)


class SeekBar(tk.Canvas):
    def __init__(self, master, command=None, bg=BG, height=16):
        super().__init__(master, height=height, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.val = 0.0  # 0..1
        self._drag = False
        self._cmd = command
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._down)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", self._up)

    def set(self, v):
        if self._drag:
            return
        self.val = max(0.0, min(1.0, float(v)))
        self.redraw()

    def _pos(self, ev):
        w = max(1, self.winfo_width())
        return max(0.0, min(1.0, ev.x / float(w)))

    def _down(self, ev):
        self._drag = True
        self.val = self._pos(ev)
        self.redraw()

    def _move(self, ev):
        self.val = self._pos(ev)
        self.redraw()

    def _up(self, ev):
        self.val = self._pos(ev)
        self._drag = False
        self.redraw()
        if self._cmd:
            self._cmd(self.val)

    def redraw(self):
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        y = h // 2
        self.create_line(0, y, w, y, fill=DIM, width=3)
        x = int(self.val * w)
        if x > 0:
            self.create_line(0, y, x, y, fill=WHITE, width=3)
        r = 6 if self._drag else 5
        self.create_oval(x - r, y - r, x + r, y + r, fill=WHITE, outline="")


class VolBar(tk.Canvas):
    def __init__(self, master, command=None, bg=BG, width=70, height=16):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.val = 1.0
        self._cmd = command
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<ButtonPress-1>", self._set)
        self.bind("<B1-Motion>", self._set)

    def _set(self, ev):
        w = max(1, self.winfo_width())
        self.val = max(0.0, min(1.0, ev.x / float(w)))
        self.redraw()
        if self._cmd:
            self._cmd(self.val)

    def set(self, v):
        self.val = max(0.0, min(1.0, float(v)))
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        y = h // 2
        self.create_line(0, y, w, y, fill=DIM, width=3)
        x = int(self.val * w)
        if x > 0:
            self.create_line(0, y, x, y, fill=WHITE, width=3)


class NavRow(tk.Frame):
    def __init__(self, master, kind, label, cmd, app, compact=False, photo=None):
        super().__init__(master, bg=BG, cursor="hand2")
        self.app = app
        self.kind = kind
        self._cmd = cmd
        self._label = label
        self._active = False
        if photo is not None:
            self._photos = {"n": photo, "d": photo}
        else:
            self._photos = {
                "n": icon_photo(kind, 22, TXT),
                "d": icon_photo(kind, 22, MUT),
            }
        self.ico = tk.Label(self, image=self._photos["n"], bg=BG, bd=0)
        self.ico.pack(side="left", padx=(16, 16), pady=8)
        self.lbl = tk.Label(self, text=label, bg=BG, fg=TXT, font=(FONT_UI, 11), anchor="w")
        self.lbl.pack(side="left", fill="x", expand=True, pady=8)
        for w in (self, self.ico, self.lbl):
            w.bind("<Button-1>", lambda e: self._cmd())
            w.bind("<Enter>", lambda e: self._hover(True))
            w.bind("<Leave>", lambda e: self._hover(False))
        self.set_compact(compact)

    def set_compact(self, compact):
        if compact:
            self.lbl.pack_forget()
            self.ico.pack_configure(padx=24)
        else:
            self.ico.pack_configure(padx=(16, 16))
            if not self.lbl.winfo_ismapped():
                self.lbl.pack(side="left", fill="x", expand=True, pady=8)

    def set_active(self, on):
        self._active = on
        bg = CARD if on else BG
        for w in (self, self.ico, self.lbl):
            w.configure(bg=bg)

    def _hover(self, on):
        if self._active:
            return
        bg = HOVER if on else BG
        for w in (self, self.ico, self.lbl):
            w.configure(bg=bg)


# -------------------- application --------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NOT TUBE")
        self.configure(bg=BG)
        self.minsize(1100, 700)
        self.geometry("1400x900+40+20")
        init_fonts(self)
        self._style()
        try:
            self.iconbitmap(res_path("assets", "logo.ico"))
        except Exception:
            try:
                self.iconphoto(True, ImageTk.PhotoImage(Image.open(res_path("assets", "icon256.png"))))
            except Exception:
                pass

        self.lib = Library()
        try:
            ensure_bundled_content(self.lib)
        except Exception:
            pass
        self.page = "home"
        self.sidebar_open = True
        self.chip = "All"
        self.search_q = ""
        self.watch_id = None
        self.shorts_id = None
        self.channel_id = None
        self._player_loop = False
        self.studio_tab = "dashboard"
        self._photos = {}
        self._toasts = []
        self._grid_after = None
        self._grid_w = 0
        self._menu = None
        self._switcher = None
        self._unsub_menu = None
        self._fullscreen = False
        self._chrome_hidden = False

        # player state
        self.player_path = None
        self.player_t = 0.0
        self.player_dur = 0.0
        self.player_playing = False
        self.player_proc = None
        self.player_job = None
        self.player_frame = None
        self.player_w, self.player_h = PLAY_W, PLAY_H
        self._player_photo = None
        self._audio_tmp = None
        self._volume = 1.0
        self._muted = False
        self._pipe_t0 = 0.0
        self._pipe_start = 0.0
        self._boost_job = None
        self._live_rate = 0

        self._load_brand()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<space>", self._key_space)
        self.bind("<Left>", lambda e: self._key_seek(-5))
        self.bind("<Right>", lambda e: self._key_seek(5))
        self.bind("f", lambda e: self._key_full())
        self.bind("<Escape>", self._key_esc)
        self.bind("m", lambda e: self._key_mute())
        self.bind("<Up>", lambda e: self._shorts_key(-1))
        self.bind("<Down>", lambda e: self._shorts_key(1))
        self.after(400, self._boost_tick)

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TScrollbar",
                        background=CARD, troughcolor=BG, bordercolor=BG,
                        arrowcolor=MUT, relief="flat", lightcolor=CARD, darkcolor=CARD)
        style.map("TScrollbar", background=[("active", HOVER)])
        style.configure("TEntry", fieldbackground=SEARCH_BG, foreground=TXT,
                        background=SEARCH_BG, insertcolor=TXT, bordercolor=BORDER)
        self.option_add("*Font", (FONT_UI, 10))
        self.option_add("*Background", BG)
        self.option_add("*Foreground", TXT)
        self.option_add("*Listbox.background", CARD)
        self.option_add("*Listbox.foreground", TXT)

    def _load_brand(self):
        try:
            raw = Image.open(res_path("assets", "logo_badge.png")).convert("RGBA")
        except Exception:
            try:
                raw = Image.open(res_path("assets", "logo_source.jpg")).convert("RGB")
            except Exception:
                raw = Image.new("RGB", (72, 72), (26, 28, 40))
        self._photos["logo32"] = ImageTk.PhotoImage(raw.resize((32, 32), Image.Resampling.LANCZOS))
        self._photos["logo36"] = ImageTk.PhotoImage(raw.resize((36, 36), Image.Resampling.LANCZOS))
        for s in (24, 28, 32, 48, 64):
            try:
                im = Image.open(res_path("assets", "not_shorts_%d.png" % s)).convert("RGBA")
                self._photos["shorts_%d" % s] = ImageTk.PhotoImage(im)
            except Exception:
                self._photos["shorts_%d" % s] = icon_photo("play", s, TXT)
        try:
            self._photos["shorts_badge"] = ImageTk.PhotoImage(
                Image.open(res_path("assets", "not_shorts_badge.png")).convert("RGBA").resize((28, 28), Image.Resampling.LANCZOS)
            )
            self._photos["shorts_color"] = ImageTk.PhotoImage(
                Image.open(res_path("assets", "not_shorts_color_64.png")).convert("RGB")
            )
        except Exception:
            self._photos["shorts_badge"] = self._photos.get("shorts_28")
            self._photos["shorts_color"] = self._photos.get("shorts_64")

    # ---------- chrome ----------
    def _build(self):
        self._build_top()
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self.body = body
        self.sidebar = tk.Frame(body, bg=BG, width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar()
        self.right = tk.Frame(body, bg=BG)
        self.right.pack(side="left", fill="both", expand=True)
        self.chip_host = tk.Frame(self.right, bg=BG)
        self.chip_host.pack(fill="x")
        self._build_chips()
        self.content = tk.Frame(self.right, bg=BG)
        self.content.pack(fill="both", expand=True)
        self.show_page("home")

    def _build_top(self):
        top = tk.Frame(self, bg=BAR, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)
        self.top = top
        left = tk.Frame(top, bg=BAR)
        left.pack(side="left", padx=(4, 8))
        self.btn_menu = IconBtn(left, "menu", self.toggle_sidebar, size=22, bg=BAR, hover=CARD, pad=10)
        self.btn_menu.pack(side="left")
        brand = tk.Frame(left, bg=BAR, cursor="hand2")
        brand.pack(side="left", padx=(4, 0))
        tk.Label(brand, image=self._photos["logo36"], bg=BAR, bd=0).pack(side="left")
        tk.Label(brand, text="NOT TUBE", bg=BAR, fg=TXT, font=(FONT_UI, 16, "bold")).pack(side="left", padx=(8, 0))
        for w in brand.winfo_children() + [brand]:
            w.bind("<Button-1>", lambda e: self.show_page("home"))

        right = tk.Frame(top, bg=BAR)
        right.pack(side="right", padx=12)
        create = tk.Frame(right, bg=BAR)
        create.pack(side="left", padx=4)
        self._photos["ic_create"] = icon_photo("create", 18, TXT)
        self.btn_create = Pill(create, "  Create", self.open_studio_upload, fill=CARD, fg=TXT,
                               hover=HOVER, radius=18, padx=12, pady=6, font=(FONT_UI, 10, "bold"))
        self.btn_create.pack()
        # overlay plus is in the text
        self.btn_updates = Pill(right, "Check for updates", self.check_updates, fill=CARD, fg=TXT,
                                hover=HOVER, radius=18, padx=12, pady=6, font=(FONT_UI, 10))
        self.btn_updates.pack(side="left", padx=6)
        self.avatar_lbl = tk.Label(right, bg=BAR, cursor="hand2", bd=0)
        self.avatar_lbl.pack(side="left", padx=(8, 4))
        self.avatar_lbl.bind("<Button-1>", lambda e: self._avatar_menu())
        self._refresh_avatar()

        # centered search pill
        self.search_wrap = tk.Frame(top, bg=BAR)
        self._build_search_pill(self.search_wrap)
        self.search_wrap.place(relx=0.5, rely=0.5, anchor="center")
        top.bind("<Configure>", lambda e: self._place_search())

        tk.Frame(self, bg=CARD, height=1).pack(fill="x")

    def _place_search(self):
        # keep the pill visually centered, shrink if needed
        try:
            tw = self.top.winfo_width()
        except Exception:
            return
        w = min(640, max(280, tw - 620))
        self.search_wrap.place_configure(relx=0.5, rely=0.5, anchor="center", width=w, height=40)

    def _build_search_pill(self, host):
        host.configure(bg=BAR)
        self._search_canvas = tk.Canvas(host, bg=BAR, highlightthickness=0, bd=0, height=40)
        self._search_canvas.pack(fill="both", expand=True)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            host, textvariable=self.search_var, bg=SEARCH_BG, fg=TXT, insertbackground=TXT,
            relief="flat", bd=0, font=(FONT_UI, 12), highlightthickness=0,
        )
        self.search_entry.bind("<Return>", lambda e: self.do_search())
        self.search_entry.bind("<FocusIn>", lambda e: self._paint_search())
        self._photos["ic_search"] = icon_photo("search", 18, TXT)
        self.search_go = tk.Label(
            host, image=self._photos["ic_search"], bg=SEARCH_BTN, cursor="hand2",
            padx=16, pady=8,
        )
        self.search_go.bind("<Button-1>", lambda e: self.do_search())
        host.bind("<Configure>", lambda e: self._paint_search())

    def _paint_search(self):
        cv = self._search_canvas
        try:
            w, h = self.search_wrap.winfo_width(), self.search_wrap.winfo_height()
        except Exception:
            return
        if w < 40 or h < 20:
            return
        cv.delete("all")
        cv.configure(width=w, height=h)
        btn_w = 64
        left_w = max(40, w - btn_w)
        r = h // 2
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, left_w + 2, h - 1), r, fill=SEARCH_BG, outline=BORDER, width=1)
        d.rounded_rectangle((left_w - r, 0, w - 1, h - 1), r, fill=SEARCH_BTN)
        d.rectangle((left_w - r, 1, left_w, h - 2), fill=SEARCH_BTN)
        ph = photo_of(im)
        self._photos["search_bg"] = ph
        cv.create_image(0, 0, image=ph, anchor="nw")
        # place entry and button on top of canvas
        self.search_entry.place(x=16, y=8, width=left_w - 28, height=h - 16)
        self.search_go.place(x=left_w, y=0, width=btn_w, height=h)
        self.search_go.configure(bg=SEARCH_BTN)
        self.search_entry.lift()
        self.search_go.lift()

    def _refresh_avatar(self):
        ch = self.lib.current_channel()
        im = self._channel_avatar_im(ch, 32) if ch else initials_avatar("You", 32)
        ph = ImageTk.PhotoImage(circle_avatar(im, 32))
        self._photos["top_avatar"] = ph
        try:
            self.avatar_lbl.configure(image=ph)
        except Exception:
            pass

    def _channel_avatar_im(self, ch, size=36):
        path = (ch or {}).get("avatar") or ""
        if path and os.path.isfile(path):
            try:
                return Image.open(path).convert("RGB")
            except Exception:
                pass
        return initials_avatar((ch or {}).get("name") or "?", size * 2)

    def _avatar_photo(self, ch, size=36):
        key = ("av", (ch or {}).get("id"), (ch or {}).get("avatar"), size)
        # always rebuild is cheap enough at small sizes; cache by mtime
        path = (ch or {}).get("avatar") or ""
        mt = int(os.path.getmtime(path)) if path and os.path.isfile(path) else 0
        key = ("av", (ch or {}).get("id"), mt, size)
        if key not in self._photos:
            im = self._channel_avatar_im(ch, size)
            self._photos[key] = ImageTk.PhotoImage(circle_avatar(im, size))
        return self._photos[key]

    def _build_sidebar(self):
        for w in self.sidebar.winfo_children():
            w.destroy()
        compact = not self.sidebar_open
        self.sidebar.configure(width=72 if compact else 240)
        sc = VScroll(self.sidebar, bg=BG)
        sc.pack(fill="both", expand=True)
        inner = sc.inner
        tk.Frame(inner, bg=BG, height=8).pack(fill="x")
        self._nav = {}
        items = [
            ("home", "home", "Home"),
            ("shorts", "shorts", "NOT SHORTS"),
            ("notscriptions", "notscriptions", "Notscriptions"),
            None,
            ("you_hdr", None, "You"),
            ("history", "history", "History"),
            ("your", "videos", "Your videos"),
            ("later", "later", "Watch later"),
            ("liked", "liked", "Liked videos"),
        ]
        for item in items:
            if item is None:
                tk.Frame(inner, bg=CARD, height=1).pack(fill="x", padx=12, pady=8)
                continue
            key, kind, label = item
            if kind is None:
                if compact:
                    continue
                tk.Label(inner, text=label, bg=BG, fg=TXT, font=(FONT_UI, 11, "bold"),
                         anchor="w").pack(fill="x", padx=16, pady=(4, 2))
                continue
            photo = self._photos.get("shorts_28") if key == "shorts" else None
            row = NavRow(inner, kind, label, lambda k=key: self._nav_go(k), self, compact=compact, photo=photo)
            row.pack(fill="x", padx=8, pady=1)
            self._nav[key] = row
        # Notscriptions list
        if not compact:
            tk.Frame(inner, bg=CARD, height=1).pack(fill="x", padx=12, pady=8)
            tk.Label(inner, text="Notscriptions", bg=BG, fg=TXT, font=(FONT_UI, 11, "bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(2, 6))
            subs = [self.lib.get_channel(cid) for cid in (self.lib.data.get("subscriptions") or [])]
            subs = [c for c in subs if c]
            if not subs:
                tk.Label(inner, text="No notscriptions yet", bg=BG, fg=DIM, font=(FONT_UI, 9),
                         anchor="w").pack(fill="x", padx=16, pady=4)
            for ch in subs:
                self._sidebar_channel_row(inner, ch)
        # footer
        tk.Frame(inner, bg=BG, height=16).pack()
        if not compact:
            tk.Label(inner, text=COPYRIGHT, bg=BG, fg=DIM, font=(FONT_UI, 8),
                     wraplength=200, justify="left", anchor="w").pack(fill="x", padx=16, pady=(8, 16))
        self._mark_nav()

    def _sidebar_channel_row(self, parent, ch):
        row = tk.Frame(parent, bg=BG, cursor="hand2")
        row.pack(fill="x", padx=8, pady=1)
        av = tk.Label(row, image=self._avatar_photo(ch, 24), bg=BG, bd=0)
        av.pack(side="left", padx=(12, 10), pady=6)
        lb = tk.Label(row, text=ch.get("name") or "", bg=BG, fg=TXT, font=(FONT_UI, 10),
                      anchor="w")
        lb.pack(side="left", fill="x", expand=True)
        def go(_e=None, cid=ch["id"]):
            self.open_channel(cid)
        for w in (row, av, lb):
            w.bind("<Button-1>", go)
            w.bind("<Enter>", lambda e, r=row, a=av, l=lb: [x.configure(bg=HOVER) for x in (r, a, l)])
            w.bind("<Leave>", lambda e, r=row, a=av, l=lb: [x.configure(bg=BG) for x in (r, a, l)])

    def _mark_nav(self):
        for k, row in (self._nav or {}).items():
            row.set_active(self.page == k and self.page not in ("watch", "channel", "studio", "search"))

    def toggle_sidebar(self):
        if self.page == "studio":
            self.show_page("home")
            return
        self.sidebar_open = not self.sidebar_open
        self._build_sidebar()

    def _build_chips(self, names=None):
        for w in self.chip_host.winfo_children():
            w.destroy()
        bar = tk.Frame(self.chip_host, bg=BG)
        bar.pack(fill="x", padx=16, pady=(10, 8))
        chips = ["All"]
        if self.lib.haul_videos() and "Try-on hauls" not in chips:
            chips.append("Try-on hauls")
        for ch in self.lib.featured_channels():
            n = ch.get("name") or ""
            if n and n not in chips:
                chips.append(n)
        for ch in self.lib.channels():
            n = ch.get("name") or ""
            if n and n not in chips:
                chips.append(n)
        chips += ["Recently uploaded", "Watched"]
        self._chip_btns = {}
        for name in chips:
            on = (self.chip == name)
            b = Pill(bar, name, cmd=lambda n=name: self._set_chip(n),
                     fill=WHITE if on else CARD, fg=BLACK if on else TXT,
                     hover="#e5e5e5" if on else HOVER, radius=8, padx=12, pady=6,
                     font=(FONT_UI, 10, "bold") if on else (FONT_UI, 10))
            b.pack(side="left", padx=4)
            self._chip_btns[name] = b
        tk.Frame(self.chip_host, bg=CARD, height=1).pack(fill="x")

    def _set_chip(self, name):
        self.chip = name
        if self.page != "home":
            self.page = "home"
        self._build_chips()
        self._fill_home()

    def _show_chips(self, on):
        if on:
            if not self.chip_host.winfo_ismapped():
                self.chip_host.pack(fill="x", before=self.content)
        else:
            self.chip_host.pack_forget()

    # ---------- navigation ----------
    def show_page(self, page, **kw):
        if page not in ("watch", "shorts"):
            self.player_pause()
            self._player_kill()
        self.page = page
        if page == "studio":
            self.sidebar_open = False
            self.sidebar.configure(width=0)
            self.sidebar.pack_forget()
            self._show_chips(False)
        else:
            if not self.sidebar.winfo_ismapped():
                self.sidebar.pack(side="left", fill="y", before=self.right)
            self.sidebar.configure(width=72 if not self.sidebar_open else 240)
            self._show_chips(page in ("home", "search"))
        self._mark_nav()
        for w in self.content.winfo_children():
            w.destroy()
        if page == "home":
            self._fill_home()
        elif page == "search":
            self._fill_home(search=True)
        elif page == "notscriptions":
            self._fill_list("Notscriptions", self.lib.notscription_videos(),
                            empty="You have no notscriptions yet. NOTSCRIBE a channel to see their videos here.")
        elif page == "history":
            self._fill_list("History", self.lib.history_videos(), empty="Videos you watch will show up here.")
        elif page == "your":
            self._fill_list("Your videos", self.lib.owned_videos(), empty="Upload a video from NOT TUBE STUDIO.")
        elif page == "later":
            self._fill_list("Watch later", self.lib.watch_later_videos(), empty="Save videos to watch later.")
        elif page == "liked":
            self._fill_list("Liked videos", self.lib.liked_videos(), empty="Videos you like will show up here.")
        elif page == "watch":
            self._fill_watch(kw.get("video_id") or self.watch_id)
        elif page == "channel":
            self._fill_channel(kw.get("channel_id") or self.channel_id)
        elif page == "shorts":
            self._fill_shorts(kw.get("video_id") or getattr(self, "shorts_id", None))
        elif page == "studio":
            self._fill_studio()
        self._refresh_avatar()

    def do_search(self):
        self.search_q = (self.search_var.get() or "").strip()
        self.chip = "All"
        self.show_page("search")

    def open_watch(self, vid):
        v = self.lib.get_video(vid)
        if not v:
            return
        self.lib.increment_views(vid)
        if v.get("is_short"):
            self.shorts_id = vid
            self.show_page("shorts", video_id=vid)
            return
        self.watch_id = vid
        self.show_page("watch", video_id=vid)

    def open_shorts(self, vid=None):
        shorts = self.lib.shorts()
        if not shorts:
            self.show_page("shorts")
            return
        if vid and any(s["id"] == vid for s in shorts):
            target = vid
        else:
            target = shorts[0]["id"]
        if target != getattr(self, "shorts_id", None) or self.page != "shorts":
            # increment only when opening a different short or entering the page
            if getattr(self, "shorts_id", None) != target or self.page != "shorts":
                self.lib.increment_views(target)
        self.shorts_id = target
        self.show_page("shorts", video_id=target)

    def open_channel(self, cid):
        if not self.lib.get_channel(cid):
            return
        self.channel_id = cid
        self.show_page("channel", channel_id=cid)

    def open_studio(self, tab="dashboard"):
        self.studio_tab = tab
        if not self.lib.current_channel() and tab != "owner":
            # force a first channel (Owner tools can open without one)
            self.show_page("studio")
            self.after(200, lambda: self._studio_new_channel(first=True))
            return
        self.show_page("studio")

    def open_studio_upload(self):
        self.open_studio("upload")

    # ---------- grid / lists ----------
    def _filtered_home(self):
        if self.page == "search":
            return self.lib.search(self.search_q)
        vids = [v for v in self.lib.videos() if not v.get("is_short")]
        if self.chip == "All":
            return vids
        if self.chip == "Try-on hauls":
            return self.lib.haul_videos()
        if self.chip == "Recently uploaded":
            return sorted(vids, key=lambda v: v.get("uploaded") or "", reverse=True)
        if self.chip == "Watched":
            return [v for v in self.lib.history_videos() if not v.get("is_short")]
        ch = self.lib.get_channel_by_name(self.chip)
        if ch:
            return [v for v in vids if v.get("channel_id") == ch["id"]]
        return vids

    def _fill_home(self, search=False):
        for w in self.content.winfo_children():
            w.destroy()
        host = VScroll(self.content, bg=BG)
        host.pack(fill="both", expand=True)
        self._grid_host = host
        top = tk.Frame(host.inner, bg=BG)
        top.pack(fill="x", padx=24, pady=(8, 0))
        if search:
            q = self.search_q
            tk.Label(top, text="Search results for “%s”" % q, bg=BG, fg=TXT,
                     font=(FONT_UI, 16, "bold"), anchor="w").pack(fill="x", pady=(4, 8))
        else:
            if self.chip == "All":
                kim_ids = self._kim_videos_shelf(host.inner) or set()
                self._hauls_shelf(host.inner, exclude_ids=kim_ids)
                self._featured_channels_shelf(host.inner)
            elif self.chip == "Try-on hauls":
                self._featured_channels_shelf(host.inner)
            if self.lib.shorts() and self.chip != "Try-on hauls":
                self._shorts_shelf(host.inner)
        vids = self._filtered_home()
        if (not search) and self.chip == "All":
            haul_ids = {v["id"] for v in self.lib.haul_videos()}
            vids = [v for v in vids if v["id"] not in haul_ids]
            kim = self.lib.kim_miyoyazu_channel()
            if kim:
                kim_ids = {v["id"] for v in self.lib.long_videos(kim["id"])}
                vids = [v for v in vids if v["id"] not in kim_ids]
        self._grid_box = tk.Frame(host.inner, bg=BG)
        self._grid_box.pack(fill="both", expand=True, padx=16, pady=8)
        self._grid_vids = vids
        if not vids:
            kim = self.lib.kim_miyoyazu_channel()
            has_kim = bool(kim and self.lib.long_videos(kim["id"]))
            if (not search) and self.chip == "All" and (has_kim or self.lib.haul_videos() or self.lib.featured_channels()):
                return
            msg = "No videos match that search." if search else "No videos yet. Click Create to upload in NOT TUBE STUDIO."
            tk.Label(self._grid_box, text=msg, bg=BG, fg=MUT, font=(FONT_UI, 13)).pack(pady=80)
            return
        self._grid_box.bind("<Configure>", self._on_grid_cfg)
        self.after_idle(lambda: self._render_grid(self._grid_box, self._grid_vids, self._grid_box.winfo_width()))

    def _fill_list(self, title, vids, empty=""):
        for w in self.content.winfo_children():
            w.destroy()
        host = VScroll(self.content, bg=BG)
        host.pack(fill="both", expand=True)
        tk.Label(host.inner, text=title, bg=BG, fg=TXT, font=(FONT_UI, 20, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(16, 8))
        box = tk.Frame(host.inner, bg=BG)
        box.pack(fill="both", expand=True, padx=16, pady=8)
        if not vids:
            tk.Label(box, text=empty, bg=BG, fg=MUT, font=(FONT_UI, 13)).pack(pady=60)
            return
        box.bind("<Configure>", lambda e, b=box, vs=vids: self._on_grid_cfg_generic(b, vs, e))
        self.after_idle(lambda: self._render_grid(box, vids, box.winfo_width()))

    def _on_grid_cfg(self, e):
        self._on_grid_cfg_generic(self._grid_box, getattr(self, "_grid_vids", []), e)

    def _on_grid_cfg_generic(self, box, vids, e):
        w = e.width
        if abs(w - getattr(box, "_last_w", 0)) < 20:
            return
        if getattr(box, "_job", None):
            try:
                self.after_cancel(box._job)
            except Exception:
                pass
        box._job = self.after(120, lambda: self._render_grid(box, vids, w))

    def _render_grid(self, box, vids, width):
        try:
            if not box.winfo_exists():
                return
        except tk.TclError:
            return
        box._last_w = width
        try:
            kids = list(box.winfo_children())
        except tk.TclError:
            return
        for w in kids:
            try:
                w.destroy()
            except tk.TclError:
                pass
        pad = 8
        min_card = 280
        usable = max(200, (width or 800) - 8)
        cols = max(1, usable // (min_card + pad))
        card_w = max(200, (usable - pad * cols) // cols)
        thumb_h = int(card_w * 9 / 16)
        for i, v in enumerate(vids):
            r, c = divmod(i, cols)
            cell = tk.Frame(box, bg=BG)
            cell.grid(row=r, column=c, padx=pad, pady=(4, 18), sticky="nw")
            self._video_card(cell, v, card_w, thumb_h)
        for c in range(cols):
            box.grid_columnconfigure(c, weight=1)

    def _video_card(self, parent, v, card_w, thumb_h):
        ch = self.lib.get_channel(v.get("channel_id")) or {"name": "Channel", "id": ""}
        frame = tk.Frame(parent, bg=BG, width=card_w, cursor="hand2")
        frame.pack()
        frame.pack_propagate(False)
        thumb_im = rounded_thumb(v.get("thumb") or "", card_w, thumb_h, 12, v.get("duration") or 0, BG)
        ph = ImageTk.PhotoImage(thumb_im)
        self._photos["t-" + v["id"] + str(card_w)] = ph
        th = tk.Label(frame, image=ph, bg=BG, bd=0)
        th.pack()
        meta = tk.Frame(frame, bg=BG)
        meta.pack(fill="x", pady=(10, 0))
        av = tk.Label(meta, image=self._avatar_photo(ch, 36), bg=BG, bd=0, cursor="hand2")
        av.pack(side="left", anchor="n", padx=(0, 12))
        text = tk.Frame(meta, bg=BG)
        text.pack(side="left", fill="x", expand=True)
        title = v.get("title") or "Untitled"
        tl = tk.Label(text, text=title, bg=BG, fg=TXT, font=(FONT_UI, 13, "bold"),
                      wraplength=card_w - 56, justify="left", anchor="w")
        tl.pack(fill="x")
        chn = tk.Label(text, text=ch.get("name") or "", bg=BG, fg=MUT, font=(FONT_UI, 12),
                       anchor="w", cursor="hand2")
        chn.pack(fill="x")
        sub = "%s · %s" % (fmt_views(v.get("views") or 0), fmt_ago(v.get("uploaded")))
        tk.Label(text, text=sub, bg=BG, fg=MUT, font=(FONT_UI, 12), anchor="w").pack(fill="x")
        # estimate card height so pack_propagate False still looks right
        frame.configure(width=card_w, height=thumb_h + 96)

        def watch(_e=None, vid=v["id"]):
            self.open_watch(vid)

        def channel(_e=None, cid=ch.get("id")):
            if cid:
                self.open_channel(cid)
            return "break"

        for w in (th, tl, frame):
            w.bind("<Button-1>", watch)
        av.bind("<Button-1>", channel)
        chn.bind("<Button-1>", channel)

    def toast(self, text):
        fr = tk.Frame(self, bg=HOVER)
        lb = tk.Label(fr, text=text, bg=HOVER, fg=TXT, font=(FONT_UI, 10), padx=16, pady=10)
        lb.pack()
        fr.place(relx=0.5, rely=0.92, anchor="s")
        def gone():
            try:
                fr.destroy()
            except Exception:
                pass
        self.after(2200, gone)

    def _nav_go(self, k):
        if k == "shorts":
            self.open_shorts(self.shorts_id)
        else:
            self.show_page(k)

    def _kim_videos_shelf(self, parent):
        """Home All: user's Kim Miyoyazu videos first. Returns their video ids, or empty set."""
        ch = self.lib.kim_miyoyazu_channel()
        if not ch:
            return set()
        vids = list(self.lib.long_videos(ch["id"]))
        vids.sort(key=lambda v: v.get("uploaded") or "", reverse=True)
        if not vids:
            return set()
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=16, pady=(4, 16))
        hdr = tk.Frame(wrap, bg=BG, cursor="hand2")
        hdr.pack(fill="x", padx=8, pady=(0, 10))
        av = tk.Label(hdr, image=self._avatar_photo(ch, 28), bg=BG, bd=0, cursor="hand2")
        av.pack(side="left", padx=(0, 8))
        title = tk.Label(hdr, text=ch.get("name") or "Kim Miyoyazu", bg=BG, fg=TXT,
                         font=(FONT_UI, 16, "bold"), cursor="hand2")
        title.pack(side="left")
        see = tk.Label(hdr, text="See all  ›", bg=BG, fg=MUT, font=(FONT_UI, 11), cursor="hand2")
        see.pack(side="right")

        def open_ch(_e=None, cid=ch["id"]):
            self.open_channel(cid)

        for w in (hdr, av, title, see):
            w.bind("<Button-1>", open_ch)
        row = None
        for i, v in enumerate(vids):
            if i % 4 == 0:
                row = tk.Frame(wrap, bg=BG)
                row.pack(fill="x")
            cell = tk.Frame(row, bg=BG)
            cell.pack(side="left", padx=8, anchor="n")
            self._video_card(cell, v, 240, int(240 * 9 / 16))
        return {v["id"] for v in vids}

    def _featured_channels_shelf(self, parent):
        chs = self.lib.featured_channels()
        if not chs:
            return
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=16, pady=(4, 16))
        hdr = tk.Frame(wrap, bg=BG)
        hdr.pack(fill="x", padx=8, pady=(0, 10))
        tk.Label(hdr, text="Featured channels", bg=BG, fg=TXT,
                 font=(FONT_UI, 16, "bold")).pack(side="left")
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x")
        for ch in chs:
            self._featured_channel_card(row, ch)

    def _featured_channel_card(self, parent, ch):
        cell = tk.Frame(parent, bg=BG, width=168, height=236)
        cell.pack(side="left", padx=10, anchor="n")
        cell.pack_propagate(False)

        def open_ch(_e=None, cid=ch["id"]):
            self.open_channel(cid)

        av = tk.Label(cell, image=self._avatar_photo(ch, 88), bg=BG, bd=0, cursor="hand2")
        av.pack(pady=(2, 8))
        name = tk.Label(cell, text=ch.get("name") or "", bg=BG, fg=TXT,
                        font=(FONT_UI, 11, "bold"), wraplength=156, justify="center",
                        cursor="hand2")
        name.pack()
        sub_lbl = tk.Label(cell, text=fmt_views(ch.get("subscribers") or 0, "notscribers"),
                           bg=BG, fg=MUT, font=(FONT_UI, 10), wraplength=156, justify="center")
        sub_lbl.pack(pady=(2, 8))
        for w in (av, name):
            w.bind("<Button-1>", open_ch)

        def after():
            c = self.lib.get_channel(ch["id"]) or ch
            try:
                if sub_lbl.winfo_exists():
                    sub_lbl.configure(text=fmt_views(c.get("subscribers") or 0, "notscribers"))
            except tk.TclError:
                pass

        host = tk.Frame(cell, bg=BG)
        host.pack()
        self._notscribe_btn(host, ch["id"], compact=True)

        def hook(_e=None):
            self.after(120, after)
        host.bind("<Button-1>", hook, add="+")
        def bind_kids():
            try:
                for w in host.winfo_children():
                    w.bind("<Button-1>", hook, add="+")
                    for k in w.winfo_children():
                        k.bind("<Button-1>", hook, add="+")
            except tk.TclError:
                pass
        self.after_idle(bind_kids)

    def _hauls_shelf(self, parent, exclude_ids=None):
        vids = self.lib.haul_videos()
        if exclude_ids:
            vids = [v for v in vids if v.get("id") not in exclude_ids]
        if not vids:
            return
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=16, pady=(0, 16))
        hdr = tk.Frame(wrap, bg=BG, cursor="hand2")
        hdr.pack(fill="x", padx=8, pady=(0, 10))
        tk.Label(hdr, text="Try-on hauls", bg=BG, fg=TXT,
                 font=(FONT_UI, 16, "bold")).pack(side="left")
        see = tk.Label(hdr, text="See all  ›", bg=BG, fg=MUT, font=(FONT_UI, 11), cursor="hand2")
        see.pack(side="right")

        def all_hauls(_e=None):
            self._set_chip("Try-on hauls")

        for w in (hdr, see):
            w.bind("<Button-1>", all_hauls)
        row = None
        for i, v in enumerate(vids):
            if i % 4 == 0:
                row = tk.Frame(wrap, bg=BG)
                row.pack(fill="x")
            cell = tk.Frame(row, bg=BG)
            cell.pack(side="left", padx=8, anchor="n")
            self._video_card(cell, v, 240, int(240 * 9 / 16))

    def _shorts_shelf(self, parent):
        shorts = self.lib.shorts()
        if not shorts:
            return
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(fill="x", padx=16, pady=(4, 20))
        hdr = tk.Frame(wrap, bg=BG, cursor="hand2")
        hdr.pack(fill="x", padx=8, pady=(0, 10))
        ic = tk.Label(hdr, image=self._photos.get("shorts_badge"), bg=BG, bd=0)
        ic.pack(side="left")
        tk.Label(hdr, text="NOT SHORTS", bg=BG, fg=TXT, font=(FONT_UI, 16, "bold")).pack(side="left", padx=(8, 0))
        see = tk.Label(hdr, text="Play all  ›", bg=BG, fg=MUT, font=(FONT_UI, 11), cursor="hand2")
        see.pack(side="right")
        for w in (hdr, ic, see):
            w.bind("<Button-1>", lambda e: self.open_shorts())
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x")
        for v in shorts:
            self._short_card(row, v, 160)

    def _short_card(self, parent, v, width=160):
        th = int(width * 16 / 9)
        ch = self.lib.get_channel(v.get("channel_id")) or {"name": "Channel", "id": ""}
        cell = tk.Frame(parent, bg=BG, cursor="hand2", width=width)
        cell.pack(side="left", padx=8, anchor="n")
        thumb_im = rounded_thumb(v.get("thumb") or "", width, th, 12, v.get("duration") or 0, BG)
        ph = ImageTk.PhotoImage(thumb_im)
        self._photos["st-" + v["id"] + str(width)] = ph
        thl = tk.Label(cell, image=ph, bg=BG, bd=0)
        thl.pack()
        tl = tk.Label(cell, text=v.get("title") or "Untitled", bg=BG, fg=TXT, font=(FONT_UI, 12, "bold"),
                      wraplength=width, justify="left", anchor="w")
        tl.pack(fill="x", pady=(8, 0))
        meta = "%s · %s" % (ch.get("name") or "", fmt_views(v.get("views") or 0))
        ml = tk.Label(cell, text=meta, bg=BG, fg=MUT, font=(FONT_UI, 10), wraplength=width,
                      justify="left", anchor="w")
        ml.pack(fill="x")
        def go(_e=None, vid=v["id"]):
            self.open_shorts(vid)
        for w in (cell, thl, tl, ml):
            w.bind("<Button-1>", go)

    # ---------- NOT SHORTS player ----------
    def _fill_shorts(self, vid):
        for w in self.content.winfo_children():
            w.destroy()
        shorts = self.lib.shorts()
        if not shorts:
            tk.Label(self.content, text="No NOT SHORTS yet. In NOT TUBE STUDIO, tick Post as NOT SHORT when you upload a vertical clip (60 seconds or under).",
                     bg=BG, fg=MUT, font=(FONT_UI, 13), wraplength=640, justify="center").pack(expand=True, pady=80)
            return
        ids = [s["id"] for s in shorts]
        if not vid or vid not in ids:
            vid = ids[0]
            self.shorts_id = vid
        self._shorts_list = shorts
        self._shorts_index = ids.index(vid)
        v = self.lib.get_video(vid)
        ch = self.lib.get_channel(v.get("channel_id")) or {"name": "Channel", "id": ""}

        root = tk.Frame(self.content, bg=BG)
        root.pack(fill="both", expand=True)
        # center cluster
        mid = tk.Frame(root, bg=BG)
        mid.place(relx=0.5, rely=0.5, anchor="center")

        stage = tk.Frame(mid, bg="#000000")
        stage.pack(side="left")
        self.player_canvas = tk.Canvas(stage, bg="#000000", highlightthickness=0, width=405, height=720, cursor="hand2")
        self.player_canvas.pack()
        self.player_canvas.bind("<Button-1>", lambda e: self.player_toggle())
        self.player_canvas.bind("<MouseWheel>", self._shorts_wheel)
        stage.bind("<MouseWheel>", self._shorts_wheel)
        root.bind("<MouseWheel>", self._shorts_wheel)

        # up / down
        nav = tk.Frame(mid, bg=BG)
        nav.pack(side="left", padx=10)
        IconBtn(nav, "chevron", lambda: self._shorts_step(-1), size=22, bg=CARD, hover=HOVER, pad=10).pack(pady=8)
        # rotate the chevron conceptually: draw up via a label
        upb = tk.Label(nav, text="▲", bg=CARD, fg=TXT, font=(FONT_UI, 14, "bold"), cursor="hand2", padx=12, pady=10)
        upb.pack(pady=6)
        upb.bind("<Button-1>", lambda e: self._shorts_step(-1))
        dnb = tk.Label(nav, text="▼", bg=CARD, fg=TXT, font=(FONT_UI, 14, "bold"), cursor="hand2", padx=12, pady=10)
        dnb.pack(pady=6)
        dnb.bind("<Button-1>", lambda e: self._shorts_step(1))

        # right actions
        acts = tk.Frame(mid, bg=BG)
        acts.pack(side="left", padx=(16, 0), anchor="s")
        self._short_action_col(acts, v, ch)

        # caption under / beside
        cap = tk.Frame(stage, bg="#000000")
        cap.pack(fill="x")
        tk.Label(cap, text=v.get("title") or "", bg="#000000", fg=TXT, font=(FONT_UI, 12, "bold"),
                 wraplength=390, justify="left", anchor="w").pack(fill="x", padx=8, pady=(6, 0))
        chl = tk.Label(cap, text=ch.get("name") or "", bg="#000000", fg=MUT, font=(FONT_UI, 11),
                       anchor="w", cursor="hand2")
        chl.pack(fill="x", padx=8, pady=(0, 8))
        chl.bind("<Button-1>", lambda e, cid=ch.get("id"): cid and self.open_channel(cid))

        self._player_loop = True
        self._start_player(v, vertical=True)

    def _short_action_col(self, parent, v, ch):
        def likes():
            return fmt_count(v.get("likes") or 0)
        def cmts():
            return fmt_count(len(self.lib.comments_for(v["id"])))

        def circle(kind, text, cmd, fill_on=False):
            wrap = tk.Frame(parent, bg=BG)
            wrap.pack(pady=(0, 12))
            bgc = WHITE if fill_on else CARD
            fg = BLACK if fill_on else TXT
            # circular-ish
            btn = tk.Label(wrap, image=icon_photo(kind, 22, fg), bg=bgc, cursor="hand2", padx=12, pady=12)
            self._photos["sa-%s-%s" % (v["id"], kind)] = btn.cget("image")
            # keep a real photo
            ph = icon_photo(kind, 22, fg)
            self._photos["sa2-%s-%s" % (v["id"], kind)] = ph
            btn.configure(image=ph, bg=bgc)
            btn.pack()
            lb = tk.Label(wrap, text=text, bg=BG, fg=TXT, font=(FONT_UI, 10, "bold"))
            lb.pack()
            btn.bind("<Button-1>", lambda e: cmd())
            return btn, lb

        like_on = bool(v.get("liked_by_me"))
        self._s_like_btn, self._s_like_lb = circle("liked", likes(), lambda: self._shorts_like(True), like_on)
        self._s_dis_btn, self._s_dis_lb = circle("thumbdown", fmt_count(v.get("dislikes") or 0),
                                                 lambda: self._shorts_like(False), bool(v.get("disliked_by_me")))
        self._s_cmt_btn, self._s_cmt_lb = circle("edit", cmts(), lambda: self._shorts_comments(v["id"]))
        circle("share", "Share", lambda: self._share(v))

        av = tk.Label(parent, image=self._avatar_photo(ch, 48), bg=BG, cursor="hand2", bd=0)
        av.pack(pady=(8, 8))
        av.bind("<Button-1>", lambda e, cid=ch.get("id"): cid and self.open_channel(cid))
        self._notscribe_btn(parent, ch.get("id"), compact=True)

    def _shorts_like(self, up):
        if not self.shorts_id:
            return
        self.lib.toggle_like(self.shorts_id, up=up)
        # refresh action column counts by rebuilding the page would restart the player;
        # just update labels if present
        v = self.lib.get_video(self.shorts_id)
        if not v:
            return
        try:
            self._s_like_lb.configure(text=fmt_count(v.get("likes") or 0))
            self._s_dis_lb.configure(text=fmt_count(v.get("dislikes") or 0))
        except Exception:
            pass

    def _shorts_comments(self, vid):
        top = tk.Toplevel(self)
        top.title("Comments")
        top.configure(bg=BG)
        top.geometry("420x520")
        top.transient(self)
        self._comments_block(top, vid, fill=True)
        top.lift()

    def _shorts_step(self, delta):
        shorts = getattr(self, "_shorts_list", None) or self.lib.shorts()
        if not shorts:
            return
        i = getattr(self, "_shorts_index", 0) + delta
        i = max(0, min(len(shorts) - 1, i))
        vid = shorts[i]["id"]
        if vid == self.shorts_id:
            return
        self.player_pause()
        self._player_kill()
        self.open_shorts(vid)

    def _shorts_wheel(self, ev):
        if ev.delta > 0:
            self._shorts_step(-1)
        elif ev.delta < 0:
            self._shorts_step(1)
        return "break"

    # ---------- NOTSCRIBE widget ----------
    def _notscribe_btn(self, parent, channel_id, compact=False):
        ch = self.lib.get_channel(channel_id)
        if not ch:
            return None
        fr = tk.Frame(parent, bg=parent.cget("bg") if parent.cget("bg") else BG)
        fr.pack(side="left") if not compact else fr.pack(pady=(0, 4))
        if ch.get("owned"):
            pill = Pill(fr, "Your channel", cmd=lambda: self.open_channel(channel_id),
                        fill=CARD, fg=TXT, hover=HOVER, radius=18, padx=14, pady=7,
                        font=(FONT_UI, 10, "bold"))
            pill.pack(side="left")
            return fr
        on = self.lib.is_notscribed(channel_id)

        def refresh():
            for w in fr.winfo_children():
                w.destroy()
            now = self.lib.is_notscribed(channel_id)
            if now:
                pill = Pill(fr, "NOTSCRIBED", cmd=lambda: self._un_notscribe_menu(pill, channel_id, refresh),
                            fill=CARD, fg=TXT, hover=HOVER, radius=18, padx=14, pady=7,
                            font=(FONT_UI, 10, "bold"))
                pill.pack(side="left")
            else:
                pill = Pill(fr, "NOTSCRIBE", cmd=lambda: self._do_notscribe(channel_id, True, refresh),
                            fill=WHITE, fg=BLACK, hover="#e5e5e5", radius=18, padx=14, pady=7,
                            font=(FONT_UI, 10, "bold"))
                pill.pack(side="left")

        refresh()
        return fr

    def _do_notscribe(self, cid, _want, after=None):
        self.lib.toggle_notscribe(cid)
        if after:
            after()
        # rebuild sidebar list
        try:
            self._build_sidebar()
        except Exception:
            pass
        self.toast("NOTSCRIBED" if self.lib.is_notscribed(cid) else "Un-notscribed")

    def _un_notscribe_menu(self, widget, cid, after=None):
        m = tk.Menu(self, tearoff=0, bg="#282828", fg=TXT, activebackground=HOVER,
                    activeforeground=TXT, bd=0, font=(FONT_UI, 10))
        m.add_command(label="Un-notscribe", command=lambda: self._do_notscribe(cid, False, after))
        try:
            m.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())
        finally:
            m.grab_release()
        self._unsub_menu = m

    # ---------- watch page ----------
    def _fill_watch(self, vid):
        for w in self.content.winfo_children():
            w.destroy()
        v = self.lib.get_video(vid)
        if not v:
            tk.Label(self.content, text="That video is no longer in your library.", bg=BG, fg=MUT,
                     font=(FONT_UI, 13)).pack(pady=80)
            return
        ch = self.lib.get_channel(v.get("channel_id")) or {"name": "Channel", "id": ""}
        self._player_loop = False

        root = tk.Frame(self.content, bg=BG)
        root.pack(fill="both", expand=True)
        left = tk.Frame(root, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(24, 12), pady=12)
        right = tk.Frame(root, bg=BG, width=402)
        right.pack(side="right", fill="y", padx=(0, 16), pady=12)
        right.pack_propagate(False)

        # player
        self.player_holder = tk.Frame(left, bg="#000000")
        self.player_holder.pack(fill="x")
        self.player_canvas = tk.Canvas(self.player_holder, bg="#000000", highlightthickness=0, height=400, cursor="hand2")
        self.player_canvas.pack(fill="both", expand=True)
        self.player_canvas.bind("<Button-1>", lambda e: self.player_toggle())
        self.player_canvas.bind("<Configure>", lambda e: self._player_redraw())
        self.player_holder.bind("<Configure>", self._layout_player)

        ctrl = tk.Frame(left, bg=SCRIM)
        ctrl.pack(fill="x")
        row = tk.Frame(ctrl, bg=SCRIM)
        row.pack(fill="x", padx=8, pady=4)
        self._photos["p_play"] = icon_photo("play", 18, TXT)
        self._photos["p_pause"] = icon_photo("pause", 18, TXT)
        self._photos["p_next"] = icon_photo("next", 18, TXT)
        self._photos["p_vol"] = icon_photo("vol", 18, TXT)
        self._photos["p_mute"] = icon_photo("mute", 18, TXT)
        self._photos["p_full"] = icon_photo("full", 18, TXT)
        self.b_play = tk.Label(row, image=self._photos["p_play"], bg=SCRIM, cursor="hand2", padx=6)
        self.b_play.pack(side="left")
        self.b_play.bind("<Button-1>", lambda e: self.player_toggle())
        self.b_next = tk.Label(row, image=self._photos["p_next"], bg=SCRIM, cursor="hand2", padx=6)
        self.b_next.pack(side="left")
        self.b_next.bind("<Button-1>", lambda e: self._watch_next())
        self.b_vol = tk.Label(row, image=self._photos["p_vol"], bg=SCRIM, cursor="hand2", padx=6)
        self.b_vol.pack(side="left")
        self.b_vol.bind("<Button-1>", lambda e: self._toggle_mute())
        self.volbar = VolBar(row, command=self._set_volume, bg=SCRIM, width=70)
        self.volbar.set(0 if self._muted else self._volume)
        self.volbar.pack(side="left", padx=4)
        self.player_time_lbl = tk.Label(row, text="0:00 / 0:00", bg=SCRIM, fg=MUT, font=(FONT_UI, 10))
        self.player_time_lbl.pack(side="left", padx=8)
        self.b_full = tk.Label(row, image=self._photos["p_full"], bg=SCRIM, cursor="hand2", padx=6)
        self.b_full.pack(side="right")
        self.b_full.bind("<Button-1>", lambda e: self.toggle_fullscreen())
        self.seek = SeekBar(ctrl, command=self._on_seek, bg=SCRIM, height=14)
        self.seek.pack(fill="x", padx=8, pady=(0, 4))

        # meta under player, scrollable
        sc = VScroll(left, bg=BG)
        sc.pack(fill="both", expand=True, pady=(12, 0))
        meta = sc.inner
        tk.Label(meta, text=v.get("title") or "Untitled", bg=BG, fg=TXT, font=(FONT_UI, 18, "bold"),
                 wraplength=760, justify="left", anchor="w").pack(fill="x", pady=(0, 10))
        chrow = tk.Frame(meta, bg=BG)
        chrow.pack(fill="x", pady=(0, 8))
        av = tk.Label(chrow, image=self._avatar_photo(ch, 40), bg=BG, cursor="hand2", bd=0)
        av.pack(side="left")
        av.bind("<Button-1>", lambda e, cid=ch.get("id"): cid and self.open_channel(cid))
        chinfo = tk.Frame(chrow, bg=BG)
        chinfo.pack(side="left", padx=12)
        nlab = tk.Label(chinfo, text=ch.get("name") or "", bg=BG, fg=TXT, font=(FONT_UI, 13, "bold"),
                        cursor="hand2", anchor="w")
        nlab.pack(anchor="w")
        nlab.bind("<Button-1>", lambda e, cid=ch.get("id"): cid and self.open_channel(cid))
        tk.Label(chinfo, text=fmt_views(ch.get("subscribers") or 0, "notscribers"),
                 bg=BG, fg=MUT, font=(FONT_UI, 12), anchor="w").pack(anchor="w")
        self._notscribe_btn(chrow, ch.get("id"))

        acts = tk.Frame(chrow, bg=BG)
        acts.pack(side="right")
        like_txt = fmt_count(v.get("likes") or 0)
        like_fill = WHITE if v.get("liked_by_me") else CARD
        like_fg = BLACK if v.get("liked_by_me") else TXT
        Pill(acts, "  %s" % like_txt, cmd=lambda: self._watch_like(True),
             fill=like_fill, fg=like_fg, hover=HOVER, radius=18, padx=12, pady=6,
             font=(FONT_UI, 10, "bold")).pack(side="left", padx=4)
        Pill(acts, "  Dislike" if not v.get("disliked_by_me") else "  Disliked",
             cmd=lambda: self._watch_like(False),
             fill=WHITE if v.get("disliked_by_me") else CARD,
             fg=BLACK if v.get("disliked_by_me") else TXT,
             hover=HOVER, radius=18, padx=12, pady=6, font=(FONT_UI, 10)).pack(side="left", padx=4)
        Pill(acts, "Share", cmd=lambda: self._share(v), fill=CARD, fg=TXT, hover=HOVER,
             radius=18, padx=12, pady=6, font=(FONT_UI, 10)).pack(side="left", padx=4)
        saved = self.lib.in_watch_later(v["id"])
        Pill(acts, "Saved" if saved else "Save", cmd=lambda: self._toggle_save(v["id"]),
             fill=CARD, fg=TXT, hover=HOVER, radius=18, padx=12, pady=6,
             font=(FONT_UI, 10)).pack(side="left", padx=4)

        # description box
        desc = tk.Frame(meta, bg=CARD)
        desc.pack(fill="x", pady=(12, 16))
        # fake rounded by padding
        dpad = tk.Frame(desc, bg=CARD)
        dpad.pack(fill="x", padx=12, pady=10)
        line = "%s  %s" % (fmt_views(v.get("views") or 0), fmt_date(v.get("uploaded")))
        tk.Label(dpad, text=line, bg=CARD, fg=TXT, font=(FONT_UI, 12, "bold"), anchor="w").pack(fill="x")
        body = (v.get("description") or "").strip() or "No description."
        tk.Label(dpad, text=body, bg=CARD, fg=TXT, font=(FONT_UI, 12), wraplength=720,
                 justify="left", anchor="w").pack(fill="x", pady=(6, 0))

        self._comments_block(meta, v["id"])

        # up next
        tk.Label(right, text="Up next", bg=BG, fg=TXT, font=(FONT_UI, 14, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 8))
        usc = VScroll(right, bg=BG)
        usc.pack(fill="both", expand=True)
        up = self._upnext_list(v)
        for u in up:
            self._compact_row(usc.inner, u)

        self._start_player(v, vertical=False)

    def _comments_block(self, parent, vid, fill=False):
        comments = self.lib.comments_for(vid)
        box = tk.Frame(parent, bg=BG)
        box.pack(fill="both", expand=fill, pady=(8, 24))
        tk.Label(box, text="%d Comments" % len(comments), bg=BG, fg=TXT,
                 font=(FONT_UI, 16, "bold"), anchor="w").pack(fill="x", pady=(0, 10))
        add = tk.Frame(box, bg=BG)
        add.pack(fill="x", pady=(0, 12))
        ch = self.lib.current_channel()
        if ch:
            tk.Label(add, image=self._avatar_photo(ch, 32), bg=BG, bd=0).pack(side="left", padx=(0, 10))
        self._cmt_var = tk.StringVar()
        ent = tk.Entry(add, textvariable=self._cmt_var, bg=BG, fg=TXT, insertbackground=TXT,
                       relief="flat", font=(FONT_UI, 12), highlightthickness=0)
        ent.pack(side="left", fill="x", expand=True)
        tk.Frame(add, bg=DIM, height=1).place(relx=0, rely=1, relwidth=1, anchor="sw")
        Pill(add, "Comment", cmd=lambda: self._post_comment(vid, box if fill else None),
             fill=CARD, fg=TXT, hover=HOVER, radius=18, padx=12, pady=6,
             font=(FONT_UI, 10, "bold")).pack(side="left", padx=8)
        ent.bind("<Return>", lambda e: self._post_comment(vid, box if fill else None))
        self._cmt_list = tk.Frame(box, bg=BG)
        self._cmt_list.pack(fill="both", expand=True)
        self._render_comments(self._cmt_list, vid)

    def _render_comments(self, host, vid):
        for w in host.winfo_children():
            w.destroy()
        for c in self.lib.comments_for(vid):
            row = tk.Frame(host, bg=BG)
            row.pack(fill="x", pady=8, anchor="w")
            av = initials_avatar(c.get("author") or "?", 32)
            ph = ImageTk.PhotoImage(circle_avatar(av, 32))
            self._photos["cmt-" + c.get("id", "")] = ph
            tk.Label(row, image=ph, bg=BG, bd=0).pack(side="left", anchor="n", padx=(0, 10))
            col = tk.Frame(row, bg=BG)
            col.pack(side="left", fill="x", expand=True)
            who = "%s  ·  %s" % (c.get("author") or "", fmt_ago(c.get("time")))
            tk.Label(col, text=who, bg=BG, fg=MUT, font=(FONT_UI, 11), anchor="w").pack(fill="x")
            tk.Label(col, text=c.get("text") or "", bg=BG, fg=TXT, font=(FONT_UI, 12),
                     wraplength=640, justify="left", anchor="w").pack(fill="x")

    def _post_comment(self, vid, rebuild=None):
        text = (self._cmt_var.get() if hasattr(self, "_cmt_var") else "").strip()
        if not text:
            return
        author = (self.lib.current_channel() or {}).get("name") or "You"
        self.lib.add_comment(vid, text, author=author)
        self._cmt_var.set("")
        if hasattr(self, "_cmt_list"):
            self._render_comments(self._cmt_list, vid)
        self.toast("Comment posted")

    def _watch_like(self, up):
        if not self.watch_id:
            return
        self.lib.toggle_like(self.watch_id, up=up)
        self._fill_watch(self.watch_id)

    def _toggle_save(self, vid):
        on = self.lib.toggle_watch_later(vid)
        self.toast("Saved to Watch later" if on else "Removed from Watch later")
        if self.page == "watch":
            self._fill_watch(vid)

    def _share(self, v):
        text = "%s\n%s" % (v.get("title") or "", v.get("path") or "")
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.toast("Copied")
        except Exception:
            self.toast("Could not copy")

    def _upnext_list(self, current):
        cid = current.get("channel_id")
        rest = [v for v in self.lib.long_videos() if v["id"] != current["id"]]
        same = [v for v in rest if v.get("channel_id") == cid]
        other = [v for v in rest if v.get("channel_id") != cid]
        return same + other

    def _compact_row(self, parent, v):
        ch = self.lib.get_channel(v.get("channel_id")) or {"name": "Channel", "id": ""}
        row = tk.Frame(parent, bg=BG, cursor="hand2")
        row.pack(fill="x", pady=6)
        tw, th = 168, 94
        im = rounded_thumb(v.get("thumb") or "", tw, th, 8, v.get("duration") or 0, BG)
        ph = ImageTk.PhotoImage(im)
        self._photos["up-" + v["id"]] = ph
        thl = tk.Label(row, image=ph, bg=BG, bd=0)
        thl.pack(side="left")
        col = tk.Frame(row, bg=BG)
        col.pack(side="left", fill="x", expand=True, padx=8, anchor="n")
        tl = tk.Label(col, text=v.get("title") or "", bg=BG, fg=TXT, font=(FONT_UI, 13, "bold"),
                      wraplength=210, justify="left", anchor="w")
        tl.pack(fill="x")
        chn = tk.Label(col, text=ch.get("name") or "", bg=BG, fg=MUT, font=(FONT_UI, 11),
                       anchor="w", cursor="hand2")
        chn.pack(fill="x")
        tk.Label(col, text=fmt_views(v.get("views") or 0), bg=BG, fg=MUT, font=(FONT_UI, 11),
                 anchor="w").pack(fill="x")
        def go(_e=None, vid=v["id"]):
            self.open_watch(vid)
        def channel(_e=None, cid=ch.get("id")):
            if cid:
                self.open_channel(cid)
            return "break"
        for w in (row, thl, tl):
            w.bind("<Button-1>", go)
        chn.bind("<Button-1>", channel)

    def _watch_next(self):
        if not self.watch_id:
            return
        cur = self.lib.get_video(self.watch_id)
        if not cur:
            return
        nxt = self._upnext_list(cur)
        if nxt:
            self.player_pause()
            self._player_kill()
            self.open_watch(nxt[0]["id"])

    def _layout_player(self, e=None):
        if not getattr(self, "player_holder", None):
            return
        try:
            w = self.player_holder.winfo_width()
            avail = self.content.winfo_height() - 120
        except Exception:
            return
        if w < 80:
            return
        h = int(w * 9 / 16)
        if avail > 160:
            h = min(h, avail)
        self.player_canvas.configure(height=max(160, h))
        self._player_redraw()

    # ---------- channel page ----------
    def _fill_channel(self, cid):
        for w in self.content.winfo_children():
            w.destroy()
        ch = self.lib.get_channel(cid)
        if not ch:
            tk.Label(self.content, text="Channel not found.", bg=BG, fg=MUT, font=(FONT_UI, 13)).pack(pady=80)
            return
        host = VScroll(self.content, bg=BG)
        host.pack(fill="both", expand=True)
        # banner
        banner_h = 160
        bfr = tk.Frame(host.inner, bg=CARD, height=banner_h)
        bfr.pack(fill="x")
        bfr.pack_propagate(False)
        bpath = ch.get("banner") or ""
        if bpath and os.path.isfile(bpath):
            def paint_banner(e, path=bpath, fr=bfr):
                w = e.width
                if w < 40 or getattr(fr, "_bw", 0) == w:
                    return
                fr._bw = w
                try:
                    im = cover_fit(Image.open(path).convert("RGB"), w, banner_h)
                    ph = ImageTk.PhotoImage(im)
                    self._photos["banner-" + ch["id"]] = ph
                    if not getattr(fr, "_lbl", None):
                        fr._lbl = tk.Label(fr, image=ph, bg=CARD, bd=0)
                        fr._lbl.place(x=0, y=0, relwidth=1, relheight=1)
                    else:
                        fr._lbl.configure(image=ph)
                except Exception:
                    pass
            bfr.bind("<Configure>", paint_banner)
        # identity row
        ident = tk.Frame(host.inner, bg=BG)
        ident.pack(fill="x", padx=32, pady=16)
        tk.Label(ident, image=self._avatar_photo(ch, 80), bg=BG, bd=0).pack(side="left", padx=(0, 16))
        col = tk.Frame(ident, bg=BG)
        col.pack(side="left", fill="x", expand=True)
        tk.Label(col, text=ch.get("name") or "", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x")
        handle = ch.get("handle") or ""
        subl = "%s  ·  %s  ·  %s" % (
            handle,
            fmt_views(ch.get("subscribers") or 0, "notscribers"),
            "%d videos" % len(self.lib.channel_videos(ch["id"])),
        )
        tk.Label(col, text=subl, bg=BG, fg=MUT, font=(FONT_UI, 13), anchor="w").pack(fill="x")
        if (ch.get("description") or "").strip():
            tk.Label(col, text=ch.get("description") or "", bg=BG, fg=MUT, font=(FONT_UI, 12),
                     wraplength=720, justify="left", anchor="w").pack(fill="x", pady=(4, 0))
        self._notscribe_btn(ident, ch["id"])

        # shorts shelf on channel
        ch_shorts = self.lib.shorts(ch["id"])
        if ch_shorts:
            self._shorts_shelf(host.inner)

        # videos tab
        tab = tk.Frame(host.inner, bg=BG)
        tab.pack(fill="x", padx=32)
        tk.Label(tab, text="Videos", bg=BG, fg=TXT, font=(FONT_UI, 14, "bold"),
                 anchor="w").pack(side="left")
        tk.Frame(host.inner, bg=WHITE, height=2).pack(fill="x", padx=32, pady=(6, 10))
        box = tk.Frame(host.inner, bg=BG)
        box.pack(fill="both", expand=True, padx=16, pady=8)
        vids = self.lib.long_videos(ch["id"])
        if not vids and not ch_shorts:
            tk.Label(box, text="This channel has no videos yet.", bg=BG, fg=MUT, font=(FONT_UI, 13)).pack(pady=40)
            return
        box.bind("<Configure>", lambda e, b=box, vs=vids: self._on_grid_cfg_generic(b, vs, e))
        self.after_idle(lambda: self._render_grid(box, vids, box.winfo_width()))

    # ---------- STUDIO ----------
    def _fill_studio(self):
        for w in self.content.winfo_children():
            w.destroy()
        root = tk.Frame(self.content, bg=BG)
        root.pack(fill="both", expand=True)
        rail = tk.Frame(root, bg=BG, width=220)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        tk.Frame(rail, bg=CARD, width=1).pack(side="right", fill="y")
        inner = tk.Frame(rail, bg=BG)
        inner.pack(fill="both", expand=True)
        back = tk.Label(inner, text="‹  Home", bg=BG, fg=MUT, font=(FONT_UI, 11), cursor="hand2", anchor="w")
        back.pack(fill="x", padx=16, pady=(16, 8))
        back.bind("<Button-1>", lambda e: self.show_page("home"))
        tk.Label(inner, text="NOT TUBE STUDIO", bg=BG, fg=TXT, font=(FONT_UI, 13, "bold"),
                 anchor="w").pack(fill="x", padx=16, pady=(4, 12))
        tabs = [
            ("dashboard", "Dashboard"),
            ("content", "Content"),
            ("upload", "Upload"),
            ("channel", "Channel"),
            ("bots", "Bot accounts"),
        ]
        if is_owner_pc():
            tabs.append(("owner", "Owner tools"))
        self._studio_tabs = {}
        for key, label in tabs:
            on = self.studio_tab == key
            row = tk.Label(inner, text=label, bg=CARD if on else BG, fg=TXT,
                           font=(FONT_UI, 11, "bold" if on else "normal"),
                           anchor="w", padx=16, pady=10, cursor="hand2")
            row.pack(fill="x", padx=8, pady=1)
            row.bind("<Button-1>", lambda e, k=key: self._studio_goto(k))
            self._studio_tabs[key] = row
        tk.Label(inner, text=COPYRIGHT, bg=BG, fg=DIM, font=(FONT_UI, 8),
                 wraplength=180, justify="left", anchor="w").pack(side="bottom", fill="x", padx=16, pady=16)

        main = tk.Frame(root, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        # studio header: channel switcher
        head = tk.Frame(main, bg=BG)
        head.pack(fill="x", padx=24, pady=(12, 8))
        ch = self.lib.current_channel()
        if ch:
            sw = tk.Frame(head, bg=CARD, cursor="hand2")
            sw.pack(side="left")
            tk.Label(sw, image=self._avatar_photo(ch, 32), bg=CARD, bd=0).pack(side="left", padx=(10, 8), pady=6)
            col = tk.Frame(sw, bg=CARD)
            col.pack(side="left", pady=6)
            tk.Label(col, text=ch.get("name") or "", bg=CARD, fg=TXT, font=(FONT_UI, 11, "bold"),
                     anchor="w").pack(anchor="w")
            tk.Label(col, text=ch.get("handle") or "", bg=CARD, fg=MUT, font=(FONT_UI, 9),
                     anchor="w").pack(anchor="w")
            tk.Label(sw, text="  ▾  ", bg=CARD, fg=MUT).pack(side="left", padx=(4, 8))
            for w in sw.winfo_children():
                w.bind("<Button-1>", lambda e: self._switch_channel_menu(sw))
            sw.bind("<Button-1>", lambda e: self._switch_channel_menu(sw))
        else:
            tk.Label(head, text="Create a channel to publish.", bg=BG, fg=MUT, font=(FONT_UI, 12)).pack(side="left")
        Pill(head, "New channel", cmd=lambda: self._studio_new_channel(), fill=CARD, fg=TXT,
             hover=HOVER, radius=16, padx=12, pady=6, font=(FONT_UI, 10)).pack(side="right")

        body = tk.Frame(main, bg=BG)
        body.pack(fill="both", expand=True)
        self._studio_body = body
        tab = self.studio_tab
        if not ch and tab not in ("channel", "owner"):
            self._studio_new_channel(first=True)
            return
        if tab == "dashboard":
            self._studio_dashboard(body, ch)
        elif tab == "content":
            self._studio_content(body, ch)
        elif tab == "upload":
            self._studio_upload(body, ch)
        elif tab == "channel":
            self._studio_channel(body, ch)
        elif tab == "bots":
            self._studio_bots(body, ch)
        elif tab == "owner":
            if not is_owner_pc():
                self.studio_tab = "dashboard"
                self._fill_studio()
                return
            self._studio_owner(body)

    def _studio_goto(self, tab):
        self.studio_tab = tab
        self._fill_studio()

    def _switch_channel_menu(self, widget):
        m = tk.Menu(self, tearoff=0, bg="#282828", fg=TXT, activebackground=HOVER,
                    activeforeground=TXT, bd=0, font=(FONT_UI, 10))
        cur = (self.lib.current_channel() or {}).get("id")
        for ch in self.lib.owned_channels():
            mark = "  ✓" if ch["id"] == cur else ""
            m.add_command(label="%s  %s%s" % (ch.get("name"), ch.get("handle") or "", mark),
                          command=lambda cid=ch["id"]: self._do_switch_channel(cid))
        m.add_separator()
        m.add_command(label="Create a channel…", command=lambda: self._studio_new_channel())
        try:
            m.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())
        finally:
            m.grab_release()
        self._switcher = m

    def _do_switch_channel(self, cid):
        self.lib.switch_channel(cid)
        self._refresh_avatar()
        if self.page == "studio":
            self._fill_studio()
        self.toast("Switched channel")

    def _studio_dashboard(self, parent, ch):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        tk.Label(sc.inner, text="Dashboard", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 16))
        stats = self.lib.channel_stats(ch["id"])
        row = tk.Frame(sc.inner, bg=BG)
        row.pack(fill="x", padx=24)
        cards = [
            ("Videos", fmt_count(stats["videos"])),
            ("Views", fmt_count(stats["views"])),
            ("Likes", fmt_count(stats["likes"])),
            ("Comments", fmt_count(stats["comments"])),
            ("Notscribers", fmt_count(stats["notscribers"])),
            ("Bot views", fmt_count(stats["bot_views"])),
        ]
        for title, val in cards:
            card = tk.Frame(row, bg=CARD)
            card.pack(side="left", padx=(0, 10), pady=4, ipadx=4)
            inner = tk.Frame(card, bg=CARD)
            inner.pack(padx=16, pady=14)
            tk.Label(inner, text=val, bg=CARD, fg=TXT, font=(FONT_UI, 22, "bold")).pack()
            tk.Label(inner, text=title, bg=CARD, fg=MUT, font=(FONT_UI, 10)).pack()
        # live bot counter
        live = tk.Frame(sc.inner, bg=CARD)
        live.pack(fill="x", padx=24, pady=16)
        self._bot_live_lbl = tk.Label(
            live, text=self._bot_live_text(ch), bg=CARD, fg=TXT, font=(FONT_UI, 13),
            anchor="w", padx=16, pady=12)
        self._bot_live_lbl.pack(fill="x")
        # recent videos
        tk.Label(sc.inner, text="Recent videos", bg=BG, fg=TXT, font=(FONT_UI, 16, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(12, 8))
        for v in self.lib.channel_videos(ch["id"])[:8]:
            self._studio_content_row(sc.inner, v, compact=True)

    def _bot_live_text(self, ch):
        stats = self.lib.channel_stats(ch["id"]) if ch else {"bot_views": 0}
        vids = self.lib.channel_videos((ch or {}).get("id")) if ch else []
        done = sum(1 for v in vids if int(v.get("bot_views") or 0) >= BOT_TARGET)
        return "NOT TUBE BOT ACCOUNTS: ACTIVE  ·  %s bot views  ·  ROCKET  ·  %d/%d videos at 2K" % (
            fmt_count(stats["bot_views"]), done, len(vids))

    def _studio_content(self, parent, ch):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        tk.Label(sc.inner, text="Content", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 16))
        vids = self.lib.channel_videos(ch["id"])
        if not vids:
            tk.Label(sc.inner, text="This channel has no videos yet. Open Upload to publish one.",
                     bg=BG, fg=MUT, font=(FONT_UI, 13)).pack(padx=24, pady=40)
            return
        hdr = tk.Frame(sc.inner, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(0, 6))
        tk.Label(hdr, text="Video", bg=BG, fg=MUT, font=(FONT_UI, 9), width=40, anchor="w").pack(side="left")
        for lab in ("Views", "Likes", "Comments"):
            tk.Label(hdr, text=lab, bg=BG, fg=MUT, font=(FONT_UI, 9), width=10, anchor="e").pack(side="left")
        for v in vids:
            self._studio_content_row(sc.inner, v)

    def _studio_content_row(self, parent, v, compact=False):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=6)
        tw, th = (80, 142) if v.get("is_short") else (128, 72)
        im = rounded_thumb(v.get("thumb") or "", tw, th, 6, v.get("duration") or 0, BG)
        ph = ImageTk.PhotoImage(im)
        self._photos["sc-" + v["id"]] = ph
        tk.Label(row, image=ph, bg=BG, bd=0).pack(side="left")
        col = tk.Frame(row, bg=BG)
        col.pack(side="left", fill="x", expand=True, padx=10)
        title = v.get("title") or "Untitled"
        if v.get("is_short"):
            title = "NOT SHORT  ·  " + title
        tk.Label(col, text=title, bg=BG, fg=TXT, font=(FONT_UI, 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(col, text=fmt_ago(v.get("uploaded")), bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x")
        if not compact:
            tk.Label(row, text=fmt_count(v.get("views") or 0), bg=BG, fg=TXT, font=(FONT_UI, 11),
                     width=10, anchor="e").pack(side="left")
            tk.Label(row, text=fmt_count(v.get("likes") or 0), bg=BG, fg=TXT, font=(FONT_UI, 11),
                     width=10, anchor="e").pack(side="left")
            tk.Label(row, text=fmt_count(len(self.lib.comments_for(v["id"]))), bg=BG, fg=TXT,
                     font=(FONT_UI, 11), width=10, anchor="e").pack(side="left")
            Pill(row, "Edit", cmd=lambda vid=v["id"]: self._edit_video_dialog(vid),
                 fill=CARD, fg=TXT, hover=HOVER, radius=14, padx=10, pady=4,
                 font=(FONT_UI, 9)).pack(side="left", padx=4)
            Pill(row, "Delete", cmd=lambda vid=v["id"]: self._delete_video_ask(vid),
                 fill=CARD, fg=TXT, hover=HOVER, radius=14, padx=10, pady=4,
                 font=(FONT_UI, 9)).pack(side="left", padx=4)

    def _may_manage_video(self, vid):
        v = self.lib.get_video(vid)
        if not v:
            return False
        ch = self.lib.get_channel(v.get("channel_id"))
        if ch and ch.get("owned"):
            return True
        if ch and ch.get("featured"):
            return is_owner_pc() and bool(v.get("owner_added"))
        return bool(ch and ch.get("owned", True))

    def _edit_video_dialog(self, vid):
        v = self.lib.get_video(vid)
        if not v:
            return
        if not self._may_manage_video(vid):
            self.toast("You can only edit your own videos")
            return
        top = tk.Toplevel(self)
        top.title("Edit video")
        top.configure(bg=BG)
        top.geometry("520x420")
        top.transient(self)
        tk.Label(top, text="Title", bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x", padx=20, pady=(16, 2))
        tv = tk.StringVar(value=v.get("title") or "")
        tk.Entry(top, textvariable=tv, bg=SEARCH_BG, fg=TXT, insertbackground=TXT, relief="flat",
                 font=(FONT_UI, 12)).pack(fill="x", padx=20, ipady=6)
        tk.Label(top, text="Description", bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x", padx=20, pady=(12, 2))
        desc = tk.Text(top, bg=SEARCH_BG, fg=TXT, insertbackground=TXT, relief="flat", height=6,
                       font=(FONT_UI, 11), wrap="word")
        desc.pack(fill="x", padx=20)
        desc.insert("1.0", v.get("description") or "")
        short_var = tk.BooleanVar(value=bool(v.get("is_short")))
        tk.Checkbutton(top, text="Post as NOT SHORT", variable=short_var, bg=BG, fg=TXT,
                       selectcolor=CARD, activebackground=BG, activeforeground=TXT,
                       font=(FONT_UI, 11)).pack(anchor="w", padx=20, pady=10)
        thumb_path = {"p": None}

        def pick_thumb():
            p = filedialog.askopenfilename(parent=top, title="Choose thumbnail",
                                           filetypes=[("Images", "*.jpg;*.jpeg;*.png;*.webp")])
            if p:
                thumb_path["p"] = p

        Pill(top, "Change thumbnail", cmd=pick_thumb, fill=CARD, fg=TXT, hover=HOVER,
             radius=14, padx=12, pady=6, font=(FONT_UI, 10)).pack(anchor="w", padx=20)

        def save():
            self.lib.update_video(vid, title=tv.get().strip(), description=desc.get("1.0", "end").strip(),
                                  thumb_src=thumb_path["p"])
            vv = self.lib.get_video(vid)
            if vv:
                vv["is_short"] = bool(short_var.get())
                self.lib.save()
            top.destroy()
            self._fill_studio()
            self.toast("Saved")

        Pill(top, "Save", cmd=save, fill=WHITE, fg=BLACK, hover="#e5e5e5",
             radius=16, padx=16, pady=6, font=(FONT_UI, 11, "bold")).pack(anchor="e", padx=20, pady=16)

    def _delete_video_ask(self, vid):
        v = self.lib.get_video(vid)
        if not v:
            return
        if not self._may_manage_video(vid):
            self.toast("You can only delete your own videos")
            return
        if messagebox.askyesno(APP, "Delete “%s”? This cannot be undone." % (v.get("title") or "video"),
                               parent=self):
            self.lib.delete_video(vid)
            self._fill_studio()
            self.toast("Deleted")

    def _studio_upload(self, parent, ch):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        tk.Label(sc.inner, text="Upload", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 8))
        tk.Label(sc.inner, text="Publishes to  %s  %s" % (ch.get("name"), ch.get("handle") or ""),
                 bg=BG, fg=MUT, font=(FONT_UI, 12), anchor="w").pack(fill="x", padx=24, pady=(0, 12))
        Pill(sc.inner, "Pick video files", cmd=lambda: self._pick_uploads(sc.inner, ch),
             fill=WHITE, fg=BLACK, hover="#e5e5e5", radius=18, padx=16, pady=8,
             font=(FONT_UI, 11, "bold")).pack(anchor="w", padx=24)
        self._upload_box = tk.Frame(sc.inner, bg=BG)
        self._upload_box.pack(fill="both", expand=True, padx=24, pady=16)
        self._upload_rows = []

    def _pick_uploads(self, _host, ch):
        paths = filedialog.askopenfilenames(
            parent=self, title="Upload videos", initialdir=downloads_dir(),
            filetypes=VID_TYPES,
        )
        if not paths:
            return
        for path in paths:
            if not os.path.isfile(path):
                continue
            self._add_upload_row(path)

    def _add_upload_row(self, path):
        box = self._upload_box
        info = probe_media(path)
        auto = looks_like_short(path, info)
        row = tk.Frame(box, bg=CARD)
        row.pack(fill="x", pady=8)
        inner = tk.Frame(row, bg=CARD)
        inner.pack(fill="x", padx=12, pady=10)
        tk.Label(inner, text=os.path.basename(path), bg=CARD, fg=MUT, font=(FONT_UI, 9),
                 anchor="w").pack(fill="x")
        tv = tk.StringVar(value=os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ").title())
        tk.Label(inner, text="Title", bg=CARD, fg=MUT, font=(FONT_UI, 9), anchor="w").pack(fill="x", pady=(6, 0))
        tk.Entry(inner, textvariable=tv, bg=SEARCH_BG, fg=TXT, insertbackground=TXT, relief="flat",
                 font=(FONT_UI, 12)).pack(fill="x", ipady=5)
        tk.Label(inner, text="Description", bg=CARD, fg=MUT, font=(FONT_UI, 9), anchor="w").pack(fill="x", pady=(6, 0))
        desc = tk.Text(inner, bg=SEARCH_BG, fg=TXT, insertbackground=TXT, relief="flat", height=3,
                       font=(FONT_UI, 11), wrap="word")
        desc.pack(fill="x")
        short_var = tk.BooleanVar(value=auto)
        cbfr = tk.Frame(inner, bg=CARD)
        cbfr.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(cbfr, text="Post as NOT SHORT", variable=short_var, bg=CARD, fg=TXT,
                       selectcolor=BG, activebackground=CARD, activeforeground=TXT,
                       font=(FONT_UI, 11)).pack(side="left")
        if auto:
            tk.Label(cbfr, text="  ·  Detected as a vertical clip (60 seconds or under)",
                     bg=CARD, fg=MUT, font=(FONT_UI, 9)).pack(side="left")
        thumb_path = {"p": None}

        def pick_thumb():
            p = filedialog.askopenfilename(parent=self, title="Choose thumbnail",
                                           filetypes=[("Images", "*.jpg;*.jpeg;*.png;*.webp")])
            if p:
                thumb_path["p"] = p
                self.toast("Thumbnail chosen")

        Pill(inner, "Custom thumbnail", cmd=pick_thumb, fill=HOVER, fg=TXT, hover=CARD,
             radius=14, padx=10, pady=4, font=(FONT_UI, 9)).pack(anchor="w", pady=(8, 0))
        rec = {"path": path, "title": tv, "desc": desc, "short": short_var, "thumb": thumb_path, "frame": row}
        self._upload_rows.append(rec)
        # Publish button once, under the box
        if not getattr(self, "_publish_btn", None) or not self._publish_btn.winfo_exists():
            self._publish_btn = Pill(box.master, "Publish", cmd=self._publish_uploads,
                                     fill=WHITE, fg=BLACK, hover="#e5e5e5", radius=18,
                                     padx=18, pady=8, font=(FONT_UI, 12, "bold"))
            self._publish_btn.pack(anchor="w", padx=24, pady=(0, 24))

    def _publish_uploads(self):
        ch = self.lib.current_channel()
        if not ch:
            self.toast("Create a channel first")
            return
        rows = [r for r in getattr(self, "_upload_rows", []) if os.path.isfile(r["path"])]
        if not rows:
            self.toast("Pick at least one file")
            return
        n = 0
        for r in rows:
            title = r["title"].get().strip()
            desc = r["desc"].get("1.0", "end").strip()
            try:
                self.lib.import_video(
                    r["path"], title, desc, ch["id"],
                    thumb_src=r["thumb"]["p"], is_short=bool(r["short"].get()),
                )
                n += 1
            except Exception as e:
                messagebox.showerror(APP, "Could not publish %s:\n%s" % (os.path.basename(r["path"]), e), parent=self)
        self._upload_rows = []
        self.toast("Published %d video%s — now on Home" % (n, "" if n == 1 else "s"))
        self.studio_tab = "content"
        self._fill_studio()

    def _studio_owner(self, parent):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        inner = sc.inner
        tk.Label(inner, text="Owner tools", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 6))
        tk.Label(inner, text="Add a video to a featured channel. It will show on that channel and on Home. Bot accounts apply as usual.",
                 bg=BG, fg=MUT, font=(FONT_UI, 12), wraplength=720, justify="left",
                 anchor="w").pack(fill="x", padx=24, pady=(0, 16))

        box = tk.Frame(inner, bg=CARD)
        box.pack(fill="x", padx=24, pady=(0, 20))
        pad = tk.Frame(box, bg=CARD)
        pad.pack(fill="x", padx=16, pady=16)
        tk.Label(pad, text="Featured channel", bg=CARD, fg=MUT, font=(FONT_UI, 10),
                 anchor="w").pack(fill="x")
        names = [c.get("name") or "" for c in self.lib.featured_channels()]
        self._owner_ch_var = tk.StringVar(value=names[0] if names else "")
        om = tk.OptionMenu(pad, self._owner_ch_var, *(names or [""]))
        om.configure(bg=SEARCH_BG, fg=TXT, activebackground=HOVER, activeforeground=TXT,
                     highlightthickness=0, bd=0, font=(FONT_UI, 11))
        try:
            om["menu"].configure(bg=CARD, fg=TXT, activebackground=HOVER, activeforeground=TXT, bd=0)
        except Exception:
            pass
        om.pack(fill="x", pady=(4, 12))
        Pill(pad, "Add video to featured channel", cmd=self._owner_add_featured_video,
             fill=WHITE, fg=BLACK, hover="#e5e5e5", radius=18, padx=16, pady=8,
             font=(FONT_UI, 11, "bold")).pack(anchor="w")

        tk.Label(inner, text="Videos you added", bg=BG, fg=TXT, font=(FONT_UI, 16, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 8))
        added = self.lib.owner_added_videos()
        if not added:
            tk.Label(inner, text="No owner-added videos yet.", bg=BG, fg=MUT,
                     font=(FONT_UI, 12), anchor="w").pack(fill="x", padx=24, pady=8)
            return
        for v in added:
            ch = self.lib.get_channel(v.get("channel_id")) or {}
            row = tk.Frame(inner, bg=BG)
            row.pack(fill="x", padx=24, pady=6)
            tw, th = (80, 142) if v.get("is_short") else (128, 72)
            im = rounded_thumb(v.get("thumb") or "", tw, th, 6, v.get("duration") or 0, BG)
            ph = ImageTk.PhotoImage(im)
            self._photos["ow-" + v["id"]] = ph
            tk.Label(row, image=ph, bg=BG, bd=0).pack(side="left")
            col = tk.Frame(row, bg=BG)
            col.pack(side="left", fill="x", expand=True, padx=10)
            tk.Label(col, text=v.get("title") or "Untitled", bg=BG, fg=TXT,
                     font=(FONT_UI, 12, "bold"), anchor="w").pack(fill="x")
            meta = "%s  ·  %s" % (ch.get("name") or "Featured", fmt_ago(v.get("uploaded")))
            tk.Label(col, text=meta, bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x")
            Pill(row, "Edit", cmd=lambda vid=v["id"]: self._edit_video_dialog(vid),
                 fill=CARD, fg=TXT, hover=HOVER, radius=14, padx=10, pady=4,
                 font=(FONT_UI, 9)).pack(side="left", padx=4)
            Pill(row, "Delete", cmd=lambda vid=v["id"]: self._delete_video_ask(vid),
                 fill=CARD, fg=TXT, hover=HOVER, radius=14, padx=10, pady=4,
                 font=(FONT_UI, 9)).pack(side="left", padx=4)

    def _owner_add_featured_video(self):
        if not is_owner_pc():
            return
        name = (getattr(self, "_owner_ch_var", None).get() if getattr(self, "_owner_ch_var", None) else "") or ""
        ch = self.lib.get_channel_by_name(name)
        if not ch or not ch.get("featured"):
            self.toast("Pick a featured channel")
            return
        path = filedialog.askopenfilename(
            parent=self, title="Add video to featured channel",
            initialdir=downloads_dir(), filetypes=VID_TYPES,
        )
        if not path or not os.path.isfile(path):
            return
        title = os.path.splitext(os.path.basename(path))[0]
        title = title.replace("-", " ").replace("_", " ").strip() or "Untitled"
        try:
            self.lib.import_video(path, title, "", ch["id"], owner_added=True)
        except Exception as e:
            messagebox.showerror(APP, "Could not add that video:\n%s" % e, parent=self)
            return
        self.toast("Added to %s — now on Home" % (ch.get("name") or "channel"))
        self.studio_tab = "owner"
        self._fill_studio()

    def _studio_channel(self, parent, ch):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        tk.Label(sc.inner, text="Channel" if ch else "Create a channel",
                 bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"), anchor="w").pack(fill="x", padx=24, pady=(8, 16))
        self._channel_form(sc.inner, ch)

    def _studio_new_channel(self, first=False):
        self.studio_tab = "channel"
        # show a blank form: temporarily clear current? better a dialog
        top = tk.Toplevel(self)
        top.title("Create a channel")
        top.configure(bg=BG)
        top.geometry("560x560")
        top.transient(self)
        tk.Label(top, text="Create a channel", bg=BG, fg=TXT, font=(FONT_UI, 18, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(16, 8))
        self._channel_form(top, None, dialog=top, first=first)

    def _channel_form(self, parent, ch, dialog=None, first=False):
        name_v = tk.StringVar(value=(ch.get("name") if ch else ""))
        handle_v = tk.StringVar(value=(ch.get("handle") if ch else ""))
        assets = {"avatar": ch.get("avatar") if ch else "", "banner": ch.get("banner") if ch else ""}

        def field(label, var):
            tk.Label(parent, text=label, bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x", padx=24, pady=(8, 2))
            e = tk.Entry(parent, textvariable=var, bg=SEARCH_BG, fg=TXT, insertbackground=TXT,
                         relief="flat", font=(FONT_UI, 12))
            e.pack(fill="x", padx=24, ipady=6)
            return e

        field("Channel name", name_v)
        field("Handle", handle_v)
        tk.Label(parent, text="Description", bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x", padx=24, pady=(8, 2))
        desc = tk.Text(parent, bg=SEARCH_BG, fg=TXT, insertbackground=TXT, relief="flat", height=5,
                       font=(FONT_UI, 11), wrap="word")
        desc.pack(fill="x", padx=24)
        if ch:
            desc.insert("1.0", ch.get("description") or "")

        def pick(kind):
            p = filedialog.askopenfilename(parent=self, title="Choose %s" % kind,
                                           filetypes=[("Images", "*.jpg;*.jpeg;*.png;*.webp")])
            if p:
                assets[kind] = p
                self.toast("%s chosen" % kind.title())

        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", padx=24, pady=12)
        Pill(row, "Choose avatar", cmd=lambda: pick("avatar"), fill=CARD, fg=TXT, hover=HOVER,
             radius=14, padx=12, pady=6, font=(FONT_UI, 10)).pack(side="left", padx=(0, 8))
        Pill(row, "Choose banner (optional)", cmd=lambda: pick("banner"), fill=CARD, fg=TXT, hover=HOVER,
             radius=14, padx=12, pady=6, font=(FONT_UI, 10)).pack(side="left")

        def save():
            name = name_v.get().strip()
            if not name:
                messagebox.showinfo(APP, "Give the channel a name.", parent=dialog or self)
                return
            handle = handle_v.get().strip()
            description = desc.get("1.0", "end").strip()
            if ch:
                cid = ch["id"]
                av = self.lib.copy_image_asset(assets["avatar"], "avatars", cid) if assets.get("avatar") and assets["avatar"] != ch.get("avatar") else ch.get("avatar")
                bn = self.lib.copy_image_asset(assets["banner"], "banners", cid) if assets.get("banner") and assets["banner"] != ch.get("banner") else ch.get("banner")
                self.lib.update_channel(cid, name=name, handle=handle, description=description,
                                        avatar=av, banner=bn)
                self.toast("Channel saved")
            else:
                new = self.lib.add_channel(name, handle, description, owned=True)
                cid = new["id"]
                av = self.lib.copy_image_asset(assets.get("avatar"), "avatars", cid) if assets.get("avatar") else ""
                bn = self.lib.copy_image_asset(assets.get("banner"), "banners", cid) if assets.get("banner") else ""
                if av or bn:
                    self.lib.update_channel(cid, avatar=av, banner=bn)
                self.lib.switch_channel(cid)
                self.toast("Channel created")
            self._refresh_avatar()
            if dialog:
                dialog.destroy()
            if self.page == "studio":
                self._fill_studio()

        Pill(parent, "Save channel" if ch else "Create channel", cmd=save,
             fill=WHITE, fg=BLACK, hover="#e5e5e5", radius=16, padx=16, pady=8,
             font=(FONT_UI, 12, "bold")).pack(anchor="w", padx=24, pady=18)

    def _studio_bots(self, parent, ch):
        sc = VScroll(parent, bg=BG)
        sc.pack(fill="both", expand=True)
        hdr = tk.Frame(sc.inner, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(8, 4))
        tk.Label(hdr, text="NOT TUBE BOT ACCOUNTS", bg=BG, fg=TXT, font=(FONT_UI, 22, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(sc.inner,
                 text="Automated and always on. Bot accounts (ntbot_4821 and similar) push every video to 2K views, with likes, notscribers and comments. Nothing to switch on.",
                 bg=BG, fg=MUT, font=(FONT_UI, 12), wraplength=760, justify="left", anchor="w").pack(fill="x", padx=24, pady=(0, 12))
        self._bot_live_lbl = tk.Label(sc.inner, text=self._bot_live_text(ch), bg=CARD, fg=TXT,
                                      font=(FONT_UI, 13), anchor="w", padx=16, pady=12)
        self._bot_live_lbl.pack(fill="x", padx=24, pady=(0, 16))

        tk.Label(sc.inner, text="Per video", bg=BG, fg=TXT, font=(FONT_UI, 16, "bold"),
                 anchor="w").pack(fill="x", padx=24, pady=(8, 8))
        vids = self.lib.channel_videos(ch["id"])
        if not vids:
            tk.Label(sc.inner, text="Publish a video first.", bg=BG, fg=MUT, font=(FONT_UI, 12)).pack(padx=24, pady=20)
            return
        for v in vids:
            row = tk.Frame(sc.inner, bg=BG)
            row.pack(fill="x", padx=24, pady=8)
            tw, th = (54, 96) if v.get("is_short") else (96, 54)
            im = rounded_thumb(v.get("thumb") or "", tw, th, 6, v.get("duration") or 0, BG)
            ph = ImageTk.PhotoImage(im)
            self._photos["bt-" + v["id"]] = ph
            tk.Label(row, image=ph, bg=BG, bd=0).pack(side="left")
            col = tk.Frame(row, bg=BG)
            col.pack(side="left", fill="x", expand=True, padx=10)
            title = v.get("title") or "Untitled"
            if v.get("is_short"):
                title = "NOT SHORT  ·  " + title
            tk.Label(col, text=title, bg=BG, fg=TXT, font=(FONT_UI, 12, "bold"), anchor="w").pack(fill="x")
            tk.Label(col, text="%s  ·  %s bot views" % (fmt_views(v.get("views") or 0), fmt_count(v.get("bot_views") or 0)),
                     bg=BG, fg=MUT, font=(FONT_UI, 10), anchor="w").pack(fill="x")
            bv = min(BOT_TARGET, int(v.get("bot_views") or 0))
            tk.Label(col, text=("Reached 2K  ✓" if bv >= BOT_TARGET else "Bots active  ·  %s / 2K" % fmt_count(bv)),
                     bg=BG, fg=TXT, font=(FONT_UI, 10, "bold"), anchor="w").pack(fill="x", pady=(4, 0))

    def _boost_controls(self, parent, on, intensity, apply):
        bar = tk.Frame(parent, bg=parent.cget("bg"))
        bar.pack(fill="x", pady=(6, 0))
        state = {"on": on, "intensity": intensity if intensity in INTENSITY_VPM else "medium"}

        def redraw():
            for w in bar.winfo_children():
                w.destroy()
            Pill(bar, "On" if state["on"] else "Off",
                 cmd=lambda: toggle(),
                 fill=WHITE if state["on"] else CARD,
                 fg=BLACK if state["on"] else TXT,
                 hover=HOVER, radius=14, padx=12, pady=4, font=(FONT_UI, 10, "bold")).pack(side="left", padx=(0, 10))
            tk.Label(bar, text="Intensity", bg=parent.cget("bg"), fg=MUT, font=(FONT_UI, 9)).pack(side="left", padx=(0, 6))
            for name, lab in (("low", "Low"), ("medium", "Medium"), ("rocket", "Rocket")):
                sel = state["intensity"] == name
                Pill(bar, lab, cmd=lambda n=name: set_i(n),
                     fill=WHITE if sel else CARD, fg=BLACK if sel else TXT,
                     hover=HOVER, radius=14, padx=10, pady=4, font=(FONT_UI, 9, "bold" if sel else "normal")).pack(side="left", padx=3)

        def toggle():
            state["on"] = not state["on"]
            apply(state["on"], state["intensity"])
            redraw()
            self._refresh_bot_live()

        def set_i(n):
            state["intensity"] = n
            apply(state["on"], state["intensity"])
            redraw()
            self._refresh_bot_live()

        redraw()

    def _refresh_bot_live(self):
        ch = self.lib.current_channel()
        lbl = getattr(self, "_bot_live_lbl", None)
        if lbl and ch:
            try:
                if lbl.winfo_exists():
                    lbl.configure(text=self._bot_live_text(ch))
            except Exception:
                pass

    # ---------- player ----------
    def _start_player(self, v, vertical=False):
        path = v.get("path") or ""
        if not path or not os.path.isfile(path):
            self.toast("Video file is missing")
            return
        self._player_kill()
        self.player_path = path
        self.player_t = 0.0
        self.player_dur = float(v.get("duration") or 0) or probe_duration(path)
        if vertical:
            self.player_w, self.player_h = 405, 720
        else:
            self.player_w, self.player_h = PLAY_W, PLAY_H
        self.player_playing = False
        self._player_show_still(0.0)
        self._update_player_time()
        if hasattr(self, "seek"):
            try:
                self.seek.set(0)
            except Exception:
                pass
        self.after(180, self.player_play)

    def player_toggle(self):
        if self.player_playing:
            self.player_pause()
        else:
            self.player_play()

    def player_play(self):
        if not self.player_path:
            return
        if self.player_t >= max(0.1, self.player_dur - 0.15) and not self._player_loop:
            self.player_t = 0.0
        self.player_playing = True
        self._player_start_pipe(self.player_t)
        self._sync_play_btn()
        self._player_tick()

    def player_pause(self):
        self.player_playing = False
        if self.player_job:
            try:
                self.after_cancel(self.player_job)
            except Exception:
                pass
            self.player_job = None
        self._player_kill()
        self._sync_play_btn()

    def _sync_play_btn(self):
        btn = getattr(self, "b_play", None)
        if not btn:
            return
        try:
            btn.configure(image=self._photos["p_pause" if self.player_playing else "p_play"])
        except Exception:
            pass

    def _player_audio_stop(self):
        if os.name == "nt":
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass

    def _player_audio_start(self, start_t):
        if os.name != "nt" or not self.player_path:
            return
        try:
            import winsound
            if not self._audio_tmp:
                self._audio_tmp = os.path.join(tempfile.gettempdir(), "not_tube_player.wav")
            self._player_audio_stop()
            vol = 0.0 if self._muted else max(0.0, min(1.0, self._volume))
            if vol <= 0.001:
                return
            p = run_hidden([
                ffmpeg_exe(), "-y", "-loglevel", "error",
                "-ss", "%.3f" % max(0.0, start_t), "-i", self.player_path,
                "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le",
                "-af", "volume=%.3f" % vol,
                self._audio_tmp,
            ], timeout=40)
            if p.returncode == 0 and os.path.isfile(self._audio_tmp) and os.path.getsize(self._audio_tmp) > 1000:
                winsound.PlaySound(self._audio_tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def _player_kill(self):
        self._player_audio_stop()
        proc = self.player_proc
        self.player_proc = None
        if proc is None:
            return
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=1)
        except Exception:
            pass

    def _player_start_pipe(self, start_t):
        self._player_kill()
        ff = ffmpeg_exe()
        w, h = self.player_w, self.player_h
        cmd = [
            ff, "-hide_banner", "-loglevel", "error",
            "-ss", "%.3f" % max(0.0, start_t),
            "-i", self.player_path,
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-vf", "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black" % (w, h, w, h),
            "-an", "-sn", "-r", str(FPS), "-",
        ]
        self._player_audio_start(start_t)
        try:
            self.player_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                bufsize=w * h * 3 * 2, creationflags=NO_WINDOW)
            self._pipe_t0 = time.time()
            self._pipe_start = start_t
        except Exception as e:
            self.player_proc = None
            messagebox.showerror(APP, "Could not start playback:\n%s" % e, parent=self)
            self.player_playing = False

    def _player_read_frame(self):
        proc = self.player_proc
        if not proc or not proc.stdout:
            return None
        need = self.player_w * self.player_h * 3
        buf = b""
        while len(buf) < need:
            chunk = proc.stdout.read(need - len(buf))
            if not chunk:
                return None
            buf += chunk
        return Image.frombytes("RGB", (self.player_w, self.player_h), buf)

    def _player_tick(self):
        if not self.player_playing:
            return
        im = self._player_read_frame()
        if im is None:
            if self._player_loop and self.player_path:
                self.player_t = 0.0
                self._player_start_pipe(0.0)
                self.player_job = self.after(int(1000 / FPS), self._player_tick)
                return
            self.player_playing = False
            self.player_t = self.player_dur
            self._update_player_time()
            self._player_kill()
            self._sync_play_btn()
            return
        self.player_frame = im
        elapsed = time.time() - self._pipe_t0
        self.player_t = min(self.player_dur, self._pipe_start + elapsed)
        if hasattr(self, "seek"):
            try:
                if self.player_dur > 0 and not self.seek._drag:
                    self.seek.set(self.player_t / self.player_dur)
            except Exception:
                pass
        self._update_player_time()
        self._player_redraw()
        self.player_job = self.after(int(1000 / FPS), self._player_tick)

    def _player_show_still(self, t):
        if not self.player_path:
            return
        ff = ffmpeg_exe()
        w, h = self.player_w, self.player_h
        cmd = [
            ff, "-hide_banner", "-loglevel", "error",
            "-ss", "%.3f" % max(0.0, t), "-i", self.player_path,
            "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-vf", "scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black" % (w, h, w, h),
            "-",
        ]
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=20, creationflags=NO_WINDOW)
            need = w * h * 3
            if p.stdout and len(p.stdout) >= need:
                self.player_frame = Image.frombytes("RGB", (w, h), p.stdout[:need])
                self._player_redraw()
        except Exception:
            pass

    def _player_redraw(self):
        cv = getattr(self, "player_canvas", None)
        if cv is None:
            return
        try:
            cw, ch = max(1, cv.winfo_width()), max(1, cv.winfo_height())
        except Exception:
            return
        cv.delete("all")
        im = self.player_frame
        if im is None:
            return
        scale = min(cw / im.width, ch / im.height)
        nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
        shown = im.resize((nw, nh), Image.BILINEAR)
        self._player_photo = ImageTk.PhotoImage(shown)
        cv.create_image(cw // 2, ch // 2, image=self._player_photo)

    def _update_player_time(self):
        lbl = getattr(self, "player_time_lbl", None)
        if lbl:
            try:
                lbl.configure(text="%s / %s" % (fmt_dur(self.player_t), fmt_dur(self.player_dur)))
            except Exception:
                pass

    def _on_seek(self, val):
        if self.player_dur <= 0 or not self.player_path:
            return
        self.player_t = float(val) * self.player_dur
        was = self.player_playing
        self.player_pause()
        self._player_show_still(self.player_t)
        if was:
            self.player_play()

    def _set_volume(self, val):
        self._volume = max(0.0, min(1.0, float(val)))
        self._muted = self._volume <= 0.001
        self._refresh_vol_icon()
        if self.player_playing:
            self._player_audio_start(self.player_t)

    def _toggle_mute(self):
        self._muted = not self._muted
        self._refresh_vol_icon()
        if hasattr(self, "volbar"):
            self.volbar.set(0 if self._muted else self._volume)
        if self.player_playing:
            if self._muted:
                self._player_audio_stop()
            else:
                self._player_audio_start(self.player_t)

    def _refresh_vol_icon(self):
        btn = getattr(self, "b_vol", None)
        if not btn:
            return
        try:
            btn.configure(image=self._photos["p_mute" if (self._muted or self._volume <= 0.001) else "p_vol"])
        except Exception:
            pass

    def toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        try:
            self.attributes("-fullscreen", self._fullscreen)
        except Exception:
            self.wm_attributes("-fullscreen", self._fullscreen)
        if self.page == "watch":
            self.after(80, self._layout_player)

    def _entry_focused(self):
        w = self.focus_get()
        return isinstance(w, (tk.Entry, tk.Text))

    def _key_space(self, ev):
        if self._entry_focused():
            return
        if self.page in ("watch", "shorts"):
            self.player_toggle()
            return "break"

    def _key_seek(self, secs):
        if self._entry_focused() or self.page != "watch":
            return
        self.player_t = max(0.0, min(self.player_dur, self.player_t + secs))
        was = self.player_playing
        self.player_pause()
        self._player_show_still(self.player_t)
        if was:
            self.player_play()

    def _key_full(self):
        if self._entry_focused():
            return
        if self.page == "watch":
            self.toggle_fullscreen()

    def _key_mute(self):
        if self._entry_focused():
            return
        if self.page in ("watch", "shorts"):
            self._toggle_mute()

    def _key_esc(self, ev):
        if self._fullscreen:
            self.toggle_fullscreen()
            return "break"
        if self.page in ("watch", "shorts", "studio", "channel"):
            self.show_page("home")
            return "break"

    def _bind_shorts_keys(self):
        self.bind("<Up>", lambda e: self._shorts_key(-1))
        self.bind("<Down>", lambda e: self._shorts_key(1))

    def _shorts_key(self, delta):
        if self._entry_focused() or self.page != "shorts":
            return
        self._shorts_step(delta)
        return "break"

    # ---------- menus / updates / about ----------
    def _avatar_menu(self):
        m = tk.Menu(self, tearoff=0, bg="#282828", fg=TXT, activebackground=HOVER,
                    activeforeground=TXT, bd=0, font=(FONT_UI, 10))
        ch = self.lib.current_channel()
        if ch:
            m.add_command(label="Your channel", command=lambda: self.open_channel(ch["id"]))
        m.add_command(label="NOT TUBE STUDIO", command=lambda: self.open_studio("dashboard"))
        m.add_command(label="Switch channel", command=lambda: self._switch_channel_menu(self.avatar_lbl))
        m.add_separator()
        m.add_command(label="About", command=self._about)
        try:
            m.tk_popup(self.avatar_lbl.winfo_rootx(), self.avatar_lbl.winfo_rooty() + self.avatar_lbl.winfo_height())
        finally:
            m.grab_release()
        self._menu = m

    def _about(self):
        messagebox.showinfo(
            APP,
            "%s  %s\n\nA local video library.\n\n%s" % (APP, APP_VERSION, "\u00a9HYPERION SYSTEMS"),
            parent=self,
        )

    def check_updates(self):
        self.toast("Checking for updates…")

        def work():
            st, d = check_update()
            self.after(0, lambda: self._update_result(st, d))

        threading.Thread(target=work, daemon=True).start()

    def _update_result(self, st, d):
        if st == "error":
            self.toast(str(d))
            return
        if st == "latest":
            self.toast(str(d))
            return
        if d.get("link") and messagebox.askyesno(
                APP, "Version %s is available.\n\n%s\n\nOpen the download page?" % (
                    d["version"], d.get("notes") or ""), parent=self):
            webbrowser.open(d["link"])

    def _boost_tick(self):
        try:
            added = self.lib.apply_boosts()
            if added and added.get("views"):
                self._refresh_bot_live()
        except Exception:
            pass
        self._boost_job = self.after(1000, self._boost_tick)

    def on_close(self):
        self.player_pause()
        self._player_kill()
        if self._boost_job:
            try:
                self.after_cancel(self._boost_job)
            except Exception:
                pass
        try:
            if self._fullscreen:
                self.attributes("-fullscreen", False)
        except Exception:
            pass
        self.destroy()


# -------------------- fonts for PIL (Wine-safe) --------------------
def pil_font_path():
    cands = [
        r"Z:\usr\share\fonts\truetype\liberation\LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        r"C:\windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf"),
    ]
    for p in cands:
        if p and os.path.isfile(p):
            return p
    return None


def get_pil_font(size):
    p = pil_font_path()
    if p:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


# -------------------- seed / smoke / shots / main --------------------
FEATURED_CHANNELS = [
    dict(slug="miravalefits", name="Mira Vale Fits", handle="@miravalefits",
         description="Evening try-on hauls from a bright loft. Satin dresses, leather jackets and heels.",
         color_subs=28400, featured=True),
    dict(slug="novaquinnstyle", name="Nova Quinn Style", handle="@novaquinnstyle",
         description="Clean going-out looks and satin evening dresses, filmed in a quiet studio.",
         color_subs=19200, featured=True),
    dict(slug="linapalomalooks", name="Lina Paloma Looks", handle="@linapalomalooks",
         description="Date-night dresses and leather jackets, filmed in warm lamp light.",
         color_subs=22100, featured=True),
    dict(slug="sablewrenwardrobe", name="Sable Wren Wardrobe", handle="@sablewrenwardrobe",
         description="Gold satin, leather jackets and midi bodycon looks from an industrial loft.",
         color_subs=31600, featured=True),
]

FEATURED_VIDEOS = [
    dict(seed_id="mira-haul-1", file="mira-satin-slip-haul.mp4", thumb="mira_satin_slip_thumb.jpg",
         title="Date night satin slip dress haul",
         channel="Mira Vale Fits",
         description="An opaque black satin midi slip dress and pointed heels, filmed in warm evening light.",
         days=1, views=920, likes=62, category="haul"),
    dict(seed_id="mira-haul-2", file="mira-leather-jacket-haul.mp4", thumb="mira_leather_jacket_thumb.jpg",
         title="Leather jacket going-out look",
         channel="Mira Vale Fits",
         description="A black leather jacket over a high-neck top, slim trousers and heeled boots.",
         days=3, views=740, likes=48, category="haul"),
    dict(seed_id="mira-haul-3", file="mira-burgundy-midi-haul.mp4", thumb="mira_burgundy_midi_thumb.jpg",
         title="Burgundy midi bodycon try-on",
         channel="Mira Vale Fits",
         description="A long-sleeve burgundy midi dress, hem below the knee, with black heels.",
         days=5, views=610, likes=41, category="haul"),
    dict(seed_id="nova-haul-1", file="nova-emerald-satin-haul.mp4", thumb="nova_emerald_satin_thumb.jpg",
         title="Emerald satin evening dress haul",
         channel="Nova Quinn Style",
         description="An emerald satin midi dress and pointed heels in a quiet evening studio.",
         days=1, views=1080, likes=71, category="haul"),
    dict(seed_id="nova-haul-2", file="nova-blazer-dress-haul.mp4", thumb="nova_blazer_dress_thumb.jpg",
         title="Tuxedo blazer dress try-on",
         channel="Nova Quinn Style",
         description="A tailored black blazer dress over a high-neck top, hem at the knee.",
         days=4, views=680, likes=44, category="haul"),
    dict(seed_id="nova-haul-3", file="nova-satin-heels-haul.mp4", thumb="nova_satin_heels_thumb.jpg",
         title="Going-out heels and satin haul",
         channel="Nova Quinn Style",
         description="A champagne satin blouse, black midi pencil skirt and tan heels.",
         days=6, views=540, likes=36, category="haul"),
    dict(seed_id="lina-haul-1", file="lina-datenight-dress-haul.mp4", thumb="lina_datenight_dress_thumb.jpg",
         title="Date night dress try-on haul",
         channel="Lina Paloma Looks",
         description="A deep-red midi dress, hem below the knee, and black heels in lamp light.",
         days=1, views=1160, likes=74, category="haul"),
    dict(seed_id="lina-haul-2", file="lina-leather-dress-haul.mp4", thumb="lina_leather_dress_thumb.jpg",
         title="Leather jacket and black dress haul",
         channel="Lina Paloma Looks",
         description="A leather jacket over an opaque black midi dress and heeled boots.",
         days=3, views=830, likes=55, category="haul"),
    dict(seed_id="lina-haul-3", file="lina-midnight-slip-haul.mp4", thumb="lina_midnight_slip_thumb.jpg",
         title="Midnight slip dress try-on",
         channel="Lina Paloma Looks",
         description="A midnight-navy satin midi slip dress and silver heels.",
         days=7, views=590, likes=39, category="haul"),
    dict(seed_id="sable-haul-1", file="sable-gold-satin-haul.mp4", thumb="sable_gold_satin_thumb.jpg",
         title="Gold satin evening dress haul",
         channel="Sable Wren Wardrobe",
         description="A gold satin midi evening dress and black heels in the loft.",
         days=2, views=1240, likes=81, category="haul"),
    dict(seed_id="sable-haul-2", file="sable-leather-heels-haul.mp4", thumb="sable_leather_heels_thumb.jpg",
         title="Leather jacket and heels going-out haul",
         channel="Sable Wren Wardrobe",
         description="A leather jacket, high-neck top, dark trousers and heeled boots.",
         days=4, views=770, likes=50, category="haul"),
    dict(seed_id="sable-haul-3", file="sable-black-midi-haul.mp4", thumb="sable_black_midi_thumb.jpg",
         title="Black midi bodycon try-on",
         channel="Sable Wren Wardrobe",
         description="A long-sleeve black midi dress with a mock neck, hem below the knee.",
         days=6, views=640, likes=43, category="haul"),
]

SAMPLE_CHANNELS = [
    dict(slug="bluehour", name="Blue Hour Films", handle="@bluehour",
         description="Still mornings and long lenses.", color_subs=12400),
    dict(slug="cedarstone", name="Cedar & Stone", handle="@cedarstone",
         description="Handmade objects, slowly.", color_subs=8300),
    dict(slug="atlaswalks", name="Atlas Walks", handle="@atlaswalks",
         description="Routes, weather, and the long way round.", color_subs=15100),
    dict(slug="kitchenwindow", name="Kitchen Window", handle="@kitchenwindow",
         description="Weeknight cooking, no fuss.", color_subs=6200),
    dict(slug="nightmarket", name="Night Market", handle="@nightmarket",
         description="After dark, stalls still open.", color_subs=19800),
    dict(slug="northwind", name="Northwind Labs", handle="@northwind",
         description="Small experiments, clearly explained.", color_subs=22100),
]

SAMPLE_VIDEOS = [
    dict(file="sunrise-glass-lake.mp4", title="Sunrise over the glass lake",
         channel="Blue Hour Films",
         description="Early light on still water, filmed on a cold morning.",
         days=2, views=18420, likes=640),
    dict(file="handmade-ceramic-bowls.mp4", title="Making handmade ceramic bowls",
         channel="Cedar & Stone",
         description="Throwing, trimming and a first glaze.",
         days=5, views=9320, likes=410),
    dict(file="autumn-streets.mp4", title="A walk through autumn streets",
         channel="Atlas Walks",
         description="Leaves underfoot and a long looping route.",
         days=1, views=22100, likes=890),
    dict(file="tomato-pasta.mp4", title="Three-minute tomato pasta",
         channel="Kitchen Window",
         description="Pan sauce, one pot, dinner is ready.",
         days=8, views=5400, likes=210),
    dict(file="city-lights-rain.mp4", title="City lights after rain",
         channel="Night Market",
         description="Reflections on the wet street after the stalls close.",
         days=3, views=16750, likes=720),
    dict(file="how-radio-waves-travel.mp4", title="How radio waves travel",
         channel="Northwind Labs",
         description="A plain-language walk through antennas and skywave.",
         days=12, views=30400, likes=1100),
    dict(file="desk-setup-tour.mp4", title="Desk setup tour 2026",
         channel="Northwind Labs",
         description="Lights, cables, and the one drawer that matters.",
         days=20, views=12880, likes=530),
    dict(file="night-market-food.mp4", title="Night market street food",
         channel="Night Market",
         description="A plate from the stall at the far end.",
         days=6, views=9900, likes=360),
    dict(file="coastal-trail-spring.mp4", title="Coastal trail in late spring",
         channel="Atlas Walks",
         description="Wind, salt, and a path that hugs the cliff.",
         days=15, views=7400, likes=280),
    dict(file="paper-lamp-workshop.mp4", title="Paper lamp workshop",
         channel="Cedar & Stone",
         description="Folding a simple lamp and wiring the cord.",
         days=30, views=4100, likes=190),
]

SAMPLE_SHORTS = [
    dict(file="hill-sprint-after-rain.mp4", title="Hill sprint after rain",
         channel="Atlas Walks",
         description="A short burst up the wet hill.",
         days=1, views=2000, likes=140),
    dict(file="lantern-walk-at-dusk.mp4", title="Lantern walk at dusk",
         channel="Night Market",
         description="Paper lanterns coming on one by one.",
         days=2, views=2180, likes=95),
    dict(file="desk-cable-wrap.mp4", title="Desk cable wrap",
         channel="Northwind Labs",
         description="Taming the cable drawer in twenty seconds.",
         days=4, views=1920, likes=80),
]


def _bundle_dirs(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    exe = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else here
    cands = [
        os.path.join(here, *parts),
        res_path(*parts),
        os.path.join(exe, *parts),
        os.path.join(exe, "_internal", *parts),
        os.path.join(r"Z:\workspace\not-tube", *parts),
        os.path.join("/workspace/not-tube", *parts),
    ]
    for d in cands:
        if d and os.path.isdir(d):
            return d
    return cands[0]


def samples_dir():
    return _bundle_dirs("samples")


def channel_art_dir():
    return _bundle_dirs("assets", "channels")


def thumbs_dir():
    return _bundle_dirs("samples", "thumbs")


def _art_file(adir, slug, kind):
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = os.path.join(adir, "%s_%s%s" % (slug, kind, ext))
        if os.path.isfile(p):
            return p
    return ""


OLD_FEATURED_HAUL_FILES = {
    "mira-trench-jeans-haul.mp4", "mira-weekend-knit-haul.mp4",
    "nova-workwear-blazer-haul.mp4", "nova-beige-set-haul.mp4",
    "lina-floral-midi-haul.mp4", "lina-denim-skirt-haul.mp4",
    "sable-utility-jacket-haul.mp4", "sable-wool-coat-haul.mp4",
}


def _is_bundled_featured_seed(lib, v):
    """True for shipped featured haul clips, never for user or owner-added uploads."""
    if not v or v.get("owner_added"):
        return False
    ch = lib.get_channel(v.get("channel_id"))
    if not ch or not ch.get("featured"):
        return False
    if ch.get("owned"):
        return False
    if v.get("seed_id"):
        return True
    sf = v.get("seed_file") or ""
    current = {spec["file"] for spec in FEATURED_VIDEOS} | {spec["seed_id"] for spec in FEATURED_VIDEOS}
    if sf in OLD_FEATURED_HAUL_FILES or sf in current:
        return True
    if v.get("category") == "haul" and not v.get("owner_added"):
        return True
    return False


def ensure_bundled_content(lib, include_classic=False):
    """Idempotently add featured (and optionally classic) bundled channels/videos.
    Replaces outdated bundled featured hauls by seed id. Never wipes user or
    owner-added uploads. Featured channels are not owned by the user."""
    ensure_kim_miyoyazu_featured(lib)
    sdir = samples_dir()
    adir = channel_art_dir()
    tdir = thumbs_dir()
    now = time.time()
    specs = list(FEATURED_CHANNELS)
    if include_classic:
        specs += list(SAMPLE_CHANNELS)
    by_name = {}
    for spec in specs:
        featured = bool(spec.get("featured"))
        owned = (not featured) and bool(spec.get("owned", include_classic and not featured))
        ch = lib.get_channel_by_handle(spec["handle"], spec["name"]) or lib.get_channel_by_name(spec["name"])
        if not ch:
            ch = lib.add_channel(
                spec["name"], spec["handle"], spec["description"],
                owned=owned, subscribers=spec["color_subs"], featured=featured,
                created=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 86400 * 80)),
            )
        else:
            if featured and not ch.get("featured"):
                ch["featured"] = True
            if featured and spec.get("description") and ch.get("description") != spec["description"]:
                lib.update_channel(ch["id"], description=spec["description"])
        av = _art_file(adir, spec["slug"], "avatar")
        bn = _art_file(adir, spec["slug"], "banner")
        kw = {}
        if av and (featured or not (ch.get("avatar") and os.path.isfile(ch.get("avatar")))):
            # Featured avatars are refreshed from bundled art on each ensure.
            copied = lib.copy_image_asset(av, "avatars", ch["id"]) or ""
            if copied:
                kw["avatar"] = copied
        if bn and not (ch.get("banner") and os.path.isfile(ch.get("banner"))):
            kw["banner"] = lib.copy_image_asset(bn, "banners", ch["id"]) or ""
        if kw:
            lib.update_channel(ch["id"], **kw)
        by_name[spec["name"]] = lib.get_channel(ch["id"])

    keep_ids = {spec["seed_id"] for spec in FEATURED_VIDEOS if spec.get("seed_id")}
    keep_files = {spec["file"] for spec in FEATURED_VIDEOS}
    # Drop superseded bundled featured hauls; leave owner-added and user videos alone.
    for v in list(lib.videos()):
        if not _is_bundled_featured_seed(lib, v):
            continue
        sid = v.get("seed_id") or ""
        sfile = v.get("seed_file") or ""
        if sid and sid in keep_ids:
            # Will be replaced in place below if the clip file changed.
            continue
        if not sid and sfile in keep_files:
            continue
        lib.delete_video(v["id"])

    def add_or_replace(spec, is_short):
        ch = by_name.get(spec["channel"])
        if not ch:
            return None
        src = os.path.join(sdir, spec["file"])
        if not os.path.isfile(src):
            return None
        thumb = ""
        if spec.get("thumb"):
            thumb = os.path.join(tdir, spec["thumb"])
            if not os.path.isfile(thumb):
                thumb = os.path.join(sdir, spec["thumb"])
        uploaded = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 86400 * int(spec.get("days") or 1)))
        existing = None
        for v in lib.channel_videos(ch["id"]):
            if spec.get("seed_id") and v.get("seed_id") == spec["seed_id"]:
                existing = v
                break
            if (v.get("seed_file") or "") == spec["file"]:
                existing = v
                break
        if existing:
            # Replace the bundled clip and metadata, keep the same id / counters.
            try:
                dest = existing.get("path") or os.path.join(app_data_dir(), "videos", existing["id"] + ".mp4")
                os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                shutil.copy2(src, dest)
                existing["path"] = dest
                existing["title"] = spec["title"]
                existing["description"] = spec["description"]
                existing["seed_file"] = spec["file"]
                existing["seed_id"] = spec.get("seed_id") or ""
                existing["category"] = spec.get("category") or ""
                existing["is_short"] = bool(is_short)
                info = probe_media(dest)
                existing["duration"] = info.get("duration") or existing.get("duration") or 0
                if thumb and os.path.isfile(thumb):
                    try:
                        im = Image.open(thumb).convert("RGB")
                        tw, th = (360, 640) if is_short else (640, 360)
                        cover_fit(im, tw, th).save(existing.get("thumb") or os.path.join(app_data_dir(), "thumbs", existing["id"] + ".jpg"), "JPEG", quality=90)
                        existing["custom_thumb"] = True
                    except Exception:
                        pass
                lib.save()
            except Exception:
                lib.delete_video(existing["id"])
                existing = None
        if existing:
            return existing
        return lib.import_video(
            src, spec["title"], spec["description"], ch["id"],
            thumb_src=thumb if thumb and os.path.isfile(thumb) else None,
            uploaded=uploaded, views=spec.get("views") or 0, likes=spec.get("likes") or 0,
            is_short=is_short, seed_file=spec["file"], category=spec.get("category") or "",
            seed_id=spec.get("seed_id") or "",
        )

    for spec in FEATURED_VIDEOS:
        add_or_replace(spec, False)
    if include_classic:
        def add_classic(spec, is_short):
            ch = by_name.get(spec["channel"])
            if not ch:
                return None
            for v in lib.channel_videos(ch["id"]):
                if (v.get("seed_file") or "") == spec["file"] or (v.get("title") or "") == spec["title"]:
                    return v
            src = os.path.join(sdir, spec["file"])
            if not os.path.isfile(src):
                return None
            uploaded = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 86400 * int(spec.get("days") or 1)))
            return lib.import_video(
                src, spec["title"], spec["description"], ch["id"],
                uploaded=uploaded, views=spec.get("views") or 0, likes=spec.get("likes") or 0,
                is_short=is_short, seed_file=spec["file"],
            )
        for spec in SAMPLE_VIDEOS:
            add_classic(spec, False)
        for spec in SAMPLE_SHORTS:
            add_classic(spec, True)
    lib.save()
    return lib


def seed_library(reset=True):
    """Build a demo library from the sample clips (for screenshots and first-run testing)."""
    lib = Library()
    if reset:
        lib.data = lib._empty()
        lib.save()
    ensure_bundled_content(lib, include_classic=True)
    by_name = {c.get("name"): c for c in lib.channels()}
    if "Northwind Labs" in by_name:
        lib.switch_channel(by_name["Northwind Labs"]["id"])
    for name in ("Night Market", "Blue Hour Films", "Atlas Walks", "Mira Vale Fits", "Sable Wren Wardrobe"):
        ch = by_name.get(name)
        if ch and not lib.is_notscribed(ch["id"]):
            lib.toggle_notscribe(ch["id"])
    for v in lib.videos():
        if v.get("title") == "How radio waves travel":
            if not lib.data.get("comments", {}).get(v["id"]):
                lib.add_comment(v["id"], "finally a clear explanation", author="Maple Row")
                lib.add_comment(v["id"], "watching this again with a notebook", author="Jon East")
        if v.get("title") == "Hill sprint after rain":
            if not lib.data.get("comments", {}).get(v["id"]):
                lib.add_comment(v["id"], "that last push though", author="Cedar Grove")
        if v.get("title") == "Sunrise over the glass lake":
            if not lib.data.get("comments", {}).get(v["id"]):
                lib.add_comment(v["id"], "the colour on the water is perfect", author="Isla North")
        if v.get("title") == "Date night satin slip dress haul":
            if not lib.data.get("comments", {}).get(v["id"]):
                lib.add_comment(v["id"], "that trench looks so clean", author="Ivy North")
    lib.save()
    return lib


def run_shots():
    seed_library(reset=True)
    app = App()
    app.geometry("1280x720+30+20")
    app.sidebar_open = True
    shots = r"Z:\workspace\not-tube\shots" if os.path.isdir(r"Z:\workspace\not-tube") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
    store = r"Z:\workspace\not-tube\store_art" if os.path.isdir(r"Z:\workspace\not-tube") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "store_art")
    os.makedirs(shots, exist_ok=True)
    os.makedirs(store, exist_ok=True)
    log = []

    def save(name, also_store=None):
        p = os.path.join(shots, name)
        im = _grab(app, p, delay=0.55)
        log.append(name + " " + str(im.size))
        if also_store:
            im.convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS).save(
                os.path.join(store, also_store), "JPEG", quality=90)
        return im

    def go():
        try:
            app.show_page("home")
            app.sidebar_open = True
            app._build_sidebar()
            app.update(); app.update()
            save("ui_home_1.0.4.png", "shot0.jpg")
            # watch a long video
            vids = app.lib.long_videos()
            radio = next((v for v in vids if "radio" in (v.get("title") or "").lower()), vids[0])
            app.open_watch(radio["id"])
            app.update()
            time.sleep(1.2)
            app.update()
            save("ui_watch_1.0.0.png", "shot1.jpg")
            app.player_pause()
            # channel page
            ch = app.lib.get_channel_by_name("Mira Vale Fits") or app.lib.get_channel_by_name("Night Market") or app.lib.current_channel()
            app.open_channel(ch["id"])
            app.update(); time.sleep(0.4)
            save("ui_channel_1.0.4.png")
            # studio dashboard
            app.open_studio("dashboard")
            app.update(); time.sleep(0.3)
            save("ui_studio_1.0.0.png", "shot2.jpg")
            # bot accounts — turn rocket on for all, wait so the counter moves
            ch = app.lib.current_channel()
            if ch:
                app.lib.set_boost_all(ch["id"], True, "rocket")
            app.open_studio("bots")
            app.update()
            time.sleep(2.5)
            app.lib.apply_boosts()
            app.open_studio("bots")
            app.update(); time.sleep(0.3)
            save("ui_studio_bots_1.0.0.png")
            # shorts player
            shorts = app.lib.shorts()
            hill = next((s for s in shorts if "sprint" in (s.get("title") or "").lower()), shorts[0] if shorts else None)
            if hill:
                app.open_shorts(hill["id"])
                app.update()
                time.sleep(1.0)
                app.update()
                save("ui_shorts_1.0.0.png")
                app.player_pause()
            # studio upload tab (empty pick UI)
            app.open_studio("upload")
            app.update(); time.sleep(0.3)
            save("ui_studio_upload_1.0.0.png")
            open(os.path.join(shots, "shot_ok_1.0.0.txt"), "w", encoding="utf-8").write(
                "ok %s\n%s\n" % (APP_VERSION, "\n".join(log)))
        except Exception as e:
            open(os.path.join(shots, "shot_fail.txt"), "w", encoding="utf-8").write(repr(e))
            raise
        finally:
            app.destroy()

    app.after(1800, go)
    app.mainloop()


def _tiny_clip(path, vertical=False, seconds=3):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    size = "720x1280" if vertical else "1280x720"
    cmd = [
        ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=0x1A3A4C:s=%s:d=%s:r=24" % (size, seconds),
        "-f", "lavfi", "-i", "sine=frequency=440:duration=%s" % seconds,
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-c:a", "aac", "-b:a", "64k", "-shortest", path,
    ]
    run_hidden(cmd, timeout=30)
    return os.path.isfile(path) and os.path.getsize(path) > 1000


def run_smoke(out_dir=None):
    out_dir = out_dir or os.path.join(tempfile.gettempdir(), "not_tube_smoke")
    os.makedirs(out_dir, exist_ok=True)
    lines = []
    # fresh library in a throwaway? we use real APPDATA — seed after smoke? 
    # Use a tiny import on a disposable channel then leave seed to the user/shots.
    # For smoke we create clips, launch app, import via API, play, search.
    lib = Library()
    ch = lib.current_channel()
    if not ch:
        ch = lib.add_channel("Smoke Channel", "@smoke", "smoke", owned=True)
        lib.switch_channel(ch["id"])
    long_p = os.path.join(out_dir, "smoke_long.mp4")
    short_p = os.path.join(out_dir, "smoke_short.mp4")
    ok_l = _tiny_clip(long_p, False, 4)
    ok_s = _tiny_clip(short_p, True, 4)
    lines.append("clips long=%s short=%s" % (ok_l, ok_s))
    v = lib.import_video(long_p, "Smoke long clip", "a horizontal test", ch["id"], is_short=False)
    s = lib.import_video(short_p, "Smoke short clip", "a vertical test", ch["id"], is_short=True)
    lines.append("imported long=%s short=%s is_short=%s" % (v["id"], s["id"], s.get("is_short")))
    lines.append("looks_like_short long=%s short=%s" % (looks_like_short(long_p), looks_like_short(short_p)))

    app = App()
    app.geometry("1100x720+20+20")
    report = {"frames": 0, "changed": False, "search": False, "boost": False}

    def go():
        try:
            app.open_watch(v["id"])
            app.update()
            time.sleep(0.8)
            app.update()
            f1 = app.player_frame.copy() if app.player_frame else None
            time.sleep(0.7)
            app.update()
            f2 = app.player_frame.copy() if app.player_frame else None
            changed = False
            if f1 is not None and f2 is not None:
                # simple difference
                a = list(f1.resize((32, 18)).getdata())
                b = list(f2.resize((32, 18)).getdata())
                changed = a != b
            report["changed"] = changed
            report["frames"] = 1 if f2 is not None else 0
            app.player_pause()
            # search
            app.search_var.set("Smoke long")
            hits = app.lib.search("Smoke long")
            report["search"] = any(h["id"] == v["id"] for h in hits)
            # shorts
            app.open_shorts(s["id"])
            app.update()
            time.sleep(0.5)
            # boost catch-up
            app.lib.set_boost_video(v["id"], True, "rocket")
            vv = app.lib.get_video(v["id"])
            vv["boost"]["last_tick"] = time.time() - 20
            app.lib.save()
            before = int(vv.get("views") or 0)
            added = app.lib.apply_boosts()
            after = int(app.lib.get_video(v["id"]).get("views") or 0)
            report["boost"] = after > before and added.get("views", 0) > 0
            lines.append("play frames=%s changed=%s" % (report["frames"], report["changed"]))
            lines.append("search=%s" % report["search"])
            lines.append("boost views %s -> %s added=%s" % (before, after, added))
            lines.append("shorts page=%s" % (app.page == "shorts"))
            ok = report["frames"] and report["changed"] and report["search"] and report["boost"] and s.get("is_short")
            lines.append("SMOKE " + ("PASS" if ok else "FAIL"))
            with open(os.path.join(out_dir, "smoke.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("\n".join(lines))
        except Exception as e:
            lines.append("EXC %r" % e)
            with open(os.path.join(out_dir, "smoke.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            print("\n".join(lines))
        finally:
            app.destroy()

    app.after(1600, go)
    app.mainloop()
    return os.path.join(out_dir, "smoke.txt")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--seed":
        seed_library(reset=True)
        print("seeded", library_path())
        return
    if args and args[0] == "--shot":
        run_shots()
        return
    if args and args[0] == "--smoke":
        dest = args[1] if len(args) > 1 else None
        run_smoke(dest)
        return
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
