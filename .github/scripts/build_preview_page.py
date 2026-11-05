#!/usr/bin/env python3
"""Rebuild posts/<week>/index.html (the review preview Catie opens from Slack)
straight from social/review-state.json, after every asset has been rendered.

Added 2026-11-05 with the new post types (Text Card, Carousel, Reel, Story).
The drafting agent still writes a preview page, but it can't know what the
runner renders afterwards, and patching individual blocks with regexes had
already left broken markup behind. Building the whole page from the final
state means the preview always matches what is in Slack. Posts nothing anywhere.
"""
import html, json, os, re, sys

STATE_PATH = "social/review-state.json"
TYPE_ORDER = {"meme": 0, "carousel": 1, "reel": 2, "text card": 3, "quote": 4, "quote image": 4, "repost": 5, "story": 6}


def esc(s):
    return html.escape(s or "").replace("\n", "<br>")


def local_name(url):
    return (url or "").rsplit("/", 1)[-1]


def media_block(post):
    t = (post.get("post_type") or "").lower()
    urls = post.get("media_urls") or ([post["media_url"]] if post.get("media_url") else [])
    files = [local_name(u) for u in urls]
    if post.get("skipped") or not files:
        if t == "repost":
            return ""
        why = esc(post.get("skip_reason") or "not rendered")
        return f'<p class="warn">⚠️ Not rendered: {why}</p>'
    if t in ("meme", "reel"):
        cls = "tall" if t == "reel" else "square"
        return f'<div class="vid {cls}"><video src="{files[0]}" autoplay loop muted playsinline controls></video></div>'
    if t in ("carousel", "story"):
        cls = "strip tallstrip" if t == "story" else "strip"
        imgs = "".join(f'<img src="{f}" alt="slide {i}" loading="lazy">' for i, f in enumerate(files, 1))
        return f'<div class="{cls}">{imgs}</div><p class="hint">Swipe sideways to see every {"frame" if t == "story" else "slide"}.</p>'
    return f'<div class="img"><img src="{files[0]}" alt="{esc(post.get("label"))}"></div>'


def notes(post):
    t = (post.get("post_type") or "").lower()
    out = []
    if t == "reel":
        out.append("No sound is baked in: add a trending audio in the Instagram app when posting.")
        if post.get("broll", {}).get("page"):
            out.append(f'Footage: <a href="{esc(post["broll"]["page"])}" target="_blank">Pexels</a> (free to use, no credit needed).')
    if t == "story":
        for i, fr in enumerate(post.get("frames") or [], 1):
            st = (fr.get("sticker") or "").lower()
            if st:
                opts = fr.get("sticker_options")
                extra = f' — options: {esc(" / ".join(opts))}' if opts else ""
                out.append(f"Frame {i}: add a <b>{esc(st)}</b> sticker in the empty middle{extra}.")
    if t == "repost":
        if post.get("url"):
            out.append(f'<a class="btn" href="{esc(post["url"])}" target="_blank">Watch the reel</a> · credit @{esc(post.get("creator", ""))}')
    return "".join(f'<p class="note">{n}</p>' for n in out)


def post_block(post):
    t = post.get("post_type") or ""
    series = f'<span class="series">{esc(post.get("series"))}</span>' if post.get("series") else ""
    parts = [f'<div class="post"><h2>{esc(post.get("label"))} <span class="type">{esc(t)}</span>{series}</h2>',
             media_block(post), notes(post)]
    if post.get("ig_caption"):
        parts.append(f'<p class="caption"><b>IG:</b> {esc(post["ig_caption"])}</p>')
    if post.get("fb_caption"):
        parts.append(f'<p class="caption"><b>FB:</b> {esc(post["fb_caption"])}</p>')
    if post.get("best_time"):
        parts.append(f'<p class="time">Best time: {esc(post["best_time"])}</p>')
    if post.get("hypothesis"):
        parts.append(f'<p class="hyp">🎯 {esc(post["hypothesis"])}</p>')
    parts.append("</div>")
    return "\n".join(p for p in parts if p)


CSS = """
:root{--purple:#6B3FA0;--lavender:#C9B1E8;--pink:#F0A0C0}
body{font-family:-apple-system,sans-serif;max-width:720px;margin:0 auto;padding:20px 16px;background:#f5f0fa;color:#1a1a2e}
h1{color:var(--purple)}.back{color:var(--purple);text-decoration:none;font-size:.9em;display:block;margin-bottom:20px}
.post{background:#fff;border-radius:16px;padding:20px;margin-bottom:24px;box-shadow:0 2px 12px rgba(107,63,160,.1);border-top:3px solid var(--lavender)}
.post h2{font-size:.8em;text-transform:uppercase;letter-spacing:.08em;color:var(--purple);margin:0 0 12px}
.type{color:#999;font-weight:400;margin-left:6px}.series{background:var(--lavender);color:#341E5A;border-radius:10px;padding:2px 8px;margin-left:8px;font-size:.9em}
.img img{width:100%;border-radius:12px;display:block}
.vid{position:relative;width:100%;border-radius:12px;overflow:hidden;background:#000;margin-bottom:12px}
.vid.square{aspect-ratio:1/1}.vid.tall{aspect-ratio:9/16;max-width:420px;margin-left:auto;margin-right:auto}
.vid video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.strip{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:6px}
.strip img{flex:0 0 82%;max-width:82%;border-radius:12px;scroll-snap-align:start}
.tallstrip img{flex:0 0 46%;max-width:46%}
.hint,.time{font-size:.8em;color:#999}.note{font-size:.88em;color:#555;background:#faf7ff;border-radius:8px;padding:8px 10px}
.caption{font-size:.95em;margin:8px 0}.hyp{font-size:.85em;color:#6B3FA0}
.warn{background:#fff1f1;color:#a33;border-radius:8px;padding:8px 10px}
.btn{display:inline-block;padding:8px 16px;background:var(--purple);color:#fff;border-radius:20px;text-decoration:none}
"""


def build(state):
    week = state.get("week_date", "")
    posts = sorted(state.get("posts", []),
                   key=lambda p: (TYPE_ORDER.get((p.get("post_type") or "").lower(), 9),
                                  int((re.search(r"\d+", p.get("label", "")) or [0])[0] or 0)))
    blocks = "\n\n".join(post_block(p) for p in posts)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zenie Drafts — {esc(week)}</title><style>{CSS}</style></head>
<body><a class="back" href="../../">← All weeks</a><h1>Zenie Drafts — {esc(week)}</h1>
{blocks}
</body></html>
"""


def main():
    state = json.load(open(STATE_PATH))
    week = state.get("week_date", "")
    if not week:
        print("build_preview_page: no week_date — skipping"); return
    os.makedirs(f"posts/{week}", exist_ok=True)
    out = f"posts/{week}/index.html"
    open(out, "w", encoding="utf-8").write(build(state))
    print(f"build_preview_page: wrote {out}")


if __name__ == "__main__":
    main()
