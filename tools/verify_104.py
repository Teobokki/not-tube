# -*- coding: utf-8 -*-
import os, sys, time, traceback, tempfile, shutil
os.environ["APPDATA"] = r"Z:\tmp\nttest104"
os.makedirs(r"Z:\tmp\nttest104", exist_ok=True)
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

def flush():
    open(os.path.join(SHOTS, "verify_104.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

log("APP_VERSION=%s" % nt.APP_VERSION)
log("samples=%s" % nt.samples_dir())

# owner detection
os.environ["USERNAME"] = "SomeoneElse"
# may still be true if another name is kimi — log all
log("is_owner_pc with SomeoneElse USERNAME=%s" % nt.is_owner_pc())
os.environ["USERNAME"] = "Kimi"
log("is_owner_pc with Kimi=%s" % nt.is_owner_pc())
os.environ["USERNAME"] = "kimi"
log("is_owner_pc with kimi=%s" % nt.is_owner_pc())

missing = [s["file"] for s in nt.FEATURED_VIDEOS if not os.path.isfile(os.path.join(nt.samples_dir(), s["file"]))]
log("missing clips=%s count_specs=%d" % (missing, len(nt.FEATURED_VIDEOS)))

nt.seed_library(reset=True)
lib = nt.Library()
feat = lib.featured_channels()
hauls = lib.haul_videos()
titles = [v.get("title") for v in hauls]
log("channels=%d featured=%d hauls=%d videos=%d titles=%s" % (
    len(lib.channels()), len(feat), len(hauls), len(lib.videos()), titles))
old_left = [t for t in titles if "trench" in t.lower() or "weekend knit" in t.lower() or "utility jacket and jeans" in t.lower() or "floral midi" in t.lower()]
log("old titles left (should be empty)=%s" % old_left)
owned_feat = [c.get("name") for c in feat if c.get("owned")]
log("owned featured=%s" % owned_feat)

# idempotent
nt.ensure_bundled_content(lib)
lib2 = nt.Library()
log("re-ensure hauls=%d videos=%d" % (len(lib2.haul_videos()), len(lib2.videos())))

# owner-added video must survive re-ensure
ch = lib2.featured_channels()[0]
# tiny clip via existing sample if needed — use a classic sample if present else a haul file as a fake user upload
src = os.path.join(nt.samples_dir(), "tomato-pasta.mp4")
if not os.path.isfile(src):
    src = os.path.join(nt.samples_dir(), nt.FEATURED_VIDEOS[0]["file"])
ov = lib2.import_video(src, "Owner upload keep me", "owner test", ch["id"], owner_added=True)
log("owner added id=%s seed_file=%s" % (ov["id"], ov.get("seed_file")))
nt.ensure_bundled_content(lib2)
lib3 = nt.Library()
kept = lib3.get_video(ov["id"])
log("owner upload survived=%s title=%s" % (bool(kept), (kept or {}).get("title")))
log("hauls after owner ensure=%d videos=%d" % (len(lib3.haul_videos()), len(lib3.videos())))

# may_manage: featured seed should not be manageable even for... that's app-level. Check flags.
seed_v = next(v for v in lib3.haul_videos() if not v.get("owner_added"))
log("seed has seed_id=%s owner_added=%s" % (seed_v.get("seed_id"), seed_v.get("owner_added")))

ok_art = True
for c in feat:
    cvs = [v for v in lib3.haul_videos() if v.get("channel_id") == c["id"]]
    av, bn = c.get("avatar") or "", c.get("banner") or ""
    # reload channel from lib3
    c3 = lib3.get_channel(c["id"]) or c
    av, bn = c3.get("avatar") or "", c3.get("banner") or ""
    log("ch %s vids=%d av=%s bn=%s" % (c3.get("name"), len(cvs), os.path.isfile(av), os.path.isfile(bn)))
    if len(cvs) < 3 or not os.path.isfile(av) or not os.path.isfile(bn):
        ok_art = False

logic_ok = (
    nt.APP_VERSION == "1.0.4"
    and len(feat) == 4
    and len(hauls) == 12
    and not old_left
    and not owned_feat
    and not missing
    and len(lib2.haul_videos()) == 12
    and kept is not None
    and kept.get("title") == "Owner upload keep me"
    and ok_art
    and nt.is_owner_pc()  # USERNAME still kimi
)
log("LOGIC " + ("PASS" if logic_ok else "FAIL"))
flush()

# Keep USERNAME=Kimi so Owner tools tab appears in shots
os.environ["USERNAME"] = "Kimi"
app = nt.App()
app.geometry("1280x720+30+20")
app.sidebar_open = True

def grab(name, store=None):
    app.update_idletasks(); app.update()
    time.sleep(0.5); app.update()
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path = os.path.join(SHOTS, name)
    im.save(path)
    log("shot %s %s" % (name, im.size))
    if store:
        im.convert("RGB").resize((1500, 940), resample=3).save(os.path.join(STORE, store), "JPEG", quality=90)
    return im

def go():
    try:
        app.show_page("home")
        app.sidebar_open = True
        app._build_sidebar()
        app.update(); time.sleep(0.4)
        grab("ui_home_1.0.4.png", "shot0.jpg")

        hauls = app.lib.haul_videos()
        date = next((v for v in hauls if "date night satin" in (v.get("title") or "").lower()), hauls[0])
        app.open_watch(date["id"])
        app.update(); time.sleep(1.1); app.update()
        f1 = app.player_frame.copy() if app.player_frame else None
        time.sleep(0.8); app.update()
        f2 = app.player_frame.copy() if app.player_frame else None
        changed = bool(f1 and f2 and list(f1.resize((24, 14)).getdata()) != list(f2.resize((24, 14)).getdata()))
        log("play frames=%s changed=%s playing=%s title=%s" % (f2 is not None, changed, app.player_playing, date.get("title")))
        grab("ui_watch_haul_1.0.4.png", "shot1.jpg")
        app.player_pause()

        ch = app.lib.get_channel_by_name("Mira Vale Fits")
        app.open_channel(ch["id"])
        app.update(); time.sleep(0.4)
        grab("ui_channel_1.0.4.png", "shot2.jpg")

        app.open_studio("owner")
        app.update(); time.sleep(0.4)
        log("studio tab=%s page=%s owner_pc=%s" % (app.studio_tab, app.page, nt.is_owner_pc()))
        grab("ui_studio_owner_1.0.4.png")

        ok = logic_ok and (f2 is not None and changed) and app.studio_tab == "owner"
        log("VERIFY " + ("PASS" if ok else "FAIL"))
        flush()
    except Exception as e:
        log("EXC %r\n%s" % (e, traceback.format_exc()))
        flush()
    finally:
        try:
            app.destroy()
        except Exception:
            pass

app.after(2000, go)
app.mainloop()
