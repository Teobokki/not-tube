# -*- coding: utf-8 -*-
"""Not AI - NOT TUBE's built-in assistant.

Works fully offline from the app's own data: titles, descriptions, tags, channel
names, durations, upload dates, watch history, caption files (.srt/.vtt sidecars or
subtitle tracks inside the video) and the video frames themselves (scene changes).
It does NOT understand speech or recognise what is on screen. Everything is local
text processing (tokens, TF-IDF / BM25 ranking, keyword extraction) plus ffmpeg
scene-change detection.  An optional user-supplied chat endpoint can polish wording;
it is off by default and nothing depends on it.
(c)2026 EX Inc./HYPERION DIGITAL (c)2026
"""
from __future__ import annotations

import json, math, os, re, ssl, subprocess, time, urllib.request
from collections import Counter

STOP = set("""
a an the and or but if then so of to in on at by for with from into onto over under about as is are was were be been being
am do does did doing have has had having i me my mine we us our you your yours he she it its they them their this that these
those there here what which who whom whose when where why how all any both each few more most other some such no nor not only
own same than too very can will just should would could might must shall may also get got gets make made let lets show shows
find found give want wanted wanna need please something anything stuff thing things video videos clip clips watch watching
one ones two three four five six seven eight nine ten minute minutes second seconds hour hours ready
part parts episode ep new newest latest recent today here
one ones some kind sort like really maybe right now today tonight im i'm id i'd ive i've dont don't feel feeling mood looking
look see seen search searching play playing put open lol pls hey hi hello okay ok yeah yes sure into thanks thank
""".split())

# small hand-written related-word table (honest: a word list, not a language model)
RELATED = {
    "outfit": ["dress", "haul", "try", "fashion", "look", "wardrobe", "style"],
    "fashion": ["dress", "haul", "outfit", "style", "wardrobe", "look"],
    "clothes": ["dress", "haul", "outfit", "jacket", "wardrobe"],
    "dress": ["midi", "satin", "slip", "gown"],
    "haul": ["try", "outfit", "dress"],
    "date": ["night", "evening"],
    "party": ["evening", "night", "going", "out"],
    "evening": ["night", "satin", "gown"],
    "calm": ["relax", "ambient", "slow", "quiet", "nature", "walk", "rain"],
    "relax": ["calm", "ambient", "slow", "quiet", "nature", "walk", "chill"],
    "chill": ["calm", "relax", "ambient", "slow"],
    "nature": ["forest", "walk", "outdoor", "trail", "rain", "river", "mountain"],
    "walk": ["walking", "stroll", "trail", "city"],
    "city": ["street", "night", "urban", "walk"],
    "food": ["cooking", "recipe", "kitchen", "market", "street"],
    "cook": ["cooking", "recipe", "kitchen"],
    "music": ["song", "beat", "theme", "trailer", "live"],
    "game": ["gaming", "gameplay", "trailer", "modding", "episode"],
    "gaming": ["game", "gameplay", "trailer", "modding"],
    "news": ["update", "launch", "release", "today"],
    "funny": ["comedy", "fun", "laugh"],
    "tech": ["fix", "network", "download", "modding", "setup", "pc"],
    "film": ["films", "cinema", "movie", "trailer", "short"],
    "movie": ["film", "films", "cinema", "trailer"],
    "jacket": ["leather", "blazer", "coat"],
    "shoes": ["heels", "boots", "sneakers"],
    "black": ["dark", "noir"],
    "red": ["burgundy", "crimson"],
}

SMALL_WORDS = set("a an and as at but by for in of on or the to vs via with from".split())
JUNK_TOKENS = set("""final finalfinal edit edited export exported render rendered copy new old draft
v1 v2 v3 v4 v5 hd fhd uhd sd hq lq 4k 8k 2k 1080p 720p 480p 360p 1440p 2160p 60fps 30fps 24fps 120fps
x264 x265 h264 h265 hevc avc aac mp4 mov mkv webm avi web dl webrip bluray rip proper remux vid img mvi dsc dji gopr gopro
pxl clip clips raw untitled video recording screen screenrecording capture obs""".split())


def tokens(text):
    text = (text or "").lower().replace("'", "")
    return [t for t in re.findall(r"[^\W_]+", text, re.UNICODE)]


def stem(t):
    if len(t) > 5 and t.endswith("ing"):
        return t[:-3]
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("es") and t[-3] in "sxz":
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    if len(t) > 4 and t.endswith("ed"):
        return t[:-2]
    return t


def content_terms(text):
    return [stem(t) for t in tokens(text) if t not in STOP and (len(t) > 1 or not t.isascii())]


def fmt_t(s):
    s = int(max(0, s))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return "%d:%02d:%02d" % (h, m, s) if h else "%d:%02d" % (m, s)


# ------------------------------------------------------------------ captions
def parse_captions(text):
    """SRT or WebVTT -> [(start, end, text)]"""
    out = []
    ts = r"(\d{1,2}:)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
    blocks = re.split(r"\n\s*\n", text.replace("\r", ""))
    for b in blocks:
        m = re.search(ts + r"\s*-->\s*" + ts, b)
        if not m:
            continue
        g = m.groups()

        def sec(h, mi, s, ms):
            return int((h or "0:")[:-1] or 0) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0
        st, en = sec(*g[0:4]), sec(*g[4:8])
        body = b[m.end():].strip()
        body = re.sub(r"<[^>]+>", "", body)
        body = re.sub(r"\{[^}]+\}", "", body)
        body = " ".join(l.strip() for l in body.split("\n") if l.strip())
        if body:
            out.append((st, en, body))
    return out


def chapters_from_description(desc, dur=0):
    """Creator-written chapters: lines like '0:00 Intro' / '01:23 - Part two'."""
    chs = []
    for line in (desc or "").splitlines():
        m = re.match(r"\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|.]?\s*(.+)", line)
        if m:
            parts = [int(x) for x in m.group(1).split(":")]
            t = 0
            for p in parts:
                t = t * 60 + p
            if dur and t > dur:
                continue
            chs.append((float(t), m.group(2).strip()))
    chs.sort()
    if len(chs) >= 2:
        return chs
    return []


# ------------------------------------------------------------------ index / ranking
class Index:
    """BM25 over the local library. Fields are weighted by repeating terms."""

    def __init__(self, videos, channels, captions_for=None):
        self.videos = list(videos)
        self.chan = {c.get("id"): c for c in channels}
        self.docs, self.df = [], Counter()
        self._surf = {}
        for v in self.videos:
            ch = self.chan.get(v.get("channel_id")) or {}
            terms = []
            terms += content_terms(v.get("title")) * 3
            terms += content_terms(" ".join(v.get("tags") or [])) * 2
            terms += content_terms(ch.get("name")) * 2
            terms += content_terms(v.get("category"))
            terms += content_terms(v.get("description"))
            cap = captions_for(v) if captions_for else ""
            if cap:
                terms += content_terms(cap)
            for k, w in surface_map(" ".join([v.get("title") or "", " ".join(v.get("tags") or []),
                                               ch.get("name") or "", v.get("description") or ""])).items():
                self._surf.setdefault(k, w)
            tf = Counter(terms)
            self.docs.append(tf)
            for t in tf:
                self.df[t] += 1
        n = max(1, len(self.docs))
        self.n = n
        self.avg = sum(sum(d.values()) for d in self.docs) / float(n) if self.docs else 1.0

    def idf(self, t):
        df = self.df.get(t, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, i, qterms):
        tf = self.docs[i]
        dl = sum(tf.values()) or 1
        k1, b = 1.4, 0.7
        s, hits = 0.0, []
        for t, w in qterms.items():
            f = tf.get(t, 0)
            if not f:
                # prefix match for partial words ("leath" -> leather)
                if len(t) >= 4:
                    f = sum(c for k, c in tf.items() if k.startswith(t)) * 0.6
                if not f:
                    continue
            s += w * self.idf(t) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avg))
            hits.append(t)
        return s, hits

    def surface(self, t):
        return self._surf.get(t, t)

    def keywords(self, i, k=8):
        tf = self.docs[i]
        sc = sorted(((c * self.idf(t), t) for t, c in tf.items() if len(t) > 2 or not t.isascii()), reverse=True)
        return [t for _s, t in sc[:k]]


def expand_query(terms):
    q = Counter()
    for t in terms:
        q[t] += 1.0
        for r in RELATED.get(t, []):
            q[stem(r)] += 0.35
    return q


# ------------------------------------------------------------------ query understanding
DUR_PAT = re.compile(r"(under|less than|shorter than|below|max|at most|over|more than|longer than|at least)\s+(\d+)\s*(seconds|second|secs|sec|s|minutes|minute|mins|min|m|hours|hour|hrs|hr|h)\b")


def parse_request(q, channels):
    """Pull simple, explainable filters out of a sentence."""
    ql = " " + (q or "").lower() + " "
    f = {"min_dur": None, "max_dur": None, "shorts": None, "recent": False, "popular": False,
         "unwatched": False, "liked": False, "channel": None, "notes": []}
    m = DUR_PAT.search(ql)
    if m:
        n = int(m.group(2)); u = m.group(3)[0]
        secs = n * (3600 if u == "h" else 60 if u == "m" else 1)
        if m.group(1) in ("over", "more than", "longer than", "at least"):
            f["min_dur"] = secs; f["notes"].append("longer than %s" % fmt_t(secs))
        else:
            f["max_dur"] = secs; f["notes"].append("up to %s" % fmt_t(secs))
        ql = ql.replace(m.group(0), " ")
    if re.search(r"\b(not shorts?|shorts|vertical)\b", ql):
        f["shorts"] = True; f["notes"].append("NOT SHORTS only")
    elif re.search(r"\b(quick|short one|something short|brief)\b", ql):
        f["max_dur"] = f["max_dur"] or 180; f["notes"].append("short (3 min or less)")
    elif re.search(r"\b(long|longer|deep dive|full length)\b", ql):
        f["min_dur"] = f["min_dur"] or 300; f["notes"].append("longer videos")
    if re.search(r"\b(new|newest|latest|recent|recently|this week|today|fresh)\b", ql):
        f["recent"] = True; f["notes"].append("newest first")
    if re.search(r"\b(popular|most viewed|trending|top|best)\b", ql):
        f["popular"] = True; f["notes"].append("most viewed first")
    if re.search(r"\b(haven'?t (seen|watched)|not watched|unwatched|new to me|never seen)\b", ql):
        f["unwatched"] = True; f["notes"].append("not in your history")
    if re.search(r"\b(i liked|my liked|liked videos|that i liked)\b", ql):
        f["liked"] = True; f["notes"].append("videos you liked")
    # creator: exact channel name / handle mentioned anywhere
    best = None
    for c in channels:
        for key in (c.get("name") or "", (c.get("handle") or "").lstrip("@")):
            k = key.lower().strip()
            if len(k) >= 3 and re.search(r"(?<![^\W_])" + re.escape(k) + r"(?![^\W_])", ql):
                if not best or len(k) > len(best[1]):
                    best = (c, k)
    if best:
        f["channel"] = best[0]
        ql = ql.replace(best[1], " ")
        f["notes"].append("from %s" % best[0].get("name"))
    filler = r"\b(find|show|give|get|recommend|suggest|search|look|looking|search for|me|some|any|videos?|clips?|about|on|with|by|from|for|a|an|the|i|want|wanna|to|watch|something|that|are|is|in|the mood|mood|feel like|what should|should|new|newest|latest|recent|recently|popular|most viewed|trending|top|best|quick|short|long|longer|not shorts?|shorts|vertical|haven'?t|seen|watched|unwatched|never)\b"
    rest = re.sub(filler, " ", ql)
    f["terms"] = content_terms(rest)
    f["words"] = [t for t in tokens(rest) if t not in STOP]
    return f


def _passes(v, f, history_ids, liked_ids):
    d = float(v.get("duration") or 0)
    if f["min_dur"] and d < f["min_dur"]:
        return False
    if f["max_dur"] and d > f["max_dur"]:
        return False
    if f["shorts"] is True and not v.get("is_short"):
        return False
    if f["channel"] and v.get("channel_id") != f["channel"].get("id"):
        return False
    if f["unwatched"] and v.get("id") in history_ids:
        return False
    if f["liked"] and v.get("id") not in liked_ids:
        return False
    return True


def rank(index, f, history_ids=(), liked_ids=(), limit=8):
    """Returns [(video, score, reasons[])]; reasons say exactly why it matched."""
    history_ids, liked_ids = set(history_ids), set(liked_ids)
    q = expand_query(f["terms"])
    out, weak = [], []
    for i, v in enumerate(index.videos):
        if not _passes(v, f, history_ids, liked_ids):
            continue
        s, hits = index.score(i, q) if q else (0.0, [])
        if q and not hits:
            continue
        reasons = []
        direct = [h for h in hits if h in f["terms"]]
        rel = [h for h in hits if h not in f["terms"]]
        nterms = len(set(f["terms"]))
        if nterms >= 2 and len(set(direct)) < max(1, int(round(nterms / 2.0 + 0.01))):
            weak.append((v, s * 0.5, ["partly matches “%s”" % ", ".join(index.surface(h) for h in (direct or rel)[:3])]))
            continue
        if direct:
            reasons.append("matches “%s”" % ", ".join(index.surface(h) for h in direct[:4]))
        if rel:
            reasons.append("related words: %s" % ", ".join(index.surface(h) for h in rel[:3]))
        if f["channel"]:
            reasons.append("by %s" % f["channel"].get("name"))
        if f["recent"]:
            s += 0.01 * _recency_days_bonus(v)
        if f["popular"]:
            s += math.log10(1 + int(v.get("views") or 0)) * 0.3
        if not q:
            s += 1.0
        out.append((v, s, reasons))
    if not out and weak:
        out = weak  # nothing matched most of the words: show the closest, labelled as partial
    if f["recent"]:
        out.sort(key=lambda x: (x[0].get("uploaded") or ""), reverse=True)
        out.sort(key=lambda x: -x[1] if q else 0)
        if not q:
            out.sort(key=lambda x: (x[0].get("uploaded") or ""), reverse=True)
    elif f["popular"] and not q:
        out.sort(key=lambda x: int(x[0].get("views") or 0), reverse=True)
    else:
        out.sort(key=lambda x: -x[1])
    for v, s, r in out:
        if f["recent"]:
            r.append("uploaded %s" % (v.get("uploaded") or "")[:10])
        if f["popular"]:
            r.append("%s views" % "{:,}".format(int(v.get("views") or 0)))
        d = float(v.get("duration") or 0)
        if f["max_dur"] or f["min_dur"]:
            r.append("%s long" % fmt_t(d))
    return out[:limit]


def _recency_days_bonus(v):
    try:
        t = time.mktime(time.strptime((v.get("uploaded") or "")[:19], "%Y-%m-%dT%H:%M:%S"))
        days = max(0.0, (time.time() - t) / 86400.0)
        return max(0.0, 30 - days)
    except Exception:
        return 0.0


def recommend(index, f, history, liked_ids, notscribed, limit=6):
    """Transparent discovery: every pick lists the signals that put it there."""
    hist_ids = [h.get("id") if isinstance(h, dict) else h for h in (history or [])]
    hset = set(hist_ids)
    if f["terms"] or f["channel"]:
        res = rank(index, f, hset, liked_ids, limit=limit * 2)
        res.sort(key=lambda x: (x[0].get("id") in hset, -x[1]))
        out = []
        for v, s, r in res[:limit]:
            if v.get("id") not in hset:
                r.append("you haven't watched it yet")
            out.append((v, s, r))
        return out
    # nothing specific asked: use your own signals, shown openly
    taste = Counter()
    pos = {v.get("id"): i for i, v in enumerate(index.videos)}
    for vid in hist_ids[:15] + list(liked_ids):
        i = pos.get(vid)
        if i is not None:
            for t in index.keywords(i, 6):
                taste[t] += 1
    tq = Counter({t: 1.0 for t, _c in taste.most_common(8)})
    out = []
    for i, v in enumerate(index.videos):
        if not _passes(v, f, hset, liked_ids):
            continue
        s, reasons = 0.0, []
        if v.get("id") not in hset:
            s += 1.0; reasons.append("you haven't watched it yet")
        if v.get("channel_id") in notscribed:
            s += 1.2
            reasons.append("from a channel you NOTSCRIBE to")
        if tq:
            ts, hits = index.score(i, tq)
            if hits and v.get("id") not in hset:
                s += ts * 0.6
                reasons.append("similar to what you watched (%s)" % ", ".join(index.surface(h) for h in hits[:3]))
        if f["recent"] or not tq:
            b = _recency_days_bonus(v)
            if b > 20:
                s += 0.4; reasons.append("uploaded recently")
        if f["popular"]:
            s += math.log10(1 + int(v.get("views") or 0)) * 0.3
            reasons.append("%s views" % "{:,}".format(int(v.get("views") or 0)))
        out.append((v, s, reasons))
    out.sort(key=lambda x: -x[1])
    # keep a little variety: max 2 per channel
    picked, per = [], Counter()
    for v, s, r in out:
        if per[v.get("channel_id")] >= 2:
            continue
        per[v.get("channel_id")] += 1
        picked.append((v, s, r or ["in your library"]))
        if len(picked) >= limit:
            break
    return picked


# ------------------------------------------------------------------ summaries
def extractive_summary(text, k=3):
    """Pick the k most informative sentences (TF-IDF style, in original order)."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 12]
    if not sents:
        return []
    if len(sents) <= k:
        return sents
    df = Counter()
    toks = [set(content_terms(s)) for s in sents]
    for t in toks:
        df.update(t)
    freq = Counter(t for s in sents for t in content_terms(s))
    scored = []
    for i, s in enumerate(sents):
        ts = toks[i]
        if not ts:
            continue
        sc = sum(freq[t] * math.log(1 + len(sents) / df[t]) for t in ts) / (len(ts) ** 0.5)
        scored.append((sc, i))
    keep = sorted(i for _s, i in sorted(scored, reverse=True)[:k])
    return [sents[i] for i in keep]


def surface_map(text):
    """stem -> the most common way it was actually written (for display)."""
    m = {}
    for t in tokens(text):
        if t in STOP:
            continue
        m.setdefault(stem(t), Counter())[t] += 1
    return {k: c.most_common(1)[0][0] for k, c in m.items()}


def keywords_of(text, k=6, extra_df=None):
    c = Counter(t for t in content_terms(text) if len(t) > 2 or not t.isascii())
    sm = surface_map(text)
    return [sm.get(t, t) for t, _n in c.most_common(k)]


def detect_scenes(ffmpeg, path, dur, run, threshold=0.30, max_scan=5400):
    """Real scene changes from the frames (ffmpeg 'scene' score). Returns seconds."""
    if not path or not os.path.isfile(path):
        return []
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-t", str(int(max_scan)), "-i", path, "-an", "-sn",
           "-vf", "scale=160:-2,select='gt(scene\\,%.2f)',showinfo" % threshold, "-f", "null", "-"]
    try:
        p = run(cmd, timeout=max(60, int(min(dur or 60, max_scan) * 0.6) + 30))
        txt = (p.stderr or b"").decode("utf-8", "replace")
        ts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", txt)]
    except Exception:
        return []
    out = []
    for t in ts:
        if t < 1.0 or (dur and t > dur - 1.0):
            continue
        if not out or t - out[-1] >= max(2.0, (dur or 60) / 40.0):
            out.append(t)
    return out


def frame_stats(path):
    """Plain-language look of a frame: brightness + dominant tone (measured, not 'seen')."""
    try:
        from PIL import Image, ImageStat
        im = Image.open(path).convert("RGB").resize((48, 27))
        r, g, b = ImageStat.Stat(im).mean
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        light = "dark" if lum < 60 else "dim" if lum < 100 else "bright" if lum > 170 else "mid-lit"
        mx = max(r, g, b); mn = min(r, g, b)
        if mx - mn < 18:
            tone = "neutral/grey tones"
        elif mx == r:
            tone = "warm tones" if g > b else "red/magenta tones"
        elif mx == g:
            tone = "green tones"
        else:
            tone = "cool/blue tones"
        return "%s, %s" % (light, tone)
    except Exception:
        return ""


def build_chapters(dur, scenes, desc_chapters, captions, max_ch=8):
    """Pick chapter start times. Priority: creator chapters > caption topic shifts >
    detected scene changes > evenly spaced segments.  Returns (source, [(t, label|None)])."""
    if desc_chapters:
        return "creator chapters in the description", desc_chapters[:12]
    dur = float(dur or 0)
    if dur <= 0:
        return "none", []
    target = max(2, min(max_ch, int(dur // 45) + 2)) if dur > 20 else 3
    starts = [0.0]
    src = "evenly spaced segments"
    if scenes:
        src = "scene changes detected in the video frames"
        cand = list(scenes)
        target = max_ch
        if len(cand) + 1 > target:
            # keep the most evenly spread subset
            step = dur / target
            chosen = []
            for k in range(1, target):
                goal = k * step
                best = min(cand, key=lambda t: abs(t - goal))
                if all(abs(best - c) > step * 0.4 for c in chosen):
                    chosen.append(best)
            cand = sorted(chosen)
        starts += cand
    if len(starts) < 2:
        step = dur / target
        starts = [round(k * step, 1) for k in range(target)]
        src = "evenly spaced segments" + (" (no clear scene changes found)" if scenes == [] else "")
    out = []
    for i, t in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else dur
        label = None
        if captions:
            seg = " ".join(c[2] for c in captions if c[0] < end and c[1] > t)
            kw = keywords_of(seg, 3)
            if kw:
                label = " · ".join(kw).capitalize()
        out.append((t, label))
    if captions and src != "creator chapters in the description":
        src += " + caption keywords"
    return src, out


# ------------------------------------------------------------------ creator helper
def clean_filename(name):
    """'VID_20261110_231005_final_v2_1080p.mp4' -> 'Untitled clip' style cleanup."""
    base = os.path.splitext(os.path.basename(name or ""))[0]
    s = base
    s = re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", " ", s)            # [tags] (1) {x}
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)                         # camelCase
    s = re.sub(r"[_\.\-+]+", " ", s)
    s = re.sub(r"\b(19|20)\d{2}\s?[01]?\d\s?[0-3]?\d(\s?[0-2]?\d\s?[0-5]\d(\s?[0-5]\d)?)?\b", " ", s)  # dates
    s = re.sub(r"\b\d{8}\s\d{6}\b|\b\d{6,}\b", " ", s)                 # long digit runs
    s = re.sub(r"\b\d{1,2}\s\d{2}\s\d{2}\b", " ", s)                   # 20 48 48 clock
    words = []
    for w in s.split():
        lw = w.lower()
        if lw in JUNK_TOKENS or re.fullmatch(r"(v|ver|take|copy)\d+", lw) or re.fullmatch(r"\d{3,4}p", lw):
            continue
        if words and words[-1].lower() == lw:
            continue
        words.append(w)
    while words and words[-1].isdigit() and len(words) > 1:
        words.pop()
    if all(w.isdigit() for w in words):
        return ""
    return smart_title(" ".join(words))


def smart_title(s):
    out = []
    for i, w in enumerate((s or "").split()):
        if w.isupper() and len(w) > 1:
            out.append(w)                     # keep acronyms
        elif i and w.lower() in SMALL_WORDS:
            out.append(w.lower())
        elif not w.isascii():
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def suggest_titles(clean, desc, dur, is_short, related_kw):
    """A few honest title options built from the words you gave it. No invented claims."""
    base = clean.strip() or "New video"
    kws = [k for k in keywords_of(base + " " + (desc or ""), 6)]
    sugg = [base]
    if desc:
        lead = extractive_summary(desc, 1)
        if lead:
            first = re.sub(r"[.!?]+$", "", lead[0])
            if 8 <= len(first) <= 70 and first.lower() != base.lower():
                sugg.append(smart_title(first))
    base_t = set(content_terms(base))
    kws = [k for k in kws if k not in base_t]
    if len(kws) >= 2:
        hook = smart_title(" ".join(kws[:3]))
        if hook.lower() != base.lower():
            sugg.append("%s | %s" % (base, hook) if len(base) < 40 else hook)
    if is_short:
        sugg.append("%s in %d Seconds" % (base, max(1, int(round(dur or 0)))) if dur else base + " (Short)")
    elif dur and dur >= 600:
        sugg.append("%s — Full %d-Minute Video" % (base, int(dur // 60)))
    else:
        rk = [r for r in (related_kw or []) if stem(r) not in base_t and r.lower() not in base.lower()]
        if rk:
            sugg.append("%s · %s" % (base, smart_title(rk[0])))
    seen, out = set(), []
    for t in sugg:
        t = re.sub(r"\s+", " ", t).strip()[:95]
        if t and t.lower() not in seen:
            seen.add(t.lower()); out.append(t)
    return out[:4]


def suggest_tags(clean, desc, channel_name, info, dur, is_short, library_tags=(), library_cooc=None):
    tags = []
    def add(t):
        t = (t or "").strip().lower()
        if t and t not in tags and len(t) <= 30:
            tags.append(t)
    for k in keywords_of(clean, 5):
        add(k)
    for k in keywords_of(desc or "", 7):
        add(k)
    words = [w for w in tokens(clean) if w not in STOP]
    for a, b in zip(words, words[1:]):
        if a not in STOP and b not in STOP and len(a) > 2 and len(b) > 2:
            add(a + " " + b)
    if channel_name:
        add(channel_name)
    if is_short:
        add("not shorts"); add("vertical")
    w, h = (info or {}).get("width") or 0, (info or {}).get("height") or 0
    if max(w, h) >= 3800:
        add("4k")
    elif max(w, h) >= 1900:
        add("1080p")
    if dur and dur >= 600:
        add("long video")
    # words other creators in this library used next to the same keywords
    if library_cooc:
        for k in list(tags)[:5]:
            for t in library_cooc.get(stem(k), [])[:2]:
                add(t)
    return tags[:14]


def library_cooccurrence(videos):
    co = {}
    for v in videos:
        ks = set(content_terms((v.get("title") or "") + " " + " ".join(v.get("tags") or [])))
        for a in ks:
            for b in ks:
                if a != b and len(b) > 2:
                    co.setdefault(a, Counter())[b] += 1
    return {a: [b for b, _n in c.most_common(4)] for a, c in co.items()}


# ------------------------------------------------------------------ optional endpoint
def llm_complete(cfg, system, user, timeout=25):
    """OPTIONAL: an OpenAI-compatible /chat/completions endpoint the user configured
    themselves. Off unless enabled + endpoint set. Normal TLS verification, no bypass."""
    if not cfg or not cfg.get("enabled") or not (cfg.get("endpoint") or "").strip():
        return None
    url = cfg["endpoint"].strip().rstrip("/")
    if not url.endswith("/chat/completions"):
        url += "/chat/completions"
    body = json.dumps({
        "model": cfg.get("model") or "default",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.4, "max_tokens": 500,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    if (cfg.get("api_key") or "").strip():
        req.add_header("Authorization", "Bearer " + cfg["api_key"].strip())
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return ((d.get("choices") or [{}])[0].get("message") or {}).get("content")


# ------------------------------------------------------------------ intent routing
def intent_of(text, page):
    t = (text or "").lower()
    if re.search(r"\b(summar|chapter|key moment|timestamps?|takeaway|tl;?dr|what happens|break ?down)", t):
        return "summary"
    if re.search(r"\b(title|tags?|rename|name (this|my)|caption for my)\b", t):
        return "helper"
    if re.search(r"\b(recommend|suggest|what should i|what to watch|in the mood|feel like|surprise me|something (good|fun|new)|bored)\b", t):
        return "discover"
    if re.search(r"\b(more like this|similar)\b", t):
        return "similar"
    if re.search(r"\b(how (do|does) you work|what can you do|help|who are you)\b", t):
        return "about"
    return "search"
