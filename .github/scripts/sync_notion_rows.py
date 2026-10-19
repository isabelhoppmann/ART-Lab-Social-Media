#!/usr/bin/env python3
"""Make the Zenie Posts rows for quotes and reposts match social/review-state.json.

The drafting agent used to write these rows itself through the Notion MCP, and it
paraphrased: the week of 2026-10-19 landed in Notion with shorter captions, no
journaling prompt and no hashtags, while review-state (and Slack) had the real
ones. This copies the exact captions across instead. Memes are already handled by
regenerate_memes.py.

Upserts by Name ("Quote 1 — 2026-10-19"). Updates captions, hashtags, link,
hypothesis, format and best time; never touches Status, Posted At, Permalink or
Outcome. Posts nothing anywhere else. Env: NOTION_TOKEN."""
import json, os, urllib.request

TOKEN = os.environ.get("NOTION_TOKEN", "")
DB = "24e014f9-d62c-43b2-b474-44072b7eff95"   # Zenie Posts
STATE = "social/review-state.json"
TYPES = {"quote": "Quote Image", "quote image": "Quote Image", "repost": "Repost"}


def notion(path, payload=None, method="GET"):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28",
                 "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def text(s):
    return {"rich_text": [{"text": {"content": (s or "")[:2000]}}]}


def main():
    if not TOKEN:
        print("sync_notion_rows: NOTION_TOKEN not set — skipping"); return
    state = json.load(open(STATE))
    week = state.get("week_date", "")
    changed = False
    for post in state.get("posts", []):
        ptype = TYPES.get((post.get("post_type") or "").lower())
        if not ptype:
            continue
        name = f"{post.get('label', '')} — {week}"
        link = post.get("media_url") if ptype == "Quote Image" else post.get("url")
        props = {
            "IG Caption": text(post.get("ig_caption")),
            "FB Caption": text(post.get("fb_caption")),
            "Hashtags": text(post.get("hashtags")),
            "Media URL": {"url": link or None},
            "Hypothesis": text(post.get("hypothesis")),
            "Best Time": text(post.get("best_time")),
        }
        if post.get("format_slug"):
            props["Format"] = {"select": {"name": post["format_slug"]}}
        hits = notion(f"databases/{DB}/query", {"filter": {"property": "Name", "title": {"equals": name}}}, "POST")["results"]
        if hits:
            for h in hits:
                notion(f"pages/{h['id']}", {"properties": props}, "PATCH")
            page_id = hits[0]["id"]
            print(f"  updated {name} ({len(hits)} row{'s' if len(hits) > 1 else ''})")
        else:
            props.update({"Name": {"title": [{"text": {"content": name}}]},
                          "Post Type": {"select": {"name": ptype}},
                          "Status": {"select": {"name": "Draft"}},
                          "Outcome": {"select": {"name": "Not evaluated"}}})
            if week:
                props["Week"] = {"date": {"start": week}}
            if post.get("scheduled_date"):
                props["Scheduled Date"] = {"date": {"start": post["scheduled_date"]}}
            page_id = notion("pages", {"parent": {"database_id": DB}, "properties": props}, "POST")["id"]
            print(f"  created {name}")
        if post.get("notion_page_id") != page_id:
            post["notion_page_id"] = page_id
            changed = True
    if changed:
        print("  (notion_page_id values differ from review-state; not written back, to avoid re-triggering Slack)")


if __name__ == "__main__":
    main()
