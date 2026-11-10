# -*- coding: utf-8 -*-
"""
Lyrics video « Où est Dieu ? » – Leobenjo x Nathan
Rendu 1080x1920 / 30 i/s – direction artistique VHS / CRT années 90.

Usage :
  python3 src/render.py stills 20.5 57 ...   -> images de contrôle dans qc/
  python3 src/render.py chunk K N            -> rend le morceau K sur N (frames/chunk_K.mp4)
  python3 src/render.py qc                   -> contrôle zones de sécurité + paroles
"""
import json, math, os, subprocess, sys, random, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
W, H, FPS = 1080, 1920, 30
DUR = 170.85
NFR = int(DUR * FPS)
PW, PH = 1188, 2112           # plaque légèrement plus grande que le cadre (mouvement lent)

# Zone de sécurité Reels/TikTok (gabarit references/instagram) : x 0-940, y 220-1500
SAFE = (110, 300, 910, 1430)  # zone réellement autorisée pour les paroles (marges en plus)
XC, YC, MAXW = 520, 880, 760

# --------------------------------------------------------------------------------------
# MONTAGE : (début, clip, centre de recadrage 0..1, options)
#   xin : durée de fondu enchaîné vers ce plan (0 = coupe franche)
#   sp  : vitesse de lecture   ss : point d'entrée (s)   z : sens du zoom (+1 avant, -1 arrière)
# --------------------------------------------------------------------------------------
S = [
 # INTRO – la cassette démarre : pluie sur la vitre, attente (phase 1)
 (0.00,  2846, .38, dict(ss=2, z=1)),
 (9.50,  33379, .68, dict(xin=1.4, sp=.7, z=-1)),
 # COUPLET 1 – le constat, un regard, la ville
 (19.96, 41420, .47, dict(z=1)),
 (25.82, 40746, .50, dict(sp=.7, z=-1)),
 # « Je partage ce que j'ai vu… » – le trajet, le paysage qui défile
 (31.16, 25251, .42, dict(z=1)),
 (36.58, 26140, .50, dict(xin=.8, ss=6, z=1)),
 # l'enfant et le père (archive familiale) / la chambre, les yeux levés
 (42.30, 4542, .56, dict(osd='date1', z=1)),
 (48.56, 32187, .30, dict(z=1)),
 # REFRAIN 1 – le cri, puis l'envol
 (53.82, 46707, .36, dict(z=1)),
 (59.04, 45246, .50, dict(z=1)),
 # PONT 1 – marcher dans le noir / la lumière guide mes pas (bascule phase 2)
 (64.16, 9678, .50, dict(ss=20, z=1)),
 (67.06, 4893, .50, dict(z=-1)),
 (69.48, 9018, .55, dict(sp=.8, z=1)),
 # REFRAIN 2 – une fenêtre s'ouvre, la lumière perce
 (74.86, 924, .56, dict(ss=6, z=1)),
 (80.34, 9673, .50, dict(xin=.8, z=1)),
 # COUPLET 2 – le flow s'accélère
 (85.80, 48490, .50, dict(ss=10, z=1)),
 (88.16, 40654, .50, dict(sp=.8, z=-1)),
 (91.02, 4701, .58, dict(z=1)),
 (96.26, 31942, .50, dict(z=1, ex=.72)),
 (101.68, 4331, .48, dict(sp=.6, z=-1)),
 # « J'ai vécu ton amour » – le retour vers le père
 (106.61, 34372, .60, dict(xin=.6, z=1)),
 (111.92, 8864, .50, dict(z=1)),
 # REFRAIN 3 – espace, paix (phase 3)
 (117.30, 35830, .50, dict(z=1)),
 (123.30, 9317, .45, dict(xin=.6, z=-1)),
 # PONT 2 – la route au lever du jour, l'horizon
 (128.16, 52452, .55, dict(ss=3, z=1)),
 (133.50, 35873, .22, dict(xin=.6, z=1, ex=.8)),
 # REFRAIN 4 – apogée chaleureuse, relèvement
 (138.80, 4629, .50, dict(z=-1)),
 (144.48, 36985, .45, dict(ss=5, z=1)),
 # OUTRO – lever de soleil
 (149.62, 1086, .50, dict(xin=.8, ss=2, z=1)),
 (160.00, 21168, .50, dict(xin=1.6, ss=1, z=1)),
]
GLITCH = [0.55, 19.96, 42.30, 53.82, 85.80, 117.30, 138.80]

# Étalonnage : images-clés (t, saturation, contraste, exposition, noir délavé RGB, gain RGB)
# Étalonnage unique (identité VHS) : noirs délavés brun-bleuté, légère désaturation,
# hautes lumières beige vieilli. Ce sont les images, choisies selon les paroles, qui portent l'émotion.
G_SAT, G_CON, G_EXP = .58, .88, .97
G_BLK = np.array((.048, .043, .045), np.float32)
G_GAIN = np.array((1.01, .975, .925), np.float32)
def grade_at(t):
    return G_SAT, G_CON, G_EXP, G_BLK, G_GAIN

# --------------------------------------------------------------------------------------
# PLANS
# --------------------------------------------------------------------------------------
def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True).stdout
    j = json.loads(o); s = j["streams"][0]
    return s["width"], s["height"], float(j["format"]["duration"])

class Shot:
    def __init__(self, i):
        t0, clip, cx, o = S[i]
        self.t0 = t0; self.t1 = S[i + 1][0] if i + 1 < len(S) else DUR
        self.xin = o.get("xin", 0.0)
        self.xout = S[i + 1][3].get("xin", 0.0) if i + 1 < len(S) else 0.0
        self.a = self.t0 - self.xin / 2; self.b = self.t1 + self.xout / 2
        self.path = f"clips/{clip}.mp4"; self.clip = clip
        self.cx = cx; self.ex = o.get("ex", 1.0); self.sp = o.get("sp", 1.0); self.z = o.get("z", 1); self.osd = o.get("osd")
        w, h, d = probe(self.path); self.sw, self.sh, self.sd = w, h, d
        need = (self.b - self.a) * self.sp
        self.ss = o.get("ss", max(0.0, (d - need) / 2))
        if self.ss + need > d - 0.1: self.ss = max(0.0, d - need - 0.1)
        self.proc = None; self.k = None; self.last = None

    def _start(self, k):
        if self.proc: self.proc.kill()
        w, h = self.sw, self.sh
        if w / h > 9 / 16:
            cw = int(h * 9 / 16) // 2 * 2; x = int((w - cw) * self.cx)
            crop = f"crop={cw}:{h}:{x}:0"
        else:
            ch = int(w * 16 / 9) // 2 * 2; crop = f"crop={w}:{ch}:0:{(h - ch) // 2}"
        st = self.ss + k / FPS * self.sp
        vf = f"setpts=PTS/{self.sp},fps={FPS},{crop},scale={PW}:{PH}:flags=lanczos,format=rgb24"
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{st:.3f}", "-i", self.path,
                                      "-vf", vf, "-an", "-f", "rawvideo", "-"],
                                     stdout=subprocess.PIPE, bufsize=PW * PH * 3 * 2)
        self.k = k

    def frame(self, t):
        k = int(round((t - self.a) * FPS))
        if self.proc is None or k < self.k or k > self.k + 5: self._start(k)
        while self.k <= k:
            buf = self.proc.stdout.read(PW * PH * 3)
            if len(buf) == PW * PH * 3: self.last = np.frombuffer(buf, np.uint8).reshape(PH, PW, 3)
            self.k += 1
        # mouvement lent : zoom avant / arrière
        p = (t - self.a) / max(.01, self.b - self.a)
        if self.z < 0: p = 1 - p
        zf = 1.0 + 0.075 * p
        cw, ch = PW / zf, PH / zf
        x0, y0 = (PW - cw) / 2, (PH - ch) / 2
        im = Image.fromarray(self.last).resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
        return im

    def close(self):
        if self.proc: self.proc.kill(); self.proc = None

# --------------------------------------------------------------------------------------
# TYPOGRAPHIE
# --------------------------------------------------------------------------------------
F_SANS = "fonts/InstrumentSerif-Regular.ttf"; F_SERIF = "fonts/InstrumentSerif-Italic.ttf"; F_CRED = "fonts/Antonio-Medium.ttf"; F_VT = "fonts/VT323-Regular.ttf"
_fc = {}
def font(path, size, weight=None, width=None):
    key = (path, size, weight, width)
    if key not in _fc:
        f = ImageFont.truetype(path, size)
        _fc[key] = f
    return _fc[key]

CREAM = (244, 236, 220); GOLD = (236, 200, 132); SILVER = (206, 210, 216)
ACCENT = {"Dieu", "Jésus", "lumière", "foi", "amour", "gloire", "Toi"}

def word_key(t):
    return re.sub(r"[^\wÀ-ÿœ'-]", "", t)

def render_word(txt, f, color, glow=False, sw=1):
    l, t, r, b = f.getbbox(txt, stroke_width=sw)
    pad = 26
    w, h = r - l + 2 * pad, b - t + 2 * pad
    base = Image.new("L", (w, h), 0)
    ImageDraw.Draw(base).text((pad - l, pad - t), txt, font=f, fill=255, stroke_width=sw, stroke_fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = base.filter(ImageFilter.GaussianBlur(9)).point(lambda v: int(v * .62))
    shadow = Image.new("RGBA", (w, h), (8, 6, 10, 0)); shadow.putalpha(sh)
    out.alpha_composite(shadow, (0, 3))
    if glow:
        g = base.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .45))
        gl = Image.new("RGBA", (w, h), color + (0,)); gl.putalpha(g); out.alpha_composite(gl)
    # légère frange chromatique (intégration VHS, sans nuire à la lecture)
    for dx, col in ((-2, (255, 70, 60)), (2, (70, 140, 255))):
        fr = Image.new("RGBA", (w, h), col + (0,)); fr.putalpha(base.point(lambda v: int(v * .28)))
        tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0)); tmp.alpha_composite(fr, (max(dx, 0), 0), (max(-dx, 0), 0))
        out.alpha_composite(tmp)
    main = Image.new("RGBA", (w, h), color + (0,)); main.putalpha(base)
    out.alpha_composite(main)
    return out, pad - l, pad - t, r - l

# Cartons : groupes de lignes affichées ensemble + style d'apparition
#   word = mot par mot, group = par groupes (ponctuation), line = phrase entière
LINES = json.load(open("sync_paroles.json", encoding="utf-8"))
CARD_DEF = []
def addc(idx, style): CARD_DEF.append((idx, style))
for i in range(0, 12): addc([i], "word" if i not in (3, 7) else "group")
for base in (12, 20):
    addc([base], "group"); addc([base + 1], "group"); addc([base + 2], "word"); addc([base + 3], "group")
    if base == 12:
        for i in range(16, 20): addc([i], "word" if i != 19 else "group")
for pr in ([24, 25], [26, 27], [28, 29], [30, 31], [32, 33], [34, 35]): addc(pr, "group")
for i in (36, 37, 38, 39): addc([i], "word")
addc([40, 41], "group"); addc([42, 43], "group")
for base in (44, 52):
    addc([base], "group"); addc([base + 1], "group"); addc([base + 2], "word"); addc([base + 3], "group")
    if base == 44:
        for i in range(48, 52): addc([i], "word" if i != 51 else "group")
assert sorted(sum([c[0] for c in CARD_DEF], [])) == list(range(len(LINES))), "paroles manquantes"

class Card:
    def __init__(self, idx, style, nxt_start):
        self.lines = [LINES[i] for i in idx]; self.style = style
        size = 86
        while True:
            ok = self._layout(size)
            if ok or size <= 62: break
            size -= 4
        self.size = size
        first = min(w["appear"] for w in self.words)
        self.start = first
        last_e = self.lines[-1]["e"]
        self.end = min(nxt_start - 0.03, last_e + 1.6) if nxt_start else last_e + 1.8

    def _layout(self, size):
        rows = []   # each row: list of (word, appear)
        self.words = []
        for line in self.lines:
            ws = line["words"]
            # temps d'apparition selon le style
            grp_t = None; appears = []
            for k, w in enumerate(ws):
                if self.style == "line": a = line["s"]
                elif self.style == "group":
                    if grp_t is None: grp_t = w["s"]
                    a = grp_t
                    if re.search(r"[,:?!.;»]$", w["t"]): grp_t = None
                else: a = w["s"]
                appears.append(a - 0.06)
            # titre "Où est Dieu ?"
            head = []
            if line["line"].startswith("Où est Dieu ?"): head = [0, 1, 2, 3]
            items = []
            for k, w in enumerate(ws):
                t = w["t"]; isacc = word_key(t) in ACCENT and not (word_key(t) == "Toi" and False)
                if k in head:
                    f = font(F_SERIF, int(size * 1.45)); col = GOLD if word_key(t) == "Dieu" else CREAM; glow = word_key(t) == "Dieu"
                elif isacc:
                    f = font(F_SERIF, int(size * 1.10)); col = GOLD; glow = True
                else:
                    f = font(F_SANS, size); col = CREAM; glow = False
                items.append(dict(t=t, f=f, col=col, glow=glow, appear=appears[k], head=k in head))
            # rangée de titre séparée
            cur = []; curw = 0; sp = size * 0.24
            def flush():
                nonlocal cur, curw
                if cur: rows.append(cur)
                cur, curw = [], 0
            prev_head = None
            for it in items:
                ww = it["f"].getlength(it["t"])
                if prev_head is not None and it["head"] != prev_head: flush()
                if cur and curw + sp + ww > MAXW: flush()
                cur.append(it); curw += (sp if len(cur) > 1 else 0) + ww; prev_head = it["head"]
                if ww > MAXW: return False
            flush()
            rows.append(None)  # séparateur de lignes
        rows = rows[:-1]
        nrows = sum(1 for r in rows if r)
        if nrows > (5 if len(self.lines) > 1 else 4): return False
        # mise en place verticale
        lh = []
        for r in rows:
            if r is None: lh.append(size * 0.45)
            else: lh.append(max(it["f"].size for it in r) * (1.08 if r[0]["head"] else 1.22))
        total = sum(lh); y = YC - total / 2
        sp = size * 0.24
        self.bbox = [9999, 9999, 0, 0]
        for r, h in zip(rows, lh):
            if r is None: y += h; continue
            base_y = y + h * 0.80          # ligne de base
            widths = [it["f"].getlength(it["t"]) for it in r]
            tw = sum(widths) + sp * (len(r) - 1); x = XC - tw / 2
            for it, ww in zip(r, widths):
                img, ox, oy, _ = render_word(it["t"], it["f"], it["col"], it["glow"])
                asc = it["f"].getmetrics()[0]
                l, t, rr, b = it["f"].getbbox(it["t"])
                px = int(round(x - ox)); py = int(round(base_y - asc - oy))
                it.update(img=img, x=px, y=py)
                gx0, gy0 = x, base_y - asc + t; gx1, gy1 = x + ww, base_y - asc + b
                self.bbox = [min(self.bbox[0], gx0), min(self.bbox[1], gy0), max(self.bbox[2], gx1), max(self.bbox[3], gy1)]
                self.words.append(it); x += ww + sp
            y += h
        x0, y0, x1, y1 = self.bbox
        return x0 >= SAFE[0] and x1 <= SAFE[2] and y0 >= SAFE[1] and y1 <= SAFE[3]

    def alpha(self, t):
        if t < self.start or t > self.end: return 0.0
        return min(1.0, (self.end - t) / 0.2)

CARDS = []
for n, (idx, st) in enumerate(CARD_DEF):
    nxt = None
    if n + 1 < len(CARD_DEF):
        nl = LINES[CARD_DEF[n + 1][0][0]]; nxt = nl["s"] - 0.06
    CARDS.append(Card(idx, st, nxt))

def ease(u): u = min(1, max(0, u)); return 1 - (1 - u) ** 3

def draw_text(fr, t):
    """fr : Image RGBA"""
    for c in CARDS:
        ca = c.alpha(t)
        if ca <= 0: continue
        drift = -6 * (t - c.start) / max(.5, c.end - c.start)
        for it in c.words:
            u = (t - it["appear"]) / 0.18
            if u <= 0: continue
            a = ease(u) * ca
            dy = (1 - ease(u)) * 14 + drift
            img = it["img"]
            if a < 0.999:
                img = img.copy(); al = np.asarray(img.getchannel("A"), np.float32) * a
                img.putalpha(Image.fromarray(al.astype(np.uint8)))
            fr.alpha_composite(img, (it["x"], int(it["y"] + dy)))

def text_shade(arr, t):
    """assombrit doucement la zone derrière les paroles (lisibilité)"""
    for c in CARDS:
        ca = c.alpha(t)
        if ca <= 0: continue
        if not hasattr(c, "shade"):
            x0, y0, x1, y1 = c.bbox; m = 90
            mk = Image.new("L", (W, H), 0)
            ImageDraw.Draw(mk).rounded_rectangle((x0 - m, y0 - m * .7, x1 + m, y1 + m * .7), radius=120, fill=255)
            c.shade = np.asarray(mk.filter(ImageFilter.GaussianBlur(70)), np.float32)[..., None] / 255
        k = min(1, (t - c.start) / 0.3 + 0.2) * ca
        arr *= (1 - 0.52 * k * c.shade)

# --------------------------------------------------------------------------------------
# TITRES ET OSD CAMÉSCOPE
# --------------------------------------------------------------------------------------
def title_layers():
    L = []
    f1 = font(F_CRED, 34)
    s = "L E O B E N J O    ×    N A T H A N"
    img, ox, oy, w = render_word(s, f1, SILVER)
    L.append(("small", img, int(XC - w / 2 - ox), 760))
    f2 = font(F_SERIF, 170)
    img2, ox2, oy2, w2 = render_word("Où est Dieu ?", f2, CREAM, glow=True)
    L.append(("big", img2, int(XC - w2 / 2 - ox2), 800))
    return L
TITLE = title_layers()

def draw_title(fr, t):
    for t0, t1 in ((9.2, 19.4), (152.0, 168.6)):
        if t0 <= t <= t1:
            for kind, img, x, y in TITLE:
                d = 0.0 if kind == "small" else 0.6
                a = ease((t - t0 - d) / 1.2) * min(1, (t1 - t) / 0.8)
                if a <= 0: continue
                im = img.copy(); al = np.asarray(im.getchannel("A"), np.float32) * a
                im.putalpha(Image.fromarray(al.astype(np.uint8)))
                fr.alpha_composite(im, (x, y))

FVT = ImageFont.truetype(F_VT, 54)
def draw_osd(fr, t, shot):
    d = ImageDraw.Draw(fr)
    col = (236, 236, 228, 215)
    def tri(x, y):
        d.polygon([(x, y), (x, y + 34), (x + 28, y + 17)], fill=col)
    if t < 4.2 and (t < 2.5 or int(t * 2) % 2 == 0):
        tri(104, 268); d.text((146, 258), "PLAY", font=FVT, fill=col)
    if t < 4.2:
        d.text((104, 316), "SP", font=FVT, fill=col)
    if shot and shot.osd:
        lt = t - shot.t0
        if lt > 0.15:
            date = "JUIN 14 1996" if shot.osd == "date1" else "DÉC. 24 1997"
            d.text((104, 262), date, font=FVT, fill=col)
            s = int(lt + (8 * 3600 + 14 * 60 + 5 if shot.osd == "date1" else 19 * 3600 + 2 * 60 + 41))
            d.text((104, 310), f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}", font=FVT, fill=col)
    if t > DUR - 3.6 and t < DUR - 0.9:
        d.rectangle((104, 272, 132, 300), fill=col); d.text((146, 258), "STOP", font=FVT, fill=col)

# --------------------------------------------------------------------------------------
# TRAITEMENT VHS / CRT
# --------------------------------------------------------------------------------------
rng0 = np.random.default_rng(7)
NOISE = [rng0.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(16)]
def noise_full(k):
    n = NOISE[k % 16]
    return np.repeat(np.repeat(n, 2, 0), 2, 1)[..., None]   # grain légèrement « gros »
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = 1 - 0.38 * (((xx - W / 2) / (W * .62)) ** 2 + ((yy - H / 2) / (H * .60)) ** 2) ** 1.25
SCAN = 1 - 0.055 * (np.floor(yy / 2) % 2)          # lignes de balayage fines et douces
MASK = np.clip(VIG * SCAN, 0, 1)[..., None].astype(np.float32)

def vhs_soft(im):
    """luminance un peu molle + chroma baveuse et décalée (signal composite)"""
    im = im.resize((760, H), Image.BILINEAR).resize((W, H), Image.BICUBIC)
    y, cb, cr = im.convert("YCbCr").split()
    cb = cb.resize((W // 5, H // 2), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    cr = cr.resize((W // 5, H // 2), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    cb = Image.fromarray(np.roll(np.asarray(cb), 4, 1)); cr = Image.fromarray(np.roll(np.asarray(cr), 5, 1))
    return Image.merge("YCbCr", (y, cb, cr)).convert("RGB")

def glitch(arr, t, n):
    """défauts de tracking ponctuels aux changements de partie"""
    rng = np.random.default_rng(n)
    g = 0.0
    for b in GLITCH:
        dt = t - b
        if -0.14 <= dt <= 0.20: g = max(g, 1 - abs(dt) / 0.2)
    if g > 0:
        # bande de tracking qui roule
        yc = int((H * (0.85 - (t * 3.7 % 1) * 0.7)))
        hb = int(60 + 160 * g)
        y0, y1 = max(0, yc - hb), min(H, yc + hb)
        for y in range(y0, y1, 3):
            arr[y:y + 3] = np.roll(arr[y:y + 3], int(rng.normal(0, 18 * g)), 1)
        nz = rng.random((y1 - y0, W)) < 0.04 * g
        arr[y0:y1][nz] = 230
        arr *= (1 + 0.08 * g * rng.normal())
        # décalage horizontal global léger
        shift = int(rng.normal(0, 7 * g))
        arr[:] = np.roll(arr, shift, 1)
    elif rng.random() < 0.025:
        # micro‑imperfection : une fine bande décalée sur une image
        y = int(rng.random() * H); h = int(4 + rng.random() * 14)
        arr[y:y + h] = np.roll(arr[y:y + h], int(rng.normal(0, 6)), 1)
    # head-switching : bas de l'image (zone d'interface, sans paroles)
    hs = 22
    for i in range(hs):
        arr[H - hs + i] = np.roll(arr[H - hs + i], int((i / hs) ** 2 * 26 + rng.normal(0, 2)), 0)

def snow(n):
    rng = np.random.default_rng(1000 + n)
    s = rng.random((H // 3, W // 3)).astype(np.float32)
    s = np.repeat(np.repeat(s, 3, 0), 3, 1)
    rows = rng.random((H // 3, 1)) * .5 + .5
    s = s * np.repeat(rows, 3, 0)
    return np.stack([s * 200, s * 205, s * 225], -1)

# --------------------------------------------------------------------------------------
SHOTS = None
def active(t):
    out = []
    for s in SHOTS:
        if s.a <= t < s.b:
            if s.xin and t < s.t0 + s.xin / 2: w = (t - s.a) / s.xin
            elif s.xout and t > s.t1 - s.xout / 2: w = 1 - (t - (s.t1 - s.xout / 2)) / s.xout
            else: w = 1.0
            out.append((s, max(0, min(1, w))))
    return out

def render_frame(n):
    t = n / FPS
    act = active(t)
    arr = None
    for s, w in act:
        a = np.asarray(s.frame(t), np.float32) * s.ex
        arr = a * w if arr is None else arr + a * w
    if arr is None: arr = np.zeros((H, W, 3), np.float32)
    # étalonnage
    sat, con, expo, blk, gain = grade_at(t)
    x = arr / 255.0
    lum = (x[..., :1] * .299 + x[..., 1:2] * .587 + x[..., 2:] * .114)
    x = lum + (x - lum) * sat
    x = 0.5 + (x - 0.5) * con
    x = np.clip(x * expo * gain, 0, 1)
    x = x ** 1.04
    x = blk + x * (1 - blk) * 0.97            # noirs délavés, blancs légèrement éteints
    text_shade(x, t)
    # fondu au noir final
    if t > DUR - 2.6: x *= max(0, (DUR - 0.4 - t) / 2.2)
    im = vhs_soft(Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8)))
    arr = np.asarray(im, np.float32)
    glitch(arr, t, n)
    if t < 0.55:   # démarrage de la cassette
        k = 1 - t / 0.55
        arr = arr * (1 - k) + snow(n) * k
    fr = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_title(fr, t)
    draw_text(fr, t)
    shot = max(act, key=lambda p: p[1])[0] if act else None
    draw_osd(fr, t, shot)
    arr = np.asarray(fr.convert("RGB"), np.float32)
    arr = arr * MASK + noise_full(n) * 7.5
    return np.clip(arr, 0, 255).astype(np.uint8)

def init_shots():
    global SHOTS
    SHOTS = [Shot(i) for i in range(len(S))]

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "qc":
        bad = 0
        for c in CARDS:
            x0, y0, x1, y1 = c.bbox
            ok = x0 >= SAFE[0] and x1 <= SAFE[2] and y0 >= SAFE[1] and y1 <= SAFE[3]
            bad += not ok
            print(f"{c.start:7.2f}-{c.end:7.2f} taille {c.size:2d} bbox x {x0:5.0f}-{x1:5.0f} y {y0:5.0f}-{y1:5.0f} {'OK' if ok else 'HORS ZONE'} | {' / '.join(l['line'] for l in c.lines)}")
        src = [l.strip() for l in open("paroles.txt", encoding="utf-8") if l.strip()]
        shown = [" ".join(w["t"] for w in l["words"]) for c in CARDS for l in c.lines]
        print("cartons hors zone :", bad, "| lignes identiques à l'original :", sum(a == b for a, b in zip(src, shown)), "/", len(src))
        for c, d in zip(CARDS, CARDS[1:]):
            if c.end > d.start + 0.01: print("CHEVAUCHEMENT", c.start, d.start)
        init_shots()
        for s in SHOTS:
            need = (s.b - s.a) * s.sp
            if s.ss + need > s.sd + 0.05: print("PLAN TROP COURT", s.clip, s.ss, need, s.sd)
    elif cmd == "stills":
        init_shots(); os.makedirs("qc", exist_ok=True)
        for v in sys.argv[2:]:
            t = float(v); Image.fromarray(render_frame(int(t * FPS))).save(f"qc/still_{t:06.2f}.jpg", quality=90)
            for s in SHOTS: s.close()
    elif cmd == "chunk":
        k, N = int(sys.argv[2]), int(sys.argv[3])
        a, b = NFR * k // N, NFR * (k + 1) // N
        init_shots(); os.makedirs("frames", exist_ok=True)
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12",
                                "-tune", "grain", "-pix_fmt", "yuv420p", f"frames/chunk_{k}.mp4"], stdin=subprocess.PIPE)
        for n in range(a, b):
            enc.stdin.write(render_frame(n).tobytes())
            t = n / FPS
            for s in SHOTS:
                if s.proc and t > s.b + 0.1: s.close()
            if (n - a) % 150 == 0: print(f"chunk {k}: {n - a}/{b - a}", flush=True)
        enc.stdin.close(); enc.wait()
        print("done", k)
