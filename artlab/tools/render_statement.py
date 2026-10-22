"""Statement slide: one opinion set in stacked capitals (a single-image post, or slide 1 of a carousel).

Modeled on the typographic slides in Kelly Wearstler's Substack (WEARSTLERworld):
one short opinion broken into lines, alternating a serif and a wide sans, each line
nudged left or right so the block reads as a composition. ART Lab's own type and
colors; small series label at the foot instead of a wordmark.

Usage: python3 render_statement.py spec.json out.png
spec: {"series": "Statement", "issue": "01",
       "ground": "#D2471C", "ink": "#F1E6D3",
       "lines": [{"text": "WE DON'T", "font": "serif", "x": 0.30}, ...]}
  font: "serif" (Instrument Serif) or "sans" (Archivo, expanded, heavy)
  x: left offset as a fraction of the free space on that line (0 = flush left, 1 = flush right)
"""
import json, sys, pathlib, base64
from playwright.sync_api import sync_playwright

FONT_DIR = pathlib.Path(__file__).resolve().parent / "fonts"
W, H = 1080, 1350
BLOCK_W = 940  # widest line fills this


def _font(name, mime):
    return f"data:{mime};base64," + base64.b64encode((FONT_DIR / name).read_bytes()).decode()


def html(spec):
    ground = spec.get("ground", "#D2471C")
    ink = spec.get("ink", "#F1E6D3")
    rows = "\n".join(
        f'<div class="row"><span class="ln {l["font"]}" data-x="{l.get("x", 0)}">{l["text"]}</span></div>'
        for l in spec["lines"])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{{font-family:'IS';src:url({_font('InstrumentSerif-Regular.ttf','font/ttf')})}}
@font-face{{font-family:'DM';src:url({_font('DMMono-Regular.ttf','font/ttf')})}}
@font-face{{font-family:'AR';src:url({_font('Archivo-Variable-wdth.woff2','font/woff2')}) format('woff2');
           font-weight:100 900;font-stretch:62% 125%}}
html,body{{margin:0;width:{W}px;height:{H}px;background:{ground};color:{ink};overflow:hidden}}
.block{{position:absolute;left:{(W-BLOCK_W)//2}px;width:{BLOCK_W}px;top:0}}
.row{{position:relative;white-space:nowrap}}
.ln{{display:inline-block;position:relative;white-space:nowrap}}
.serif{{font-family:'IS';font-size:var(--fs);line-height:.86;letter-spacing:-.005em}}
.sans{{font-family:'AR';font-weight:780;font-stretch:125%;font-size:calc(var(--fs) * .74);line-height:.98;letter-spacing:.005em}}
.label{{position:absolute;bottom:84px;left:0;right:0;text-align:center;font-family:'DM';
        font-size:22px;letter-spacing:.16em;text-transform:uppercase;opacity:.75}}
</style></head><body>
<div class="block" id="b">{rows}</div>
<div class="label">{spec['series']} {spec['issue']}</div>
<script>
const b=document.getElementById('b');
function fit(){{
  let fs=200; b.style.setProperty('--fs',fs+'px');
  const widest=()=>Math.max(...[...b.querySelectorAll('.ln')].map(e=>e.getBoundingClientRect().width));
  fs=fs*{BLOCK_W}/widest(); b.style.setProperty('--fs',fs+'px');
  // keep the block inside the frame vertically
  const maxH={H}-300; if(b.getBoundingClientRect().height>maxH){{fs=fs*maxH/b.getBoundingClientRect().height;b.style.setProperty('--fs',fs+'px');}}
  b.querySelectorAll('.ln').forEach(e=>{{const free={BLOCK_W}-e.getBoundingClientRect().width;e.style.left=(free*parseFloat(e.dataset.x))+'px';}});
  b.style.top=(({H}-60-b.getBoundingClientRect().height)/2)+'px';
}}
window.fit=fit;
</script></body></html>"""


def main(spec_path, out_path):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={"width": W, "height": H})
        page.set_content(html(spec))
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(300)
        page.evaluate("fit()")
        page.wait_for_timeout(100)
        page.screenshot(path=out_path)
        br.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
