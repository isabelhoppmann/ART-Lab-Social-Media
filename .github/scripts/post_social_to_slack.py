import json, urllib.request, urllib.parse, sys, os

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = "C0B32JUDVD3"
STATE_PATH = "social/review-state.json"

with open(STATE_PATH) as f:
    state = json.load(f)

week = state.get("week_date", "")


def normalize_preview_url(url):
    """jsDelivr serves .html with Content-Type: text/plain, so the preview page shows
    raw source and the meme videos don't render. Force HTML previews onto GitHub Pages,
    which serves text/html. Non-HTML media_url links are left alone (jsDelivr serves
    .mp4/.jpg with correct content-types). This is a guardrail: the agent is also
    instructed to never use a jsDelivr URL for preview_url, but it has regressed before."""
    if not url or "cdn.jsdelivr.net/gh/" not in url:
        return url
    if not (url.endswith(".html") or url.endswith("/")):
        return url  # only rewrite HTML previews, not media files
    rest = url.split("cdn.jsdelivr.net/gh/", 1)[1]      # OWNER/REPO@BRANCH/PATH...
    parts = rest.split("/")
    if len(parts) < 2:
        return url
    owner = parts[0]
    repo = parts[1].split("@")[0]                        # strip @branch
    path = "/".join(parts[2:])
    if path.endswith("index.html"):
        path = path[: -len("index.html")]                # Pages serves dir → index.html
    pages = f"https://{owner}.github.io/{repo}/{path}"
    if pages != url:
        print(f"Rewrote jsDelivr preview_url to GitHub Pages: {pages}")
    return pages


preview_url = normalize_preview_url(state.get("preview_url", ""))
posts = state.get("posts", [])

# Backward compat: support legacy dict-keyed format
if isinstance(posts, dict):
    legacy = []
    for key, post in posts.items():
        post = dict(post)
        post.setdefault("label", key)
        post.setdefault("post_type", key.split("_")[0].capitalize())
        legacy.append(post)
    posts = legacy


def local_path_for(url):
    """Map a media/preview URL to its checked-out file path. The GitHub Action
    checks out the repo, so the real bytes are on disk — using them avoids CDN
    propagation lag (jsDelivr/Pages can 404 for a minute right after a push)."""
    if url and "/posts/" in url:
        return "posts/" + url.split("/posts/", 1)[1]
    return ""


# Minimum sane file sizes — anything smaller is a broken/placeholder asset.
# Mirrors the watchdog's SIZE_FLOOR so the gate and the alarm agree.
SIZE_FLOOR = {".mp4": 100_000, ".jpg": 20_000, ".jpeg": 20_000, ".html": 1_500}


def _check_asset(label, path, problems):
    ext = os.path.splitext(path)[1].lower()
    floor = SIZE_FLOOR.get(ext, 1)
    if not path:
        problems.append(f"{label}: media_url doesn't map to a repo file.")
    elif not os.path.isfile(path):
        problems.append(f"{label}: file is missing on disk ({path}) — not openable.")
    elif os.path.getsize(path) < floor:
        sz = os.path.getsize(path)
        problems.append(f"{label}: file is suspiciously small ({sz} bytes < {floor}) at {path} — likely broken/placeholder.")


def preflight(preview_url, posts):
    """Return a list of plain-English problems. If non-empty, we post NOTHING to
    Slack — Catie should never receive a review where something won't open."""
    problems = []
    if not preview_url.startswith("https://isabelhoppmann.github.io/"):
        problems.append(
            f"Preview link is not a GitHub Pages URL ({preview_url!r}) — it would show source code instead of rendering the videos."
        )
    if "/posts/" in preview_url:
        seg = preview_url.split("/posts/", 1)[1].strip("/").split("/")[0]  # the DATE folder
        _check_asset("Preview page (index.html)", f"posts/{seg}/index.html", problems)
    for post in posts:
        ptype = (post.get("post_type") or "").lower()
        if ptype in ("meme", "quote", "quote image"):
            label = post.get("label", "?")
            url = post.get("media_url") or post.get("mp4_url") or ""
            if not url:
                problems.append(f"{label}: no media_url in review-state.json — nothing to attach.")
                continue
            _check_asset(label, local_path_for(url), problems)
    return problems

def slack_api(path, payload, content_type="application/json"):
    if content_type == "application/json":
        body = json.dumps(payload).encode()
    else:
        body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        f"https://slack.com/api/{path}",
        data=body,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": content_type}
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

def slack_post(channel, blocks, thread_ts=None, text_fallback=None):
    payload = {"channel": channel, "blocks": blocks}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    if text_fallback:
        payload["text"] = text_fallback[:300]
    return slack_api("chat.postMessage", payload)

def slack_upload_to_thread(channel, thread_ts, media_url, filename, comment):
    """Upload media as a file attached to a thread reply. Prefers the local
    checked-out file (the exact bytes that passed pre-flight, no CDN lag); falls
    back to downloading media_url only if the local file isn't present.
    Returns the completeUploadExternal result. Raises on any network/API failure."""
    local = local_path_for(media_url)
    if local and os.path.isfile(local):
        with open(local, "rb") as f:
            content = f.read()
    else:
        req = urllib.request.Request(media_url, headers={"User-Agent": "ZenieSlackBot/1.0"})
        with urllib.request.urlopen(req) as r:
            content = r.read()
    step1 = slack_api(
        "files.getUploadURLExternal",
        {"filename": filename, "length": str(len(content))},
        content_type="application/x-www-form-urlencoded",
    )
    if not step1.get("ok"):
        raise RuntimeError(f"getUploadURLExternal failed: {step1}")
    upload_url = step1["upload_url"]
    file_id = step1["file_id"]
    put_req = urllib.request.Request(upload_url, data=content, method="POST")
    with urllib.request.urlopen(put_req) as resp:
        resp.read()
    payload = {
        "files": [{"id": file_id, "title": filename}],
        "channel_id": channel,
        "thread_ts": thread_ts,
        "initial_comment": comment,
    }
    return slack_api("files.completeUploadExternal", payload)

def post_media_or_fallback(label, comment, media_url, filename, thread_ts):
    """Try to upload media inline; if upload fails, post text + URL as a fallback message."""
    if media_url:
        try:
            result = slack_upload_to_thread(SLACK_CHANNEL_ID, thread_ts, media_url, filename, comment)
            if result.get("ok"):
                return result
            print(f"  Upload returned not-ok for {label}: {result}")
        except Exception as e:
            print(f"  Upload threw for {label}: {e}")
    fallback_text = f"{comment}\nMedia: {media_url}" if media_url else comment
    return slack_post(
        SLACK_CHANNEL_ID,
        [{"type": "section", "text": {"type": "mrkdwn", "text": fallback_text[:3000]}}],
        thread_ts=thread_ts,
        text_fallback=label,
    )

def save_state():
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

# Pre-flight gate: refuse to post ANYTHING to Slack if any asset isn't openable.
# Catie should never receive a review with a broken preview or missing media.
# Only enforced before the thread exists — once the header is up we just fill in
# any still-missing replies (a re-run shouldn't be blocked by a later hiccup).
if not state.get("slack_thread_ts"):
    problems = preflight(preview_url, posts)
    if problems:
        state["slack_error"] = " | ".join(problems)
        save_state()
        print(f"PRE-FLIGHT FAILED — refusing to post to Slack ({len(problems)} issue(s)):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    state["preview_url"] = preview_url  # persist the normalized (Pages) URL

thread_ts = state.get("slack_thread_ts")
if thread_ts:
    print(f"Header already posted (ts: {thread_ts}). Will post any missing thread replies.")
else:
    main_blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"\U0001f3a8 Zenie — Week of {week}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*{len(posts)} posts ready for review.* <{preview_url}|Open preview ↗>\nReact ✅ to approve or reply with feedback."}},
        {"type": "divider"}
    ]
    result = slack_post(SLACK_CHANNEL_ID, main_blocks, text_fallback=f"Zenie Week of {week}")
    if not result.get("ok"):
        print("Error posting to Slack:", result)
        sys.exit(1)
    thread_ts = result["ts"]
    state["slack_thread_ts"] = thread_ts
    state["slack_error"] = None
    save_state()
    print(f"Posted main message. Thread ts: {thread_ts}")

any_posted = False
for post in posts:
    if post.get("slack_posted"):
        continue
    label = post.get("label", "Post")
    post_type = (post.get("post_type") or "").lower()
    if post_type == "meme":
        comment = (
            f"*{label} — Meme*\n_{post.get('overlay_text', '')}_\n\n"
            f"*IG:* {post.get('ig_caption', '')}\n`{post.get('hashtags', '')}`"
        )
        filename = f"{label.replace(' ', '_').lower()}.mp4"
        # New schema uses media_url for all post types; older runs used mp4_url for memes.
        meme_url = post.get("media_url") or post.get("mp4_url") or ""
        reply = post_media_or_fallback(label, comment, meme_url, filename, thread_ts)
    elif post_type == "repost":
        hashtags = post.get('hashtags', '')
        hashtags_line = f"\n`{hashtags}`" if hashtags else ""
        text = f"*{label} — Repost*\nFrom @{post.get('creator', '')} — {post.get('url', '')}\n*Caption:* {post.get('ig_caption', '')}{hashtags_line}"
        reply = slack_post(
            SLACK_CHANNEL_ID,
            [{"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}],
            thread_ts=thread_ts,
            text_fallback=label,
        )
    elif post_type in ("quote", "quote image"):
        comment = (
            f"*{label} — Quote (FB only)*\n\"{post.get('quote', '')}\" — {post.get('attribution', '')}\n"
            f"*FB caption:* {post.get('fb_caption', '')}\n`{post.get('hashtags', '')}`"
        )
        filename = f"{label.replace(' ', '_').lower()}.jpg"
        reply = post_media_or_fallback(label, comment, post.get("media_url", ""), filename, thread_ts)
    else:
        print(f"Skipping {label}: unknown post_type {post.get('post_type')!r}")
        continue
    if not reply.get("ok"):
        print(f"Error posting {label} to thread:", reply)
        save_state()
        sys.exit(1)
    post["slack_posted"] = True
    any_posted = True
    print(f"Posted {label} to thread")

save_state()
if any_posted:
    print("Updated review-state.json")
else:
    print("No new replies to post.")
