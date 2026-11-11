# -*- coding: utf-8 -*-
"""Quick 1.0.6 check: Kim videos shelf first on Home, then hauls, then featured."""
import os, sys, time, shutil

os.environ["APPDATA"] = r"Z:\tmp\nttest106"
if os.path.isdir(r"Z:\tmp\nttest106"):
    shutil.rmtree(r"Z:\tmp\nttest106")
os.makedirs(r"Z:\tmp\nttest106", exist_ok=True)
sys.path.insert(0, r"Z:\workspace\not-tube")
os.chdir(r"Z:\workspace\not-tube")
os.environ["USERNAME"] = "Kimi"

import not_tube as nt

SHOTS = r"Z:\workspace\not-tube\shots"
os.makedirs(SHOTS, exist_ok=True)
LOG = []

def log(s):
    print(s, flush=True)
    LOG.append(s)

def flush():
    open(os.path.join(SHOTS, "verify_106.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

log("APP_VERSION=%s" % nt.APP_VERSION)

nt.seed_library(reset=True)
lib = nt.Library()
KIM_ID = "ch-1794350964930-0494"
lib.data.setdefault("channels", []).append({
    "id": KIM_ID, "name": "Kim Miyoyazu", "handle": "@kimmiyoyazu",
    "description": "mine", "avatar": "", "banner": "",
    "subscribers": 7, "bot_subscribers": 0, "created": "2026-11-10T12:00:00",
    "owned": True,
})
lib.data["current_channel_id"] = KIM_ID
lib.save()
nt.ensure_bundled_content(lib)
lib = nt.Library()

src = os.path.join(nt.samples_dir(), "autumn-streets.mp4")
if not os.path.isfile(src):
    src = os.path.join(nt.samples_dir(), nt.FEATURED_VIDEOS[0]["file"])
older = lib.import_video(src, "Older kim clip", "", KIM_ID, is_short=False,
                         uploaded="2026-11-01T10:00:00")
newer = lib.import_video(src, "Newest kim clip", "", KIM_ID, is_short=False,
                         uploaded="2026-11-11T16:00:00")
# also a haul on kim — should sit in Kim shelf, not duplicated in hauls
lib.import_video(src, "Kim own haul", "", KIM_ID, is_short=False, category="haul",
                 uploaded="2026-11-10T12:00:00")

ch = lib.kim_miyoyazu_channel()
longs = list(lib.long_videos(ch["id"]))
longs.sort(key=lambda v: v.get("uploaded") or "", reverse=True)
titles = [v.get("title") for v in longs]
log("kim channel=%s featured=%s owned=%s titles=%s" % (
    (ch or {}).get("id"), bool(ch and ch.get("featured")), bool(ch and ch.get("owned")), titles))
feat = [c.get("name") for c in lib.featured_channels()]
log("featured order=%s" % feat)
order_ok = titles[:2] == ["Newest kim clip", "Kim own haul"] and feat[:1] == ["Kim Miyoyazu"]
log("LOGIC " + ("PASS" if nt.APP_VERSION == "1.0.6" and order_ok and ch else "FAIL"))
flush()

app = nt.App()
app.geometry("1280x720+30+20")
app.sidebar_open = True
app.lib.switch_channel(KIM_ID)

def heading_order(widget):
    found = []
    def walk(w):
        try:
            kids = list(w.winfo_children())
        except Exception:
            return
        for k in kids:
            try:
                if k.winfo_class() == "Label":
                    t = k.cget("text") or ""
                    if t in ("Kim Miyoyazu", "Try-on hauls", "Featured channels", "NOT SHORTS"):
                        if t not in found:
                            found.append(t)
            except Exception:
                pass
            walk(k)
    walk(widget)
    return found

def grab(name):
    app.update_idletasks(); app.update()
    time.sleep(0.45); app.update()
    from PIL import ImageGrab
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(SHOTS, name)
    im.save(path)
    log("shot %s %s" % (name, im.size))
    return path

def go():
    try:
        app.chip = "All"
        app.show_page("home")
        path = grab("ui_home_1.0.6.png")
        order = heading_order(app.content)
        log("home headings=%s" % order)
        want = ["Kim Miyoyazu", "Try-on hauls", "Featured channels"]
        # NOT SHORTS may appear after featured
        ui_ok = order[:3] == want
        log("VERIFY " + ("PASS" if ui_ok and order_ok and nt.APP_VERSION == "1.0.6" else "FAIL"))
        log("shot_path=%s" % path)
        flush()
    except Exception:
        import traceback
        log(traceback.format_exc())
        log("VERIFY FAIL")
        flush()
    finally:
        try:
            app.destroy()
        except Exception:
            pass

app.after(400, go)
app.mainloop()
flush()
sys.exit(0 if "VERIFY PASS" in "\n".join(LOG) else 1)
