# -*- coding: utf-8 -*-
"""Not AI screenshots / checks for NOT TUBE 1.0.9 (run under Wine)."""
import os, sys, time, shutil
AD = r"Z:\tmp\notai_test\appdata"
if os.path.isdir(AD):
    shutil.rmtree(AD)
os.makedirs(AD, exist_ok=True)
os.environ["APPDATA"] = AD
sys.path.insert(0, r"Z:\workspace\not-tube"); os.chdir(r"Z:\workspace\not-tube")
import not_tube as nt
from PIL import ImageGrab
OUT = r"Z:\workspace\not-tube\shots\notai_109"
os.makedirs(OUT, exist_ok=True)
LOG = []
def log(s):
    print(s, flush=True); LOG.append(str(s))
nt.seed_library(reset=True)
lib = nt.Library()
atlas = lib.get_channel_by_name("Atlas Walks")
reel = lib.import_video(r"Z:\tmp\notai_test\walk_reel.mp4",
    "Evening Walks: Streets, Rain, Coast, Lake and Night Market",
    "Five short walks stitched into one evening reel. We start on autumn streets, then city lights in the rain. "
    "The coastal trail in spring is the quietest part. Sunrise over a glass-still lake follows. "
    "It ends at a busy night market with street food.",
    atlas["id"], uploaded="2026-11-12T10:00:00", views=812, tags=["walk", "calm", "city", "nature"])
log("reel=%s dur=%s" % (reel["id"], reel["duration"]))
app = nt.App()
app.geometry("1600x1000+20+20")
try: app.attributes("-topmost", True)
except Exception: pass
def pump(t=0.4):
    end = time.time() + t
    while time.time() < end:
        app.update(); time.sleep(0.02)
def grab(name):
    pump(0.7)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h)); p = os.path.join(OUT, name + ".png")
    im.save(p); log("shot %s" % p)
    return im
def clear_chat():
    for w in app._ai_scroll.inner.winfo_children():
        w.destroy()
    app._ai_photos = []
pump(1.5)
grab("00_home_button")
# 1) summary on a video page
app.open_watch(reel["id"]); pump(1.2)
app.ai_toggle(True); pump(0.6)
clear_chat()
t0 = time.time()
app.ai_ask("Summarize this video with key moments")
while getattr(app, "_ai_pending", None) is not None and time.time() - t0 < 120:
    pump(0.2)
log("summary took %.1fs" % (time.time() - t0))
import json
sj = json.load(open(os.path.join(AD, "NOT TUBE", "notai", reel["id"], "summary.json"), encoding="utf-8"))
log("source=%s chapters=%s" % (sj["source"], [(c["t"], c["label"], c["look"]) for c in sj["chapters"]]))
log("takeaways=%s" % sj["takeaways"])
pump(0.6)
app.player_pause(); pump(0.3)
grab("01_summary_key_moments")
app.ai_seek(reel["id"], sj["chapters"][2]["t"]); pump(1.0)
log("after clicking moment %s player_t=%.2f page=%s" % (sj["chapters"][2]["t"], app.player_t, app.page))
app.player_pause(); pump(0.4)
grab("01b_after_seek")
# 2) conversational search
clear_chat()
app.show_page("home"); pump(0.8)
app.ai_ask("find leather jacket hauls under 1 minute"); pump(1.0)
grab("02_conversational_search")
clear_chat()
app.ai_ask("newest from Atlas Walks"); pump(1.0)
grab("02b_search_creator")
# 4) discovery
clear_chat()
app.lib.data["history"] = [{"id": v["id"]} for v in app.lib.haul_videos()[:3]]
app.ai_ask("I feel like something calm I haven't seen"); pump(1.0)
grab("03_transparent_discovery")
# 3) title & tag helper
clear_chat()
app.open_studio("upload"); pump(1.0)
rec_path = r"Z:\tmp\notai_test\VID_20261112_184512_tomato_pasta_FINAL_v2_1080p.mp4"
app._add_upload_row(rec_path); pump(0.6)
rec = app._upload_rows[-1]
rec["desc"].insert("1.0", "Quick weeknight tomato pasta with garlic and basil. Ready in 15 minutes.")
app.ai_helper_for_upload(rec); pump(1.0)
grab("04_title_tag_helper")
log("title field before Use=%r" % rec["title"].get())
# press first "Use" + "Use these tags"
fr = app._ai_scroll.inner.winfo_children()[-1]
def find_pills(w, out):
    for k in w.winfo_children():
        if isinstance(k, nt.Pill): out.append(k)
        find_pills(k, out)
    return out
pills = find_pills(fr, [])
log("pills=%s" % [p.cget("text") for p in pills])
pills[1]._click(); pills[-1]._click(); pump(0.6)
log("title after Use=%r tags=%r" % (rec["title"].get(), rec["tags"].get()))
grab("04b_helper_applied")
# about + settings default
clear_chat()
app.show_page("home"); pump(0.6)
app.ai_ask("How do you work?"); pump(0.8)
grab("05_how_it_works")
log("cfg default=%s" % app.ai_cfg())
# search bar still OK (1.0.8)
app.search_var.set("try on haul"); app.do_search(); pump(0.8)
log("search bar page=%s results=%d" % (app.page, len(app._filtered_home())))
app.ai_toggle(False); pump(0.5)
grab("06_search_bar_panel_closed")
open(os.path.join(OUT, "log.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
try: app._player_kill()
except Exception: pass
app.destroy()
os._exit(0)
