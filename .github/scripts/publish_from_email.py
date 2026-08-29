#!/usr/bin/env python3
"""
Publish the ART Lab daily briefing from email -> GitHub -> Slack.

The claude.ai routine (free under the Claude subscription) researches and
composes the briefing, then emails it to isabel@art-lab.ai with subject
"ART LAB BRIEFING <YYYY-MM-DD>" and the briefing text as the plain-text body.

This script, run from a GitHub Action, fetches that email via the Gmail API,
validates it, and writes briefings/<date>.txt. The workflow then commits the
file and posts it to Slack via post_to_slack.py.

No Claude API call -> no metered cost. Standard library only.

Required env (already repo secrets): GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET,
GMAIL_REFRESH_TOKEN.

Exit codes:
  0  briefing written (new file), OR today's file already exists (skip),
     OR today's briefing is not due yet (see briefing_is_due)
  1  no briefing email found, or body failed validation -> nothing written,
     so nothing reaches Slack (the workflow's failure step alerts the error
     channel).
"""

import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIEFINGS_DIR = os.path.join(REPO_ROOT, "briefings")
SUBJECT_PREFIX = "ART LAB BRIEFING"
FETCH_ATTEMPTS = 5
FETCH_WAIT_SECONDS = 60

# The composing routine fires at 14:00 UTC Mon-Fri and its email has landed as
# late as 14:25. Before this time-of-day there is simply nothing to publish yet.
BRIEFING_DUE_UTC = (14, 20)


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
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _b64url(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def extract_plain_body(payload):
    """Recursively pull the first text/plain part out of a Gmail message."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return _b64url(payload["body"]["data"])
    for part in payload.get("parts") or []:
        body = extract_plain_body(part)
        if body:
            return body
    if payload.get("body", {}).get("data"):  # fallback: top-level body
        return _b64url(payload["body"]["data"])
    return None


def find_briefing_email(token, today_str):
    query = f'subject:"{SUBJECT_PREFIX} {today_str}" newer_than:1d'
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


def validate(text):
    """Guardrail: only a well-formed briefing may reach Slack."""
    if not text:
        return "empty body"
    first = text.splitlines()[0].strip()
    if "Morning Briefing" not in first:
        return f"first line is not a title: {first!r}"
    headers = re.findall(r"^=== .+ ===$", text, re.MULTILINE)
    if len(headers) < 4:
        return f"only {len(headers)} section headers found"
    if "=== ROBOTICS & AI ===" not in text:
        return "missing ROBOTICS & AI section"
    return None


def briefing_is_due(now):
    """Is today's briefing supposed to exist yet?

    Two ways the answer is no, and in both a missing briefing is normal rather
    than a failure worth alerting on:

      1. It isn't a weekday — the composing routine only runs Mon-Fri.
      2. It is a weekday, but earlier than the routine's daily run, so nothing
         has been written yet and there is nothing to publish.

    This guard exists because GitHub delivers these scheduled runs HOURS late:
    on 2026-08-28 all four cron rungs arrived 8-9h behind schedule. A straggler
    that lands after 00:00 UTC computes the NEXT day's date, goes looking for a
    briefing that isn't due for another 14 hours, fails, and emails an alert.

    That false alarm is worse than useless — it trains the reader to ignore the
    one email that matters on a morning the pipeline genuinely breaks. A run
    inside the real publish window still alerts exactly as before.
    """
    if now.weekday() > 4:  # Saturday or Sunday
        return False
    return (now.hour, now.minute) >= BRIEFING_DUE_UTC


def main():
    now = datetime.now(timezone.utc)
    today_str = now.date().strftime("%Y-%m-%d")
    out_path = os.path.join(BRIEFINGS_DIR, f"{today_str}.txt")

    if os.path.exists(out_path):
        print(f"Briefing for {today_str} already exists — skipping.")
        return 0

    if not briefing_is_due(now):
        print(
            f"No briefing is due for {today_str} yet "
            f"(now {now:%a %H:%M} UTC; due from "
            f"{BRIEFING_DUE_UTC[0]:02d}:{BRIEFING_DUE_UTC[1]:02d} UTC on weekdays). "
            "Nothing to publish — exiting quietly rather than alerting."
        )
        return 0

    token = gmail_access_token()

    body = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        body = find_briefing_email(token, today_str)
        if body:
            break
        if attempt < FETCH_ATTEMPTS:
            print(
                f"No briefing email yet (attempt {attempt}/{FETCH_ATTEMPTS}); "
                f"waiting {FETCH_WAIT_SECONDS}s…"
            )
            time.sleep(FETCH_WAIT_SECONDS)

    if not body:
        print(
            f"ERROR: no '{SUBJECT_PREFIX} {today_str}' email found after "
            f"{FETCH_ATTEMPTS} attempts.",
            file=sys.stderr,
        )
        return 1

    text = body.strip()
    text = re.sub(r"^Title:\s*", "", text)
    # Defensive: drop any greeting/preamble before the title line.
    idx = text.find("Morning Briefing")
    if idx > 0:
        text = text[idx:]
    text = text.strip()

    err = validate(text)
    if err:
        print(f"ERROR: briefing failed validation ({err}). Not writing.", file=sys.stderr)
        print("---- raw body ----", file=sys.stderr)
        print(text[:1500], file=sys.stderr)
        return 1

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
    print(f"Wrote {out_path} ({len(text)} chars).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
