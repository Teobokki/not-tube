# -*- coding: utf-8 -*-
import os, sys, json, shutil
os.environ["APPDATA"] = r"Z:\tmp\nttest104m"
os.makedirs(r"Z:\tmp\nttest104m\NOT TUBE", exist_ok=True)
sys.path.insert(0, r"Z:\workspace\not-tube")
os.chdir(r"Z:\workspace\not-tube")
os.environ["USERNAME"] = "box"
import not_tube as nt

# Build a fake 1.0.3 library: featured channels + old haul filenames as videos
lib_path = os.path.join(r"Z:\tmp\nttest104m", "NOT TUBE", "library.json")
# First seed current then rewrite videos to old files
nt.seed_library(reset=True)
lib = nt.Library()
# replace haul videos with fake 1.0.3 records
kept = [v for v in lib.videos() if not nt._is_bundled_featured_seed(lib, v)]
# add old-style records on featured channels
old_files = list(nt.OLD_FEATURED_HAUL_FILES)
# pair 2 per channel like 1.0.3
feat = lib.featured_channels()
old_specs = [
    (feat[0]["id"], "mira-trench-jeans-haul.mp4", "Trench coat and jeans haul"),
    (feat[0]["id"], "mira-weekend-knit-haul.mp4", "Weekend knit haul"),
    (feat[1]["id"], "nova-workwear-blazer-haul.mp4", "Workwear blazer haul"),
    (feat[1]["id"], "nova-beige-set-haul.mp4", "Beige set haul"),
    (feat[2]["id"], "lina-floral-midi-haul.mp4", "Floral midi haul"),
    (feat[2]["id"], "lina-denim-skirt-haul.mp4", "Denim skirt haul"),
    (feat[3]["id"], "sable-utility-jacket-haul.mp4", "Utility jacket haul"),
    (feat[3]["id"], "sable-wool-coat-haul.mp4", "Wool coat haul"),
]
old_vids = []
for i, (cid, fn, title) in enumerate(old_specs):
    old_vids.append({
        "id": "old-%d" % i, "title": title, "description": "", "path": fn,
        "thumb": "", "channel_id": cid, "duration": 6, "width": 960, "height": 540,
        "views": 100, "likes": 1, "uploaded": 1, "is_short": False,
        "seed_file": fn, "category": "haul",
    })
# also a user-looking video wrongly having seed_file basename on an owned channel (1.0.3 bug)
owned = [c for c in lib.channels() if c.get("owned") and not c.get("featured")]
if owned:
    old_vids.append({
        "id": "user-keep", "title": "My own upload", "description": "", "path": "my-own.mp4",
        "thumb": "", "channel_id": owned[0]["id"], "duration": 6, "width": 960, "height": 540,
        "views": 10, "likes": 0, "uploaded": 1, "is_short": False,
        "seed_file": "my-own.mp4",
    })
data = json.loads(open(lib_path, encoding="utf-8").read())
# keep non-haul videos + old
others = [v for v in data["videos"] if v.get("category") != "haul"]
data["videos"] = others + old_vids
open(lib_path, "w", encoding="utf-8").write(json.dumps(data, indent=2))

lib = nt.Library()
print("before featured=%d hauls=%d old_ids=%s user=%s owner_pc=%s" % (
    len(lib.featured_channels()), len(lib.haul_videos()),
    [v["id"] for v in lib.videos() if str(v["id"]).startswith("old-")],
    bool(lib.get_video("user-keep")), nt.is_owner_pc()))
nt.ensure_bundled_content(lib)
lib2 = nt.Library()
old_left = [v["id"] for v in lib2.videos() if str(v.get("id","")).startswith("old-") or (v.get("seed_file") or "") in nt.OLD_FEATURED_HAUL_FILES]
titles = [v.get("title") for v in lib2.haul_videos()]
print("after featured=%d hauls=%d videos=%d old_left=%s user=%s titles=%s" % (
    len(lib2.featured_channels()), len(lib2.haul_videos()), len(lib2.videos()),
    old_left, bool(lib2.get_video("user-keep")), titles))
ok = len(lib2.featured_channels())==4 and len(lib2.haul_videos())==12 and not old_left and bool(lib2.get_video("user-keep")) and not nt.is_owner_pc()
print("MIGRATE " + ("PASS" if ok else "FAIL"))
