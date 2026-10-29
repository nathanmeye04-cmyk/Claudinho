"""Rendu de la vidéo « lettre manuscrite » IMPACT — A.L.V.A.N.

    python3 partition.py                       # paroles + minutage → timings/partition.json
    python3 render.py                          # vidéo complète (3:42) avec l'audio officiel
    python3 render.py --t0 60 --t1 75          # un extrait
    python3 render.py --frames 23.3,68.2       # images de contrôle (PNG)

Chaque processus rend une tranche continue d'images et l'encode ; les tranches
sont concaténées et l'audio officiel est copié tel quel (aucun réencodage)."""
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
import scene as S  # noqa: E402
import plume  # noqa: E402
from direction import Direction  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, '..', 'audio', 'ALVAN_IMPACT_audio_officiel.m4a')
PARTITION = os.path.join(HERE, 'timings', 'partition.json')
CACHE = os.path.join(HERE, 'cache')
W, H, FPS = S.W, S.H, S.FPS
DUREE = 222.0
smooth = S.smooth


def cairo_matrix(M):
    return cairo.Matrix(xx=M[0, 0], yx=M[1, 0], xy=M[0, 1], yy=M[1, 1], x0=M[0, 2], y0=M[1, 2])


class PageInk:
    """Encre d'une feuille dans l'espace monde : couverture et charge d'encre."""

    def __init__(self, D, pi):
        self.D, self.pi, self.L = D, pi, D.pages[pi]
        self.cov = cairo.ImageSurface(cairo.FORMAT_A8, S.WW, S.WH)
        self.den = cairo.ImageSurface(cairo.FORMAT_A8, S.WW, S.WH)
        self.cc, self.dc = cairo.Context(self.cov), cairo.Context(self.den)
        for c in (self.cc, self.dc):
            c.set_line_cap(cairo.LINE_CAP_ROUND)
        self.dc.set_operator(cairo.OPERATOR_SOURCE)
        self.k = 0
        self.cov_np = np.ndarray((S.WH, self.cov.get_stride()), np.uint8, self.cov.get_data())
        self.den_np = np.ndarray((S.WH, self.den.get_stride()), np.uint8, self.den.get_data())

    def update(self, t):
        segs = self.L.segs
        k2 = int(np.searchsorted(segs[:, 5], t, side='right'))
        for x0, y0, x1, y1, w, _, ink in segs[self.k:k2]:
            self.cc.set_line_width(w)
            self.cc.move_to(x0, y0); self.cc.line_to(x1, y1); self.cc.stroke()
            self.dc.set_source_rgba(0, 0, 0, ink)
            self.dc.set_line_width(w * 1.15)
            self.dc.move_to(x0, y0); self.dc.line_to(x1, y1); self.dc.stroke()
        self.k = k2
        self.D.draw_marks(self.pi, self.cc, t)
        self.dc.set_source_rgba(0, 0, 0, 1)
        self.D.draw_marks(self.pi, self.dc, t)
        self.cov.flush()
        self.den.flush()


# --- déchirure (« j'ai perdu une part de moi ») -------------------------------------

def tear_poly():
    px, py, pw, ph = S.PAPER
    rng = np.random.default_rng(9)
    a = np.array([px + pw - 340.0, py])
    b = np.array([px + pw, py + 300.0])
    n = 28
    pts = [a + (b - a) * k / n + rng.normal(0, 7, 2) * (0 < k < n) for k in range(n + 1)]
    return np.array(pts + [np.array([px + pw + 2.0, py - 2.0])])


TEAR = tear_poly()


def tear_frag_T(u):
    c = TEAR.mean(axis=0)
    ang = math.radians(70) * u
    R = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), -math.degrees(ang), 1.0)
    R[:, 2] += (900 * u ** 1.2, -650 * u - 300 * u * u)
    return R


def to_screen(pts, M):
    return (M[:, :2] @ pts.T).T + M[:, 2]


# --- rendu ----------------------------------------------------------------------------

class Renderer:
    def __init__(self):
        self.D = Direction(PARTITION)
        self.world, self.desk = S.build_world(CACHE)
        self.inks = {}
        rng = np.random.default_rng(31)
        self.grain = [cv2.GaussianBlur(rng.normal(0, 0.008, (H, W)).astype(np.float32), (0, 0), 0.6) for _ in range(6)]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2)
        self.vign = np.clip(1 - 0.40 * np.clip(r, 0, 1.6) ** 2.3, 0.25, 1).astype(np.float32)[..., None]
        self.xx, self.yy = xx, yy
        self.names = [p['name'] for p in self.D.data['pages']]

    def ink(self, pi, t):
        if pi not in self.inks:
            self.inks[pi] = PageInk(self.D, pi)
        self.inks[pi].update(t)
        for k in [k for k in self.inks if k < pi - 1]:
            del self.inks[k]
        return self.inks[pi]

    def page_view(self, pi, t, M, wet=True, ghost=None, tear=None):
        ink = self.ink(pi, t)
        alb = cv2.warpAffine(self.world, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        cov = cv2.warpAffine(ink.cov_np[:, :S.WW], M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        den = cv2.warpAffine(ink.den_np[:, :S.WW], M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        paper = alb[..., :3].astype(np.float32) * (1 / 255)
        dn = 0.84 + 0.34 * (alb[..., 3].astype(np.float32) * (1 / 255) - 0.5)
        a = cov.astype(np.float32) * (1 / 255) * np.clip(den.astype(np.float32) * (1 / 255), 0.45, 1.0)
        a = np.clip(a * dn + 0.11 * cv2.GaussianBlur(a, (0, 0), 1.8), 0, 1)
        if ghost is not None:            # le recto se devine à travers le papier
            px, _, pw, _ = S.PAPER
            mir = np.array([[-1.0, 0, 2 * px + pw], [0, 1.0, 0]])
            g = cv2.warpAffine(ghost.cov_np[:, :S.WW], S.compose(M, mir), (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
            g = cv2.GaussianBlur(g.astype(np.float32) * (1 / 255), (0, 0), 3.0)
            paper *= (1 - 0.06 * g)[..., None]
        if tear is not None:
            m = S.poly_mask(to_screen(TEAR, M))
            a *= 1 - m
            paper *= (1 - 0.16 * m)[..., None]                 # la feuille du dessous
            edge = cv2.GaussianBlur(cv2.Canny((m * 255).astype(np.uint8), 50, 150).astype(np.float32) / 255, (0, 0), 1.2)
            paper += (0.10 * edge)[..., None]
        col = paper * (1 - a[..., None]) + S.INK * a[..., None]
        wa = None
        if wet:
            segs = ink.L.segs
            i1 = int(np.searchsorted(segs[:, 5], t, side='right'))
            i0 = int(np.searchsorted(segs[:, 5], t - 1.0, side='right'))
            if i1 > i0:
                sf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
                c = cairo.Context(sf)
                c.set_matrix(cairo_matrix(M))
                c.set_line_cap(cairo.LINE_CAP_ROUND)
                for x0, y0, x1, y1, w, ts, _ in segs[i0:i1]:
                    c.set_source_rgba(0, 0, 0, max(0.0, 1 - (t - ts) / 1.0))
                    c.set_line_width(w * 0.8)
                    c.move_to(x0, y0); c.line_to(x1, y1); c.stroke()
                sf.flush()
                wa = np.ndarray((H, sf.get_stride()), np.uint8, sf.get_data())[:, :W].astype(np.float32) * (1 / 255)
                wa = (wa * a)[..., None]
                col = col * (1 - 0.6 * wa) + S.INK_WET * 0.6 * wa
        return col, wa, a, alb

    def frame(self, t, cam, fi):
        D = self.D
        pi = D.page_at(t)
        tr = D.transition(t)
        M = D.matrix(cam, t)
        zoom = math.hypot(M[0, 0], M[1, 0])
        name = self.names[pi]
        ghost = self.ink(pi - 1, t) if name.endswith('verso') else None
        tear_u = D.tear(t)
        wa = None
        if tr is None or tr[0].startswith('glisse'):
            col, wa, a_ink, alb = self.page_view(pi, t, M, ghost=ghost, tear=tear_u)
            if tr:
                u = tr[1]
                e = u * u
                c = S.PAPER_C
                T = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), 7 * e, 1.0)
                T[:, 2] += (-3000 * e, -700 * e)
                Mo = S.compose(M, T)
                po = tr[2]
                col_o, _, _, _ = self.page_view(po, t, Mo, wet=False,
                                                ghost=self.ink(po - 1, t) if self.names[po].endswith('verso') else None,
                                                tear=1.0 if D.a.get('dechire') and D.a['dechire']['page'] == po else None)
                poly = S.paper_poly(M, T)
                mk = S.poly_mask(poly)
                sh = S.poly_mask(poly + np.array([30, 36]) * zoom, 26)
                col = col * (1 - 0.5 * sh * (1 - mk))[..., None]
                col = col * (1 - mk[..., None]) + col_o * mk[..., None]
        else:                                    # la feuille se retourne
            u = tr[1]
            cth = math.cos(math.pi * u)
            sx = max(abs(cth), 0.015)
            lift = math.sin(math.pi * u)
            c = S.PAPER_C
            T = np.array([[sx * (1 + 0.05 * lift), 0, c[0] * (1 - sx * (1 + 0.05 * lift))],
                          [0, 1 + 0.05 * lift, c[1] * (-0.05 * lift)]])
            which = tr[2] if u < 0.5 else pi
            v, _, a_ink, alb = self.page_view(which, t, S.compose(M, T), wet=False,
                                              ghost=self.ink(tr[2], t) if which == pi else None)
            desk = cv2.warpAffine(self.desk, M, (W, H), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_REPLICATE).astype(np.float32) * (1 / 255)
            poly = S.paper_poly(M, T)
            mk = S.poly_mask(poly)
            sh = S.poly_mask(poly + np.array([40, 50]) * zoom * (0.5 + lift), 30 + 30 * lift)
            col = desk * (1 - 0.6 * sh)[..., None]
            col = col * (1 - mk[..., None]) + v * (0.62 + 0.38 * sx) * mk[..., None]
        # fragment déchiré qui s'envole
        if tear_u is not None and tear_u < 1.0:
            Tf = tear_frag_T(tear_u)
            Mf = S.compose(M, Tf)
            fr = cv2.warpAffine(self.world, Mf, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            fr = fr[..., :3].astype(np.float32) * (1 / 255)
            pts = to_screen(TEAR, Mf)
            mk = S.poly_mask(pts)
            sh = S.poly_mask(pts + np.array([30, 40]) * (1 + 2 * tear_u), 12 + 20 * tear_u)
            col = col * (1 - 0.45 * sh * (1 - mk))[..., None]
            col = col * (1 - mk[..., None]) + fr * 1.04 * mk[..., None]
        # plume, ombre de la plume et de la main
        px, py, lift = D.pen(t)
        tip = M @ np.array([px, py, 1.0])
        if not (tr and tr[0] == 'retourne'):
            cand = D.candle(pi)
            cs = M @ np.array([cand[0], cand[1], 1.0])
            prgb, pal, sha = plume.draw(tip, zoom, lift, D.pen_angle(t), (tip[0] - cs[0], tip[1] - cs[1]))
            col *= (1 - sha)[..., None]
            col = col * (1 - pal) + prgb
        # filigrane de la rose des vents (dans le papier)
        comp = D.compass(t, M)
        if comp is not None:
            col *= (1 - comp)[..., None]
        # lumière
        L = D.lighting(t, M, tip)
        img = col * L
        if wa is not None:
            img += wa * 0.10 * L.mean(axis=2, keepdims=True)
        cl = D.city_lights(t, M)
        if cl is not None:
            img += cl[..., None] * np.array([1.0, 0.78, 0.42], np.float32) * 0.55
        gw, ge = D.glow_word(t)
        if ge > 0 and self.names[gw['page']] == name:
            box = np.array([[gw['x0'] - 30, gw['base'] - 95], [gw['x1'] + 30, gw['base'] - 95],
                            [gw['x1'] + 30, gw['base'] + 45], [gw['x0'] - 30, gw['base'] + 45]])
            m = S.poly_mask(to_screen(box, M), 6)
            g = cv2.GaussianBlur(a_ink * m, (0, 0), 12) * 1.4 + cv2.GaussianBlur(a_ink * m, (0, 0), 3) * 0.35
            img += (g * ge)[..., None] * np.array([1.0, 0.82, 0.5], np.float32)
        rp = D.rope(t)
        if rp is not None:
            img *= (1 - rp)[..., None]
        we = D.water(t)
        if we > 0:
            sx_, sy_ = self.xx[::4, ::4], self.yy[::4, ::4]
            c1 = np.sin(sx_ / 95 + t * 1.1) + np.sin(sy_ / 77 - t * 0.9) + np.sin((sx_ + sy_) / 130 + t * 0.6) \
                + np.sin((sx_ - 0.6 * sy_) / 66 - t * 1.4)
            caus = cv2.GaussianBlur((np.clip(1 - np.abs(c1) / 1.2, 0, 1) ** 3).astype(np.float32), (0, 0), 2)
            caus = cv2.resize(caus.astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
            img = img * (1 - we * 0.45 * np.array([0.45, 0.22, 0.0], np.float32))
            img += (we * 0.09 * caus)[..., None] * np.array([0.55, 0.85, 1.0], np.float32)
            mx = (self.xx + we * 4.0 * np.sin(self.yy / 37 + t * 3.0)).astype(np.float32)
            my = (self.yy + we * 3.0 * np.sin(self.xx / 53 + t * 2.2)).astype(np.float32)
            img = cv2.remap(img.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # profondeur de champ : net autour de la ligne écrite
        ys = np.arange(H, dtype=np.float32)
        m = smooth((np.abs(ys - tip[1]) - 300) / 420.0) * 0.9
        blur = cv2.GaussianBlur(img, (0, 0), 2.6)
        img = img + (blur - img) * m[:, None, None]
        img *= self.vign
        img = img / (1 + 0.22 * img) * 1.22
        img = img * 0.975 + np.array([0.008, 0.011, 0.016], np.float32)
        # caméra rasante qui se relève (« je marcherai pas la tête basse »)
        k = D.tilt(t)
        if k > 0.002:
            src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
            dst = np.float32([[-W * 0.02 * k, -H * 0.03 * k], [W + W * 0.02 * k, -H * 0.03 * k],
                              [W + W * 0.26 * k, H + H * 0.12 * k], [-W * 0.26 * k, H + H * 0.12 * k]])
            P = cv2.getPerspectiveTransform(src, dst)
            img = cv2.warpPerspective(img, P, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            img *= (1 - 0.25 * k * smooth(1 - self.yy / H * 1.6))[..., None]
        top, bot = D.letterbox(t, tip[1])
        if top > 0.5:
            img[:int(top)] = 0
            img[H - int(bot):] = 0
        img *= D.fade(t)
        img += self.grain[fi % 6][..., None] * (0.3 + 0.7 * D.fade(t))
        return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_chunk(args):
    idx, frames, cams, out, crf = args
    R = Renderer()
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264',
                           '-preset', 'medium', '-crf', str(crf), '-pix_fmt', 'yuv420p', out],
                          stdin=subprocess.PIPE)
    t_start = time.time()
    for n, fi in enumerate(frames):
        img = R.frame(fi / FPS, cams[n], fi)
        ff.stdin.write(img.tobytes())
        if n % 150 == 0:
            el = time.time() - t_start
            print(f'[{idx}] {n}/{len(frames)} t={fi / FPS:.1f} {el / (n + 1):.2f}s/img', flush=True)
    ff.stdin.close()
    ff.wait()
    return out


def frame_count(path):
    if not os.path.exists(path):
        return -1
    r = subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v',
                        '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', path],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except ValueError:
        return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t0', type=float, default=0.0)
    ap.add_argument('--t1', type=float, default=DUREE)
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'sorties', 'IMPACT_ALVAN_lettre_master.mp4'))
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--crf', type=int, default=15)
    ap.add_argument('--frames', default='', help='timecodes à exporter en PNG (contrôle)')
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    out_dir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(out_dir, exist_ok=True)
    S.build_world(CACHE)
    D = Direction(PARTITION)
    cams = D.camera_track(max(a.t1, DUREE) + 0.1)
    if a.frames:
        R = Renderer()
        for tc in a.frames.split(','):
            fi = int(round(float(tc) * FPS))
            img = R.frame(fi / FPS, cams[fi], fi)
            png = os.path.join(out_dir, f'controle_{float(tc):06.2f}.png')
            cv2.imwrite(png, img[..., ::-1])
            print(png, flush=True)
        return
    f0, f1 = int(round(a.t0 * FPS)), int(round(a.t1 * FPS))
    allf = list(range(f0, f1))
    n = max(1, min(a.jobs, len(allf)))
    # tranches plus petites que le nombre de cœurs pour équilibrer la charge
    k = n * 3
    parts = [allf[i * len(allf) // k:(i + 1) * len(allf) // k] for i in range(k)]
    jobs = [(i, p, cams[p[0]:p[-1] + 1], os.path.join(CACHE, f'part_{i:03d}.mp4'), a.crf)
            for i, p in enumerate(parts) if p]
    t = time.time()
    # reprise : les tranches déjà rendues en entier (redémarrage de la machine) sont gardées
    todo = [j for j in jobs if frame_count(j[3]) != len(j[1])]
    print(f'{len(jobs) - len(todo)} tranches déjà rendues, {len(todo)} à rendre', flush=True)
    if todo:
        with Pool(min(n, len(todo))) as pool:
            pool.map(render_chunk, todo, chunksize=1)
    outs = [j[3] for j in jobs]
    lst = os.path.join(CACHE, 'parts.txt')
    with open(lst, 'w') as f:
        f.writelines(f"file '{os.path.abspath(o)}'\n" for o in outs)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst]
    if a.t0 > 0 or a.t1 < DUREE:
        cmd += ['-ss', f'{a.t0:.3f}', '-t', f'{a.t1 - a.t0:.3f}']
    cmd += ['-i', AUDIO, '-map', '0:v', '-map', '1:a', '-c', 'copy', '-movflags', '+faststart', a.out]
    subprocess.run(cmd, check=True)
    for o in outs:
        os.remove(o)
    print(f'{a.out} en {time.time() - t:.0f} s')


if __name__ == '__main__':
    main()
