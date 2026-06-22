#!/usr/bin/env python3
"""Regenerate any skipped/missing Zenie memes on the GitHub Actions runner.

The cloud drafting agent runs in a network-restricted sandbox whose egress
allowlist blocks the media CDNs (Giphy/Tenor/Pexels), so it ships memes as
SKIPPED. GitHub-hosted runners have open internet, so we re-source + render the
memes here (same offload pattern already used for Slack), then let the existing
post_social_to_slack.py step post them. No-op when no meme is skipped/missing.

Reads PEXELS_KEY from env. Idempotent and defensive: a meme that can't be
generated is left skipped (the Slack gate then holds the post — safe by design).
"""
import json, os, re, subprocess, textwrap, urllib.request, urllib.parse, traceback
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO = "isabelhoppmann/ART-Lab-Social-Media"
STATE_PATH = "social/review-state.json"
PEXELS_KEY = os.environ.get("PEXELS_KEY", "")
PEXELS_UA = {"User-Agent": "ZenieAgent/1.0"}
VIDEO_W, VIDEO_H = 1080, 1920

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # GitHub ubuntu runner
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",       # local mac
    "/Library/Fonts/Arial Bold.ttf",
]

# Theme keywords -> Pexels queries. A universal fallback list is always appended
# so a search never comes back empty.
THEME_QUERIES = [
    (("journal", "write", "writing", "diary", "notebook"),
     ["woman writing journal bed", "woman journaling notebook", "woman writing diary home"]),
    (("text", "phone", "he ", "dm", "dating", "talking stage", "situationship", "ex ", "crush"),
     ["woman surprised phone", "woman looking at phone", "woman texting smiling couch"]),
    (("bestie", "friend", "besties", "girls"),
     ["women friends laughing home", "two women talking couch", "female friends together"]),
    (("heal", "cry", "sad", "therapy", "emotional", "feel"),
     ["woman reflective window", "woman emotional home", "woman calm tea"]),
    (("coffee", "morning", "self care", "selfcare", "soft life", "relax"),
     ["woman morning coffee home", "woman self care relaxing", "woman candle reading"]),
]
UNIVERSAL_FALLBACK = ["woman smiling home", "woman lifestyle candid", "woman portrait indoor", "happy woman home"]


def queries_for(overlay_text):
    t = (overlay_text or "").lower()
    qs = []
    for keys, q in THEME_QUERIES:
        if any(k.strip() in t for k in keys):
            qs.extend(q)
    qs.extend(UNIVERSAL_FALLBACK)
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q); out.append(q)
    return out


def pexels_search(query, per_page=8):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": query, "orientation": "portrait", "per_page": per_page})
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, **PEXELS_UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    out = []
    for v in data.get("videos", []):
        hd = [f for f in v["video_files"] if f.get("width") == 1080 and f.get("height") in (1920, 2048)]
        if hd and v.get("duration", 0) >= 4:
            out.append({"id": v["id"], "duration": v["duration"], "url": hd[0]["link"], "page": v.get("url", "")})
    return out


def pexels_download(mp4_url, out_path):
    req = urllib.request.Request(mp4_url, headers=PEXELS_UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(out_path, "wb") as f:
        f.write(r.read())


def render_text_card(text, path):
    font_path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if not font_path:
        raise RuntimeError("no bold sans-serif font found")
    font = ImageFont.truetype(font_path, 60)
    side_margin, h_padding, v_padding, line_h = 40, 35, 28, 78
    card_w = VIDEO_W - 2 * side_margin
    cpl = max(15, int((card_w - 2 * h_padding) / (font.getlength("M") * 0.55)))
    wrapped = textwrap.wrap(text, width=cpl)
    card_h = 2 * v_padding + len(wrapped) * line_h
    canvas_h = card_h + 2 * side_margin
    shadow = Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle(
        [(side_margin + 4, side_margin + 4), (side_margin + card_w + 4, side_margin + card_h + 4)], fill=(0, 0, 0, 50))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))
    canvas = Image.alpha_composite(Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0)), shadow)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(side_margin, side_margin), (side_margin + card_w, side_margin + card_h)], fill=(255, 255, 255, 250))
    y = side_margin + v_padding
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((VIDEO_W - (bbox[2] - bbox[0])) // 2, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_h
    canvas.save(path, "PNG")


def make_mp4(src, overlay_text, out_path):
    card = "/tmp/zenie_card.png"
    render_text_card(overlay_text, card)
    cmd = ["ffmpeg", "-y", "-stream_loop", "-1", "-t", "6", "-i", src, "-i", card,
           "-filter_complex",
           "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[base];[base][1:v]overlay=0:H-h-60",
           "-t", "6", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", out_path]
    subprocess.run(cmd, check=True, capture_output=True)


def verify(path):
    if os.path.getsize(path) < 100_000:
        raise RuntimeError("rendered mp4 too small")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=width,height,codec_type", "-of", "json", path],
                           capture_output=True, text=True)
    s = [x for x in json.loads(probe.stdout)["streams"] if x.get("codec_type") == "video"][0]
    if (s["width"], s["height"]) != (1080, 1920):
        raise RuntimeError(f"bad dims {s['width']}x{s['height']}")


def pick_and_render(overlay_text, out_path):
    cands, seen = [], set()
    for q in queries_for(overlay_text):
        try:
            for c in pexels_search(q):
                if c["id"] not in seen:
                    seen.add(c["id"]); c["query"] = q; cands.append(c)
        except Exception as e:
            print(f"    search '{q}' failed: {e}")
        if len(cands) >= 6:
            break
    if not cands:
        raise RuntimeError("no Pexels candidates from any query")
    pick = sorted(cands, key=lambda c: abs(c["duration"] - 6))[0]
    src = "/tmp/zenie_src.mp4"
    pexels_download(pick["url"], src)
    make_mp4(src, overlay_text, out_path)
    verify(out_path)
    return pick


def update_index_html(path, meme_num, post):
    if not os.path.exists(path):
        return
    html = open(path, encoding="utf-8").read()
    block = (
        '<div class="post">\n'
        f'  <h2>Meme {meme_num}</h2>\n'
        f'  <div class="meme-wrap"><video src="meme_{meme_num}.mp4" autoplay loop muted playsinline controls></video></div>\n'
        f'  <p class="caption">{post.get("ig_caption", "")}</p>\n'
        f'  <p class="tags">{post.get("hashtags", "")}</p>\n'
        f'  <p class="time">Best time: {post.get("best_time", "")}</p>\n'
        '</div>'
    )
    # Replace the existing (skipped) Meme N post block, whatever its inner content.
    pattern = re.compile(r'<div class="post[^"]*">\s*<h2>Meme ' + str(meme_num) + r'\b.*?</div>', re.DOTALL)
    new_html, n = pattern.subn(block, html, count=1)
    if n:
        open(path, "w", encoding="utf-8").write(new_html)


def clear_md_skip(path, meme_num):
    if not os.path.exists(path):
        return
    md = open(path, encoding="utf-8").read()
    md = re.sub(r'(## Meme ' + str(meme_num) + r'\b[^\n]*?) ?⚠️ SKIPPED', r'\1', md)
    md = re.sub(r'\n\*\*⚠️ SKIPPED[^\n]*\*\*\n', '\n', md)
    open(path, "w", encoding="utf-8").write(md)


def main():
    if not PEXELS_KEY:
        print("regenerate_memes: PEXELS_KEY not set — skipping"); return
    state = json.load(open(STATE_PATH))
    week = state.get("week_date", "")
    changed = False
    for post in state.get("posts", []):
        if (post.get("post_type") or "").lower() != "meme":
            continue
        if post.get("media_url") and not post.get("skipped"):
            continue  # already has a real meme
        label = post.get("label", "")
        m = re.search(r"\d+", label)
        if not m:
            continue
        n = m.group(0)
        overlay = post.get("overlay_text", "")
        out_path = f"posts/{week}/meme_{n}.mp4"
        print(f"Regenerating {label} (overlay: {overlay!r})")
        try:
            pick = pick_and_render(overlay, out_path)
            post["skipped"] = False
            post.pop("skip_reason", None)
            post["media_url"] = f"https://cdn.jsdelivr.net/gh/{REPO}@main/posts/{week}/meme_{n}.mp4"
            post["slack_posted"] = False
            update_index_html(f"posts/{week}/index.html", n, post)
            clear_md_skip(f"posts/{week}/zenie_drafts.md", n)
            changed = True
            print(f"  OK {label} <- Pexels {pick['id']} ({pick['duration']}s) q='{pick['query']}' {pick['page']}")
        except Exception as e:
            print(f"  FAILED to regenerate {label}: {e}")
            traceback.print_exc()
    if changed:
        json.dump(state, open(STATE_PATH, "w"), indent=2, ensure_ascii=False)
        print("regenerate_memes: updated review-state.json + assets")
    else:
        print("regenerate_memes: nothing to do (no skipped/missing memes)")


if __name__ == "__main__":
    main()
