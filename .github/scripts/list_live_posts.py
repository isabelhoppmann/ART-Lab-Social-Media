#!/usr/bin/env python3
"""Diagnostic: show which accounts the Meta token is connected to, and list what's
actually live on Zenie's Instagram (via Business Discovery on the public handle)
and on the connected Facebook page. Prints JSON to the run log; writes nothing.

Env: PAGE_ACCESS_TOKEN, IG_USER_ID, FB_PAGE_ID, ZENIE_HANDLE."""
import json, os, urllib.parse, urllib.request

TOKEN = os.environ["PAGE_ACCESS_TOKEN"]
IG_USER_ID = os.environ.get("IG_USER_ID", "17841465217874624")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "227999857070404")
HANDLE = os.environ.get("ZENIE_HANDLE", "zenie.app")
API = "https://graph.facebook.com/v21.0"


def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ZenieAgent/1.0"}), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8", "ignore")[:400]}


out = {
    "token_ig_account": get(IG_USER_ID, fields="username,name,followers_count,media_count"),
    "token_fb_page": get(FB_PAGE_ID, fields="name,link,instagram_business_account{username}"),
    "zenie_public": get(IG_USER_ID, fields=f"business_discovery.username({HANDLE}){{username,followers_count,media_count,"
                         "media.limit(100){permalink,media_type,media_product_type,caption,timestamp,like_count,comments_count}}"),
    "fb_page_posts": get(f"{FB_PAGE_ID}/published_posts", fields="message,created_time,permalink_url", limit=50),
}
print("LIVE_POSTS_JSON_START")
print(json.dumps(out, ensure_ascii=False))
print("LIVE_POSTS_JSON_END")
