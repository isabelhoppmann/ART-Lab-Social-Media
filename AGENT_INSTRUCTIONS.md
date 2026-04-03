# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy GIFs. You MUST NOT generate PNG files for memes.
- QUOTE IMAGES: You MUST generate PNG files with PIL.
- GITHUB PUSH: To push a file, always use PUT. If a file already exists, GET it first to retrieve its SHA, then include the SHA in the PUT body. If a file does not exist yet, omit the SHA.

---

## Step 1: Research (WebSearch)
Find 3 trending topics TODAY in relationships, dating, mental health, self-care on TikTok/X.

---

## Step 2A: Find 2 Giphy GIFs for memes

For each meme topic from Step 1:
1. Run WebSearch: "site:giphy.com [TOPIC] reaction funny"
2. Pick a result URL from giphy.com/gifs/...
3. Extract the Giphy ID — the alphanumeric code at the very end of the URL after the last dash.
   Example: giphy.com/gifs/happy-reaction-lol-AbCdEfGhIjKlMnOp → ID is AbCdEfGhIjKlMnOp
4. Write a caption (1 sentence, under 12 words) and 5-8 hashtags

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

make_quote_image("your rest is not laziness. it is survival.", "quote_1.png", (201,177,232), (240,160,192))
make_quote_image("you don't need to earn your own softness.", "quote_2.png", (245,201,160), (240,160,184))
```

Write your own quotes — these are just examples. Write captions + hashtags for each.

---

## Step 3: Push all files to GitHub using the API

For each file, use this Python pattern:

```python
import urllib.request, json, base64

TOKEN = "YOUR_GITHUB_TOKEN"  # from credentials
REPO = "isabelhoppmann/ART-Lab-Social-Media"
DATE = "2026-04-02"  # use today's actual date

def push_file(path, content_bytes, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    # Check if file exists (get SHA)
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

# Example usage:
push_file(f"posts/{DATE}/quote_1.png", open("quote_1.png","rb").read(), "Add quote_1.png")
push_file(f"posts/{DATE}/index.html", index_html_content.encode(), "Add index.html")
```

Push these files: quote_1.png, quote_2.png, meme_ids.txt, index.html, zenie_drafts.md

---

## Step 4: Build and push index.html

For memes, use Giphy iframes (NOT img tags). Template:

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
<div class="giphy-wrap"><iframe src="https://giphy.com/embed/[MEME1_GIPHY_ID]" allowFullScreen></iframe></div>
<p class="caption">[MEME1_CAPTION]</p>
<p class="tags">[MEME1_HASHTAGS]</p>
<p class="time">Best time: [MEME1_TIME]</p>
</div>

<div class="post">
<h2>Meme 2</h2>
<div class="giphy-wrap"><iframe src="https://giphy.com/embed/[MEME2_GIPHY_ID]" allowFullScreen></iframe></div>
<p class="caption">[MEME2_CAPTION]</p>
<p class="tags">[MEME2_HASHTAGS]</p>
<p class="time">Best time: [MEME2_TIME]</p>
</div>

<div class="post">
<h2>Repost 1</h2>
<p>[CREATOR1]</p><p class="caption">[REPOST1_CAPTION]</p>
<a class="btn" href="[VIDEO1_URL]" target="_blank">Watch Video</a>
<p class="time">Best time: [REPOST1_TIME]</p>
</div>

<div class="post">
<h2>Repost 2</h2>
<p>[CREATOR2]</p><p class="caption">[REPOST2_CAPTION]</p>
<a class="btn" href="[VIDEO2_URL]" target="_blank">Watch Video</a>
<p class="time">Best time: [REPOST2_TIME]</p>
</div>

<div class="post">
<h2>Quote Image 1</h2>
<img src="quote_1.png" alt="Quote 1">
<p class="caption">[QUOTE1_CAPTION]</p>
<p class="tags">[QUOTE1_HASHTAGS]</p>
<p class="time">Best time: [QUOTE1_TIME]</p>
</div>

<div class="post">
<h2>Quote Image 2</h2>
<img src="quote_2.png" alt="Quote 2">
<p class="caption">[QUOTE2_CAPTION]</p>
<p class="tags">[QUOTE2_HASHTAGS]</p>
<p class="time">Best time: [QUOTE2_TIME]</p>
</div>

</body></html>
```

---

## Step 5: Update root index.html
Fetch, decode, prepend new entry at top, remove "latest" from previous entry, push.
New entry: <a class="week latest" href="posts/[DATE]/"><span class="week-date">[Month Day, Year]</span><span class="week-arrow">→</span></a>
