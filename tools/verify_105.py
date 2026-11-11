# -*- coding: utf-8 -*-
"""NOT TUBE 1.0.5: Kim Miyoyazu featured, still a fully owned Studio channel."""
import os, sys, time, shutil, tempfile, json

os.environ["APPDATA"] = r"Z:\tmp\nttest105"
if os.path.isdir(r"Z:\tmp\nttest105"):
    shutil.rmtree(r"Z:\tmp\nttest105")
os.makedirs(r"Z:\tmp\nttest105", exist_ok=True)
sys.path.insert(0, r"Z:\workspace\not-tube")
os.chdir(r"Z:\workspace\not-tube")

import not_tube as nt

SHOTS = r"Z:\workspace\not-tube\shots"
os.makedirs(SHOTS, exist_ok=True)
LOG = []

def log(s):
    print(s, flush=True)
    LOG.append(s)

def flush():
    open(os.path.join(SHOTS, "verify_105.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")

class Probe:
    def __init__(self, lib):
        self.lib = lib
    _may_manage_video = nt.App._may_manage_video

log("APP_VERSION=%s" % nt.APP_VERSION)

# Bundled seeds first (fresh library), then inject the user's existing owned channel
# exactly as it would appear in %APPDATA%\NOT TUBE\library.json (no featured key).
nt.seed_library(reset=True)
lib = nt.Library()

KIM_ID = "ch-1794350964930-0494"
KIM_DESC = "My personal channel — do not overwrite"
# leave avatar empty; migration must not invent one
kim = {
    "id": KIM_ID,
    "name": "Kim Miyoyazu",
    "handle": "@kimmiyoyazu",
    "description": KIM_DESC,
    "avatar": "",
    "banner": "",
    "subscribers": 7,
    "bot_subscribers": 0,
    "created": "2026-11-10T12:00:00",
    "owned": True,
}
lib.data.setdefault("channels", []).append(kim)
lib.data["current_channel_id"] = KIM_ID
lib.save()

src = os.path.join(nt.samples_dir(), "autumn-streets.mp4")
if not os.path.isfile(src):
    src = os.path.join(nt.samples_dir(), nt.FEATURED_VIDEOS[0]["file"])
# Studio Upload path: import_video without owner_added
existing = lib.import_video(src, "Kim studio upload keep me", "from studio", KIM_ID, is_short=False)
# A haul-category user upload must also survive (not treated as bundled seed)
haul = lib.import_video(src, "Kim haul keep me", "haul from studio", KIM_ID,
                       is_short=False, category="haul")
log("pre featured=%s owned=%s desc=%r av=%r videos=%s" % (
    bool(lib.get_channel(KIM_ID).get("featured")),
    bool(lib.get_channel(KIM_ID).get("owned")),
    lib.get_channel(KIM_ID).get("description"),
    lib.get_channel(KIM_ID).get("avatar"),
    [v["id"] for v in lib.channel_videos(KIM_ID)],
))

# Simulate app start / migration twice (idempotent)
nt.ensure_bundled_content(lib)
nt.ensure_bundled_content(lib)
lib = nt.Library()
ch = lib.get_channel(KIM_ID)
feat = lib.featured_channels()
feat_names = [c.get("name") for c in feat]
bundled = [spec["name"] for spec in nt.FEATURED_CHANNELS]
log("featured order=%s" % feat_names)
log("kim featured=%s owned=%s desc=%r av=%r id=%s" % (
    bool(ch and ch.get("featured")), bool(ch and ch.get("owned")),
    (ch or {}).get("description"), (ch or {}).get("avatar"), (ch or {}).get("id")))

kept_existing = lib.get_video(existing["id"])
kept_haul = lib.get_video(haul["id"])
log("studio video survived=%s title=%s" % (bool(kept_existing), (kept_existing or {}).get("title")))
log("haul video survived=%s title=%s" % (bool(kept_haul), (kept_haul or {}).get("title")))

# Studio: still selectable as current channel
lib.switch_channel(KIM_ID)
cur = lib.current_channel()
owned_ids = [c["id"] for c in lib.owned_channels()]
log("switch current=%s in owned_channels=%s" % ((cur or {}).get("id"), KIM_ID in owned_ids))

# Studio Upload path after feature: publish lands on Kim, shows on channel + home
posted = lib.import_video(src, "Post-feature studio upload", "after featured", KIM_ID, is_short=False)
home_ids = [v["id"] for v in lib.videos() if not v.get("is_short")]
ch_ids = [v["id"] for v in lib.channel_videos(KIM_ID)]
log("post-feature upload on channel=%s on home=%s" % (posted["id"] in ch_ids, posted["id"] in home_ids))

probe = Probe(lib)
can_edit_old = probe._may_manage_video(existing["id"])
can_edit_new = probe._may_manage_video(posted["id"])
can_edit_haul = probe._may_manage_video(haul["id"])
log("may_manage existing=%s new=%s haul=%s" % (can_edit_old, can_edit_new, can_edit_haul))

# Edit / delete works for owned featured videos
lib.update_video(existing["id"], title="Kim studio upload edited")
edited = lib.get_video(existing["id"])
log("edit title=%s" % (edited or {}).get("title"))
lib.delete_video(posted["id"])
log("deleted post-feature=%s" % (lib.get_video(posted["id"]) is None))

# Non-owned featured seed is still locked; owner_added on bundled still allowed on owner PC
os.environ["USERNAME"] = "Kimi"
seed_v = next(v for v in lib.haul_videos() if not v.get("owner_added") and not (lib.get_channel(v.get("channel_id")) or {}).get("owned"))
log("bundled seed may_manage (should be False)=%s" % probe._may_manage_video(seed_v["id"]))
# SomeoneElse still cannot manage non-owned featured (is_owner_pc false) — even owner_added
# but owned Kim remains manageable regardless of username
os.environ["USERNAME"] = "SomeoneElse"
# is_owner_pc may still be true if USER/LOGNAME/getpass is kimi — just log
log("is_owner_pc SomeoneElse USERNAME=%s" % nt.is_owner_pc())
log("kim still manageable when USERNAME=SomeoneElse=%s" % probe._may_manage_video(existing["id"]))
os.environ["USERNAME"] = "Kimi"

# Re-ensure must not wipe remaining Kim videos or change desc/avatar
nt.ensure_bundled_content(lib)
lib2 = nt.Library()
ch2 = lib2.get_channel(KIM_ID)
log("re-ensure kim videos=%s desc=%r av=%r featured=%s owned=%s" % (
    [v.get("title") for v in lib2.channel_videos(KIM_ID)],
    ch2.get("description"), ch2.get("avatar"),
    bool(ch2.get("featured")), bool(ch2.get("owned"))))

# Case-insensitive handle match (fresh inject would already be featured; check helper)
log("helper lower handle=%s name=%s" % (
    nt._is_kim_miyoyazu_channel({"handle": "@KimMiyoyazu", "name": "x"}),
    nt._is_kim_miyoyazu_channel({"handle": "", "name": "KIM MIYOYAZU"}),
))

order_ok = feat_names and feat_names[0] == "Kim Miyoyazu" and feat_names[1:5] == bundled
logic_ok = (
    nt.APP_VERSION == "1.0.5"
    and ch is not None
    and ch.get("featured") is True
    and ch.get("owned") is True
    and ch.get("description") == KIM_DESC
    and (ch.get("avatar") or "") == ""
    and kept_existing is not None
    and kept_haul is not None
    and (cur or {}).get("id") == KIM_ID
    and KIM_ID in owned_ids
    and can_edit_old and can_edit_new and can_edit_haul
    and (edited or {}).get("title") == "Kim studio upload edited"
    and lib.get_video(posted["id"]) is None
    and not probe._may_manage_video(seed_v["id"]) if os.environ.get("USERNAME") else True
    and order_ok
    and ch2.get("description") == KIM_DESC
    and any(v.get("title") == "Kim studio upload edited" for v in lib2.channel_videos(KIM_ID))
    and any(v.get("title") == "Kim haul keep me" for v in lib2.channel_videos(KIM_ID))
    and nt._is_kim_miyoyazu_channel({"handle": "@KimMiyoyazu", "name": "x"})
    and nt._is_kim_miyoyazu_channel({"handle": "", "name": "KIM MIYOYAZU"})
)
# Recompute bundled seed manage after USERNAME=Kimi (we set it back)
os.environ["USERNAME"] = "Kimi"
seed_locked = not Probe(lib2)._may_manage_video(seed_v["id"])
logic_ok = bool(logic_ok) and seed_locked and order_ok
log("order_ok=%s seed_locked=%s" % (order_ok, seed_locked))
log("LOGIC " + ("PASS" if logic_ok else "FAIL"))
flush()

# GUI: featured row first + Your channel button + studio content/upload/channel for Kim
os.environ["USERNAME"] = "Kimi"
app = nt.App()
app.geometry("1280x720+30+20")
app.sidebar_open = True
# App() calls ensure_bundled_content on the same APPDATA library
app.lib.switch_channel(KIM_ID)

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
    return im

def go():
    try:
        app.show_page("home")
        grab("ui_home_1.0.5.png")
        names = [c.get("name") for c in app.lib.featured_channels()]
        log("app featured order=%s" % names)
        # featured card for Kim should use Your channel, not NOTSCRIBE
        app.open_channel(KIM_ID)
        grab("ui_channel_kim_1.0.5.png")
        app.open_studio("content")
        grab("ui_studio_content_kim_1.0.5.png")
        app.open_studio("upload")
        grab("ui_studio_upload_kim_1.0.5.png")
        app.open_studio("channel")
        grab("ui_studio_channel_kim_1.0.5.png")
        cur = app.lib.current_channel() or {}
        may = all(app._may_manage_video(v["id"]) for v in app.lib.channel_videos(KIM_ID))
        ui_ok = (cur.get("id") == KIM_ID and names[:1] == ["Kim Miyoyazu"] and may)
        log("ui current=%s may_all=%s" % (cur.get("id"), may))
        log("VERIFY " + ("PASS" if logic_ok and ui_ok else "FAIL"))
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
