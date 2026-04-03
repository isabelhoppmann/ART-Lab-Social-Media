# Zenie Agent Instructions

Credentials are in the message that invoked you (GitHub token, Notion token, Pexels key).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: You MUST embed Giphy GIFs. You MUST NOT generate PNG files for memes.
- QUOTE IMAGES: You MUST generate PNG files with PIL.
- DO NOT skip any step.

---

## Step 1: Research (WebSearch)
Find 3 trending topics TODAY in relationships, dating, mental health, self-care on TikTok/X.

---

## Step 2A: Find 2 Giphy GIFs for memes

For each meme topic from Step 1:
1. Run: WebSearch("site:giphy.com [TOPIC] reaction funny 2025")
2. Pick a result URL from giphy.com/gifs/...
3. Extract the Giphy ID — it's the alphanumeric code at the end of the slug after the last dash.
   Example: giphy.com/gifs/reaction-funny-lol-AbCdEfGhIjKlMnOp → ID is AbCdEfGhIjKlMnOp
4. Write a caption for this GIF (1 sentence, under 12 words)
5. Write 5-8 hashtags

Save results to posts/[DATE]/meme_ids.txt:
```
MEME1_ID=AbCdEfGhIjKlMnOp
MEME1_CAPTION=when you finally set a boundary and mean it
MEME1_HASHTAGS=#boundaries #selfcare #heyzenie
MEME1_TIME=Wednesday 7-9pm EST
MEME2_ID=XyZaBcDeFgHiJkLm
MEME2_CAPTION=situationship era is officially over
MEME2_HASHTAGS=#situationship #heyzenie
MEME2_TIME=Friday 6-8pm EST
```

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 real TikTok/Instagram video URLs from wellness/relationships creators.
Search: site:tiktok.com self-care OR journaling OR relationships 2026
Save: video URL, creator handle, repost caption ("via @creator").

---

## Step 2C: Create 2 Quote Images with PIL

For each quote image:
1. Create a 1080x1080 gradient image:
   - Quote 1: lavender to rose (#C9B1E8 → #F0A0C0)
   - Quote 2: peach to blush (#F5C9A0 → #F0A0B8)
2. Overlay a short inspirational quote (under 12 words), centered, white text, ~80px font, word-wrapped
3. Save as quote_1.png and quote_2.png in posts/[DATE]/
4. Write a caption ending with a reflective question + 5-8 hashtags

Python PIL template:
```python
from PIL import Image, ImageDraw
img = Image.new("RGB", (1080, 1080))
draw = ImageDraw.Draw(img)
c1, c2 = (201,177,232), (240,160,192)  # lavender to rose
for y in range(1080):
    t = y/1080
    r,g,b = [int(c1[i]+(c2[i]-c1[i])*t) for i in range(3)]
    draw.line([(0,y),(1080,y)], fill=(r,g,b))
# add centered wrapped text here
img.save("quote_1.png")
```

---

## Step 3: Build index.html

Create posts/[DATE]/index.html. For memes use Giphy iframes (NOT img tags):

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
<div class="giphy-wrap"><iframe src="https://giphy.com/embed/[MEME1_ID]" allowFullScreen></iframe></div>
<p class="caption">[MEME1_CAPTION]</p>
<p class="tags">[MEME1_HASHTAGS]</p>
<p class="time">Best time: [MEME1_TIME]</p>
</div>

<div class="post">
<h2>Meme 2</h2>
<div class="giphy-wrap"><iframe src="https://giphy.com/embed/[MEME2_ID]" allowFullScreen></iframe></div>
<p class="caption">[MEME2_CAPTION]</p>
<p class="tags">[MEME2_HASHTAGS]</p>
<p class="time">Best time: [MEME2_TIME]</p>
</div>

<div class="post">
<h2>Repost 1</h2>
<p>[CREATOR1]</p>
<p class="caption">[REPOST1_CAPTION]</p>
<a class="btn" href="[VIDEO1_URL]" target="_blank">Watch Video</a>
<p class="time">Best time: [REPOST1_TIME]</p>
</div>

<div class="post">
<h2>Repost 2</h2>
<p>[CREATOR2]</p>
<p class="caption">[REPOST2_CAPTION]</p>
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

## Step 4: Push all files to GitHub
Push to posts/[DATE]/: meme_ids.txt, quote_1.png, quote_2.png, index.html, zenie_drafts.md
Use GitHub API with your GitHub token.

---

## Step 5: Update root index.html
Fetch https://api.github.com/repos/isabelhoppmann/ART-Lab-Social-Media/contents/index.html
Decode, prepend new entry, remove "latest" from previous top, re-encode, push.
New entry: <a class="week latest" href="posts/[DATE]/"><span class="week-date">[MONTH DAY, YEAR]</span><span class="week-arrow">→</span></a>
