# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

Your GitHub token, Notion token, and Pexels API key are all provided in the message that invoked you.
Notion parent page ID: 336c2cdd-459d-817f-8afa-e0ca8687306f

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS
Do NOT try to generate meme images with PIL. Instead, find REAL existing memes or GIFs from the internet.

For each meme:
1. Use WebSearch to find a real, shareable meme image or GIF that fits the trend. Good search queries:
   - "situationship meme gif site:giphy.com"
   - "self care meme funny site:tenor.com"
   - "relationships funny meme 2026 site:reddit.com"
   - Search for the trend topic + "meme" or "gif"
2. Use WebFetch on the result page to extract the direct image/GIF URL (a URL ending in .gif, .jpg, .png, or a Giphy/Tenor embed URL)
3. Write a CAPTION (1 sentence, under 12 words) to go with it
4. List 5-8 HASHTAGS
5. Note the best time to post

For Giphy: the embed URL format is https://media.giphy.com/media/[ID]/giphy.gif
For Tenor: use the direct .gif URL from the page source

Save meme_1_url.txt and meme_2_url.txt with the image URLs (used in Step 4 HTML).
Do NOT create meme_1.png or meme_2.png.

### 2 REPOST VIDEOS
For each video:
1. Use WebSearch to find a REAL existing TikTok or Instagram video (not a description, an actual URL) from a creator in self-care, relationships, or wellness that fits Zenie audience
2. Search queries like: site:tiktok.com self-care OR relationships OR journaling 2026
3. Provide the ACTUAL VIDEO URL that can be clicked and watched
4. Provide the CREATOR HANDLE
5. Write a short REPOST CAPTION with credit ("via @creator")

### 2 QUOTE IMAGE POSTS
For each quote image, create an actual image file with Python:
1. Download a photo from Pexels using Python urllib (NOT curl):

python3 << 'EOF'
import urllib.request, json, sys

PEXELS_KEY = "YOUR_PEXELS_KEY"  # replace with key from your credentials
keyword = "flowers"  # change per quote topic

req = urllib.request.Request(
    f"https://api.pexels.com/v1/search?query={keyword}&per_page=3&orientation=square",
    headers={"Authorization": PEXELS_KEY}
)
with urllib.request.urlopen(req, timeout=15) as r:
    data = json.load(r)
    url = data["photos"][0]["src"]["large2x"]
    print(url)

photo_req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(photo_req, timeout=30) as r:
    with open("bg_q1.jpg", "wb") as f:
        f.write(r.read())
print("Downloaded")
EOF

2. Write a SHORT QUOTE (under 12 words) to overlay
3. Write a CAPTION ending with a reflective question
4. List 5-8 HASHTAGS
5. Use Python PIL:
   - Open the downloaded photo, resize/crop to 1080x1080
   - Add a semi-transparent dark overlay (RGBA 0,0,0,150)
   - Center the quote text in white font, size ~70px, with word wrapping
   - Save as quote_1.png and quote_2.png

If Pexels download fails, fall back to a clean gradient:
- Create a 1080x1080 image with a soft gradient (e.g. lavender #E8D5F5 to pink #F5D5E8)
- Overlay the quote text centered in white

## Step 3: Save to GitHub
- Save quote_1.png and quote_2.png in posts/[DATE]/
- Save meme_1_url.txt and meme_2_url.txt in posts/[DATE]/
- Save zenie_drafts.md summary
- Generate posts/[DATE]/index.html (see Step 4)
- Update root index.html (see Step 5)
- Commit all files and push using GitHub API with your GitHub token

## Step 4: Generate HTML Preview Page
Create posts/[DATE]/index.html. For memes, use the external URLs. For quote images, use relative paths.

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
  .caption { font-size: 1em; margin-bottom: 8px; }
  .hashtags { font-size: 0.85em; color: #5b5bd6; margin-bottom: 8px; }
  .time { font-size: 0.8em; color: #888; }
  .video-link { display: inline-block; margin: 8px 0; padding: 8px 16px; background: #000; color: white; border-radius: 20px; text-decoration: none; font-size: 0.9em; }
  .creator { font-size: 0.85em; color: #888; margin-bottom: 6px; }
  .meme-source { font-size: 0.75em; color: #bbb; margin-top: 4px; }
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts</h1>
<div class="date">[DATE]</div>

<div class="post">
  <h2>Meme 1</h2>
  <img src="[MEME_1_EXTERNAL_URL]" alt="Meme 1">
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
</div>

<div class="post">
  <h2>Meme 2</h2>
  <img src="[MEME_2_EXTERNAL_URL]" alt="Meme 2">
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
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
Fetch root index.html from GitHub API, add new week entry at top, remove "latest" class from previous top entry, push updated file.

New entry format:
<a class="week latest" href="posts/[DATE]/"><span class="week-date">[FORMATTED DATE]</span><span class="week-arrow">→</span></a>

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
