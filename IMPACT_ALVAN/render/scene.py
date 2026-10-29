"""Constantes de la scène, matières (bureau, feuille) et géométrie de caméra."""
import math
import os

import cv2
import numpy as np

W, H = 1920, 1080
FPS = 30

# monde (px) : chaque feuille est posée au même endroit sur le bureau
WW, WH = 3600, 4400
PAPER = (600, 500, 2400, 3400)          # x, y, largeur, hauteur
TEXT_ORIGIN = (PAPER[0] + 200, PAPER[1] + 330)
TEXT_WIDTH = 2000
PAPER_C = np.array([PAPER[0] + PAPER[2] / 2, PAPER[1] + PAPER[3] / 2])

INK = np.array([0.050, 0.055, 0.090], np.float32)
INK_WET = np.array([0.025, 0.030, 0.070], np.float32)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def sm(x):
    """smoothstep scalaire."""
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _noise(shape, sigma, rng):
    n = rng.standard_normal(shape).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), sigma)
    return n / (n.std() + 1e-6)


def build_world(cache, seed=3):
    """Texture monde (bureau + feuille, RGB) avec l'absorption du papier en
    canal A, et le bureau seul (pour les feuilles qui bougent)."""
    pw_path = os.path.join(cache, 'monde.npy')
    pd_path = os.path.join(cache, 'bureau.npy')
    if os.path.exists(pw_path) and os.path.exists(pd_path):
        return np.load(pw_path), np.load(pd_path)
    rng = np.random.default_rng(seed)
    small = rng.standard_normal((WH // 2, WW // 32)).astype(np.float32)
    small = cv2.GaussianBlur(small, (0, 0), 2.0)
    grain = cv2.resize(small, (WW, WH), interpolation=cv2.INTER_CUBIC)
    rings = np.sin(np.linspace(0, 1, WH)[:, None] * 260 + grain * 2.2)
    base = np.array([0.150, 0.092, 0.058], np.float32)
    v = 1 + 0.10 * rings + 0.06 * grain + 0.05 * _noise((WH, WW), 1.2, rng)
    desk = base * v[..., None]
    desk_only = np.clip(desk * 255, 0, 255).astype(np.uint8)
    px, py, pw, ph = PAPER
    # feuilles empilées dessous : bords légèrement décalés
    under = np.zeros((WH, WW), np.float32)
    for dx, dy, a in ((14, 10, 0.006), (-9, 18, -0.004)):
        M = cv2.getRotationMatrix2D((float(PAPER_C[0]), float(PAPER_C[1])), math.degrees(a), 1.0)
        M[:, 2] += (dx, dy)
        r = np.zeros((WH, WW), np.float32)
        r[py:py + ph, px:px + pw] = 1
        under = np.maximum(under, cv2.warpAffine(r, M, (WW, WH)))
    sh = np.zeros((WH, WW), np.float32)
    sh[py + 18:py + ph + 34, px + 20:px + pw + 30] = 1
    sh = cv2.GaussianBlur(np.maximum(sh, under), (0, 0), 28)
    desk *= (1 - 0.65 * sh)[..., None]
    cream = np.array([0.935, 0.895, 0.815], np.float32)
    desk = desk * (1 - under[..., None]) + (cream * 0.80) * under[..., None]
    pap = np.empty((ph, pw, 3), np.float32)
    mott = 0.012 * _noise((ph, pw), 110, rng) + 0.007 * _noise((ph, pw), 16, rng)
    fine = 0.018 * _noise((ph, pw), 0.7, rng)
    yy = np.arange(ph)[:, None]
    xx = np.arange(pw)[None, :]
    laid = 0.006 * np.sin(yy * 2 * math.pi / 9.0)
    chain = 0.012 * np.exp(-((xx % 250) - 125) ** 2 / 18.0)
    lum = 1 + mott + fine + laid - chain
    fib = np.zeros((ph, pw), np.float32)
    for _ in range(5000):
        x0, y0 = rng.uniform(0, pw), rng.uniform(0, ph)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(6, 26)
        cv2.line(fib, (int(x0), int(y0)), (int(x0 + L * math.cos(a)), int(y0 + L * math.sin(a))),
                 float(rng.choice([-1, 1])), 1, cv2.LINE_AA)
    lum += 0.02 * cv2.GaussianBlur(fib, (0, 0), 0.6)
    ex = np.minimum(xx, pw - 1 - xx)
    ey = np.minimum(yy, ph - 1 - yy)
    edge = smooth(np.minimum(ex, ey) / 60.0)
    lum *= 0.93 + 0.07 * edge
    pap[:] = cream * lum[..., None]
    pap[..., 2] -= 0.025 * (1 - edge)
    world = desk
    world[py:py + ph, px:px + pw] = pap
    absorb = np.full((WH, WW), 128, np.float32)
    absorb[py:py + ph, px:px + pw] += 60 * _noise((ph, pw), 1.0, rng) + 25 * _noise((ph, pw), 6, rng)
    rgba = np.dstack([np.clip(world * 255, 0, 255), np.clip(absorb, 0, 255)]).astype(np.uint8)
    np.save(pw_path, rgba)
    np.save(pd_path, desk_only)
    return rgba, desk_only


def affine(cx, cy, z, r, dx=0.0, dy=0.0):
    """Monde → écran : écran = R·z·(monde − centre) + milieu."""
    c, s = math.cos(r) * z, math.sin(r) * z
    return np.array([[c, -s, W / 2 + dx - (c * cx - s * cy)],
                     [s, c, H / 2 + dy - (s * cx + c * cy)]], np.float64)


def compose(M, T):
    """M ∘ T pour deux matrices affines 2×3."""
    A = np.vstack([M, [0, 0, 1]]) @ np.vstack([T, [0, 0, 1]])
    return A[:2]


def paper_poly(M, T=None):
    px, py, pw, ph = PAPER
    pts = np.array([[px, py], [px + pw, py], [px + pw, py + ph], [px, py + ph]], np.float64)
    A = compose(M, T) if T is not None else M
    return (A[:, :2] @ pts.T).T + A[:, 2]


def poly_mask(pts, blur=0.0):
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts * 16).astype(np.int32)], 255, cv2.LINE_AA, shift=4)
    m = m.astype(np.float32) * (1 / 255)
    if blur > 0:
        m = cv2.GaussianBlur(m, (0, 0), blur)
    return m
