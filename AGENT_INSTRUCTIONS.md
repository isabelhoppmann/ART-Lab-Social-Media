# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy or Tenor GIFs. You MUST NOT generate PNG files for memes.
- QUOTE IMAGES: You MUST generate PNG files with PIL.
- GITHUB PUSH: To push a file, always use PUT. If a file already exists, GET it first to retrieve its SHA, then include the SHA in the PUT body. If a file does not exist yet, omit the SHA.

---

## Step 1: Research trending memes (WebSearch)

First find what's trending culturally RIGHT NOW:
1. WebSearch("trending memes relationships dating 2026 tiktok")
2. WebSearch("viral memes self care mental health april 2026")
3. WebSearch("funniest memes this week relationships")

Identify 2-3 specific meme formats or viral moments that are trending (e.g. "delulu", "soft life era", "girl math", a specific reaction meme). These should feel current and culturally relevant to Zenie's audience (women, relationships, self-growth, dating).

---

## Step 2A: Find 2 GIFs matching trending memes

For each meme, use the specific trending meme name/format to search — NOT generic topics.

Strategy:
1. WebSearch("site:giphy.com [SPECIFIC MEME NAME OR FORMAT]")
   AND
   WebSearch("site:tenor.com [SPECIFIC MEME NAME OR FORMAT]")
2. Pick whichever result looks more on-trend and funny
3. For Giphy: extract the ID from the end of the URL (after the last dash)
   Example: giphy.com/gifs/reaction-omg-AbCdEfGhIjKlMnOp → ID is AbCdEfGhIjKlMnOp
   Embed: https://giphy.com/embed/[ID]
4. For Tenor: use WebFetch on the Tenor page to find the direct .gif URL or embed URL
   Tenor direct GIF URLs look like: https://media.tenor.com/[hash]/[name].gif
   Embed: use an <img> tag with the direct .gif URL
5. Write a caption that ties the GIF to Zenie's theme (relationships, self-care, growth)
6. Write 5-8 hashtags

Prioritize GIFs that are:
- From a recognizable meme format (reaction memes, character memes, show clips)
- Funny and relatable to women aged 20-35
- Currently viral or trending — not generic clip art reactions

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 real TikTok/Instagram video URLs from wellness/relationships creators.
Search: site:tiktok.com self-care OR journaling OR relationships 2026
Get: video URL, creator handle, repost caption ("via @creator"), best time to post.

---

## Step 2C: Create 2 Quote Images with PIL

```python
from PIL import Image, ImageDraw, ImageFont
import textwrap

def make_quote_image(quote, filename, c1, c2):
    img = Image.new("RGB", (1080, 1080))
    draw = ImageDraw.Draw(img)
    for y in range(1080):
        t = y / 1080
        r, g, b = [int(c1[i] + (c2[i]-c1[i])*t) for i in range(3)]
        draw.line([(0,y),(1080,y)], fill=(r,g,b))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 80)
    except:
        font = ImageFont.load_default()
    lines = textwrap.wrap(quote, width=20)
    total_h = len(lines) * 100
    y = (1080 - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0,0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((1080-w)//2, y), line, font=font, fill=(255,255,255))
        y += 100
    img.save(filename)

make_quote_image("YOUR QUOTE HERE", "quote_1.png", (201,177,232), (240,160,192))
make_quote_image("YOUR QUOTE HERE", "quote_2.png", (245,201,160), (240,160,184))
```

Write original inspirational quotes for Zenie's audience. Add captions + hashtags.

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

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Drafts — [DATE]</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:700px;margin:0 auto;padding:20px;background:#fafafa}
.back{color:#5b5bd6;text-decoration:none;font-size:.9em;display:block;margin-bottom:20px}
.post{background:white;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.post h2{font-size:.85em;text-transform:uppercase;letter-spacing:.05em;color:#888;margin:0 0 12px}
.giphy-wrap{width:100%;padding-bottom:100%;height:0;position:relative;border-radius:8px;overflow:hidden;margin-bottom:12px}
.giphy-wrap iframe{position:absolute;width:100%;height:100%;border:0}
img{width:100%;border-radius:8px;margin-bottom:12px}
.caption{margin-bottom:6px}
.tags{font-size:.85em;color:#5b5bd6;margin-bottom:6px}
.time{font-size:.8em;color:#888}
.btn{display:inline-block;padding:8px 16px;background:#000;color:white;border-radius:20px;text-decoration:none;font-size:.9em;margin:8px 0}
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts — [DATE]</h1>

<div class="post">
<h2>Meme 1</h2>
<!-- If Giphy: -->
<div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID]" allowFullScreen></iframe></div>
<!-- If Tenor: -->
<!-- <img src="[TENOR_DIRECT_GIF_URL]" alt="Meme 1"> -->
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
<img src="quote_1.png" alt="Quote 1">
<p class="caption">[CAPTION]</p>
<p class="tags">[HASHTAGS]</p>
<p class="time">Best time: [TIME]</p>
</div>

<div class="post">
<h2>Quote Image 2</h2>
<img src="quote_2.png" alt="Quote 2">
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
