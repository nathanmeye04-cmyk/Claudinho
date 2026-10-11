"""Génère le logotype CI-O MIAM (lettrage dessiné, tracés SVG) et ses variantes."""
import os
OUT = os.path.dirname(os.path.abspath(__file__))

CREME, CHOCO, CAFE = "#EAD3B5", "#4A241A", "#79513A"
W = 50          # graisse du trait (lettres pleines, terminaisons rondes)
TOP, BASE = 26, 186   # ligne de tête / ligne de base (axe du trait)

def drip(c, y0, L, n=17, nn=12, r=19, f=22):
    """Goutte de crème : congé large, col qui s'affine, perle ronde au bout."""
    import math
    yb = y0 + L - r
    dy = math.sqrt(r * r - nn * nn)
    return (f"M{c-n-f},{y0} C{c-n+2},{y0} {c-n},{y0+10} {c-n},{y0+20} "
            f"C{c-n},{y0+L*0.45} {c-nn},{y0+L*0.45} {c-nn},{yb-dy:.1f} "
            f"A{r},{r} 0 1 0 {c+nn},{yb-dy:.1f} "
            f"C{c+nn},{y0+L*0.45} {c+n},{y0+L*0.45} {c+n},{y0+20} "
            f"C{c+n},{y0+10} {c+n-2},{y0} {c+n+f},{y0} Z")

def letters():
    """Renvoie une liste de lettres : (traits, formes pleines, décalage vertical, rotation, pivot)."""
    L = []
    cy = 106
    # C — ovale ouvert, terminaisons arrondies
    cx = 96
    L.append(([f"M{cx+50},{cy-56} C{cx+30},{cy-80} {cx-8},{cy-84} {cx-36},{cy-70} "
               f"C{cx-80},{cy-48} {cx-82},{cy+40} {cx-44},{cy+68} "
               f"C{cx-12},{cy+88} {cx+30},{cy+82} {cx+54},{cy+52}"], [], 0, -3, cx))
    # I
    ix = 212
    L.append(([f"M{ix},{TOP} C{ix-2},80 {ix+2},130 {ix},{BASE}"], [], -5, 0, ix))
    # trait d'union — pastille avec une petite goutte
    hx = 276
    L.append(([f"M{hx},112 L{hx+34},112"], [drip(hx+24, 118, 40, n=8, nn=8, r=8, f=8)], 2, 0, hx))
    # O — une goutte coule de sa base
    ox = 444
    L.append(([f"M{ox},{cy-80} C{ox+46},{cy-80} {ox+74},{cy-40} {ox+74},{cy} "
               f"C{ox+74},{cy+44} {ox+44},{cy+80} {ox},{cy+80} "
               f"C{ox-44},{cy+80} {ox-74},{cy+44} {ox-74},{cy} "
               f"C{ox-74},{cy-40} {ox-46},{cy-80} {ox},{cy-80} Z"],
              [drip(ox+2, 186, 66, n=15, nn=15, r=15, f=9)], 5, 4, ox))
    def M(x, w=146):
        return (f"M{x},{BASE} L{x},62 C{x},30 {x+30},18 {x+44},46 "
                f"L{x+w/2},118 L{x+w-44},46 C{x+w-30},18 {x+w},30 {x+w},62 L{x+w},{BASE}")
    m1 = 636
    L.append(([M(m1)], [], -3, -2, m1 + 73))
    i2 = m1 + 146 + 66
    L.append(([f"M{i2},{TOP} C{i2-2},80 {i2+2},130 {i2},{BASE}"], [], 3, 0, i2))
    ax, aw = i2 + 66, 132
    L.append(([f"M{ax},{BASE} L{ax},96 C{ax},48 {ax+28},{TOP} {ax+aw/2},{TOP} "
               f"C{ax+aw-28},{TOP} {ax+aw},48 {ax+aw},96 L{ax+aw},{BASE}",
               f"M{ax},138 L{ax+aw},138"], [], -4, 2, ax + aw / 2))
    m2 = ax + aw + 66
    L.append(([M(m2)], [drip(m2 + 146, 186, 54, n=15, nn=15, r=15, f=9)], 1, -2, m2 + 73))
    return L

def _letter(st, fl, dy, rot, px, color, outline, ow):
    g = []
    if outline:
        g.append(f'<g fill="none" stroke="{outline}" stroke-width="{W+ow}" stroke-linecap="round" stroke-linejoin="round">'
                 + "".join(f'<path d="{d}"/>' for d in st) + "</g>")
        g.append(f'<g fill="{outline}" stroke="{outline}" stroke-width="{ow}" stroke-linejoin="round">'
                 + "".join(f'<path d="{d}"/>' for d in fl) + "</g>")
    g.append(f'<g fill="none" stroke="{color}" stroke-width="{W}" stroke-linecap="round" stroke-linejoin="round">'
             + "".join(f'<path d="{d}"/>' for d in st) + "</g>")
    g.append(f'<g fill="{color}">' + "".join(f'<path d="{d}"/>' for d in fl) + "</g>")
    return f'<g transform="translate(0 {dy}) rotate({rot} {px} 106)">' + "".join(g) + "</g>"

def wordmark(color, outline=None, ow=30):
    Ls = letters()
    body = ""
    if outline:
        body += "".join(_letter(*l, outline, outline, ow) for l in Ls)
    body += "".join(_letter(*l, color, None, ow) for l in Ls)
    return f'<g transform="skewX(-6) translate(14 0)">{body}</g>'

VB = "-40 -40 1420 360"
def svg(color, bg=None, outline=None):
    rect = f'<rect x="-40" y="-40" width="1420" height="360" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VB}">'
            f'<title>CI-O MIAM</title>{rect}{wordmark(color, outline)}</svg>')

files = {
    "ci-o-miam_principal.svg": svg(CHOCO, CREME),
    "ci-o-miam_inverse.svg": svg(CREME, CHOCO),
    "ci-o-miam_mono-choco.svg": svg(CHOCO),
    "ci-o-miam_mono-cafe.svg": svg(CAFE),
    "ci-o-miam_mono-blanc.svg": svg("#FFFFFF"),
    "ci-o-miam_pot-transparent.svg": svg(CHOCO, outline=CREME),
}
os.makedirs(f"{OUT}/svg", exist_ok=True)
for n, c in files.items():
    open(f"{OUT}/svg/{n}", "w").write(c)

def inline(color, outline=None):
    return (f'<svg viewBox="{VB}" xmlns="http://www.w3.org/2000/svg">{wordmark(color, outline)}</svg>')

board = f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}}
body{{width:1600px;height:1740px;background:#F6EBDD;font-family:'Inter',sans-serif;color:{CHOCO};padding:70px}}
.k{{font-size:13px;letter-spacing:.22em;text-transform:uppercase;font-weight:600;opacity:.7}}
.hero{{background:{CREME};border-radius:44px;height:640px;display:flex;align-items:center;justify-content:center;position:relative}}
.hero svg{{width:1120px}}
.tag{{position:absolute;left:44px;top:38px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:28px}}
.card{{border-radius:36px;height:360px;display:flex;align-items:center;justify-content:center;position:relative}}
.card svg{{width:600px}}
.card .k{{position:absolute;left:34px;top:28px}}
.row3{{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:28px}}
.row3 .card{{height:280px}} .row3 .card svg{{width:400px}}
.pal{{display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:28px}}
.sw{{border-radius:28px;height:150px;padding:28px;display:flex;flex-direction:column;justify-content:flex-end;font-size:15px;font-weight:600}}
.sw span{{font-weight:400;opacity:.8;font-size:13px;margin-top:4px}}
.head{{display:flex;justify-content:space-between;align-items:end;margin-bottom:36px}}
.head h1{{font-size:20px;letter-spacing:.2em;font-weight:700}}
</style></head><body>
<div class="head"><h1>CI-O MIAM — LOGOTYPE</h1><div class="k">Proposition 01 · Lettrage sur mesure</div></div>
<div class="hero"><div class="k tag">Version principale</div>{inline(CHOCO)}</div>
<div class="row">
 <div class="card" style="background:{CHOCO}"><div class="k" style="color:{CREME}">Version inversée</div>{inline(CREME)}</div>
 <div class="card" style="background:#fff;border:1.5px solid #e6d6c2"><div class="k">Monochrome</div>{inline(CHOCO)}</div>
</div>
<div class="row3">
 <div class="card" style="background:#F2E3C9"><div class="k">Pot · Cerelac</div>{inline(CHOCO, CREME)}</div>
 <div class="card" style="background:#5A2E20"><div class="k" style="color:{CREME}">Pot · Chocolat</div>{inline(CHOCO, CREME)}</div>
 <div class="card" style="background:#A27A5C"><div class="k" style="color:#fff">Pot · Nescafé</div>{inline(CHOCO, CREME)}</div>
</div>
<div class="pal">
 <div class="sw" style="background:{CREME}">Beige crème<span>{CREME} · Cerelac</span></div>
 <div class="sw" style="background:{CHOCO};color:{CREME}">Brun chocolat<span>{CHOCO} · Chocolat</span></div>
 <div class="sw" style="background:{CAFE};color:{CREME}">Marron café<span>{CAFE} · Nescafé</span></div>
</div>
</body></html>"""
open(f"{OUT}/planche.html", "w").write(board)
