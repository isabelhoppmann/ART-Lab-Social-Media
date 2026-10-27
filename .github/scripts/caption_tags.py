"""Guarantee every Zenie caption ends with the post's hashtags.

Isabel's rule (2026-10-15): both ig_caption AND fb_caption end with a blank line
and then the hashtags, so either can be pasted straight into Business Suite. The
drafting routine is told this but keeps dropping them from the FB caption (week of
2026-10-26: all six FB captions shipped bare), so this enforces it in code instead
of trusting the prompt."""


def ensure_caption_tags(post):
    """Append post['hashtags'] to ig_caption / fb_caption where missing.
    Returns the number of captions changed."""
    tags = (post.get("hashtags") or "").strip()
    if not tags:
        return 0
    changed = 0
    for key in ("ig_caption", "fb_caption"):
        cap = (post.get(key) or "").rstrip()
        if not cap or cap.endswith(tags):
            continue
        post[key] = f"{cap}\n\n{tags}"
        changed += 1
    return changed
