#!/usr/bin/env python3
"""Find real Instagram reels for Zenie to repost, with verified creator handles.

Web search can't surface individual reel links (it failed the weeks of 2026-10-05
and 2026-10-12, so both weeks' reposts shipped with no link). Instead, this uses
Meta's Instagram Business Discovery API, through Zenie's own Instagram account, to
list the recent reels of each account in Zenie's verified cohort
(formats/zenie.json -> cohort.accounts). Every link it returns is a real reel and
every handle is the account that published it.

Writes repost_library/library.json (the drafting agent picks from it in Step 2B),
skipping anything already in repost_library/used.json. Runs Sunday after the Meta
token refresh, before the Monday drafting run.

Env: PAGE_ACCESS_TOKEN, IG_USER_ID. DRY_RUN=1 prints instead of writing.
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "17841465217874624")
API_BASE = "https://graph.facebook.com/v21.0"
DRY_RUN = os.environ.get("DRY_RUN", "") not in ("", "0", "false")

COHORT_PATH = "formats/zenie.json"
LIBRARY_PATH = "repost_library/library.json"
USED_PATH = "repost_library/used.json"

MAX_AGE_DAYS = 120        # older reels read as stale reposts
PER_ACCOUNT = 3           # keep the top N reels per creator so one account can't dominate
MEDIA_LIMIT = 30          # recent posts to scan per account


def norm_url(u):
    """Must stay identical to mark_reposts_used.py and AGENT_INSTRUCTIONS.md Step 2B."""
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.split("?")[0].split("#")[0].rstrip("/")


def discover(handle):
    fields = (f"business_discovery.username({handle})"
              f"{{username,followers_count,media.limit({MEDIA_LIMIT})"
              f"{{permalink,media_type,media_product_type,caption,like_count,comments_count,timestamp}}}}")
    qs = urllib.parse.urlencode({"fields": fields, "access_token": PAGE_ACCESS_TOKEN})
    req = urllib.request.Request(f"{API_BASE}/{IG_USER_ID}?{qs}", headers={"User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("business_discovery", {})


def main():
    if not PAGE_ACCESS_TOKEN:
        sys.exit("find_reposts: PAGE_ACCESS_TOKEN is not set")
    handles = [a["handle"].lstrip("@") for a in json.load(open(COHORT_PATH))["cohort"]["accounts"]]
    try:
        used = {norm_url(u.get("url")) for u in json.load(open(USED_PATH)).get("used", [])}
    except Exception:
        used = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    reels, failures = [], []
    for h in handles:
        try:
            bd = discover(h)
        except Exception as e:  # personal (non-business) accounts aren't discoverable; skip them
            body = getattr(e, "read", lambda: b"")().decode("utf-8", "ignore")[:200]
            failures.append(f"@{h}: {e} {body}".strip())
            continue
        followers = bd.get("followers_count") or 0
        mine = []
        for m in bd.get("media", {}).get("data", []):
            is_reel = m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO"
            if not is_reel or not m.get("permalink") or norm_url(m["permalink"]) in used:
                continue
            ts = datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00"))
            if ts < cutoff:
                continue
            likes, comments = m.get("like_count") or 0, m.get("comments_count") or 0
            caption = re.sub(r"\s+", " ", m.get("caption") or "").strip()
            mine.append({
                "url": m["permalink"],
                "creator": bd.get("username") or h,
                "theme": caption[:280],          # what the reel is about, for writing the prompt
                "likes": likes,
                "comments": comments,
                "engagement_rate": round((likes + 3 * comments) / followers, 5) if followers else None,
                "posted": ts.date().isoformat(),
                "source": "business_discovery",
            })
        mine.sort(key=lambda r: (r["engagement_rate"] or 0), reverse=True)
        reels.extend(mine[:PER_ACCOUNT])

    reels.sort(key=lambda r: (r["engagement_rate"] or 0), reverse=True)
    print(f"find_reposts: {len(reels)} unused reels from {len(handles) - len(failures)}/{len(handles)} accounts")
    for f in failures:
        print("  skipped", f)
    if not reels:
        sys.exit("find_reposts: found no reels — check the token's permissions and the log above")

    lib = json.load(open(LIBRARY_PATH))
    lib["reels"] = reels
    lib["refreshed"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lib["skipped_accounts"] = failures
    if DRY_RUN:
        print(json.dumps(reels[:5], indent=2, ensure_ascii=False))
        return
    json.dump(lib, open(LIBRARY_PATH, "w"), indent=2, ensure_ascii=False)
    open(LIBRARY_PATH, "a").write("\n")


if __name__ == "__main__":
    main()
