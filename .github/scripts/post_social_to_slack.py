import json, urllib.request, sys, os

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

def slack_post(channel, blocks, thread_ts=None):
    payload = {"channel": channel, "blocks": blocks}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)

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
    result = slack_post(SLACK_CHANNEL_ID, main_blocks)
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
        text = f"*{label} — Meme*\n_{post.get('overlay_text', '')}_\n\n*IG:* {post.get('ig_caption', '')}\n`{post.get('hashtags', '')}`\nGIF: {post.get('gif_url', '')}"
    elif post_type == "repost":
        text = f"*{label} — Repost*\nFrom @{post.get('creator', '')} — {post.get('url', '')}\n*Caption:* {post.get('ig_caption', '')}"
    elif post_type in ("quote", "quote image"):
        media = post.get("media_url", "")
        media_line = f"\nImage: {media}" if media else ""
        text = f"*{label} — Quote (FB only)*\n\"{post.get('quote', '')}\" — {post.get('attribution', '')}\n*FB caption:* {post.get('fb_caption', '')}\n`{post.get('hashtags', '')}`{media_line}"
    else:
        print(f"Skipping {label}: unknown post_type {post.get('post_type')!r}")
        continue
    reply = slack_post(SLACK_CHANNEL_ID, [{"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}], thread_ts=thread_ts)
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
