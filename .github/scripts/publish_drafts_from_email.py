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

This Action is scheduled to run MANY times across Monday morning (GitHub drops or
delays any single scheduled tick), so it must be safe to run repeatedly and must
NOT cry wolf when it simply runs before the bundle email has arrived.

Exit codes / GitHub step output `status`:
  0  status=materialized  -> fresh files written this run; workflow runs render+post
  0  status=already_done  -> this week already published; workflow skips downstream
  0  status=waiting       -> bundle email not here yet; skip quietly, a later tick
                            will get it (NOT an error -- no alert)
  1  (no status)          -> bundle found but garbled/failed validation; a real
                            failure, so the workflow's failure step alerts.
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
# Kept short on purpose: the workflow now retries every 30 min all morning, so each
# tick only needs a couple of quick looks rather than a long in-tick wait.
FETCH_ATTEMPTS = 3
FETCH_WAIT_SECONDS = 60


def set_output(status):
    """Expose the run's outcome to the workflow as step output `status` so the
    render/post/commit steps only run when we actually materialized fresh files."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"status={status}\n")


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
    # includeSpamTrash so a re-run still finds the bundle after we trash it below.
    list_url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?includeSpamTrash=true&q="
        + urllib.parse.quote(query)
    )
    # Newest first. Subject search can collide with watchdog/failure emails that
    # share the words "Zenie Drafts", so return the newest one whose body actually
    # parses AND validates as a bundle — not merely the newest subject match.
    msgs = gmail_get(list_url, token).get("messages") or []
    for m in msgs:
        msg = gmail_get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}?format=full",
            token,
        )
        body = extract_plain_body(msg.get("payload", {}))
        if not body:
            continue
        try:
            bundle = parse_bundle(body)
        except Exception:
            continue
        if validate(bundle, today_str) is None:
            return body, m["id"]
    return None, None


def trash_bundle_email(token, msg_id):
    """Trash the processed bundle email so the bulky machine-to-machine JSON (which
    the agent sends from Isabel to Isabel, so it lands in Sent) stops cluttering her
    mailbox each week. The full content lives in git, and Trash is 30-day
    recoverable + still found by find_bundle_email (includeSpamTrash=true), so a
    re-run is safe. Best-effort — never fail the publish over this."""
    if not msg_id:
        return
    try:
        req = urllib.request.Request(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/trash",
            data=b"",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=30)
        print(f"Trashed bundle email {msg_id} (content preserved in git).")
    except Exception as e:
        print(f"(non-fatal) could not trash bundle email: {e}")


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


LABEL_TO_POST_TYPE = (("meme", "Meme"), ("repost", "Repost"), ("quote", "Quote Image"))


def normalize_review_state():
    """Safety net: the drafting agent sometimes emits posts with a null/empty
    post_type. The render + Slack scripts gate on post_type ("meme"/"quote"/
    "repost"), so a blank one silently drops the post (no meme render, no Slack
    reply). Derive it from the label, which is reliably "Meme N" / "Quote N" /
    "Repost N"."""
    if not os.path.exists(STATE_PATH):
        return
    state = json.load(open(STATE_PATH))
    fixed = 0
    for post in state.get("posts", []):
        if post.get("post_type"):
            continue
        label = (post.get("label") or "").strip().lower()
        for prefix, ptype in LABEL_TO_POST_TYPE:
            if label.startswith(prefix):
                post["post_type"] = ptype
                fixed += 1
                break
    if fixed:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"normalize: filled missing post_type on {fixed} post(s) from labels.")


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
        set_output("already_done")
        return 0

    token = gmail_access_token()

    body, msg_id = None, None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        body, msg_id = find_bundle_email(token, today_str)
        if body:
            break
        if attempt < FETCH_ATTEMPTS:
            print(
                f"No '{SUBJECT_PREFIX} {today_str}' email yet "
                f"(attempt {attempt}/{FETCH_ATTEMPTS}); waiting {FETCH_WAIT_SECONDS}s..."
            )
            time.sleep(FETCH_WAIT_SECONDS)

    if not body:
        # Not an error: this tick simply ran before the bundle arrived. Skip
        # quietly and let a later Monday-morning tick pick it up. The watchdog
        # (mid-morning) is the authoritative alarm if the week never publishes.
        print(
            f"No '{SUBJECT_PREFIX} {today_str}' bundle email yet after "
            f"{FETCH_ATTEMPTS} attempts -- skipping; a later tick will retry."
        )
        set_output("waiting")
        return 0

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

    normalize_review_state()
    trash_bundle_email(token, msg_id)

    print(f"Materialized {len(written)} file(s) for week {today_str}:")
    for w in sorted(written):
        print("  -", w)
    set_output("materialized")
    return 0


if __name__ == "__main__":
    sys.exit(main())
