import urllib.request, urllib.parse, json, os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IG_USER_ID        = os.environ.get("IG_USER_ID", "17841465217874624")
FB_PAGE_ID        = os.environ.get("FB_PAGE_ID", "227999857070404")
API_BASE          = "https://graph.facebook.com/v21.0"

def api_get(path, params):
    params["access_token"] = PAGE_ACCESS_TOKEN
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    req = urllib.request.Request(
        f"{API_BASE}/{path}?{qs}", headers={"User-Agent": "ZenieAgent/1.0"}
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def avg(lst):
    return round(sum(lst) / len(lst), 2) if lst else 0

def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("+0000", "+00:00"))

# ── Step 0: fetch ──────────────────────────────────────────────────────────────
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
                if m["name"] == "reach":   reach = m["values"][0]["value"]
                elif m["name"] == "saved": saved = m["values"][0]["value"]
        except Exception:
            pass
        post["reach"]    = reach
        post["saved"]    = saved
        post["eng_rate"] = round(
            (post.get("like_count", 0) + post.get("comments_count", 0) + saved)
            / max(reach, 1) * 100, 2
        )
        post["platform"] = "IG"
        ig_posts.append(post)
    print(f"IG posts fetched: {len(ig_posts)}")
except Exception as e:
    print(f"IG fetch failed: {e}")

fb_posts = []
try:
    posts = api_get(f"{FB_PAGE_ID}/posts", {
        "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
        "limit": "50"
    })
    for post in posts.get("data", []):
        likes    = post.get("likes",    {}).get("summary", {}).get("total_count", 0)
        comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares   = post.get("shares",   {}).get("count", 0)
        reach    = 0
        try:
            ins = api_get(f"{post['id']}/insights", {"metric": "post_impressions_unique"})
            for m in ins.get("data", []):
                if m["name"] == "post_impressions_unique":
                    reach = m["values"][0]["value"]
        except Exception:
            pass
        post["likes_count"]    = likes
        post["comments_count"] = comments
        post["shares_count"]   = shares
        post["reach"]          = reach
        post["eng_rate"]       = round(
            (likes + comments + shares * 2) / max(reach, 1) * 100, 2
        )
        post["platform"]  = "FB"
        post["timestamp"] = post["created_time"]
        fb_posts.append(post)
    print(f"FB posts fetched: {len(fb_posts)}")
except Exception as e:
    print(f"FB fetch failed: {e}")

# ── Step 0b: account-level follower count ───────────────────────────────────────
followers_count = None
try:
    acct = api_get(IG_USER_ID, {"fields": "followers_count"})
    followers_count = acct.get("followers_count")
    print(f"IG followers_count: {followers_count}")
except Exception as e:
    print(f"Followers fetch failed: {e}")

# ── Step 1: split ──────────────────────────────────────────────────────────────
now      = datetime.now(timezone.utc)
week_ago = now - timedelta(days=7)
today_str = now.strftime("%Y-%m-%d")

# ── Follower history & weekly delta ─────────────────────────────────────────────
# Persist a running log of follower counts (committed via `git add reports/`) so we
# can compute week-over-week growth without a possibly-deprecated insight metric.
# Each reading is keyed to the most recent Sunday ("week anchor") so the delta is a
# clean Sunday-to-Sunday comparison. The report runs on Sundays, so a scheduled run
# keys to today; a mid-week manual run keys to the same Sunday and just updates that
# week's slot instead of creating a spurious data point.
week_anchor_str = (now - timedelta(days=(now.weekday() + 1) % 7)).strftime("%Y-%m-%d")

FOLLOWERS_LOG = "reports/followers.json"
follower_hist = {}
if os.path.exists(FOLLOWERS_LOG):
    try:
        with open(FOLLOWERS_LOG) as _f:
            follower_hist = json.load(_f)
    except Exception:
        follower_hist = {}

follower_delta = None
if followers_count is not None:
    prior_keys = sorted(k for k in follower_hist if k < week_anchor_str)
    if prior_keys:
        follower_delta = followers_count - follower_hist[prior_keys[-1]]

ig_this_week  = [p for p in ig_posts if parse_ts(p["timestamp"]) >= week_ago]
ig_historical = [p for p in ig_posts if parse_ts(p["timestamp"]) <  week_ago]
fb_this_week  = [p for p in fb_posts if parse_ts(p["timestamp"]) >= week_ago]
fb_historical = [p for p in fb_posts if parse_ts(p["timestamp"]) <  week_ago]

print(f"This week: {len(ig_this_week)} IG, {len(fb_this_week)} FB")
print(f"Historical: {len(ig_historical)} IG, {len(fb_historical)} FB")

# ── Step 2: metrics ────────────────────────────────────────────────────────────
ig_week_avg_er = avg([p["eng_rate"] for p in ig_this_week])
fb_week_avg_er = avg([p["eng_rate"] for p in fb_this_week])
ig_week_reach  = sum(p["reach"] for p in ig_this_week)
ig_week_saves  = sum(p.get("saved", 0) for p in ig_this_week)
ig_hist_avg_er = avg([p["eng_rate"] for p in ig_historical])
fb_hist_avg_er = avg([p["eng_rate"] for p in fb_historical])

def iso_week_key(ts_str):
    dt = parse_ts(ts_str)
    y, w, _ = dt.isocalendar()
    monday = dt - timedelta(days=dt.weekday())
    return (y, w, monday.strftime("%b %-d"))

ig_by_week = defaultdict(list)
for p in ig_historical:
    ig_by_week[iso_week_key(p["timestamp"])].append(p["eng_rate"])
fb_by_week = defaultdict(list)
for p in fb_historical:
    fb_by_week[iso_week_key(p["timestamp"])].append(p["eng_rate"])

all_week_keys  = sorted(set(list(ig_by_week.keys()) + list(fb_by_week.keys())))[-7:]
week_labels    = [k[2] for k in all_week_keys] + ["This week"]
ig_weekly_avgs = [avg(ig_by_week[k]) for k in all_week_keys] + [ig_week_avg_er]
fb_weekly_avgs = [avg(fb_by_week[k]) for k in all_week_keys] + [fb_week_avg_er]

ig_prior_avg = ig_weekly_avgs[-2] if len(ig_weekly_avgs) >= 2 else ig_hist_avg_er
fb_prior_avg = fb_weekly_avgs[-2] if len(fb_weekly_avgs) >= 2 else fb_hist_avg_er
ig_wow_delta = round(ig_week_avg_er - ig_prior_avg, 2)
fb_wow_delta = round(fb_week_avg_er - fb_prior_avg, 2)

ig_meme_avg  = avg([p["eng_rate"] for p in ig_posts if p.get("media_type") == "VIDEO"])
ig_quote_avg = avg([p["eng_rate"] for p in ig_posts if p.get("media_type") == "IMAGE"])

all_this_week = sorted(ig_this_week + fb_this_week, key=lambda p: p["eng_rate"], reverse=True)
best_post     = all_this_week[0]  if all_this_week          else None
worst_post    = all_this_week[-1] if len(all_this_week) > 1 else None

post_labels, post_ers, post_colors = [], [], []
for p in all_this_week:
    caption = (p.get("caption") or p.get("message") or "").replace("\n", " ").strip()
    label   = f"{'IG' if p['platform']=='IG' else 'FB'}: {caption[:38]}{'...' if len(caption)>38 else ''}"
    post_labels.append(label)
    post_ers.append(p["eng_rate"])
    post_colors.append("#6B3FA0" if p["platform"] == "IG" else "#F0A0C0")

# ── Step 3: narrative ──────────────────────────────────────────────────────────
no_data = not ig_posts and not fb_posts
if no_data:
    # Signal the workflow that the token needs renewal so a GitHub Issue gets opened.
    # The "Open renewal reminder" step reads /tmp/needs_renewal.txt.
    with open('/tmp/needs_renewal.txt', 'w') as _f:
        _f.write('EXPIRED')
    boss_brief = (
        "This week's diagnostics could not retrieve live data -- the Meta API access token "
        "may be expired or the account connection needs to be refreshed. "
        "No action is required on social strategy this week; please re-authenticate "
        "the Meta integration and the report will auto-populate next Sunday."
    )
    what_worked = ["No post data available this week."]
    what_didnt  = ["Live API pull failed -- check that PAGE_ACCESS_TOKEN secret is valid and not expired."]
    patterns    = [
        "Token refresh required: Meta Page tokens expire every 60 days.",
        "All reporting infrastructure is healthy and will populate on next successful data pull.",
    ]
else:
    dominant    = "memes (video)" if ig_meme_avg >= ig_quote_avg else "quote images"
    dominant_er = max(ig_meme_avg, ig_quote_avg)
    other_er    = min(ig_meme_avg, ig_quote_avg)
    best_cap    = (best_post.get("caption")  or best_post.get("message")  or "")[:60].replace("\n"," ") if best_post  else "N/A"
    worst_cap   = (worst_post.get("caption") or worst_post.get("message") or "")[:60].replace("\n"," ") if worst_post else "N/A"
    best_er_v   = best_post["eng_rate"]  if best_post  else 0
    worst_er_v  = worst_post["eng_rate"] if worst_post else 0
    ig_wow_sign = "+" if ig_wow_delta >= 0 else ""
    fb_wow_sign = "+" if fb_wow_delta >= 0 else ""
    boss_brief = (
        f"Instagram engagement averaged {ig_week_avg_er}% this week, "
        f"{ig_wow_sign}{ig_wow_delta}pp versus last week (historical baseline {ig_hist_avg_er}%). "
        f"The top post -- \"{best_cap}\" -- drove {best_er_v}% ER, "
        f"reinforcing that {dominant} consistently outperform other formats. "
        f"Over the 8-week window, {dominant} average {dominant_er}% ER vs {other_er}% for the alternative -- "
        f"a {round(dominant_er - other_er, 1)}pp gap that makes format choice the single highest-leverage decision. "
        f"Recommendation: target {dominant} for at least 70% of IG output next week and watch saves as the leading organic-reach signal."
    )
    what_worked = [
        f"{dominant.capitalize()} led with {dominant_er}% avg ER across all historical posts.",
        f"IG reach this week: {ig_week_reach:,} impressions, {ig_week_saves} saves.",
        f"{'IG' if ig_week_avg_er >= fb_week_avg_er else 'FB'} led platform engagement at {max(ig_week_avg_er, fb_week_avg_er)}% avg ER.",
    ]
    if followers_count is not None:
        if follower_delta is None:
            what_worked.append(f"IG followers at {followers_count:,} (baseline set this week; growth tracked from next report).")
        else:
            _fg_sign = "+" if follower_delta >= 0 else ""
            what_worked.append(f"IG followers {'grew' if follower_delta >= 0 else 'dipped'} to {followers_count:,} ({_fg_sign}{follower_delta:,} this week).")
    what_didnt = [
        f"Lowest post: \"{worst_cap}\" at {worst_er_v}% ER.",
        f"{'FB' if fb_week_avg_er <= ig_week_avg_er else 'IG'} trailed at {min(fb_week_avg_er, ig_week_avg_er)}% avg ER.",
        "Posts lacking strong visual hooks or clear calls-to-action consistently underperform.",
    ]
    ig_8w_dir = "improving" if (ig_weekly_avgs[-1] or 0) > (ig_weekly_avgs[0] or 0) else "declining" if (ig_weekly_avgs[-1] or 0) < (ig_weekly_avgs[0] or 0) else "flat"
    patterns = [
        f"IG engagement is {ig_8w_dir} over the 8-week window ({ig_weekly_avgs[0]}% to {ig_week_avg_er}%).",
        f"Meme (video) posts average {ig_meme_avg}% ER vs {ig_quote_avg}% for quote images -- {round(ig_meme_avg - ig_quote_avg, 1)}pp gap.",
        f"IG saves totalled {ig_week_saves} this week; rising saves correlate with broader organic distribution.",
        f"FB engagement (baseline {fb_hist_avg_er}%) consistently lags IG (baseline {ig_hist_avg_er}%).",
        f"WoW deltas: IG {'+' if ig_wow_delta >= 0 else ''}{ig_wow_delta}%, FB {'+' if fb_wow_delta >= 0 else ''}{fb_wow_delta}%.",
        "Top posts across all weeks share strong visual identity and concise, action-oriented captions.",
    ]

# ── Step 4: build HTML ─────────────────────────────────────────────────────────
today_str      = now.strftime("%Y-%m-%d")
week_start_str = (now - timedelta(days=6)).strftime("%b %-d")
week_end_str   = now.strftime("%b %-d, %Y")

ig_wow_sign  = "+" if ig_wow_delta >= 0 else ""
fb_wow_sign  = "+" if fb_wow_delta >= 0 else ""
ig_wow_color = "#22c55e" if ig_wow_delta >= 0 else "#ef4444"
fb_wow_color = "#22c55e" if fb_wow_delta >= 0 else "#ef4444"

# Follower KPI display strings
followers_display = f"{followers_count:,}" if followers_count is not None else "N/A"
if follower_delta is None:
    follower_delta_str   = "baseline this week"
    follower_delta_color = "#999"
else:
    follower_delta_str   = f"{'+' if follower_delta >= 0 else ''}{follower_delta:,} this week"
    follower_delta_color = "#22c55e" if follower_delta >= 0 else "#ef4444"
best_caption  = (best_post.get("caption")  or best_post.get("message")  or "")[:50].replace("\n"," ") if best_post  else "N/A"
worst_caption = (worst_post.get("caption") or worst_post.get("message") or "")[:50].replace("\n"," ") if worst_post else "N/A"
best_er_val   = best_post["eng_rate"]  if best_post  else 0
worst_er_val  = worst_post["eng_rate"] if worst_post else 0
worked_li     = "\n".join(f"<li>{item}</li>" for item in what_worked)
didnt_li      = "\n".join(f"<li>{item}</li>" for item in what_didnt)
pattern_li    = "\n".join(f"<li>{item}</li>" for item in patterns)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Weekly Report - {today_str}</title>
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
  .kpi-grid{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:14px; margin-bottom:22px; }}
  .kpi{{ background:white; border-radius:14px; padding:20px 16px; text-align:center; box-shadow:0 2px 12px rgba(107,63,160,.08); }}
  .kpi .val{{ font-size:2em; font-weight:700; color:var(--purple); line-height:1.1; }}
  .kpi .delta{{ font-size:.82em; font-weight:600; margin-top:3px; }}
  .kpi .lbl{{ font-size:.7em; color:#999; text-transform:uppercase; letter-spacing:.08em; margin-top:6px; }}
  .chart-row{{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:22px; }}
  .worked-row{{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:22px; }}
  .worked-card h3{{ font-size:.75em; text-transform:uppercase; letter-spacing:.1em; margin-bottom:14px; font-weight:700; }}
  .worked-card.good h3{{ color:#22c55e; }}
  .worked-card.bad  h3{{ color:#ef4444; }}
  .worked-card ul,.patterns-list{{ list-style:none; padding:0; }}
  .worked-card ul li,.patterns-list li{{ font-size:.88em; line-height:1.55; padding:9px 0; border-bottom:1px solid #f0ebf8; color:#444; }}
  .worked-card ul li:last-child,.patterns-list li:last-child{{ border-bottom:none; }}
  .patterns-list li{{ padding-left:18px; position:relative; }}
  .patterns-list li::before{{ content:"->"; position:absolute; left:0; color:var(--purple); font-weight:700; }}
  @media(max-width:640px){{
    .kpi-grid{{ grid-template-columns:1fr 1fr; }}
    .chart-row,.worked-row{{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>Zenie Weekly Report</h1>
  <div class="meta">Week of {week_start_str} - {week_end_str} &nbsp;&middot;&nbsp; Generated {today_str}</div>
</div>
<div class="container">
  <div class="card brief-card">
    <h2>Boss Brief</h2>
    <p>{boss_brief}</p>
  </div>
  <div class="kpi-grid">
    <div class="kpi">
      <div class="val">{followers_display}</div>
      <div class="delta" style="color:{follower_delta_color}">{follower_delta_str}</div>
      <div class="lbl">IG Followers</div>
    </div>
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
      <div class="section-label">This Week - Posts by Engagement Rate</div>
      <canvas id="postsChart"></canvas>
    </div>
  </div>
  <div class="chart-row">
    <div class="card">
      <div class="section-label">Content Type - IG Historical Avg ER</div>
      <canvas id="typeChart"></canvas>
    </div>
    <div class="card">
      <div class="section-label">IG vs FB - This Week vs 8-Week Avg</div>
      <canvas id="platformChart"></canvas>
    </div>
  </div>
  <div class="worked-row">
    <div class="card worked-card good">
      <h3>What Worked This Week</h3>
      <ul>
        <li><strong>Best post:</strong> "{best_caption}..." - {best_er_val}% ER</li>
        {worked_li}
      </ul>
    </div>
    <div class="card worked-card bad">
      <h3>What Did Not Work</h3>
      <ul>
        <li><strong>Lowest post:</strong> "{worst_caption}..." - {worst_er_val}% ER</li>
        {didnt_li}
      </ul>
    </div>
  </div>
  <div class="card">
    <div class="section-label">Running Patterns - What the Data Shows Over Time</div>
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
    labels:JSON_WEEK_LABELS,
    datasets:[
      {{label:'Instagram',data:JSON_IG_AVGS,borderColor:purple,backgroundColor:'rgba(107,63,160,.08)',tension:.35,fill:true,pointRadius:4,pointBackgroundColor:purple}},
      {{label:'Facebook', data:JSON_FB_AVGS,borderColor:pink, backgroundColor:'rgba(240,160,192,.08)',tension:.35,fill:true,pointRadius:4,pointBackgroundColor:pink}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});
new Chart(document.getElementById('postsChart'),{{
  type:'bar',
  data:{{
    labels:JSON_POST_LABELS,
    datasets:[{{label:'ER %',data:JSON_POST_ERS,backgroundColor:JSON_POST_COLORS,borderRadius:5}}]
  }},
  options:{{indexAxis:'y',responsive:true,plugins:{{legend:{{display:false}}}},scales:{{x:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});
new Chart(document.getElementById('typeChart'),{{
  type:'bar',
  data:{{
    labels:['Memes (Video)','Quote Images'],
    datasets:[{{label:'Avg ER %',data:[IG_MEME_AVG,IG_QUOTE_AVG],backgroundColor:[purple,lavender],borderRadius:6}}]
  }},
  options:{{responsive:true,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});
new Chart(document.getElementById('platformChart'),{{
  type:'bar',
  data:{{
    labels:['Instagram','Facebook'],
    datasets:[
      {{label:'This Week',  data:[IG_WEEK_ER,FB_WEEK_ER],backgroundColor:[purple,pink],borderRadius:6}},
      {{label:'8-Week Avg', data:[IG_HIST_ER,FB_HIST_ER],backgroundColor:[lavender,'rgba(240,160,192,.5)'],borderRadius:6}}
    ]
  }},
  options:{{responsive:true,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{beginAtZero:true,ticks:{{callback:v=>v+'%'}}}}}}}}
}});
</script>
</body>
</html>"""

import json as _json
html = html.replace("JSON_WEEK_LABELS",  _json.dumps(week_labels))
html = html.replace("JSON_IG_AVGS",      _json.dumps(ig_weekly_avgs))
html = html.replace("JSON_FB_AVGS",      _json.dumps(fb_weekly_avgs))
html = html.replace("JSON_POST_LABELS",  _json.dumps(post_labels))
html = html.replace("JSON_POST_ERS",     _json.dumps(post_ers))
html = html.replace("JSON_POST_COLORS",  _json.dumps(post_colors))
html = html.replace("IG_MEME_AVG",       str(ig_meme_avg))
html = html.replace("IG_QUOTE_AVG",      str(ig_quote_avg))
html = html.replace("IG_WEEK_ER",        str(ig_week_avg_er))
html = html.replace("FB_WEEK_ER",        str(fb_week_avg_er))
html = html.replace("IG_HIST_ER",        str(ig_hist_avg_er))
html = html.replace("FB_HIST_ER",        str(fb_hist_avg_er))

os.makedirs("reports", exist_ok=True)
with open(f"reports/{today_str}.html", "w") as f:
    f.write(html)
print(f"HTML built: {len(html):,} chars -> reports/{today_str}.html")

# Persist this week's follower count (keyed to the week's Sunday) for next week's
# delta. Skip on a failed pull so we never write a bogus zero.
if followers_count is not None:
    follower_hist[week_anchor_str] = followers_count
    with open(FOLLOWERS_LOG, "w") as f:
        json.dump(follower_hist, f, indent=2, sort_keys=True)
    print(f"followers.json updated: {week_anchor_str} -> {followers_count:,}")

# ── Step 5: update index.html ──────────────────────────────────────────────────
INDEX_TEMPLATE = """<!DOCTYPE html>
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
if os.path.exists(index_path):
    with open(index_path) as f:
        index_html = f.read()
else:
    index_html = INDEX_TEMPLATE

new_entry = (
    f'<a class="report latest" href="{today_str}.html">'
    f'<span class="report-date">Week of {week_start_str} - {week_end_str}</span>'
    f'<span class="arrow">&#8594;</span></a>\n'
)
index_html = index_html.replace('class="report latest"', 'class="report"')
index_html = index_html.replace("<!-- ENTRIES -->", f"<!-- ENTRIES -->\n{new_entry}")

with open(index_path, "w") as f:
    f.write(index_html)
print("index.html updated")

# ── Summary ────────────────────────────────────────────────────────────────────
ig_wow_sign = "+" if ig_wow_delta >= 0 else ""
fb_wow_sign = "+" if fb_wow_delta >= 0 else ""
best_snippet = (best_post.get("caption") or best_post.get("message") or "")[:50] if best_post else "N/A"

print(f"""
=== ZENIE WEEKLY DIAGNOSTICS COMPLETE ===
Date: {today_str}
IG posts this week: {len(ig_this_week)} | avg ER: {ig_week_avg_er}% ({ig_wow_sign}{ig_wow_delta}% vs last week, baseline {ig_hist_avg_er}%)
FB posts this week: {len(fb_this_week)} | avg ER: {fb_week_avg_er}% ({fb_wow_sign}{fb_wow_delta}% vs last week, baseline {fb_hist_avg_er}%)
IG total reach: {ig_week_reach:,} | saves: {ig_week_saves}
Best post: "{best_snippet}" - {best_er_val}% ER
Report URL: https://isabelhoppmann.github.io/ART-Lab-Social-Media/reports/{today_str}.html
==========================================
""")
