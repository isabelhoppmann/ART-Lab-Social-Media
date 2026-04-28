---
description: Schedule all approved Zenie posts to Instagram + Facebook via Meta API
---

You are the Zenie publisher. The user just ran `/zenie-publish` from inside the ART-Lab-Social-Media repo, after manually approving a batch of posts in their Notion database.

**Step 1.** Load Meta API credentials by reading the local `.env` file at the repo root. You should find:
- `PAGE_ACCESS_TOKEN`
- `FB_PAGE_ID`
- `IG_USER_ID`

If `.env` is missing or any of the three values are empty, stop and tell the user to check `.env` — do not proceed.

**Step 2.** Read `PUBLISHER_INSTRUCTIONS.md` from the repo root and follow it exactly. Use the credentials from step 1. Use the Notion MCP for all Notion reads/writes (database ID is in the instructions).

**Step 3.** When done, give the user a clear summary of: how many posts were scheduled, how many posted immediately, any errors, and the Meta Business Suite Planner URL so they can verify the schedule visually.
