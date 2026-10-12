#!/usr/bin/env python3
"""CI-O MIAM — glace CERELAC : publicité vidéo verticale 9:16 (1080 x 1920, 15 s, 30 i/s).

Tout part de l'image de référence (reference/cerelac_reference.webp) :
  - le pot, le logo et le titre CERELAC sont détourés de l'affiche (rembg) : rien n'est redessiné,
    le contenant et le logo restent strictement identiques ;
  - le décor « table de dégustation » est l'affiche elle-même, textes effacés (inpainting OpenCV) ;
  - les céréales qui flottent / tombent sont de vrais flocons détourés de la photo ;
  - voix off française (voix neuronale Microsoft « Vivienne », via edge-tts), musique originale et bruitages
    synthétisés ici (numpy), musique baissée automatiquement sous la voix.

Scénario : 0-3 s révélation du pot · 3-6 s gros plan en arc de cercle · 6-10 s travelling sur la
table de dégustation · 10-15 s plan final, logo et informations de commande.

Usage : python3 cio_miam_cerelac/build_pub.py  ->  cio_miam_cerelac/CIO_MIAM_CERELAC_pub_9x16.mp4
Dépendances : ffmpeg, numpy, scipy, pillow ; pour régénérer assets/ : rembg, opencv-python-headless ;
pour régénérer la voix : edge-tts (voix neuronale « Vivienne », connexion internet requise).
"""
import math
import os
import subprocess
import tempfile
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference", "cerelac_reference.webp")
ASSETS = os.path.join(HERE, "assets")
VOIX = os.path.join(HERE, "voix")
FONTS = os.path.join(HERE, "fonts")
CACHE = os.path.expanduser("~/.cache/cio_miam")
OUT = os.path.join(HERE, "CIO_MIAM_CERELAC_pub_9x16.mp4")
W, H, FPS, SR, DUR = 1080, 1920, 30, 48000, 15.0
NF = int(DUR * FPS)

# Informations commerciales (affichées uniquement dans le plan final)
TEL = "+241 77 14 12 14"
LIEU = "Ambowé (cimetière)"
LIVRAISON = ("Livraison disponible", "à partir de 5 pots commandés.")

# Voix off : texte du brief, écrit « comme il se prononce » pour la synthèse vocale
VOICE_LINES = [
    "Retrouvez le goût de l'enfance, avec la glace Céréla de Si-O Miam !",
    "Une douceur crémeuse, une touche de céréales... et le plaisir, à chaque cuillère !",
    "Commandez au plus deux cent quarante et un, soixante-dix-sept, quatorze, douze, quatorze !",
    "Livraison disponible dès cinq pots !",
    "Si-O Miam, des glaces qui font plaisir !",
]
VOICE_START, VOICE_GAP, VOICE_TEMPO = 0.15, 0.08, 1.0
VOICE_NAME, VOICE_RATE, VOICE_PITCH = "fr-FR-VivienneMultilingualNeural", "+19%", "+2Hz"

BROWN = (62, 31, 16)
CHOCO = (78, 40, 20)
ORANGE = (214, 104, 34)
CREAM = (250, 241, 228)
FLASH = (253, 246, 235)


# ----------------------------------------------------------------------------- utilitaires
def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def lerp(a, b, x):
    return a + (b - a) * x


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONTS, f"Poppins-{weight}.ttf"), size)


# ----------------------------------------------------------------------------- assets (détourages)
ASSET_FILES = ["pot.png", "logo.png", "titre.png", "decor_table.png", "flocon_a.png", "flocon_b.png"]


def alpha_crop(img, thr=12):
    return img.crop(img.split()[3].point(lambda v: 255 if v > thr else 0).getbbox())


def build_assets():
    if all(os.path.exists(os.path.join(ASSETS, f)) for f in ASSET_FILES):
        return
    import cv2
    from rembg import new_session, remove

    os.makedirs(ASSETS, exist_ok=True)
    ref = Image.open(REF).convert("RGB")
    sess = new_session("isnet-general-use")
    cut = remove(ref, session=sess)
    a = np.array(cut)

    # Pot : on retire les restes des textes latéraux à hauteur de la crème
    pot = a[515:1345, 250:925].copy()
    pot[: 690 - 515, : 320 - 250, 3] = 0
    pot[: 690 - 515, 890 - 250:, 3] = 0
    alpha_crop(Image.fromarray(pot)).save(os.path.join(ASSETS, "pot.png"))
    alpha_crop(cut.crop((360, 35, 790, 265))).save(os.path.join(ASSETS, "logo.png"))
    alpha_crop(cut.crop((190, 280, 955, 462))).save(os.path.join(ASSETS, "titre.png"))

    # Vrais flocons de céréales posés sur la table
    for name, (x0, y0, x1, y1) in {"flocon_a": (60, 1110, 150, 1215), "flocon_b": (285, 1255, 370, 1300)}.items():
        c = remove(ref.crop((x0 - 30, y0 - 30, x1 + 30, y1 + 30)), session=sess)
        alpha_crop(c, 40).save(os.path.join(ASSETS, f"{name}.png"))

    # Décor : l'affiche sans ses textes (logo, titre, accroche, mentions latérales)
    im = cv2.cvtColor(np.array(ref), cv2.COLOR_RGB2BGR)
    mask = np.zeros(im.shape[:2], np.uint8)
    for x0, y0, x1, y1 in [(360, 35, 790, 265), (190, 280, 955, 470), (200, 462, 920, 505),
                           (95, 560, 310, 690), (890, 560, 1100, 690)]:
        reg = im[y0:y1, x0:x1].astype(int)
        m = (reg.mean(2) < 200) | ((reg.max(2) - reg.min(2)) > 60)
        mask[y0:y1, x0:x1] = m.astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    out = cv2.inpaint(im, mask, 12, cv2.INPAINT_TELEA)
    bl = cv2.GaussianBlur(out, (0, 0), 18)
    mk = cv2.GaussianBlur(cv2.dilate(mask, np.ones((25, 25), np.uint8)).astype(np.float32) / 255, (0, 0), 8)[..., None]
    clean = (out * (1 - mk) + bl * mk).astype(np.uint8)
    Image.fromarray(cv2.cvtColor(clean, cv2.COLOR_BGR2RGB)).save(os.path.join(ASSETS, "decor_table.png"))


# ----------------------------------------------------------------------------- calques fixes
A = {}


def load():
    for f in ASSET_FILES:
        A[f[:-4]] = Image.open(os.path.join(ASSETS, f)).convert("RGBA" if f != "decor_table.png" else "RGB")
    A["studio"] = studio_base()
    A["beams"] = beams_layer()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.62)) ** 2)
    A["vignette"] = (1 - 0.16 * np.clip(d - 0.45, 0, 1) ** 1.4)[..., None]
    rng = np.random.default_rng(7)
    A["grain"] = [rng.normal(0, 2.2, (H, W, 1)).astype(np.float32) for _ in range(6)]
    A["shadow"] = shadow_sprite()
    A["texts"] = final_texts()


def studio_base():
    """Studio crème/caramel, plus grand que l'image pour permettre les mouvements de caméra."""
    bw, bh = int(W * 1.25), int(H * 1.25)
    y = np.linspace(0, 1, bh)[:, None, None]
    top, mid, floor0, floor1 = [np.array(c, np.float32) for c in
                                [(247, 237, 223), (238, 222, 203), (229, 210, 188), (212, 188, 162)]]
    horizon = 0.70
    wall = top + (mid - top) * (y / horizon)
    fl = floor0 + (floor1 - floor0) * np.clip((y - horizon) / (1 - horizon), 0, 1)
    k = 1 / (1 + np.exp(-(y - horizon) / 0.012))
    img = wall * (1 - k) + fl * k
    img = np.broadcast_to(img, (bh, bw, 3)).copy()
    yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
    glow = np.exp(-(((xx - bw / 2) / (bw * 0.42)) ** 2 + ((yy - bh * 0.50) / (bh * 0.30)) ** 2))
    img += glow[..., None] * np.array([14, 12, 9], np.float32)
    return np.clip(img, 0, 255).astype(np.float32)


def beams_layer():
    """Rayons de lumière diagonaux, doux (comme sur l'affiche)."""
    bw, bh = int(W * 1.6), int(H * 1.25)
    m = Image.new("L", (bw, bh), 0)
    d = ImageDraw.Draw(m)
    for x, wdt, v in [(0.10, 0.10, 120), (0.30, 0.06, 90), (0.52, 0.12, 110), (0.80, 0.07, 80)]:
        x0 = x * bw
        d.polygon([(x0, -50), (x0 + wdt * bw, -50), (x0 + wdt * bw - bh * 0.55, bh + 50), (x0 - bh * 0.55, bh + 50)], fill=v)
    m = m.filter(ImageFilter.GaussianBlur(70))
    fade = np.linspace(1.0, 0.25, bh, dtype=np.float32)[:, None]
    return (np.asarray(m, np.float32) / 255 * fade)[..., None]


def shadow_sprite():
    s = Image.new("L", (600, 160), 0)
    ImageDraw.Draw(s).ellipse((60, 40, 540, 120), fill=255)
    return s.filter(ImageFilter.GaussianBlur(22))


def spaced(draw, xy, text, fnt, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + track


def spaced_len(text, fnt, track):
    return sum(fnt.getlength(c) + track for c in text) - track


def text_img(parts, height, pad=8):
    """parts = [(texte, police, couleur, interlettrage)] posés à la suite sur une ligne."""
    total = sum(spaced_len(t, f, k) for t, f, c, k in parts)
    img = Image.new("RGBA", (int(total) + 2 * pad, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for t, f, c, k in parts:
        asc, desc = f.getmetrics()
        spaced(d, (x, (height - asc - desc) // 2 + 2), t, f, c, k)
        x += spaced_len(t, f, k)
    return img


def hstack(items, gap, height):
    w = sum(i.width for i in items) + gap * (len(items) - 1)
    out = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    x = 0
    for i in items:
        out.alpha_composite(i, (x, (height - i.height) // 2))
        x += i.width + gap
    return out


def fit(img, max_w):
    if img.width <= max_w:
        return img
    return img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)


def final_texts():
    """Calques du plan final : (image, centre x, haut y, instant d'apparition)."""
    T = []
    logo = A["logo"].resize((400, round(A["logo"].height * 400 / A["logo"].width)), Image.LANCZOS)
    titre = A["titre"].resize((700, round(A["titre"].height * 700 / A["titre"].width)), Image.LANCZOS)
    T.append(("logo", logo, 540, 215, 10.05))
    T.append(("titre", titre, 540, 215 + logo.height + 12, 10.20))
    y_tag = 215 + logo.height + 12 + titre.height + 14
    tag = text_img([("LE GOÛT D’ENFANCE AUTREMENT", font("Medium", 27), BROWN, 7)], 44)
    T.append(("tag", tag, 540, y_tag, 10.35))

    # bouton « Commandez maintenant »
    lab = text_img([("COMMANDEZ MAINTENANT", font("SemiBold", 36), CREAM, 3)], 60)
    pill = Image.new("RGBA", (lab.width + 90, 84), (0, 0, 0, 0))
    ImageDraw.Draw(pill).rounded_rectangle((0, 0, pill.width - 1, 83), radius=42, fill=CHOCO)
    ImageDraw.Draw(pill).rounded_rectangle((26, 74, pill.width - 27, 77), radius=2, fill=ORANGE)
    pill.alpha_composite(lab, (45, 10))
    T.append(("pill", pill, 540, 1300, 10.55))

    # WhatsApp
    wa_lab = text_img([("WhatsApp", font("SemiBold", 25), (255, 255, 255), 0)], 40, pad=0)
    badge = Image.new("RGBA", (wa_lab.width + 36, 48), (0, 0, 0, 0))
    ImageDraw.Draw(badge).rounded_rectangle((0, 0, badge.width - 1, 47), radius=24, fill=(37, 190, 95))
    badge.alpha_composite(wa_lab, (18, 4))
    num = text_img([(TEL, font("Bold", 46), BROWN, 1)], 64)
    T.append(("wa", fit(hstack([badge, num], 14, 66), 860), 540, 1404, 10.80))

    # Localisation (repère dessiné)
    pin = Image.new("RGBA", (34, 46), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pin)
    pd.ellipse((2, 2, 32, 32), fill=ORANGE)
    pd.polygon([(6, 24), (28, 24), (17, 45)], fill=ORANGE)
    pd.ellipse((11, 11, 23, 23), fill=CREAM)
    loc = text_img([("Localisation : ", font("Medium", 31), BROWN, 0), (LIEU, font("SemiBold", 31), BROWN, 0)], 50)
    T.append(("loc", fit(hstack([pin, loc], 8, 52), 860), 540, 1482, 11.05))

    liv = text_img([(LIVRAISON[0] + " ", font("SemiBold", 28), ORANGE, 0), (LIVRAISON[1], font("Medium", 28), BROWN, 0)], 46)
    T.append(("liv", fit(liv, 880), 540, 1542, 11.25))
    return T


# ----------------------------------------------------------------------------- outils de composition
def to_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def studio(t, zoom=1.0, dx=0.0, beam_shift=0.0):
    base = A["studio"]
    bh, bw = base.shape[:2]
    cw, ch = W / zoom * 1.0, H / zoom * 1.0
    cx, cy = bw / 2 + dx, bh / 2
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    # recadrage sous-pixel via PIL
    img = Image.fromarray(base.astype(np.uint8)).resize((W, H), Image.BILINEAR, box=box)
    arr = np.asarray(img, np.float32)
    beams = A["beams"]
    off = int(140 + 60 * math.sin(t * 0.35) + beam_shift)
    b = beams[: H, off: off + W]
    if b.shape[0] < H:
        b = np.pad(b, ((0, H - b.shape[0]), (0, 0), (0, 0)))
    arr = arr + b * np.array([26, 22, 16], np.float32)
    return arr


def place(canvas, sprite, cx, cy, width, alpha=1.0, rot=0.0, blur=0.0, sharpen=False, anchor="center"):
    if alpha <= 0.003 or width < 2:
        return
    h = max(2, round(sprite.height * width / sprite.width))
    s = sprite.resize((max(2, round(width)), h), Image.LANCZOS if width < sprite.width * 1.5 else Image.BICUBIC)
    if sharpen:
        s = s.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2))
    if rot:
        s = s.rotate(rot, resample=Image.BICUBIC, expand=True)
    if blur > 0.3:
        pad = int(blur * 3)
        big = Image.new("RGBA", (s.width + 2 * pad, s.height + 2 * pad), (0, 0, 0, 0))
        big.paste(s, (pad, pad))
        s = big.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1:
        s.putalpha(s.split()[3].point(lambda v: int(v * alpha)))
    x = round(cx - s.width / 2)
    y = round(cy - s.height / 2) if anchor == "center" else round(cy - s.height)
    canvas.alpha_composite(s, (x, y)) if 0 <= x and 0 <= y and x + s.width <= canvas.width and y + s.height <= canvas.height \
        else paste_clipped(canvas, s, x, y)


def paste_clipped(canvas, s, x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.width, x + s.width), min(canvas.height, y + s.height)
    if x1 <= x0 or y1 <= y0:
        return
    canvas.alpha_composite(s.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def shine(sprite, pos, width=0.18, strength=0.55, angle=0.35):
    """Reflet lumineux diagonal qui balaie un calque (pos 0 -> 1)."""
    arr = np.asarray(sprite, np.float32).copy()
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx / w) + angle * (yy / h)
    c = lerp(-0.4, 1.4, pos)
    band = np.exp(-((u - c) / width) ** 2) * strength
    arr[..., :3] += band[..., None] * (255 - arr[..., :3])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def pot_shadow(canvas, cx, bottom, width, alpha=1.0):
    s = A["shadow"].resize((round(width * 1.25), round(width * 0.30)), Image.BILINEAR)
    s = s.point(lambda v: int(v * 0.55 * alpha))
    layer = Image.new("RGBA", s.size, (70, 40, 20, 0))
    layer.putalpha(s)
    paste_clipped(canvas, layer, round(cx - s.width / 2), round(bottom - s.height * 0.62))


def finish(arr, t, warm=0.0):
    arr = arr * A["vignette"]
    if warm:
        arr = arr * np.array([1 + 0.03 * warm, 1.0, 1 - 0.05 * warm], np.float32)
    arr = arr + A["grain"][int(t * FPS) % len(A["grain"])]
    return arr


# ----------------------------------------------------------------------------- flocons
class Flake:
    def __init__(self, sprite, x, y, size, rot0, vrot, blur, front, vx=0.0, vy=0.0, bob=0.0, phase=0.0, t0=0.0, g=0.0):
        self.__dict__.update(locals())

    def draw(self, canvas, t, alpha=1.0, ox=0.0, oy=0.0):
        dt = t - self.t0
        if dt < 0:
            return
        x = self.x + self.vx * dt + ox + self.bob * 0.4 * math.sin(1.3 * t + self.phase)
        y = self.y + self.vy * dt + 0.5 * self.g * dt * dt + oy + self.bob * math.sin(1.7 * t + self.phase)
        place(canvas, A[self.sprite], x, y, self.size, alpha, self.rot0 + self.vrot * dt, self.blur)


def flakes_s1():
    r = np.random.default_rng(3)
    F = []
    spots = [(170, 520), (900, 470), (250, 860), (840, 820), (130, 1180), (960, 1150), (420, 380), (690, 330), (560, 260)]
    for i, (x, y) in enumerate(spots):
        F.append(Flake("flocon_a" if i % 2 == 0 else "flocon_b", x, y, r.uniform(48, 80), r.uniform(0, 360),
                       r.uniform(-25, 25), r.uniform(0.6, 1.6), False, vx=r.uniform(-8, 8), vy=r.uniform(-14, -4),
                       bob=r.uniform(8, 16), phase=r.uniform(0, 6)))
    for x, y, s, b in [(80, 1540, 230, 9), (1010, 300, 190, 7), (980, 1680, 170, 6)]:
        F.append(Flake("flocon_a", x, y, s, r.uniform(0, 360), r.uniform(-12, 12), b, True, vx=r.uniform(-6, 6),
                       vy=-10, bob=10, phase=r.uniform(0, 6)))
    return F


def flakes_fall(seed, n_back, n_front, t_start, t_end, xs=(80, 1000)):
    r = np.random.default_rng(seed)
    F = []
    for i in range(n_back + n_front):
        front = i >= n_back
        F.append(Flake("flocon_a" if r.random() < 0.6 else "flocon_b", r.uniform(*xs), r.uniform(-260, -80),
                       r.uniform(150, 230) if front else r.uniform(46, 84), r.uniform(0, 360), r.uniform(-90, 90),
                       r.uniform(5, 8) if front else r.uniform(0.4, 1.4), front, vx=r.uniform(-25, 25),
                       vy=r.uniform(260, 380), bob=0, t0=r.uniform(t_start, t_end), g=120))
    return F


FL1 = flakes_s1()
FL2 = flakes_fall(11, 9, 2, 2.9, 5.4)
FL3 = flakes_fall(23, 0, 3, 6.0, 9.0, xs=(60, 260))


# ----------------------------------------------------------------------------- scènes
def scene1(t):
    """0-3 s : révélation du pot dans un studio lumineux, céréales en suspension."""
    push = lerp(1.0, 1.05, smooth(prog(t, 0, 3.2))) + 0.10 * smooth(prog(t, 2.8, 3.2)) ** 2
    canvas = to_img(studio(t, zoom=push))
    a_in = ease_out(prog(t, 0.0, 0.7))
    k = lerp(0.93, 1.0, ease_out(prog(t, 0, 1.0))) * push
    width = 740 * k
    cx, bottom = 540, 1440 + (1440 - 960) * (push - 1) + lerp(80, 0, ease_out(prog(t, 0, 1.0)))
    for f in FL1:
        if not f.front:
            f.draw(canvas, t, alpha=a_in)
    pot_shadow(canvas, cx, bottom - 18 * k, width, a_in)
    place(canvas, A["pot"], cx, bottom, width, a_in, anchor="bottom", sharpen=True)
    lw = 340 * push
    place(canvas, A["logo"], 540, 300 - 40 * (push - 1) * 4, lw, ease_out(prog(t, 0.5, 1.2)))
    for f in FL1:
        if f.front:
            f.draw(canvas, t, alpha=a_in)
    return finish(np.asarray(canvas.convert("RGB"), np.float32), t)


def scene2(t):
    """3-6 s : gros plan, mouvement circulaire autour du pot, céréales qui retombent."""
    x = smooth(prog(t, 2.85, 6.15))
    canvas = to_img(studio(t, zoom=1.12, dx=lerp(-70, 70, x), beam_shift=lerp(-60, 60, x)))
    for f in FL2:
        if not f.front:
            f.draw(canvas, t)
    width = lerp(1420, 1500, x)
    pot = shine(A["pot"], lerp(1.0, 0.0, x), width=0.16, strength=0.22)
    cx = lerp(540 + 120, 540 - 120, x)
    top = lerp(190, 170, x)
    h = A["pot"].height * width / A["pot"].width
    pot_shadow(canvas, cx, top + h - 30, width)
    place(canvas, pot, cx, top + h, width, rot=lerp(1.4, -1.4, x), anchor="bottom", sharpen=True)
    for f in FL2:
        if f.front:
            f.draw(canvas, t)
    return finish(np.asarray(canvas.convert("RGB"), np.float32), t)


def scene3(t):
    """6-10 s : travelling sur la table de dégustation (décor de l'affiche)."""
    x = smooth(prog(t, 5.85, 10.15))
    src = A["decor_table"]
    z = lerp(1.04, 1.13, x)
    s = H / src.height * z
    cw, ch = W / s, H / s
    cx, cy = lerp(430, 600, x), lerp(700, 770, x)
    cx = clamp(cx, cw / 2, src.width - cw / 2)
    cy = clamp(cy, ch / 2, src.height - ch / 2)
    img = src.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=45, threshold=2)).convert("RGBA")
    for f in FL3:
        f.draw(img, t, alpha=0.9)
    return finish(np.asarray(img.convert("RGB"), np.float32), t, warm=1.0)


def scene4(t):
    """10-15 s : plan final centré, logo, informations de commande, effet lumineux."""
    canvas = to_img(studio(t, zoom=lerp(1.06, 1.0, ease_out(prog(t, 9.85, 11.5)))))
    k = lerp(1.06, 1.0, ease_out(prog(t, 9.85, 11.0)))
    width = 470 * k
    bottom = 1268
    a_pot = ease_out(prog(t, 9.85, 10.3))
    glow = smooth(prog(t, 13.4, 14.2))
    pot = A["pot"]
    if glow > 0:
        pot = shine(pot, prog(t, 13.5, 14.5), width=0.20, strength=0.30)
    pot_shadow(canvas, 540, bottom - 10, width, a_pot)
    place(canvas, pot, 540, bottom, width, a_pot, anchor="bottom")
    sweep = prog(t, 13.6, 14.6)
    for name, img, cx, top, t0 in A["texts"]:
        a = ease_out(prog(t, t0, t0 + 0.45))
        if a <= 0:
            continue
        if name in ("logo", "titre") and 0 < sweep < 1:
            img = shine(img, sweep, width=0.12, strength=0.45)
        rise = lerp(18, 0, a)
        place(canvas, img, cx, top + img.height / 2 + rise, img.width, a)
    arr = np.asarray(canvas.convert("RGB"), np.float32)
    # léger halo lumineux final
    if glow > 0:
        yy = np.linspace(-1, 1, H, dtype=np.float32)[:, None]
        xx = np.linspace(-1, 1, W, dtype=np.float32)[None, :]
        halo = np.exp(-((xx / 0.55) ** 2 + ((yy + 0.05) / 0.35) ** 2)) * glow * 0.06
        arr = arr + halo[..., None] * (255 - arr)
    return finish(arr, t)


# (début, fin, scène) — les plans se chevauchent pour les fondus enchaînés
SCENES = [(0.0, 3.1, scene1), (2.9, 6.1, scene2), (5.9, 10.1, scene3), (9.85, 15.0, scene4)]


def frame(i):
    t = i / FPS
    act = [(a, b, f) for a, b, f in SCENES if a <= t < b + 1e-6]
    if len(act) == 1:
        out = act[0][2](t)
    else:
        # transition « flash lumineux » crème : jamais deux pots superposés
        (a0, b0, f0), (a1, b1, f1) = act[0], act[1]
        m = clamp((t - a1) / (b0 - a1))
        w = 0.92 * math.sin(math.pi * m)
        out = (f0(t) if m < 0.5 else f1(t)) * (1 - w) + np.array(FLASH, np.float32) * w
    return np.clip(out, 0, 255).astype(np.uint8).tobytes()


def render_video(path):
    load()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, buf in enumerate(pool.imap(frame, range(NF), chunksize=4)):
            p.stdin.write(buf)
            if i % 60 == 0:
                print(f"  image {i}/{NF}", flush=True)
    p.stdin.close()
    p.wait()


# ----------------------------------------------------------------------------- voix off
def tts_edge(text, dst):
    """Voix neuronale Microsoft (edge-tts) : naturelle, expressive, ton publicitaire."""
    import asyncio
    import ssl

    import edge_tts
    import edge_tts.communicate as ec

    ca = "/root/.ccr/ca-bundle.crt"  # proxy de l'environnement cloud, ignoré ailleurs
    if os.path.exists(ca):
        ec._SSL_CTX = ssl.create_default_context(cafile=ca)
    # le service renvoie parfois un flux tronqué : on recommence tant que la durée est anormale
    for _ in range(4):
        asyncio.run(edge_tts.Communicate(text, VOICE_NAME, rate=VOICE_RATE, pitch=VOICE_PITCH).save(dst))
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "csv=p=0", dst]))
        if dur > 0.045 * len(text):
            return
    raise RuntimeError(f"voix incomplète pour : {text}")


def read_wav(path):
    sr, x = wavfile.read(path)
    x = x.astype(np.float32) / 32768.0
    if x.ndim > 1:
        x = x.mean(1)
    return sr, x


def build_voice(tmp):
    """Une phrase = un fichier ; nettoyage des silences, tempo, puis 48 kHz."""
    os.makedirs(VOIX, exist_ok=True)
    clips = []
    for i, line in enumerate(VOICE_LINES, 1):
        dst = os.path.join(VOIX, f"phrase_{i}.wav")
        if not os.path.exists(dst):
            mp3 = os.path.join(tmp, f"raw{i}.mp3")
            tts_edge(line, mp3)
            raw = os.path.join(tmp, f"raw{i}.wav")
            run(["ffmpeg", "-y", "-i", mp3, "-ac", "1", raw])
            sr, x = read_wav(raw)
            nz = np.where(np.abs(x) > 0.01)[0]
            x = x[max(0, nz[0] - int(0.02 * sr)): nz[-1] + int(0.06 * sr)]
            trimmed = os.path.join(tmp, f"trim{i}.wav")
            wavfile.write(trimmed, sr, (x * 32767).astype(np.int16))
            run(["ffmpeg", "-y", "-i", trimmed, "-af",
                 f"atempo={VOICE_TEMPO},highpass=f=80,equalizer=f=180:t=q:w=1:g=1.5,"
                 "equalizer=f=4500:t=q:w=1.5:g=1.5,acompressor=threshold=-18dB:ratio=2.5:attack=5:release=120:makeup=1.5",
                 "-ar", str(SR), "-ac", "1", dst])
        clips.append(read_wav(dst)[1])
    track = np.zeros(int(DUR * SR), np.float32)
    t = VOICE_START
    starts = []
    for c in clips:
        s = int(t * SR)
        n = min(len(c), len(track) - s)
        track[s:s + n] += c[:n]
        starts.append((round(t, 2), round(t + len(c) / SR, 2)))
        t += len(c) / SR + VOICE_GAP
    print("  voix :", starts)
    if t - VOICE_GAP > DUR:
        print("  ATTENTION : la voix dépasse 15 s")
    return track / (np.abs(track).max() + 1e-9) * 0.9


# ----------------------------------------------------------------------------- musique & bruitages
def env_ar(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def put(buf, x, at):
    s = int(at * SR)
    if s >= len(buf):
        return
    n = min(len(x), len(buf) - s)
    buf[s:s + n] += x[:n]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def music():
    """Musique originale, joyeuse et gourmande : 112 BPM, fa majeur, 7 mesures = 15 s."""
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / 112
    rng = np.random.default_rng(5)
    # F  C  Dm  Bb  F  C  F
    chords = [[53, 57, 60, 65], [48, 55, 60, 64], [50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65],
              [48, 55, 60, 64], [53, 57, 60, 65]]
    for bar, ch in enumerate(chords):
        t0 = bar * 4 * beat
        last = bar == len(chords) - 1
        d = (4 * beat if not last else DUR - t0) + 0.3
        tt = np.arange(int(d * SR)) / SR
        # nappe douce
        pad = sum(np.sin(2 * np.pi * hz(m + 12) * tt) + 0.25 * np.sin(4 * np.pi * hz(m + 12) * tt) for m in ch[1:])
        put(out, (pad * env_ar(len(tt), 0.35, 0.5) * 0.020).astype(np.float32), t0)
        # basse
        for b in ([0, 1.5, 2, 3] if not last else [0]):
            dd = 0.45 if not last else 1.6
            tb = np.arange(int(dd * SR)) / SR
            f = hz(ch[0] - 12)
            x = np.tanh(1.6 * np.sin(2 * np.pi * f * tb)) * np.exp(-tb * (5 if not last else 1.6))
            put(out, (x * 0.09).astype(np.float32), t0 + b * beat)
        # arpège type marimba (croches)
        arp = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[2] + 24, ch[3] + 12, ch[2] + 12, ch[1] + 12]
        for k, m in enumerate(arp if not last else arp[:5]):
            tm = np.arange(int(0.5 * SR)) / SR
            f = hz(m)
            x = (np.sin(2 * np.pi * f * tm) * np.exp(-tm * 9) + 0.35 * np.sin(2 * np.pi * 4 * f * tm) * np.exp(-tm * 30))
            put(out, (x * 0.055 * (1 - 0.15 * (k % 2))).astype(np.float32), t0 + k * beat / 2)
        # batterie (à partir de la 2e mesure, s'arrête à la dernière)
        if 1 <= bar < len(chords) - 1:
            for b in range(4):
                tb = t0 + b * beat
                if b in (0, 2):
                    tk = np.arange(int(0.28 * SR)) / SR
                    ph = 2 * np.pi * np.cumsum(50 + 90 * np.exp(-tk * 28)) / SR
                    put(out, (np.sin(ph) * np.exp(-tk * 11) * 0.22).astype(np.float32), tb)
                else:
                    clap = np.zeros(int(0.2 * SR), np.float32)
                    for j, o in enumerate((0, 0.011, 0.022)):
                        nn = rng.normal(0, 1, int(0.12 * SR)) * np.exp(-np.arange(int(0.12 * SR)) / SR * (60 if j < 2 else 22))
                        clap[int(o * SR): int(o * SR) + len(nn)] += nn[: len(clap) - int(o * SR)]
                    put(out, (bandpass(clap, 900, 3500) * 0.10).astype(np.float32), tb)
            if bar >= 2:
                for s16 in range(16):
                    nn = rng.normal(0, 1, int(0.05 * SR)) * np.exp(-np.arange(int(0.05 * SR)) / SR * 70)
                    put(out, (bandpass(nn, 6000, 12000) * (0.025 if s16 % 2 else 0.04)).astype(np.float32),
                        t0 + s16 * beat / 4)
    fade = np.ones(n, np.float32)
    fade[: int(0.15 * SR)] = np.linspace(0, 1, int(0.15 * SR))
    fade[-int(0.5 * SR):] = np.linspace(1, 0, int(0.5 * SR))
    return out * fade


def whoosh(d=0.6):
    rng = np.random.default_rng(9)
    nn = rng.normal(0, 1, int(d * SR)).astype(np.float32)
    out = np.zeros_like(nn)
    seg = int(0.03 * SR)
    for i in range(0, len(nn), seg):
        p = i / len(nn)
        fc = 400 + 3200 * math.sin(math.pi * p)
        out[i:i + seg] = bandpass(nn[max(0, i - seg):i + seg], fc * 0.6, min(fc * 1.6, 15000))[-len(nn[i:i + seg]):]
    e = np.sin(np.pi * np.linspace(0, 1, len(nn))) ** 2
    return out * e * 0.10


def chime(notes, step=0.07, amp=0.05, decay=4.0):
    out = np.zeros(int((len(notes) * step + 1.4) * SR), np.float32)
    for k, m in enumerate(notes):
        tm = np.arange(int(1.2 * SR)) / SR
        f = hz(m)
        x = (np.sin(2 * np.pi * f * tm) + 0.3 * np.sin(2 * np.pi * 2.76 * f * tm) * np.exp(-tm * 8)) * np.exp(-tm * decay)
        put(out, (x * amp).astype(np.float32), k * step)
    return out


def sfx():
    out = np.zeros(int(DUR * SR), np.float32)
    put(out, chime([77, 81, 84, 89], 0.06, 0.035), 0.12)      # apparition du pot
    for tt in (2.72, 5.72, 9.72):                              # transitions
        put(out, whoosh(), tt)
    put(out, chime([89], 0.0, 0.018, 9), 10.55)               # bouton « Commandez »
    put(out, chime([84, 89, 93, 96, 101], 0.05, 0.03), 13.6)  # éclat lumineux final
    return out


def build_audio(path, tmp):
    voice = build_voice(tmp)
    mus = music()
    # ducking : la musique baisse d'environ 8 dB quand la voix parle
    env = np.abs(voice)
    win = int(0.12 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    duck = 1 - 0.6 * np.clip(env / 0.05, 0, 1)
    duck = np.convolve(duck, np.ones(int(0.08 * SR)) / int(0.08 * SR), mode="same")
    mix = voice * 1.0 + mus * 0.55 * duck + sfx() * 0.8
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    raw = os.path.join(tmp, "mix.wav")
    wavfile.write(raw, SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
    run(["ffmpeg", "-y", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", str(SR), path])


# ----------------------------------------------------------------------------- main
def main():
    build_assets()
    tmp = tempfile.mkdtemp(prefix="cio_")
    wav = os.path.join(tmp, "audio.wav")
    vid = os.path.join(tmp, "video.mp4")
    print("Audio…")
    build_audio(wav, tmp)
    print("Vidéo…")
    render_video(vid)
    run(["ffmpeg", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-t", str(DUR), "-movflags", "+faststart", OUT])
    print("OK ->", OUT)


if __name__ == "__main__":
    main()
