"""Écriture manuscrite : tracés réels (police à trait unique Hershey « cursive »),
rendus humains (irrégularités de taille, d'inclinaison, de ligne, tremblement),
mise en page sur la feuille et ordonnancement temporel trait par trait.

Chaque segment d'encre : x0, y0, x1, y1, largeur, instant, charge d'encre."""
import math
import zlib

import numpy as np
import HersheyFonts

# --- Glyphes -----------------------------------------------------------------

_H = HersheyFonts.HersheyFonts()
_H.load_default_font('cursive')
_CACHE = {}

_COMPOSE = {
    'é': ('e', 'aigu'), 'è': ('e', 'grave'), 'ê': ('e', 'circ'), 'ë': ('e', 'trema'),
    'à': ('a', 'grave'), 'â': ('a', 'circ'), 'ù': ('u', 'grave'), 'û': ('u', 'circ'),
    'î': ('i', 'circ'), 'ï': ('i', 'trema'), 'ô': ('o', 'circ'), 'ç': ('c', 'cedille'),
    'É': ('E', 'aigu'), 'È': ('E', 'grave'), 'À': ('A', 'grave'), 'Ç': ('C', 'cedille'),
    'Ê': ('E', 'circ'),
}
_SUBST = {'’': "'", '‘': "'", '«': '"', '»': '"', '…': '.'}


def _accent(kind, cx, capital):
    top = -23.0 if capital else -11.0
    if kind == 'aigu':
        return [[(cx - 1.5, top), (cx + 0.8, top - 2.6), (cx + 2.8, top - 4.6)]]
    if kind == 'grave':
        return [[(cx - 2.2, top - 4.5), (cx - 0.2, top - 2.0), (cx + 1.6, top)]]
    if kind == 'circ':
        return [[(cx - 3.0, top), (cx + 0.2, top - 3.8), (cx + 3.2, top)]]
    if kind == 'trema':
        return [[(cx - 2.6, top - 1.0), (cx - 2.2, top - 1.6)], [(cx + 2.4, top - 1.0), (cx + 2.8, top - 1.6)]]
    if kind == 'cedille':
        return [[(cx + 0.3, 0.0), (cx + 0.8, 2.2), (cx + 2.8, 3.4), (cx + 1.8, 5.8), (cx - 1.6, 6.2)]]
    return []


def glyph(ch):
    """Traits du caractère en unités Hershey : x depuis le bord gauche,
    y = 0 sur la ligne de base, négatif vers le haut. Renvoie (traits, chasse)."""
    if ch in _CACHE:
        return _CACHE[ch]
    ch2 = _SUBST.get(ch, ch)
    base, acc = _COMPOSE.get(ch2, (ch2, None))
    gs = list(_H.glyphs_for_text(base))
    if not gs:
        raise ValueError(f'glyphe manquant : {ch!r}')
    g = gs[0]
    lo = g.left_offset
    strokes = [[(x - lo, y - 9.0) for x, y in s] for s in g.strokes]
    if base == "'":                       # apostrophe plus marquée, comme à la plume
        strokes = [[(2.4, -15.5), (2.2, -14.2), (1.5, -12.5), (0.4, -10.6)]]
    if acc:
        if base in 'ij':
            strokes = [s for s in strokes if (max(p[1] for p in s) - min(p[1] for p in s)) > 2.5]
        (x0, _), (x1, _) = g.draw_box
        cx = (x0 + x1) / 2 - lo + (1.0 if base.islower() else 2.5)
        strokes += _accent(acc, cx, base.isupper())
    _CACHE[ch] = (strokes, float(g.char_width))
    return _CACHE[ch]


# --- Géométrie ----------------------------------------------------------------

def catmull_rom(pts, step):
    """Lissage centripète d'un trait puis rééchantillonnage à pas constant (px)."""
    p = np.asarray(pts, float)
    if len(p) == 1:
        return p
    keep = np.r_[True, np.linalg.norm(np.diff(p, axis=0), axis=1) > 1e-6]
    p = p[keep]
    if len(p) < 3:
        dense = p
    else:
        q = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
        out = []
        for i in range(1, len(q) - 2):
            p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
            t0 = 0.0
            t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
            t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
            t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
            n = max(2, int(np.linalg.norm(p2 - p1) / 0.8))
            for t in np.linspace(t1, t2, n, endpoint=False):
                a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
                a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
                a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
                b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
                b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
                out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
        out.append(p[-1])
        dense = np.asarray(out)
    seg = np.linalg.norm(np.diff(dense, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seg)]
    if cum[-1] < 1e-6:
        return dense[:1]
    n = max(2, int(math.ceil(cum[-1] / step)) + 1)
    s = np.linspace(0, cum[-1], n)
    return np.c_[np.interp(s, cum, dense[:, 0]), np.interp(s, cum, dense[:, 1])]


def tremble(d, rng, amp=1.0):
    """Tremblement de la main : petites ondulations lentes le long du trait."""
    if len(d) < 3:
        return d
    seg = np.linalg.norm(np.diff(d, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]
    tg = np.gradient(d, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9
    nrm = np.c_[-tg[:, 1], tg[:, 0]]
    off = amp * (0.75 * np.sin(s / 37.0 + rng.uniform(0, 6.3)) + 0.4 * np.sin(s / 11.0 + rng.uniform(0, 6.3))
                 + 0.25 * np.sin(s / 5.3 + rng.uniform(0, 6.3)))
    return d + nrm * off[:, None]


class Plume:
    """Épaisseur selon la direction (pleins descendants, déliés montants),
    l'angle du bec et la vitesse (la plume appuie dans les courbes)."""

    def __init__(self, w0, nib_deg=38.0):
        self.w0 = w0
        self.nib = math.radians(nib_deg)

    def widths(self, p, heavy=1.0, rng=None):
        d = np.gradient(p, axis=0)
        ln = np.linalg.norm(d, axis=1) + 1e-9
        down = np.clip(d[:, 1] / ln, 0, 1)
        theta = np.arctan2(d[:, 1], d[:, 0])
        nib = np.abs(np.sin(theta - self.nib))
        dd = np.gradient(np.unwrap(theta))
        curv = np.clip(np.abs(dd) * 4, 0, 1)
        w = self.w0 * (0.38 + 0.70 * down ** 1.25) * (0.76 + 0.34 * nib) * (1 + 0.18 * curv) * heavy
        if rng is not None:                                  # pression irrégulière
            s = np.arange(len(w))
            w *= 1 + 0.10 * np.sin(s / 23.0 + rng.uniform(0, 6.3)) + 0.05 * np.sin(s / 7.0 + rng.uniform(0, 6.3))
        k = np.ones(7) / 7
        if len(w) > 7:
            w = np.convolve(np.pad(w, 3, mode='edge'), k, mode='valid')
        n = len(w)
        ramp = np.minimum(1, np.minimum(np.arange(n) + 1, n - np.arange(n)) / 5.0)
        return w * (0.62 + 0.38 * ramp)


# --- Mise en page et ordonnancement --------------------------------------------

STYLES = {
    None: dict(scale=1.0, align='left'),
    'entete': dict(scale=1.0, align='center'),
    'titre': dict(scale=1.3, align='center'),
    'signature': dict(scale=2.6, align='center'),
    'signature2': dict(scale=1.15, align='right'),
}


class Lettre:
    """Une feuille : mise en page des mots, segments d'encre datés et
    trajectoire de la plume."""

    def __init__(self, page, origin, text_width, scale=3.4, line_h=128, space=10.0, seed=7):
        self.page = page
        self.S = scale
        self.LH = line_h
        self.space = space
        self.ox, self.oy = origin
        self.tw = text_width
        self.t_in = page.get('t_in', 0.0)
        self.rng = np.random.default_rng(seed)
        self.plume = Plume(w0=scale * 1.3)
        self.words = []
        self._layout()
        self._schedule()

    # mise en page ---------------------------------------------------------------
    def _word_strokes(self, text, x, base, sc_w, rng):
        S = self.S * sc_w
        strokes = []
        shear = rng.normal(0.0, 0.05)
        wy = rng.normal(0, 0.8)
        for ch in text:
            st, adv = glyph(ch)
            sc = 1 + rng.normal(0, 0.045)
            rot = rng.normal(0, 0.035)
            dy = rng.normal(0, 0.7) + wy
            cr, sr = math.cos(rot), math.sin(rot)
            for s in st:
                pts = []
                for px, py in s:
                    px, py = px * sc, py * sc
                    px = px - shear * py
                    rx, ry = px * cr - py * sr, px * sr + py * cr
                    pts.append((x + S * rx, base + S * (ry + dy)))
                strokes.append(pts)
            x += S * sc * adv * 0.95 + S * rng.normal(0, 0.28)
        return strokes, x

    def _measure(self, text, sc):
        return sum(glyph(ch)[1] * 0.95 for ch in text) * self.S * sc

    def _layout(self):
        y = self.oy
        for li, line in enumerate(self.page['lines']):
            if line.get('blank'):
                y += self.LH * 0.55
                continue
            st = STYLES[line.get('style')]
            sc = st['scale']
            if line.get('style') == 'signature':
                y += self.LH * 0.9
            words = line['words']
            widths = [self._measure(w[0], sc) for w in words]
            sp = self.space * self.S * sc
            rows, cur, cw = [], [], 0.0
            for w, wd in zip(words, widths):
                need = wd if not cur else cw + sp + wd
                if cur and need > self.tw:
                    rows.append(cur)
                    cur, cw = [], 0.0
                    need = wd
                cur.append((w, wd))
                cw = need
            rows.append(cur)
            for ri, row in enumerate(rows):
                total = sum(wd for _, wd in row) + sp * (len(row) - 1)
                if st['align'] == 'center':
                    x = self.ox + (self.tw - total) / 2
                elif st['align'] == 'right':
                    x = self.ox + self.tw - total - 60
                else:
                    x = self.ox + self.rng.normal(0, 9) + (70 if ri > 0 else 0)
                slope = self.rng.normal(-0.008, 0.007)
                bow = self.rng.normal(0, 4)
                x_start = x
                for (w, wd) in row:
                    text, t0, t1 = w[0], w[1], w[2]
                    flags = w[3] if len(w) > 3 else {}
                    u = (x - x_start) / max(self.tw, 1)
                    base = y + slope * (x - x_start) + bow * math.sin(math.pi * u)
                    rng = np.random.default_rng(zlib.crc32(f"{self.page.get('name')}|{li}|{text}|{t0:.2f}".encode()))
                    sc_w = sc * (1 + rng.normal(0, 0.03))
                    sp_w = sp * (1 + abs(rng.normal(0, 0.15)))
                    strokes, x_end = self._word_strokes(text, x, base, sc_w, rng)
                    self.words.append(dict(text=text, t0=t0, t1=t1, flags=flags, strokes=strokes, x0=x, x1=x_end,
                                           base=base, style=line.get('style'), scale=sc_w, line=li))
                    x = x_end + sp_w
                y += self.LH * (sc if sc > 1 else 1)
        self.bottom = y

    # ordonnancement --------------------------------------------------------------
    def _emit(self, d, ts, wd, ink, segs, strokes_t):
        for i in range(len(d) - 1):
            segs.append((d[i, 0], d[i, 1], d[i + 1, 0], d[i + 1, 1], 0.5 * (wd[i] + wd[i + 1]), ts[i + 1], ink[i]))
        strokes_t.append((ts[0], ts[-1], d, ts))

    def _line_mark(self, x0, x1, y, t0, t1, rng, w0, wave=3.0, rise=-6.0, segs=None, strokes_t=None, back=False):
        n = max(20, int(abs(x1 - x0) / 2))
        u = np.linspace(0, 1, n)
        e = 0.82 * u + 0.18 * (3 * u ** 2 - 2 * u ** 3)
        xa, xb = (x1, x0) if back else (x0, x1)
        xs = xa + (xb - xa) * e
        ys = y + wave * np.sin(u * 5.0 + rng.uniform(0, 6)) * (0.4 + 0.6 * u) + rise * u
        d = tremble(np.c_[xs, ys], rng, 0.6)
        wd = np.full(n, w0) * (0.5 + 0.5 * np.minimum(1, np.minimum(np.arange(n) + 1, n - np.arange(n)) / 8.0))
        ts = t0 + (t1 - t0) * u
        self._emit(d, ts, wd, np.full(n, 0.95), segs, strokes_t)

    def _schedule(self):
        segs, strokes_t = [], []
        cursor = self.t_in + 0.05
        written = 0.0
        ink_level = 1.0
        rng = np.random.default_rng(5)
        pending = []      # marques à tracer après un mot : (après_mot, fonction)
        for wi, w in enumerate(self.words):
            heavy = 1.0 + 0.38 * float(w['flags'].get('heavy', 0.0))
            sc = w['scale']
            wrng = np.random.default_rng(wi * 7919 + 13)
            dense = [tremble(catmull_rom(s, 1.6), wrng, 0.55 * sc) for s in w['strokes']]
            lens = [float(np.sum(np.linalg.norm(np.diff(d, axis=0), axis=1))) if len(d) > 1 else 1.0 for d in dense]
            total = sum(lens)
            # la plume suit la voix ; dans le rap rapide elle accélère pour ne pas prendre de retard
            behind = cursor + 0.03 > w['t0'] - 0.03
            t_start = max(w['t0'] - 0.03, cursor + (0.012 if behind else 0.03))
            dur = max(w['t1'] - 0.01 - t_start, 0.045 + 0.005 * len(dense))
            lift = min(0.035, 0.2 * dur / max(1, len(dense)))
            draw_time = dur - lift * (len(dense) - 1)
            # la plume se recharge en début de mot quand l'encre s'épuise
            if ink_level < 0.74:
                ink_level = 1.0
                written = 0.0
            t = t_start
            for d, L in zip(dense, lens):
                td = draw_time * L / total
                n = len(d)
                if n > 1:
                    wd = self.plume.widths(d, heavy * sc ** 0.5, wrng)
                    u = np.linspace(0, 1, n)
                    ease = 0.80 * u + 0.20 * (3 * u ** 2 - 2 * u ** 3)
                    ts = t + td * ease
                    s = written + np.r_[0, np.cumsum(np.linalg.norm(np.diff(d, axis=0), axis=1))]
                    ink = 0.60 + 0.40 * np.exp(-s / 7000.0)
                    ink[:5] = np.minimum(1, ink[:5] + 0.18)          # dépôt au poser de la plume
                    ink[-3:] = np.minimum(1, ink[-3:] + 0.10)
                    if heavy > 1.05:
                        ink = np.maximum(ink, 0.95)
                    self._emit(d, ts, wd, ink, segs, strokes_t)
                    written = s[-1]
                    ink_level = ink[-1]
                t += td + lift
            w['t_write0'], w['t_write1'] = t_start, t - lift
            cursor = t - lift
            # rature : après le dernier mot du groupe
            key = w['flags'].get('strike')
            nxt = self.words[wi + 1] if wi + 1 < len(self.words) else None
            if key and not (nxt and nxt['flags'].get('strike') == key):
                grp = [x for x in self.words[:wi + 1] if x['flags'].get('strike') == key]
                t0 = cursor + 0.02
                t1 = t0 + 0.22
                self._line_mark(min(x['x0'] for x in grp) - 10, max(x['x1'] for x in grp) + 12,
                                grp[0]['base'] - 4.4 * self.S, t0, t1, rng, self.plume.w0 * 1.15,
                                wave=5, rise=-10, segs=segs, strokes_t=strokes_t, back=True)
                cursor = t1
            ul = w['flags'].get('underline')
            if ul:
                ln = [x for x in self.words if x['line'] == w['line']]
                t0 = cursor + 0.05
                t1 = t0 + 0.38
                self._line_mark(ln[0]['x0'] - 6, w['x1'] + 10, w['base'] + 2.4 * self.S, t0, t1, rng,
                                self.plume.w0 * 0.95, wave=3, rise=-4, segs=segs, strokes_t=strokes_t)
                cursor = t1
            if w['style'] == 'titre' and (nxt is None or nxt['line'] != w['line']):
                ln = [x for x in self.words if x['line'] == w['line']]
                y = w['base'] + 3.0 * self.S
                t0 = cursor + 0.04
                self._line_mark(ln[0]['x0'] - 20, w['x1'] + 20, y, t0, t0 + 0.16, rng, self.plume.w0,
                                wave=2, rise=-3, segs=segs, strokes_t=strokes_t)
                self._line_mark(ln[0]['x0'] + 10, w['x1'] - 5, y + 16, t0 + 0.2, t0 + 0.34, rng,
                                self.plume.w0 * 0.85, wave=2, rise=-2, segs=segs, strokes_t=strokes_t, back=True)
                cursor = t0 + 0.34
            if w['style'] == 'signature2':
                t0 = cursor + 0.05
                self._line_mark(w['x0'] - 30, w['x1'] + 60, w['base'] + 3.5 * self.S, t0, t0 + 0.6, rng,
                                self.plume.w0 * 1.1, wave=9, rise=-14, segs=segs, strokes_t=strokes_t)
                cursor = t0 + 0.6
        strokes_t.sort(key=lambda s: s[0])
        segs.sort(key=lambda s: s[5])
        self.segs = np.array(segs, dtype=np.float64).reshape(-1, 7)
        self.strokes_t = strokes_t
        self._stroke_starts = np.array([s[0] for s in strokes_t])
        self.t_end = strokes_t[-1][1] if strokes_t else self.t_in

    def anchors(self):
        """Mots marqués {ev=nom} : instants d'écriture et position."""
        out = {}
        for w in self.words:
            ev = w['flags'].get('ev')
            if ev:
                out[ev] = w
        return out

    # trajectoire de la plume -------------------------------------------------------
    def pen(self, t, leave_after=None):
        """Position (x, y) de la pointe et levée (0 = sur le papier, 1 = levée)."""
        st = self.strokes_t
        if not st:
            return self.ox + 200, self.oy, 1.0
        i = int(np.searchsorted(self._stroke_starts, t, side='right')) - 1
        if i >= 0:
            t0, t1, d, ts = st[i]
            if t <= t1:
                k = int(np.searchsorted(ts, t))
                k = min(max(k, 0), len(d) - 1)
                return d[k, 0], d[k, 1], 0.0
        if i < 0:
            p1 = st[0][2][0]
            rem = st[0][0] - t
            u = min(1.0, rem / 0.5)
            return p1[0] + 70 * u, p1[1] - 55 * u, u
        prev = st[i]
        p0 = prev[2][-1]
        if i + 1 >= len(st):
            el = t - prev[1]
            if leave_after is not None and t > leave_after:
                # la plume quitte le cadre
                u = min(1.0, (t - leave_after) / 1.4)
                s = u * u * (3 - 2 * u)
                return p0[0] + 70 + 1600 * s, p0[1] - 55 - 1300 * s, 1.0
            u = min(1, el / 0.4)
            b = 3.0 * math.sin(t * 1.7) * u
            return p0[0] + 70 * u + b, p0[1] - 55 * u + 0.6 * b, u
        nxt = st[i + 1]
        p1 = nxt[2][0]
        gap = nxt[0] - prev[1]
        el = t - prev[1]
        if gap <= 0.7:
            u = el / max(gap, 1e-6)
            s = u * u * (3 - 2 * u)
            h = math.sin(math.pi * u) * min(1.0, gap / 0.35) * 0.55
            return p0[0] + (p1[0] - p0[0]) * s, p0[1] + (p1[1] - p0[1]) * s, h
        rest = (p0[0] + 70, p0[1] - 55)
        if el < 0.4:
            u = el / 0.4
            s = u * u * (3 - 2 * u)
            return p0[0] + (rest[0] - p0[0]) * s, p0[1] + (rest[1] - p0[1]) * s, s
        rem = nxt[0] - t
        if rem < 0.4:
            u = 1 - rem / 0.4
            s = u * u * (3 - 2 * u)
            return rest[0] + (p1[0] - rest[0]) * s, rest[1] + (p1[1] - rest[1]) * s, 1 - s
        b = 3.0 * math.sin(t * 1.7)
        return rest[0] + b, rest[1] + 0.6 * b, 1.0
