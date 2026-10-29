"""Scène : bureau, feuille, encre, plume, lumière de bougie, caméra et effets.
Rendu image par image en 1920×1080 (numpy + OpenCV + cairo)."""
import math
import os

import cairo
import cv2
import numpy as np

W, H = 1920, 1080
FPS = 30

# monde (px) : la feuille est posée sur le bureau
WW, WH = 3600, 4400
PAPER = (600, 500, 2400, 3400)          # x, y, largeur, hauteur
TEXT_ORIGIN = (PAPER[0] + 200, PAPER[1] + 330)
TEXT_WIDTH = 2000
CANDLE = np.array([180.0, 760.0])       # bougie hors champ, en haut à gauche

INK = np.array([0.055, 0.06, 0.095], np.float32)
INK_WET = np.array([0.03, 0.035, 0.075], np.float32)
WARM = np.array([1.0, 0.80, 0.56], np.float32)
AMBIENT = np.array([0.075, 0.085, 0.115], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


# --- Matières ------------------------------------------------------------------

def _noise(shape, sigma, rng):
    n = rng.standard_normal(shape).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), sigma)
    return n / (n.std() + 1e-6)


def build_world(path, seed=3):
    """Texture du bureau + feuille (RGB) et absorption du papier (canal A)."""
    if os.path.exists(path):
        return np.load(path, mmap_mode='r')
    rng = np.random.default_rng(seed)
    # bureau : noyer sombre, veines horizontales
    small = rng.standard_normal((WH // 2, WW // 32)).astype(np.float32)
    small = cv2.GaussianBlur(small, (0, 0), 2.0)
    grain = cv2.resize(small, (WW, WH), interpolation=cv2.INTER_CUBIC)
    rings = np.sin(np.linspace(0, 1, WH)[:, None] * 260 + grain * 2.2)
    desk = np.empty((WH, WW, 3), np.float32)
    base = np.array([0.155, 0.095, 0.060], np.float32)
    v = 1 + 0.10 * rings + 0.06 * grain + 0.05 * _noise((WH, WW), 1.2, rng)
    desk[:] = base * v[..., None]
    # ombre portée de la feuille sur le bureau
    px, py, pw, ph = PAPER
    sh = np.zeros((WH, WW), np.float32)
    sh[py + 18:py + ph + 30, px + 22:px + pw + 26] = 1
    sh = cv2.GaussianBlur(sh, (0, 0), 28)
    desk *= (1 - 0.65 * sh)[..., None]
    # feuille : papier vergé crème
    pap = np.empty((ph, pw, 3), np.float32)
    cream = np.array([0.935, 0.895, 0.815], np.float32)
    mott = 0.012 * _noise((ph, pw), 110, rng) + 0.007 * _noise((ph, pw), 16, rng)
    fine = 0.018 * _noise((ph, pw), 0.7, rng)
    yy = np.arange(ph)[:, None]
    xx = np.arange(pw)[None, :]
    laid = 0.006 * np.sin(yy * 2 * math.pi / 9.0)
    chain = 0.012 * np.exp(-((xx % 250) - 125) ** 2 / 18.0)
    lum = 1 + mott + fine + laid - chain
    # fibres
    fib = np.zeros((ph, pw), np.float32)
    for _ in range(5000):
        x0, y0 = rng.uniform(0, pw), rng.uniform(0, ph)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(6, 26)
        cv2.line(fib, (int(x0), int(y0)), (int(x0 + L * math.cos(a)), int(y0 + L * math.sin(a))),
                 float(rng.choice([-1, 1])), 1, cv2.LINE_AA)
    lum += 0.02 * cv2.GaussianBlur(fib, (0, 0), 0.6)
    # bords légèrement plus sombres et usés
    ex = np.minimum(xx, pw - 1 - xx)
    ey = np.minimum(yy, ph - 1 - yy)
    edge = smooth(np.minimum(ex, ey) / 60.0)
    lum *= 0.93 + 0.07 * edge
    pap[:] = cream * lum[..., None]
    pap[..., 2] -= 0.025 * (1 - edge)          # jaunissement des bords
    world = desk
    world[py:py + ph, px:px + pw] = pap
    absorb = np.full((WH, WW), 128, np.float32)
    absorb[py:py + ph, px:px + pw] += 60 * _noise((ph, pw), 1.0, rng) + 25 * _noise((ph, pw), 6, rng)
    rgba = np.dstack([np.clip(world * 255, 0, 255), np.clip(absorb, 0, 255)]).astype(np.uint8)
    np.save(path, rgba)
    return np.load(path, mmap_mode='r')


# --- Caméra --------------------------------------------------------------------

def camera_track(lettre, ev, t_end):
    """Trajectoire de caméra (ressort amorti) calculée de 0 à t_end, à 30 i/s."""
    n = int(round(t_end * FPS)) + 1
    out = np.zeros((n, 4))                       # cx, cy, zoom, rotation (rad)
    cx0 = TEXT_ORIGIN[0] + TEXT_WIDTH / 2
    first = lettre.pen(0.0)
    pos = np.array([cx0, first[1] + 120.0])
    vel = np.zeros(2)
    zoom, zvel = 0.95, 0.0
    omega = 2.0
    sub = 4
    dt = 1.0 / FPS / sub
    sil0, sil1 = ev['silence']
    for i in range(n):
        t = i / FPS
        for _ in range(sub):
            px, py, lift = lettre.pen(t)
            target = np.array([cx0 + 0.2 * (px - cx0), py - 0.06 * H / zoom])
            acc = omega * omega * (target - pos) - 2 * omega * vel
            vel += acc * dt
            pos += vel * dt
            zt = 0.86
            if sil0 <= t < sil1:                 # le silence : lente poussée
                zt = 0.86 + 0.05 * smooth((t - sil0) / (sil1 - sil0))
            za = 1.6 ** 2 * (zt - zoom) - 2 * 1.6 * zvel
            zvel += za * dt
            zoom += zvel * dt
        rot = math.radians(-0.9 + 0.25 * math.sin(t * 0.21))
        out[i] = (pos[0] + 6 * math.sin(t * 0.37), pos[1] + 5 * math.sin(t * 0.29 + 1), zoom
                  * (1 + 0.004 * math.sin(t * 0.5)), rot)
    return out


def hit_shake(t, hits):
    dx = dy = dr = 0.0
    for th, a in hits:
        u = t - th
        if 0 <= u < 0.6:
            e = a * math.exp(-u / 0.09)
            dx += 9 * e * math.sin(2 * math.pi * 17 * u)
            dy += 6 * e * math.sin(2 * math.pi * 13 * u + 1)
            dr += math.radians(0.22) * e * math.sin(2 * math.pi * 11 * u)
    return dx, dy, dr


def affine(cam, t, hits):
    cx, cy, z, r = cam
    dx, dy, dr = hit_shake(t, hits)
    r += dr
    c, s = math.cos(r) * z, math.sin(r) * z
    # écran = R·z·(monde − centre) + milieu
    return np.array([[c, -s, W / 2 + dx - (c * cx - s * cy)],
                     [s, c, H / 2 + dy - (s * cx + c * cy)]], np.float64)


# --- Plume -----------------------------------------------------------------------

def _pen_path(c, part):
    if part == 'nib':
        c.move_to(0, 0)
        c.curve_to(18, -2.5, 46, -9, 72, -11.5)
        c.line_to(80, -12.5)
        c.line_to(80, 12.5)
        c.line_to(72, 11.5)
        c.curve_to(46, 9, 18, 2.5, 0, 0)
    elif part == 'section':
        c.move_to(78, -12.5); c.line_to(172, -14.5); c.line_to(172, 14.5); c.line_to(78, 12.5)
    elif part == 'ring':
        c.rectangle(170, -16.5, 12, 33)
    elif part == 'body':
        c.move_to(181, -17.5); c.line_to(1500, -19); c.line_to(1500, 19); c.line_to(181, 17.5)
    c.close_path()


def draw_pen(tip, zoom, lift, angle=math.radians(52)):
    """Plume (ARGB) et sa silhouette d'ombre (A8), en espace écran."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    k = zoom * (1 + 0.05 * lift)
    c.translate(tip[0], tip[1] - 12 * lift * zoom)
    c.rotate(angle)
    c.scale(k, k * 1.25)
    # corps laqué noir
    g = cairo.LinearGradient(0, -19, 0, 19)
    g.add_color_stop_rgb(0.0, 0.10, 0.10, 0.11)
    g.add_color_stop_rgb(0.22, 0.42, 0.40, 0.38)
    g.add_color_stop_rgb(0.34, 0.07, 0.07, 0.08)
    g.add_color_stop_rgb(1.0, 0.015, 0.015, 0.02)
    _pen_path(c, 'body'); c.set_source(g); c.fill()
    _pen_path(c, 'section'); c.set_source(g); c.fill()
    g2 = cairo.LinearGradient(0, -16, 0, 16)
    g2.add_color_stop_rgb(0.0, 0.55, 0.42, 0.20)
    g2.add_color_stop_rgb(0.25, 0.98, 0.86, 0.55)
    g2.add_color_stop_rgb(1.0, 0.30, 0.21, 0.09)
    _pen_path(c, 'ring'); c.set_source(g2); c.fill()
    # bec doré
    g3 = cairo.LinearGradient(0, -12, 0, 12)
    g3.add_color_stop_rgb(0.0, 0.60, 0.46, 0.22)
    g3.add_color_stop_rgb(0.30, 0.97, 0.88, 0.62)
    g3.add_color_stop_rgb(0.55, 0.74, 0.58, 0.30)
    g3.add_color_stop_rgb(1.0, 0.36, 0.25, 0.10)
    _pen_path(c, 'nib'); c.set_source(g3); c.fill()
    c.set_source_rgba(0.12, 0.08, 0.04, 0.9)
    c.set_line_width(1.1)
    c.move_to(2, 0); c.line_to(48, 0); c.stroke()
    c.arc(50, 0, 2.6, 0, 2 * math.pi); c.fill()
    c.set_source_rgba(0.02, 0.02, 0.03, 0.85)            # pointe encrée
    c.move_to(0, 0); c.curve_to(6, -1.2, 12, -2.3, 16, -3); c.line_to(16, 3); c.curve_to(12, 2.3, 6, 1.2, 0, 0)
    c.fill()
    # ombre : même silhouette décalée à l'opposé de la bougie
    sh = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    cs = cairo.Context(sh)
    off = (12 + 34 * lift) * zoom
    cs.translate(tip[0] + off * 0.75, tip[1] + off)
    cs.rotate(angle)
    cs.scale(zoom, zoom * 1.25)
    for part in ('body', 'section', 'ring', 'nib'):
        _pen_path(cs, part)
        cs.fill()
    return surf, sh


def surf_array(s, ch):
    s.flush()
    a = np.ndarray((s.get_height(), s.get_stride() // (4 if ch == 4 else 1), ch) if ch == 4 else
                   (s.get_height(), s.get_stride()), np.uint8, s.get_data())
    return a
