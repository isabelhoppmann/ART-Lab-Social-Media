#!/usr/bin/env python3
"""
ART Lab Daily Briefing — research + compose, run from a GitHub Action.

Uses the Anthropic Messages API with the server-side web_search / web_fetch
tools to research robotics/AI news and compose the daily briefing, then writes
briefings/<today>.txt. The workflow commits that file and posts it to Slack via
the existing post_to_slack.py.

This replaces the old claude.ai routine, whose sandbox can no longer write to
api.github.com (it routes GitHub through a managed proxy that rejects the
hardcoded PAT). A GitHub Action has native GitHub access, so the publish step
that used to fail with "502 builtin injection failed" just works here.

Exit codes:
  0  briefing written (new file), OR today's file already exists (skip)
  1  research/compose failed or output failed validation -> nothing is written,
     so nothing reaches Slack (the workflow's failure step alerts the error
     channel). A missing briefing is better than a broken one.
"""

import os
import re
import sys
from datetime import datetime, timezone, timedelta

import anthropic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIEFINGS_DIR = os.path.join(REPO_ROOT, "briefings")
MODEL = os.environ.get("MODEL", "claude-opus-4-8")

SYSTEM_PROMPT = """\
You are the ART Lab Daily Briefing Agent. ART Lab is a seed-stage AI consumer \
robotics startup building physical AI systems (home robots). You produce a \
concise daily news briefing for the founding team.

Use the web_search tool to research and web_fetch to verify publication dates \
when a snippet doesn't show one. Quality over quantity.

## RESEARCH AREAS
- Industry: consumer robotics / home robots, embodied AI / humanoids, VLM / \
multimodal AI research, notable AI product launches, AI/robotics breakthroughs.
- Funding: AI/robotics venture funding, consumer-robotics raises, embodied-AI / \
humanoid raises, notable robotics VC deals.
- Competitors: 1X Technologies, Figure AI, Physical Intelligence, Gemini \
Robotics / Google DeepMind robotics, NVIDIA robotics / Isaac, OpenAI robotics, \
Meta embodied AI, ElliQ, Loona, TCL, Apple home robot, Samsung home robot, LG \
home robot, Lenovo smart-home AI.
- Bay Area: relevant AI/robotics events, meetups, demos, or conferences coming \
up within ~2 weeks.

## DATE VERIFICATION (CRITICAL)
For every candidate story, confirm it is genuinely recent before including it.
- News items (all sections except BAY AREA): must be published within the last \
48 hours. If you cannot confirm a publication date, DISCARD the item. Never use \
vague phrases like "recently" to justify inclusion.
- Bay Area events: must be upcoming within 2 weeks. Discard past or far-future \
events.
A briefing with fewer items is better than one with stale or unverifiable news.

## DEDUPLICATION
You will be given URLs and funding lines from the past 7 days of briefings.
- Never reuse a URL that already appeared.
- Never repeat a funding announcement for a company already covered in the past \
7 days, even under a different URL — funding stories get syndicated across \
outlets for days.
- Each story appears in EXACTLY ONE section. Assign to the most specific: a \
competitor's funding goes in FUNDING (not COMPETITOR WATCH); a competitor's \
research goes in RESEARCH. COMPETITOR WATCH is only for news that fits no other \
section.

## OUTPUT FORMAT (EXACT)
Output ONLY the briefing as plain text, under 500 words total. The FIRST LINE \
must be exactly:
Morning Briefing {Month} {D}, {Year}
(e.g. "Morning Briefing June 26, 2026" — no "Title:" prefix, no markdown, no \
preamble, no closing remarks.)

Then these sections, each header on its own line:

=== ROBOTICS & AI ===
- Headline, one sentence. URL

=== RESEARCH ===
- Headline, one sentence. URL

=== FUNDING & INVESTMENT ===
- Company, amount, investors if known, confirmed announcement date. URL

=== COMPETITOR WATCH ===
- [Company] what they announced (only if not already covered above). URL
If nothing new: "No significant competitor activity in the last 48 hours."

=== BAY AREA ===
- Event, date, location, one line. URL
Omit this section entirely if nothing notable within 2 weeks.

Each FUNDING entry MUST include the confirmed announcement date; if you can't \
confirm it, omit the entry. If a whole section has no qualifying items, write a \
single line "- No qualifying items in the last 48 hours." under its header \
(except BAY AREA, which is omitted entirely when empty).
"""


def load_dedup_context(today):
    seen_urls = set()
    past_funding = []
    for d in range(1, 8):
        path = os.path.join(
            BRIEFINGS_DIR, f"{(today - timedelta(days=d)).strftime('%Y-%m-%d')}.txt"
        )
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        seen_urls.update(re.findall(r"https?://\S+", content))
        m = re.search(r"=== FUNDING.*?===\s*\n(.*?)(?:\n===|\Z)", content, re.DOTALL)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip()
                if line.startswith("- ") and not line[2:].strip().lower().startswith("no "):
                    past_funding.append(line[2:].strip())
    return seen_urls, past_funding


def validate(text):
    """Guardrail: only a well-formed briefing may reach Slack."""
    if not text:
        return "empty output"
    first = text.splitlines()[0].strip()
    if "Morning Briefing" not in first:
        return f"first line is not a title: {first!r}"
    headers = re.findall(r"^=== .+ ===$", text, re.MULTILINE)
    if len(headers) < 4:
        return f"only {len(headers)} section headers found"
    if "=== ROBOTICS & AI ===" not in text:
        return "missing ROBOTICS & AI section"
    return None


def main():
    today = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")
    out_path = os.path.join(BRIEFINGS_DIR, f"{today_str}.txt")

    if os.path.exists(out_path):
        print(f"Briefing for {today_str} already exists — skipping.")
        return 0

    seen_urls, past_funding = load_dedup_context(today)
    print(
        f"Dedup context: {len(seen_urls)} seen URLs, "
        f"{len(past_funding)} prior funding entries."
    )

    pretty_date = today.strftime("%B %-d, %Y")
    user_lines = [
        f"Today is {pretty_date} (UTC). Research and compose today's briefing.",
        "",
        "Do NOT reuse any of these URLs from the past 7 days:",
        *(sorted(seen_urls) or ["(none)"]),
        "",
        "Do NOT repeat funding for any company already covered in the past 7 days "
        "(even under a different URL):",
        *(past_funding or ["(none)"]),
    ]
    user = "\n".join(user_lines)

    client = anthropic.Anthropic(timeout=600)
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 20},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 15},
    ]
    messages = [{"role": "user", "content": user}]

    resp = None
    for _ in range(15):  # server-side tool loop: continue on pause_turn
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break

    if resp is None:
        print("ERROR: no response from the API", file=sys.stderr)
        return 1
    if resp.stop_reason == "refusal":
        print("ERROR: model refused the request", file=sys.stderr)
        return 1

    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    # Defensive: strip a stray "Title:" prefix if the model adds one.
    text = re.sub(r"^Title:\s*", "", text)

    err = validate(text)
    if err:
        print(f"ERROR: output failed validation ({err}). Not writing.", file=sys.stderr)
        print("---- raw output ----", file=sys.stderr)
        print(text[:1500], file=sys.stderr)
        return 1

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
    print(f"Wrote {out_path} ({len(text)} chars).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
