#!/usr/bin/env python3
"""Send a failure alert to Isabel by email.

Errors never go to Slack — the Slack channels carry published content only.
Every Action failure path in this repo routes here instead.

Usage:
    notify_error_email.py "<subject>" "<body>"
    ... or set ALERT_SUBJECT / ALERT_BODY in the environment.

Reads GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN — the same
secrets the publish scripts already use. Never exits non-zero: this runs inside
`if: failure()` steps, and a broken alert must not mask the real failure.
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage

ALERT_TO = os.environ.get("ALERT_TO", "isabel@art-lab.ai")


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


def send(subject, body):
    token = gmail_access_token()
    # EmailMessage handles RFC 2047 for us — a hand-built "Subject: ..." line
    # renders emoji as mojibake (Ã¢ÂœÂ…) in Gmail.
    msg = EmailMessage()
    msg["From"] = ALERT_TO
    msg["To"] = ALERT_TO
    msg["Subject"] = subject
    msg.set_content(body, subtype="plain", charset="utf-8")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode().rstrip("=")
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ALERT_SUBJECT", "")
    body = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ALERT_BODY", "")
    if not subject:
        subject = "⚠️ ART Lab Action failed"

    run_url = ""
    if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID"):
        run_url = (
            f"https://github.com/{os.environ['GITHUB_REPOSITORY']}"
            f"/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        )
        body = f"{body}\n\nRun log: {run_url}".strip()

    try:
        send(subject, body)
        print(f"Alert emailed to {ALERT_TO}: {subject}")
    except Exception as e:  # never mask the underlying failure
        print(f"Could not email alert ({e}). Subject was: {subject}")


if __name__ == "__main__":
    main()
