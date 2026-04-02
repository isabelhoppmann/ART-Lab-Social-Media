# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

Note: Your GitHub token and any other credentials are provided in the message that invoked you.

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS
For each meme:
1. Download a background photo from Picsum using a seeded URL so it's deterministic:
   - meme_1: https://picsum.photos/seed/meme1/1080/1080
   - meme_2: https://picsum.photos/seed/meme2/1080/1080
   Download via: curl -L "https://picsum.photos/seed/meme1/1080/1080" -o bg.jpg
2. Write the IMAGE TEXT (punchy, under 15 words, lowercase, often starts with "when")
   - Top text goes on a black bar at the top in white bold font
   - Bottom text goes on a black bar at the bottom in yellow bold font
3. Write the CAPTION (1 sentence, under 12 words)
4. List 5-8 HASHTAGS
5. Use Python PIL/Pillow to composite the meme:
   - Open the Picsum photo as background (resize to 1080x1080)
   - Add a black bar (height ~160px) at top and bottom
   - Overlay top text in white, bottom text in yellow
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
1. Download a background photo from Picsum:
   - quote_1: https://picsum.photos/seed/quote1/1080/1080
   - quote_2: https://picsum.photos/seed/quote2/1080/1080
2. Write a SHORT QUOTE (under 12 words) to overlay
3. Write a CAPTION ending with a reflective question
4. List 5-8 HASHTAGS
5. Use Python PIL to create the image:
   - Open the Picsum photo as background (resize to 1080x1080)
   - Add a semi-transparent dark overlay (rgba 0,0,0,120) over the whole image
   - Overlay the quote text centered in white italic font, large size
   - Save as quote_1.png and quote_2.png

## Step 3: Save to GitHub
- Save meme_1.png, meme_2.png, quote_1.png, quote_2.png as actual image files in a folder called posts/[DATE]/
- Append a summary to zenie_drafts.md with: full image URLs (jsDelivr CDN format below), captions, hashtags, video URLs, and best time to post for each
- Commit all files and push to main using the GitHub API with the token provided to you

Image URL format to use everywhere (jsDelivr CDN — works in Notion):
https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/[filename]

## Step 4: Create Notion Preview Page
After pushing to GitHub, use the Notion MCP tool notion-create-pages to create a new page.

Parent page ID: 336c2cdd-459d-817f-8afa-e0ca8687306f
(This is the "Zenie Social Media Drafts" page — create each week's page as a child under it.)

Page title: "Zenie Drafts — [DATE]"

Use jsDelivr URLs for all images (NOT raw.githubusercontent.com):
https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/[filename]

The page content should be a visual draft board in Notion Markdown. Include:

For each MEME POST:
- Embed the image: ![meme description](https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_1.png)
- Caption text
- Hashtags
- Suggested posting time

For each QUOTE IMAGE POST:
- Embed the image: ![quote description](https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/quote_1.png)
- Caption text
- Hashtags
- Suggested posting time

For each REPOST VIDEO:
- Clickable video URL as a hyperlink
- Creator handle
- Repost caption
- Suggested posting time

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
