# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## ABOUT ZENIE
Zenie is a journaling app for women focused on self-reflection, personal growth, relationships, and living intentionally. The brand is warm, aspirational, and empowering — not clinical or heavy. Think: romanticizing your life, main character energy, soft life, glow-up mindset. The tone is like a wise, fun best friend. Color identity: **purple-forward** (primary: deep violet #6B3FA0, accent: soft lavender #C9B1E8, highlight: blush pink #F0A0C0).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy or Tenor GIFs. You MUST NOT generate PNG files for memes.
- QUOTE IMAGES: You MUST generate PNG files with PIL. Backgrounds MUST be real photographs from Pexels curated — never flat colors, gradients, or blurs.
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
3. Giphy embed: https://giphy.com/embed/[ID] (ID = last segment of URL after final dash)
4. Tenor: WebFetch to find direct .gif URL, embed with img tag.

Caption: one short punchy sentence, instant impact, no setup needed. 5-8 hashtags including #Zenie.

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 real TikTok/Instagram video URLs from wellness/relationships/self-growth creators.
Search: site:tiktok.com self-care OR journaling OR relationships 2026
Get: video URL, creator handle, repost caption, best time to post.

---

## Step 2C: Create 2 Quote Images

### Quotes
- SHORT: under 12 words, max 15. Must fit on 2 lines.
- TONE: aspirational, warm, fun — not heavy or clinical
- THEMES: romanticizing life, growth, self-love, confidence, intentional living
- Good: "Soft life isn't a reward. It's the whole plan."
- Good: "You're not behind. You're right on time."

### Step A — Download Playfair Display font

```python
import urllib.request, os

font_url = "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Bold.ttf"
font_path = "/tmp/PlayfairDisplay-Bold.ttf"
if not os.path.exists(font_path):
    urllib.request.urlretrieve(font_url, font_path)
```

### Step B — Fetch background photo from Pexels Curated

Use the **curated** endpoint (NOT search). Curated photos are hand-picked editorial quality — always sharp, always beautiful.

```python
import urllib.request, json, random, io
from PIL import Image

def get_curated_photo(pexels_key):
    page = random.randint(1, 8)
    url = f"https://api.pexels.com/v1/curated?per_page=80&page={page}"
    req = urllib.request.Request(url, headers={"Authorization": pexels_key})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)

    # Keep only high-res landscape or square photos (sharp source = large width)
    candidates = [p for p in data["photos"] if p["width"] >= 3000 and p["width"] >= p["height"]]
    if not candidates:
        candidates = sorted(data["photos"], key=lambda p: p["width"], reverse=True)[:10]

    photo = random.choice(candidates)
    photo_url = photo["src"]["large2x"]

    with urllib.request.urlopen(photo_url) as r:
        img = Image.open(io.BytesIO(r.read())).convert("RGB")

    # Center-crop to square
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((1080, 1080), Image.LANCZOS)
    return img
```

### Step C — Compose the quote image

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import textwrap

def make_quote_image(quote, filename, pexels_key, font_path):
    # 1. Background photo — from curated, always a real sharp photograph
    bg = get_curated_photo(pexels_key)

    # 2. Enhance photo
    bg = ImageEnhance.Contrast(bg).enhance(1.1)
    bg = ImageEnhance.Color(bg).enhance(1.15)
    bg = ImageEnhance.Sharpness(bg).enhance(1.4)
    bg = bg.convert("RGBA")

    # 3. Light overlay — photo stays dominant (~30% dark)
    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 75))
    bg = Image.alpha_composite(bg, overlay)

    # 4. Soft edge vignette only — center stays bright
    vignette = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(100):
        alpha = int(65 * (i / 100) ** 2)
        vd.rectangle([(i, i), (1080 - i, 1080 - i)], outline=(0, 0, 0, alpha))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=30))
    bg = Image.alpha_composite(bg, vignette)
    bg = bg.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # 5. Fonts — Playfair Display (elegant, premium)
    try:
        font = ImageFont.truetype(font_path, 78)
        small_font = ImageFont.truetype(font_path, 34)
    except:
        font = ImageFont.load_default()
        small_font = font

    # 6. Quote text — centered white with drop shadow
    lines = textwrap.wrap(quote, width=20)
    line_height = 95
    total_h = len(lines) * line_height
    y = (1080 - total_h) // 2 - 20

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (1080 - w) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 140))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += line_height

    # 7. Thin decorative lines above and below quote
    cx = 540
    top_y = (1080 - total_h) // 2 - 42
    draw.line([(cx - 55, top_y), (cx + 55, top_y)], fill=(255, 255, 255), width=1)
    draw.line([(cx - 55, y + 12), (cx + 55, y + 12)], fill=(255, 255, 255), width=1)

    # 8. Zenie watermark
    watermark = "✦ Zenie"
    wb = draw.textbbox((0, 0), watermark, font=small_font)
    draw.text((1080 - (wb[2] - wb[0]) - 28, 1038), watermark, font=small_font, fill=(201, 177, 232))

    bg.save(filename)

make_quote_image("YOUR QUOTE 1 HERE", "quote_1.png", PEXELS_KEY, font_path)
make_quote_image("YOUR QUOTE 2 HERE", "quote_2.png", PEXELS_KEY, font_path)
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

Push: quote_1.png, quote_2.png, meme_ids.txt, index.html, zenie_drafts.md

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
  .quote-wrap { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 12px; position: relative; }
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
  <div class="quote-wrap"><img src="quote_1.png" alt="Quote 1"></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Quote Image 2</h2>
  <div class="quote-wrap"><img src="quote_2.png" alt="Quote 2"></div>
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
