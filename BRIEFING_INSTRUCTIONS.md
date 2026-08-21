# ART Lab Daily Briefing Agent Instructions

Credentials are in the message that invoked you.

## ABOUT ART LAB
ART Lab is a seed-stage AI consumer robotics startup building physical AI systems (home robots). You are delivering a daily news briefing to the founding team.

## ERROR HANDLING (CRITICAL)
Wrap your ENTIRE execution in a try/except. If ANY step fails for ANY reason:
1. Do NOT attempt to publish to GitHub (it may produce a partial/corrupt file)
2. Try to email an alert to isabel@art-lab.ai using the Gmail credentials — but if that also fails, ignore it silently. NEVER post an error to Slack.
3. Exit immediately

Errors NEVER go to Slack. The Slack channel carries published content only — no failure notices, no partial output. All failures go to Isabel by email.

---

## STEP 0 — LOAD THE 7-DAY LEDGER (DEDUPLICATION)

Before searching for news, load the last 7 briefings. One day is not enough: a
running story (a conference, an IPO, an upcoming event) reappears for days under
fresh URLs, which is exactly how the briefing started repeating itself.

Use Python with urllib. No auth needed — the sandbox cannot reach
`api.github.com`, but `raw.githubusercontent.com` works fine.

1. Compute `today` as a UTC date.
2. For each of the past 7 days, GET
   `https://raw.githubusercontent.com/{GITHUB_REPO}/main/briefings/{YYYY-MM-DD}.txt`
   with a User-Agent header. HTTP 404 means no briefing that day — skip it.
3. From every file you load, collect:
   - `seen_urls` — every URL.
   - `seen_keys` — every comma-separated value on a line starting with `#KEYS:`.
     Track how many separate days each key appears on, and whether it appears in
     yesterday's file.
   - `past_bullets` — every bullet line, from every section.
   - `past_funding` — every bullet under FUNDING & INVESTMENT.
4. Briefings published before the `#KEYS:` convention have no ledger line. For
   those, derive a key per bullet using the rule in Step 2 and add it to
   `seen_keys`.
5. Print `seen_keys` before searching, so the run log shows what is blocked.

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

After collecting results, remove any item whose URL is in `seen_urls`.

### DATE VERIFY (critical)

Keep a news item only if you can confirm it was published in the last 48 hours;
if the snippet shows no date, fetch the article to find one. **Exception:**
RESEARCH items (papers, preprints, lab technical blogs) may be up to 7 days old —
a paper does not go stale the way a news story does — but they still need a
confirmed date. Bay Area events: upcoming within 2 weeks. No confirmable date,
no item. Never justify an item with "recently" or "earlier this year."

---

## STEP 1C — ONE STORY, ONE MENTION

The rule that matters most. A **story** is the underlying event, not the article
about it. Two items are the same story when they concern the same company and the
same development — however much the URL, outlet, wording, framing, or section
differ. When an item is a borderline call, drop it.

- **Blocked keys.** Discard any item whose story key is already in `seen_keys`,
  unless the multi-day rule below permits a second mention.
- **Same story, fresh source.** Discard anything that restates a line in
  `past_bullets`. A newer article about the same development is not new
  information. Check deliberately: name the company and the development, then
  scan `past_bullets` for that pair before keeping the item.
- **Multi-day stories.** A conference, IPO, funding round, or product launch is
  ONE story for its entire run. Report it at most twice: once when it breaks or
  as a preview, and a second time only if there is a concrete new fact — a named
  product, a specific number, a signed deal, a stated outcome — that appears in
  no past bullet, and that fact must be the point of the bullet. Never report
  that the same event opened, debuted, or is underway on more than one day. Never
  report the same market move twice because the number moved.
- **Repeat companies.** If a company appears anywhere in `past_bullets` from the
  last 7 days, a new item about it must carry a materially new fact, stated in
  the bullet itself.
- **Sections reset nothing.** Moving a story to a different section does not make
  it new. These rules apply across all five sections and all 7 days.

---

## STEP 1D — BAY AREA IS A CALENDAR, NOT A FEED

An event stays "upcoming within 2 weeks" for up to fourteen days, so a plain
freshness rule guarantees repeats. Instead: an event may appear in at most TWO
briefings, ever — once on the day you first find it, and once on the day before
it begins. Before listing an event, count the days its key appears in
`seen_keys`; if that count is 2 or more, drop it. If its key is in yesterday's
briefing, drop it — never two days running. If every candidate is already spent,
omit the BAY AREA section entirely. An empty BAY AREA section is normal on most
days.

---

## STEP 2 — COMPOSE BRIEFING

### SECTION RULE (CRITICAL)
Each news item must appear in EXACTLY ONE section. Assign to the most specific section:
- Competitor raises funding -> FUNDING only, not COMPETITOR WATCH
- Competitor publishes research -> RESEARCH only, not COMPETITOR WATCH
- COMPETITOR WATCH = only news that does not belong in any other section
- Never repeat the same URL or story across two sections
- At most ONE bullet per company per day, across the whole briefing
- Never pad a section to make the briefing look fuller

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

### STORY KEYS

Give every bullet a story key: lowercase, hyphenated, naming the subject and the
development — the company or organization, then what happened. Examples:
`unitree-ipo`, `wrc-beijing-2026`, `ruggedize-2026`, `actuate-26`,
`nvidia-physical-ai-models`, `infiforce-series-a`.

The key identifies the **story, not the article**, so reuse the same key every
time you would write about that development, and keep one key for an event across
its whole run — never version a key by day or by outlet. Keys are how tomorrow's
run recognizes what you already covered; choose them as if a stranger had to
match them.

### REPEAT GATE (do not skip)

After composing and before sending, re-read every bullet against `seen_keys` and
`past_bullets` and delete any that violates Step 1C or Step 1D. If a section
empties, write its no-qualifying-items line. If the whole briefing empties, send
it that way. Deleting a repeat is always the right call — a two-item briefing is
more useful than a five-item one that repeats yesterday, and there is no penalty
for a quiet day.

### LEDGER LINE

The final line of the briefing must be `#KEYS:` followed by the comma-separated
keys of every bullet you kept:

```
#KEYS: unitree-ipo, ruggedize-2026
```

If you kept no real items, write `#KEYS:` with nothing after it. Nothing may
follow that line, and the keys must not appear anywhere else in the text.

The ledger is internal bookkeeping. `.github/scripts/post_to_slack.py` strips any
`#KEYS:` line before rendering, so it never reaches the channel — **if you change
where the ledger lives, change that script too.** It must stay at the bottom:
`publish_from_email.py` truncates everything above the `Morning Briefing` title
line, so a ledger at the top would be silently discarded.

---

## STEP 3 — EMAIL FOR PUBLISHING

Do **not** try to write to GitHub. The routine's sandbox can no longer reach
`api.github.com` (its managed proxy rejects the PAT with "502 builtin injection
failed"). A GitHub Action publishes from your email instead.

Send one email with the Gmail credentials, subject EXACTLY:

```
ART LAB BRIEFING YYYY-MM-DD
```

The body is the briefing and nothing else: the `Morning Briefing` title line, the
section blocks, then the `#KEYS:` ledger line last. No greeting, no closing
remarks, no markdown.

`daily-briefing.yml` runs 30 minutes later, fetches the email, validates it,
writes `briefings/<date>.txt`, commits it, and posts it to Slack.

Print: "Briefing emailed for publishing."
