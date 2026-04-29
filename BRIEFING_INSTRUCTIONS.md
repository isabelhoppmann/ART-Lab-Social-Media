# ART Lab Daily Briefing Agent Instructions

Credentials are in the message that invoked you.

## ABOUT ART LAB
ART Lab is a seed-stage AI consumer robotics startup building physical AI systems (home robots). You are delivering a daily news briefing to the founding team.

## ERROR HANDLING (CRITICAL)
Wrap your ENTIRE execution in a try/except. If ANY step fails for ANY reason:
1. Do NOT post anything to SLACK_WEBHOOK_URL (the group channel)
2. POST an error alert to SLACK_ERROR_WEBHOOK_URL instead:
   {"text": "Briefing agent failed: <error message here>. Nothing was sent to the group."}
3. Exit immediately

This ensures the group never sees partial output, duplicate posts, or error messages.

---

## STEP 1 — RESEARCH NEWS

Run ALL of these web searches. Only keep items from the **last 48 hours**, or upcoming Bay Area events within 2 weeks. Be selective — quality over quantity.

**Industry:**
1. consumer robotics OR home robot news 2026
2. embodied AI OR humanoid robot news this week
3. vision language model OR VLM OR multimodal AI research 2026
4. new AI product launch OR robotics product announcement 2026
5. artificial intelligence research breakthrough this week
6. AI robotics Bay Area event OR meetup OR demo OR conference 2026

**Funding:**
7. AI robotics venture capital investment funding 2026
8. consumer robotics startup funding round 2026
9. embodied AI OR humanoid robot funding raised 2026
10. robotics VC deal announced this week

**Competitors:**
11. "1X Technologies" news OR announcement 2026
12. "Figure AI" news OR announcement 2026
13. "Physical Intelligence" news OR announcement 2026
14. "Gemini Robotics" OR "Google DeepMind robotics" news 2026
15. "NVIDIA robotics" OR "NVIDIA Isaac" news 2026
16. "OpenAI robotics" OR "OpenAI" robot announcement 2026
17. "Meta" AI robotics OR embodied AI 2026
18. "ElliQ" OR "Loona" robot news 2026
19. "TCL" robot OR AI product 2026
20. "Apple" home robot OR AI hardware 2026
21. "Samsung" home robot OR AI assistant 2026
22. "LG" home robot OR AI product 2026
23. "Lenovo" AI robot OR smart home 2026

---

## STEP 2 — COMPOSE BRIEFING

### DEDUPLICATION RULE (CRITICAL)
Each news item must appear in EXACTLY ONE section. Assign to the most specific section:
- Competitor raises funding -> FUNDING only, not COMPETITOR WATCH
- Competitor publishes research -> RESEARCH only, not COMPETITOR WATCH
- COMPETITOR WATCH = only news that does not belong in any other section
- Never repeat the same URL or story across two sections

### Format

Title: Morning Briefing {Month} {Date}, {Year}

Sections (plain text, under 500 words total):

=== ROBOTICS & AI ===
- Headline, one sentence. URL

=== RESEARCH ===
- Headline, one sentence. URL

=== FUNDING & INVESTMENT ===
- Company, amount, investors if known. URL

=== COMPETITOR WATCH ===
- [Company] what they announced (only if NOT already covered in another section above). URL
If nothing new: "No significant competitor activity in the last 48 hours."

=== BAY AREA ===
- Event, date, location, one line. URL
Omit this section entirely if nothing notable within 2 weeks.

---

## STEP 3 — POST TO SLACK

Use Python with urllib only (no pip). SLACK_WEBHOOK_URL and SLACK_ERROR_WEBHOOK_URL are passed in as variables.

This step must run inside the top-level try/except. If the POST fails or returns anything other than b"ok", raise an exception — do not post a fallback message to the group channel.

1. Build a list of Slack blocks:
   - Start with a header block: {"type": "header", "text": {"type": "plain_text", "text": "Morning Briefing {Month} {Date}, {Year}"}}
   - For each section that has content, add:
     - A divider block: {"type": "divider"}
     - A section block with mrkdwn text containing the bold section name and bullet items:
       {"type": "section", "text": {"type": "mrkdwn", "text": "*ROBOTICS & AI*\n• item 1\n• item 2"}}
   - URLs go inline as plain text — Slack auto-links them
   - Omit BAY AREA block entirely if no events

2. POST to SLACK_WEBHOOK_URL:
   - Method: POST
   - Content-Type: application/json
   - Body: json.dumps({"blocks": [...]}).encode()
   - If response is not b"ok", raise an exception with the response body included

---

## STEP 4 — ARCHIVE TO GITHUB

This step runs inside the top-level try/except. If it fails, raise — do not silently continue.

Push briefing to briefings/YYYY-MM-DD.txt. Token is passed in as GITHUB_TOKEN, repo as GITHUB_REPO.

CRITICAL to avoid 422 errors: Always GET the file first before PUT.
- If GET returns 200: extract sha and include it in the PUT body
- If GET returns 404: set sha = None and omit it from PUT body
- If GET returns anything else: raise the error
