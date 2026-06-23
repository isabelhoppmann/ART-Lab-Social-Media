#!/usr/bin/env python3
"""Regenerate Zenie quote images on the GitHub Actions runner in response to
Catie's review feedback.

The cloud feedback agent runs in a network-restricted sandbox that blocks the
media CDNs, so it can't re-render images itself. Instead it edits
social/review-state.json — setting a quote post's `needs_render` (new quote /
attribution) and/or `needs_new_background` (different photo) — and pushes. This
runner has open internet, so it re-renders the flagged quote images here, then
post_social_to_slack.py re-posts them into the review thread.

Mirrors the quote-rendering logic in AGENT_INSTRUCTIONS.md so revised quotes are
visually identical to the originals. No-op when nothing is flagged.
"""
import io, json, os, re, random, urllib.request, traceback
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

REPO = "isabelhoppmann/ART-Lab-Social-Media"
STATE_PATH = "social/review-state.json"
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")

FONT_VAR = "/tmp/PlayfairDisplay-VAR.ttf"
FONT_VAR_ITALIC = "/tmp/PlayfairDisplay-Italic-VAR.ttf"


def ensure_fonts():
    if not os.path.exists(FONT_VAR):
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
            FONT_VAR)
    if not os.path.exists(FONT_VAR_ITALIC):
        urllib.request.urlretrieve(
            "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
            FONT_VAR_ITALIC)


def load_font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None and hasattr(f, "set_variation_by_axes"):
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def get_curated_photo(pexels_key, page=None):
    if page is None:
        page = random.randint(1, 8)
    url = f"https://api.pexels.com/v1/curated?per_page=80&page={page}"
    req = urllib.request.Request(url, headers={"Authorization": pexels_key, "User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    candidates = [p for p in data["photos"] if p["width"] >= 3000 and p["width"] >= p["height"]]
    if not candidates:
        candidates = sorted(data["photos"], key=lambda p: p["width"], reverse=True)[:10]
    photo = random.choice(candidates)
    photo_req = urllib.request.Request(photo["src"]["large2x"], headers={"User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(photo_req, timeout=60) as r:
        img = Image.open(io.BytesIO(r.read())).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((1080, 1080), Image.LANCZOS)
    img = ImageEnhance.Color(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    return img


def make_quote_image(quote, attribution, filename, bg_img):
    SIZE = 1080
    CARD_W, CARD_H = 730, 730
    CARD_X = (SIZE - CARD_W) // 2
    CARD_Y = (SIZE - CARD_H) // 2
    TEXT_COLOR = (52, 30, 90)
    ATTR_COLOR = (100, 75, 150)
    CREAM = (250, 247, 241, 248)

    bg = bg_img.convert("RGBA")

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([(CARD_X + 10, CARD_Y + 10), (CARD_X + CARD_W + 10, CARD_Y + CARD_H + 10)],
                         radius=10, fill=(0, 0, 0, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    bg = Image.alpha_composite(bg, shadow)

    card_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_layer)
    cd.rounded_rectangle([(CARD_X, CARD_Y), (CARD_X + CARD_W, CARD_Y + CARD_H)], radius=8, fill=CREAM)
    bg = Image.alpha_composite(bg, card_layer)

    deco = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    palette = [(180, 155, 220, 70), (210, 175, 210, 60), (160, 195, 180, 55),
               (220, 175, 195, 65), (195, 170, 225, 75)]

    def draw_corner_blobs(cx, cy):
        for _ in range(10):
            ox = cx + random.randint(-45, 45)
            oy = cy + random.randint(-45, 45)
            r = random.randint(22, 52)
            dd.ellipse([(ox - r, oy - r), (ox + r, oy + r)], fill=random.choice(palette))

    draw_corner_blobs(CARD_X + 20, CARD_Y + 20)
    draw_corner_blobs(CARD_X + CARD_W - 20, CARD_Y + CARD_H - 20)
    deco = deco.filter(ImageFilter.GaussianBlur(radius=10))
    bg = Image.alpha_composite(bg, deco)

    bg_rgb = bg.convert("RGB")
    draw = ImageDraw.Draw(bg_rgb)
    font_bold = load_font(FONT_VAR, 56, weight=700)
    font_attr = load_font(FONT_VAR_ITALIC, 30, weight=400)
    font_brand = load_font(FONT_VAR, 34, weight=400)

    import textwrap
    wrapped = textwrap.wrap(f"“{quote}”", width=24)
    line_h = 70
    text_block_h = len(wrapped) * line_h
    text_start_y = CARD_Y + (CARD_H - text_block_h) // 2 - 30
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_bold)
        lw = bbox[2] - bbox[0]
        lx = CARD_X + (CARD_W - lw) // 2
        draw.text((lx, text_start_y), line, font=font_bold, fill=TEXT_COLOR)
        text_start_y += line_h

    attr_text = f"–{attribution}"
    ab = draw.textbbox((0, 0), attr_text, font=font_attr)
    ax = CARD_X + (CARD_W - (ab[2] - ab[0])) // 2
    draw.text((ax, text_start_y + 18), attr_text, font=font_attr, fill=ATTR_COLOR)

    zb = draw.textbbox((0, 0), "zenie", font=font_brand)
    zx = CARD_X + (CARD_W - (zb[2] - zb[0])) // 2
    draw.text((zx, CARD_Y + CARD_H - 58), "zenie", font=font_brand, fill=TEXT_COLOR)

    bg_rgb.save(filename, format="JPEG", quality=95)


def verify(path):
    if os.path.getsize(path) < 20_000:
        raise RuntimeError("rendered jpg too small")


def update_index_html(path, num, post):
    if not os.path.exists(path):
        return
    html = open(path, encoding="utf-8").read()
    block = (
        '<div class="post">\n'
        f'  <h2>Quote {num}</h2>\n'
        f'  <div class="quote-wrap"><img src="quote_{num}.jpg" alt="Quote {num}"></div>\n'
        f'  <p class="caption">{post.get("fb_caption", "")}</p>\n'
        f'  <p class="tags">{post.get("hashtags", "")}</p>\n'
        f'  <p class="time">Best time: {post.get("best_time", "")}</p>\n'
        '</div>'
    )
    pattern = re.compile(r'<div class="post[^"]*">\s*<h2>Quote ' + str(num) + r'\b.*?</div>', re.DOTALL)
    new_html, n = pattern.subn(block, html, count=1)
    if n:
        open(path, "w", encoding="utf-8").write(new_html)


def main():
    if not PEXELS_KEY:
        print("regenerate_quotes: PEXELS_KEY not set — skipping")
        return
    state = json.load(open(STATE_PATH))
    week = state.get("week_date", "")
    ensure_fonts()
    changed = False
    for post in state.get("posts", []):
        if (post.get("post_type") or "").lower() not in ("quote", "quote image"):
            continue
        if not (post.get("needs_render") or post.get("needs_new_background")):
            continue
        label = post.get("label", "")
        m = re.search(r"\d+", label)
        if not m:
            continue
        n = m.group(0)
        quote = post.get("quote", "")
        attribution = post.get("attribution", "")
        out_path = f"posts/{week}/quote_{n}.jpg"
        print(f"Regenerating {label} (quote: {quote!r} — {attribution!r})")
        try:
            bg = get_curated_photo(PEXELS_KEY, page=random.randint(1, 8))
            make_quote_image(quote, attribution, out_path, bg)
            verify(out_path)
            post["media_url"] = f"https://cdn.jsdelivr.net/gh/{REPO}@main/posts/{week}/quote_{n}.jpg"
            post["slack_posted"] = False
            post["revised"] = True
            post.pop("needs_render", None)
            post.pop("needs_new_background", None)
            update_index_html(f"posts/{week}/index.html", n, post)
            changed = True
            print(f"  OK {label} re-rendered")
        except Exception as e:
            print(f"  FAILED to regenerate {label}: {e}")
            traceback.print_exc()
    if changed:
        json.dump(state, open(STATE_PATH, "w"), indent=2, ensure_ascii=False)
        print("regenerate_quotes: updated review-state.json + assets")
    else:
        print("regenerate_quotes: nothing to do (no flagged quotes)")


if __name__ == "__main__":
    main()
