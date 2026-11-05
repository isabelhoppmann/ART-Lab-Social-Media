#!/usr/bin/env python3
"""Render Zenie's newer post types on the GitHub Actions runner.

Added 2026-11-05 when Catie asked to try new tactics (followers had dropped every
week since July and reach was ~6% of followers). The drafting agent writes only
TEXT for these posts into social/review-state.json; this script turns them into
finished, upload-ready files, the same way regenerate_memes.py and
regenerate_quotes.py already do for memes and quote cards.

Post types handled here (everything else is left alone):

  Text Card   1080x1350 JPG. `card_style` picks the look:
                notes_app    a phone-notes page (title + body lines)
                text_thread  a text-message thread (`messages`: [{from: me|them, text}])
                fill_blank   "finish the sentence" stem with a drawn blank
                big_type     one bold statement on a solid brand colour
  Carousel    1080x1350 JPGs, one per entry in `slides` ([{title, body}]).
              Slide 1 is the cover, the last slide is the journaling prompt.
  Reel        1080x1920 MP4 on moving stock footage (Pexels portrait video),
              no audio (Isabel adds a trending sound in the Instagram app).
                reel_style pov    `overlay_text` as native-looking caption text
                reel_style quote  `quote` + `attribution` centred on a soft scrim
  Story       1080x1920 JPG frames from `frames` ([{text, sticker}]). Stickers
              (poll, question box, slider) are added by hand in the app, so the
              frame leaves clean space for them.

Every post may carry `series` (e.g. "Sunday Scaries"), printed as a small
kicker so the series is recognisable in the feed.

A post renders when it has no media yet, or when feedback set `needs_render`.
A post that can't be rendered is marked skipped with a reason; it never blocks
the rest of the week. Env: PEXELS_KEY (only needed for Reels).
"""
import io, json, os, random, re, subprocess, sys, textwrap, traceback, urllib.parse, urllib.request, zlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
REPO = "isabelhoppmann/ART-Lab-Social-Media"
STATE_PATH = "social/review-state.json"
USED_BROLL_PATH = "social/used_broll.json"
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
UA = {"User-Agent": "ZenieAgent/1.0"}
FONT_DIR = os.path.join(REPO_ROOT, "assets", "fonts")

W, H_FEED, H_TALL = 1080, 1350, 1920

# Zenie palette
VIOLET = (107, 63, 160)
LAVENDER = (201, 177, 232)
BLUSH = (240, 160, 192)
INK = (52, 30, 90)            # dark purple text, same as the quote cards
SOFT_INK = (110, 90, 140)
CREAM = (250, 247, 241)
LILAC_BG = (239, 230, 250)
BLUSH_BG = (251, 232, 239)

HANDLED = {"text card", "carousel", "reel", "story"}


# ── fonts + text helpers ──────────────────────────────────────────────────────
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


SERIF_BOLD, SERIF, SERIF_ITALIC = "Playfair-Bold.ttf", "Playfair-Regular.ttf", "Playfair-Italic.ttf"
SANS, SANS_SEMI, SANS_BOLD = "Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"

# Burned-in text can't show colour emoji (they render as tofu boxes); captions keep theirs.
_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
                       "\U00002B00-\U00002BFF\U0000FE00-\U0000FE0F\U0000200D]+")


def clean(text):
    return re.sub(r"[ \t]+", " ", _EMOJI_RE.sub("", text or "")).strip()


def wrap(draw, text, fnt, max_w):
    """Pixel-accurate word wrap that keeps explicit newlines."""
    out = []
    for para in clean(text).split("\n"):
        words, line = para.split(), ""
        if not words:
            out.append("")
            continue
        for w in words:
            trial = f"{line} {w}".strip()
            if draw.textlength(trial, font=fnt) <= max_w or not line:
                line = trial
            else:
                out.append(line)
                line = w
        out.append(line)
    # never leave one word alone on the last line if it can be helped
    if len(out) >= 2 and len(out[-1].split()) == 1 and len(out[-2].split()) > 2:
        prev = out[-2].split()
        moved = prev.pop()
        cand = f"{moved} {out[-1]}"
        if draw.textlength(cand, font=fnt) <= max_w:
            out[-2], out[-1] = " ".join(prev), cand
    return out


def fit(draw, text, face, max_w, max_h, start, smallest, leading=1.25):
    """Largest size (start→smallest) at which `text` fits the box."""
    size = start
    while size >= smallest:
        f = font(face, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) * size * leading <= max_h:
            return f, lines, int(size * leading)
        size -= 4
    f = font(face, smallest)
    return f, wrap(draw, text, f, max_w), int(smallest * leading)


def draw_lines(draw, lines, fnt, x, y, lh, fill, align="left", box_w=None):
    for ln in lines:
        lx = x
        if align == "center":
            lx = x + (box_w - draw.textlength(ln, font=fnt)) / 2
        draw.text((lx, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def kicker(draw, text, x, y, fill, size=30, align="left", box_w=None):
    if not text:
        return y
    t = " ".join(clean(text).upper())  # letter-spaced small caps look
    f = font(SANS_SEMI, size)
    if align == "center":
        x = x + (box_w - draw.textlength(t, font=f)) / 2
    draw.text((x, y), t, font=f, fill=fill)
    return y + int(size * 1.9)


def wordmark(draw, x, y, fill, size=38, align="left", box_w=None):
    f = font(SERIF, size)
    if align == "center":
        x = x + (box_w - draw.textlength("zenie", font=f)) / 2
    draw.text((x, y), "zenie", font=f, fill=fill)


def watercolor(img, corners=("tl", "br"), alpha=70, seed=0):
    """Soft blurred blobs at the corners — the same motif as the quote cards,
    so new formats read as the same brand."""
    rnd = random.Random(seed)
    w, h = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pal = [(180, 155, 220), (210, 175, 210), (160, 195, 180), (220, 175, 195), (195, 170, 225)]
    pts = {"tl": (40, 40), "tr": (w - 40, 40), "bl": (40, h - 40), "br": (w - 40, h - 40)}
    for c in corners:
        cx, cy = pts[c]
        for _ in range(12):
            ox, oy, r = cx + rnd.randint(-90, 90), cy + rnd.randint(-90, 90), rnd.randint(40, 110)
            d.ellipse([(ox - r, oy - r), (ox + r, oy + r)], fill=(*rnd.choice(pal), alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(28))
    return Image.alpha_composite(img.convert("RGBA"), layer)


def save_jpg(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert("RGB").save(path, "JPEG", quality=94)


def seed_for(week, label, n=0):
    return zlib.crc32(f"{week}|{label}|{n}".encode())


# ── Text Card ─────────────────────────────────────────────────────────────────
def card_notes_app(post, path, seed):
    img = Image.new("RGB", (W, H_FEED), (255, 253, 247))
    d = ImageDraw.Draw(img)
    amber = (214, 150, 20)
    d.text((56, 60), "‹", font=font(SANS, 64), fill=amber)
    d.text((96, 78), "All notes", font=font(SANS, 38), fill=amber)
    d.text((W - 120, 70), "···", font=font(SANS_BOLD, 44), fill=amber)
    date = clean(post.get("card_date") or "")
    y = 190
    if date:
        f = font(SANS, 30)
        d.text(((W - d.textlength(date, font=f)) / 2, y), date, font=f, fill=(150, 145, 140))
        y += 80
    title = post.get("card_title") or ""
    if title:
        f, lines, lh = fit(d, title, SANS_BOLD, W - 140, 300, 76, 48, 1.18)
        y = draw_lines(d, lines, f, 70, y, lh, (30, 28, 32)) + 30
    body = post.get("card_text") or ""
    f, lines, lh = fit(d, body, SANS, W - 140, H_FEED - y - 160, 56, 32, 1.45)
    draw_lines(d, lines, f, 70, y, lh, (40, 38, 44))
    wordmark(d, 70, H_FEED - 95, (190, 180, 200), 34)
    save_jpg(img, path)


def card_text_thread(post, path, seed):
    img = Image.new("RGB", (W, H_FEED), (255, 255, 255))
    d = ImageDraw.Draw(img)
    name = clean(post.get("thread_name") or "me")
    # header
    d.ellipse([(W / 2 - 46, 50), (W / 2 + 46, 142)], fill=LAVENDER)
    init = (name[:1] or "z").upper()
    fi = font(SANS_SEMI, 44)
    d.text((W / 2 - d.textlength(init, font=fi) / 2, 70), init, font=fi, fill=(255, 255, 255))
    fn = font(SANS, 30)
    d.text(((W - d.textlength(name, font=fn)) / 2, 156), name, font=fn, fill=(60, 60, 66))
    d.line([(0, 214), (W, 214)], fill=(232, 228, 238), width=2)
    msgs = post.get("messages") or [{"from": "me", "text": post.get("card_text", "")}]
    fb = font(SANS, 52)
    max_bw = int(W * 0.74)
    y = 260
    blocks = []
    for m in msgs:
        lines = wrap(d, m.get("text", ""), fb, max_bw - 64)
        bw = max(d.textlength(l, font=fb) for l in lines) + 64
        bh = len(lines) * 66 + 44
        blocks.append((m.get("from", "me") == "me", lines, bw, bh))
    total = sum(b[3] + 22 for b in blocks)
    if total < H_FEED - 420:  # vertically settle a short thread
        y = 260 + (H_FEED - 420 - total) // 3
    for mine, lines, bw, bh in blocks:
        x = W - 48 - bw if mine else 48
        fill = VIOLET if mine else (236, 232, 242)
        d.rounded_rectangle([(x, y), (x + bw, y + bh)], radius=40, fill=fill)
        ty = y + 18
        for l in lines:
            d.text((x + 32, ty), l, font=fb, fill=(255, 255, 255) if mine else (30, 28, 36))
            ty += 66
        y += bh + 22
    status = clean(post.get("thread_status") or "")
    if status and blocks and blocks[-1][0]:
        fs = font(SANS, 26)
        d.text((W - 48 - d.textlength(status, font=fs), y), status, font=fs, fill=(150, 146, 156))
    wordmark(d, 48, H_FEED - 95, (200, 190, 214), 34)
    save_jpg(img, path)


def card_fill_blank(post, path, seed):
    img = watercolor(Image.new("RGB", (W, H_FEED), LILAC_BG), ("tr", "bl"), 60, seed)
    d = ImageDraw.Draw(img)
    pad = 110
    y = kicker(d, post.get("series") or "Finish the sentence", pad, 170, VIOLET)
    stem = clean(post.get("card_text") or "").rstrip(" _.…")
    f, lines, lh = fit(d, stem, SERIF_BOLD, W - 2 * pad, 620, 96, 56, 1.18)
    y = draw_lines(d, lines, f, pad, y + 30, lh, INK)
    # the blank
    last_w = d.textlength(lines[-1], font=f) if lines else 0
    bx = pad + last_w + 28
    if bx > W - pad - 220:
        bx, y = pad, y + 10
    else:
        y -= lh
    base = y + int(lh * 0.82)
    d.line([(bx, base), (W - pad, base)], fill=VIOLET, width=6)
    hint = clean(post.get("card_hint") or "")
    if hint:
        d.text((pad, base + 70), hint, font=font(SERIF_ITALIC, 40), fill=SOFT_INK)
    wordmark(d, pad, H_FEED - 150, INK, 40)
    save_jpg(img, path)


def card_big_type(post, path, seed):
    bgs = [(VIOLET, (255, 255, 255), LAVENDER), (BLUSH_BG, INK, VIOLET), (CREAM, INK, VIOLET)]
    bg, fg, accent = bgs[seed % len(bgs)]
    if post.get("card_color") in ("violet", "blush", "cream"):
        bg, fg, accent = bgs[("violet", "blush", "cream").index(post["card_color"])]
    img = Image.new("RGB", (W, H_FEED), bg)
    d = ImageDraw.Draw(img)
    pad = 100
    y = kicker(d, post.get("series"), pad, 150, accent)
    f, lines, lh = fit(d, post.get("card_text", ""), SANS_BOLD, W - 2 * pad, H_FEED - y - 330, 104, 52, 1.16)
    block_h = len(lines) * lh
    y0 = max(y + 20, (H_FEED - block_h) // 2 - 40)
    draw_lines(d, lines, f, pad, y0, lh, fg)
    wordmark(d, pad, H_FEED - 150, accent, 40)
    save_jpg(img, path)


CARD_STYLES = {"notes_app": card_notes_app, "text_thread": card_text_thread,
               "fill_blank": card_fill_blank, "big_type": card_big_type}


def render_text_card(post, week, n):
    style = (post.get("card_style") or "big_type").strip().lower()
    if style not in CARD_STYLES:
        style = "big_type"
    post["card_style"] = style
    rel = f"posts/{week}/text_card_{n}.jpg"
    CARD_STYLES[style](post, rel, seed_for(week, post.get("label", "")))
    return [rel]


# ── Carousel ──────────────────────────────────────────────────────────────────
def render_carousel(post, week, n):
    slides = post.get("slides") or []
    if len(slides) < 3:
        raise RuntimeError(f"carousel needs at least 3 slides, got {len(slides)}")
    slides = slides[:10]                      # Instagram's cap
    total = len(slides)
    series = post.get("series")
    seed = seed_for(week, post.get("label", ""))
    out = []
    for i, s in enumerate(slides, 1):
        title, body = clean(s.get("title", "")), clean(s.get("body", ""))
        role = s.get("role") or ("cover" if i == 1 else "prompt" if i == total else "item")
        pad = 100
        if role == "cover":
            img = watercolor(Image.new("RGB", (W, H_FEED), CREAM), ("tr", "bl"), 75, seed)
            d = ImageDraw.Draw(img)
            y = kicker(d, series, pad, 150, VIOLET)
            f, lines, lh = fit(d, title, SERIF_BOLD, W - 2 * pad, 640, 104, 60, 1.14)
            y0 = max(y + 40, (H_FEED - len(lines) * lh) // 2 - 80)
            y = draw_lines(d, lines, f, pad, y0, lh, INK)
            if body:
                fb, bl, blh = fit(d, body, SANS, W - 2 * pad, 220, 40, 30, 1.4)
                draw_lines(d, bl, fb, pad, y + 30, blh, SOFT_INK)
            ax, ay = W - pad - 70, H_FEED - 122
            d.line([(ax, ay), (ax + 64, ay)], fill=VIOLET, width=6)
            d.line([(ax + 40, ay - 22), (ax + 66, ay), (ax + 40, ay + 22)], fill=VIOLET, width=6, joint="curve")
            wordmark(d, pad, H_FEED - 150, INK, 40)
        elif role == "prompt":
            img = Image.new("RGB", (W, H_FEED), VIOLET)
            img = watercolor(img, ("tl", "br"), 45, seed + 1)
            d = ImageDraw.Draw(img)
            f, lines, lh = fit(d, title or body, SERIF_BOLD, W - 2 * pad, 640, 92, 52, 1.2)
            fb = bl = None
            if title and body:
                fb, bl, blh = fit(d, body, SANS, W - 2 * pad, 220, 44, 30, 1.4)
            block = 60 + len(lines) * lh + (30 + len(bl) * blh if bl else 0)
            y = max(170, (H_FEED - block) // 2 - 40)
            y = kicker(d, s.get("kicker") or "Journal on this", pad, y, LAVENDER)
            y = draw_lines(d, lines, f, pad, y + 10, lh, (255, 255, 255))
            if bl:
                draw_lines(d, bl, fb, pad, y + 30, blh, LAVENDER)
            wordmark(d, pad, H_FEED - 150, (255, 255, 255), 40)
        else:
            img = Image.new("RGB", (W, H_FEED), CREAM)
            d = ImageDraw.Draw(img)
            idx = s.get("number") or f"{i - 1:02d}"
            ft = lines = fb = bl = None
            lh = blh = 0
            if title:
                ft, lines, lh = fit(d, title, SANS_BOLD, W - 2 * pad, 360, 80, 48, 1.18)
            if body:
                fb, bl, blh = fit(d, body, SANS, W - 2 * pad, 520, 52, 32, 1.42)
            block = 190 + (len(lines) * lh + 40 if lines else 0) + (len(bl) * blh if bl else 0)
            y = max(120, (H_FEED - block) // 2 - 30)
            d.text((pad, y), str(idx), font=font(SERIF_BOLD, 150), fill=LAVENDER)
            y += 190
            if lines:
                y = draw_lines(d, lines, ft, pad, y, lh, INK) + 40
            if bl:
                draw_lines(d, bl, fb, pad, y, blh, (70, 60, 86))
            wordmark(d, pad, H_FEED - 140, (190, 175, 210), 34)
        dd = ImageDraw.Draw(img)
        pg = f"{i}/{total}"
        fp = font(SANS_SEMI, 28)
        col = LAVENDER if role == "prompt" else (170, 155, 190)
        dd.text((W - pad - dd.textlength(pg, font=fp), 80), pg, font=fp, fill=col)
        rel = f"posts/{week}/carousel_{n}_{i:02d}.jpg"
        save_jpg(img, rel)
        out.append(rel)
    return out


# ── Story frames ──────────────────────────────────────────────────────────────
def render_story(post, week, n):
    frames = post.get("frames") or []
    if not frames:
        raise RuntimeError("story has no frames")
    out = []
    seed = seed_for(week, post.get("label", ""))
    for i, fr in enumerate(frames[:5], 1):
        img = Image.new("RGB", (W, H_TALL), LILAC_BG)
        grad = Image.linear_gradient("L").resize((W, H_TALL))
        img = Image.composite(Image.new("RGB", (W, H_TALL), BLUSH_BG), img, grad)
        img = watercolor(img, ("tl", "br"), 55, seed + i)
        d = ImageDraw.Draw(img)
        pad = 100
        y = kicker(d, fr.get("kicker") or post.get("series"), pad, 300, VIOLET, align="center", box_w=W - 2 * pad)
        f, lines, lh = fit(d, fr.get("text", ""), SERIF_BOLD, W - 2 * pad, 560, 84, 52, 1.2)
        y = draw_lines(d, lines, f, pad, y + 30, lh, INK, "center", W - 2 * pad)
        # the band from ~y+60 to ~y+560 is left empty for the poll / question sticker
        wordmark(d, pad, H_TALL - 330, INK, 40, "center", W - 2 * pad)
        rel = f"posts/{week}/story_{n}_{i:02d}.jpg"
        save_jpg(img, rel)
        out.append(rel)
    return out


# ── Reel (moving background) ──────────────────────────────────────────────────
CALM_FALLBACKS = ["window light curtains", "coffee morning light", "rain on window", "notebook writing pen",
                  "city lights night window", "clouds sky timelapse", "candle flame dark", "ocean waves slow"]


def load_used_broll():
    try:
        return json.load(open(USED_BROLL_PATH))
    except Exception:
        return {"used": []}


def pexels_videos(query, used_ids):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": query, "orientation": "portrait", "per_page": 15, "size": "medium"})
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, **UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    out = []
    for v in data.get("videos", []):
        if v["id"] in used_ids or v.get("duration", 0) < 6:
            continue
        files = [f for f in v.get("video_files", []) if f.get("width") and f.get("height")
                 and f["height"] > f["width"] and f["width"] >= 1080]
        if files:
            best = sorted(files, key=lambda f: f["width"])[0]
            out.append({"id": v["id"], "url": best["link"], "page": v.get("url", ""), "duration": v["duration"]})
    return out


def pick_broll(post):
    if not PEXELS_KEY:
        raise RuntimeError("PEXELS_KEY not set")
    used_ids = {u.get("id") for u in load_used_broll().get("used", [])}
    queries = [q for q in [post.get("broll_query")] + post.get("broll_alternates", []) if q] + CALM_FALLBACKS
    for q in queries:
        try:
            cands = pexels_videos(q, used_ids)
        except Exception as e:
            print(f"    pexels '{q}' failed: {e}")
            continue
        if cands:
            pick = cands[zlib.crc32(q.encode()) % min(3, len(cands))]
            pick["query"] = q
            return pick
    raise RuntimeError("no usable portrait footage found on Pexels")


def reel_overlay_png(post, path):
    img = Image.new("RGBA", (W, H_TALL), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    style = post.get("reel_style", "pov")
    pad = 90
    if style == "quote":
        # soft scrim behind the centre so the quote reads on any footage
        scrim = Image.new("L", (W, H_TALL), 0)
        ImageDraw.Draw(scrim).rectangle([(0, 520), (W, H_TALL - 520)], fill=150)
        scrim = scrim.filter(ImageFilter.GaussianBlur(160))
        img = Image.composite(Image.new("RGBA", (W, H_TALL), (20, 10, 35, 255)), img, scrim)
        d = ImageDraw.Draw(img)
        q = clean(post.get("quote", ""))
        f, lines, lh = fit(d, f"“{q}”", SERIF_BOLD, W - 2 * pad, 760, 84, 52, 1.22)
        y = (H_TALL - len(lines) * lh) // 2 - 60
        y = draw_lines(d, lines, f, pad, y, lh, (255, 255, 255), "center", W - 2 * pad)
        attr = clean(post.get("attribution", ""))
        if attr:
            fa = font(SERIF_ITALIC, 42)
            t = f"– {attr}"
            d.text(((W - d.textlength(t, font=fa)) / 2, y + 30), t, font=fa, fill=(235, 225, 248))
        kicker(d, post.get("series"), pad, 360, (235, 225, 248), 30, "center", W - 2 * pad)
    else:
        text = clean(post.get("overlay_text", ""))
        f, lines, lh = fit(d, text, SANS_SEMI, W - 2 * pad, 640, 68, 46, 1.24)
        y = 330
        shadow = Image.new("RGBA", (W, H_TALL), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        draw_lines(sd, lines, f, pad, y, lh, (0, 0, 0, 200), "center", W - 2 * pad)
        img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(10)))
        d = ImageDraw.Draw(img)
        draw_lines(d, lines, f, pad, y, lh, (255, 255, 255, 255), "center", W - 2 * pad)
        if post.get("series"):
            kicker(d, post["series"], pad, 230, (255, 255, 255, 230), 28, "center", W - 2 * pad)
    fw = font(SERIF, 44)
    d.text(((W - d.textlength("zenie", font=fw)) / 2, H_TALL - 470), "zenie", font=fw, fill=(255, 255, 255, 235))
    img.save(path, "PNG")


def render_reel(post, week, n):
    pick = pick_broll(post)
    src = f"/tmp/zenie_broll_{n}.mp4"
    with urllib.request.urlopen(urllib.request.Request(pick["url"], headers=UA), timeout=120) as r, open(src, "wb") as f:
        f.write(r.read())
    words = len(clean(post.get("quote") or post.get("overlay_text") or "").split())
    dur = max(7, min(12, round(3 + words * 0.35)))
    png = f"/tmp/zenie_reel_overlay_{n}.png"
    reel_overlay_png(post, png)
    rel = f"posts/{week}/reel_{n}.mp4"
    os.makedirs(os.path.dirname(rel), exist_ok=True)
    fc = ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,"
          "eq=brightness=-0.04:saturation=0.92,fps=30[base];[base][1:v]overlay=0:0,"
          f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.5}:d=0.5[v]")
    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-t", str(dur), "-i", src, "-i", png,
           "-filter_complex", fc, "-map", "[v]", "-t", str(dur), "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", rel]
    subprocess.run(cmd, check=True, capture_output=True)
    if os.path.getsize(rel) < 100_000:
        raise RuntimeError("rendered reel too small")
    post["broll"] = {"id": pick["id"], "page": pick["page"], "query": pick["query"]}
    return [rel]


def mark_broll_used(post, week):
    b = post.get("broll")
    if not b:
        return
    data = load_used_broll()
    if not any(u.get("id") == b["id"] for u in data["used"]):
        data["used"].append({"id": b["id"], "page": b["page"], "week": week, "label": post.get("label", "")})
        json.dump(data, open(USED_BROLL_PATH, "w"), indent=2)


# ── main ──────────────────────────────────────────────────────────────────────
RENDERERS = {"text card": render_text_card, "carousel": render_carousel,
             "reel": render_reel, "story": render_story}


def cdn(rel):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@main/{rel}"


def main():
    state = json.load(open(STATE_PATH))
    week = state.get("week_date", "")
    changed = False
    for post in state.get("posts", []):
        ptype = (post.get("post_type") or "").strip().lower()
        if ptype not in HANDLED:
            continue
        needs = bool(post.get("needs_render")) or not post.get("media_url")
        if not needs:
            continue
        label = post.get("label", "")
        m = re.search(r"\d+", label)
        n = m.group(0) if m else "1"
        print(f"Rendering {label} ({ptype})")
        try:
            files = RENDERERS[ptype](post, week, n)
            post["media_urls"] = [cdn(f) for f in files]
            post["media_url"] = post["media_urls"][0]
            post["skipped"] = False
            post.pop("skip_reason", None)
            post["slack_posted"] = False
            if post.get("needs_render"):
                post["revised"] = True
            post.pop("needs_render", None)
            if ptype == "reel":
                mark_broll_used(post, week)
                if post.get("reel_style") == "quote" and post.get("quote"):
                    try:
                        sys.path.insert(0, HERE)
                        from regenerate_quotes import mark_quote_used
                        mark_quote_used(post["quote"], post.get("attribution", ""), week, label)
                    except Exception as e:
                        print(f"  (could not mark quote used: {e})")
            print(f"  OK {label}: {len(files)} file(s)")
        except Exception as e:
            print(f"  FAILED {label}: {e}")
            traceback.print_exc()
            post["skipped"] = True
            post["skip_reason"] = str(e)[:300]
            post.pop("needs_render", None)
        changed = True
    if changed:
        json.dump(state, open(STATE_PATH, "w"), indent=2, ensure_ascii=False)
        print("render_zenie_formats: updated review-state.json + assets")
    else:
        print("render_zenie_formats: nothing to render")


if __name__ == "__main__":
    main()
