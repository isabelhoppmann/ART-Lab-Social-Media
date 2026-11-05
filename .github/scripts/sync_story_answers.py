#!/usr/bin/env python3
"""Copy the "Zenie Story Answers" Notion page into social/story_answers.md.

Isabel pastes the answers from each week's Instagram Story question box / poll
into that page (Instagram's API does not return question-sticker replies). The
Monday drafting agent can't safely call Notion before it has emailed its bundle
(a hanging Notion call killed four runs in July), so this Sunday step copies the
page into the repo, where the agent reads it from raw.githubusercontent.com.

Only the text under the "Answers" heading is copied. Best-effort: on any error
the existing file is left alone. Env: NOTION_TOKEN. Posts nothing anywhere.
"""
import json, os, sys, urllib.request

TOKEN = os.environ.get("NOTION_TOKEN", "")
PAGE = "40fc2cdd-459d-81cc-9e1d-d6b905bb5825"   # Zenie Story Answers (under Zenie Social Media)
OUT = "social/story_answers.md"


def get(path):
    req = urllib.request.Request(f"https://api.notion.com/v1/{path}",
                                 headers={"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def text_of(block):
    data = block.get(block["type"], {})
    return "".join(t.get("plain_text", "") for t in data.get("rich_text", []))


def main():
    if not TOKEN:
        print("sync_story_answers: NOTION_TOKEN not set — skipping"); return
    try:
        blocks, cursor = [], None
        while True:
            res = get(f"blocks/{PAGE}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else ""))
            blocks += res.get("results", [])
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")
    except Exception as e:
        print(f"sync_story_answers: could not read the Notion page ({e}). If this is a 404, share the "
              f"'Zenie Story Answers' page with the repo's Notion integration. Leaving {OUT} unchanged.")
        return
    lines, started = [], False
    for b in blocks:
        t, txt = b["type"], text_of(b).strip()
        if t.startswith("heading") and txt.lower() == "answers":
            started = True
            continue
        if not started or not txt:
            continue
        if t.startswith("heading"):
            lines += ["", f"## {txt}"]
        elif t in ("bulleted_list_item", "numbered_list_item", "to_do"):
            lines.append(f"- {txt}")
        else:
            lines.append(txt)
    body = "\n".join(lines).strip()
    header = ("# Zenie Story answers\n\nCopied every Sunday from the Notion page \"Zenie Story Answers\". "
              "Each heading is the date of one week's Story; bullets are anonymous answers.\n\n")
    open(OUT, "w", encoding="utf-8").write(header + (body or "(no answers yet)") + "\n")
    print(f"sync_story_answers: wrote {OUT} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
