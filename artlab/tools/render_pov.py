"""Point of View cover slide: one typographic slide that carries a design opinion.

Modeled on how Kelly Wearstler writes: an ALL-CAPS title of two or three words,
then a short first-person opinion. The rest of the carousel is images.
Distinct from Field Notes: no disc, no slide counter, the whole opinion on one slide.

Usage: python3 render_pov.py spec.json out.png
spec: {"series": "Point of View", "issue": "01", "title": "ONE SOURCE",
       "body": "...", "ground": "#1C1A16", "ink": "#EEE8DC"}
"""
import json, sys, pathlib, base64
from playwright.sync_api import sync_playwright

FONT_DIR = pathlib.Path(__file__).resolve().parent / "fonts"
W, H = 1080, 1350


def _font(name):
    return "data:font/ttf;base64," + base64.b64encode((FONT_DIR / name).read_bytes()).decode()


def html(spec):
    ground = spec.get("ground", "#1C1A16")
    ink = spec.get("ink", "#EEE8DC")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'IS';src:url({_font('InstrumentSerif-Regular.ttf')})}}
@font-face{{font-family:'ISI';src:url({_font('InstrumentSerif-Italic.ttf')})}}
@font-face{{font-family:'DM';src:url({_font('DMMono-Regular.ttf')})}}
html,body{{margin:0;width:{W}px;height:{H}px;background:{ground};color:{ink}}}
.wrap{{position:absolute;inset:0;padding:96px 96px 104px;display:flex;flex-direction:column}}
.label{{font-family:'DM';font-size:22px;letter-spacing:.14em;text-transform:uppercase;opacity:.6}}
.title{{font-family:'IS';font-size:168px;line-height:1.0;letter-spacing:.01em;margin-top:auto;
        text-wrap:balance}}
.rule{{height:1px;background:{ink};opacity:.35;margin:56px 0 48px}}
.body{{font-family:'IS';font-size:46px;line-height:1.22;max-width:820px;text-wrap:pretty}}
</style></head><body><div class="wrap">
<div class="label">{spec['series']} {spec['issue']}</div>
<div class="title">{spec['title']}</div>
<div class="rule"></div>
<div class="body">{spec['body']}</div>
</div></body></html>"""


def main(spec_path, out_path):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H})
        page.set_content(html(spec))
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(200)
        page.screenshot(path=out_path)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
