#!/usr/bin/env python3
"""Render docs/demo.gif: a terminal-style walkthrough of pr-risk-score on two real PRs.

Dev-only helper (needs Pillow and the Menlo font on macOS, or pass --font). The numbers
shown come from real runs of the skill on supabase/auth#2887 and cli/cli#14907.

    python3 docs/demo/make_demo_gif.py [--out docs/demo.gif] [--font /path/to/mono.ttf]
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 960, 460
PAD = 28
BG = (13, 17, 23)
CHROME = (22, 27, 34)
FG = (230, 237, 243)
DIM = (125, 133, 144)
GREEN = (63, 185, 80)
YELLOW = (210, 153, 34)
ORANGE = (240, 136, 62)
RED = (248, 81, 73)
BLUE = (88, 166, 255)
PURPLE = (188, 140, 255)

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "demo.gif"))
ap.add_argument("--font", default="/System/Library/Fonts/Menlo.ttc")
args = ap.parse_args()

F = ImageFont.truetype(args.font, 17, index=0)
FB = ImageFont.truetype(args.font, 17, index=1)
FBIG = ImageFont.truetype(args.font, 34, index=1)
LH = 25

frames, durations = [], []


def base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 36], fill=CHROME)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 22, 12, 28 + i * 22, 24], fill=c)
    d.text((W // 2 - 110, 9), "claude — pr-risk-score", font=F, fill=DIM)
    return im, d


def draw_lines(d, lines, y0=56):
    """lines: list of list[(text, color, bold)] segments."""
    y = y0
    for segs in lines:
        x = PAD
        for text, color, bold in segs:
            font = FB if bold else F
            d.text((x, y), text, font=font, fill=color)
            x += d.textlength(text, font=font)
        y += LH
    return y


def push(lines, ms, extra=None):
    im, d = base()
    y = draw_lines(d, lines)
    if extra:
        extra(d, y)
    frames.append(im)
    durations.append(ms)


def seg(t, c=FG, b=False):
    return (t, c, b)


def bar(points, maximum, width=10):
    n = int(round(width * points / maximum))
    return "█" * n + "░" * (width - n)


def type_prompt(history, prompt, per=2):
    for i in range(0, len(prompt) + 1, per):
        push(history + [[seg("> ", PURPLE, True), seg(prompt[:i]), seg("▍", DIM)]], 35)
    done = history + [[seg("> ", PURPLE, True), seg(prompt)]]
    push(done, 450)
    return done


def score_card(d, y, score, level, color, decision, human):
    box = [PAD, y + 6, W - PAD, y + 112]
    if hasattr(d, "rounded_rectangle"):  # Pillow >= 8.2
        d.rounded_rectangle(box, radius=10, outline=color, width=3)
    else:
        d.rectangle(box, outline=color, width=3)
    d.ellipse([PAD + 22, y + 30, PAD + 54, y + 62], fill=color)
    d.text((PAD + 72, y + 22), "%d / 100  %s" % (score, level), font=FBIG, fill=color)
    d.text((PAD + 72, y + 72), decision, font=FB, fill=ORANGE if human else GREEN)


# ---- Scene 1: risky PR -------------------------------------------------------------
h = type_prompt([], "how risky is supabase/auth#2887? does a human need to look?")
h = h + [[]]
steps = [
    [seg("● ", GREEN), seg("Baseline  ", DIM), seg("python3 scripts/pr_risk.py supabase/auth#2887", BLUE)],
]
for s in steps:
    h = h + [s]
    push(h, 500)

factors = [("Sensitive areas", 20, 40, "auth: magic_link.go, verify.go"), ("Change size", 10, 20, "185 lines"), ("Change spread", 2, 10, "7 files"), ("Tests", 0, 20, "144 test lines")]
for i in range(1, 11):
    rows = []
    for name, pts, mx, why in factors:
        p = pts * i / 10.0
        rows.append([seg("    %-16s" % name, FG), seg(bar(p, mx), YELLOW if pts else DIM), seg(" %2d/%-3d " % (round(p), mx), FG), seg(why, DIM)])
    push(h + rows, 60)
h = h + rows + [[seg("    baseline ", DIM), seg("32", YELLOW, True), seg("  MEDIUM — by itself, AI review would pass it", DIM)], []]
push(h, 1100)

h = h + [[seg("● ", GREEN), seg("Semantic review  ", DIM), seg("reading hotspots + inline review threads", BLUE)]]
push(h, 700)
items = [
    [seg("    +8  ", ORANGE, True), seg("magic_link.go:84  ", BLUE), seg("password wiped on request, before ownership is proven")],
    [seg("        ", FG), seg("[ESCALATION] unauthenticated change to another user's credentials", RED, True)],
    [seg("    +3  ", ORANGE, True), seg("bot flagged this line; concern dismissed", FG)],
    [seg("    +3  ", ORANGE, True), seg("description says the opposite of the code", FG)],
    [seg("    -6  ", GREEN, True), seg("tests cover the attacker scenario", FG)],
]
for it in items:
    h = h + [it]
    push(h, 650)
push(h, 1200)

verdict = h[:1] + [[]]
push(verdict, 2600, extra=lambda d, y: (
    score_card(d, y, 60, "HIGH", ORANGE, "Human review required  ·  32 baseline, +8 semantic, escalated to 60", True),
    draw_lines(d, [[seg("Focus: ", DIM, True), seg("magic_link.go:88", BLUE), seg(" — move the wipe to the verify step?")],
                   [seg("       ", DIM), seg("verify.go:313", BLUE), seg(" — signup-confirm path still keeps an attacker's password")]], y + 132),
))

# ---- Scene 2: boring PR ------------------------------------------------------------
h2 = type_prompt([], "and cli/cli#14907?")
h2 = h2 + [[], [seg("● ", GREEN), seg("Baseline  ", DIM), seg("dependency patch bump (goldmark 1.8.6 → 1.8.7), go.mod only", FG)]]
push(h2, 900)
push(h2[:1] + [[]], 2400, extra=lambda d, y: (
    score_card(d, y, 6, "LOW", GREEN, "AI review is sufficient  ·  no human needed", False),
    draw_lines(d, [[seg("Humans review the PR that can hurt you. The rest flows through.", DIM)]], y + 140),
))

# ---- Outro -------------------------------------------------------------------------
im, d = base()
d.text((W // 2 - d.textlength("pr-risk-score", font=FBIG) // 2, 160), "pr-risk-score", font=FBIG, fill=FG)
sub = "Let AI review the boring PRs. Send humans only the risky ones."
d.text((W // 2 - d.textlength(sub, font=F) // 2, 220), sub, font=F, fill=DIM)
inst = "/plugin marketplace add karamage/pr-risk-score"
d.text((W // 2 - d.textlength(inst, font=FB) // 2, 280), inst, font=FB, fill=BLUE)
frames.append(im)
durations.append(2600)

out = os.path.abspath(args.out)
# One shared palette for every frame (ffmpeg palettegen) keeps colors stable; per-frame
# adaptive palettes make text flicker between colors.
import shutil, subprocess, tempfile
tmp = tempfile.mkdtemp()
with open(os.path.join(tmp, "list.txt"), "w") as fh:
    for i, (f, ms) in enumerate(zip(frames, durations)):
        f.save(os.path.join(tmp, "%04d.png" % i))
        fh.write("file '%04d.png'\nduration %.3f\n" % (i, ms / 1000.0))
    fh.write("file '%04d.png'\n" % (len(frames) - 1))
if shutil.which("ffmpeg"):
    lst = os.path.join(tmp, "list.txt")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-i", lst, "-vf", "palettegen=max_colors=128:stats_mode=full", os.path.join(tmp, "pal.png")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-i", lst, "-i", os.path.join(tmp, "pal.png"),
                    "-lavfi", "paletteuse=dither=none", "-loop", "0", out], check=True)
else:  # fallback: shared palette via Pillow
    pal_src = frames[-4].quantize(colors=128, method=Image.MEDIANCUT)
    q = [f.quantize(palette=pal_src, dither=0) for f in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0)
shutil.rmtree(tmp)
print(out, len(frames), "frames", os.path.getsize(out) // 1024, "KB")
