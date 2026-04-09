# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## ABOUT ZENIE
Zenie is a journaling app for women focused on self-reflection, personal growth, relationships, and living intentionally. The brand is warm, aspirational, and empowering — not clinical or heavy. Think: romanticizing your life, main character energy, soft life, glow-up mindset. The tone is like a wise, fun best friend. Color identity: **purple-forward** (primary: deep violet #6B3FA0, accent: soft lavender #C9B1E8, highlight: blush pink #F0A0C0).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy or Tenor GIFs. You MUST NOT generate PNG files for memes.
- QUOTE IMAGES: You MUST generate PNG files with PIL using Pexels photo backgrounds (not flat gradients).
- GITHUB PUSH: To push a file, always use PUT. If a file already exists, GET it first to retrieve its SHA, then include the SHA in the PUT body. If a file does not exist yet, omit the SHA.

---

## Step 1: Research trending memes (WebSearch)

Find what's trending culturally RIGHT NOW relevant to Zenie's audience (women 20-35, relationships, self-growth, dating, wellness):
1. WebSearch("trending memes relationships dating 2026 tiktok")
2. WebSearch("viral memes self care journaling april 2026")
3. WebSearch("funniest memes this week women relatable")

Identify 2-3 specific meme formats or viral moments that are trending (e.g. "delulu", "main character", "girl math", a specific reaction meme). Must feel current.

---

## Step 2A: Find 2 GIFs matching trending memes

For each meme, search for the specific trending format — NOT generic topics.

Strategy:
1. WebSearch("site:giphy.com [SPECIFIC MEME NAME OR FORMAT]")
   AND WebSearch("site:tenor.com [SPECIFIC MEME NAME OR FORMAT]")
2. **Quality check (REQUIRED):** Use WebFetch on each candidate GIF/embed page. Reject any GIF that:
   - Is blurry, pixelated, or low-resolution (under ~400px wide)
   - Is from an obscure or unrecognized source
   - Looks like clip art or has very few colors
   Only use crisp, HD-quality GIFs from recognizable meme formats or shows/films.
3. For Giphy: extract the ID from the URL end (after the last dash). Embed: https://giphy.com/embed/[ID]
4. For Tenor: use WebFetch to find the direct .gif URL. Embed with <img> tag.

Caption rules — the caption must land IMMEDIATELY (within 2 seconds of reading):
- One short, punchy sentence that states the relatable truth directly
- No setup required — the caption IS the joke or the vibe
- Tie it to journaling, self-reflection, growth, or relationships in Zenie's world
- Bad example: "When you realize your journal knows more about you than anyone" (too wordy, needs thinking)
- Good example: "Your journal: the only one you can fully be honest with 💜" (instant, clear)
- Good example: "POV: you finally said what you actually feel" (immediate, relatable)
Write 5-8 hashtags using Zenie's purple brand voice (include #Zenie, #journaling or similar).

Prioritize GIFs that are:
- HD quality, crisp and clear
- From a recognizable meme/show/film format
- Funny and relatable to women 20-35
- Currently viral or trending

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 real TikTok/Instagram video URLs from wellness/relationships/self-growth creators.
Search: site:tiktok.com self-care OR journaling OR relationships 2026
Get: video URL, creator handle, repost caption ("via @creator"), best time to post.
Keep doing what's working here — these have been landing well.

---

## Step 2C: Create 2 Quote Images with Pexels backgrounds + PIL

**Quote writing rules:**
- SHORT: ideally under 12 words, max 15. If it doesn't fit on 2 lines it's too long.
- LIGHTHEARTED: inspiring, aspirational, fun — not heavy mental health language
- Think: romanticizing life, growth, self-love, confidence — not anxiety, trauma, healing
- Bad: "It's okay to not be okay. Your pain is valid and healing takes time." (heavy, long)
- Good: "Soft life isn't a reward. It's the whole plan." (short, punchy, aspirational)
- Good: "You're not behind. You're right on time." (light, encouraging, immediate)
- Must connect to Zenie's world: journaling, self-reflection, intentional living, relationships

**Background image rules:**
- Use the Pexels API to fetch a beautiful, aspirational background image
- Search for: dreamy landscapes, golden hour, neon cityscapes, tropical settings, flowers in bloom, editorial/fashion photography, iconic travel locations, starry skies, cozy interiors — anything visually stunning and idealistic
- Pexels API: GET https://api.pexels.com/v1/search?query=[SEARCH TERM]&per_page=5&orientation=square
  Header: Authorization: {pexels_key}
- Pick the highest-quality, most visually striking result
- Download the image and resize to 1080x1080

**Search query rules — match the photo to the quote's emotional world:**
- Romanticizing life / soft life → "golden hour aesthetic dreamy soft light", "cozy morning linen editorial"
- Love / longing / relationships → "soft bokeh warm romantic light", "film grain golden sunset couple"
- Growth / new chapter / hope → "sunrise mountain misty path", "cherry blossoms spring bloom aerial"
- Confidence / glow-up → "neon city night editorial fashion", "luxury minimalist fashion editorial"
- Journaling / reflection / stillness → "cozy reading window warm candle", "notebook coffee morning light"

**PIL code:**
```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import urllib.request, textwrap, io, json, random

def make_quote_image(quote, filename, pexels_key, search_query):
    # --- 1. Fetch Pexels photo matching the quote's world ---
    url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=5&orientation=square"
    req = urllib.request.Request(url, headers={"Authorization": pexels_key})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    photo_url = data["photos"][0]["src"]["large2x"]
    with urllib.request.urlopen(photo_url) as r:
        bg = Image.open(io.BytesIO(r.read())).convert("RGB").resize((1080, 1080))

    bg = bg.convert("RGBA")

    # --- 2. Light dusky overlay — let the photo breathe, just darken bottom for text ---
    overlay = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for y in range(1080):
        t = y / 1080
        # Barely-there at top (alpha ~25), soft purple-dark at bottom (alpha ~130)
        alpha = int(25 + 105 * t)
        r_val = int(107 * (1 - t * 0.2))
        g_val = int(63 * (1 - t * 0.2))
        b_val = int(160 * (1 - t * 0.05))
        draw_ov.line([(0, y), (1080, y)], fill=(r_val, g_val, b_val, alpha))
    bg = Image.alpha_composite(bg, overlay)

    # --- 3. Bokeh glow layer — soft lavender/blush orbs like lens flare ---
    bokeh = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    bokeh_colors = [(201, 177, 232), (240, 160, 192), (255, 240, 230), (180, 160, 220)]
    for _ in range(14):
        cx = random.randint(-60, 1140)
        cy = random.randint(-60, 1140)
        radius = random.randint(40, 180)
        color = random.choice(bokeh_colors)
        alpha = random.randint(18, 52)
        bd.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*color, alpha))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(radius=42))
    bg = Image.alpha_composite(bg, bokeh)

    # --- 4. Light leak — soft warm wash from upper-left corner ---
    leak = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leak)
    for i in range(5):
        off = i * 35
        ld.polygon([(off, 0), (420 + off, 0), (0, 420 + off)], fill=(255, 245, 220, 20))
    leak = leak.filter(ImageFilter.GaussianBlur(radius=55))
    bg = Image.alpha_composite(bg, leak)

    # --- 5. Grain — stops it looking flat, adds editorial texture ---
    grain = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    gp = grain.load()
    for x in range(0, 1080, 2):
        for y in range(0, 1080, 2):
            v = 128 + random.randint(-18, 18)
            gp[x, y] = (v, v, v, 15)
    bg = Image.alpha_composite(bg, grain)

    # --- 6. Soft vignette behind text area for readability ---
    vignette = Image.new("RGBA", (1080, 1080), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    vd.rectangle([80, 310, 1000, 770], fill=(0, 0, 0, 55))
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=40))
    bg = Image.alpha_composite(bg, vignette)

    bg = bg.convert("RGB")
    draw = ImageDraw.Draw(bg)

    # --- 7. Font ---
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 82)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 40)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 82)
            small_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
        except:
            font = ImageFont.load_default()
            small_font = font

    # --- 8. Quote text centered ---
    lines = textwrap.wrap(quote, width=18)
    total_h = len(lines) * 98
    y_start = (1080 - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (1080 - w) // 2
        draw.text((x + 3, y_start + 3), line, font=font, fill=(0, 0, 0, 90))
        draw.text((x + 1, y_start + 1), line, font=font, fill=(80, 50, 120, 60))
        draw.text((x, y_start), line, font=font, fill=(255, 255, 255))
        y_start += 98

    # --- 9. Zenie watermark ---
    watermark = "✦ Zenie"
    wb = draw.textbbox((0, 0), watermark, font=small_font)
    draw.text((1080 - (wb[2] - wb[0]) - 30, 1030), watermark, font=small_font, fill=(201, 177, 232))

    bg.save(filename)

# Choose search_query based on each quote's emotional tone (see rules above)
make_quote_image("YOUR QUOTE 1 HERE", "quote_1.png", PEXELS_KEY, "golden hour dreamy soft light aesthetic")
make_quote_image("YOUR QUOTE 2 HERE", "quote_2.png", PEXELS_KEY, "neon city night editorial fashion")
```

---

## Step 3: Push all files to GitHub using the API

```python
import urllib.request, json, base64

TOKEN = "YOUR_GITHUB_TOKEN"
REPO = "isabelhoppmann/ART-Lab-Social-Media"
DATE = "TODAYS_DATE"  # e.g. 2026-04-05

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
For quote images: add a subtle CSS Ken Burns animation (slow zoom) on the image in the preview to give a "moving parts" feel.

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
  <!-- If Giphy: -->
  <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID]" allowFullScreen></iframe></div>
  <!-- If Tenor: <img class="meme" src="[TENOR_DIRECT_GIF_URL]" alt="Meme 1"> -->
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
