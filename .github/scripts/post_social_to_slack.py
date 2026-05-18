import json, urllib.request, sys, os

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = "C0B32JUDVD3"

with open("social/review-state.json") as f:
    state = json.load(f)

if state.get("slack_thread_ts"):
    print(f"Already posted to Slack (ts: {state['slack_thread_ts']}). Skipping.")
    sys.exit(0)

week = state.get("week_date", "")
preview_url = state.get("preview_url", "")
posts = state.get("posts", {})

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
print(f"Posted main message. Thread ts: {thread_ts}")

for key, post in posts.items():
    label = post.get("label", key)
    post_type = key.split("_")[0]
    if post_type == "meme":
        text = f"*{label} — Meme*\n_{post.get('overlay_text', '')}_\n\n*IG:* {post.get('ig_caption', '')}\n`{post.get('hashtags', '')}`\nGIF: {post.get('gif_url', '')}"
    elif post_type == "repost":
        text = f"*{label} — Repost*\nFrom @{post.get('creator', '')} — {post.get('url', '')}\n*Caption:* {post.get('ig_caption', '')}"
    elif post_type == "quote":
        text = f"*{label} — Quote (FB only)*\n\"{post.get('quote', '')}\" — {post.get('attribution', '')}\n*FB caption:* {post.get('fb_caption', '')}\n`{post.get('hashtags', '')}`"
    else:
        continue
    slack_post(SLACK_CHANNEL_ID, [{"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}], thread_ts=thread_ts)
    print(f"Posted {label} to thread")

state["slack_thread_ts"] = thread_ts
state["slack_error"] = None
with open("social/review-state.json", "w") as f:
    json.dump(state, f, indent=2)
print("Updated review-state.json with thread_ts:", thread_ts)
