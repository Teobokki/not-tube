# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, r"Z:\workspace\not-tube")
os.chdir(r"Z:\workspace\not-tube")
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

log("seeding...")
nt.seed_library(reset=True)
log("seeded videos=%d shorts=%d channels=%d" % (
    len(nt.Library().videos()), len(nt.Library().shorts()), len(nt.Library().channels())))

app = nt.App()
app.geometry("1280x720+30+20")
app.sidebar_open = True

def grab(name, store=None):
    app.update_idletasks(); app.update()
    time.sleep(0.45); app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(SHOTS, name)
    im.save(path)
    log("shot %s %s" % (name, im.size))
    if store:
        im.convert("RGB").resize((1280, 720)).save(os.path.join(STORE, store), "JPEG", quality=88)
    return im

def go():
    try:
        app.show_page("home")
        app.sidebar_open = True
        app._build_sidebar()
        app.update()
        grab("ui_home_1.0.0.png", "shot0.jpg")

        vids = app.lib.long_videos()
        radio = next((v for v in vids if "radio" in (v.get("title") or "").lower()), vids[0])
        app.open_watch(radio["id"])
        app.update()
        time.sleep(1.0)
        app.update()
        f1 = app.player_frame.copy() if app.player_frame else None
        time.sleep(0.7)
        app.update()
        f2 = app.player_frame.copy() if app.player_frame else None
        changed = bool(f1 and f2 and list(f1.resize((24, 14)).getdata()) != list(f2.resize((24, 14)).getdata()))
        log("play frames=%s changed=%s playing=%s" % (f2 is not None, changed, app.player_playing))
        grab("ui_watch_1.0.0.png", "shot1.jpg")
        app.player_pause()

        # Studio + bots
        ch = app.lib.current_channel()
        if ch:
            app.lib.set_boost_all(ch["id"], True, "rocket")
        app.open_studio("dashboard")
        app.update()
        time.sleep(0.3)
        grab("ui_studio_1.0.0.png", "shot2.jpg")

        # quick shorts + upload path
        shorts = app.lib.shorts()
        log("shorts=%d" % len(shorts))
        if shorts:
            app.open_shorts(shorts[0]["id"])
            app.update()
            time.sleep(0.6)
            log("shorts page=%s playing=%s frame=%s" % (app.page, app.player_playing, app.player_frame is not None))
            app.player_pause()

        # upload API path (same as Publish)
        src = r"Z:\workspace\not-tube\samples\tomato-pasta.mp4"
        ch = app.lib.current_channel()
        before = len(app.lib.videos())
        if os.path.isfile(src) and ch:
            nv = app.lib.import_video(src, "Upload check pasta", "verify upload", ch["id"], is_short=False)
            log("upload ok id=%s count %d->%d" % (nv["id"], before, len(app.lib.videos())))

        hits = app.lib.search("radio waves")
        log("search hits=%d" % len(hits))

        # bot catch-up
        v = app.lib.get_video(radio["id"])
        before_v = int(v.get("views") or 0)
        app.lib.set_boost_video(radio["id"], True, "rocket")
        v = app.lib.get_video(radio["id"])
        v["boost"]["last_tick"] = time.time() - 15
        app.lib.save()
        added = app.lib.apply_boosts()
        after_v = int(app.lib.get_video(radio["id"]).get("views") or 0)
        log("bots views %s->%s added=%s" % (before_v, after_v, added))

        # studio bots page exists
        app.open_studio("bots")
        app.update()
        log("studio tab=%s page=%s" % (app.studio_tab, app.page))

        ok = (f2 is not None and changed and len(hits) > 0 and after_v > before_v
              and len(shorts) >= 1 and app.page == "studio")
        log("VERIFY " + ("PASS" if ok else "FAIL"))
        open(os.path.join(SHOTS, "verify.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    except Exception as e:
        import traceback
        log("EXC %r\n%s" % (e, traceback.format_exc()))
        open(os.path.join(SHOTS, "verify.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

app.after(2000, go)
app.mainloop()
