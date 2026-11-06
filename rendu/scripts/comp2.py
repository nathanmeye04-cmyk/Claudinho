import glob, os, sys, numpy as np, cv2
from pymatting import estimate_foreground_ml

W, H = 1024, 576
fs = sorted(glob.glob('src/*.png')); N = len(fs)
OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
frames = range(N) if len(sys.argv) <= 2 else [int(x) for x in sys.argv[2].split(',')]
os.makedirs(OUT, exist_ok=True)

# ---------- camera: compose frame-to-frame similarity -> world(frame0) to frame i
Ms = np.load('motion.npy')
C = [np.eye(3)]
for i in range(1, N): C.append(Ms[i] @ C[-1])
C = np.array(C)
# light temporal smoothing of the camera path is NOT applied: the plate must stick to real shake

# world bounds
corners = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1]], float).T
pts = np.hstack([(np.linalg.inv(c) @ corners)[:2] for c in C])
M = 200
x0, y0 = pts[0].min() - M, pts[1].min() - M
x1, y1 = pts[0].max() + M, pts[1].max() + M
PW, PH = int(x1 - x0), int(y1 - y0)
T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])  # world -> plate px

def load_alpha(i):
    p = fs[i].replace('src', 'alpha_fix')
    a = cv2.imread(p, -1)
    return None if a is None else a.astype(np.float32) / 65535

# subject centroid in world coords -> where the light pool sits
cx, cy, n = 0, 0, 0
for i in range(0, N, 10):
    a = load_alpha(i)
    if a is None: a = cv2.imread(fs[i].replace('src', 'u2m'), 0) / 255.
    ys, xs = np.nonzero(a > .5)
    if len(xs) == 0: continue
    w = np.linalg.inv(C[i]) @ np.array([xs.mean(), ys.mean(), 1])
    cx += w[0]; cy += w[1]; n += 1
cx, cy = cx / n - x0, cy / n - y0

# ---------- plate (world space, low frequency only, linear-ish float 0..1)
rng = np.random.default_rng(7)
yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
# main soft light pool behind subject, slightly above and to camera-left (key comes from left)
pool = np.exp(-(((xx - (cx - 120)) / 1500) ** 2 + ((yy - (cy - 220)) / 750) ** 2))
# gentle vertical falloff (top darker like a ceiling falloff, bottom slightly darker too)
vert = 1 - 0.10 * np.clip((cy - 300 - yy) / 600, 0, 1) - 0.05 * np.clip((yy - cy - 250) / 500, 0, 1)
# very subtle large-scale non-uniformity of a painted/paper wall
nz = rng.standard_normal((PH // 32 + 2, PW // 32 + 2)).astype(np.float32)
nz = cv2.GaussianBlur(cv2.resize(nz, (PW, PH), interpolation=cv2.INTER_CUBIC), (0, 0), 140)
nz /= nz.std() + 1e-6
lum = (0.72 + 0.20 * pool) * vert * (1 + 0.012 * nz)
tint = np.array([0.905, 0.958, 1.0], np.float32)  # BGR: warm off-white matching tungsten key
plate = (lum[..., None] * tint).astype(np.float32)

# ---------- exposure tracking: follow camera auto-exposure through subject luminance
expo = np.ones(N, np.float32)
lums = []
for i in range(N):
    a = load_alpha(i)
    if a is None: a = cv2.imread(fs[i].replace('src', 'u2m'), 0) / 255.
    im = cv2.imread(fs[i]).astype(np.float32).mean(2)
    m = a > .9
    lums.append(im[m].mean() if m.sum() > 2000 else np.nan)
lums = np.array(lums); good = ~np.isnan(lums)
lums = np.interp(np.arange(N), np.nonzero(good)[0], lums[good])
k = 31; ker = np.hanning(k); ker /= ker.sum()
sm = np.convolve(np.pad(lums, k // 2, mode='edge'), ker, 'valid')
expo = np.ones(N, np.float32)  # content-driven luminance is not camera exposure: keep wall exposure fixed

gray = lambda i: cv2.cvtColor(cv2.imread(fs[i]), cv2.COLOR_BGR2GRAY)

def warp_to(i, j, a_j):
    """warp alpha of frame j onto frame i using dense flow i->j"""
    gi, gj = gray(i), gray(j)
    fl = cv2.calcOpticalFlowFarneback(gi, gj, None, 0.5, 4, 21, 5, 7, 1.5, 0)
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    mx, my = gx + fl[..., 0], gy + fl[..., 1]
    aw = cv2.remap(a_j, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    iw = cv2.remap(gj.astype(np.float32), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    err = np.abs(iw - gi.astype(np.float32))
    conf = np.exp(-(cv2.GaussianBlur(err, (0, 0), 2) / 6) ** 2)
    return aw, conf

def grade_fg(F):
    # discreet: tame warm cast ~20%, small exposure lift with protected blacks
    F = F.copy()
    b, g, r = F[..., 0], F[..., 1], F[..., 2]
    l = (b + g + r) / 3
    F[..., 0] = b + 0.10 * (l - b)
    F[..., 2] = r + 0.10 * (l - r)
    F = np.clip(F, 0, 1)
    F = 1 - (1 - F) ** 1.06          # gentle global lift, no local retouch
    return F

grain_rng = np.random.default_rng(123)

for i in frames:
    I = cv2.imread(fs[i]).astype(np.float32) / 255
    a = load_alpha(i)
    # temporal stabilization of the matte (motion compensated, no lag)
    acc, wsum = a * 2.0, np.full_like(a, 2.0)
    for j in (i - 1, i + 1):
        if 0 <= j < N:
            aj = load_alpha(j)
            if aj is None: continue
            aw, conf = warp_to(i, j, aj)
            acc += aw * conf; wsum += conf
    a = np.clip(acc / wsum, a - 0.15, a + 0.15)  # temporal filter only steadies edges, never empties the subject
    # tighten soft garbage, keep true edge softness
    a = np.clip((a - 0.02) / 0.96, 0, 1)

    # foreground colour without the old wall bleeding in
    Fe = estimate_foreground_ml(I.astype(np.float64), a.astype(np.float64)).astype(np.float32)
    # original pixels kept wherever the matte is solid; estimated colour only on the soft fringe
    solid = np.clip((a - 0.90) / 0.08, 0, 1)[..., None]
    F = I * solid + Fe * (1 - solid)
    F = grade_fg(F)

    # background: the real room, emptied and repainted white (bg.py), steadied over 5 frames
    def bgload(j):
        return cv2.imread(f'bg/{j + 1:04d}.png', -1).astype(np.float32) / 65535
    B = bgload(i) * 3.0; wsum = 3.0
    for j, wt in ((i - 2, 1.0), (i - 1, 2.0), (i + 1, 2.0), (i + 2, 1.0)):
        if 0 <= j < N:
            Mji = C[i] @ np.linalg.inv(C[j])          # frame j -> frame i
            B += cv2.warpAffine(bgload(j), Mji[:2], (W, H), borderMode=cv2.BORDER_REPLICATE) * wt; wsum += wt
    B /= wsum

    # real shadow of the person, transferred from the original wall (where it is visible)
    S2 = cv2.imread(f'shadow2/{i + 1:04d}.png', -1).astype(np.float32) / 65535
    pres = np.clip(S2.max() / 0.15, 0, 1)
    # elsewhere: very discreet contact shadow (lamp close to camera axis -> shadow mostly hidden)
    sh = cv2.warpAffine(a, np.float32([[1, 0, 30], [0, 1, 12]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
    sh = cv2.GaussianBlur(sh, (0, 0), 30)
    ao = cv2.GaussianBlur(a, (0, 0), 90)
    B *= (1 - 0.85 * S2 - (1 - pres) * 0.12 * sh - 0.06 * ao)[..., None]

    # light wrap: let a touch of the bright wall bleed onto the subject's edge
    Bb = cv2.GaussianBlur(B, (0, 0), 9)
    edge = np.clip(a * (1 - cv2.GaussianBlur(a, (0, 0), 5)) * 2.2, 0, 1)[..., None]
    Fw = F * (1 - 0.22 * edge) + Bb * 0.22 * edge

    out = Fw * a[..., None] + B * (1 - a[..., None])

    # unify with a shared fine grain (matches compressed source texture)
    gn = grain_rng.standard_normal((H, W)).astype(np.float32)
    gn = cv2.GaussianBlur(gn, (0, 0), 0.7) * (1.0 / 255) * 1.6
    out += gn[..., None] * (1 - a[..., None])  # no grain added on the person
    out = np.clip(out, 0, 1)
    cv2.imwrite(f'{OUT}/{i + 1:04d}.png', (out * 255 + 0.5).astype(np.uint8))
    print(i + 1, flush=True)
