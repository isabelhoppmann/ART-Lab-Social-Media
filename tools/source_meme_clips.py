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

# A clip is crop-filled to 1080x1080, so very wide footage loses its edges. Not a
# hard reject — two of the three clips added on 2026-08-11 were ~1.9:1 and
# survived because the subject sat dead centre — but it drives the sort order so
# the safest candidates surface first.
IDEAL_RATIO = 1.0
MIN_W, MIN_H = 240, 220


def _key():
    k = os.environ.get("GIPHY_KEY", "").strip()
    if not k:
        sys.exit("GIPHY_KEY not set. Get a beta key at developers.giphy.com (choose API, not SDK).")
    return k


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def _slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def harvest(queries, limit):
    os.makedirs(WORKDIR, exist_ok=True)
    manifest_path = os.path.join(WORKDIR, "candidates.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

    for q in queries:
        url = f"{API}?" + urllib.parse.urlencode(
            {"api_key": _key(), "q": q, "limit": limit, "rating": "pg",
             "bundle": "messaging_non_clips"})
        try:
            data = _get(url).get("data", [])
        except Exception as e:
            print(f"  search {q!r} failed: {e}")
            continue

        rows = []
        for g in data:
            orig = (g.get("images") or {}).get("original") or {}
            mp4, w, h = orig.get("mp4"), int(orig.get("width") or 0), int(orig.get("height") or 0)
            if not mp4 or w < MIN_W or h < MIN_H or g.get("is_sticker"):
                continue
            rows.append({
                "id": g["id"], "query": q, "title": g.get("title", ""),
                "w": w, "h": h, "ratio": round(w / h, 2), "mp4": mp4,
                "page": g.get("url", ""),
                # Branded/verified channel uploads carry logos far more often than
                # anonymous ones — surface it so review can weight accordingly.
                "uploader": ((g.get("user") or {}).get("username") or ""),
            })
        # safest shapes first: closest to square
        rows.sort(key=lambda r: abs(r["ratio"] - IDEAL_RATIO))
        rows = rows[:limit]

        got = []
        for r in rows:
            dest = os.path.join(WORKDIR, f"{r['id']}.mp4")
            if not os.path.exists(dest):
                try:
                    with urllib.request.urlopen(urllib.request.Request(r["mp4"], headers=UA), timeout=45) as resp, \
                         open(dest, "wb") as f:
                        f.write(resp.read())
                except Exception as e:
                    print(f"  download {r['id']} failed: {e}")
                    continue
            r["file"] = dest
            manifest[r["id"]] = r
            got.append(r)
            _frames_sheet(r, dest)

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
