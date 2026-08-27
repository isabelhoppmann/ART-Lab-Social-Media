"""ART Lab weekly review. Reads the ART Lab — Posts Notion table, scores each post
against the trailing median, rolls the results up by Format, and writes a summary.

NO META API. Isabel posts ART Lab content herself and types in Likes/Comments/Reach
after the fact. That is a deliberate choice, not a limitation we're working around:
at this account's size the API's extra precision is worth nothing, and the credential
setup cost is real. The scoring, the format roll-up and the suggestions are identical
to Zenie's; only the source of the numbers differs. When the account is big enough for
the API to matter, swap fetch_rows() and nothing else changes.

Engagement metric: Reach is optional. When present, engagement rate is
(likes + comments) / reach. When absent -- the normal case -- raw (likes + comments)
is used instead. Both are compared only against posts measured the same way, so the
two never mix.

Env: NOTION_TOKEN (already a repo secret), ARTLAB_POSTS_DB.
DRY_RUN=1 prints without writing back.
"""

import importlib.util, json, os, statistics, sys, urllib.request
from datetime import datetime, timezone

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
POSTS_DB     = os.environ.get("ARTLAB_POSTS_DB", "eb0c4ba6-6268-4557-9b98-4c199924b9a4")
DRY_RUN      = os.environ.get("DRY_RUN", "") not in ("", "0", "false")

MIN_PRIORS = 6    # below this there is no baseline worth dividing by
WINDOW     = 12   # trailing posts forming the median
MIN_FORMAT = 6    # posts of one format before a read is allowed
BANDS = [(2.0, "Winner"), (1.3, "Interesting"), (0.7, "Neutral"), (0.0, "Underperformed")]


def load_formats():
    """The format library doubles as the source of each format's EXPECTED effect, so
    a hypothesis can be filled in automatically from the format tag alone. Isabel
    should not have to hand-write a prediction every week to keep the record intact —
    tagging the format already says what the post was betting on."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "formats", "artlab.json")
    try:
        with open(os.path.abspath(path)) as f:
            return {x["slug"]: x for x in json.load(f)["formats"]}
    except Exception as e:
        print(f"(couldn't read formats/artlab.json: {e})")
        return {}


def auto_hypothesis(fmt, formats):
    f = formats.get(fmt)
    if not f:
        return ""
    return (f"[auto] {f['name']}: {f['why_it_works']} "
            f"Expected to perform at or above the recent median for this account.")[:1900]


def band_for(ratio):
    for floor, name in BANDS:
        if ratio >= floor:
            return name
    return "Underperformed"


def notion(path, payload=None, method="GET"):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28",
                 "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def prop(props, name, kind):
    p = props.get(name) or {}
    if kind == "number":
        return p.get("number")
    if kind == "select":
        return (p.get("select") or {}).get("name", "")
    if kind == "date":
        return ((p.get("date") or {}).get("start") or "")
    if kind == "title":
        return "".join(t.get("plain_text", "") for t in p.get("title", []))
    return ""


def fetch_rows():
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = notion(f"databases/{POSTS_DB}/query", body, "POST")
        for pg in data.get("results", []):
            p = pg.get("properties", {})
            likes, comments = prop(p, "Likes", "number"), prop(p, "Comments", "number")
            if likes is None and comments is None:
                continue                      # not filled in yet — skip, don't guess
            posted = prop(p, "Posted At", "date")
            if not posted:
                continue
            hypo = "".join(t.get("plain_text", "")
                           for t in (p.get("Hypothesis") or {}).get("rich_text", []))
            reach = prop(p, "Reach", "number")
            eng = (likes or 0) + (comments or 0)
            rows.append({
                "id": pg["id"],
                "name": prop(p, "Name", "title"),
                "platform": prop(p, "Platform", "select") or "Unknown",
                "format": prop(p, "Format", "select") or "Unassigned",
                "outcome": prop(p, "Outcome", "select"),
                "posted": posted[:10],
                "hypothesis": hypo,
                # Rate when reach is known, raw engagement otherwise. Kept separate
                # below so a rate is never compared against a raw count.
                "metric": (eng / reach * 100) if reach else eng,
                "basis": "rate" if reach else "raw",
            })
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return rows


def write_outcome(row, outcome):
    if DRY_RUN:
        print(f"    [dry-run] would set Outcome={outcome}")
        return True
    try:
        notion(f"pages/{row['id']}", {"properties": {"Outcome": {"select": {"name": outcome}}}}, "PATCH")
        return True
    except Exception as e:
        print(f"    write failed for {row['name']}: {e}")
        return False


def write_hypothesis(row, text):
    if DRY_RUN:
        print(f"    [dry-run] would backfill Hypothesis for {row['name']}")
        return
    try:
        notion(f"pages/{row['id']}",
               {"properties": {"Hypothesis": {"rich_text": [{"text": {"content": text}}]}}},
               "PATCH")
    except Exception as e:
        print(f"    hypothesis backfill failed for {row['name']}: {e}")


def email(subject, body):
    """Deliver the digest instead of leaving it in a JSON file nobody opens.
    Reuses the Gmail sender already in the repo. Email, never Slack — Slack
    carries published content only."""
    try:
        spec = importlib.util.spec_from_file_location(
            "notify", os.path.join(os.path.dirname(__file__), "notify_error_email.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.send(subject, body)
        print("Digest emailed.")
    except Exception as e:
        print(f"(couldn't email digest: {e})")


def main():
    if not NOTION_TOKEN:
        print("artlab_weekly: NOTION_TOKEN not set — skipping"); return
    formats = load_formats()
    rows = fetch_rows()
    if not rows:
        print("artlab_weekly: no posts with numbers filled in yet — nothing to score.")
        print("Add Likes and Comments to a row in 'ART Lab — Posts' and this will pick it up.")
        return
    rows.sort(key=lambda r: r["posted"])
    print(f"Posts with numbers filled in: {len(rows)}\n")

    # Backfill any missing hypothesis from the format tag, so the record stays
    # complete without Isabel writing one by hand each week.
    for row in rows:
        if not row["hypothesis"] and row["format"] != "Unassigned":
            text = auto_hypothesis(row["format"], formats)
            if text:
                write_hypothesis(row, text)
                row["hypothesis"] = text
                print(f"  + filled in hypothesis for {row['name']} from its format")

    scored, no_baseline = [], []
    for i, row in enumerate(rows):
        # Compare only against earlier posts on the same platform measured the same way.
        priors = [r["metric"] for r in rows[:i]
                  if r["platform"] == row["platform"] and r["basis"] == row["basis"]]
        if len(priors) < MIN_PRIORS:
            no_baseline.append(row); continue
        med = statistics.median(priors[-WINDOW:])
        if med <= 0:
            no_baseline.append(row); continue
        ratio = row["metric"] / med
        outcome = band_for(ratio)
        print(f"  {row['name']} [{row['platform']}] {round(row['metric'],2)} "
              f"vs median {round(med,2)} -> {round(ratio,2)}x -> {outcome}")
        if row["outcome"] != outcome and write_outcome(row, outcome):
            pass
        scored.append({**row, "ratio": round(ratio, 2), "outcome": outcome})

    print("\n=== READ BY FORMAT ===")
    groups = {}
    for s in scored:
        groups.setdefault(s["format"], []).append(s["ratio"])
    reads, suggestions = {}, []
    for fmt, ratios in sorted(groups.items()):
        if len(ratios) < MIN_FORMAT:
            reads[fmt] = {"n": len(ratios), "verdict": "no read yet"}
            print(f"  {fmt}: {len(ratios)}/{MIN_FORMAT} posts — no read yet, change nothing")
        else:
            med = round(statistics.median(ratios), 2)
            verdict = ("outperforming" if med >= 1.3 else
                       "underperforming" if med <= 0.7 else "holding steady")
            reads[fmt] = {"n": len(ratios), "median_ratio": med, "verdict": verdict}
            print(f"  {fmt}: {len(ratios)} posts, median {med}x — {verdict}")
            if verdict == "outperforming":
                suggestions.append(f"Lean on {fmt} — {len(ratios)} posts, median {med}x.")
            elif verdict == "underperforming":
                suggestions.append(f"Rest {fmt} — {len(ratios)} posts, median {med}x.")

    if no_baseline:
        print(f"\n{len(no_baseline)} post(s) not scored yet: fewer than {MIN_PRIORS} "
              f"comparable earlier posts. This is expected early on.")
    if not suggestions:
        suggestions.append(
            f"No format has {MIN_FORMAT} scored posts yet, so there is nothing to act on. "
            "Keep posting across formats and log the numbers; the read arrives on its own.")

    print("\n=== SUGGESTIONS ===")
    for s in suggestions:
        print(f"  • {s}")

    os.makedirs("reports", exist_ok=True)
    out = f"reports/artlab-{datetime.now(timezone.utc):%Y-%m-%d}.json"
    with open(out, "w") as f:
        json.dump({"scored": scored, "reads": reads, "suggestions": suggestions,
                   "unscored": [r["name"] for r in no_baseline]}, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {out}")

    lines = [f"ART Lab weekly review — {datetime.now(timezone.utc):%d %B %Y}", ""]
    lines.append(f"Scored {len(scored)} post(s) this run.")
    if no_baseline:
        lines.append(f"{len(no_baseline)} not scored yet — fewer than {MIN_PRIORS} comparable "
                     "earlier posts to compare against. Normal early on.")
    lines += ["", "WHAT THE FORMATS ARE DOING", ""]
    for fmt, r in sorted(reads.items()):
        if "median_ratio" in r:
            lines.append(f"  {fmt}: {r['n']} posts, median {r['median_ratio']}x — {r['verdict']}")
        else:
            lines.append(f"  {fmt}: {r['n']} of {MIN_FORMAT} posts — no read yet")
    lines += ["", "SUGGESTIONS FOR NEXT WEEK", ""]
    lines += [f"  - {s}" for s in suggestions]
    lines += ["", "Nothing here needs a reply. Outcomes are already written back to the",
              "ART Lab — Posts table in Notion."]
    email(f"ART Lab weekly review — {datetime.now(timezone.utc):%Y-%m-%d}", "\n".join(lines))


if __name__ == "__main__":
    main()
