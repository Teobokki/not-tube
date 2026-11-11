# -*- coding: utf-8 -*-
"""Store-page screenshots for NOT TUBE 1.0.7."""
import os, sys, time, shutil

os.environ["APPDATA"] = r"Z:\tmp\ntshots107\appdata"
if os.path.isdir(r"Z:\tmp\ntshots107\appdata"):
    shutil.rmtree(r"Z:\tmp\ntshots107\appdata")
os.makedirs(r"Z:\tmp\ntshots107\appdata", exist_ok=True)
sys.path.insert(0, r"Z:\workspace\not-tube")
os.chdir(r"Z:\workspace\not-tube")
os.environ["USERNAME"] = "Kimi"

import not_tube as nt
from PIL import ImageGrab

SHOTS = r"Z:\workspace\not-tube\shots"
STORE = r"Z:\workspace\not-tube\store_art"
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(STORE, exist_ok=True)
LOG = []

def log(s):
    print(s, flush=True)
    LOG.append(s)

def flush():
    open(os.path.join(SHOTS, "shots_106_store.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

lib = nt.Library()
lib.data = lib._empty()
lib.save()
KIM_ID = "ch-1794350964930-0494"
av_src = r"Z:\tmp\ntshots107\kim_avatar.png"
lib.data.setdefault("channels", []).append({
    "id": KIM_ID, "name": "Kim Miyoyazu", "handle": "@kimmiyoyazu",
    "description": "Videos from Kim Miyoyazu.", "avatar": "", "banner": "",
    "subscribers": 3851, "bot_subscribers": 0, "created": "2026-11-10T12:00:00",
    "owned": True,
})
lib.data["current_channel_id"] = KIM_ID
lib.save()
if os.path.isfile(av_src):
    copied = lib.copy_image_asset(av_src, "avatars", KIM_ID) or ""
    if copied:
        lib.update_channel(KIM_ID, avatar=copied)
nt.ensure_bundled_content(lib)
lib = nt.Library()
lib.switch_channel(KIM_ID)

# The owner's real Kim Miyoyazu uploads (read-only copies), real frames only.
REAL = [
    (r"Z:\workspace\nt107\pc\videos\v-1794352205142-0679.mp4", "Ex Network Fixes Your Download Issues Try Today At No Cost!", "2026-11-10T23:10:05"),
    (r"Z:\workspace\nt107\pc\videos\v-1794351020980-0903.mp4", "\u0411\u0435\u0437 \u0426\u0435\u043d\u0437\u0443\u0440\u0438 No Censorship 2026", "2026-11-10T22:50:21"),
]
for p, t, up in REAL:
    lib.import_video(p, t, "", KIM_ID, is_short=False, uploaded=up, views=2003)
log("kim videos=%s av=%s" % ([v.get("title") for v in lib.long_videos(KIM_ID)], bool((lib.get_channel(KIM_ID) or {}).get("avatar"))))

app = nt.App()
app.geometry("1600x1080+40+50")
app.sidebar_open = True
try:
    app.attributes("-topmost", True)
except Exception:
    pass
app.lib.switch_channel(KIM_ID)

def save_store(im, name):
    rgb = im.convert("RGB")
    raw = os.path.join(SHOTS, name.replace(".jpg", ".png")) if name.endswith(".jpg") else os.path.join(SHOTS, name)
    if name.endswith(".jpg"):
        rgb.save(os.path.join(SHOTS, name.replace(".jpg", "_raw.png")))
    else:
        rgb.save(raw)
    out = rgb.resize((1500, 940), resample=3)
    path = os.path.join(STORE, name if name.endswith(".jpg") else name.replace(".png", ".jpg"))
    # if name already shotN.jpg
    if not name.startswith("shot") and name.endswith(".png"):
        path = os.path.join(SHOTS, name)
        rgb.save(path)
        return path
    out.save(os.path.join(STORE, name), "JPEG", quality=90)
    log("store %s %s" % (name, out.size))
    return os.path.join(STORE, name)

def grab_raw(png_name):
    app.update_idletasks(); app.update()
    time.sleep(0.55); app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(SHOTS, png_name)
    im.save(path)
    log("shot %s %s" % (png_name, im.size))
    return im, path

def scroll_to_label(text):
    host = getattr(app, "_grid_host", None)
    if not host:
        return False
    def find(w):
        try:
            if w.winfo_class() == "Label" and (w.cget("text") or "") == text:
                return w
        except Exception:
            pass
        try:
            for k in w.winfo_children():
                r = find(k)
                if r:
                    return r
        except Exception:
            pass
        return None
    lab = find(host.inner)
    if not lab:
        return False
    app.update(); host.update()
    try:
        y = lab.winfo_rooty() - host.inner.winfo_rooty() - 8
        h = max(1, host.inner.winfo_height())
        host.canvas.yview_moveto(max(0.0, min(1.0, y / h)))
        app.update()
        return True
    except Exception as e:
        log("scroll fail %s" % e)
        return False

def go():
    try:
        app.chip = "All"
        app.show_page("home")
        im, p = grab_raw("ui_home_store_1.0.7.png")
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, "shot0.jpg"), "JPEG", quality=90)
        log("store shot0.jpg")

        scrolled = scroll_to_label("Featured channels")
        log("scrolled featured=%s" % scrolled)
        im, p = grab_raw("ui_featured_store_1.0.7.png")
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, "shot1.jpg"), "JPEG", quality=90)
        log("store shot1.jpg")

        kim_vids = [v for v in app.lib.long_videos(KIM_ID)]
        kim_vids.sort(key=lambda v: v.get("uploaded") or "", reverse=True)
        vid = kim_vids[0]["id"] if kim_vids else app.lib.videos()[0]["id"]
        app.show_page("watch", video_id=vid)
        app.watch_id = vid
        # reopen to be sure
        try:
            app.show_page("watch")
        except Exception:
            pass
        # App uses watch_id
        app.watch_id = vid
        app.show_page("watch")
        im, p = grab_raw("ui_watch_store_1.0.7.png")
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, "shot2.jpg"), "JPEG", quality=90)
        log("store shot2.jpg")

        app.open_channel(KIM_ID)
        im, p = grab_raw("ui_channel_store_1.0.7.png")
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, "shot3.jpg"), "JPEG", quality=90)
        log("store shot3.jpg")

        app.open_studio("content")
        im, p = grab_raw("ui_studio_store_1.0.7.png")
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, "shot4.jpg"), "JPEG", quality=90)
        log("store shot4.jpg")

        log("SHOTS DONE")
        flush()
    except Exception:
        import traceback
        log(traceback.format_exc())
        log("SHOTS FAIL")
        flush()
    finally:
        try:
            app.destroy()
        except Exception:
            pass

app.after(500, go)
app.mainloop()
flush()
sys.exit(0 if "SHOTS DONE" in "\n".join(LOG) else 1)
