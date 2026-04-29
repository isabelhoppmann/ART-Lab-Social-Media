# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## ABOUT ZENIE
Zenie is a journaling app for women focused on self-reflection, personal growth, relationships, and living intentionally. The brand is warm, aspirational, and empowering — not clinical or heavy. Think: romanticizing your life, main character energy, soft life, glow-up mindset. The tone is like a wise, fun best friend. Color identity: **purple-forward** (primary: deep violet #6B3FA0, accent: soft lavender #C9B1E8, highlight: blush pink #F0A0C0).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy or Tenor GIFs in the HTML preview. You MUST NOT generate static PNG files for memes. You MUST also generate an MP4 version (Step 2A.5) for the auto-publisher.
- QUOTE IMAGES: Follow the exact design spec in Step 2C. The card-on-photo format is non-negotiable.
- EXPLICIT CONTENT: All GIFs, images, and content must be 100% family-friendly. Absolutely NO nudity, sexual activity, sexual references, expletives, or adult content. Reject and replace immediately. Zero exceptions.
- GITHUB PUSH: To push a file, always use PUT. If a file already exists, GET it first to retrieve its SHA, then include the SHA in the PUT body. If a file does not exist yet, omit the SHA.

---

## Step 1: Research trending memes (WebSearch)

Find what's trending culturally RIGHT NOW relevant to Zenie's audience (women 20-35, relationships, self-growth, dating, wellness):
1. WebSearch("trending memes relationships dating 2026 tiktok")
2. WebSearch("viral memes self care journaling april 2026")
3. WebSearch("funniest memes this week women relatable")

Identify 2-3 specific meme formats or viral moments that are trending. Must feel current.

---

## Step 2A: Find 2 GIFs matching trending memes

For each meme, search for the specific trending format:
1. WebSearch("site:giphy.com [SPECIFIC MEME NAME]") AND WebSearch("site:tenor.com [SPECIFIC MEME NAME]")
2. **Quality check (REQUIRED):** WebFetch each candidate. Reject if: blurry/low-res, obscure source, clip art, or ANY explicit/adult content.
3. Giphy direct .gif URL: `https://media.giphy.com/media/[ID]/giphy.gif` (ID = last segment of share URL after final dash)
4. Giphy embed (for HTML preview only): `https://giphy.com/embed/[ID]`
5. Tenor: WebFetch the share page to find the direct `media.tenor.com/.../...gif` URL.

For each meme produce THREE pieces of text (matching Zenie's existing IG style — see @zenie.app):

- **`overlay_text`** — the joke/setup that gets rendered ONTO the video as a white card at the top. This is the part that makes the meme work. 6–14 words, punchy. Examples from existing posts: *"Me and my bestie talking about our coworkers we don't like"*, *"I told my BF I'm not drinking tonight I don't wanna be hungover"*, *"When you finally start journaling and your whole vibe upgrades"*.
- **`caption`** — the short reaction/wink shown in the IG post caption field. 2–8 words plus optional emoji. Examples: *"She knows…"*, *"Clearly he wants the smoke"*, *"He couldn't do anything to make me happier!"*. Do NOT repeat the overlay text here — the caption riffs on it.
- **`hashtags`** — 5–8 hashtags including #Zenie or #zenieapp.

---

## Step 2A.5: Convert each meme GIF to MP4 with text overlay (Zenie meme style)

The auto-publisher posts to Instagram as Reels (vertical 9:16), which does not accept GIFs — it requires MP4 video. The visual style mirrors @zenie.app's existing memes: vertical 1080×1920, blurred background of the GIF filling the frame, GIF content centered, and a **white card at the top with black bold sans-serif text** containing the `overlay_text`. The HTML preview still uses the Giphy iframe (better preview UX); the MP4 is what gets posted.

```python
import urllib.request, subprocess, shutil, os, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Portable ffmpeg lookup: use system ffmpeg if available, else install via pip
def _ffmpeg_path():
    p = shutil.which("ffmpeg")
    if p:
        return p
    subprocess.run(["pip", "install", "--quiet", "imageio-ffmpeg"], check=True)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

FFMPEG = _ffmpeg_path()

VIDEO_W = 1080
VIDEO_H = 1920

def render_meme_text_card(overlay_text, output_path):
    """Render Zenie meme-style text card: white solid box with black bold sans-serif text."""
    # Find a bold sans-serif system font
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    font_path = next((p for p in font_candidates if os.path.exists(p)), None)
    if not font_path:
        # Last resort: install dejavu via apt or fall back to default
        raise RuntimeError("No bold sans-serif font found. Install dejavu-fonts or arial.")

    font = ImageFont.truetype(font_path, 60)
    side_margin = 40
    card_w = VIDEO_W - 2 * side_margin
    h_padding = 35
    v_padding = 28
    line_h = 78

    # Wrap text using actual font metrics
    avg_char_w = font.getlength("M") * 0.55
    chars_per_line = max(15, int((card_w - 2 * h_padding) / avg_char_w))
    wrapped = textwrap.wrap(overlay_text, width=chars_per_line)

    card_h = 2 * v_padding + len(wrapped) * line_h
    canvas_h = card_h + 2 * side_margin

    # Soft drop shadow for the card
    shadow = Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle(
        [(side_margin + 4, side_margin + 4), (side_margin + card_w + 4, side_margin + card_h + 4)],
        fill=(0, 0, 0, 50),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))

    canvas = Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, shadow)
    draw = ImageDraw.Draw(canvas)

    # White card
    draw.rectangle(
        [(side_margin, side_margin), (side_margin + card_w, side_margin + card_h)],
        fill=(255, 255, 255, 250),
    )

    # Centered text
    y = side_margin + v_padding
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (VIDEO_W - lw) // 2
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_h

    canvas.save(output_path, "PNG")

def gif_to_mp4(gif_url, output_path, overlay_text):
    """Download GIF, convert to vertical 9:16 MP4 with white text card overlay (Zenie meme style)."""
    tmp_gif = "/tmp/meme_input.gif"
    text_card_path = "/tmp/meme_text_card.png"
    urllib.request.urlretrieve(gif_url, tmp_gif)
    render_meme_text_card(overlay_text, text_card_path)

    # Filter chain:
    # - blurred GIF stretched to 1080x1920 background
    # - GIF content scaled to 1000px wide max, centered vertically
    # - text card overlaid at y=120 (top region)
    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1", "-t", "6",
        "-i", tmp_gif,
        "-i", text_card_path,
        "-filter_complex",
        ("[0:v]scale=1000:-2:force_original_aspect_ratio=decrease[fg];"
         "color=c=white:s=1080x1920:r=30[bg];"
         "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[base];"
         "[base][1:v]overlay=0:120"),
        "-t", "6",
        "-r", "30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(tmp_gif)

# Run for each meme — pass the overlay_text from Step 2A
gif_to_mp4(MEME_1_GIF_URL, "/tmp/meme_1.mp4", MEME_1_OVERLAY_TEXT)
gif_to_mp4(MEME_2_GIF_URL, "/tmp/meme_2.mp4", MEME_2_OVERLAY_TEXT)
```

Both `.mp4` files will be pushed to GitHub in Step 3. Verify each is under 100MB and at least 6 seconds before pushing.

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 real TikTok/Instagram video URLs from wellness/relationships/self-growth creators.
Search: site:tiktok.com self-care OR journaling OR relationships 2026
Get: video URL, creator handle, repost caption, best time to post.

---

## Step 2C: Create 2 Quote Images — EXACT DESIGN SPEC

The design is: **a beautiful full-bleed photo background with a floating cream card on top**, with decorative watercolor/botanical elements at the card corners. This matches Zenie's existing Instagram aesthetic exactly.

### Quotes
- Source REAL attributed quotes from famous thinkers, writers, philosophers (Buddha, Rumi, Maya Angelou, Brené Brown, Stoics, poets, etc.)
- Tone: self-reflection, growth, relationships, intentional living, inner peace
- Length: 10–25 words is fine — the card has room
- Format: include the attribution (name of person, or "Unknown")
- Example: quote="When life gets blurry, adjust your focus, not your vision.", attribution="Unknown"
- Example: quote="A crack is where the light comes in.", attribution="Rumi"

### Step A — Download Playfair Display fonts

Google Fonts ships Playfair Display only as variable fonts (`PlayfairDisplay[wght].ttf`), not as separate Bold/Regular files, so download those and apply the weight axis at render time:

```python
import urllib.request, os
from PIL import ImageFont

FONT_VAR = "/tmp/PlayfairDisplay-VAR.ttf"
FONT_VAR_ITALIC = "/tmp/PlayfairDisplay-Italic-VAR.ttf"

if not os.path.exists(FONT_VAR):
    urllib.request.urlretrieve(
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        FONT_VAR,
    )
if not os.path.exists(FONT_VAR_ITALIC):
    urllib.request.urlretrieve(
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
        FONT_VAR_ITALIC,
    )

def load_font(path, size, weight=None):
    """Load a font and apply variable-font weight axis if specified."""
    f = ImageFont.truetype(path, size)
    if weight is not None and hasattr(f, "set_variation_by_axes"):
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f
```

### Step B — Fetch background photo from Pexels Curated

```python
import urllib.request, json, random, io
from PIL import Image, ImageEnhance

def get_curated_photo(pexels_key):
    # Pexels API and CDN both reject requests without a User-Agent — always send one.
    page = random.randint(1, 8)
    url = f"https://api.pexels.com/v1/curated?per_page=80&page={page}"
    req = urllib.request.Request(url, headers={
        "Authorization": pexels_key,
        "User-Agent": "ZenieAgent/1.0",
    })
    with urllib.request.urlopen(req) as r:
        data = json.load(r)

    # High-res landscape or square only
    candidates = [p for p in data["photos"] if p["width"] >= 3000 and p["width"] >= p["height"]]
    if not candidates:
        candidates = sorted(data["photos"], key=lambda p: p["width"], reverse=True)[:10]

    photo = random.choice(candidates)
    photo_req = urllib.request.Request(photo["src"]["large2x"], headers={"User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(photo_req) as r:
        img = Image.open(io.BytesIO(r.read())).convert("RGB")

    # Center-crop to square
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((1080, 1080), Image.LANCZOS)

    # Boost vibrancy so the photo pops behind the card
    img = ImageEnhance.Color(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    return img
```

### Step C — Compose the quote image

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap, random

def make_quote_image(quote, attribution, filename, pexels_key):
    SIZE = 1080
    CARD_W, CARD_H = 730, 730
    CARD_X = (SIZE - CARD_W) // 2   # 175
    CARD_Y = (SIZE - CARD_H) // 2   # 175

    TEXT_COLOR = (52, 30, 90)        # dark purple #341E5A
    ATTR_COLOR = (100, 75, 150)      # medium purple
    CREAM = (250, 247, 241, 248)     # warm cream card, very slightly transparent

    # --- 1. Background photo (no dark overlay — photo is fully visible) ---
    bg = get_curated_photo(pexels_key).convert("RGBA")

    # --- 2. Card shadow ---
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [(CARD_X + 10, CARD_Y + 10), (CARD_X + CARD_W + 10, CARD_Y + CARD_H + 10)],
        radius=10, fill=(0, 0, 0, 55)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    bg = Image.alpha_composite(bg, shadow)

    # --- 3. Cream card ---
    card_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_layer)
    cd.rounded_rectangle(
        [(CARD_X, CARD_Y), (CARD_X + CARD_W, CARD_Y + CARD_H)],
        radius=8, fill=CREAM
    )
    bg = Image.alpha_composite(bg, card_layer)

    # --- 4. Watercolor corner decorations ---
    # Soft blobs in lavender, dusty pink, and sage that bleed off card corners
    deco = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)

    palette = [
        (180, 155, 220, 70),   # lavender
        (210, 175, 210, 60),   # mauve
        (160, 195, 180, 55),   # sage
        (220, 175, 195, 65),   # dusty pink
        (195, 170, 225, 75),   # soft purple
    ]

    def draw_corner_blobs(cx, cy):
        for _ in range(10):
            ox = cx + random.randint(-45, 45)
            oy = cy + random.randint(-45, 45)
            r = random.randint(22, 52)
            color = random.choice(palette)
            dd.ellipse([(ox - r, oy - r), (ox + r, oy + r)], fill=color)

    # Top-left corner
    draw_corner_blobs(CARD_X + 20, CARD_Y + 20)
    # Bottom-right corner
    draw_corner_blobs(CARD_X + CARD_W - 20, CARD_Y + CARD_H - 20)

    deco = deco.filter(ImageFilter.GaussianBlur(radius=10))
    bg = Image.alpha_composite(bg, deco)

    # --- 5. Text ---
    bg_rgb = bg.convert("RGB")
    draw = ImageDraw.Draw(bg_rgb)

    font_bold = load_font(FONT_VAR, 56, weight=700)
    font_attr = load_font(FONT_VAR_ITALIC, 30, weight=400)
    font_brand = load_font(FONT_VAR, 34, weight=400)

    # Quote text — centered on card, with curly quotes
    wrapped = textwrap.wrap(f'\u201c{quote}\u201d', width=24)
    line_h = 70
    text_block_h = len(wrapped) * line_h
    text_start_y = CARD_Y + (CARD_H - text_block_h) // 2 - 30

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_bold)
        lw = bbox[2] - bbox[0]
        lx = CARD_X + (CARD_W - lw) // 2
        draw.text((lx, text_start_y), line, font=font_bold, fill=TEXT_COLOR)
        text_start_y += line_h

    # Attribution — centered, below quote
    attr_text = f"\u2013{attribution}"
    ab = draw.textbbox((0, 0), attr_text, font=font_attr)
    ax = CARD_X + (CARD_W - (ab[2] - ab[0])) // 2
    draw.text((ax, text_start_y + 18), attr_text, font=font_attr, fill=ATTR_COLOR)

    # "zenie" wordmark — bottom center of card
    zb = draw.textbbox((0, 0), "zenie", font=font_brand)
    zx = CARD_X + (CARD_W - (zb[2] - zb[0])) // 2
    draw.text((zx, CARD_Y + CARD_H - 58), "zenie", font=font_brand, fill=TEXT_COLOR)

    bg_rgb.save(filename, format="JPEG", quality=95)

# Call for each quote
make_quote_image("QUOTE TEXT HERE", "Attribution Here", "quote_1.jpg", PEXELS_KEY)
make_quote_image("QUOTE TEXT HERE", "Attribution Here", "quote_2.jpg", PEXELS_KEY)
```

---

## Step 3: Push all files to GitHub using the API

```python
import urllib.request, json, base64

TOKEN = "YOUR_GITHUB_TOKEN"
REPO = "isabelhoppmann/ART-Lab-Social-Media"
DATE = "TODAYS_DATE"

def push_file(path, content_bytes, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"token {TOKEN}", "User-Agent": "agent"})
        with urllib.request.urlopen(req) as r:
            sha = json.load(r)["sha"]
    except:
        sha = None
    payload = {"message": message, "content": base64.b64encode(content_bytes).decode()}
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
        headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json", "User-Agent": "agent"},
        method="PUT")
    with urllib.request.urlopen(req) as r:
        print(f"Pushed {path}: {r.status}")
```

Push: quote_1.jpg, quote_2.jpg, meme_1.mp4, meme_2.mp4, meme_ids.txt, index.html, zenie_drafts.md

---

## Step 4: Build and push index.html

For Giphy memes use iframes. For Tenor memes use img tags with the direct .gif URL.
For quote images: add a subtle CSS Ken Burns animation (slow zoom).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Drafts — [DATE]</title>
<style>
  :root { --purple: #6B3FA0; --lavender: #C9B1E8; --pink: #F0A0C0; }
  body { font-family: -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #f5f0fa; }
  h1 { color: var(--purple); }
  .back { color: var(--purple); text-decoration: none; font-size: .9em; display: block; margin-bottom: 20px; }
  .post { background: white; border-radius: 16px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(107,63,160,.1); border-top: 3px solid var(--lavender); }
  .post h2 { font-size: .8em; text-transform: uppercase; letter-spacing: .08em; color: var(--purple); margin: 0 0 12px; }
  .giphy-wrap { width: 100%; padding-bottom: 100%; height: 0; position: relative; border-radius: 12px; overflow: hidden; margin-bottom: 12px; }
  .giphy-wrap iframe { position: absolute; width: 100%; height: 100%; border: 0; }
  .quote-wrap { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 12px; }
  .quote-wrap img { width: 100%; display: block; animation: kenburns 12s ease-in-out infinite alternate; transform-origin: center; }
  @keyframes kenburns { from { transform: scale(1); } to { transform: scale(1.06); } }
  img.meme { width: 100%; border-radius: 12px; margin-bottom: 12px; }
  .caption { margin-bottom: 6px; font-size: .95em; }
  .tags { font-size: .85em; color: var(--purple); margin-bottom: 6px; }
  .time { font-size: .8em; color: #999; }
  .btn { display: inline-block; padding: 9px 18px; background: var(--purple); color: white; border-radius: 20px; text-decoration: none; font-size: .9em; margin: 8px 0; }
  .btn:hover { background: #5a3390; }
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts — [DATE]</h1>

<div class="post">
  <h2>Meme 1</h2>
  <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID]" allowFullScreen></iframe></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Meme 2</h2>
  <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID]" allowFullScreen></iframe></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Repost 1</h2>
  <p>[CREATOR]</p><p class="caption">[CAPTION]</p>
  <a class="btn" href="[URL]" target="_blank">Watch Video</a>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Repost 2</h2>
  <p>[CREATOR]</p><p class="caption">[CAPTION]</p>
  <a class="btn" href="[URL]" target="_blank">Watch Video</a>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Quote Image 1</h2>
  <div class="quote-wrap"><img src="quote_1.jpg" alt="Quote 1"></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Quote Image 2</h2>
  <div class="quote-wrap"><img src="quote_2.jpg" alt="Quote 2"></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

</body></html>
```

---

## Step 5: Update root index.html
Fetch, decode, prepend new entry at top, remove "latest" from previous entry, push.
New entry: <a class="week latest" href="posts/[DATE]/"><span class="week-date">[Month Day, Year]</span><span class="week-arrow">→</span></a>


---

## Step 6: Save posts to Notion database

After pushing files to GitHub, save each post to the **Zenie Posts** Notion database (ID: `468afa8e-3a1a-49dd-8852-c130077221d5`) using the Notion MCP tool `notion-create-pages`.

Save 4 posts (memes and quote images only — skip reposts).

### Calculating Scheduled Dates
Each post has a recommended Best Time (e.g. "Wednesday 7–9 PM EST"). Convert this into a real ISO-8601 datetime for the coming week starting from today's date (the date you are running):
- Find the next occurrence of that weekday at the midpoint of the time range (e.g. "7–9 PM" → 20:00, "6–8 PM" → 19:00, "10 AM–12 PM" → 11:00)
- Use EST = UTC-5 offset, so add 5 hours (e.g. 8 PM EST = 01:00 next day UTC)
- Format: `YYYY-MM-DDTHH:MM:00.000+00:00`
- If the weekday has already passed this week, use next week's occurrence
- All 4 posts must be on different days

For each post, call `notion-create-pages` with parent page ID `468afa8e-3a1a-49dd-8852-c130077221d5` and these properties:

**Meme 1:**
- Name: `Meme 1 — [DATE]`
- Post Type: `Meme`
- Caption: the meme caption
- Hashtags: the meme hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_1.mp4`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE] (ISO format YYYY-MM-DD)

**Meme 2:**
- Name: `Meme 2 — [DATE]`
- Post Type: `Meme`
- Caption: the meme caption
- Hashtags: the meme hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_2.mp4`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Quote Image 1:**
- Name: `Quote 1 — [DATE]`
- Post Type: `Quote Image`
- Caption: the quote caption
- Hashtags: the quote hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/quote_1.jpg`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Quote Image 2:**
- Name: `Quote 2 — [DATE]`
- Post Type: `Quote Image`
- Caption: the quote caption
- Hashtags: the quote hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/quote_2.jpg`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

After creating all 4 rows, print: "Saved 4 posts to Notion Zenie Posts database with scheduled dates."
