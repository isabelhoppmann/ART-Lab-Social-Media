"""Guarantee the tail of every Zenie caption: ...copy → credit → hashtags.

Isabel's rules:
- 2026-10-15: both ig_caption AND fb_caption end with a blank line and then the
  hashtags, so either can be pasted straight into Business Suite. The drafting
  routine kept dropping them from the FB caption (week of 2026-10-26: all six FB
  captions shipped bare).
- 2026-10-26: a repost's "Credit: @handle" goes between the copy and the
  hashtags, never first.

Both are enforced here in code instead of trusting the prompt."""
import re

CREDIT_RE = re.compile(r"Credit:\s*(@[\w.]+)", re.IGNORECASE)


def fix_caption(cap, tags):
    """Return cap rebuilt as: copy, blank line, Credit (if any), blank line, tags."""
    text = (cap or "").strip()
    if not text:
        return cap
    if tags and text.endswith(tags):
        text = text[: -len(tags)].rstrip()

    credit = None
    m = CREDIT_RE.search(text)
    if m:
        credit = f"Credit: {m.group(1)}"
        # Drop the credit plus any separator glued to it ("Credit: @x — copy").
        text = (text[: m.start()] + text[m.end():])
        text = re.sub(r"^\s*[—–\-:|]\s*", "", text.strip()).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)

    parts = [text] if text else []
    if credit:
        parts.append(credit)
    if tags:
        parts.append(tags)
    return "\n\n".join(parts)


def ensure_caption_tags(post):
    """Fix ig_caption / fb_caption in place. Returns the number changed."""
    tags = (post.get("hashtags") or "").strip()
    changed = 0
    for key in ("ig_caption", "fb_caption"):
        cap = post.get(key)
        if not cap:
            continue
        new = fix_caption(cap, tags)
        if new != cap:
            post[key] = new
            changed += 1
    return changed
