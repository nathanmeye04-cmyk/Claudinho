"""Rendu de la vidéo « lettre manuscrite ».

    python3 render.py --t0 15 --t1 36.5 --out essai_refrain.mp4

Chaque processus rend une tranche continue d'images et l'encode ; les
tranches sont ensuite concaténées et l'audio officiel est copié tel quel."""
import argparse
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import cairo
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ecriture import Lettre  # noqa: E402
import scene as S  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, '..', 'audio', 'ALVAN_IMPACT_audio_officiel.m4a')
CACHE = os.path.join(HERE, 'cache')
W, H, FPS = S.W, S.H, S.FPS
smooth = S.smooth


# --- Événements ----------------------------------------------------------------

def light_intensity(t, ev):
    f = 1 + 0.045 * math.sin(2 * math.pi * 1.3 * t) + 0.03 * math.sin(2 * math.pi * 3.7 * t + 1) \
        + 0.02 * math.sin(2 * math.pi * 7.9 * t + 2)
    s0, s1 = ev['silence']
    if s0 <= t < s1:          # silence : la flamme vacille davantage, la lumière baisse un peu
        k = smooth((t - s0) / 0.6) * smooth((s1 - t) / 0.4)
        f = 1 + (f - 1) * (1 + 1.6 * k) - 0.10 * k
    d = ev['devil']           # « le diable travaille… pendant que le chrétien dort »
    if d['t0'] <= t < d['t1']:
        if t < d['low']:
            e = smooth((t - d['t0']) / (d['low'] - d['t0']))
        elif t < d['low'] + 0.5:
            e = 1.0
        else:
            e = 1 - smooth((t - d['low'] - 0.5) / (d['t1'] - d['low'] - 0.5))
        f *= 1 - 0.5 * e
    for th, a in ev['hits']:
        u = t - th
        if 0 <= u < 0.8:
            f *= 1 + 0.10 * a * math.exp(-u / 0.14)
    u = t - ev['drop_beat']
    if 0 <= u < 1.2:
        f *= 1 + 0.08 * math.exp(-u / 0.3)
    return f


class Effects:
    def __init__(self, lettre, ev):
        self.ev = ev
        self.L = lettre
        rng = np.random.default_rng(11)
        # goutte d'encre tombée à la fin de « nations » (ligne « Impacter ma ville… »)
        nat = [w for w in lettre.words if w['flags'].get('drop')]
        self.drop = None
        if nat:
            w = nat[0]
            c = np.array([w['x1'] + 70.0, w['base'] - 26.0])
            ang = np.linspace(0, 2 * math.pi, 90, endpoint=False)
            rad = 1 + 0.10 * np.sin(3 * ang + 1) + 0.07 * np.sin(5 * ang + 2) + 0.05 * np.sin(9 * ang)
            sats = [(c + rng.normal(0, 1, 2) * 9 + np.array([26, 6]), rng.uniform(1.5, 3.0)) for _ in range(2)]
            # lumières de villes vues du ciel : grappes autour de l'impact
            pts = []
            for _ in range(38):
                ca = rng.uniform(0, 2 * math.pi)
                cr = 140 + 900 * math.sqrt(rng.uniform())
                cc = c + cr * np.array([math.cos(ca), math.sin(ca)])
                for _ in range(rng.integers(6, 30)):
                    pts.append(cc + rng.normal(0, 1, 2) * rng.uniform(10, 45))
            pts = np.array(pts)
            self.drop = dict(t=w['t_write1'] + 0.04, c=c, ang=ang, rad=rad, sats=sats, pts=pts,
                             pd=np.linalg.norm(pts - c, axis=1), pb=rng.uniform(0.4, 1, len(pts)))
        # grain de pellicule
        self.grain = [rng.normal(0, 0.011, (H, W)).astype(np.float32) for _ in range(6)]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vign = (1 - 0.40 * np.clip(r, 0, 1.6) ** 2.3).astype(np.float32)[..., None]
        self.vign = np.clip(self.vign, 0.25, 1)
        gy, gx = np.mgrid[0:H // 8, 0:W // 8].astype(np.float64)
        self.grid = np.stack([gx.ravel() * 8 + 4, gy.ravel() * 8 + 4, np.ones(gx.size)])

    def blot(self, ctx, t):
        d = self.drop
        if not d or t < d['t']:
            return
        u = t - d['t']
        R = 19 * (1 - math.exp(-u / 0.10))
        c = d['c']
        ctx.new_path()
        for a, r in zip(d['ang'], d['rad']):
            ctx.line_to(c[0] + R * r * math.cos(a), c[1] + R * r * math.sin(a))
        ctx.close_path(); ctx.fill()
        if u > 0.05:
            for p, rr in d['sats']:
                ctx.arc(p[0], p[1], rr * min(1, (u - 0.05) / 0.1), 0, 2 * math.pi); ctx.fill()

    def lighting(self, t, M, Minv, tip):
        """Carte d'éclairage basse résolution (bougie, ombres, lumières), RGB."""
        wp = (Minv @ self.grid).T[:, :2]               # coordonnées monde de chaque cellule
        d = np.linalg.norm(wp - S.CANDLE, axis=1)
        f = 1.0 / (1 + (d / 1750.0) ** 2) ** 1.25
        I = light_intensity(t, self.ev)
        L = S.AMBIENT[None] + (1.55 * I * f)[:, None] * S.WARM[None]
        gh, gw = H // 8, W // 8
        L = L.reshape(gh, gw, 3)
        # lumière de « la gloire de Dieu » : un rai chaud traverse la feuille
        g0, g1 = self.ev['gloire_light']
        if g0 <= t < g1:
            u = (t - g0) / (g1 - g0)
            s = (wp[:, 0] + 0.45 * wp[:, 1]) - (200 + 3900 * u)
            band = np.exp(-(s / 330.0) ** 2) * math.sin(math.pi * u) ** 1.2
            L += (0.42 * band).reshape(gh, gw, 1) * np.array([1.0, 0.86, 0.6])
        # ombre qui passe derrière l'écrivain
        dv = self.ev['devil']
        p0, p1 = dv['t0'] + 0.1, dv['low'] + 1.2
        if p0 <= t < p1:
            u = (t - p0) / (p1 - p0)
            xs = gw * (1.25 - 1.6 * smooth(u))
            yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
            sil = ((xx - xs) / 19.0) ** 2 + ((yy - 42) / 21.0) ** 2 < 1
            sil |= ((xx - xs) / 58.0) ** 2 + ((yy - 120) / 50.0) ** 2 < 1
            m = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 9)
            k = 0.62 * math.sin(math.pi * u) ** 0.6
            L *= (1 - k * m)[..., None]
        # onde d'impact de la goutte d'encre
        dr = self.drop
        if dr and 0 <= t - dr['t'] < 2.0:
            u = (t - dr['t']) / 1.8
            r = 1500 * (1 - (1 - min(u, 1)) ** 2.2)
            dd = np.linalg.norm(wp - dr['c'], axis=1)
            ring = np.exp(-((dd - r) / 70.0) ** 2) * 0.16 * (1 - min(u, 1)) ** 1.5
            L += ring.reshape(gh, gw, 1) * np.array([1.0, 0.84, 0.55])
        # « Impacter » : brève onde sombre autour de la plume
        for th, a in self.ev['hits']:
            u = t - th
            if 0 <= u < 0.5:
                tw = (Minv @ np.array([tip[0], tip[1], 1.0]))[:2]
                dd = np.linalg.norm(wp - tw, axis=1)
                r = 900 * (u / 0.5) ** 0.6
                ring = np.exp(-((dd - r) / 60.0) ** 2) * 0.16 * a * (1 - u / 0.5)
                L *= (1 - ring.reshape(gh, gw, 1))
        return cv2.resize(L.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)

    def city_lights(self, t, M):
        dr = self.drop
        if not dr or not (0 <= t - dr['t'] < 3.0):
            return None
        el = t - dr['t']
        r = 1500 * (1 - (1 - min(el / 1.8, 1)) ** 2.2)
        lay = np.zeros((H, W), np.float32)
        on = dr['pd'] < r
        if not on.any():
            return None
        tin = 1.8 * (1 - (1 - np.clip(dr['pd'][on] / 1500, 0, 1)) ** (1 / 2.2))
        age = el - tin
        a = dr['pb'][on] * np.clip(age / 0.15, 0, 1) * np.exp(-np.clip(age, 0, None) / 0.55) * 0.75
        sp = (M[:, :2] @ dr['pts'][on].T).T + M[:, 2]
        for (x, y), aa in zip(sp, a):
            if 0 <= x < W and 0 <= y < H and aa > 0.02:
                cv2.circle(lay, (int(x), int(y)), 2, float(aa), -1, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 2.2) * 2.2 + cv2.GaussianBlur(lay, (0, 0), 9) * 1.5
        return lay


# --- Rendu d'une tranche -------------------------------------------------------------

def cairo_matrix(M):
    return cairo.Matrix(xx=M[0, 0], yx=M[1, 0], xy=M[0, 1], yy=M[1, 1], x0=M[0, 2], y0=M[1, 2])


def draw_segs(ctx, segs):
    for x0, y0, x1, y1, w, _ in segs:
        ctx.set_line_width(w)
        ctx.move_to(x0, y0)
        ctx.line_to(x1, y1)
        ctx.stroke()


def render_chunk(args):
    idx, frames, cams, timing, out = args
    world = np.ascontiguousarray(np.load(os.path.join(CACHE, 'monde.npy')))
    lettre = Lettre(timing, origin=S.TEXT_ORIGIN, text_width=S.TEXT_WIDTH)
    ev = lettre.data['events']
    fx = Effects(lettre, ev)
    ink = cairo.ImageSurface(cairo.FORMAT_A8, S.WW, S.WH)
    ictx = cairo.Context(ink)
    ictx.set_line_cap(cairo.LINE_CAP_ROUND)
    ink_np = S.surf_array(ink, 1)
    segs = lettre.segs
    t_first = frames[0] / FPS
    k = int(np.searchsorted(segs[:, 5], t_first, side='right'))
    draw_segs(ictx, segs[:k])
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', '13', '-pix_fmt', 'yuv420p', out],
                          stdin=subprocess.PIPE)
    t_start = time.time()
    for n, fi in enumerate(frames):
        t = fi / FPS
        k2 = int(np.searchsorted(segs[:, 5], t, side='right'))
        draw_segs(ictx, segs[k:k2])
        k = k2
        fx.blot(ictx, t)
        ink.flush()
        M = S.affine(cams[n], t, ev['hits'])
        Minv = np.linalg.inv(np.vstack([M, [0, 0, 1]]))
        img = render_frame(t, M, Minv, world, ink_np, lettre, fx, segs, fi)
        ff.stdin.write(img.tobytes())
        if n % 60 == 0:
            print(f'[{idx}] {n}/{len(frames)} t={t:.2f} {(time.time() - t_start) / (n + 1):.2f}s/img', flush=True)
    ff.stdin.close()
    ff.wait()
    return out


def render_frame(t, M, Minv, world, ink_np, lettre, fx, segs, fi):
    alb = cv2.warpAffine(world, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    inkw = cv2.warpAffine(ink_np[:, :S.WW], M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    paper = alb[..., :3].astype(np.float32) * (1 / 255)
    dens = 0.86 + 0.30 * (alb[..., 3].astype(np.float32) * (1 / 255) - 0.5)
    a = inkw.astype(np.float32) * (1 / 255)
    a = np.clip(a * dens + 0.10 * cv2.GaussianBlur(a, (0, 0), 1.7), 0, 1)
    # encre fraîche : plus sombre et brillante, sèche en ~1 s
    wet = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    wc = cairo.Context(wet)
    wc.set_matrix(cairo_matrix(M))
    wc.set_line_cap(cairo.LINE_CAP_ROUND)
    i1 = int(np.searchsorted(segs[:, 5], t, side='right'))
    i0 = int(np.searchsorted(segs[:, 5], t - 1.0, side='right'))
    for x0, y0, x1, y1, w, ts in segs[i0:i1]:
        wc.set_source_rgba(0, 0, 0, max(0.0, 1 - (t - ts) / 1.0))
        wc.set_line_width(w * 0.8)
        wc.move_to(x0, y0); wc.line_to(x1, y1); wc.stroke()
    wet_a = S.surf_array(wet, 1)[:, :W].astype(np.float32) * (1 / 255)
    col = paper * (1 - a[..., None]) + S.INK * a[..., None]
    wa = (wet_a * a)[..., None]
    col = col * (1 - 0.6 * wa) + S.INK_WET * 0.6 * wa
    # plume et son ombre
    px, py, lift = lettre.pen(t)
    tip = M @ np.array([px, py, 1.0])
    pen, sh = S.draw_pen(tip, math.hypot(M[0, 0], M[1, 0]), lift)
    sha = S.surf_array(sh, 1)[:, :W].astype(np.float32) * (1 / 255)
    sha = cv2.GaussianBlur(sha, (0, 0), 3 + 9 * lift)
    col *= (1 - 0.42 * sha)[..., None]
    pa = S.surf_array(pen, 4)[:, :W].astype(np.float32) * (1 / 255)
    col = col * (1 - pa[..., 3:4]) + pa[..., 2::-1]
    # lumière
    L = fx.lighting(t, M, Minv, tip)
    img = col * L
    img += wa * 0.10 * L.mean(axis=2, keepdims=True)               # reflet de l'encre humide
    cl = fx.city_lights(t, M)
    if cl is not None:
        img += cl[..., None] * np.array([1.0, 0.78, 0.42], np.float32) * 0.55
    # profondeur de champ : net autour de la ligne écrite
    ys = np.arange(H, dtype=np.float32)
    m = smooth((np.abs(ys - tip[1]) - 300) / 420.0) * 0.9
    blur = cv2.GaussianBlur(img, (0, 0), 2.6)
    img = img + (blur - img) * m[:, None, None]
    img *= fx.vign
    img = img / (1 + 0.22 * img) * 1.22
    img = img * 0.975 + np.array([0.008, 0.011, 0.016], np.float32)
    img += fx.grain[fi % 6][..., None]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t0', type=float, default=15.0)
    ap.add_argument('--t1', type=float, default=36.5)
    ap.add_argument('--timing', default=os.path.join(HERE, 'timings', 'refrain1.json'))
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'sorties', 'essai_refrain.mp4'))
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--frames', default='', help='liste de timecodes à exporter en PNG (contrôle)')
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    S.build_world(os.path.join(CACHE, 'monde.npy'))
    lettre = Lettre(a.timing, origin=S.TEXT_ORIGIN, text_width=S.TEXT_WIDTH)
    ev = lettre.data['events']
    cams = S.camera_track(lettre, ev, a.t1 + 1)
    if a.frames:
        # images de contrôle isolées
        for tc in a.frames.split(','):
            fi = int(round(float(tc) * FPS))
            tmp = os.path.join(CACHE, f'ctrl_{fi}.mp4')
            render_chunk((0, [fi], cams[fi:fi + 1], a.timing, tmp))
            png = os.path.join(os.path.dirname(os.path.abspath(a.out)), f'controle_{float(tc):06.2f}.png')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-frames:v', '1', png], check=True)
            print(png)
        return
    f0, f1 = int(round(a.t0 * FPS)), int(round(a.t1 * FPS))
    allf = list(range(f0, f1))
    n = a.jobs
    parts = [allf[i * len(allf) // n:(i + 1) * len(allf) // n] for i in range(n)]
    jobs = [(i, p, cams[p[0]:p[-1] + 1], a.timing, os.path.join(CACHE, f'part_{i}.mp4'))
            for i, p in enumerate(parts) if p]
    t = time.time()
    with Pool(len(jobs)) as pool:
        outs = pool.map(render_chunk, jobs)
    lst = os.path.join(CACHE, 'parts.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{os.path.abspath(o)}'\n" for o in outs)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-ss', f'{a.t0:.3f}', '-t', f'{a.t1 - a.t0:.3f}', '-i', AUDIO,
                    '-map', '0:v', '-map', '1:a', '-c', 'copy', '-movflags', '+faststart', a.out], check=True)
    print(f'{a.out} en {time.time() - t:.0f} s')


if __name__ == '__main__':
    main()
