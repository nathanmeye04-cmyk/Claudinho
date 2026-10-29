"""Direction : feuilles, ancrages temporels des effets, caméra, lumière et
effets visuels liés au sens des paroles (voir STORYBOARD_lettre_manuscrite.md)."""
import json
import math

import cairo
import cv2
import numpy as np

import scene as S
from ecriture import Lettre

W, H, FPS = S.W, S.H, S.FPS
sm = S.sm

CANDLE_L = np.array([180.0, 760.0])
CANDLE_R = np.array([3420.0, 900.0])
WARM = np.array([1.0, 0.80, 0.56], np.float32)
TRANS = {'intro': 0.0, 'glisse': 0.6, 'glisse_vite': 0.38, 'retourne': 0.5}
ZOOMS = [0.86, 0.93, 0.87, 0.86, 0.84, 0.92, 0.86, 0.88, 0.90, 0.86]


def env(t, a, b, fin=0.3, fout=0.3):
    """Enveloppe : monte de a à a+fin, tient, descend jusqu'à b."""
    if t < a or t > b:
        return 0.0
    return min(sm((t - a) / max(fin, 1e-6)), sm((b - t) / max(fout, 1e-6)))


class Direction:
    def __init__(self, partition_path):
        with open(partition_path, encoding='utf-8') as f:
            self.data = json.load(f)
        self.pages = []
        for i, pg in enumerate(self.data['pages']):
            L = Lettre(pg, origin=S.TEXT_ORIGIN, text_width=S.TEXT_WIDTH, seed=11 + i)
            self.pages.append(L)
        self.t_ins = np.array([p['t_in'] for p in self.data['pages']])
        # ancrages {ev=…}
        self.a = {}
        self.drops, self.hits = [], []
        for pi, L in enumerate(self.pages):
            for w in L.words:
                ev = w['flags'].get('ev')
                if ev:
                    self.a[ev] = dict(w, page=pi)
                if w['flags'].get('drop'):
                    self.drops.append(dict(w=w, page=pi, kind=w['flags']['drop'], t=w['t_write1'] + 0.04))
                if w['flags'].get('hit'):
                    self.hits.append((w['t0'], float(w['flags']['hit'])))
        self.leave_after = self.pages[-1].t_end + 0.8
        self.silence = (16.2, 19.06)
        self._prep_drops()
        self._prep_drips()
        rng = np.random.default_rng(21)
        self.noise_tex = cv2.GaussianBlur(rng.standard_normal((540, 960)).astype(np.float32), (0, 0), 6)
        self.noise_tex /= self.noise_tex.std()
        gy, gx = np.mgrid[0:H // 8, 0:W // 8].astype(np.float64)
        self.grid = np.stack([gx.ravel() * 8 + 4, gy.ravel() * 8 + 4, np.ones(gx.size)])
        self.gxy = (gx, gy)

    # --- feuilles ---------------------------------------------------------------
    def page_at(self, t):
        return max(0, int(np.searchsorted(self.t_ins, t, side='right')) - 1)

    def transition(self, t):
        """(type, avancement 0..1, feuille précédente) ou None."""
        pi = self.page_at(t)
        pg = self.data['pages'][pi]
        d = TRANS.get(pg.get('enter'), 0)
        if pi > 0 and d > 0 and t < pg['t_in'] + d:
            return pg['enter'], (t - pg['t_in']) / d, pi - 1
        return None

    def candle(self, pi):
        return CANDLE_L if pi < 3 else CANDLE_R

    def pen(self, t):
        pi = self.page_at(t)
        L = self.pages[pi]
        x, y, lift = L.pen(t, self.leave_after if pi == len(self.pages) - 1 else None)
        tr = self.transition(t)
        if tr:
            lift = 1.0
        return x, y, lift

    def pen_angle(self, t):
        pi = self.page_at(t)
        base = self.data['pages'][pi].get('pen', -40)
        return math.radians(base + 4 * math.sin(t * 0.9) + 2.5 * math.sin(t * 2.3))

    # --- caméra ------------------------------------------------------------------
    def zoom_target(self, t, pi):
        z = ZOOMS[pi % len(ZOOMS)]
        if t < 8.5:
            z = 0.50 + (z - 0.50) * sm((t - 0.4) / 7.4)
        s0, s1 = self.silence
        if s0 <= t < s1:
            z += 0.05 * sm((t - s0) / (s1 - s0))
        lo, de = self.a.get('loin'), self.a.get('dedans')
        if lo and de:
            t0, t1 = lo['t0'] - 0.25, de['t1']
            if t0 <= t < t0 + 0.45:
                z = z + (0.50 - z) * sm((t - t0) / 0.45)
            elif t0 + 0.45 <= t < t1:
                z = 0.50 + (1.0 - 0.50) * sm((t - t0 - 0.45) / (t1 - t0 - 0.45))
            elif t1 <= t < t1 + 1.4:
                z = 1.0 + (z - 1.0) * sm((t - t1) / 1.4)
        sg = self.a.get('signe')
        if sg and t > sg['t_write1'] + 0.6:
            z = z + (0.40 - z) * sm((t - sg['t_write1'] - 0.6) / 8.0)
        return z

    def camera_track(self, t_end):
        n = int(round(t_end * FPS)) + 2
        out = np.zeros((n, 4))
        cx0 = S.TEXT_ORIGIN[0] + S.TEXT_WIDTH / 2
        pos = np.array([cx0, S.PAPER[1] + 1500.0])
        vel = np.zeros(2)
        zoom, zvel = 0.50, 0.0
        rot = math.radians(self.data['pages'][0].get('tilt', 0))
        sub = 4
        dt = 1.0 / FPS / sub
        sg = self.a.get('signe')
        for i in range(n):
            t = i / FPS
            for _ in range(sub):
                pi = self.page_at(t)
                px, py, lift = self.pen(t)
                follow = 0.2
                target = np.array([cx0 + follow * (px - cx0), py - 0.06 * H / zoom])
                if sg and t > sg['t_write1'] + 0.6:        # recul final : on voit toute la feuille
                    k = sm((t - sg['t_write1'] - 0.6) / 8.0)
                    target = target * (1 - k) + S.PAPER_C * k
                omega = 2.0
                acc = omega * omega * (target - pos) - 2 * omega * vel
                vel += acc * dt
                pos += vel * dt
                zt = self.zoom_target(t, pi)
                zo = 3.2 if (self.a.get('loin') and abs(t - self.a['loin']['t0']) < 3.5) else 1.6
                za = zo * zo * (zt - zoom) - 2 * zo * zvel
                zvel += za * dt
                zoom += zvel * dt
                rt = math.radians(self.data['pages'][pi].get('tilt', 0))
                rot += (rt - rot) * min(1, dt * 1.6)
            out[i] = (pos[0] + 6 * math.sin(t * 0.37), pos[1] + 5 * math.sin(t * 0.29 + 1),
                      zoom * (1 + 0.004 * math.sin(t * 0.5)), rot + math.radians(0.25) * math.sin(t * 0.21))
        return out

    def shake(self, t):
        dx = dy = dr = 0.0
        for th, a in self.hits:
            u = t - th
            if 0 <= u < 0.6:
                e = a * math.exp(-u / 0.09)
                dx += 9 * e * math.sin(2 * math.pi * 17 * u)
                dy += 6 * e * math.sin(2 * math.pi * 13 * u + 1)
                dr += math.radians(0.22) * e * math.sin(2 * math.pi * 11 * u)
        return dx, dy, dr

    def matrix(self, cam, t):
        dx, dy, dr = self.shake(t)
        return S.affine(cam[0], cam[1], cam[2], cam[3] + dr, dx, dy)

    # --- gouttes et coulures (dessinées dans l'encre de la feuille) --------------------
    def _prep_drops(self):
        rng = np.random.default_rng(11)
        for d in self.drops:
            w = d['w']
            c = np.array([w['x1'] + 70.0, w['base'] - 26.0])
            ang = np.linspace(0, 2 * math.pi, 90, endpoint=False)
            d.update(c=c, ang=ang,
                     rad=1 + 0.10 * np.sin(3 * ang + rng.uniform(0, 6)) + 0.07 * np.sin(5 * ang + 2) + 0.05 * np.sin(9 * ang),
                     sats=[(c + rng.normal(0, 1, 2) * 9 + np.array([26, 6]), rng.uniform(1.5, 3.0)) for _ in range(2)])
            if d['kind'] == 'villes':
                pts = []
                for _ in range(38):
                    ca = rng.uniform(0, 2 * math.pi)
                    cr = 140 + 900 * math.sqrt(rng.uniform())
                    cc = c + cr * np.array([math.cos(ca), math.sin(ca)])
                    for _ in range(rng.integers(6, 30)):
                        pts.append(cc + rng.normal(0, 1, 2) * rng.uniform(10, 45))
                pts = np.array(pts)
                d.update(pts=pts, pd=np.linalg.norm(pts - c, axis=1), pb=rng.uniform(0.4, 1, len(pts)))

    def _prep_drips(self):
        self.drips = []
        a = self.a.get('enfonce')
        if not a:
            return
        rng = np.random.default_rng(4)
        for k in range(6):
            x = a['x0'] + (a['x1'] - a['x0']) * (0.08 + 0.84 * k / 5) + rng.normal(0, 8)
            self.drips.append(dict(page=a['page'], x=x, y=a['base'] + 4, L=rng.uniform(50, 150),
                                   w=rng.uniform(3.0, 5.5), t=a['t_write1'] + rng.uniform(0.0, 0.35),
                                   ph=rng.uniform(0, 6)))

    def draw_marks(self, pi, ctx, t):
        """Gouttes et coulures de la feuille pi jusqu'à l'instant t (croissance monotone)."""
        for d in self.drops:
            if d['page'] != pi or t < d['t']:
                continue
            u = t - d['t']
            R = 19 * (1 - math.exp(-u / 0.10))
            c = d['c']
            ctx.new_path()
            for a, r in zip(d['ang'], d['rad']):
                ctx.line_to(c[0] + R * r * math.cos(a), c[1] + R * r * math.sin(a))
            ctx.close_path()
            ctx.fill()
            if u > 0.05:
                for p, rr in d['sats']:
                    ctx.arc(p[0], p[1], rr * min(1, (u - 0.05) / 0.1), 0, 2 * math.pi)
                    ctx.fill()
        for d in self.drips:
            if d['page'] != pi or t < d['t']:
                continue
            u = min(1.0, (t - d['t']) / 1.5)
            L = d['L'] * (1 - (1 - u) ** 2.2)
            n = max(2, int(L / 2))
            ys = d['y'] + np.linspace(0, L, n)
            xs = d['x'] + 2.5 * np.sin(np.linspace(0, L, n) / 23 + d['ph'])
            for i in range(n - 1):
                ctx.set_line_width(d['w'] * (1 - 0.35 * i / n))
                ctx.move_to(xs[i], ys[i])
                ctx.line_to(xs[i + 1], ys[i + 1])
                ctx.stroke()
            ctx.arc(xs[-1], ys[-1], d['w'] * 0.75, 0, 2 * math.pi)
            ctx.fill()

    # --- lumière -------------------------------------------------------------------
    def light_state(self, t):
        """Gain de la bougie, ambiance, reflets de ville, aube."""
        pi = self.page_at(t)
        names = [p.get('light', 'bougie') for p in self.data['pages']]

        def st(name):
            return {'bougie': (1.55, np.array([0.075, 0.085, 0.115]), 0.0),
                    'ville': (1.35, np.array([0.085, 0.105, 0.155]), 1.0),
                    'aube': (1.45, np.array([0.085, 0.105, 0.155]), 0.4)}[name]
        g, amb, win = st(names[pi])
        if pi > 0 and names[pi] != names[pi - 1]:
            k = sm((t - self.t_ins[pi]) / 1.5)
            g0, a0, w0 = st(names[pi - 1])
            g, amb, win = g0 + (g - g0) * k, a0 + (amb - a0) * k, w0 + (win - w0) * k
        dawn = sm((t - 162.6) / 28.0)
        win *= 1 - dawn
        return g, amb, win, dawn

    def flicker(self, t):
        f = 1 + 0.045 * math.sin(2 * math.pi * 1.3 * t) + 0.03 * math.sin(2 * math.pi * 3.7 * t + 1) \
            + 0.02 * math.sin(2 * math.pi * 7.9 * t + 2)
        s0, s1 = self.silence
        if s0 <= t < s1:
            k = sm((t - s0) / 0.6) * sm((s1 - t) / 0.4)
            f = 1 + (f - 1) * (1 + 1.6 * k) - 0.10 * k
        for name in ('dort', 'dort2'):
            d = self.a.get(name)
            if d:
                t0, low, t1 = d['t0'] - 2.3, d['t0'], d['t1'] + 1.6
                if t0 <= t < t1:
                    e = sm((t - t0) / (low - t0)) if t < low else (1.0 if t < low + 0.5 else
                                                                   1 - sm((t - low - 0.5) / (t1 - low - 0.5)))
                    f *= 1 - 0.5 * e
        for th, a in self.hits:
            u = t - th
            if 0 <= u < 0.8:
                f *= 1 + 0.10 * a * math.exp(-u / 0.14)
        u = t - self.silence[1]
        if 0 <= u < 1.2:
            f *= 1 + 0.08 * math.exp(-u / 0.3)
        pr = self.a.get('preche')
        if pr:
            f *= 1 + 0.30 * env(t, pr['t0'], pr['t0'] + 1.2, 0.08, 0.8)
        es = self.a.get('esprit')
        if es:
            e = env(t, es['t0'] - 0.1, es['t1'] + 1.6, 0.25, 1.0)
            f *= 1 + e * (0.35 + 0.12 * math.sin(t * 41) + 0.08 * math.sin(t * 23))
        if t < 6:
            f *= 0.25 + 0.75 * sm((t - 0.3) / 4.5)
        sg = self.a.get('signe')
        if sg:
            t_off = sg['t_write1'] + 5.0          # la bougie s'éteint
            if t > t_off:
                f *= max(0.0, 1 - (t - t_off) / 0.7) * (1 + 0.3 * math.sin(t * 50))
        return f

    def lighting(self, t, M, tip):
        """Carte d'éclairage basse résolution (bougie, ville, aube, ombres), RGB plein format."""
        Minv = np.linalg.inv(np.vstack([M, [0, 0, 1]]))
        wp = (Minv @ self.grid).T[:, :2]
        gh, gw = H // 8, W // 8
        pi = self.page_at(t)
        g, amb, win, dawn = self.light_state(t)
        cand = self.candle(pi)
        tr = self.transition(t)
        if tr and tr[0] == 'retourne':                # la bougie change de côté avec la feuille
            k = sm(tr[1])
            cand = self.candle(tr[2]) * (1 - k) + cand * k
        d = np.linalg.norm(wp - cand, axis=1)
        f = 1.0 / (1 + (d / 1750.0) ** 2) ** 1.25
        I = self.flicker(t) * g * (1 - 0.45 * dawn)
        L = (amb * (1 + 1.6 * dawn))[None] + (I * f)[:, None] * WARM[None]
        L = L.reshape(gh, gw, 3)
        wx, wy = wp[:, 0].reshape(gh, gw), wp[:, 1].reshape(gh, gw)
        # reflets de la ville à travers une fenêtre
        if win > 0.01:
            refl = np.zeros((gh, gw))
            for k, (x0, y0, ww, hh, sp) in enumerate(((900, 600, 520, 900, 14), (1600, 1300, 380, 700, -9),
                                                      (2300, 400, 600, 1100, 11))):
                cx = x0 + sp * t + 120 * math.sin(t * 0.13 + k)
                cy = y0 + 0.4 * sp * t
                bx = np.exp(-(np.maximum(0, np.abs(wx - cx) - ww / 2) / 120) ** 2)
                by = np.exp(-(np.maximum(0, np.abs(wy - cy - (wx - cx) * 0.25) - hh / 2) / 160) ** 2)
                refl += bx * by * (0.55 + 0.45 * math.sin(t * 0.7 + k * 2))
            ph = (t % 7.3) / 1.4                     # phares qui balaient la pièce
            if ph < 1:
                s = (wx + 0.6 * wy) - (-800 + 5200 * ph)
                refl += 1.4 * np.exp(-(s / 380) ** 2) * math.sin(math.pi * ph)
            L += (0.17 * win * refl)[..., None] * np.array([0.45, 0.62, 1.0])
        # aube : grande lumière dorée venant du haut à droite
        if dawn > 0.01:
            gdir = np.clip(0.45 + 0.35 * (wx - 600) / 2400 + 0.4 * (1 - (wy - 500) / 3400), 0, 1.2)
            L += (dawn * 1.05 * gdir)[..., None] * np.array([1.0, 0.84, 0.62])
        # « la gloire de Dieu » : un rai chaud traverse la feuille
        gl = self.a.get('gloire')
        if gl:
            g0, g1 = gl['t_write0'] - 0.4, gl['t_write0'] + 3.0
            if g0 <= t < g1:
                u = (t - g0) / (g1 - g0)
                s = (wx + 0.45 * wy) - (200 + 3900 * u)
                L += (0.42 * np.exp(-(s / 330.0) ** 2) * math.sin(math.pi * u) ** 1.2)[..., None] * np.array([1.0, 0.86, 0.6])
        # prière : lumière douce qui tombe d'en haut
        p0, p1 = self.a.get('priere'), self.a.get('priere_fin')
        if p0 and p1:
            e = env(t, p0['t0'] - 0.1, p1['t1'] + 1.0, 0.6, 1.0)
            if e > 0:
                cx = p0['x0'] + 700
                shaft = np.exp(-((wx - cx + 0.3 * (wy - 700)) / 520) ** 2) * np.clip(1.2 - (wy - 500) / 2600, 0, 1)
                L += (0.45 * e * shaft)[..., None] * np.array([1.0, 0.95, 0.85])
        # « enfoncé » : le cadre se referme dans l'ombre
        ef = self.a.get('enfonce')
        if ef and p0:
            e = env(t, ef['t0'] - 0.2, p0['t0'] + 0.6, 0.4, 0.6)
            if e > 0:
                gx, gy = self.gxy
                r = np.sqrt(((gx - gw / 2) / (gw / 2)) ** 2 + ((gy - gh / 2) / (gh / 2)) ** 2)
                L *= (1 - 0.55 * e * np.clip(r, 0, 1.4) ** 1.6)[..., None]
        # ombre qui passe derrière l'écrivain (« le diable travaille… »)
        for name in ('dort', 'dort2'):
            dv = self.a.get(name)
            if not dv:
                continue
            q0, q1 = dv['t0'] - 2.2, dv['t0'] + 1.2
            if q0 <= t < q1:
                u = (t - q0) / (q1 - q0)
                xs = gw * (1.25 - 1.6 * sm(u))
                gx, gy = self.gxy
                sil = ((gx - xs) / 19.0) ** 2 + ((gy - 42) / 21.0) ** 2 < 1
                sil |= ((gx - xs) / 58.0) ** 2 + ((gy - 120) / 50.0) ** 2 < 1
                m = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 9)
                L *= (1 - 0.62 * math.sin(math.pi * u) ** 0.6 * m)[..., None]
        # onde d'impact de la goutte « villes »
        for dr in self.drops:
            if dr['kind'] == 'villes' and 0 <= t - dr['t'] < 2.0:
                u = (t - dr['t']) / 1.8
                r = 1500 * (1 - (1 - min(u, 1)) ** 2.2)
                dd = np.hypot(wx - dr['c'][0], wy - dr['c'][1])
                ring = np.exp(-((dd - r) / 70.0) ** 2) * 0.13 * (1 - min(u, 1)) ** 1.5
                L += ring[..., None] * np.array([1.0, 0.84, 0.55])
        # « Impacter » : brève onde autour de la plume
        for th, a in self.hits:
            u = t - th
            if 0 <= u < 0.5:
                tw = (Minv @ np.array([tip[0], tip[1], 1.0]))[:2]
                dd = np.hypot(wx - tw[0], wy - tw[1])
                r = 900 * (u / 0.5) ** 0.6
                ring = np.exp(-((dd - r) / 60.0) ** 2) * 0.12 * a * (1 - u / 0.5)
                L *= (1 - ring)[..., None]
        # démons : ombres qui rôdent sur les bords, puis reculent
        de, pr, fu = self.a.get('demons'), self.a.get('preche'), self.a.get('fuient_fin')
        if de and pr and fu and de['t0'] - 0.4 <= t < fu['t1'] + 0.8:
            e = env(t, de['t0'] - 0.4, fu['t1'] + 0.8, 0.9, 0.8)
            ret = sm((t - pr['t0']) / (fu['t1'] - pr['t0']))
            gx, gy = self.gxy
            dist = np.minimum.reduce([gx, gw - 1 - gx, gy, gh - 1 - gy]).astype(np.float32)
            n1 = cv2.resize(self.noise_tex, (gw, gh))
            ox = int(t * 9) % gw
            n2 = np.roll(n1, ox, axis=1) * 0.6 + np.roll(n1, -int(t * 5) % gh, axis=0) * 0.6
            reach = 34 * (1 - ret) - 10 * ret
            m = np.clip((reach - dist + 9 * n2) / 14.0, 0, 1)
            m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.5)
            L *= (1 - 0.62 * e * m)[..., None]
        return cv2.resize(L.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)

    # --- surimpressions plein format --------------------------------------------------
    def city_lights(self, t, M):
        lay = None
        for dr in self.drops:
            if dr['kind'] != 'villes' or not (0 <= t - dr['t'] < 3.0):
                continue
            el = t - dr['t']
            r = 1500 * (1 - (1 - min(el / 1.8, 1)) ** 2.2)
            on = dr['pd'] < r
            if not on.any():
                continue
            tin = 1.8 * (1 - (1 - np.clip(dr['pd'][on] / 1500, 0, 1)) ** (1 / 2.2))
            age = el - tin
            a = dr['pb'][on] * np.clip(age / 0.15, 0, 1) * np.exp(-np.clip(age, 0, None) / 0.55) * 0.75
            sp = (M[:, :2] @ dr['pts'][on].T).T + M[:, 2]
            if lay is None:
                lay = np.zeros((H, W), np.float32)
            for (x, y), aa in zip(sp, a):
                if 0 <= x < W and 0 <= y < H and aa > 0.02:
                    cv2.circle(lay, (int(x), int(y)), 2, float(aa), -1, cv2.LINE_AA)
        if lay is None:
            return None
        return cv2.GaussianBlur(lay, (0, 0), 2.2) * 2.2 + cv2.GaussianBlur(lay, (0, 0), 9) * 1.5

    def compass(self, t, M):
        """Rose des vents en filigrane qui se dérègle (« perdre le nord »)."""
        a = self.a.get('nord')
        if not a:
            return None
        t0, t1 = a['t0'] - 0.7, a['t1'] + 1.0
        e = env(t, t0, t1, 0.4, 0.5)
        if e <= 0:
            return None
        sf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
        c = cairo.Context(sf)
        m = cairo.Matrix(xx=M[0, 0], yx=M[1, 0], xy=M[0, 1], yy=M[1, 1], x0=M[0, 2], y0=M[1, 2])
        c.set_matrix(m)
        cx, cy = min(a['x1'] + 380, 2750), a['base'] - 40
        s = max(0.0, t - a['t0'] + 0.2)
        th = 8.0 * s * s + 0.5 * math.sin(s * 23) * min(1, s * 3)
        c.translate(cx, cy)
        c.rotate(th)
        R = 230
        c.set_line_width(3)
        c.arc(0, 0, R, 0, 2 * math.pi); c.stroke()
        c.set_line_width(1.5)
        c.arc(0, 0, R * 0.86, 0, 2 * math.pi); c.stroke()
        for k in range(16):
            ang = k * math.pi / 8
            ln = R * (0.95 if k % 4 == 0 else 0.62 if k % 2 == 0 else 0.42)
            wd = 22 if k % 4 == 0 else 12
            c.move_to(ln * math.cos(ang), ln * math.sin(ang))
            c.line_to(wd * math.cos(ang + math.pi / 2), wd * math.sin(ang + math.pi / 2))
            c.line_to(0, 0)
            c.close_path()
            c.fill() if k % 2 == 0 else c.stroke()
        c.move_to(-10, -R - 18); c.line_to(-10, -R - 50); c.line_to(10, -R - 18); c.line_to(10, -R - 50)
        c.set_line_width(4); c.stroke()
        sf.flush()
        arr = np.ndarray((H, sf.get_stride()), np.uint8, sf.get_data())[:, :W].astype(np.float32) * (1 / 255)
        return cv2.GaussianBlur(arr, (0, 0), 1.2) * 0.20 * e

    def rope(self, t):
        """Ombre d'une corde qui tombe puis se tend (« le péché me jette une corde »)."""
        a, b = self.a.get('corde'), self.a.get('pere')
        if not a or not b:
            return None
        t0, t1 = a['t0'] - 0.2, b['t0'] + 0.2
        e = env(t, t0, t1, 0.25, 0.3)
        if e <= 0:
            return None
        u = t - t0
        fall = 1 - (1 - min(1, u / 0.55)) ** 3
        cou = self.a.get('coffre')
        taut = sm((t - (a['t0'] + 1.0)) / 0.5)
        sf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
        c = cairo.Context(sf)
        x0, y0 = 1650, -60 + (1 - fall) * -500
        x1, y1 = 1150, 1150 + (1 - fall) * -500
        sag = (1 - taut) * 260 + 30 * math.sin(u * 3.1) * (1 - taut)
        c.set_line_width(30)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        c.move_to(x0, y0)
        c.curve_to(x0 - 120 + sag, y0 + 420, x1 + 260 + sag * 0.5, y1 - 380, x1, y1)
        c.stroke()
        for k in range(26):                               # torsion de la corde
            s = k / 26
            px = (1 - s) ** 3 * x0 + 3 * (1 - s) ** 2 * s * (x0 - 120 + sag) + 3 * (1 - s) * s * s * (x1 + 260 + sag * 0.5) + s ** 3 * x1
            py = (1 - s) ** 3 * y0 + 3 * (1 - s) ** 2 * s * (y0 + 420) + 3 * (1 - s) * s * s * (y1 - 380) + s ** 3 * y1
            c.arc(px, py, 18, 0, 2 * math.pi)
            c.fill()
        sf.flush()
        arr = np.ndarray((H, sf.get_stride()), np.uint8, sf.get_data())[:, :W].astype(np.float32) * (1 / 255)
        return cv2.GaussianBlur(arr, (0, 0), 9) * 0.55 * e

    def letterbox(self, t, tip_y):
        a, b = self.a.get('coffre'), self.a.get('pere')
        if not a or not b:
            return 0.0, 0.0
        if a['t0'] <= t < b['t0'] + 0.15:
            k = sm((t - a['t0']) / 0.3) * (1 - sm((t - b['t0']) / 0.15))
            band = 420
            cy = min(max(tip_y - 40, band / 2 + 40), H - band / 2 - 40)
            return k * (cy - band / 2), k * (H - cy - band / 2)
        return 0.0, 0.0

    def water(self, t):
        a, b = self.a.get('eau'), self.a.get('calme')
        if not a or not b:
            return 0.0
        return env(t, a['t0'] - 0.1, b['t1'] + 0.6, 0.45, 0.7)

    def tilt(self, t):
        a, b = self.a.get('releve'), self.a.get('salut')
        if not a or not b:
            return 0.0
        if a['t0'] - 0.6 <= t < a['t0']:
            return sm((t - a['t0'] + 0.6) / 0.6)
        if a['t0'] <= t < b['t1']:
            return 1 - sm((t - a['t0']) / (b['t1'] - a['t0']))
        return 0.0

    def glow_word(self, t):
        a = self.a.get('esprit')
        if not a:
            return None, 0.0
        return a, env(t, a['t0'], a['t1'] + 1.6, 0.3, 1.0)

    def tear(self, t):
        a = self.a.get('dechire')
        if not a or self.page_at(t) != a['page']:
            return None
        t0 = a['t_write1'] + 0.05
        if t < t0:
            return None
        return min(1.0, (t - t0) / 0.9)

    def fade(self, t):
        f = sm(t / 2.5)
        f *= 1 - sm((t - 219.4) / 2.5)
        return f
