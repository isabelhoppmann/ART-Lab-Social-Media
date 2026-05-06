# Zenie Weekly Diagnostics Agent Instructions

`PAGE_ACCESS_TOKEN`, `IG_USER_ID`, and `FB_PAGE_ID` are available as environment variables.
`GITHUB_TOKEN` is passed in the invoking message.

## OVERVIEW

You run every Sunday evening. Your output is a polished HTML performance report pushed to
`reports/YYYY-MM-DD.html` in the `isabelhoppmann/ART-Lab-Social-Media` GitHub repo, plus an
updated `reports/index.html`.

The report is designed to be presented to a non-technical boss. It must include:
- A concise boss brief (3–4 sentences, narrative, data-backed)
- Key performance KPIs for the week with week-over-week delta
- Chart.js charts: 8-week trend, this week's posts, content type breakdown, IG vs FB comparison
- What worked / what didn't this week
- Running patterns from the full historical dataset

---

## Step 0: Pull performance data from Instagram and Facebook

```python
import urllib.request, urllib.parse, json, os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "17841465217874624")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "227999857070404")
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

# Pull last 50 IG posts
ig_posts = []
try:
    media = api_get(f"{IG_USER_ID}/media", {
        "fields": "id,media_type,timestamp,like_count,comments_count,caption",
        "limit": "50"
    })
    for post in media.get("data", []):
        saved = reach = 0
        try:
            ins = api_get(f"{post['id']}/insights", {"metric": "reach,saved"})
            for m in ins.get("data", []):
                if m["name"] == "reach": reach = m["values"][0]["value"]
                elif m["name"] == "saved": saved = m["values"][0]["value"]
        except Exception:
            pass
        post["reach"] = reach
        post["saved"] = saved
        post["eng_rate"] = round(
            (post.get("like_count", 0) + post.get("comments_count", 0) + saved) / max(reach, 1) * 100, 2
        )
        post["platform"] = "IG"
        ig_posts.append(post)
except Exception as e:
    print(f"IG fetch failed: {e}")

# Pull last 50 FB posts
fb_posts = []
try:
    posts = api_get(f"{FB_PAGE_ID}/posts", {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
        "limit": "50"
    })
    for post in posts.get("data", []):
        likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = post.get("shares", {}).get("count", 0)
        reach = 0
        try:
            ins = api_get(f"{post['id']}/insights", {"metric": "post_impressions_unique"})
            for m in ins.get("data", []):
                if m["name"] == "post_impressions_unique": reach = m["values"][0]["value"]
        except Exception:
            pass
        post["likes_count"] = likes
        post["comments_count"] = comments
        post["shares_count"] = shares
        post["reach"] = reach
        post["eng_rate"] = round(
            (likes + comments + shares * 2) / max(reach, 1) * 100, 2
        )
        post["platform"] = "FB"
        post["timestamp"] = post["created_time"]
        fb_posts.append(post)
except Exception as e:
    print(f"FB fetch failed: {e}")
```

---

## Step 1: Separate this week vs historical

```python
now = datetime.now(timezone.utc)
week_ago = now - timedelta(days=7)

def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("+0000", "+00:00"))

ig_this_week = [p for p in ig_posts if parse_ts(p["timestamp"]) >= week_ago]
ig_historical = [p for p in ig_posts if parse_ts(p["timestamp"]) < week_ago]
fb_this_week = [p for p in fb_posts if parse_ts(p["timestamp"]) >= week_ago]
fb_historical = [p for p in fb_posts if parse_ts(p["timestamp"]) < week_ago]

print(f"This week: {len(ig_this_week)} IG posts, {len(fb_this_week)} FB posts")
print(f"Historical: {len(ig_historical)} IG posts, {len(fb_historical)} FB posts")
```

---

## Step 2: Compute metrics

```python
def avg(lst):
    return round(sum(lst) / len(lst), 2) if lst else 0

# This week
ig_week_avg_er    = avg([p["eng_rate"] for p in ig_this_week])
fb_week_avg_er    = avg([p["eng_rate"] for p in fb_this_week])
ig_week_reach     = sum(p["reach"] for p in ig_this_week)
ig_week_saves     = sum(p["saved"] for p in ig_this_week)
fb_week_shares    = sum(p.get("shares_count", 0) for p in fb_this_week)

# Historical baseline
ig_hist_avg_er = avg([p["eng_rate"] for p in ig_historical])
fb_hist_avg_er = avg([p["eng_rate"] for p in fb_historical])

# Group historical by ISO week to build 8-week trend
def iso_week_key(ts_str):
    dt = parse_ts(ts_str)
    y, w, _ = dt.isocalendar()
    # Return Monday of that week as a label
    monday = dt - timedelta(days=dt.weekday())
    return (y, w, monday.strftime("%b %-d"))

ig_by_week = defaultdict(list)
for p in ig_historical:
    ig_by_week[iso_week_key(p["timestamp"])].append(p["eng_rate"])

fb_by_week = defaultdict(list)
for p in fb_historical:
    fb_by_week[iso_week_key(p["timestamp"])].append(p["eng_rate"])

all_week_keys = sorted(set(list(ig_by_week.keys()) + list(fb_by_week.keys())))[-7:]
week_labels   = [k[2] for k in all_week_keys] + ["This week"]
ig_weekly_avgs = [avg(ig_by_week[k]) for k in all_week_keys] + [ig_week_avg_er]
fb_weekly_avgs = [avg(fb_by_week[k]) for k in all_week_keys] + [fb_week_avg_er]

# Week-over-week delta
ig_prior_avg = ig_weekly_avgs[-2] if len(ig_weekly_avgs) >= 2 else ig_hist_avg_er
fb_prior_avg = fb_weekly_avgs[-2] if len(fb_weekly_avgs) >= 2 else fb_hist_avg_er
ig_wow_delta = round(ig_week_avg_er - ig_prior_avg, 2)
fb_wow_delta = round(fb_week_avg_er - fb_prior_avg, 2)

# Content type breakdown (IG only: VIDEO = memes, IMAGE = quotes)
ig_meme_avg  = avg([p["eng_rate"] for p in ig_posts if p.get("media_type") == "VIDEO"])
ig_quote_avg = avg([p["eng_rate"] for p in ig_posts if p.get("media_type") == "IMAGE"])

# Best/worst posts this week
all_this_week = sorted(ig_this_week + fb_this_week, key=lambda p: p["eng_rate"], reverse=True)
best_post  = all_this_week[0]  if all_this_week else None
worst_post = all_this_week[-1] if len(all_this_week) > 1 else None

# Per-post chart data (horizontal bar, sorted best to worst)
post_labels = []
post_ers    = []
post_colors = []
for p in all_this_week:
    caption = (p.get("caption") or p.get("message") or "").replace("\n", " ").strip()
    label = f"{'IG' if p['platform']=='IG' else 'FB'}: {caption[:38]}{'…' if len(caption)>38 else ''}"
    post_labels.append(label)
    post_ers.append(p["eng_rate"])
    post_colors.append("#6B3FA0" if p["platform"] == "IG" else "#F0A0C0")

print(f"\nIG this week: {ig_week_avg_er}% ER ({ig_wow_delta:+.2f}% vs last week)")
print(f"FB this week: {fb_week_avg_er}% ER ({fb_wow_delta:+.2f}% vs last week)")
print(f"IG meme avg ER (all time): {ig_meme_avg}% | quote avg: {ig_quote_avg}%")
```

---

## Step 3: Identify patterns and what worked / what didn't

Based on the data, write these as Python string lists:

**`patterns`** — 4–6 bullet points about what the data shows *over time* (not just this week). Address:
- Is IG or FB trending up/flat/down over 8 weeks?
- Which content type (memes vs quotes) outperforms on IG, and by how much?
- Are saves trending up (positive algorithm signal)?
- Any day-of-week pattern in the top-performing posts?
- Any other meaningful signal in the data.

**`what_worked`** — 2–3 bullet points about what specifically performed well *this week*.
Include the best post with its metric, and any theme/format that outperformed.

**`what_didnt`** — 2–3 bullet points about what underperformed *this week*.
Include the worst post and any format or topic that fell flat.

Example structure (write based on real data, do not copy):
```python
patterns = [
    "Memes (video) outperform quote images on Instagram — avg 4.2% vs 2.1% engagement rate historically.",
    "Overall IG engagement has trended up 22% over 8 weeks, now consistently above the baseline.",
    "FB engagement remains low across all post types — shares are the primary signal there.",
    "IG saves are increasing week-over-week, a strong indicator the algorithm is broadening reach.",
    "Wednesday and Friday evening posts consistently appear in the top performers.",
]

what_worked = [
    "\"Day 3 of journaling\" meme — 6.2% ER and 43 saves, highest save count in 6 weeks.",
    "Meme format in general outperformed all other content this week (avg 5.1% vs 2.8% for images).",
]

what_didnt = [
    "Carl Jung quote image — 1.4% ER, well below the 2.8% image baseline.",
    "Long-form FB captions on the quote posts drove zero shares this week.",
]
```

---

## Step 4: Write the boss brief

Write `boss_brief` as a single string: 3–4 sentences. This is what Isabel presents to her ART Lab boss.

Guidelines:
- Lead with the headline metric (IG avg ER this week vs prior week or baseline)
- Name the best post specifically and what made it work
- State the single most important strategic pattern
- Close with one forward-looking recommendation

Tone: confident, data-backed, concise. Not fluffy. Appropriate for a startup context.

---

## Step 5: Generate the HTML report

```python
import json as _json

def build_report_html(today_str, week_start_str, week_end_str):
    ig_wow_sign  = "+" if ig_wow_delta >= 0 else ""
    fb_wow_sign  = "+" if fb_wow_delta >= 0 else ""
    ig_wow_color = "#22c55e" if ig_wow_delta >= 0 else "#ef4444"
    fb_wow_color = "#22c55e" if fb_wow_delta >= 0 else "#ef4444"

    best_caption  = (best_post.get("caption") or best_post.get("message") or "")[:50].replace("\n"," ") if best_post else "N/A"
    worst_caption = (worst_post.get("caption") or worst_post.get("message") or "")[:50].replace("\n"," ") if worst_post else "N/A"
    best_er  = best_post["eng_rate"]  if best_post  else 0
    worst_er = worst_post["eng_rate"] if worst_post else 0

    worked_li  = "\n".join(f"<li>{item}</li>" for item in what_worked)
    didnt_li   = "\n".join(f"<li>{item}</li>" for item in what_didnt)
    pattern_li = "\n".join(f"<li>{item}</li>" for item in patterns)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Weekly Report — {today_str}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{ --purple:#6B3FA0; --lavender:#C9B1E8; --pink:#F0A0C0; --bg:#f0ebf8; --text:#1a1a2e; }}
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); }}
  .header{{ background:linear-gradient(135deg,#6B3FA0 0%,#9b59d0 100%); color:white; padding:36px 40px 28px; }}
  .header h1{{ font-size:1.8em; font-weight:700; margin-bottom:4px; }}
  .header .meta{{ font-size:.9em; opacity:.8; }}
  .container{{ max-width:960px; margin:0 auto; padding:28px 20px 60px; }}
  .card{{ background:white; border-radius:14px; padding:24px; box-shadow:0 2px 16px rgba(107,63,160,.09); margin-bottom:22px; }}
  .brief-card{{ border-left:5px solid var(--purple); }}
  .brief-card h2,.section-label{{ font-size:.72em; text-transform:uppercase; letter-spacing:.12em; color:var(--purple); margin-bottom:12px; font-weight:700; }}
  .brief-card p{{ font-size:1.05em; line-height:1.75; color:#333; }}
  .kpi-grid{{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
  .kpi{{ background:white; border-radius:14px; padding:20px 16px; text-align:center; box-shadow:0 2px 12px rgba(107,63,160,.08); }}
  .kpi .val{{ font-size:2em; font-weight:700; color:var(--purple); line-height:1.1; }}
  .kpi .delta{{ font-size:.82em; font-weight:600; margin-top:3px; }}
  .kpi .lbl{{ font-size:.7em; color:#999; text-transform:uppercase; letter-spacing:.08em; margin-top:6px; }}
  .chart-row{{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:22px; }}
  .chart-card canvas{{ max-height:240px; }}
  .worked-row{{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:22px; }}
  .worked-card h3{{ font-size:.75em; text-transform:uppercase; letter-spacing:.1em; margin-bottom:14px; font-weight:700; }}
  .worked-card.good h3{{ color:#22c55e; }}
  .worked-card.bad h3{{ color:#ef4444; }}
  .worked-card ul,.patterns-list{{ list-style:none; padding:0; }}
  .worked-card ul li,.patterns-list li{{ font-size:.88em; line-height:1.55; padding:9px 0; border-bottom:1px solid #f0ebf8; color:#444; }}
  .worked-card ul li:last-child,.patterns-list li:last-child{{ border-bottom:none; }}
  .patterns-list li{{ padding-left:18px; position:relative; }}
  .patterns-list li::before{{ content:"→"; position:absolute; left:0; color:var(--purple); font-weight:700; }}
  @media(max-width:640px){{
    .kpi-grid{{ grid-template-columns:1fr 1fr; }}
    .chart-row,.worked-row{{ grid-template-columns:1fr; }}
  }}
  @media print{{
    body{{ background:white; }}
    .header{{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .card,.kpi{{ box-shadow:none; border:1px solid #e8e0f5; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Zenie Weekly Report</h1>
  <div class="meta">Week of {week_start_str} – {week_end_str} &nbsp;·&nbsp; Generated {today_str}</div>
</div>

<div class="container">

  <div class="card brief-card">
    <h2>Boss Brief</h2>
    <p>{boss_brief}</p>
  </div>

  <div class="kpi-grid">
    <div class="kpi">
      <div class="val">{ig_week_avg_er}%</div>
      <div class="delta" style="color:{ig_wow_color}">{ig_wow_sign}{ig_wow_delta}% vs last week</div>
      <div class="lbl">IG Avg Engagement</div>
    </div>
    <div class="kpi">
      <div class="val">{fb_week_avg_er}%</div>
      <div class="delta" style="color:{fb_wow_color}">{fb_wow_sign}{fb_wow_delta}% vs last week</div>
      <div class="lbl">FB Avg Engagement</div>
    </div>
    <div class="kpi">
      <div class="val">{ig_week_reach:,}</div>
      <div class="lbl">IG Total Reach</div>
    </div>
    <div class="kpi">
      <div class="val">{ig_week_saves}</div>
      <div class="lbl">IG Total Saves</div>
    </div>
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="section-label">8-Week Engagement Trend</div>
      <canvas id="trendChart"></canvas>
    </div>
    <div class="card">
      <div class="section-label">This Week — Posts by Engagement Rate</div>
      <canvas id="postsChart"></canvas>
    </div>
  </div>

  <div class="chart-row">
    <div class="card">
      <div class="section-label">Content Type — IG Historical Avg ER</div>
      <canvas id="typeChart"></canvas>
    </div>
    <div class="card">
      <div class="section-label">IG vs FB — This Week vs 8-Week Avg</div>
      <canvas id="platformChart"></canvas>
    </div>
  </div>

  <div class="worked-row">
    <div class="card worked-card good">
      <h3>✓ What Worked This Week</h3>
      <ul>
        <li><strong>Best post:</strong> "{best_caption}…" — {best_er}% ER</li>
        {worked_li}
      </ul>
    </div>
    <div class="card worked-card bad">
      <h3>✗ What Didn't</h3>
      <ul>
        <li><strong>Lowest post:</strong> "{worst_caption}…" — {worst_er}% ER</li>
        {didnt_li}
      </ul>
    </div>
  </div>

  <div class="card">
    <div class="section-label">Running Patterns — What the Data Shows Over Time</div>
    <ul class="patterns-list">
      {pattern_li}
    </ul>
  </div>

</div>

<script>
const purple='#6B3FA0', lavender='#C9B1E8', pink='#F0A0C0';

new Chart(document.getElementById('trendChart'),{{
  type:'line',
  data:{{
    labels:{_json.dumps(week_labels)},
    datasets:[
      {{label:'Instagram',data:{_json.dumps(ig_weekly_avgs)},borderColor:purple,backgroundColor:'rgba(107,63,160,.08)',tension:.35,fill:true,pointRadius:4,pointBackgroundColor:purple}},
      {{label:'Facebook',data:{_json.dumps(fb_weekly_avgs)},borderColor:pink,backgroundColor:'rgba(240,160,192,.08)',tension:.35,fill:true,pointRadius:4,pointBackgroundColor:pink}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});

new Chart(document.getElementById('postsChart'),{{
  type:'bar',
  data:{{
    labels:{_json.dumps(post_labels)},
    datasets:[{{label:'ER %',data:{_json.dumps(post_ers)},backgroundColor:{_json.dumps(post_colors)},borderRadius:5}}]
  }},
  options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});

new Chart(document.getElementById('typeChart'),{{
  type:'bar',
  data:{{
    labels:['Memes (Video)','Quote Images'],
    datasets:[{{label:'Avg ER %',data:[{ig_meme_avg},{ig_quote_avg}],backgroundColor:[purple,lavender],borderRadius:6}}]
  }},
  options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});

new Chart(document.getElementById('platformChart'),{{
  type:'bar',
  data:{{
    labels:['Instagram','Facebook'],
    datasets:[
      {{label:'This Week',data:[{ig_week_avg_er},{fb_week_avg_er}],backgroundColor:[purple,pink],borderRadius:6}},
      {{label:'8-Week Avg',data:[{ig_hist_avg_er},{fb_hist_avg_er}],backgroundColor:[lavender,'rgba(240,160,192,.5)'],borderRadius:6}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});
</script>
</body>
</html>"""

today_str      = now.strftime("%Y-%m-%d")
week_start_str = (now - timedelta(days=6)).strftime("%b %-d")
week_end_str   = now.strftime("%b %-d, %Y")

html = build_report_html(today_str, week_start_str, week_end_str)

with open(f"/tmp/zenie_report_{today_str}.html", "w") as f:
    f.write(html)
print(f"HTML built: {len(html):,} chars")
```

---

## Step 6: Push report to GitHub and update reports/index.html

```python
import base64

GITHUB_TOKEN = "GITHUB_TOKEN_FROM_INVOKING_MESSAGE"
REPO = "isabelhoppmann/ART-Lab-Social-Media"

def push_file(path, content_bytes, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    sha = None
    try:
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {GITHUB_TOKEN}", "User-Agent": "ZenieAgent/1.0"
        })
        with urllib.request.urlopen(req) as r:
            sha = json.load(r)["sha"]
    except Exception:
        pass
    payload = {"message": message, "content": base64.b64encode(content_bytes).decode()}
    if sha:
        payload["sha"] = sha
    req = urllib.request.Request(url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"token {GITHUB_TOKEN}", "Content-Type": "application/json", "User-Agent": "ZenieAgent/1.0"},
        method="PUT"
    )
    with urllib.request.urlopen(req) as r:
        print(f"Pushed {path}: {r.status}")

# Push the report
with open(f"/tmp/zenie_report_{today_str}.html", "rb") as f:
    push_file(f"reports/{today_str}.html", f.read(), f"Weekly diagnostics report {today_str}")

# Update reports/index.html
FRESH_INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Weekly Reports</title>
<style>
  body{font-family:-apple-system,sans-serif;max-width:580px;margin:0 auto;padding:40px 20px;background:#f0ebf8;}
  h1{color:#6B3FA0;margin-bottom:24px;}
  a.report{display:flex;justify-content:space-between;align-items:center;background:white;border-radius:12px;padding:16px 20px;margin-bottom:12px;text-decoration:none;color:#1a1a2e;box-shadow:0 2px 8px rgba(107,63,160,.1);}
  a.report:hover{background:#f5f0fa;}
  a.report.latest{border-left:4px solid #6B3FA0;}
  .report-date{font-weight:600;}
  .arrow{color:#6B3FA0;font-weight:700;}
</style>
</head>
<body>
<h1>Zenie Weekly Reports</h1>
<!-- ENTRIES -->
</body></html>"""

index_path = "reports/index.html"
index_sha  = None
index_html = FRESH_INDEX

try:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{index_path}",
        headers={"Authorization": f"token {GITHUB_TOKEN}", "User-Agent": "ZenieAgent/1.0"}
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
        index_sha = data["sha"]
        index_html = base64.b64decode(data["content"]).decode()
except Exception:
    pass  # Will create fresh

new_entry = f'<a class="report latest" href="{today_str}.html"><span class="report-date">Week of {week_start_str} – {week_end_str}</span><span class="arrow">→</span></a>\n'
index_html = index_html.replace('class="report latest"', 'class="report"')
index_html = index_html.replace("<!-- ENTRIES -->", f"<!-- ENTRIES -->\n{new_entry}")

push_file(index_path, index_html.encode(), f"Add weekly report index entry {today_str}")
```

---

## Step 7: Print summary

```
=== ZENIE WEEKLY DIAGNOSTICS COMPLETE ===
Date: [today_str]
IG posts this week: [N] | avg ER: [X]% ([+/-X]% vs last week, baseline [X]%)
FB posts this week: [N] | avg ER: [X]% ([+/-X]% vs last week, baseline [X]%)
IG total reach: [N] | saves: [N]
Best post: "[caption snippet]" — [X]% ER
Report URL: https://isabelhoppmann.github.io/ART-Lab-Social-Media/reports/[today_str].html
==========================================
```
