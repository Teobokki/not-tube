# -*- coding: utf-8 -*-
import os, sys, time, traceback
os.environ["APPDATA"] = r"Z:\tmp\nttest103"
os.makedirs(r"Z:\tmp\nttest103", exist_ok=True)
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

def flush_log(name="verify_103.txt"):
    open(os.path.join(SHOTS, name), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

# --- library / seed ---
log("APPDATA=%s" % os.environ.get("APPDATA"))
log("APP_VERSION=%s" % nt.APP_VERSION)
log("samples_dir=%s" % nt.samples_dir())
log("channel_art_dir=%s" % nt.channel_art_dir())

missing = []
for spec in nt.FEATURED_VIDEOS:
    p = os.path.join(nt.samples_dir(), spec["file"])
    if not os.path.isfile(p):
        missing.append(p)
    else:
        log("clip %s %d" % (spec["file"], os.path.getsize(p)))
if missing:
    log("MISSING CLIPS %s" % missing)

nt.seed_library(reset=True)
lib = nt.Library()
feat = lib.featured_channels()
hauls = lib.haul_videos()
names = [c.get("name") for c in feat]
log("channels=%d featured=%d hauls=%d videos=%d shorts=%d names=%s" % (
    len(lib.channels()), len(feat), len(hauls), len(lib.videos()), len(lib.shorts()), names))
owned_feat = [c.get("name") for c in feat if c.get("owned")]
log("owned featured (should be empty)=%s" % owned_feat)

# idempotent ensure
nt.ensure_bundled_content(lib)
lib2 = nt.Library()
log("after re-ensure featured=%d hauls=%d videos=%d" % (
    len(lib2.featured_channels()), len(lib2.haul_videos()), len(lib2.videos())))

# each featured channel has 2 haul videos, art, handle
ok_art = True
for c in feat:
    cvs = [v for v in hauls if v.get("channel_id") == c["id"]]
    av = c.get("avatar") or ""
    bn = c.get("banner") or ""
    log("ch %s handle=%s vids=%d avatar=%s banner=%s subs=%s" % (
        c.get("name"), c.get("handle"), len(cvs), os.path.isfile(av), os.path.isfile(bn), c.get("subscribers")))
    if len(cvs) < 2 or not os.path.isfile(av) or not os.path.isfile(bn):
        ok_art = False
        log("ART/VID FAIL %s" % c.get("name"))

# boost a haul
v0 = hauls[0]
before = int(v0.get("views") or 0)
v0.setdefault("boost", {})["last_tick"] = time.time() - 15
lib.save()
added = lib.apply_boosts()
after = int(lib.get_video(v0["id"]).get("views") or 0)
botv = int(lib.get_video(v0["id"]).get("bot_views") or 0)
log("boost %s %s->%s bot_views=%s added=%s" % (v0.get("title"), before, after, botv, added))

# logic ok so far
logic_ok = (
    nt.APP_VERSION == "1.0.3"
    and len(feat) == 4
    and len(hauls) == 8
    and not owned_feat
    and ok_art
    and after > before
    and botv > 0
    and not missing
    and len(lib2.haul_videos()) == 8
)
log("LOGIC " + ("PASS" if logic_ok else "FAIL"))
flush_log()

# --- GUI shots + playback ---
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
        # store art is 1500x940 for catalog shots historically? previous used 1280x720 then catalog hashes.
        # We'll also write a 1500x940 later. Keep 1280x720 jpeg here plus a 1500x940.
        rgb = im.convert("RGB")
        rgb.resize((1280, 720)).save(os.path.join(STORE, store), "JPEG", quality=88)
        rgb.resize((1500, 940)).save(os.path.join(STORE, store.replace(".jpg", "_1500.jpg")), "JPEG", quality=88)
    return im

def go():
    try:
        app.show_page("home")
        app.sidebar_open = True
        app._build_sidebar()
        app.update()
        time.sleep(0.4)
        grab("ui_home_1.0.3.png", "shot0.jpg")

        # Try-on hauls chip
        app._set_chip("Try-on hauls")
        app.update(); time.sleep(0.3)
        grab("ui_hauls_1.0.3.png")

        # watch a haul
        hauls = app.lib.haul_videos()
        trench = next((v for v in hauls if "trench" in (v.get("title") or "").lower()), hauls[0])
        app.open_watch(trench["id"])
        app.update()
        time.sleep(1.1)
        app.update()
        f1 = app.player_frame.copy() if app.player_frame else None
        time.sleep(0.8)
        app.update()
        f2 = app.player_frame.copy() if app.player_frame else None
        changed = bool(f1 and f2 and list(f1.resize((24, 14)).getdata()) != list(f2.resize((24, 14)).getdata()))
        log("play frames=%s changed=%s playing=%s title=%s" % (f2 is not None, changed, app.player_playing, trench.get("title")))
        grab("ui_watch_haul_1.0.3.png", "shot1.jpg")
        app.player_pause()

        # featured channel page
        ch = app.lib.get_channel_by_name("Mira Vale Fits")
        app.open_channel(ch["id"])
        app.update(); time.sleep(0.4)
        grab("ui_channel_1.0.3.png", "shot2.jpg")

        # about text still HYPERION SYSTEMS
        # (visual only)

        ok = logic_ok and (f2 is not None and changed)
        log("VERIFY " + ("PASS" if ok else "FAIL"))
        flush_log()
    except Exception as e:
        log("EXC %r\n%s" % (e, traceback.format_exc()))
        flush_log()
    finally:
        try:
            app.destroy()
        except Exception:
            pass

app.after(2000, go)
app.mainloop()
