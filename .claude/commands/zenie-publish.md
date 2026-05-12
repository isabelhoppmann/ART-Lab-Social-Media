---
description: Schedule all approved Zenie posts to Facebook via Meta API
---

You are the Zenie publisher. The user just ran `/zenie-publish` after manually approving a batch of posts in Notion.

**Step 1.** Ask the user to provide their full posting Page Access Token. Say:
"Please paste your Zenie posting token. This is stored separately from the repo — check your password manager."

Do NOT read PAGE_ACCESS_TOKEN from .env — that token is read-only and cannot post. The posting token must be provided explicitly by the user each time.

Also read FB_PAGE_ID and IG_USER_ID from the local .env file at the repo root.

**Step 2.** Read `PUBLISHER_INSTRUCTIONS.md` from the repo root and follow it exactly. Use the token provided in Step 1. Use the Notion MCP for all Notion reads/writes (database ID is in the instructions).

**Step 3.** When done, give the user a clear summary of: how many posts were scheduled, how many posted immediately, any errors, and the Meta Business Suite Planner URL so they can verify the schedule visually.
