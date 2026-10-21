"""Render an ART Lab typographic carousel spec as a silent 9:16 reel (motion first).

Usage: python3 render_reel.py spec.json out.mp4 [seconds_per_beat]

Same spec as render_carousel.py. The vermilion disc is already moving in the
first frame and travels continuously for the whole reel; each slide's text
holds for a beat, fades out, and the next fades in. Silent: audio is added in
Instagram on upload. Output is 1080x1920, 30fps, H.264, under 3 minutes.
"""
import json, sys, pathlib, math, base64, subprocess, tempfile, shutil
from playwright.sync_api import sync_playwright

FONT_DIR = pathlib.Path(__file__).resolve().parent / "fonts"
if not FONT_DIR.exists():
    FONT_DIR = pathlib.Path(__file__).resolve().parent.parent / "fonts"
W, H, FPS, FADE = 1080, 1920, 30, 0.6

def _font(name):
    return "data:font/ttf;base64," + base64.b64encode((FONT_DIR / name).read_bytes()).decode()

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face { font-family:'Serif'; src:url('%(sr)s'); }
@font-face { font-family:'Serif'; font-style:italic; src:url('%(si)s'); }
@font-face { font-family:'Mono'; src:url('%(mr)s'); }
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:%(W)dpx; height:%(H)dpx; background:#EEE8DC; overflow:hidden; color:#1C1A16; -webkit-font-smoothing:antialiased; }
.top { position:absolute; left:88px; right:88px; top:150px; display:flex; justify-content:space-between;
  font-family:'Mono'; font-size:24px; letter-spacing:.14em; color:#6F685C; text-transform:uppercase;
  border-bottom:1px solid #CFC6B5; padding-bottom:26px; }
#disc { position:absolute; border-radius:50%%; background:#D2471C; }
.t { position:absolute; left:88px; right:110px; bottom:520px; font-family:'Serif'; opacity:0; text-wrap:pretty; }
.hook { font-size:104px; line-height:1.0; letter-spacing:-.01em; }
.body { font-size:72px; line-height:1.12; }
.close { font-size:80px; line-height:1.08; }
.k { display:block; margin-top:40px; font-family:'Mono'; font-size:24px; letter-spacing:.12em; text-transform:uppercase; color:#6F685C; }
em { font-style:italic; }
.foot { position:absolute; left:88px; right:88px; bottom:300px; font-family:'Mono'; font-size:22px;
  letter-spacing:.14em; color:#6F685C; text-transform:uppercase; border-top:1px solid #CFC6B5; padding-top:24px; }
</style></head><body>
<div class="top"><span>%(series)s %(issue)s</span><span id="count"></span></div>
<div id="disc"></div>
%(texts)s
<div class="foot">%(footer)s</div>
<script>
const N = %(n)d, W = %(W)d;
function ease(x){ return x<.5 ? 4*x*x*x : 1-Math.pow(-2*x+2,3)/2; }
window.setFrame = function(t, total, beat, fade){
  // Disc: continuous path across the whole reel, eased, never still.
  const p = ease(Math.min(t/total,1));
  const size = 360 - 170*p;
  const x = (W-88-size) - (W-176-size)*p;
  const y = 330 + 260*Math.sin(Math.PI*p) + 18*Math.sin(t*2.1);
  const d = document.getElementById('disc');
  d.style.width = d.style.height = size+'px'; d.style.left = x+'px'; d.style.top = y+'px';
  // Text: each beat holds, crossfades over `fade` seconds.
  for (let i=0;i<N;i++){
    const start = i*beat, end = (i+1)*beat;
    // Dip through paper: outgoing text fades out, then incoming fades in; the disc never stops.
    let o = (t >= start && t <= end) ? 1 : 0;
    if (o && i>0) o = Math.min(o, (t-start)/(fade/2));
    if (o && i<N-1) o = Math.min(o, (end-t)/(fade/2));
    document.getElementById('t'+i).style.opacity = Math.max(0,Math.min(1,o));
  }
  const cur = Math.min(N-1, Math.floor(t/beat));
  document.getElementById('count').textContent = String(cur+1).padStart(2,'0')+' / '+String(N).padStart(2,'0');
};
</script></body></html>"""

def build_page(spec):
    texts = []
    for i, s in enumerate(spec["slides"]):
        extra = "".join(f'<span class="k">{s[k]}</span>' for k in ("kicker", "sub") if s.get(k))
        texts.append(f'<div class="t {s.get("kind","body")}" id="t{i}">{s["text"]}{extra}</div>')
    page = PAGE.replace("#D2471C", spec.get("accent", "#D2471C"))
    return page % dict(sr=_font("InstrumentSerif-Regular.ttf"), si=_font("InstrumentSerif-Italic.ttf"),
                       mr=_font("DMMono-Regular.ttf"), W=W, H=H, series=spec["series"], issue=spec["issue"],
                       texts="\n".join(texts), footer=spec["footer"], n=len(spec["slides"]))

def main(spec_path, out_path, beat=4.5):
    spec = json.loads(pathlib.Path(spec_path).read_text())
    n = len(spec["slides"])
    total = n * beat
    assert total < 180, "Reels over 3 minutes are not recommended to non-followers"
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.set_content(build_page(spec))
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            frames = int(total * FPS)
            for f in range(frames):
                pg.evaluate(f"setFrame({f/FPS}, {total}, {beat}, {FADE})")
                pg.screenshot(path=str(tmp / f"f{f:05d}.png"))
            b.close()
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png"),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out_path],
                       check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"rendered {total:.1f}s reel to {out_path}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 4.5)
