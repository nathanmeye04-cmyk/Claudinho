"""Stylo-plume tenu par une main hors champ.

Le corps remonte vers le haut de l'image, raccourci et élargi par la
perspective (il s'approche de l'objectif) et de plus en plus flou. L'ombre
part de la pointe, à l'opposé de la bougie, avec celle de la main au bout."""
import math

import cairo
import cv2
import numpy as np

W, H = 1920, 1080


def _profile():
    """Demi-largeur (unités monde) le long de l'axe, depuis la pointe."""
    u = np.r_[np.linspace(0, 66, 40), np.linspace(66.5, 150, 20), np.linspace(150.5, 162, 4), np.linspace(162.5, 1300, 40)]
    hw = np.empty_like(u)
    nib = u <= 66
    hw[nib] = 0.8 + 11.5 * (u[nib] / 66) ** 0.75
    sec = (u > 66) & (u <= 150)
    s = (u[sec] - 66) / 84
    hw[sec] = 12.6 + 1.6 * s - 0.9 * np.sin(math.pi * s)
    ring = (u > 150) & (u <= 162)
    hw[ring] = 15.8
    body = u > 162
    hw[body] = 16.8 + 0.6 * np.clip((u[body] - 162) / 200, 0, 1)
    return u, hw


_U, _HW = _profile()


def _project(u, v, tip, ang, k, persp):
    """Pointe → écran : axe raccourci, largeur croissante avec la proximité."""
    g = 1 + u / persp
    uu = u * k * 0.78 * (1 + u / (persp * 2.2))
    vv = v * k * g
    ca, sa = math.cos(ang), math.sin(ang)
    return tip[0] + uu * ca - vv * sa, tip[1] + uu * sa + vv * ca


def _poly(c, u0, u1, tip, ang, k, persp, scale_v=1.0):
    m = (_U >= u0) & (_U <= u1)
    us, hs = _U[m], _HW[m] * scale_v
    pts = [_project(a, -b, tip, ang, k, persp) for a, b in zip(us, hs)]
    pts += [_project(a, b, tip, ang, k, persp) for a, b in zip(us[::-1], hs[::-1])]
    c.move_to(*pts[0])
    for p in pts[1:]:
        c.line_to(*p)
    c.close_path()


def _grad(tip, ang, k, u, hw, persp, stops):
    a = _project(u, -hw, tip, ang, k, persp)
    b = _project(u, hw, tip, ang, k, persp)
    g = cairo.LinearGradient(a[0], a[1], b[0], b[1])
    for s, col in stops:
        g.add_color_stop_rgb(s, *col)
    return g


RESIN = [(0.0, (0.06, 0.06, 0.07)), (0.16, (0.55, 0.53, 0.50)), (0.24, (0.10, 0.10, 0.11)),
         (0.62, (0.025, 0.025, 0.03)), (0.86, (0.09, 0.085, 0.09)), (1.0, (0.02, 0.02, 0.025))]
GOLD = [(0.0, (0.50, 0.37, 0.16)), (0.2, (0.99, 0.88, 0.58)), (0.42, (0.78, 0.60, 0.30)),
        (0.75, (0.45, 0.32, 0.12)), (1.0, (0.62, 0.48, 0.22))]
NIB = [(0.0, (0.55, 0.42, 0.20)), (0.22, (0.98, 0.90, 0.66)), (0.5, (0.80, 0.64, 0.36)),
       (0.8, (0.50, 0.36, 0.15)), (1.0, (0.70, 0.56, 0.28))]


def draw(tip, zoom, lift, ang, light_dir, persp=420.0):
    """Renvoie (plume ARGB prémultipliée float, alpha, ombre float)."""
    k = zoom * (1 + 0.06 * lift)
    tip = (tip[0] - 4 * lift * zoom, tip[1] - 16 * lift * zoom)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    # corps en résine noire, bague dorée, section, bec bicolore
    _poly(c, 162, 1300, tip, ang, k, persp)
    c.set_source(_grad(tip, ang, k, 400, 17.4, persp, RESIN)); c.fill()
    _poly(c, 66, 150.5, tip, ang, k, persp)
    c.set_source(_grad(tip, ang, k, 100, 13.5, persp, RESIN)); c.fill()
    _poly(c, 150, 162.5, tip, ang, k, persp)
    c.set_source(_grad(tip, ang, k, 156, 15.8, persp, GOLD)); c.fill()
    _poly(c, 0, 66.5, tip, ang, k, persp)
    c.set_source(_grad(tip, ang, k, 40, 9, persp, NIB)); c.fill()
    # incrustation argentée (cœur du bec) et fente
    _poly(c, 14, 46, tip, ang, k, persp, scale_v=0.42)
    c.set_source(_grad(tip, ang, k, 30, 4, persp, [(0, (0.55, 0.56, 0.58)), (0.35, (0.95, 0.96, 0.97)), (1, (0.45, 0.46, 0.5))]))
    c.fill()
    c.set_source_rgba(0.10, 0.07, 0.03, 0.95)
    c.set_line_width(max(0.8, 1.0 * k))
    c.move_to(*_project(1.5, 0, tip, ang, k, persp)); c.line_to(*_project(44, 0, tip, ang, k, persp)); c.stroke()
    x, y = _project(46, 0, tip, ang, k, persp)
    c.arc(x, y, 2.4 * k, 0, 2 * math.pi); c.fill()
    # gravure discrète
    c.set_source_rgba(0.35, 0.24, 0.08, 0.7)
    c.set_line_width(0.6 * k)
    for s in (-1, 1):
        c.move_to(*_project(50, 3 * s, tip, ang, k, persp))
        c.curve_to(*_project(55, 7 * s, tip, ang, k, persp), *_project(60, 5 * s, tip, ang, k, persp),
                   *_project(63, 9 * s, tip, ang, k, persp))
        c.stroke()
    # pointe encrée
    c.set_source_rgba(0.02, 0.02, 0.035, 0.92)
    _poly(c, 0, 9, tip, ang, k, persp)
    c.fill()
    # reflet de la bougie sur la résine
    c.set_source_rgba(1.0, 0.86, 0.62, 0.35)
    c.set_line_width(2.2 * k)
    c.move_to(*_project(175, -11.5, tip, ang, k, persp)); c.line_to(*_project(1200, -12.5, tip, ang, k, persp)); c.stroke()
    surf.flush()
    a = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W].astype(np.float32) * (1 / 255)
    rgb, alpha = a[..., 2::-1].copy(), a[..., 3:4].copy()
    # flou de mise au point : net à la pointe, de plus en plus flou vers l'objectif
    yy, xx = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
    ca, sa = math.cos(ang), math.sin(ang)
    along = ((xx - tip[0]) * ca + (yy - tip[1]) * sa) / max(k, 1e-3)
    m = np.clip((along - 90) / 380.0, 0, 1)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    pre = np.concatenate([rgb, alpha], axis=2)
    b1 = cv2.GaussianBlur(pre, (0, 0), 3.5)
    b2 = cv2.GaussianBlur(pre, (0, 0), 11)
    w1 = np.clip(m * 2, 0, 1)
    w2 = np.clip(m * 2 - 1, 0, 1)
    pre = pre * (1 - w1) + b1 * w1
    pre = pre * (1 - w2) + b2 * w2
    rgb, alpha = pre[..., :3], pre[..., 3:4]
    # ombre : part de la pointe, s'allonge à l'opposé de la lumière
    sh = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    cs = cairo.Context(sh)
    ld = np.asarray(light_dir, float)
    ld /= np.linalg.norm(ld) + 1e-9
    sa_ = math.atan2(ld[1], ld[0])
    st = (tip[0] + ld[0] * 10 * lift * zoom, tip[1] + ld[1] * 10 * lift * zoom)
    _poly(cs, 0, 760, st, sa_, zoom * 0.95, 1e9)
    cs.fill()
    # main : doigts et paume au bout de l'ombre du stylo
    for du, dv, rx, ry in ((300, -10, 70, 38), (360, 40, 95, 60), (470, 30, 150, 115), (330, -55, 60, 30)):
        x, y = _project(du, dv, st, sa_, zoom, 1e9)
        cs.save(); cs.translate(x, y); cs.rotate(sa_); cs.scale(rx * zoom, ry * zoom)
        cs.arc(0, 0, 1, 0, 2 * math.pi); cs.restore(); cs.fill()
    sh.flush()
    s = np.ndarray((H, sh.get_stride()), np.uint8, sh.get_data())[:, :W].astype(np.float32) * (1 / 255)
    s1 = cv2.GaussianBlur(s, (0, 0), 2.5 + 6 * lift)
    s2 = cv2.GaussianBlur(s, (0, 0), 26)
    along = ((xx - st[0]) * math.cos(sa_) + (yy - st[1]) * math.sin(sa_)) / max(zoom, 1e-3)
    ms = cv2.resize(np.clip((along - 30) / 260.0, 0, 1), (W, H), interpolation=cv2.INTER_LINEAR)
    shadow = (s1 * (1 - ms) + s2 * ms) * (0.55 - 0.25 * ms)
    return rgb, alpha, shadow
