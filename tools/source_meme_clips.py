#!/usr/bin/env python3
"""Top up meme_library from Giphy.

The no-repeat rule in meme_library/used.json is permanent — a slug is spent the
moment it renders — so the library needs restocking every few weeks. Doing that
by hand is slow: Giphy's pages are JS-rendered, so without an API key you can
scrape about one candidate per search page, and roughly three in four candidates
fail the watermark bar anyway.

This automates the mechanical half. What it does NOT do is decide whether a clip
is clean: AGENT_INSTRUCTIONS requires eyes on first/middle/last frames of every
candidate, because watermarks fade in and out. So `harvest` ends by writing a
contact sheet, and a human (or Claude, reading the sheet) makes the call.

Usage
-----
  export GIPHY_KEY=...

  # 1. pull candidates for one or more concepts
  python3 tools/source_meme_clips.py harvest "clutching pearls" "unbothered sipping"

  # 2. look at <workdir>/_sheet_<query>.jpg and _frames_<id>.jpg, pick winners

  # 3. promote a candidate into the library
  python3 tools/source_meme_clips.py add --id <candidate-id> --slug ugly_cry \
      --title "Ugly-crying with a tissue" \
      --vibes emotional,sobbing,overwhelmed \
      --use-when "Full-body emotional release..." \
      --example "me rereading the journal entry from when i thought he was the one"

Rejection notes worth keeping in mind while reviewing a sheet — these are the
marks that actually showed up in past sweeps: network bugs (a "Global" logo in
the corner), show hashtags (#SchittsCreek), broadcaster idents (CBC), burned-in
subtitles ("DELETE.", "Inner peace"), and uploader watermarks on text cards.
"""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request

API = "https://api.giphy.com/v1/gifs/search"
LIBRARY = "meme_library/library.json"
USED = "meme_library/used.json"
CLIPS = "meme_library/clips"
WORKDIR = os.environ.get("MEME_WORKDIR", ".meme_candidates")
UA = {"User-Agent": "ZenieLibrarian/1.0"}

# A clip is crop-filled to 1080x1080, so very wide footage loses its edges. This
# is reported on the review sheet but is NOT a filter — two of the three clips
# added on 2026-08-11 were ~1.9:1 and worked because the subject sat dead centre.
MIN_W, MIN_H = 240, 220

# QUERY ADVICE (learned the hard way on 2026-08-11): search the EXPRESSION, not
# the caption. Phrase queries like "i told you so" or "delulu" return GIFs with
# that phrase burned into them, which fails the watermark bar every time — two
# sheets scored 0/8 that way. "smirking woman", "raised eyebrow", "rubbing eyes
# tired" return clean footage instead. Adding "woman" also helps, since Zenie's
# audience is women 20-35 and male-led clips get rejected downstream anyway.


BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def _search_api(q, limit, key):
    url = f"{API}?" + urllib.parse.urlencode(
        {"api_key": key, "q": q, "limit": limit, "rating": "pg",
         "bundle": "messaging_non_clips"})
    rows = []
    for g in _get(url).get("data", []):
        orig = (g.get("images") or {}).get("original") or {}
        if not orig.get("mp4") or g.get("is_sticker"):
            continue
        rows.append({"id": g["id"], "mp4": orig["mp4"], "page": g.get("url", ""),
                     "title": g.get("title", ""),
                     "uploader": ((g.get("user") or {}).get("username") or "")})
    return rows


def _search_scrape(q, limit):
    """No-key fallback. Giphy's /search/ pages ship ~25 ids in the server HTML
    (their /explore/ pages ship one, which is why hand-sourcing used to crawl).
    Only ids come back — dimensions get probed after download."""
    url = "https://giphy.com/search/" + urllib.parse.quote(q.replace(" ", "-"))
    with urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER_UA), timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    ids, seen = [], set()
    for m in re.finditer(r"media\d?\.giphy\.com/media/(?:v1\.[A-Za-z0-9]+/)?([A-Za-z0-9]{8,})/", html):
        gid = m.group(1)
        if gid not in seen:
            seen.add(gid)
            ids.append(gid)
    return [{"id": i, "mp4": f"https://media.giphy.com/media/{i}/giphy.mp4",
             "page": f"https://giphy.com/gifs/{i}", "title": "", "uploader": ""}
            for i in ids[:limit]]


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split("\n")[0]
    try:
        w, h = (int(x) for x in out.split(",")[:2])
        return w, h
    except Exception:
        return 0, 0


def _slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def harvest(queries, limit):
    os.makedirs(WORKDIR, exist_ok=True)
    manifest_path = os.path.join(WORKDIR, "candidates.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

    key = os.environ.get("GIPHY_KEY", "").strip()
    print(f"source: {'Giphy API' if key else 'scraped /search/ pages (no GIPHY_KEY)'}\n")

    for q in queries:
        try:
            rows = _search_api(q, limit * 2, key) if key else _search_scrape(q, limit * 2)
        except Exception as e:
            print(f"  search {q!r} failed: {e}")
            continue

        # Download first, then judge: the scrape path has no dimensions until the
        # file is on disk, so both paths filter and sort after the fetch.
        got = []
        for r in rows:
            dest = os.path.join(WORKDIR, f"{r['id']}.mp4")
            if not os.path.exists(dest):
                try:
                    with urllib.request.urlopen(urllib.request.Request(r["mp4"], headers=UA), timeout=45) as resp, \
                         open(dest, "wb") as f:
                        f.write(resp.read())
                except Exception:
                    continue
            w, h = _probe(dest)
            if w < MIN_W or h < MIN_H:
                os.remove(dest)
                continue
            r.update({"query": q, "w": w, "h": h, "ratio": round(w / h, 2), "file": dest})
            got.append(r)

        # Keep the source's own relevance order. Sorting by closeness-to-square
        # was tried on 2026-08-11 and actively backfired: perfectly square clips
        # on Giphy are overwhelmingly stickers, cartoons and text cards, so the
        # "safest shape" sort buried the real footage and two whole sheets came
        # back with zero usable candidates. Relevance order surfaces the widely
        # used meme formats, which is what the library wants; the crop risk on a
        # wide clip is a judgement call for the review sheet, not a sort key.
        for r in got[limit:]:
            os.remove(r["file"])
        got = got[:limit]

        for r in got:
            manifest[r["id"]] = r
            _frames_sheet(r, r["file"])
        if got:
            _contact_sheet(got, os.path.join(WORKDIR, f"_sheet_{_slugify(q)}.jpg"))
        print(f"{q!r}: {len(got)} candidates -> {WORKDIR}/_sheet_{_slugify(q)}.jpg")

    json.dump(manifest, open(manifest_path, "w"), indent=2, ensure_ascii=False)
    print(f"\nmanifest: {manifest_path} ({len(manifest)} total)")
    print("Review the sheets, then promote winners with `add`.")


def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def _frame(src, t, dest, size=None):
    vf = f"scale={size}:{size}:force_original_aspect_ratio=increase,crop={size}:{size}" if size else "scale=iw:ih"
    subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", src, "-vf", vf,
                    "-frames:v", "1", dest], capture_output=True)
    return os.path.exists(dest)


def _frames_sheet(row, src):
    """First / middle / last at FULL frame — the watermark check. Full frame, not
    the square crop, so corner marks the crop would hide are still visible."""
    from PIL import Image, ImageDraw
    d = _duration(src) or 1.0
    paths = []
    for i, frac in enumerate((0.05, 0.5, 0.92)):
        p = os.path.join(WORKDIR, f"_f{i}_{row['id']}.png")
        if _frame(src, d * frac, p):
            paths.append(p)
    if not paths:
        return
    ims = [Image.open(p) for p in paths]
    for im in ims:
        im.thumbnail((420, 300))
    W = max(i.width for i in ims)
    sheet = Image.new("RGB", (len(ims) * (W + 10) + 10, max(i.height for i in ims) + 34), (24, 24, 27))
    for i, im in enumerate(ims):
        sheet.paste(im, (10 + i * (W + 10), 10))
    ImageDraw.Draw(sheet).text(
        (10, sheet.height - 20),
        f"{row['id']}  {row['w']}x{row['h']}  ratio {row['ratio']}  "
        f"{'@' + row['uploader'] if row['uploader'] else 'no uploader'}  |  first / middle / last",
        fill=(240, 240, 240))
    sheet.save(os.path.join(WORKDIR, f"_frames_{row['id']}.jpg"), quality=92)
    for p in paths:
        os.remove(p)


def _contact_sheet(rows, dest, cols=4, tile=340):
    """One square-cropped tile per candidate — how it will actually ship."""
    from PIL import Image, ImageDraw
    picks = []
    for r in rows:
        p = os.path.join(WORKDIR, f"_t_{r['id']}.png")
        if _frame(r["file"], (_duration(r["file"]) or 1.0) * 0.5, p, size=tile):
            picks.append((r, p))
    if not picks:
        return
    rows_n = (len(picks) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tile + 10) + 10, rows_n * (tile + 40) + 10), (24, 24, 27))
    d = ImageDraw.Draw(sheet)
    for i, (r, p) in enumerate(picks):
        x, y = 10 + (i % cols) * (tile + 10), 10 + (i // cols) * (tile + 40)
        sheet.paste(Image.open(p), (x, y))
        d.text((x + 2, y + tile + 6), f"{r['id']}", fill=(245, 245, 245))
        d.text((x + 2, y + tile + 20), f"{r['w']}x{r['h']} r{r['ratio']}", fill=(170, 170, 170))
        os.remove(p)
    sheet.save(dest, quality=90)


def add(args):
    manifest_path = os.path.join(WORKDIR, "candidates.json")
    if not os.path.exists(manifest_path):
        sys.exit("no candidates.json — run `harvest` first")
    manifest = json.load(open(manifest_path))
    row = manifest.get(args.id)
    if not row:
        sys.exit(f"candidate {args.id!r} not in manifest")

    lib = json.load(open(LIBRARY))
    if any(c["slug"] == args.slug for c in lib["clips"]):
        sys.exit(f"slug {args.slug!r} already in library")
    used = {u["slug"] for u in json.load(open(USED)).get("used", [])}
    if args.slug in used:
        sys.exit(f"slug {args.slug!r} is in the no-repeat ledger — pick another name")

    os.makedirs(CLIPS, exist_ok=True)
    dest = f"{CLIPS}/{args.slug}.mp4"
    # even dimensions + yuv420p so libx264 and every downstream player accept it
    subprocess.run(["ffmpeg", "-y", "-i", row["file"], "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", dest],
                   check=True, capture_output=True)

    lib["clips"].append({
        "slug": args.slug,
        "title": args.title,
        "file": dest,
        "vibes": [v.strip() for v in args.vibes.split(",") if v.strip()],
        "use_when": args.use_when,
        "example_overlay": args.example,
    })
    json.dump(lib, open(LIBRARY, "w"), indent=2, ensure_ascii=False)

    available = sorted({c["slug"] for c in lib["clips"]} - used)
    print(f"added {args.slug} <- giphy:{row['id']} ({row['w']}x{row['h']})")
    print(f"available now ({len(available)}, ~{len(available)//2} weeks): {', '.join(available)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    h = sub.add_parser("harvest", help="search Giphy, download candidates, build review sheets")
    h.add_argument("queries", nargs="+")
    h.add_argument("--limit", type=int, default=12, help="candidates per query (default 12)")

    a = sub.add_parser("add", help="promote a reviewed candidate into the library")
    a.add_argument("--id", required=True)
    a.add_argument("--slug", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--vibes", required=True, help="comma-separated")
    a.add_argument("--use-when", required=True, dest="use_when")
    a.add_argument("--example", required=True, help="example_overlay")

    args = ap.parse_args()
    if args.cmd == "harvest":
        harvest(args.queries, args.limit)
    else:
        add(args)


if __name__ == "__main__":
    main()
