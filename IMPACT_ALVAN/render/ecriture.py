"""Écriture manuscrite : tracés réels (police à trait unique Hershey « cursive »),
mise en page sur la feuille et ordonnancement temporel trait par trait."""
import json
import math

import numpy as np
import HersheyFonts

# --- Glyphes -----------------------------------------------------------------

_H = HersheyFonts.HersheyFonts()
_H.load_default_font('cursive')
_CACHE = {}

# accents composés : (lettre de base, accent)
_COMPOSE = {
    'é': ('e', 'aigu'), 'è': ('e', 'grave'), 'ê': ('e', 'circ'), 'ë': ('e', 'trema'),
    'à': ('a', 'grave'), 'â': ('a', 'circ'), 'ù': ('u', 'grave'), 'û': ('u', 'circ'),
    'î': ('i', 'circ'), 'ï': ('i', 'trema'), 'ô': ('o', 'circ'), 'ç': ('c', 'cedille'),
    'É': ('E', 'aigu'), 'È': ('E', 'grave'), 'À': ('A', 'grave'), 'Ç': ('C', 'cedille'),
}
_SUBST = {'’': "'", '‘': "'", '«': '"', '»': '"', '…': '.'}


def _accent(kind, cx, capital):
    top = -23.0 if capital else -11.0   # au-dessus de la hauteur d'x (-9) ou des capitales (-21)
    if kind == 'aigu':
        return [[(cx - 1.5, top), (cx + 2.8, top - 4.5)]]
    if kind == 'grave':
        return [[(cx - 2.2, top - 4.5), (cx + 1.6, top)]]
    if kind == 'circ':
        return [[(cx - 3.0, top), (cx + 0.2, top - 3.8), (cx + 3.2, top)]]
    if kind == 'trema':
        return [[(cx - 2.6, top - 1.0), (cx - 2.2, top - 1.6)], [(cx + 2.4, top - 1.0), (cx + 2.8, top - 1.6)]]
    if kind == 'cedille':
        return [[(cx + 0.3, 0.0), (cx + 0.8, 2.2), (cx + 2.8, 3.4), (cx + 1.8, 5.8), (cx - 1.6, 6.2)]]
    return []


def glyph(ch):
    """Traits du caractère en unités Hershey locales : x depuis le bord gauche,
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
    if acc:
        if base in 'ij':      # on retire le point du i
            strokes = [s for s in strokes if (max(p[1] for p in s) - min(p[1] for p in s)) > 2.5]
        (x0, _), (x1, _) = g.draw_box
        cx = (x0 + x1) / 2 - lo + (1.0 if base.islower() else 2.5)
        strokes += _accent(acc, cx, base.isupper())
    _CACHE[ch] = (strokes, float(g.char_width))
    return _CACHE[ch]


# --- Géométrie ----------------------------------------------------------------

def catmull_rom(pts, step):
    """Lissage centripète d'un trait Hershey (polyligne grossière) puis
    rééchantillonnage à pas constant (en px)."""
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


class Plume:
    """Modèle de plume : épaisseur selon la direction (pleins descendants,
    déliés montants) et l'angle du bec."""

    def __init__(self, w0, nib_deg=38.0):
        self.w0 = w0
        self.nib = math.radians(nib_deg)

    def widths(self, p, heavy=1.0):
        d = np.gradient(p, axis=0)
        ln = np.linalg.norm(d, axis=1) + 1e-9
        down = np.clip(d[:, 1] / ln, 0, 1)                  # y vers le bas = plein
        theta = np.arctan2(d[:, 1], d[:, 0])
        nib = np.abs(np.sin(theta - self.nib))
        w = self.w0 * (0.42 + 0.62 * down ** 1.3) * (0.78 + 0.32 * nib) * heavy
        k = np.ones(9) / 9
        if len(w) > 9:
            w = np.convolve(np.pad(w, 4, mode='edge'), k, mode='valid')
        n = len(w)
        ramp = np.minimum(1, np.minimum(np.arange(n) + 1, n - np.arange(n)) / 6.0)
        return w * (0.55 + 0.45 * ramp)


# --- Mise en page et ordonnancement --------------------------------------------

class Lettre:
    """Construit, à partir d'un fichier de minutage, la liste de tous les
    segments d'encre (x0, y0, x1, y1, largeur, instant) et la trajectoire de la plume."""

    def __init__(self, timing_path, origin, text_width, scale=3.4, line_h=128,
                 space=8.0, seed=7):
        with open(timing_path, encoding='utf-8') as f:
            self.data = json.load(f)
        self.S = scale
        self.LH = line_h
        self.space = space
        self.ox, self.oy = origin
        self.tw = text_width
        self.rng = np.random.default_rng(seed)
        self.plume = Plume(w0=scale * 1.25)
        self.words = []       # mots posés : dict(text, t0, t1, flags, strokes, bbox, baseline)
        self._layout()
        self._schedule()

    # mise en page ---------------------------------------------------------------
    def _word_strokes(self, text, x, base, gseed):
        S = self.S
        rng = np.random.default_rng(gseed)
        strokes = []
        for ch in text:
            st, adv = glyph(ch)
            sc = 1 + rng.normal(0, 0.022)
            dy = rng.normal(0, 0.45)
            for s in st:
                pts = [(x + S * sc * px, base + S * (sc * py + dy) + 1.2 * math.sin((x + S * px) / 260.0)) for px, py in s]
                strokes.append(pts)
            x += S * sc * adv * 0.96
        return strokes, x

    def _measure(self, text):
        return sum(glyph(ch)[1] * 0.96 for ch in text) * self.S

    def _layout(self):
        y = self.oy
        for li, line in enumerate(self.data['lines']):
            if line.get('blank'):
                y += self.LH * 0.55
                continue
            words = line['words']
            widths = [self._measure(w[0]) for w in words]
            sp = self.space * self.S
            # découpage en lignes visuelles si la ligne dépasse la largeur utile
            rows, cur, cw = [], [], 0.0
            for w, wd in zip(words, widths):
                need = wd if not cur else cw + sp + wd
                if cur and need > self.tw:
                    rows.append(cur); cur, cw = [], 0.0
                    need = wd
                cur.append((w, wd)); cw = need
            rows.append(cur)
            for row in rows:
                total = sum(wd for _, wd in row) + sp * (len(row) - 1)
                if line.get('style') == 'header':
                    x = self.ox + (self.tw - total) / 2
                else:
                    x = self.ox + self.rng.normal(0, 6) + (40 if li % 3 == 1 else 0) * 0
                slope = self.rng.normal(0, 0.004)
                x_start = x
                for (w, wd) in row:
                    text, t0, t1 = w[0], w[1], w[2]
                    flags = w[3] if len(w) > 3 else {}
                    base = y + slope * (x - x_start)
                    strokes, x_end = self._word_strokes(text, x, base, hash((li, text, round(t0, 2))) & 0xffffffff)
                    self.words.append(dict(text=text, t0=t0, t1=t1, flags=flags, strokes=strokes,
                                           x0=x, x1=x_end, base=base, style=line.get('style')))
                    x = x_end + sp
                y += self.LH

    # ordonnancement --------------------------------------------------------------
    def _schedule(self):
        """Chaque mot est écrit pendant qu'il est chanté. La vitesse de la plume
        suit la longueur des traits ; entre deux traits, la plume se lève."""
        segs = []          # x0 y0 x1 y1 w t
        strokes_t = []     # (t_start, t_end, pts) pour la trajectoire de la plume
        cursor = -1.0
        lift = 0.035
        for w in self.words:
            heavy = 1.0 + 0.38 * float(w['flags'].get('heavy', 0.0))
            dense = [catmull_rom(s, 1.6) for s in w['strokes']]
            lens = [float(np.sum(np.linalg.norm(np.diff(d, axis=0), axis=1))) if len(d) > 1 else 1.0 for d in dense]
            total = sum(lens)
            # la plume suit la voix : le mot s'écrit pendant qu'il est chanté
            t_start = max(w['t0'] - 0.03, cursor + 0.03)
            dur = max(w['t1'] - 0.01 - t_start, 0.09 + 0.012 * len(dense))
            lift = min(0.035, 0.25 * dur / max(1, len(dense)))
            draw_time = dur - lift * (len(dense) - 1)
            t = t_start
            for d, L in zip(dense, lens):
                td = draw_time * L / total
                n = len(d)
                if n > 1:
                    wd = self.plume.widths(d, heavy)
                    u = np.linspace(0, 1, n)
                    ease = 0.82 * u + 0.18 * (3 * u ** 2 - 2 * u ** 3)
                    ts = t + td * ease
                    for i in range(n - 1):
                        segs.append((d[i, 0], d[i, 1], d[i + 1, 0], d[i + 1, 1],
                                     0.5 * (wd[i] + wd[i + 1]), ts[i + 1]))
                    strokes_t.append((t, t + td, d, ts))
                t += td + lift
            w['t_write0'], w['t_write1'] = t_start, t - lift
            cursor = t - lift
        # rature « Christian Dior »
        for key, st in self.data.get('strikes', {}).items():
            ws = [w for w in self.words if w['flags'].get('strike') == key]
            if not ws:
                continue
            x0 = min(w['x0'] for w in ws) - 10
            x1 = max(w['x1'] for w in ws) + 12
            yb = ws[0]['base'] - 4.6 * self.S
            n = 160
            u = np.linspace(0, 1, n)
            xs = x1 + (x0 - x1) * (0.85 * u + 0.15 * (3 * u ** 2 - 2 * u ** 3))
            ys = yb + 6 * np.sin(u * 5.3 + 0.7) * (0.4 + 0.6 * u) - 10 * u
            d = np.c_[xs, ys]
            wd = np.full(n, self.plume.w0 * 1.15)
            wd *= np.minimum(1, np.minimum(np.arange(n) + 1, n - np.arange(n)) / 8.0) * 0.5 + 0.5
            ts = st['t0'] + (st['t1'] - st['t0']) * u
            for i in range(n - 1):
                segs.append((d[i, 0], d[i, 1], d[i + 1, 0], d[i + 1, 1], 0.5 * (wd[i] + wd[i + 1]), ts[i + 1]))
            strokes_t.append((st['t0'], st['t1'], d, ts))
        strokes_t.sort(key=lambda s: s[0])
        self.segs = np.array(sorted(segs, key=lambda s: s[5]), dtype=np.float64)
        self.strokes_t = strokes_t
        self._stroke_starts = np.array([s[0] for s in strokes_t])

    def word(self, text_pred):
        return [w for w in self.words if text_pred(w)]

    # trajectoire de la plume -------------------------------------------------------
    def pen(self, t):
        """Position (x, y) de la pointe et levée (0 = sur le papier, 1 = levée haute)."""
        st = self.strokes_t
        i = int(np.searchsorted(self._stroke_starts, t, side='right')) - 1
        if i >= 0:
            t0, t1, d, ts = st[i]
            if t <= t1:
                k = int(np.searchsorted(ts, t))
                k = min(max(k, 0), len(d) - 1)
                return d[k, 0], d[k, 1], 0.0
        # en l'air entre le trait i et le trait i+1
        if i < 0:
            nxt = st[0]
            p1 = nxt[2][0]
            return p1[0] + 40, p1[1] - 40, 1.0
        prev = st[i]
        p0 = prev[2][-1]
        if i + 1 >= len(st):
            el = t - prev[1]
            u = min(1, el / 0.5)
            return p0[0] + 50 * u, p0[1] - 40 * u, u
        nxt = st[i + 1]
        p1 = nxt[2][0]
        gap = nxt[0] - prev[1]
        el = t - prev[1]
        if gap <= 0.7:
            u = el / max(gap, 1e-6)
            s = u * u * (3 - 2 * u)
            h = math.sin(math.pi * u) * min(1.0, gap / 0.35) * 0.55
            return p0[0] + (p1[0] - p0[0]) * s, p0[1] + (p1[1] - p0[1]) * s, h
        # longue pause : la plume se lève, se repose en l'air, puis rejoint le trait suivant
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
