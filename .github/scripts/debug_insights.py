#!/usr/bin/env python3
"""Diagnostic: what the Meta insights endpoints return for Zenie's recent posts.
Writes reports/insights-debug.json."""
import json, os, urllib.parse, urllib.request
T = os.environ["PAGE_ACCESS_TOKEN"]; IG = "17841465217874624"; FB = "227999857070404"
API = "https://graph.facebook.com/v21.0"
def get(path, **p):
    p["access_token"] = T
    try:
        with urllib.request.urlopen(f"{API}/{path}?{urllib.parse.urlencode(p)}", timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8", "ignore")[:300]}
out = {"ig": [], "fb": []}
media = get(f"{IG}/media", fields="id,media_product_type,timestamp,like_count,comments_count,permalink", limit=8)
for m in media.get("data", []):
    m["insights_reach_saved"] = get(f"{m['id']}/insights", metric="reach,saved")
    m["insights_views"] = get(f"{m['id']}/insights", metric="views,reach,saved,shares,total_interactions")
    out["ig"].append(m)
out["ig_media_error"] = media.get("error")
posts = get(f"{FB}/posts", fields="id,created_time,permalink_url,likes.summary(true),comments.summary(true),shares", limit=8)
for p in posts.get("data", []):
    p["impressions_unique"] = get(f"{p['id']}/insights", metric="post_impressions_unique")
    p["media_view_unique"] = get(f"{p['id']}/insights", metric="post_total_media_view_unique")
    out["fb"].append(p)
out["fb_posts_error"] = posts.get("error")
out["page_followers"] = get(FB, fields="followers_count,fan_count")
out["ig_followers"] = get(IG, fields="followers_count")
os.makedirs("reports", exist_ok=True)
json.dump(out, open("reports/insights-debug.json", "w"), indent=1)
