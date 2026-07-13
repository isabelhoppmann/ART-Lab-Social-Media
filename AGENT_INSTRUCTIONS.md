# Zenie Agent Instructions

The only credential you need is the Gmail account (to email the finished bundle in Step 8) — it is in the message that invoked you. Notion is handled through the connected Notion MCP tool (no token needed). You do NOT need a GitHub token (you only read the public repo) or a Pexels key (quote images render on the GitHub runner — see Step 2C).

## ABOUT ZENIE
Zenie is a journaling app for women focused on self-reflection, personal growth, relationships, and living intentionally. The brand is warm, aspirational, and empowering — not clinical or heavy. Think: romanticizing your life, main character energy, soft life, glow-up mindset. The tone is like a wise, fun best friend. Color identity: **purple-forward** (primary: deep violet #6B3FA0, accent: soft lavender #C9B1E8, highlight: blush pink #F0A0C0).

## CRITICAL RULES — DO NOT VIOLATE
- MEMES: Do NOT source from Giphy/Tenor/Pexels and do NOT render meme MP4s yourself. Pick TWO distinct meme formats from the vetted library (Step 2A), obeying the no-repeat rule (never reuse a slug in `meme_library/used.json`). Write each meme's `overlay_text` + captions, set its `meme_slug`, and ship it with `skipped=true` + `media_url=null` in review-state (Step 7). The `post-social-to-slack` GitHub Action renders `meme_library/clips/<meme_slug>.mp4` with your overlay (white-card style), fills `media_url`, marks the slug used, creates the Notion row, and posts it. You MUST NOT generate static PNGs or placeholder memes.
  - SAFETY NET (do not fight it): rendering happens on the Action's open-internet runner (`.github/scripts/regenerate_memes.py`), not here. Just ship each meme cleanly with a real `meme_slug` + `overlay_text`. Only mark a meme genuinely SKIPPED if the library has fewer than 2 available (unused) clips — then note in the Slack handoff that the library needs new clips.
- QUOTE IMAGES: Follow the exact design spec in Step 2C. The card-on-photo format is non-negotiable.
- EXPLICIT CONTENT: All GIFs, images, and content must be 100% family-friendly. Absolutely NO nudity, sexual activity, sexual references, expletives, or adult content. Reject and replace immediately. Zero exceptions.
- PUBLISHING: You do NOT push to GitHub (your sandbox can't — api.github.com returns `502 builtin injection failed`). You collect every output file into one BUNDLE and EMAIL it in Step 8; a GitHub Action publishes it. Never call api.github.com.
- **RUN ROBUSTNESS — READ FIRST (added 2026-07-13 after three silent, output-less runs). Your #1 obligation is to REACH Step 8 and email something. A run that produces nothing is the worst outcome. Enforce all of the following:**
  - **At the very start of your Python, run `import socket; socket.setdefaulttimeout(25)` so no network call can ever hang the run.** This is mandatory.
  - **Every step before Step 8 is BEST-EFFORT.** Wrap each step in `try/except`. If a step fails, times out, or its data is unavailable: log one line, skip that piece, and CONTINUE. Never let any pre-Step-8 step abort the run.
  - **Never retry a network call more than once.** No loops that keep hitting an API/search until success — one retry max, then move on with what you have.
  - **Step 0 (Instagram/Facebook performance data) is optional context only.** If the Graph API errors or times out (e.g. an expired Meta token), skip it entirely and proceed — do NOT retry or block on it.
  - **Partial output is a SUCCESS.** If you produced e.g. the quotes but had to skip a meme, still go to Step 8 and email the BUNDLE with what you have (mark the missing piece SKIPPED). Only if you produced literally zero usable files, send the error alert instead of the bundle.

---

## Step 0: Pull performance data from Instagram and Facebook

Before drafting anything, pull the last 8 weeks of post performance from both platforms. This shapes every content decision in Steps 1–2.

Read `.env` (or accept token from the invoking message) for `PAGE_ACCESS_TOKEN`, `IG_USER_ID`, `FB_PAGE_ID`.

```python
import urllib.request, urllib.parse, json, os
from datetime import datetime, timezone

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IG_USER_ID = "17841465217874624"
FB_PAGE_ID = "227999857070404"
API_BASE = "https://graph.facebook.com/v21.0"

def api_get(path, params):
    params["access_token"] = PAGE_ACCESS_TOKEN
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    req = urllib.request.Request(
        f"{API_BASE}/{path}?{qs}",
        headers={"User-Agent": "ZenieAgent/1.0"}
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)

# --- Instagram: recent media + engagement ---
ig_posts = []
try:
    media = api_get(f"{IG_USER_ID}/media", {
        "fields": "id,media_type,timestamp,like_count,comments_count,caption",
        "limit": "30"
    })
    for post in media.get("data", []):
        saved = reach = 0
        try:
            ins = api_get(f"{post['id']}/insights", {"metric": "reach,saved"})
            for m in ins.get("data", []):
                if m["name"] == "reach":
                    reach = m["values"][0]["value"]
                elif m["name"] == "saved":
                    saved = m["values"][0]["value"]
        except Exception:
            pass
        post["reach"] = reach
        post["saved"] = saved
        post["eng_rate"] = round(
            (post.get("like_count", 0) + post.get("comments_count", 0) + saved) / max(reach, 1) * 100, 2
        )
        ig_posts.append(post)
except Exception as e:
    print(f"IG fetch failed: {e}")

# --- Facebook: recent posts + engagement ---
fb_posts = []
try:
    posts = api_get(f"{FB_PAGE_ID}/posts", {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
        "limit": "30"
    })
    for post in posts.get("data", []):
        likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = post.get("shares", {}).get("count", 0)
        reach = 0
        try:
            ins = api_get(f"{post['id']}/insights", {"metric": "post_impressions_unique"})
            for m in ins.get("data", []):
                if m["name"] == "post_impressions_unique":
                    reach = m["values"][0]["value"]
        except Exception:
            pass
        post["likes_count"] = likes
        post["comments_count"] = comments
        post["shares_count"] = shares
        post["reach"] = reach
        post["eng_rate"] = round(
            (likes + comments + shares * 2) / max(reach, 1) * 100, 2
        )
        fb_posts.append(post)
except Exception as e:
    print(f"FB fetch failed: {e}")

# --- Summarize into a Performance Brief ---
print("\n=== PERFORMANCE BRIEF ===")

if ig_posts:
    ig_sorted = sorted(ig_posts, key=lambda p: p["eng_rate"], reverse=True)
    print("\nTop 5 IG posts by engagement rate:")
    for p in ig_sorted[:5]:
        caption_preview = (p.get("caption") or "")[:80].replace("\n", " ")
        print(f"  [{p['media_type']}] {p['timestamp'][:10]} | eng_rate={p['eng_rate']}% | saves={p['saved']} | \"{caption_preview}\"")
    # Aggregate by type
    by_type = {}
    for p in ig_posts:
        t = p["media_type"]
        by_type.setdefault(t, []).append(p["eng_rate"])
    for t, rates in by_type.items():
        print(f"  Avg eng_rate {t}: {round(sum(rates)/len(rates),2)}%")
else:
    print("IG: no data retrieved (check token permissions)")

if fb_posts:
    fb_sorted = sorted(fb_posts, key=lambda p: p["eng_rate"], reverse=True)
    print("\nTop 5 FB posts by engagement rate:")
    for p in fb_sorted[:5]:
        msg_preview = (p.get("message") or "")[:80].replace("\n", " ")
        print(f"  {p['created_time'][:10]} | eng_rate={p['eng_rate']}% | shares={p['shares_count']} | \"{msg_preview}\"")
else:
    print("FB: no data retrieved (check token permissions)")

print("\nUse this brief to guide content selection in Steps 1–2.")
print("=========================\n")
```

**What to do with the brief:**
- Identify which content types (Reels/memes vs quote images) get higher engagement on each platform
- Note which themes/topics appeared in high-performing captions (journaling? relationships? dating humor?)
- Note which post types get more saves on IG (saves = algorithm signal) vs more shares on FB (shares = reach signal)
- If data is sparse (< 5 posts), skip analysis and rely on best practices: IG rewards saves + Reels plays, FB rewards shares + longer conversational copy

---

## Step 1: Research trending memes (WebSearch)

Find what's trending culturally RIGHT NOW relevant to Zenie's audience (women 20-35, relationships, self-growth, dating, wellness):
1. WebSearch("trending memes relationships dating 2026 tiktok")
2. WebSearch("viral memes self care journaling april 2026")
3. WebSearch("funniest memes this week women relatable")

Identify 2-3 specific meme formats or viral moments that are trending. Must feel current.

**Use the Performance Brief from Step 0 to weight your choices:** if memes outperformed quote images on IG last month, lean into meme themes; if certain topics (e.g. journaling, dating) drove higher saves, prioritize those themes. If FB data shows certain content drove more shares, note that for FB caption writing in Step 2.

---

## Step 2A: Choose 2 meme formats from the vetted library

**THIS REPLACES ALL GIF SOURCING.** Do NOT search Giphy/Tenor, do NOT download or render memes, and IGNORE everything below in this section as well as Step 2A-PEXELS and Step 2A.5 — those are legacy and no longer apply. Memes now come from a curated, pre-vetted, watermark-free clip library committed in the repo, and GitHub Actions renders them automatically after you publish (you can't reach the media CDNs from here anyway).

Do this instead:

1. Fetch the library and the no-repeat ledger:
```python
import urllib.request, json
def _raw(p):
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        "https://raw.githubusercontent.com/isabelhoppmann/ART-Lab-Social-Media/main/" + p,
        headers={"User-Agent": "ZenieAgent/1.0"})).read())
lib  = _raw("meme_library/library.json")["clips"]   # each: slug, title, vibes[], use_when, example_overlay
used = {u["slug"] for u in _raw("meme_library/used.json").get("used", [])}
available = [c for c in lib if c["slug"] not in used]
```
2. From `available` ONLY, pick the TWO clips whose `vibes`/`use_when` best fit your two trending meme ideas this week. The two MUST be different slugs. Read each chosen clip's `example_overlay` for tone.
   - **THE CLIP AND THE JOKE MUST ALIGN — the clip has to DEPICT the joke's scenario, not just match its "energy" (REQUIRED, Isabel's rule).** A viewer should look at the footage and see the situation the caption describes. Correct: a journaling joke → a journaling/notebook clip; an "I'm fine but not fine" joke → a clip of someone visibly cracking/sweating (e.g. `fake_smile`, `this_is_fine`, `dead_inside_stare`); a texting joke → a clip of someone on their phone (e.g. `kermit_typing`). WRONG: pairing a sweating or shifty-eyes clip with a texting joke just because the anxious energy matches. If no available clip depicts your meme idea, change the joke/topic to fit a clip that does — alignment beats any pre-decided caption.
3. **NO-REPEAT RULE (critical):** never pick a slug listed in `used` — a format may be used only ONCE, ever, even with a different caption. If `available` has fewer than 2 clips, cover only the meme(s) you can and note in the Slack handoff that the meme library is running low and needs new clips added. Never reuse a used clip.
4. Record each meme's chosen slug (you'll write it to review-state as `meme_slug` in Step 7). Then write the FOUR pieces of copy described just below, making the joke fit BOTH the chosen clip's energy and this week's topic. After that, go straight to Step 2B — skip Step 2A-PEXELS and Step 2A.5 entirely.

---

<details><summary>LEGACY GIF-sourcing steps (IGNORED — kept for reference only)</summary>

For each meme, search for the specific trending format:
1. WebSearch("site:giphy.com [SPECIFIC MEME NAME]") AND WebSearch("site:tenor.com [SPECIFIC MEME NAME]")
2. **Real humans only (REQUIRED):** GIFs must feature real people in real footage — no illustrations, cartoons, drawings, animations, anime, or CGI characters. If it's not a real human being filmed, reject it and find another.
3. **Logo/watermark check (REQUIRED — ZERO TOLERANCE):** WebFetch each candidate. Then sample the GIF at THREE distinct moments — first frame, middle frame, last frame — because many watermarks fade in/out or only appear mid-clip. For each frame, write out loud: "Frame [N]: I see [describe every pixel of text, logo, icon, signature, channel handle, episode bug, network ident, song-credit tag, brand mark, platform bug, subtitle, caption, or any letter/number anywhere in the frame — including faint, semi-transparent, or corner-tucked marks]." If you see ANY text, logo, watermark, handle, network bug, song credit, attribution, or burned-in subtitle in ANY frame, REJECT. This includes: TikTok logo + username, Instagram handle, YouTube logo, Twitter/X logo, Apple Music/Spotify song-credit bars, MTV/network/TV-channel idents, late-night-show logos, record-label tags, Giphy/Tenor stickers, "for X" credits, episode titles, subtitles/captions, creator signatures, dating-show name plates, and reaction-channel logos. No exceptions, no cropping workarounds, no "it's small so it's fine." If a GIF looks promising but has any mark, find a completely different GIF. If you cannot find a 100% clean GIF for a meme idea after 3 tries, switch to a different meme entirely. **Last week's "Meme 2" shipped with a visible watermark — this check is failing, treat it as the most important step in this section.**
4. **Source quality check (REQUIRED — no grainy footage):** Reject low-resolution, pixelated, heavily compressed, or visibly grainy GIFs — they look amateur when scaled up to 1080×1920. Before accepting, check the GIF's native dimensions (e.g. via WebFetch of the Giphy page — look for the image-source dimensions, or load the direct .gif URL and read the size). Minimum acceptable native size: **480px on the shorter side**. Strongly prefer GIFs ≥720p source. Also reject GIFs that look softened, motion-blurry, dim, color-washed, or like screen-recordings of small videos. When two candidates are otherwise equal, pick the higher-resolution one. Aim for footage that looks crisp at full Reel size.
5. **Aspect ratio check (REQUIRED):** The GIF will be cropped to fill a 9:16 portrait frame. Only accept GIFs where the subject is **centered horizontally** in the frame AND the GIF is square (1:1) or portrait (tall) — or at most mildly landscape (no wider than ~4:3). Reject any ultra-wide landscape GIFs (16:9 or wider) where the subject is off-center — they will crop the subject out of frame. If no suitable GIF exists for a meme idea, choose a different meme.
6. Giphy direct .gif URL (for Step 2A.5 MP4 conversion): `https://media.giphy.com/media/[ID]/giphy.gif` (ID = last segment of share URL after final dash)
7. Tenor: WebFetch the share page to find the direct `media.tenor.com/.../...gif` URL.

**No duplicate GIF sources (REQUIRED):** The two meme GIFs must come from completely different creators, shows, or source accounts. Do NOT pick two GIFs from the same person, artist, or channel — even if the Giphy IDs are different. Before finalising both GIFs, explicitly verify: "Meme 1 GIF is from [creator/source]. Meme 2 GIF is from [creator/source]. These are different." If they are from the same source, replace one of them.

**No visually identical or near-identical GIFs:** If both GIFs show the same scene, setting, or action (e.g. both show someone writing in a notebook, or both show someone sitting at a desk), that is not acceptable even if the creators differ. The two GIFs must have clearly distinct visual energy and subject matter.

**Before writing copy, look at the GIF and read its energy** — the vibe, expression, tone, and momentum of the clip. Then use humor and inference to write copy that *feels* like it belongs with that specific GIF. The joke doesn't have to describe the clip literally — it should use the GIF's energy as the punchline or reaction. Use the top-performing posts from the Performance Brief as inspiration for humor style and tone.

</details>

For each meme produce FOUR pieces of text (write these for BOTH memes — they apply whether the clip came from the library or legacy sourcing):

- **`overlay_text`** — the joke/setup rendered ONTO the video. 6–14 words, punchy. Must describe the actual scene in THIS clip — someone looking at it should recognize the situation in the footage (see the alignment rule in Step 2A). Not interchangeable with any other clip. Examples: *"Me and my bestie talking about our coworkers we don't like"*, *"When you finally start journaling and your whole vibe upgrades"*.
- **`ig_caption`** — short reaction/wink for the Instagram caption field. 2–8 words + optional emoji. Do NOT repeat overlay_text — riff on it. Examples: *"She knows…"*, *"He couldn't do anything to make me happier!"*
- **`fb_caption`** — Facebook caption. More conversational, 1–3 sentences. Drive a reaction or question to spark comments/shares (FB algorithm rewards both). Example: *"Okay but why does this describe my entire Tuesday? 😅 Tag a friend who gets it."*
- **`hashtags`** — 5–8 hashtags including #Zenie or #zenieapp. Same set used on both platforms.

---

## Step 2A-PEXELS: Pexels fallback (LEGACY — IGNORED)

> **DEPRECATED: skip this entire step.** Memes come from the library (Step 2A) and are rendered by GitHub Actions. Do not source memes from Pexels here.

If after 3 Giphy/Tenor candidates per meme you cannot find a clean HD GIF, fall back to Pexels stock video. Pexels videos are 1080×1920 vertical, license-free, no watermarks, no compression artifacts — they pass the new quality bar by default.

```python
import urllib.request, urllib.parse, json
# Pexels API and CDN both reject requests without a User-Agent — always send one
# on BOTH the search request and the MP4 download below. Same requirement as the
# quote-image Pexels pipeline (Step B). Missing User-Agent = 403, which the agent
# may misread as a sandbox egress block.
PEXELS_UA = {"User-Agent": "ZenieAgent/1.0"}

def pexels_search(query, per_page=10):
    url = f"https://api.pexels.com/videos/search?{urllib.parse.urlencode({'query': query, 'orientation': 'portrait', 'per_page': per_page})}"
    req = urllib.request.Request(url, headers={"Authorization": PEXELS_KEY, **PEXELS_UA})
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    out = []
    for v in data.get("videos", []):
        hd = [f for f in v["video_files"] if f.get("width") == 1080 and f.get("height") in (1920, 2048)]
        if hd:
            out.append({"id": v["id"], "duration": v["duration"], "url": hd[0]["link"], "page": v.get("url", "")})
    return out

def pexels_download(mp4_url, out_path):
    req = urllib.request.Request(mp4_url, headers=PEXELS_UA)
    with urllib.request.urlopen(req) as r, open(out_path, "wb") as f:
        f.write(r.read())
```

Then call `pexels_download(pick["url"], "source_meme_N.mp4")` and feed the result into Step 2A.5 in place of the GIF (the rendering pipeline handles both inputs — only the source loader changes). For each Pexels pick, write out loud: "I see: [describe people, clothing, setting, any text]." Same family-friendly + brand-fit rules as Giphy: real humans only, modest clothing, no logos/brand marks, on-theme. Note the Pexels video ID in `meme_ids.txt` for traceability.

### Query strategy — try multiple queries before declaring a meme SKIPPED

**Do NOT give up on Pexels after a single empty search.** Catie's reviewers see a SKIPPED meme as a broken week. For each meme, run AT LEAST 3 different search queries before concluding Pexels has no usable clip. Vary the queries along these axes:

- The literal feeling ("exhausted woman", "stressed woman", "frustrated woman")
- The setting ("woman couch", "woman home", "woman office")
- The body language ("woman head in hands", "woman eye roll", "woman sigh")
- The vibe word ("woman tired", "woman drained", "woman burnt out")

Concrete example for a meme about emotional labor / friend-group therapist energy:
```python
QUERIES_MEME_1 = [
    "exhausted woman couch",
    "tired woman home",
    "woman head in hands",
    "stressed woman laptop",
]
candidates = []
for q in QUERIES_MEME_1:
    candidates.extend(pexels_search(q, per_page=5))
    if len(candidates) >= 6:
        break  # plenty to choose from
# Now apply quality bar + brand fit + dedupe by id, pick one
```

Only declare a meme SKIPPED if ALL queries return zero viable candidates (videos that pass the watermark check, are 1080×1920 HD, and meet the family-friendly + brand-fit rules). When you do skip, record every query you tried and what they returned on the meme's in-memory state struct (e.g. `meme_N_state["queries_tried"]`). Do NOT write to `zenie_drafts.md` mid-execution — that file is built once at the end from final state (see Step 2D). The in-memory query log becomes part of the SKIPPED block emitted in Step 2D.

The HTML preview always embeds the local MP4 — whether the source was Giphy, Tenor, or Pexels — via `<video src="meme_N.mp4" autoplay loop muted playsinline controls>`. Pexels-sourced memes follow the same pipeline as Giphy: the only difference is the input file in Step 2A.5.

---

## Step 2A.5: Convert meme GIF to MP4 (LEGACY — IGNORED)

> **DEPRECATED: skip this entire step.** You do NOT render memes. GitHub Actions renders your chosen library clip (with your `overlay_text`) into `meme_N.mp4` after you publish, using the same white-card overlay style. Just make sure each meme's `meme_slug` and `overlay_text` are in review-state (Step 7).

<details><summary>Legacy in-sandbox MP4 rendering (ignored)</summary>

### Original Step 2A.5 — Convert each meme GIF to MP4 with text overlay (Zenie meme style)

**This step is non-negotiable. Every meme MUST ship as an MP4 with the white-card text overlay burned in. The raw GIF is NEVER what gets posted to Instagram — not as a Reel, not as a feed post, not as a fallback. If MP4 generation fails for a meme, that meme is dropped from this week's batch (find a replacement GIF and retry); the agent must NOT proceed with the GIF-only version.**

Style is the classic Instagram Reel / TikTok caption look: GIF scaled+cropped to fill the full 1080×1920 frame, with a **solid white card containing bold black sans-serif text** (`overlay_text`) burned onto the video near the bottom. No white space outside the GIF. The HTML preview embeds this same MP4 via `<video src="meme_N.mp4">` so Catie reviews the exact file that ships to Meta.

```python
import urllib.request, subprocess, shutil, os, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Portable ffmpeg lookup: use system ffmpeg if available, else install via pip
def _ffmpeg_path():
    p = shutil.which("ffmpeg")
    if p:
        return p
    subprocess.run(["pip", "install", "--quiet", "imageio-ffmpeg"], check=True)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

FFMPEG = _ffmpeg_path()

VIDEO_W = 1080
VIDEO_H = 1920

def render_meme_text_card(overlay_text, output_path):
    """Render Zenie meme-style text card: white solid box with black bold sans-serif text."""
    # Find a bold sans-serif system font
    font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]
    font_path = next((p for p in font_candidates if os.path.exists(p)), None)
    if not font_path:
        # Last resort: install dejavu via apt or fall back to default
        raise RuntimeError("No bold sans-serif font found. Install dejavu-fonts or arial.")

    font = ImageFont.truetype(font_path, 60)
    side_margin = 40
    card_w = VIDEO_W - 2 * side_margin
    h_padding = 35
    v_padding = 28
    line_h = 78

    # Wrap text using actual font metrics
    avg_char_w = font.getlength("M") * 0.55
    chars_per_line = max(15, int((card_w - 2 * h_padding) / avg_char_w))
    wrapped = textwrap.wrap(overlay_text, width=chars_per_line)

    card_h = 2 * v_padding + len(wrapped) * line_h
    canvas_h = card_h + 2 * side_margin

    # Soft drop shadow for the card
    shadow = Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle(
        [(side_margin + 4, side_margin + 4), (side_margin + card_w + 4, side_margin + card_h + 4)],
        fill=(0, 0, 0, 50),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=8))

    canvas = Image.new("RGBA", (VIDEO_W, canvas_h), (0, 0, 0, 0))
    canvas = Image.alpha_composite(canvas, shadow)
    draw = ImageDraw.Draw(canvas)

    # White card
    draw.rectangle(
        [(side_margin, side_margin), (side_margin + card_w, side_margin + card_h)],
        fill=(255, 255, 255, 250),
    )

    # Centered text
    y = side_margin + v_padding
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (VIDEO_W - lw) // 2
        draw.text((x, y), line, font=font, fill=(0, 0, 0, 255))
        y += line_h

    canvas.save(output_path, "PNG")

def gif_to_mp4(gif_url, output_path, overlay_text):
    """Download GIF, convert to vertical 9:16 MP4 with white text card overlay (Zenie meme style)."""
    tmp_gif = "/tmp/meme_input.gif"
    text_card_path = "/tmp/meme_text_card.png"

    # Download GIF with browser-like User-Agent (Giphy blocks server-side requests without one)
    req = urllib.request.Request(gif_url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://giphy.com/",
        "Accept": "image/gif,image/*,*/*",
    })
    with urllib.request.urlopen(req) as r:
        data = r.read()
    if len(data) < 10000:
        raise RuntimeError(f"GIF download too small ({len(data)} bytes) — likely blocked or invalid. URL: {gif_url}")
    if not (data[:3] == b'GIF' or data[:4] == b'\x89PNG'):
        raise RuntimeError(f"Downloaded file is not a valid GIF (got: {data[:20]}). Giphy may have blocked the request. Try a different GIF.")
    with open(tmp_gif, 'wb') as f:
        f.write(data)

    render_meme_text_card(overlay_text, text_card_path)

    # Filter chain:
    # - GIF scaled+cropped to fill full 1080x1920 frame
    # - white text card overlaid near the bottom so it clears the subject's face
    cmd = [
        FFMPEG, "-y",
        "-stream_loop", "-1", "-t", "6",
        "-i", tmp_gif,
        "-i", text_card_path,
        "-filter_complex",
        ("[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
         "crop=1080:1920,setsar=1[base];"
         "[base][1:v]overlay=0:H-h-60"),
        "-t", "6",
        "-r", "30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(tmp_gif)

# Run for each meme — pass the overlay_text from Step 2A
gif_to_mp4(MEME_1_GIF_URL, "/tmp/meme_1.mp4", MEME_1_OVERLAY_TEXT)
gif_to_mp4(MEME_2_GIF_URL, "/tmp/meme_2.mp4", MEME_2_OVERLAY_TEXT)
```

### Post-generation verification (REQUIRED)

After both `gif_to_mp4` calls, verify each MP4 actually exists, is well-formed, and contains the overlay. Do NOT skip this — last week's posts shipped without the white-card overlay because MP4 generation silently failed and the publisher fell back to the raw GIF.

```python
import os, subprocess, json

def verify_meme_mp4(mp4_path, label):
    # 1. File exists and is non-trivial
    if not os.path.exists(mp4_path):
        raise RuntimeError(f"{label}: MP4 not generated at {mp4_path}. Drop this meme and find a replacement GIF.")
    size = os.path.getsize(mp4_path)
    if size < 50_000:
        raise RuntimeError(f"{label}: MP4 suspiciously small ({size} bytes). Probably corrupt. Drop this meme.")
    if size > 100 * 1024 * 1024:
        raise RuntimeError(f"{label}: MP4 over 100MB ({size} bytes). Re-encode or drop.")

    # 2. ffprobe to confirm it's a valid 1080x1920 video of at least 6s
    probe = subprocess.run(
        [FFMPEG.replace("ffmpeg", "ffprobe"), "-v", "error", "-show_entries",
         "stream=width,height,duration,codec_type", "-of", "json", mp4_path],
        capture_output=True, text=True,
    )
    meta = json.loads(probe.stdout or "{}")
    streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]
    if not streams:
        raise RuntimeError(f"{label}: no video stream in MP4. Drop this meme.")
    w, h = streams[0].get("width"), streams[0].get("height")
    if (w, h) != (1080, 1920):
        raise RuntimeError(f"{label}: MP4 dimensions {w}x{h}, expected 1080x1920. Drop this meme.")
    dur = float(streams[0].get("duration") or 0)
    if dur < 5.5:
        raise RuntimeError(f"{label}: MP4 duration {dur}s, expected ≥6s. Drop this meme.")

    print(f"  ✅ {label}: {w}x{h}, {dur:.1f}s, {size//1024}KB — overlay burned in")

verify_meme_mp4("/tmp/meme_1.mp4", "Meme 1")
verify_meme_mp4("/tmp/meme_2.mp4", "Meme 2")
```

If either verification raises, DROP that meme from this week's batch and either (a) find a replacement GIF and re-run Step 2A.5 for it, or (b) ship only the surviving meme and note the drop in the Slack handoff message. **Do not proceed past this step with a missing or malformed MP4. Do not commit the raw GIF as a substitute. Do not let the auto-publisher fall back to the GIF.**

</details>

---

## Step 2B: Find 2 Repost Videos (WebSearch)
Find 2 Instagram Reels. **TikTok is absolutely not allowed — do not use TikTok under any circumstances.**

Search strategies (try all until you find 2 valid Instagram reel URLs):
- WebSearch("instagram reel self-care 2026 site:instagram.com")
- WebSearch("instagram.com/reel journaling women relationships")
- WebSearch("instagram reel viral wellness women 2026")

A valid URL must:
1. Contain "instagram.com" — not "tiktok.com", not any other domain
2. Link directly to a specific reel or post — format: instagram.com/reel/[ID]/ or instagram.com/p/[ID]/
3. NOT be a profile page (instagram.com/username/ with no post ID is invalid)

Before including each repost, write out loud: "This URL is: [URL]. It is from: [platform]. It links to: [specific post or profile page]." If it is not Instagram or not a direct post link, reject it and search again.

**Creator handle — TREAT AS UNVERIFIED.** WebSearch cannot reliably tell you who actually *made* a reel. Self-care and wellness reels are constantly re-shared by aggregator/repost accounts, so the handle that appears in search results is very often the aggregator, not the original creator. Do NOT trust a handle that came only from a search snippet. **Do NOT WebFetch instagram.com to confirm the creator.** Instagram blocks/stalls automated fetches from this sandbox, and a hanging fetch here silently killed two entire drafting runs (2026-07-13 incident) before they could email their output. Instead, always fill your best-guess handle from the search result and **flag it as unverified**: append ` ⚠️ UNVERIFIED — confirm creator against the reel before posting` to the Creator line in the review bundle so the human confirms it during Slack review. Never present a repost credit as confirmed when it came only from a search result.

Get: direct Instagram reel URL, creator handle (per the caution above), repost caption, best time to post. **The credit goes in BOTH the Instagram caption and the Facebook caption** — see the Notion schema below.

---

## Step 2C: Create 2 Quote Images — EXACT DESIGN SPEC

> **⚠️ RENDERING MOVED TO THE RUNNER (2026-07-13) — DO NOT render the quote images yourself, and do NOT use Pexels or PIL here.** For each of the 2 quotes, only DECIDE the quote text + attribution + the caption(s), and write them into review-state (Step 7) as a `Quote Image` post with `needs_render: true` and `media_url: null`. The GitHub Action's `regenerate_quotes.py` renders the actual `quote_{n}.jpg` on its open-internet runner (it sources its own Pexels background), fills `media_url`, and updates the preview page. The design spec below still governs the FINISHED image, so pick quotes that suit it — but you produce only the TEXT, not the image. Skip every Pexels/PIL/font/rendering instruction in this section; you do not need a Pexels key.

The design is: **a beautiful full-bleed photo background with a floating cream card on top**, with decorative watercolor/botanical elements at the card corners. This matches Zenie's existing Instagram aesthetic exactly.

### Quotes
- Source REAL attributed quotes from famous thinkers, writers, philosophers (Buddha, Rumi, Maya Angelou, Brené Brown, Stoics, poets, etc.)
- Tone: self-reflection, growth, relationships, intentional living, inner peace
- Length: **10–18 words max** — prefer short, elegant, poetic quotes. Avoid long or analytical quotes that require unpacking. The best quotes land instantly.
- Style: lean toward poets, writers, and spiritual thinkers (Rilke, Rumi, Mary Oliver, Kahlil Gibran, Maya Angelou). Be cautious with psychologists/analysts (Jung, Freud) — their quotes often feel clinical rather than warm.
- Format: include the attribution (name of person, or "Unknown")
- Example: quote="When life gets blurry, adjust your focus, not your vision.", attribution="Unknown"
- Example: quote="A crack is where the light comes in.", attribution="Rumi"
- Example (ideal style): quote="The only journey is the one within.", attribution="Rainer Maria Rilke"
- **Use the Performance Brief:** if quote images drove higher saves on IG, lean into themes that resonated (e.g. inner peace, relationships). Pick quotes that match those themes.

**Quote images are Facebook-only. Do NOT post quote images to Instagram.**

For each quote image, produce one caption only:
- **`fb_caption`** — 2–3 sentences, more reflective. Invite a comment or share. Example: *"Sometimes a single line can reframe your whole day. ✨ Save this one for when you need a reminder. Who would you share this with?"*

### Step A — Download Playfair Display fonts

Google Fonts ships Playfair Display only as variable fonts (`PlayfairDisplay[wght].ttf`), not as separate Bold/Regular files, so download those and apply the weight axis at render time:

```python
import urllib.request, os
from PIL import ImageFont

FONT_VAR = "/tmp/PlayfairDisplay-VAR.ttf"
FONT_VAR_ITALIC = "/tmp/PlayfairDisplay-Italic-VAR.ttf"

if not os.path.exists(FONT_VAR):
    urllib.request.urlretrieve(
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf",
        FONT_VAR,
    )
if not os.path.exists(FONT_VAR_ITALIC):
    urllib.request.urlretrieve(
        "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf",
        FONT_VAR_ITALIC,
    )

def load_font(path, size, weight=None):
    """Load a font and apply variable-font weight axis if specified."""
    f = ImageFont.truetype(path, size)
    if weight is not None and hasattr(f, "set_variation_by_axes"):
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f
```

### Step B — Fetch background photo from Pexels Curated

```python
import urllib.request, json, random, io
from PIL import Image, ImageEnhance

def get_curated_photo(pexels_key, page=None):
    # Pexels API and CDN both reject requests without a User-Agent — always send one.
    if page is None:
        page = random.randint(1, 8)
    url = f"https://api.pexels.com/v1/curated?per_page=80&page={page}"
    req = urllib.request.Request(url, headers={
        "Authorization": pexels_key,
        "User-Agent": "ZenieAgent/1.0",
    })
    with urllib.request.urlopen(req) as r:
        data = json.load(r)

    # High-res landscape or square only
    candidates = [p for p in data["photos"] if p["width"] >= 3000 and p["width"] >= p["height"]]
    if not candidates:
        candidates = sorted(data["photos"], key=lambda p: p["width"], reverse=True)[:10]

    photo = random.choice(candidates)
    photo_req = urllib.request.Request(photo["src"]["large2x"], headers={"User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(photo_req) as r:
        img = Image.open(io.BytesIO(r.read())).convert("RGB")

    # Center-crop to square
    w, h = img.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((1080, 1080), Image.LANCZOS)

    # Boost vibrancy so the photo pops behind the card
    img = ImageEnhance.Color(img).enhance(1.2)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    return img
```

### Step C — Compose the quote image

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap, random

def make_quote_image(quote, attribution, filename, bg_img):
    """bg_img: a PIL Image pre-fetched via get_curated_photo(). Pass a different one for each quote."""
    SIZE = 1080
    CARD_W, CARD_H = 730, 730
    CARD_X = (SIZE - CARD_W) // 2   # 175
    CARD_Y = (SIZE - CARD_H) // 2   # 175

    TEXT_COLOR = (52, 30, 90)        # dark purple #341E5A
    ATTR_COLOR = (100, 75, 150)      # medium purple
    CREAM = (250, 247, 241, 248)     # warm cream card, very slightly transparent

    # --- 1. Background photo (no dark overlay — photo is fully visible) ---
    bg = bg_img.convert("RGBA")

    # --- 2. Card shadow ---
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [(CARD_X + 10, CARD_Y + 10), (CARD_X + CARD_W + 10, CARD_Y + CARD_H + 10)],
        radius=10, fill=(0, 0, 0, 55)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))
    bg = Image.alpha_composite(bg, shadow)

    # --- 3. Cream card ---
    card_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card_layer)
    cd.rounded_rectangle(
        [(CARD_X, CARD_Y), (CARD_X + CARD_W, CARD_Y + CARD_H)],
        radius=8, fill=CREAM
    )
    bg = Image.alpha_composite(bg, card_layer)

    # --- 4. Watercolor corner decorations ---
    # Soft blobs in lavender, dusty pink, and sage that bleed off card corners
    deco = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)

    palette = [
        (180, 155, 220, 70),   # lavender
        (210, 175, 210, 60),   # mauve
        (160, 195, 180, 55),   # sage
        (220, 175, 195, 65),   # dusty pink
        (195, 170, 225, 75),   # soft purple
    ]

    def draw_corner_blobs(cx, cy):
        for _ in range(10):
            ox = cx + random.randint(-45, 45)
            oy = cy + random.randint(-45, 45)
            r = random.randint(22, 52)
            color = random.choice(palette)
            dd.ellipse([(ox - r, oy - r), (ox + r, oy + r)], fill=color)

    # Top-left corner
    draw_corner_blobs(CARD_X + 20, CARD_Y + 20)
    # Bottom-right corner
    draw_corner_blobs(CARD_X + CARD_W - 20, CARD_Y + CARD_H - 20)

    deco = deco.filter(ImageFilter.GaussianBlur(radius=10))
    bg = Image.alpha_composite(bg, deco)

    # --- 5. Text ---
    bg_rgb = bg.convert("RGB")
    draw = ImageDraw.Draw(bg_rgb)

    font_bold = load_font(FONT_VAR, 56, weight=700)
    font_attr = load_font(FONT_VAR_ITALIC, 30, weight=400)
    font_brand = load_font(FONT_VAR, 34, weight=400)

    # Quote text — centered on card, with curly quotes
    wrapped = textwrap.wrap(f'\u201c{quote}\u201d', width=24)
    line_h = 70
    text_block_h = len(wrapped) * line_h
    text_start_y = CARD_Y + (CARD_H - text_block_h) // 2 - 30

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_bold)
        lw = bbox[2] - bbox[0]
        lx = CARD_X + (CARD_W - lw) // 2
        draw.text((lx, text_start_y), line, font=font_bold, fill=TEXT_COLOR)
        text_start_y += line_h

    # Attribution — centered, below quote
    attr_text = f"\u2013{attribution}"
    ab = draw.textbbox((0, 0), attr_text, font=font_attr)
    ax = CARD_X + (CARD_W - (ab[2] - ab[0])) // 2
    draw.text((ax, text_start_y + 18), attr_text, font=font_attr, fill=ATTR_COLOR)

    # "zenie" wordmark — bottom center of card
    zb = draw.textbbox((0, 0), "zenie", font=font_brand)
    zx = CARD_X + (CARD_W - (zb[2] - zb[0])) // 2
    draw.text((zx, CARD_Y + CARD_H - 58), "zenie", font=font_brand, fill=TEXT_COLOR)

    bg_rgb.save(filename, format="JPEG", quality=95)

# Fetch two backgrounds that are DIFFERENT STYLES — not just different colors or different photos of the same type of scene.
# After fetching each, write out loud: "bg_1 is: [subject, setting, mood, style]" and "bg_2 is: [subject, setting, mood, style]"
# They must differ in STYLE — e.g. one is nature/outdoors and the other is cozy interior; or one is abstract/minimal and the other is lush botanical; or one is moody dark tones and the other is bright airy. Same vibe in different colors is NOT acceptable.
# If they are the same style, discard bg_2 and fetch again until they are genuinely different in style.
bg_1 = get_curated_photo(PEXELS_KEY, page=random.randint(1, 3))
bg_2 = get_curated_photo(PEXELS_KEY, page=random.randint(6, 8))

make_quote_image("QUOTE TEXT HERE", "Attribution Here", "quote_1.jpg", bg_1)
make_quote_image("QUOTE TEXT HERE", "Attribution Here", "quote_2.jpg", bg_2)
```

---

## Step 2D: Build `zenie_drafts.md` from FINAL STATE (do NOT write earlier)

`zenie_drafts.md` is Catie's plain-English briefing for the week. It MUST be written exactly once, at this step, deterministically from the FINAL on-disk state of each asset. NEVER accumulate notes into this file during Steps 1–2C. If you wrote a SKIPPED warning into the briefing earlier and a Pexels (or other) fallback later succeeded, the briefing ships stale and Catie discards real, postable memes. (Concrete incident: 2026-06-15 — both memes were generated successfully via Pexels fallback, but `zenie_drafts.md` still said "Giphy/Tenor/Pexels all blocked ⚠️ SKIPPED" for both. The watchdog can't fully unwind this — fix the source by writing this file ONCE here.)

Build the file as a single Python string (`drafts_md`), save it to `/tmp/zenie_drafts.md`, and add it to the BUNDLE in Step 3 alongside the other assets. Do NOT write or transmit `zenie_drafts.md` from any earlier step.

**Posting-time timezone — ALWAYS PST.** Every `**Best time to post:**` value in this file (memes, quotes, reposts) MUST be expressed in Pacific time and labelled `PST` — e.g. `Tuesday 6–8 PM PST`. Do NOT use EST. The same PST `best_time` string flows into Notion (Step 6) and is converted to a UTC Scheduled Date there.

### Header (always)

```
# Zenie Social Media Drafts — {DATE}

**Performance Brief:** {brief_text_from_step_0}

**Trending Themes ({Month YYYY}):** {themes_from_step_1}

---
```

### Per-meme section (deterministic from disk)

For each meme slot N in (1, 2):

Memes are now rendered downstream by GitHub Actions from the library, so the MP4
does NOT exist on disk yet at this step. A meme is "real" if you assigned it a
`meme_slug` (it WILL be rendered); only treat it as skipped if you couldn't
assign a slug (e.g. the library ran out of available clips).

```python
is_real = bool(meme_N_state.get("meme_slug"))   # a slug was chosen → it will render
```

If `is_real`:
```
## Meme N — {theme}

**overlay_text:** {text}

**ig_caption:** {ig_caption}

**fb_caption:** {fb_caption}

**hashtags:** {hashtags}

**Best time to post:** {day, time}

**Asset:** meme_N.mp4 — rendered automatically from library clip `{meme_slug}` ({clip title}) with white-card overlay

---
```

If NOT `is_real` (no library clip was available for this meme):
```
## Meme N — {theme} ⚠️ SKIPPED

**⚠️ SKIPPED — no library clip was available (the meme library is exhausted; add new clips to `meme_library/`).**

**Intended overlay_text:** {text}

**ig_caption:** {ig_caption}

**fb_caption:** {fb_caption}

**hashtags:** {hashtags}

**Best time to post:** {day, time}

---
```

### Per-quote section (deterministic from disk)

For each quote slot N in (1, 2):

```python
jpg = f"/tmp/quote_{N}.jpg"
is_real = os.path.exists(jpg) and os.path.getsize(jpg) >= 20_000
```

Render the normal Quote section if `is_real` (with `**Asset:** quote_N.jpg ...`), otherwise a SKIPPED Quote section using the same shape as the meme SKIPPED block.

### Per-repost section (always rendered — no asset generation)

```
## Repost N — {theme}

**URL:** {url}

**Creator:** {creator_or_placeholder}

**Repost caption:** {caption}

**Best time to post:** {day, time}

---
```

### Footer

```
*Generated: {YYYY-MM-DD} | Zenie Social Media Agent*
```

After concatenating header + sections + footer into `drafts_md`, save to `/tmp/zenie_drafts.md` and add it to the BUNDLE in Step 3. The on-disk file is the single source of truth for the briefing — no other step should append, modify, or duplicate it.

---

## Step 3: Publishing = email a bundle (your sandbox CANNOT push to GitHub)

Your sandbox can no longer write to GitHub — every call to `api.github.com`
returns `502 builtin injection failed`. So you do **NOT** push anything and you do
**NOT** call api.github.com. Instead you collect every output file into one
in-memory bundle and EMAIL it at the very end (Step 8). A GitHub Action
(`publish-drafts-from-email.yml`) receives the email, writes the files into the
repo, renders the library memes, and posts to Slack — exactly as a push would have.

Set up the bundle now, then add to it as you build each file in the later steps:

```python
import base64

DATE = "TODAYS_DATE"   # YYYY-MM-DD — the Monday you are running
BUNDLE = {"week_date": DATE, "text_files": {}, "binary_files": {}}

def add_text(path, content):       # path is repo-relative, e.g. f"posts/{DATE}/index.html"
    BUNDLE["text_files"][path] = content

def add_binary(path, content_bytes):
    BUNDLE["binary_files"][path] = base64.b64encode(content_bytes).decode()
```

Add the two quote images you rendered in Step 2C (saved as `quote_1.jpg` and
`quote_2.jpg` in the working directory):

```python
for n in (1, 2):
    with open(f"quote_{n}.jpg", "rb") as f:
        add_binary(f"posts/{DATE}/quote_{n}.jpg", f.read())
```

Add the `zenie_drafts.md` you built in Step 2D (saved at `/tmp/zenie_drafts.md`):

```python
with open("/tmp/zenie_drafts.md", encoding="utf-8") as f:
    add_text(f"posts/{DATE}/zenie_drafts.md", f.read())
```

Do NOT add meme MP4s — you don't render memes; the Action renders them from the
library after it reads your `review-state.json` (Step 7). The remaining files
(this week's `index.html`, the root `index.html`, and `review-state.json`) get
added to the bundle in Steps 4, 5, and 7 below.

---

## Step 4: Build this week's preview index.html

For memes: use a `<video>` tag pointing to the local MP4 (`meme_1.mp4` / `meme_2.mp4`) — this is the same file that ships to Meta, with the white-card overlay burned in. Do NOT embed Giphy/Tenor iframes — third-party iframes are blocked by many browsers and by Slack's link unfurler, which is what reviewers see.
For quote images: add a subtle CSS Ken Burns animation (slow zoom).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Drafts — [DATE]</title>
<style>
  :root { --purple: #6B3FA0; --lavender: #C9B1E8; --pink: #F0A0C0; }
  body { font-family: -apple-system, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #f5f0fa; }
  h1 { color: var(--purple); }
  .back { color: var(--purple); text-decoration: none; font-size: .9em; display: block; margin-bottom: 20px; }
  .post { background: white; border-radius: 16px; padding: 20px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(107,63,160,.1); border-top: 3px solid var(--lavender); }
  .post h2 { font-size: .8em; text-transform: uppercase; letter-spacing: .08em; color: var(--purple); margin: 0 0 12px; }
  .meme-wrap { width: 100%; padding-bottom: 177.78%; height: 0; position: relative; border-radius: 12px; overflow: hidden; margin-bottom: 12px; background: #000; }
  .meme-wrap video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }
  .quote-wrap { width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 12px; }
  .quote-wrap img { width: 100%; display: block; animation: kenburns 12s ease-in-out infinite alternate; transform-origin: center; }
  @keyframes kenburns { from { transform: scale(1); } to { transform: scale(1.06); } }
  .caption { margin-bottom: 6px; font-size: .95em; }
  .tags { font-size: .85em; color: var(--purple); margin-bottom: 6px; }
  .time { font-size: .8em; color: #999; }
  .btn { display: inline-block; padding: 9px 18px; background: var(--purple); color: white; border-radius: 20px; text-decoration: none; font-size: .9em; margin: 8px 0; }
  .btn:hover { background: #5a3390; }
</style>
</head>
<body>
<a class="back" href="../../">← All weeks</a>
<h1>Zenie Drafts — [DATE]</h1>

<div class="post">
  <h2>Meme 1</h2>
  <div class="meme-wrap"><video src="meme_1.mp4" autoplay loop muted playsinline controls></video></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Meme 2</h2>
  <div class="meme-wrap"><video src="meme_2.mp4" autoplay loop muted playsinline controls></video></div>
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
  <div class="quote-wrap"><img src="quote_1.jpg" alt="Quote 1"></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

<div class="post">
  <h2>Quote Image 2</h2>
  <div class="quote-wrap"><img src="quote_2.jpg" alt="Quote 2"></div>
  <p class="caption">[CAPTION]</p>
  <p class="tags">[HASHTAGS]</p>
  <p class="time">Best time: [TIME]</p>
</div>

</body></html>
```

Add the finished HTML string to the bundle (do NOT push it):

```python
add_text(f"posts/{DATE}/index.html", html)   # `html` = the preview page you just built
```

---

## Step 5: Update the root index.html
The root `index.html` lists every week. READ the current one via the **raw URL**
(reads still work from the sandbox), prepend this week's entry at the top, remove
`latest` from the previously-latest entry, then add the updated HTML to the bundle.
Do NOT push it.

```python
import urllib.request
root_html = urllib.request.urlopen(
    "https://raw.githubusercontent.com/isabelhoppmann/ART-Lab-Social-Media/main/index.html"
).read().decode()
# prepend the new entry, strip "latest" from the old one -> root_new
add_text("index.html", root_new)
```

New entry: `<a class="week latest" href="posts/[DATE]/"><span class="week-date">[Month Day, Year]</span><span class="week-arrow">→</span></a>`


---

## Step 6: Save posts to Notion database

> **⚠️ ORDER CHANGED 2026-07-13 — DO STEPS 7 AND 8 (build review-state + EMAIL THE BUNDLE) BEFORE THIS STEP.** Publishing must NEVER depend on Notion. A hanging Notion MCP call here silently killed four drafting runs (2026-07-13) before they could email anything — and an MCP call is NOT covered by the socket timeout, so it can hang indefinitely. Therefore: finish the files, build review-state (Step 7), and **email the bundle (Step 8) FIRST**. Only AFTER the bundle email is sent do you come back and do this Notion save.
>
> **This Notion save is BEST-EFFORT and fully skippable.** Give the Notion MCP calls at most ~30 seconds of total effort. If `notion-search`/`notion-create-pages`/`notion-update-page` is slow, errors, or seems to hang, STOP immediately and just finish — do not retry, do not wait. Skipping Notion only means the quote/repost rows are missing from the database (a human can add them later); the week is already published via the emailed bundle, which is all that matters.

After building the files AND after emailing the bundle (Step 8), save the **two quote images and the two reposts** to the **Zenie Posts** Notion database (ID: `468afa8e-3a1a-49dd-8852-c130077221d5`) using the Notion MCP tool `notion-create-pages`.

**Save 4 posts (the two quote images + the two reposts).** Do NOT create Notion rows for the memes — the render step (`regenerate_memes.py`) creates each meme's Notion row automatically when it renders the library clip, so creating them here would duplicate them. (The Meme 1/Meme 2 property templates below are kept only as a field reference for the automated render step.)

### Idempotency — check BEFORE creating (prevents retry duplicates)
This step can run more than once for the same week: if an earlier run failed partway (e.g. an egress/proxy error blocked the email bundle or Slack post), the agent gets re-invoked and reaches Step 6 again. `notion-create-pages` ALWAYS creates new rows, so a naive re-run produces duplicate `Quote 1 — [DATE]` / `Quote 2 — [DATE]` / `Repost 1 — [DATE]` / `Repost 2 — [DATE]` pages (this happened on 2026-06-29: three of each quote). Before creating, you MUST check for an existing row for **each of the 4 slots** (`Quote 1`, `Quote 2`, `Repost 1`, `Repost 2`):
1. Call `notion-search` with `data_source_url: collection://468afa8e-3a1a-49dd-8852-c130077221d5` and query the exact slot name, e.g. `Quote 1 — [DATE]`, then `Quote 2 — [DATE]`, then `Repost 1 — [DATE]`, then `Repost 2 — [DATE]`. Do NOT use `notion-query-data-sources` — it is gated on this workspace.
2. If a page titled EXACTLY `<slot> — [DATE]` already exists, UPDATE it in place with `notion-update-page` (`update_properties`) using the properties below — do not create a second one.
3. Only call `notion-create-pages` for a slot that has no existing row.

This makes Step 6 safe to re-run: exactly one row per slot per week, no matter how many times the agent retries. (Note: Notion's search index can lag a minute or two behind a just-created page, so this catches retries that are minutes apart but is not bulletproof for back-to-back runs. The fully robust fix is to move quote/repost row creation into the `post-social-to-slack` Action the same way memes already work — the Action runs once per pipeline, so it cannot duplicate. Do that if retry-duplication recurs.)

### Calculating Scheduled Dates
Each post has a recommended Best Time (e.g. "Wednesday 7–9 PM PST"). Convert this into a real ISO-8601 datetime for the coming week starting from today's date (the date you are running):
- Find the next occurrence of that weekday at the midpoint of the time range (e.g. "7–9 PM" → 20:00, "6–8 PM" → 19:00, "10 AM–12 PM" → 11:00)
- Convert that Pacific local time to UTC. Pacific is **UTC-7 during US daylight saving** (roughly mid-March to early November — this covers most of the year) and **UTC-8 otherwise**; pick the offset that applies to the run date. So in summer 8 PM PST → add 7 hours = 03:00 next day UTC; in winter add 8 hours.
- Format: `YYYY-MM-DDTHH:MM:00.000+00:00`
- If the weekday has already passed this week, use next week's occurrence
- Spread the posts across different days — aim for all 6 (2 memes, 2 quotes, 2 reposts) on distinct days where possible, and never schedule two on the same day+time

For each post, call `notion-create-pages` with parent page ID `468afa8e-3a1a-49dd-8852-c130077221d5` and these properties:

**Meme 1:**
- Name: `Meme 1 — [DATE]`
- Post Type: `Meme`
- Caption: `ig_caption` (Instagram caption)
- FB Caption: `fb_caption` (Facebook caption)
- Hashtags: the meme hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_1.mp4`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE] (ISO format YYYY-MM-DD)

**Meme 2:**
- Name: `Meme 2 — [DATE]`
- Post Type: `Meme`
- Caption: `ig_caption`
- FB Caption: `fb_caption`
- Hashtags: the meme hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/meme_2.mp4`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Quote Image 1:**
- Name: `Quote 1 — [DATE]`
- Post Type: `Quote Image`
- Caption: *(leave blank — quote images are Facebook only)*
- FB Caption: `fb_caption`
- Hashtags: the quote hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/quote_1.jpg`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Quote Image 2:**
- Name: `Quote 2 — [DATE]`
- Post Type: `Quote Image`
- Caption: *(leave blank — quote images are Facebook only)*
- FB Caption: `fb_caption`
- Hashtags: the quote hashtags
- Media URL: `https://cdn.jsdelivr.net/gh/isabelhoppmann/ART-Lab-Social-Media@main/posts/[DATE]/quote_2.jpg`
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Repost 1:** *(the Zenie Posts DB has no Creator field, so put the credit in the caption and the reel link in Media URL)*
- Name: `Repost 1 — [DATE]`
- Post Type: `Repost`
- Caption: the repost caption, prefixed with the credit, e.g. `Credit: @[creator] — [repost caption]` (Instagram caption — now carries the credit too)
- FB Caption: the repost caption, prefixed with the credit, e.g. `Credit: @[creator] — [repost caption]`
- Hashtags: the repost hashtags (if any)
- Media URL: the **direct Instagram reel URL** being reposted (this is the link, not a file we host)
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

**Repost 2:**
- Name: `Repost 2 — [DATE]`
- Post Type: `Repost`
- Caption: the repost caption, prefixed with the credit, e.g. `Credit: @[creator] — [repost caption]` (Instagram caption — now carries the credit too)
- FB Caption: the repost caption, prefixed with the credit, e.g. `Credit: @[creator] — [repost caption]`
- Hashtags: the repost hashtags (if any)
- Media URL: the direct Instagram reel URL being reposted
- Status: `Draft`
- Best Time: the recommended posting time text
- Scheduled Date: calculated ISO-8601 datetime
- Week: [DATE]

After creating the rows, print: "Saved 2 quote + 2 repost posts to Notion (memes are added automatically by the render step)."

Make sure every post (both memes, both quotes, and both reposts) has a distinct `best_time` on a different day — the render step computes the memes' Notion Scheduled Date from their `best_time`, so distinct days still matter.



---

## Step 7: Build review state (added to the bundle; Slack posting is handled automatically)

Build `social/review-state.json` with the full post state: week_date, preview_url, slack_thread_ts set to null, slack_error set to null, and for each post: label, notion_page_id, all captions, hashtags, `media_url`, url/creator (reposts), quote/attribution (quotes), approved=false.

**Memes (library-rendered — IMPORTANT):** you did NOT render the meme MP4s; GitHub Actions does. For each of the two meme posts set:
- `meme_slug` = the library slug you chose in Step 2A
- `overlay_text` = your meme overlay line
- `skipped` = true  and  `media_url` = null  (this is the signal that tells the render step to build it)
- `notion_page_id` = null (the render step creates the meme's Notion row automatically — do NOT create meme rows yourself in Step 6)
- plus `ig_caption`, `fb_caption`, `hashtags`, `best_time`
The `post-social-to-slack` Action will render `meme_library/clips/<meme_slug>.mp4` with your overlay, fill `media_url`, set `skipped=false`, mark the slug used (no-repeat), create the Notion row, and post it to Slack. **Quote images keep `media_url`** = the jsdelivr URL of the .jpg (you rendered those). Reposts carry url/creator.

**`preview_url` MUST be the GitHub Pages URL, not jsDelivr.** Use exactly this format:
`https://isabelhoppmann.github.io/ART-Lab-Social-Media/posts/[DATE]/`

Reason: jsDelivr serves `.html` with `Content-Type: text/plain` (anti-abuse policy), so reviewers clicking a jsdelivr index.html link see raw HTML source instead of the rendered preview. GitHub Pages serves the same file with the correct `text/html` type. Keep `media_url` on jsDelivr — that policy only affects HTML, not `.mp4` or `.jpg`.

Add this file to the bundle instead of pushing it (leave `slack_thread_ts` = null —
the Action sets it after it posts):

```python
import json
add_text("social/review-state.json", json.dumps(state, indent=2, ensure_ascii=False))
```

The publish Action (`publish-drafts-from-email.yml`) receives your emailed bundle,
writes `review-state.json`, renders the library memes, and posts all content to
#social-media-content-review in Slack with full thread replies per post — then
commits the updated file with `slack_thread_ts` set.

Do NOT call the Slack API directly from this agent. The network environment blocks slack.com — the GitHub Action handles this instead.

---

## Step 8: Email the bundle (this is how everything gets published)

> **DO THIS BEFORE Step 6 (Notion).** This email is the ONLY thing that publishes the week. Send it as soon as the files and review-state (Step 7) are ready — do not do the Notion save first. Once this email is sent, the week is safely published; only then go back and do Step 6 (Notion) as a best-effort extra.

Send the bundle as the **plain-text body of one email**. The publish Action polls
for it (subject match), parses it, and publishes everything. Use `urllib` only.

- **Subject:** EXACTLY `ZENIE DRAFTS <DATE>` — e.g. `ZENIE DRAFTS 2026-06-29`
- **From / To:** isabel@art-lab.ai
- **Body:** `json.dumps(BUNDLE)` and nothing else — no greeting, no ``` fences, no commentary.

Use the GMAIL_CLIENT_ID / GMAIL_SECRET / GMAIL_REFRESH credentials from your run
message (the same ones you'd use for a failure email): POST them to
`https://oauth2.googleapis.com/token` (grant_type=refresh_token) to get an
access_token, build an RFC 2822 message (From, To, Subject, `Content-Type: text/plain; charset="utf-8"`,
then the body), base64url-encode the whole message, and POST to
`https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with
`Authorization: Bearer <access_token>` and body `{"raw": "<encoded>"}`.

```python
import json, base64, urllib.parse, urllib.request

raw_msg = (
    "From: isabel@art-lab.ai\r\n"
    "To: isabel@art-lab.ai\r\n"
    f"Subject: ZENIE DRAFTS {DATE}\r\n"
    'Content-Type: text/plain; charset="utf-8"\r\n\r\n'
    + json.dumps(BUNDLE)
).encode("utf-8")
encoded = base64.urlsafe_b64encode(raw_msg).decode()

tok = json.load(urllib.request.urlopen(urllib.request.Request(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "client_id": GMAIL_CLIENT_ID, "client_secret": GMAIL_SECRET,
        "refresh_token": GMAIL_REFRESH, "grant_type": "refresh_token",
    }).encode())))["access_token"]

req = urllib.request.Request(
    "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
    data=json.dumps({"raw": encoded}).encode(),
    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    method="POST")
urllib.request.urlopen(req)
```

After it sends, print `Emailed ZENIE DRAFTS <DATE> bundle (<N> files)` and STOP.
Do NOT attempt any GitHub push. Do NOT call Slack. The publish Action takes it
from here (it runs ~40 min later on Monday, or can be run on demand).

If the email send itself fails, fall back to the failure-email path in your run
message so Isabel is alerted.

