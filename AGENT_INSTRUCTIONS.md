# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

Note: Your GitHub token and any other credentials are provided in the message that invoked you.

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS
For each meme:
1. Download a background photo from Picsum using the DATE in the seed so photos change each week:
   - meme_1: https://picsum.photos/seed/[DATE]-meme1/1080/1080
   - meme_2: https://picsum.photos/seed/[DATE]-meme2/1080/1080
   Replace [DATE] with today's date (e.g. 2026-04-05).
   Download via: curl -L "https://picsum.photos/seed/2026-04-05-meme1/1080/1080" -o bg1.jpg
   IMPORTANT: After downloading, check the image isn't abstract/dark. If it is, try a different seed like [DATE]-meme1b or use a specific photo ID from this list of good meme backgrounds: 1015, 1020, 1047, 64, 106, 338, 396, 452, 490, 539.
   Example with specific ID: curl -L "https://picsum.photos/id/1015/1080/1080" -o bg1.jpg
2. Write the IMAGE TEXT (punchy, under 15 words, lowercase, often starts with "when")
   - Top text goes on a black bar at the top in white bold font
   - Bottom text goes on a black bar at the bottom in yellow bold font
3. Write the CAPTION (1 sentence, under 12 words)
4. List 5-8 HASHTAGS
5. Use Python PIL/Pillow to composite the meme:
   - Open the downloaded photo as background (resize to 1080x1080)
   - Add a black bar (height ~160px) at top and bottom
   - Overlay top text in white bold, bottom text in yellow bold
   - Save as meme_1.png and meme_2.png

### 2 REPOST VIDEOS
For each video:
1. Use WebSearch to find a REAL existing TikTok or Instagram video (not a description, an actual URL) from a creator in self-care, relationships, or wellness that fits Zenie audience
2. Search queries like: site:tiktok.com self-care OR relationships OR journaling 2026
3. Provide the ACTUAL VIDEO URL that can be clicked and watched
4. Provide the CREATOR HANDLE
5. Write a short REPOST CAPTION with credit ("via @creator")

### 2 QUOTE IMAGE POSTS
For each quote image:
1. Download a background photo from Picsum using the DATE in the seed:
   - quote_1: https://picsum.photos/seed/[DATE]-quote1/1080/1080
   - quote_2: https://picsum.photos/seed/[DATE]-quote2/1080/1080
   Good specific IDs for quote backgrounds (nature/soft): 1043, 1054, 1060, 1074, 1080, 15, 25, 63, 177, 240.
2. Write a SHORT QUOTE (under 12 words) to overlay
3. Write a CAPTION ending with a reflective question
4. List 5-8 HASHTAGS
5. Use Python PIL to create the image:
   - Open the downloaded photo as background (resize to 1080x1080)
   - Add a semi-transparent dark overlay (rgba 0,0,0,140) over the whole image
   - Overlay the quote text centered in white italic font, large size
   - Save as quote_1.png and quote_2.png

## Step 3: Save to GitHub
- Save meme_1.png, meme_2.png, quote_1.png, quote_2.png in posts/[DATE]/
- Save zenie_drafts.md summary with captions, hashtags, video URLs, posting times
- Generate posts/[DATE]/index.html (see Step 4)
- Commit all files and push to main using the GitHub API with the token provided to you

## Step 4: Generate HTML Preview Page
Create posts/[DATE]/index.html with this structure (fill in real content):

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
  .post { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .post h2 { font-size: 1em; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin: 0 0 12px; }
  .post img { width: 100%; border-radius: 8px; margin-bottom: 12px; }
  .caption { font-size: 1em; margin-bottom: 8px; }
  .hashtags { font-size: 0.85em; color: #5b5bd6; margin-bottom: 8px; }
  .time { font-size: 0.8em; color: #888; }
  .video-link { display: inline-block; margin: 8px 0; padding: 8px 16px; background: #000; color: white; border-radius: 20px; text-decoration: none; font-size: 0.9em; }
  .creator { font-size: 0.85em; color: #888; margin-bottom: 6px; }
  a { color: inherit; }
</style>
</head>
<body>
<h1>Zenie Drafts</h1>
<div class="date">[DATE]</div>

<div class="post">
  <h2>Meme 1</h2>
  <img src="meme_1.png" alt="Meme 1">
  <div class="caption">[CAPTION]</div>
  <div class="hashtags">[HASHTAGS]</div>
  <div class="time">Best time: [TIME]</div>
</div>

<div class="post">
  <h2>Meme 2</h2>
  <img src="meme_2.png" alt="Meme 2">
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

Replace all [PLACEHOLDERS] with actual content. Use relative paths for images (just meme_1.png, not full URLs).

After pushing, the page will be live at:
https://isabelhoppmann.github.io/ART-Lab-Social-Media/posts/[DATE]/

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
