# ART Lab Content Principles

Working rules for ART Lab's social and outreach content (@artlabfuture). Read this before drafting a post, a comment, a caption, or an outreach note.

**This is not Zenie's voice.** Zenie is a warm best friend talking to millennial women about their inner life. ART Lab is a company introducing an object nobody has seen before. The registers are different and should stay different — do not carry Zenie's captions, cadence, or humor over here. `AGENT_INSTRUCTIONS.md` governs Zenie; this file governs ART Lab.

**ART Lab does not shoot.** There is no photography, no set, no shoot day. Every post is assembled from two banks that already exist in Notion:

- **Media Library** — approved assets (Image, Video, Clip, Render, GIF), tagged by Facet, Orientation and audience Weighting.
- **Information Pipelines** — copy modules, tagged with the same Facet and Weighting vocabulary, and joined to the media by a two-way relation.

A post is one copy module plus one paired asset. That makes content selection and sequencing — not production — the whole job, and it is why the format work below is expressed as *which asset, in which order* rather than as shot lists.

**The proven formats live in `formats/library.json`** in this repo, with the structure spec for each, which cohort account proves it, and the Facet/Type each one needs from the Media Library. That file is the operational half of this document; read it before selecting anything. Every format in it is satisfiable from assets that already exist — a format needing new footage is not usable and is not in there.

Four rules. They are ordered by how often they get broken, not by importance.

---

## 1. Log every test with its hypothesis, not just its result

**The rule:** every outreach attempt and every content experiment gets written down *before* it goes out, with a one-sentence hypothesis. Not just what happened — what you thought would happen, and why you shaped it that way.

**Why:** ART Lab posts a handful of times a week and sends outreach in single digits. That is nowhere near enough volume to rediscover what works by staring at results. A high-volume account can afford to forget its reasoning, because the pattern re-emerges in the data. ART Lab cannot. The record *is* the learning system — if the reasoning isn't captured at the moment of writing, it's gone, and six weeks later a result is just a number with no explanation attached.

**A hypothesis is a prediction, not a description.** It has to be able to turn out wrong.

- Good: *"Leading with the 8-second motion clip instead of the static hero shot, because the three posts that showed movement got more saves than the six that didn't — expect saves to lead likes again."*
- Good: *"Cold outreach to gallery directors framed around the Exploratorium residency rather than the product, on the theory that institutional credibility opens doors that a product pitch doesn't."*
- Bad — describes, predicts nothing: *"A post showing the lamp with a caption about the design process."*
- Bad — unfalsifiable: *"This should get good engagement."*

**Where it goes:** a `Hypothesis` (text) and `Outcome` (select) pair on the ART Lab Content Calendar and the Outreach Master, filled at draft time and scored later. Same two columns, same meaning, as the pair now on Zenie Posts.

**Reading the results — the discipline that keeps this honest:**
- **Expect most of it to be neutral.** Roughly two things in twenty are real winners. A flat stretch is the normal shape of a small account, not a signal that the approach is broken.
- **Judge by format, not by individual post, and never on fewer than 6–8 comparable attempts.** ART Lab's per-post numbers are currently single-digit likes, which is small enough that one post tells you nothing at all. Below roughly 6 posts of a given format, you do not have a read — say so and change nothing rather than inventing a pattern.
- Do not retire a format because one attempt underperformed. Do not double down on one because one attempt spiked.

---

## 2. Pull references from unrelated categories

**The rule:** when looking for visual, tonal, or structural references, go to **watchmaking, gallery publishing, and hi-fi** — not to other lighting brands and not to other robotics companies.

**Why:** if you study the category you're in, you produce work that looks like the category you're in. Every lighting brand studying lighting brands is why lighting brands look identical. Distinctiveness comes from importing a convention that doesn't belong here yet.

**What each category is actually for:**
- **Watchmaking** — how to make mechanism the subject. Watch brands have spent a century getting people to care about movement they can barely see: exploded views, the language of complications, the caseback shot that shows the thing working. ART Lab is selling a mechanism. Steal the vocabulary and the reverence.
- **Gallery publishing** — how to present an object as worth sustained attention. Exhibition catalogues, artist monographs, gallery announcement cards: generous white space, restrained typography, captions that inform rather than sell, the confidence to show one object large and say very little. This is the register for anything that has to read as art-adjacent rather than gadget-adjacent.
- **Hi-fi** — how to talk to people who care about how something is made. Hi-fi copy takes materials, engineering choices, and tolerances seriously without becoming a spec sheet, and it treats the buyer as someone with taste rather than someone who needs convincing. This is the tone for build and process content.

**In practice:** when a reference gets pulled, note which category it came from. If a week's references are all from lighting or robotics, that week's research failed and should be redone.

**The line that makes this compatible with studying top performers.** Analysing the best-performing posts in your own niche is a legitimate and useful exercise — it is how you learn craft. The rule is *what* you take from them: **borrow structure, never aesthetic.**

| Borrow freely | Build your own |
|---|---|
| Shot order and where the cut lands | Colour and grade |
| Clip length and loop points | Typography and on-screen text |
| What occupies the first frame | Set dressing and styling |
| Caption length and where the ask sits | Music and sound identity |
| Carousel sequencing | Voice and phrasing |
| Posting rhythm | Which references you look at at all |

Copy how a post is *built* and you learn craft. Copy how it *looks* and you produce another account in a category that already has plenty. This split is encoded in `formats/library.json` under `hard_rules`, so the agents enforce it rather than relying on memory.

---

## 3. No AI-generated imagery — and this is the reason

**The rule:** no AI-generated or AI-composited imagery in ART Lab content. Photography, renders of the actual product, and real footage only.

**Why — the part that matters more than the rule:** **AI copies proven work; humans invent new work.** A generative model can only recombine what already exists, so whatever it produces is a weighted average of work that has already been made and already been seen. That is a genuinely useful property when the goal is to produce a competent version of a known thing. It is precisely the wrong property here.

ART Lab's entire proposition is that this object does not have a category yet. Imagery that reads as a remix of existing product photography quietly makes the opposite argument — it says *this is another one of those*, which is the one thing the work cannot afford to say. The medium contradicts the message.

This is why the rule is absolute rather than a matter of taste or quality. A *good* AI image is worse for ART Lab than a mediocre one, because it's more convincingly ordinary.

**Corollary:** the same logic applies to copy. Do not reach for the phrasing that sounds like every other launch. If a line could appear verbatim in a competitor's post, it is the average of existing work and it should be rewritten.

**Reading is not generating.** Using a model to find the pattern across thirty competitor posts is research, and it is fine. Using one to make the image is not. The distinction is whether the model's output reaches the feed.

---

## 4. Lead with movement, and never gate it

**The rule:** whatever is moving in a given piece of content goes first, and it is never placed behind a price, a form, a waitlist, a signup, or a "link in bio to see more."

This is not a rule about one particular subject. It is about the fact that **movement is the thing that separates this from everything else in the feed**, whatever form the moving asset takes. The subject changes; the rule doesn't.

In practice that means the Media Library's motion assets — anything catalogued as Clip or Video, and any pair of renders that captures two states of the same subject — outrank the stills. A still can support a post. It should rarely open one.

**Why:** a still image of a robotics company is a category the viewer already understands and has already decided how they feel about. Motion is the only thing that breaks the category, and breaking the category is the only thing that stops a scroll. Gating it means spending the one asset that reliably works in order to protect a conversion step that does not work without it. Nobody fills in a form to find out whether they're interested — they fill it in because they already are.

**In practice:**
- Motion appears in the first frame or the first second. Not after a title card, not after a logo animation, not after a slow reveal.
- Price, preorder, signup and "learn more" come *after* the motion has landed — later in the video, further down the caption, in a follow-up post. Never before it, never as the gate.
- A post carrying no movement at all needs a reason. The `catalogue_plate` format is the sanctioned exception, and it is capped deliberately — a feed with no quiet frames reads as a brand rather than a practice, but a feed of nothing but quiet frames doesn't get seen at all.
- Since there are no shoots, "we had no footage" is never the explanation. If the motion assets in the Media Library are exhausted or stale, that is a restocking problem to raise, the same way the Zenie meme library gets topped up when it runs low.
- This applies to outreach too. If a note to a gallery, a press contact, or a partner includes one asset, it is the one where something moves.
- **Corollary — movement is also the strongest thing you own strategically.** Catie's background is robot choreography; the company's differentiator is how the machine *moves*, not what it looks like standing still. Content that treats motion as the subject rather than the demo is playing to the actual strength.
