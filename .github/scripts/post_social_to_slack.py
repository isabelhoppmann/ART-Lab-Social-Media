import json, urllib.request, urllib.parse, sys, os

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = "C0B32JUDVD3"
STATE_PATH = "social/review-state.json"

with open(STATE_PATH) as f:
    state = json.load(f)

week = state.get("week_date", "")
preview_url = state.get("preview_url", "")
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
    """Download media bytes and upload as a file attached to a thread reply.
    Returns the completeUploadExternal result. Raises on any network/API failure."""
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
        text = f"*{label} — Repost*\nFrom @{post.get('creator', '')} — {post.get('url', '')}\n*Caption:* {post.get('ig_caption', '')}"
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
