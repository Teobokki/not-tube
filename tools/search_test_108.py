# -*- coding: utf-8 -*-
"""Search bar glitch repro / verify for NOT TUBE 1.0.8 (run under Wine)."""
import os, sys, time, shutil
TAG = sys.argv[1]; SRC = sys.argv[2]
AD = r"Z:\tmp\ntsearch_%s\appdata" % TAG
if os.path.isdir(AD):
    shutil.rmtree(AD)
os.makedirs(AD, exist_ok=True)
os.environ["APPDATA"] = AD
sys.path.insert(0, SRC); os.chdir(SRC)
import not_tube as nt
from PIL import ImageGrab
OUT = r"Z:\workspace\not-tube\shots\search_108"
os.makedirs(OUT, exist_ok=True)
LOG = []
def log(s):
    print(s, flush=True); LOG.append(str(s))
nt.seed_library(reset=True)
app = nt.App()
app.geometry("1600x1000+20+20")
app.sidebar_open = True
try: app.attributes("-topmost", True)
except Exception: pass
cnt = {"paint": 0, "pages": 0, "fill": 0}
_p = app._paint_search
def paint(*a, **k):
    cnt["paint"] += 1; return _p(*a, **k)
app._paint_search = paint
_s = app.show_page
def sp(*a, **k):
    cnt["pages"] += 1; return _s(*a, **k)
app.show_page = sp
_f = app._fill_home
def fh(*a, **k):
    cnt["fill"] += 1; return _f(*a, **k)
app._fill_home = fh
def pump(t=0.35):
    end = time.time() + t
    while time.time() < end:
        app.update(); time.sleep(0.02)
def grab(name):
    pump(0.5)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    im = ImageGrab.grab(bbox=(x, y, x + w, y + h)); p = os.path.join(OUT, "%s_%s.png" % (TAG, name))
    im.save(p)
    # top bar crop
    im.crop((0, 0, w, 64)).save(os.path.join(OUT, "%s_%s_bar.png" % (TAG, name)))
    log("shot %s" % p)
def overlap():
    sw = app.search_wrap
    sx, sxe = sw.winfo_rootx(), sw.winfo_rootx() + sw.winfo_width()
    res = []
    for w in app.top.winfo_children():
        if w is sw or not w.winfo_ismapped() or w.winfo_height() < 10: continue
        x0, x1 = w.winfo_rootx(), w.winfo_rootx() + w.winfo_width()
        if x0 < sxe and x1 > sx: res.append((w.winfo_class(), x0, x1))
    return (sx, sxe, res)
def type_text(s):
    app.search_entry.focus_force(); pump(0.1)
    ts = []
    for ch in s:
        t0 = time.time()
        if ch == " ":
            app.search_entry.event_generate("<KeyPress>", keysym="space")
        else:
            app.search_entry.event_generate("<KeyPress>", keysym=ch)
        app.update()
        ts.append(time.time() - t0)
        pump(0.04)
    return ts
pump(1.5)
grab("01_idle")
log("idle bg-entry h=%s font=%s" % (app.search_entry.winfo_height(), app.search_entry.cget("font")))
c0 = dict(cnt)
app.search_entry.focus_force(); pump(0.3)
app.focus_force(); pump(0.2); app.search_entry.focus_force(); pump(0.3)
log("focus x2 -> paints=%d" % (cnt["paint"] - c0["paint"]))
grab("02_focused_empty")
c0 = dict(cnt)
ts = type_text("try on haul")
log("typing 11 keys: paints=%d pages=%d fills=%d max_key_ms=%.1f entry=%r" % (
    cnt["paint"] - c0["paint"], cnt["pages"] - c0["pages"], cnt["fill"] - c0["fill"], max(ts) * 1000, app.search_var.get()))
pump(0.8)
log("after-typing page=%s fills=%d" % (app.page, cnt["fill"] - c0["fill"]))
grab("03_typing")
c0 = dict(cnt)
app.search_entry.event_generate("<Return>"); pump(1.2)
log("enter: page=%s q=%r focus=%s results=%d" % (app.page, getattr(app, "search_q", ""), app.focus_get(), len(app._filtered_home())))
grab("04_results")
c0 = dict(cnt)
for _ in range(3):
    app.search_entry.event_generate("<Return>"); pump(0.15)
pump(0.8)
log("enter x3 same query: pages=%d fills=%d" % (cnt["pages"] - c0["pages"], cnt["fill"] - c0["fill"]))
# multi-word out of order
app.search_var.set("haul try"); app.search_entry.event_generate("<Return>"); pump(1.0)
log("'haul try' results=%d" % len(app._filtered_home()))
grab("05_multiword")
# empty query
app.search_var.set("   "); app.search_entry.event_generate("<Return>"); pump(1.0)
log("empty query: page=%s results=%d" % (app.page, len(app._filtered_home())))
grab("06_empty_query")
# long text
app.search_var.set(""); type_text("a very long search query that keeps going past the end of the box ok")
pump(0.5)
grab("07_long_text")
log("long text xview=%s" % (app.search_entry.xview(),))
# escape while on watch page with search focused
vids = app.lib.videos()
if vids:
    app.open_watch(vids[0]["id"]); pump(1.0)
    app.search_entry.focus_force(); pump(0.2)
    app.search_entry.event_generate("<Escape>"); pump(0.5)
    log("esc in search on watch -> page=%s" % app.page)
    app.show_page("home"); pump(0.5)
# window sizes
app.search_var.set("haul")
for W in (1280, 1100):
    app.geometry("%dx800+20+20" % W); pump(1.0)
    log("W=%d overlap=%s entry_w=%s" % (W, overlap(), app.search_entry.winfo_width()))
    grab("08_w%d" % W)
c0 = dict(cnt)
for W in range(1000, 1400, 20):
    app.geometry("%dx800+20+20" % W); app.update()
pump(0.5)
log("resize sweep 20 steps paints=%d" % (cnt["paint"] - c0["paint"]))
log("has clear=%s" % hasattr(app, "search_clear"))
if hasattr(app, "search_clear"):
    app.geometry("1600x1000+20+20"); pump(0.8)
    app.search_var.set("satin"); app.search_entry.focus_force(); pump(0.4)
    grab("09_clear_visible")
    app.search_clear(); pump(0.4)
    log("after clear text=%r focus_in_search=%s" % (app.search_var.get(), app.focus_get() is app.search_entry))
    # live results on results page (debounced)
    app.search_var.set("satin"); app.do_search(); pump(0.8)
    c0 = dict(cnt)
    app.search_var.set("")
    type_text("leather")
    pump(1.0)
    log("live typing 7 keys on results page: fills=%d q=%r results=%d focus_in_search=%s" % (cnt["fill"] - c0["fill"], app.search_q, len(app._filtered_home()), app.focus_get() is app.search_entry))
    grab("10_live_results")
    app.focus_set(); pump(0.4)
    app.search_var.set(""); pump(0.4)
    grab("11_unfocused_placeholder")
open(os.path.join(OUT, "%s_log.txt" % TAG), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
try: app._player_kill()
except Exception: pass
app.destroy()
os._exit(0)
