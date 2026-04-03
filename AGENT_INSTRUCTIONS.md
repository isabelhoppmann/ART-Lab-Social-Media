# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

Your GitHub token, Notion token, and Pexels API key are all provided in the message that invoked you.
Notion parent page ID: 336c2cdd-459d-817f-8afa-e0ca8687306f

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS — USE GIPHY EMBEDS, DO NOT GENERATE PNG FILES

For each meme:
1. Use WebSearch to find a relevant GIF on Giphy. Search query examples:
   - "site:giphy.com situationship"
   - "site:giphy.com self care funny"
   - "site:giphy.com relationships 2025"
   - "site:giphy.com dating meme"
2. Use WebFetch on the Giphy page URL to get the GIF's embed ID. The Giphy embed ID is the string in the URL: giphy.com/gifs/[TITLE]-[ID] — the ID is the last segment after the final dash.
3. The embed iframe for the HTML is:
   <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID]" width="100%" height="100%" frameBorder="0" class="giphy-embed" allowFullScreen></iframe></div>
4. Write a CAPTION (1 sentence, under 12 words)
5. List 5-8 HASHTAGS
6. Note the source credit: "via GIPHY"

DO NOT create meme_1.png or meme_2.png. Save the Giphy IDs to meme_ids.txt in posts/[DATE]/.

### 2 REPOST VIDEOS
For each video:
1. Use WebSearch to find a REAL existing TikTok or Instagram video URL from a creator in self-care, relationships, or wellness
2. Search: site:tiktok.com self-care OR journaling OR relationships 2026
3. Provide the actual video URL, creator handle, and a short repost caption with credit ("via @creator")

### 2 QUOTE IMAGE POSTS — GENERATE WITH PIL

For each quote image, create an actual PNG file:
1. Create a 1080x1080 image using Python PIL with a beautiful gradient background in Zenie brand colors:
   - Quote 1: soft lavender to rose gradient (#C9B1E8 to #F0A0C0)
   - Quote 2: warm peach to blush gradient (#F5C9A0 to #F0A0B8)
2. Write a SHORT inspirational QUOTE (under 12 words)
3. Overlay the quote text: white, centered, large font (~80px), word-wrapped, with a subtle shadow
4. Write a CAPTION ending with a reflective question
5. List 5-8 HASHTAGS
6. Save as quote_1.png and quote_2.png

PIL gradient + text example:
python3 << 'EOF'
from PIL import Image, ImageDraw, ImageFont
import math

img = Image.new("RGB", (1080, 1080))
draw = ImageDraw.Draw(img)
# Draw gradient
for y in range(1080):
    t = y / 1080
    r = int(201 + (240-201)*t)
    g = int(177 + (160-177)*t)
    b = int(232 + (192-232)*t)
    draw.line([(0,y),(1080,y)], fill=(r,g,b))
# Add text (wrap manually)
text = "your rest is not laziness. it is survival."
# draw centered text with wrapping...
img.save("quote_1.png")
EOF

## Step 3: Save to GitHub
- Save quote_1.png, quote_2.png, meme_ids.txt in posts/[DATE]/
- Save zenie_drafts.md summary with all captions, hashtags, Giphy IDs, video URLs, posting times
- Generate posts/[DATE]/index.html (Step 4)
- Update root index.html (Step 5)
- Commit all and push using GitHub API with your GitHub token

## Step 4: Generate HTML Preview Page
Create posts/[DATE]/index.html:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zenie Drafts — [DATE]</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #fafafa; color: #222; }
  h1 { font-size: 1.4em; margin-bottom: 4px; }
  .date { color: #888; font-size: 0.9em; margin-bottom: 32px; }
  .back { display: inline-block; margin-bottom: 24px; color: #5b5bd6; text-decoration: none; font-size: 0.9em; }
  .post { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .post h2 { font-size: 1em; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin: 0 0 12px; }
  .post img { width: 100%; border-radius: 8px; margin-bottom: 12px; }
  .giphy-wrap { width:100%; padding-bottom:100%; height:0; position:relative; border-radius:8px; overflow:hidden; margin-bottom:12px; }
  .giphy-wrap iframe { position:absolute; width:100%; height:100%; }
  .caption { font-size: 1em; margin-bottom: 8px; }
  .hashtags { font-size: 0.85em; color: #5b5bd6; margin-bottom: 8px; }
  .time { font-size: 0.8em; color: #888; }
  .video-link { display: inline-block; margin: 8px 0; padding: 8px 16px; background: #000; color: white; border-radius: 20px; text-decoration: none; font-size: 0.9em; }
  .creator { font-size: 0.85em; color: #888; margin-bottom: 6px; }
  .source { font-size: 0.75em; color: #bbb; margin-top: 4px; }
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts</h1>
<div class="date">[DATE]</div>

<div class="post">
  <h2>Meme 1</h2>
  <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID_1]" width="100%" height="100%" frameBorder="0" class="giphy-embed" allowFullScreen></iframe></div>
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
  <div class="source">via GIPHY</div>
</div>

<div class="post">
  <h2>Meme 2</h2>
  <div class="giphy-wrap"><iframe src="https://giphy.com/embed/[GIPHY_ID_2]" width="100%" height="100%" frameBorder="0" class="giphy-embed" allowFullScreen></iframe></div>
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
  <div class="source">via GIPHY</div>
</div>

<div class="post">
  <h2>Repost 1</h2>
  <div class="creator">[CREATOR HANDLE]</div>
  <div class="caption">[REPOST CAPTION]</div>
  <a class="video-link" href="[VIDEO URL]" target="_blank">Watch Video</a>
  <div class="time">Best time: [TIME]</div>
</div>

<div class="post">
  <h2>Repost 2</h2>
  <div class="creator">[CREATOR HANDLE]</div>
  <div class="caption">[REPOST CAPTION]</div>
  <a class="video-link" href="[VIDEO URL]" target="_blank">Watch Video</a>
  <div class="time">Best time: [TIME]</div>
</div>

<div class="post">
  <h2>Quote Image 1</h2>
  <img src="quote_1.png" alt="Quote 1">
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
</div>

<div class="post">
  <h2>Quote Image 2</h2>
  <img src="quote_2.png" alt="Quote 2">
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
</div>

</body>
</html>
```

## Step 5: Update Root Index
Fetch root index.html from GitHub API, prepend new week entry, remove "latest" from previous top entry, push.

New entry:
<a class="week latest" href="posts/[DATE]/"><span class="week-date">[FORMATTED DATE]</span><span class="week-arrow">→</span></a>

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
