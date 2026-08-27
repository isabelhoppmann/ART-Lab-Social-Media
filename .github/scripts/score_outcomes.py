"""Backfill the Outcome (and Permalink) columns on Zenie Posts from live performance.

Runs Sunday, after the weekly diagnostics. For every Notion row still marked
"Not evaluated", it finds the corresponding live post, scores it against the
trailing median of the last 12 posts on the same platform, and writes the verdict
back.

WHY CAPTIONS AND NOT PERMALINKS
-------------------------------
The obvious join key is the post's permalink, and it does not work here. Zenie's
Instagram posts and all reposts are published by hand through Business Suite, so
nothing in the pipeline ever learns their URL — a permalink-keyed matcher would
silently score only the Facebook posts and leave everything else untouched.

The caption is a better key precisely because we wrote it. It is already sitting
in the Notion row, and it survives the manual posting path unchanged. So we match
on a normalized prefix of the caption and treat the permalink as a bonus: when a
match lands, we fill Permalink in from the live post, which is how those cells get
populated at all.

Matching is deliberately forgiving (hashtags, emoji, punctuation and links are
stripped; only the first PREFIX_LEN characters are compared) because a caption
that got lightly edited at posting time should still match. A caption that was
rewritten wholesale will not, and is reported as unmatched rather than guessed at.

Env: PAGE_ACCESS_TOKEN, IG_USER_ID, FB_PAGE_ID, NOTION_TOKEN.
Set DRY_RUN=1 to print what it would do without writing to Notion.
"""

import urllib.request, urllib.parse, json, os, re, sys, statistics
from datetime import datetime, timezone

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IG_USER_ID        = os.environ.get("IG_USER_ID", "17841465217874624")
FB_PAGE_ID        = os.environ.get("FB_PAGE_ID", "227999857070404")
NOTION_TOKEN      = os.environ.get("NOTION_TOKEN", "")
NOTION_DB         = os.environ.get("NOTION_DB", "24e014f9-d62c-43b2-b474-44072b7eff95")
DRY_RUN           = os.environ.get("DRY_RUN", "") not in ("", "0", "false")

API_BASE   = "https://graph.facebook.com/v21.0"
PREFIX_LEN = 60      # chars of normalized caption compared
MIN_PRIORS = 6       # below this there is no baseline worth dividing by
WINDOW     = 12      # trailing posts that form the median
MIN_FORMAT = 6       # posts of one Post Type before a format-level read is allowed

# Ratio of a post's engagement rate to the trailing median, in descending order.
BANDS = [(2.0, "Winner"), (1.3, "Interesting"), (0.7, "Neutral"), (0.0, "Underperformed")]


def band_for(ratio):
    for floor, name in BANDS:
        if ratio >= floor:
            return name
    return "Underperformed"


def norm(text):
    """Normalize a caption down to comparable prose: no hashtags, links, emoji or
    punctuation. Must behave the same on the Notion side and the live-post side."""
    t = (text or "").lower()
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"#\w+", " ", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def key_of(text):
    n = norm(text)
    return n[:PREFIX_LEN] if len(n) >= 20 else ""   # too short to be distinctive


def parse_ts(s):
    return datetime.fromisoformat(s.replace("+0000", "+00:00"))


# ── Meta ──────────────────────────────────────────────────────────────────────
def api_get(path, params):
    params["access_token"] = PAGE_ACCESS_TOKEN
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    req = urllib.request.Request(f"{API_BASE}/{path}?{qs}",
                                 headers={"User-Agent": "ZenieAgent/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_live_posts():
    """Every recent post on both platforms, with engagement rate and permalink."""
    posts = []
    try:
        media = api_get(f"{IG_USER_ID}/media", {
            "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
            "limit": "50"})
        for p in media.get("data", []):
            reach = saved = 0
            try:
                for m in api_get(f"{p['id']}/insights", {"metric": "reach,saved"}).get("data", []):
                    if m["name"] == "reach":
                        reach = m["values"][0]["value"]
                    elif m["name"] == "saved":
                        saved = m["values"][0]["value"]
            except Exception:
                pass
            posts.append({
                "platform": "IG", "text": p.get("caption", ""),
                "ts": parse_ts(p["timestamp"]), "permalink": p.get("permalink", ""),
                "eng_rate": round((p.get("like_count", 0) + p.get("comments_count", 0) + saved)
                                  / max(reach, 1) * 100, 2)})
        print(f"IG posts fetched: {sum(1 for p in posts if p['platform']=='IG')}")
    except Exception as e:
        print(f"IG fetch failed: {e}")

    try:
        data = api_get(f"{FB_PAGE_ID}/posts", {
            "fields": "id,message,created_time,permalink_url,"
                      "likes.summary(true),comments.summary(true),shares",
            "limit": "50"})
        for p in data.get("data", []):
            likes    = p.get("likes", {}).get("summary", {}).get("total_count", 0)
            comments = p.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares   = p.get("shares", {}).get("count", 0)
            reach    = 0
            try:
                for m in api_get(f"{p['id']}/insights",
                                 {"metric": "post_impressions_unique"}).get("data", []):
                    if m["name"] == "post_impressions_unique":
                        reach = m["values"][0]["value"]
            except Exception:
                pass
            posts.append({
                "platform": "FB", "text": p.get("message", ""),
                "ts": parse_ts(p["created_time"]), "permalink": p.get("permalink_url", ""),
                "eng_rate": round((likes + comments + shares * 2) / max(reach, 1) * 100, 2)})
        print(f"FB posts fetched: {sum(1 for p in posts if p['platform']=='FB')}")
    except Exception as e:
        print(f"FB fetch failed: {e}")
    return posts


# ── Notion ────────────────────────────────────────────────────────────────────
def notion(path, payload=None, method="GET"):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28",
                 "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def plain(prop):
    if not prop:
        return ""
    if prop.get("type") == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if prop.get("type") == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if prop.get("type") == "select":
        return (prop.get("select") or {}).get("name", "")
    return ""


def fetch_unscored_rows():
    """Rows still awaiting a verdict. Paginates; Outcome may legitimately be unset
    on very old rows created before the column existed, so treat empty as unscored."""
    rows, cursor = [], None
    while True:
        body = {"page_size": 100,
                "filter": {"or": [
                    {"property": "Outcome", "select": {"equals": "Not evaluated"}},
                    {"property": "Outcome", "select": {"is_empty": True}}]}}
        if cursor:
            body["start_cursor"] = cursor
        data = notion(f"databases/{NOTION_DB}/query", body, "POST")
        for pg in data.get("results", []):
            props = pg.get("properties", {})
            rows.append({
                "id": pg["id"],
                "name": plain(props.get("Name")),
                "post_type": plain(props.get("Post Type")),
                "format": plain(props.get("Format")),
                "ig": plain(props.get("IG Caption")),
                "fb": plain(props.get("FB Caption")),
            })
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return rows


def write_back(row, outcome, permalink):
    props = {"Outcome": {"select": {"name": outcome}}}
    if permalink:
        props["Permalink"] = {"url": permalink}
    if DRY_RUN:
        print(f"    [dry-run] would set Outcome={outcome}"
              f"{' Permalink=' + permalink if permalink else ''}")
        return True
    try:
        notion(f"pages/{row['id']}", {"properties": props}, "PATCH")
        return True
    except Exception as e:
        print(f"    write failed for {row['name']}: {e}")
        return False


# ── Scoring ───────────────────────────────────────────────────────────────────
def score(live, all_by_platform):
    """Engagement rate against the median of the WINDOW posts that preceded it on
    the same platform. Returns (outcome, ratio, n_priors) or None when there is no
    honest baseline — too few priors, or a median of zero to divide by."""
    priors = [p["eng_rate"] for p in all_by_platform[live["platform"]] if p["ts"] < live["ts"]]
    if len(priors) < MIN_PRIORS:
        return None
    med = statistics.median(priors[:WINDOW])
    if med <= 0:
        return None
    ratio = live["eng_rate"] / med
    return band_for(ratio), round(ratio, 2), min(len(priors), WINDOW)


def main():
    if not PAGE_ACCESS_TOKEN or not NOTION_TOKEN:
        print("score_outcomes: PAGE_ACCESS_TOKEN or NOTION_TOKEN not set — skipping")
        return
    live = fetch_live_posts()
    if not live:
        print("score_outcomes: no live posts retrieved (token may be expired) — skipping")
        return

    by_platform = {"IG": [], "FB": []}
    for p in live:
        by_platform[p["platform"]].append(p)
    for v in by_platform.values():
        v.sort(key=lambda p: p["ts"], reverse=True)

    # Caption prefix -> live post. Later (older) posts must not clobber newer ones.
    index = {}
    for p in sorted(live, key=lambda p: p["ts"]):
        k = key_of(p["text"])
        if k:
            index[(p["platform"], k)] = p

    rows = fetch_unscored_rows()
    print(f"Notion rows awaiting a verdict: {len(rows)}\n")

    scored, unmatched, no_baseline = [], [], []
    for row in rows:
        match = None
        for platform, text in (("IG", row["ig"]), ("FB", row["fb"])):
            k = key_of(text)
            if k and (platform, k) in index:
                match = index[(platform, k)]
                break
        if not match:
            unmatched.append(row)
            continue
        result = score(match, by_platform)
        if not result:
            no_baseline.append(row)
            continue
        outcome, ratio, n = result
        print(f"  {row['name']} [{match['platform']}] "
              f"{match['eng_rate']}% vs median of {n} -> {ratio}x -> {outcome}")
        if write_back(row, outcome, match.get("permalink", "")):
            scored.append({"name": row["name"], "post_type": row["post_type"],
                           "format": row["format"],
                           "platform": match["platform"], "eng_rate": match["eng_rate"],
                           "ratio": ratio, "outcome": outcome})

    # ── Format-level read ────────────────────────────────────────────────────
    # Per-post outcomes are bookkeeping. The only conclusion anyone should ACT on
    # is a format holding up across enough posts to outrun the noise, so anything
    # thinner than MIN_FORMAT is reported as "no read" rather than as a trend.
    # Grouped by Format first (the proven-format the post was an instance of) and
    # by Post Type second, because "did the mechanism-reveal format work" is a more
    # actionable question than "did memes work".
    def rollup(key):
        groups = {}
        for s in scored:
            groups.setdefault(s.get(key) or "Unassigned", []).append(s["ratio"])
        return groups

    reads = {}
    for dimension, key in (("format", "format"), ("post_type", "post_type")):
        print(f"\n=== READ BY {dimension.upper().replace('_', ' ')} ===")
        dim_reads = {}
        for fmt, ratios in sorted(rollup(key).items()):
            if len(ratios) < MIN_FORMAT:
                dim_reads[fmt] = {"n": len(ratios), "verdict": "no read yet"}
                print(f"  {fmt}: {len(ratios)}/{MIN_FORMAT} posts — no read yet, change nothing")
            else:
                med = round(statistics.median(ratios), 2)
                verdict = ("outperforming" if med >= 1.3 else
                           "underperforming" if med <= 0.7 else "holding steady")
                dim_reads[fmt] = {"n": len(ratios), "median_ratio": med, "verdict": verdict}
                print(f"  {fmt}: {len(ratios)} posts, median {med}x — {verdict}")
        reads[dimension] = dim_reads

    print(f"\nScored {len(scored)} | unmatched {len(unmatched)} | "
          f"no baseline yet {len(no_baseline)}")
    for r in unmatched:
        print(f"  unmatched: {r['name']}")

    os.makedirs("reports", exist_ok=True)
    out = f"reports/{datetime.now(timezone.utc):%Y-%m-%d}-outcomes.json"
    with open(out, "w") as f:
        json.dump({"scored": scored, "reads": reads,
                   "unmatched": [r["name"] for r in unmatched],
                   "no_baseline": [r["name"] for r in no_baseline]},
                  f, indent=2, ensure_ascii=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
