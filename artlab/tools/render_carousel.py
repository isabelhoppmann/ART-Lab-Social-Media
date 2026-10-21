import json, sys, pathlib, math, base64
from playwright.sync_api import sync_playwright

FONT_DIR = pathlib.Path(__file__).resolve().parent / "fonts"
W, H = 1080, 1350

def _font(name):
    return "data:font/ttf;base64," + base64.b64encode((FONT_DIR / name).read_bytes()).decode()

CSS = f"""
@font-face {{ font-family: 'Serif'; src: url('{_font("InstrumentSerif-Regular.ttf")}'); }}
@font-face {{ font-family: 'Serif'; font-style: italic; src: url('{_font("InstrumentSerif-Italic.ttf")}'); }}
@font-face {{ font-family: 'Mono'; src: url('{_font("DMMono-Regular.ttf")}'); }}
:root {{ --paper:#EEE8DC; --ink:#1C1A16; --muted:#6F685C; --accent:#D2471C; --rule:#CFC6B5; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{W}px; height:{H}px; background:var(--paper); overflow:hidden; }}
.slide {{ position:relative; width:{W}px; height:{H}px; padding:84px 88px; color:var(--ink); -webkit-font-smoothing:antialiased; }}
.top {{ display:flex; justify-content:space-between; font-family:'Mono'; font-size:21px; letter-spacing:.14em; color:var(--muted); text-transform:uppercase; }}
.rule {{ position:absolute; left:88px; right:88px; top:140px; height:1px; background:var(--rule); }}
.disc {{ position:absolute; border-radius:50%; background:var(--accent); }}
.text {{ position:absolute; left:88px; right:120px; font-family:'Serif'; color:var(--ink); text-wrap:pretty; }}
.hook {{ font-size:96px; line-height:1.0; letter-spacing:-.01em; bottom:300px; }}
.body {{ font-size:64px; line-height:1.12; bottom:250px; }}
.close {{ font-size:72px; line-height:1.08; bottom:330px; }}
.kicker, .sub {{ position:absolute; left:88px; right:88px; font-family:'Mono'; font-size:22px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
.kicker {{ bottom:220px; }} .sub {{ bottom:250px; }}
em {{ font-style:italic; }}
.foot {{ position:absolute; left:88px; right:88px; bottom:84px; display:flex; justify-content:space-between; font-family:'Mono'; font-size:20px; letter-spacing:.14em; color:var(--muted); text-transform:uppercase; border-top:1px solid var(--rule); padding-top:22px; }}
"""

def disc_pos(i, n):
    t = i / max(n - 1, 1)
    size = int(300 - 150 * t)
    x = int(W - 88 - size - (W - 2 * 88 - size) * t)
    y = int(230 + 120 * math.sin(math.pi * t))
    return x, y, size

def slide_html(spec, s, i, n):
    x, y, size = disc_pos(i, n)
    extra = "".join(f'<div class="{k}">{s[k]}</div>' for k in ("kicker", "sub") if s.get(k))
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="slide">
<div class="top"><span>{spec['series']} {spec['issue']}</span><span>{i+1:02d} / {n:02d}</span></div>
<div class="rule"></div>
<div class="disc" style="left:{x}px; top:{y}px; width:{size}px; height:{size}px; background:{spec.get('accent', '#D2471C')}"></div>
<div class="text {s.get('kind','body')}">{s['text']}</div>{extra}
<div class="foot"><span>{spec['footer']}</span><span></span></div>
</div></body></html>"""

def main(spec_path, out_dir):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    n = len(spec["slides"])
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(spec["slides"]):
            pg.set_content(slide_html(spec, s, i, n))
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            pg.screenshot(path=str(out / f"slide_{i+1:02d}.png"))
        b.close()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
