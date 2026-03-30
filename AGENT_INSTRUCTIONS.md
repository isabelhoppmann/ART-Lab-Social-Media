# Zenie Agent Instructions

You prepare ACTUAL ready-to-post content for Zenie (@heyzenie). Do not describe what to make. Actually make it.

## Step 1: Research
Use WebSearch to find trending topics TODAY in relationships, dating, mental health, and self-care on TikTok and X. Identify the top 3 trends with specific examples.

## Step 2: Create 6 Posts

### 2 MEME POSTS
For each meme:
1. Use WebFetch to get a real image URL from Unsplash. Fetch https://unsplash.com/s/photos/[relevant-keyword] and extract an actual image src URL from the HTML.
2. Write the IMAGE TEXT (punchy, under 15 words, lowercase, often starts with "when")
3. Write the CAPTION (1 sentence, under 12 words)
4. List 5-8 HASHTAGS
5. Use Python PIL/Pillow to create the actual meme image: download the Unsplash photo, overlay the text, save as meme_1.png and meme_2.png in the repo

### 2 REPOST VIDEOS
For each video:
1. Use WebSearch to find a REAL existing TikTok or Instagram video (not a description, an actual URL) from a creator in self-care, relationships, or wellness that fits Zenie audience
2. Search queries like: site:tiktok.com self-care OR relationships OR journaling 2026
3. Provide the ACTUAL VIDEO URL that can be clicked and watched
4. Provide the CREATOR HANDLE
5. Write a short REPOST CAPTION with credit ("via @creator")

### 2 QUOTE IMAGE POSTS
For each quote image:
1. Fetch https://unsplash.com/s/photos/flowers or similar and extract a real image URL
2. Write a SHORT QUOTE (under 12 words) to overlay
3. Write a CAPTION ending with a reflective question
4. List 5-8 HASHTAGS
5. Use Python PIL to create the actual image with quote text overlaid, save as quote_1.png and quote_2.png

## Step 3: Save Everything
- Save meme_1.png, meme_2.png, quote_1.png, quote_2.png as actual image files in a folder called posts/[DATE]/
- Append a summary to zenie_drafts.md with: full raw GitHub image URLs (format: https://raw.githubusercontent.com/isabelhoppmann/ART-Lab-Social-Media/main/posts/[DATE]/[filename]), captions, hashtags, video URLs, and best time to post for each
- Commit all files and push to main

## Git Setup
git config user.email agent@zenie.ai
git config user.name ZenieAgent
Commit message: Add Zenie posts [DATE]
