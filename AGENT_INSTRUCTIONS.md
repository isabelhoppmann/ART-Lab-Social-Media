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
- Commit all files and push to main using the GitHub API with your GitHub token

## Step 4: Create Notion Preview Page
After pushing to GitHub, create a Notion page using the REST API with your Notion token.

Parent page ID: 336c2cdd-459d-817f-8afa-e0ca8687306f

Image URLs (replace [DATE] with actual date):
https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_1.png

Create the page:
curl -s -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer NOTION_TOKEN" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"page_id": "336c2cdd-459d-817f-8afa-e0ca8687306f"},
    "properties": {"title": [{"text": {"content": "Zenie Drafts — [DATE]"}}]},
    "children": [BLOCKS]
  }'

Build BLOCKS as a JSON array with these block types:
- Image block: {"type":"image","image":{"type":"external","external":{"url":"IMAGE_URL"}}}
- Paragraph: {"type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"TEXT"}}]}}
- Heading: {"type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":"TEXT"}}]}}
- Divider: {"type":"divider","divider":{}}

Structure the page as:
- heading_2 "Meme 1" + image (meme_1.png CDN URL) + paragraph (caption) + paragraph (hashtags) + paragraph (best time to post)
- divider
- heading_2 "Meme 2" + image (meme_2.png CDN URL) + paragraph (caption) + paragraph (hashtags) + paragraph (best time to post)
- divider
- heading_2 "Repost 1" + paragraph (creator handle) + paragraph (repost caption) + paragraph (video URL)
- divider
- heading_2 "Repost 2" + paragraph (creator handle) + paragraph (repost caption) + paragraph (video URL)
- divider
- heading_2 "Quote 1" + image (quote_1.png CDN URL) + paragraph (caption) + paragraph (hashtags) + paragraph (best time to post)
- divider
- heading_2 "Quote 2" + image (quote_2.png CDN URL) + paragraph (caption) + paragraph (hashtags) + paragraph (best time to post)

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
