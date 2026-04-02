# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

Your GitHub token, Notion token, and Pexels API key are all provided in the message that invoked you.
Notion parent page ID: 336c2cdd-459d-817f-8afa-e0ca8687306f

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS
For each meme:
1. Pick a search keyword relevant to the meme topic (e.g. "couple", "coffee", "friends laughing", "sunset", "woman thinking")
2. Search Pexels for a real photo using your Pexels API key:
   curl -s -H "Authorization: PEXELS_KEY" "https://api.pexels.com/v1/search?query=KEYWORD&per_page=5&orientation=square" | python3 -c "import sys,json; photos=json.load(sys.stdin)['photos']; print(photos[0]['src']['large2x'])"
3. Download the photo: curl -L "URL" -o bg1.jpg
4. Write the IMAGE TEXT (punchy, under 15 words, lowercase, often starts with "when")
   - Top text: white bold on black bar at top
   - Bottom text: yellow bold on black bar at bottom
5. Write the CAPTION (1 sentence, under 12 words)
6. List 5-8 HASHTAGS
7. Use Python PIL/Pillow to composite the meme:
   - Open the downloaded photo, resize to 1080x1080 (crop to square from center)
   - Add a black bar (height 160px) at top and bottom
   - Wrap and center the top text in white bold, bottom text in yellow bold
   - Use font size ~60px, wrap text so it fits within the bar width
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
1. Pick a keyword for a calm/beautiful background (e.g. "flowers", "nature", "soft light", "pastel sky")
2. Search Pexels using your Pexels API key:
   curl -s -H "Authorization: PEXELS_KEY" "https://api.pexels.com/v1/search?query=KEYWORD&per_page=5&orientation=square" | python3 -c "import sys,json; photos=json.load(sys.stdin)['photos']; print(photos[0]['src']['large2x'])"
3. Download the photo: curl -L "URL" -o bg_q1.jpg
4. Write a SHORT QUOTE (under 12 words) to overlay
5. Write a CAPTION ending with a reflective question
6. List 5-8 HASHTAGS
7. Use Python PIL:
   - Open the downloaded photo, resize/crop to 1080x1080
   - Add a semi-transparent dark overlay (RGBA 0,0,0,140)
   - Center the quote text in white italic font, large size (~70px), with word wrapping
   - Save as quote_1.png and quote_2.png

## Step 3: Save to GitHub
- Save meme_1.png, meme_2.png, quote_1.png, quote_2.png in posts/[DATE]/
- Save zenie_drafts.md summary with captions, hashtags, video URLs, posting times
- Generate posts/[DATE]/index.html (see Step 4)
- Update the root index.html (see Step 5)
- Commit all files and push to main using the GitHub API with your GitHub token

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
  .back { display: inline-block; margin-bottom: 24px; color: #5b5bd6; text-decoration: none; font-size: 0.9em; }
  .post { background: white; border-radius: 12px; padding: 20px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .post h2 { font-size: 1em; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin: 0 0 12px; }
  .post img { width: 100%; border-radius: 8px; margin-bottom: 12px; }
  .caption { font-size: 1em; margin-bottom: 8px; }
  .hashtags { font-size: 0.85em; color: #5b5bd6; margin-bottom: 8px; }
  .time { font-size: 0.8em; color: #888; }
  .video-link { display: inline-block; margin: 8px 0; padding: 8px 16px; background: #000; color: white; border-radius: 20px; text-decoration: none; font-size: 0.9em; }
  .creator { font-size: 0.85em; color: #888; margin-bottom: 6px; }
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts</h1>
<div class="date">[DATE]</div>
[POST SECTIONS]
</body>
</html>
```

Use relative image paths (just meme_1.png). Include all 6 posts with their captions, hashtags, and posting times.

## Step 5: Update Root Index
Fetch the current root index.html from GitHub, then prepend a new entry for this week at the top (and remove the "latest" class from the previous top entry). Push the updated file.

The new entry to add at the top (inside the <body>, after the subtitle div):
<a class="week latest" href="posts/[DATE]/"><span class="week-date">[FORMATTED DATE e.g. April 5, 2026]</span><span class="week-arrow">→</span></a>

Remove class "latest" from the previously newest entry.

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
