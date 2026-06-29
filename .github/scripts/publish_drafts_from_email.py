#!/usr/bin/env python3
"""
Materialize a week's Zenie draft files from an email bundle -> repo working tree.

Why this exists: the claude.ai drafting routine (free under the Claude
subscription) runs in a network-restricted sandbox whose managed GitHub proxy now
rejects writes to api.github.com ("502 builtin injection failed"). So instead of
pushing its files, the routine EMAILS them as one JSON bundle (subject
"ZENIE DRAFTS <YYYY-MM-DD>"). This script -- run from a GitHub Action with native
GitHub access -- fetches that email, writes every file to its path in the
checked-out repo, and exits. The workflow then runs the *existing* render+post
pipeline (regenerate_memes.py, regenerate_quotes.py, post_social_to_slack.py)
exactly as if the files had been pushed. Same outputs, only the transport changed.

Bundle JSON shape (the email's plain-text body):
  {
    "week_date": "2026-06-29",
    "text_files":   { "<repo/relative/path>": "<utf-8 content>", ... },
    "binary_files": { "<repo/relative/path>": "<standard base64 bytes>", ... }
  }
The bundle MUST include social/review-state.json among text_files.

No Claude API call -> no metered cost. Standard library only.
Required env (already repo secrets): GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
GMAIL_REFRESH_TOKEN.

Exit codes:
  0  files written, OR this week already published (skip) -> pipeline runs idempotently
  1  no bundle email found, or bundle failed validation -> nothing written, so the
     workflow's failure step alerts the error channel.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_PATH = os.path.join(REPO_ROOT, "social", "review-state.json")
REQUIRED_FILE = "social/review-state.json"
SUBJECT_PREFIX = "ZENIE DRAFTS"
FETCH_ATTEMPTS = 6
FETCH_WAIT_SECONDS = 60


def gmail_access_token():
    data = urllib.parse.urlencode(
        {
            "client_id": os.environ["GMAIL_CLIENT_ID"],
            "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
            "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def gmail_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _b64url_to_bytes(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def extract_plain_body(payload):
    """Recursively pull the first text/plain part out of a Gmail message."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _b64url_to_bytes(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts") or []:
        body = extract_plain_body(part)
        if body:
            return body
    if payload.get("body", {}).get("data"):  # fallback: top-level body
        return _b64url_to_bytes(payload["body"]["data"]).decode("utf-8", "replace")
    return None


def find_bundle_email(token, today_str):
    query = f'subject:"{SUBJECT_PREFIX} {today_str}" newer_than:2d'
    list_url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?q="
        + urllib.parse.quote(query)
    )
    listing = gmail_get(list_url, token)
    msgs = listing.get("messages") or []
    if not msgs:
        return None
    # Newest first; take the most recent match.
    msg = gmail_get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msgs[0]['id']}?format=full",
        token,
    )
    return extract_plain_body(msg.get("payload", {}))


def parse_bundle(body):
    """Tolerate stray preamble / ``` fences around the JSON object."""
    body = body.strip()
    start = body.find("{")
    end = body.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in email body")
    return json.loads(body[start : end + 1])


def validate(bundle, today_str):
    if not isinstance(bundle, dict):
        return "bundle is not a JSON object"
    text_files = bundle.get("text_files") or {}
    if REQUIRED_FILE not in text_files:
        return f"bundle missing {REQUIRED_FILE}"
    try:
        state = json.loads(text_files[REQUIRED_FILE])
    except Exception as e:
        return f"{REQUIRED_FILE} is not valid JSON: {e}"
    if not state.get("posts"):
        return "review-state.json has no posts"
    wd = bundle.get("week_date") or state.get("week_date")
    if wd != today_str:
        return f"week_date {wd!r} does not match today {today_str!r}"
    return None


def safe_join(root, rel):
    """Resolve rel under root, refusing path traversal from a malformed bundle."""
    dest = os.path.normpath(os.path.join(root, rel.lstrip("/")))
    if dest != root and not dest.startswith(root + os.sep):
        raise ValueError(f"unsafe path in bundle: {rel!r}")
    return dest


def already_published(today_str):
    """True if this week's review-state is already committed AND posted to Slack.
    A re-run must NOT clobber it with the email's fresh (thread_ts=null) copy and
    trigger a duplicate Slack thread."""
    if not os.path.exists(STATE_PATH):
        return False
    try:
        state = json.load(open(STATE_PATH))
    except Exception:
        return False
    return state.get("week_date") == today_str and bool(state.get("slack_thread_ts"))


def main():
    today_str = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")

    if already_published(today_str):
        print(
            f"Week {today_str} already published (review-state has slack_thread_ts) "
            f"-- skipping write; downstream steps will no-op."
        )
        return 0

    token = gmail_access_token()

    body = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        body = find_bundle_email(token, today_str)
        if body:
            break
        if attempt < FETCH_ATTEMPTS:
            print(
                f"No '{SUBJECT_PREFIX} {today_str}' email yet "
                f"(attempt {attempt}/{FETCH_ATTEMPTS}); waiting {FETCH_WAIT_SECONDS}s..."
            )
            time.sleep(FETCH_WAIT_SECONDS)

    if not body:
        print(
            f"ERROR: no '{SUBJECT_PREFIX} {today_str}' email found after "
            f"{FETCH_ATTEMPTS} attempts.",
            file=sys.stderr,
        )
        return 1

    try:
        bundle = parse_bundle(body)
    except Exception as e:
        print(f"ERROR: could not parse bundle JSON: {e}", file=sys.stderr)
        print("---- body head ----", file=sys.stderr)
        print(body[:1000], file=sys.stderr)
        return 1

    err = validate(bundle, today_str)
    if err:
        print(f"ERROR: bundle failed validation ({err}). Nothing written.", file=sys.stderr)
        return 1

    written = []
    for rel, content in (bundle.get("text_files") or {}).items():
        dest = safe_join(REPO_ROOT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(rel)
    for rel, b64 in (bundle.get("binary_files") or {}).items():
        dest = safe_join(REPO_ROOT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(base64.b64decode(b64))
        written.append(rel)

    print(f"Materialized {len(written)} file(s) for week {today_str}:")
    for w in sorted(written):
        print("  -", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
