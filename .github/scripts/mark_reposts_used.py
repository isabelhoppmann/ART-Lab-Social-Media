#!/usr/bin/env python3
"""No-repeat ledger for reposts (mirrors meme_library/used.json and
social/used_quotes.json). Reads social/review-state.json and records every
Repost url as consumed, so the
drafting agent can never pick it again. Idempotent; no-op when nothing matches."""
import json, os, re

STATE_PATH = "social/review-state.json"
USED_PATH = "repost_library/used.json"


def norm_url(u):
    """Match key: lowercase, no scheme/www/query, no trailing slash.
    Must stay identical to the norm in AGENT_INSTRUCTIONS.md Step 2B."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.split("?")[0].split("#")[0].rstrip("/")


def main():
    if not os.path.exists(STATE_PATH):
        print("mark_reposts_used: nothing to do")
        return
    state = json.load(open(STATE_PATH))
    try:
        data = json.load(open(USED_PATH))
    except Exception:
        data = {"used": []}
    used = data.setdefault("used", [])
    seen = {norm_url(u.get("url")) for u in used}
    week = state.get("week_date")
    changed = False
    for post in state.get("posts", []):
        if (post.get("post_type") or "").lower() != "repost":
            continue
        key = norm_url(post.get("url"))
        if key and "instagram.com" in key and key not in seen:
            used.append({"url": post.get("url"), "creator": post.get("creator"),
                         "week": week, "label": post.get("label")})
            seen.add(key)
            changed = True
            print(f"  marked repost used (no-repeat): {post.get('url')}")
    if changed:
        json.dump(data, open(USED_PATH, "w"), indent=2, ensure_ascii=False)
        open(USED_PATH, "a").write("\n")


if __name__ == "__main__":
    main()
