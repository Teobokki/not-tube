#!/usr/bin/env python3
import os, subprocess, sys
OUT = "/workspace/not-tube/samples"
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
os.makedirs(OUT, exist_ok=True)

def text_vf(label, y="(h-text_h)/2", size=36, color="white"):
    return (
        f"drawtext=fontfile={FONT}:text='{label}':fontsize={size}:"
        f"fontcolor={color}:x=(w-text_w)/2:y={y}:"
        f"shadowcolor=black@0.55:shadowx=2:shadowy=2,format=yuv420p"
    )

CLIPS = [
    # src is lavfi video, vf is additional video filters
    dict(file="sunrise-glass-lake.mp4", dur=12, freq=196,
         src="gradients=s=1280x720:d=12:r=24:n=2:c0=0x0B1A33:c1=0xE07A3A:speed=0.02:x0=640:y0=720:x1=640:y1=0",
         vf=text_vf("SUNRISE OVER THE GLASS LAKE", "h-80")),
    dict(file="handmade-ceramic-bowls.mp4", dur=11, freq=247,
         src="gradients=s=1280x720:d=11:r=24:n=2:c0=0x5C3A2B:c1=0xD9A066:speed=0.02:x0=0:y0=0:x1=1280:y1=720",
         vf="drawbox=x=390:y=200:w=500:h=280:color=0xC48A58@0.85:t=fill,"
            "drawbox=x=430:y=230:w=420:h=220:color=0xE8C49A@0.5:t=fill,"
            + text_vf("HANDMADE CERAMIC BOWLS", "80")),
    dict(file="autumn-streets.mp4", dur=14, freq=220,
         src="gradients=s=1280x720:d=14:r=24:n=2:c0=0x2B1508:c1=0xC45A12:speed=0.03:x0=0:y0=720:x1=1280:y1=0",
         vf="noise=alls=16:allf=t," + text_vf("A WALK THROUGH AUTUMN STREETS", "(h-text_h)/2", 34, "0xFFE7C2")),
    dict(file="tomato-pasta.mp4", dur=10, freq=294,
         src="gradients=s=1280x720:d=10:r=24:n=2:c0=0x6B120A:c1=0xF2C14E:speed=0.025:x0=200:y0=200:x1=1000:y1=600",
         vf=text_vf("THREE-MINUTE TOMATO PASTA")),
    dict(file="city-lights-rain.mp4", dur=13, freq=165,
         src="gradients=s=1280x720:d=13:r=24:n=2:c0=0x050816:c1=0x1C3A6E:speed=0.04:x0=0:y0=0:x1=1280:y1=720",
         vf=text_vf("CITY LIGHTS AFTER RAIN", "80")),
    dict(file="how-radio-waves-travel.mp4", dur=12, freq=330,
         src="color=c=0x071018:s=1280x720:d=12:r=24",
         vf=("geq=r='20+80*sin(hypot(X-640,Y-360)/40-T*2.2)':"
             "g='30+90*sin(hypot(X-640,Y-360)/40-T*2.2+0.4)':"
             "b='50+140*sin(hypot(X-640,Y-360)/40-T*2.2+0.8)',"
             + text_vf("HOW RADIO WAVES TRAVEL"))),
    dict(file="desk-setup-tour.mp4", dur=11, freq=175,
         src="gradients=s=1280x720:d=11:r=24:n=2:c0=0x1A1D24:c1=0x3D4C5C:speed=0.01:x0=0:y0=0:x1=1280:y1=720",
         vf=("drawbox=x=180:y=140:w=640:h=360:color=0x9AA6B2@0.35:t=fill,"
             "drawbox=x=200:y=156:w=600:h=328:color=0x15181E@0.9:t=fill,"
             "drawbox=x=860:y=260:w=220:h=140:color=0x6E7B86@0.4:t=fill,"
             + text_vf("DESK SETUP TOUR 2026", "48"))),
    dict(file="night-market-food.mp4", dur=12, freq=262,
         src="gradients=s=1280x720:d=12:r=24:n=2:c0=0x14080A:c1=0xC45C18:speed=0.035:x0=640:y0=0:x1=640:y1=720",
         vf=text_vf("NIGHT MARKET STREET FOOD", "h-80", 36, "0xFFE6C0")),
    dict(file="coastal-trail-spring.mp4", dur=13, freq=208,
         src="gradients=s=1280x720:d=13:r=24:n=2:c0=0x0D3B4C:c1=0x7EC8A0:speed=0.02:x0=0:y0=720:x1=1280:y1=0",
         vf=text_vf("COASTAL TRAIL IN LATE SPRING", "(h-text_h)/2", 34)),
    dict(file="paper-lamp-workshop.mp4", dur=10, freq=185,
         src="gradients=s=1280x720:d=10:r=24:n=2:c0=0x2A2318:c1=0xF0D48A:speed=0.018:x0=640:y0=360:x1=200:y1=200",
         vf=text_vf("PAPER LAMP WORKSHOP", "(h-text_h)/2", 36, "0xFFF6D8")),
]

def run(clip):
    dst = os.path.join(OUT, clip["file"])
    d = clip["dur"]
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", clip["src"],
        "-f", "lavfi", "-i", f"sine=frequency={clip['freq']}:sample_rate=44100:duration={d}",
        "-vf", clip["vf"],
        "-af", f"volume=0.28,afade=t=in:st=0:d=0.3,afade=t=out:st={d-0.4}:d=0.4",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        "-movflags", "+faststart", dst,
    ]
    print("making", clip["file"], "...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("FAILED", clip["file"], "code", r.returncode)
        return False
    print("  ok", os.path.getsize(dst), "bytes")
    return True

ok = all(run(c) for c in CLIPS)
sys.exit(0 if ok else 1)
