"""Empty white room: keep the real walls/ceiling/floor lighting, remove objects, repaint white.
Writes bg/NNNN.png (16-bit BGR, painted room without the person) for each frame."""
import sys, os, numpy as np, cv2

W, H = 1024, 576
WALL, CEIL, FLOOR = 0, 5, 3
TINT = np.array([0.875, 0.948, 1.0], np.float32)      # BGR: white paint under the warm lamp (from the grey hoodie)
GAIN = float(os.environ.get('BG_GAIN', '1.75'))      # white paint vs beige paint albedo (constant over the clip)

def pushpull(x, w, eps=1e-9):
    """fill x where w~0 from surrounding weighted samples (multi-scale). x: HxW or HxWxC, w: HxW"""
    xs, ws = [x * (w[..., None] if x.ndim == 3 else w)], [w]
    while min(ws[-1].shape) > 2:
        ws.append(cv2.resize(ws[-1], (max(1, ws[-1].shape[1] // 2), max(1, ws[-1].shape[0] // 2)), interpolation=cv2.INTER_AREA))
        xs.append(cv2.resize(xs[-1], (ws[-1].shape[1], ws[-1].shape[0]), interpolation=cv2.INTER_AREA))
    est = xs[-1] / (ws[-1][..., None] if x.ndim == 3 else ws[-1]).clip(eps)
    wl0 = ws[-1][..., None] if x.ndim == 3 else ws[-1]
    gmean = xs[-1].sum(axis=(0, 1)) / max(float(ws[-1].sum()), eps)
    est = np.where(wl0 > 1e-6, est, gmean).astype(np.float32)
    for l in range(len(ws) - 2, -1, -1):
        up = cv2.resize(est, (ws[l].shape[1], ws[l].shape[0]), interpolation=cv2.INTER_LINEAR)
        wl = ws[l][..., None] if x.ndim == 3 else ws[l]
        own = xs[l] / wl.clip(eps)
        c = np.clip(wl / 0.25, 0, 1)
        est = own * c + up * (1 - c)
    return est

def masked_blur(x, R, sig):
    Rf = R.astype(np.float32)
    return cv2.GaussianBlur(x * Rf, (0, 0), sig) / cv2.GaussianBlur(Rf, (0, 0), sig).clip(1e-3)

CORNERS = []
def corner_lines(Ld, w, inD):
    # long near-vertical luminance steps with clean wall on both sides = a corner between two walls
    bar = np.zeros(Ld.shape, np.uint8)
    e = cv2.Canny((cv2.GaussianBlur(Ld, (0, 0), 2) * 255).astype(np.uint8), 6, 16)
    ww = (w > 0).astype(np.uint8)
    both = cv2.erode(ww, np.ones((1, 9), np.uint8))  # placeholder, refined below
    left = cv2.warpAffine(ww, np.float32([[1, 0, 8], [0, 1, 0]]), (Ld.shape[1], Ld.shape[0]))
    right = cv2.warpAffine(ww, np.float32([[1, 0, -8], [0, 1, 0]]), (Ld.shape[1], Ld.shape[0]))
    e = e * (left & right)
    ls = cv2.HoughLinesP(e, 1, np.pi / 360, 60, minLineLength=140, maxLineGap=25)
    CORNERS.clear()
    if ls is None: return bar
    for x1, y1, x2, y2 in ls[:, 0]:
        ang = np.degrees(np.arctan2(abs(x2 - x1), abs(y2 - y1)))
        if ang > 25: continue
        # require a real brightness step across the line
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        L1 = Ld[int(my), int(np.clip(mx - 10, 0, Ld.shape[1] - 1))]; L2 = Ld[int(my), int(np.clip(mx + 10, 0, Ld.shape[1] - 1))]
        if abs(L1 - L2) / max(L1, L2) < 0.04: continue
        # extend the line across the whole wall height
        dx = (x2 - x1) / max(y2 - y1, 1e-3) if y2 != y1 else 0
        X1 = int(x1 - dx * y1); X2 = int(x1 + dx * (Ld.shape[0] - y1))
        cv2.line(bar, (X1, 0), (X2, Ld.shape[0]), 1, 3); CORNERS.append((X1, X2))
    return bar * inD

def shoulder(x, knee=0.80, top=0.965):
    # soft highlight roll-off so the white never clips flat
    y = x.copy(); m = x > knee
    y[m] = knee + (top - knee) * (1 - np.exp(-(x[m] - knee) / (top - knee)))
    return y

def domains(k):
    p = np.load(f'seg/{k:04d}_p.npy').astype(np.float32)          # wall, ceiling, floor
    p = np.stack([cv2.GaussianBlur(c, (0, 0), 6) for c in p])
    d = p.argmax(0).astype(np.uint8)
    d = cv2.medianBlur(d, 31)
    d[d == 2] = 0          # floor folded into the white seamless wall
    # a ceiling must touch the top of the frame; anything else labelled ceiling is wall
    n, lab = cv2.connectedComponents((d == 1).astype(np.uint8))
    for c in range(1, n):
        R = lab == c
        if not R[:8].any() or R.sum() < 3000: d[R] = 0
    return d                                                        # 0 wall, 1 ceiling, 2 floor

def build(k):
    I = cv2.imread(f'src/{k:04d}.png').astype(np.float32) / 255
    L = I.mean(2)
    lab = cv2.imread(f'seg/{k:04d}.png', 0)
    a = cv2.imread(f'alpha_fix/{k:04d}.png', -1).astype(np.float32) / 65535
    person = cv2.dilate((a > 0.02).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    dom = domains(k)
    if ((dom == 1) & (lab == CEIL) & ~person).sum() < 1500: dom[dom == 1] = 0
    shad = cv2.dilate(cv2.imread(f'shadow2/{k:04d}.png', -1).astype(np.float32) / 65535, np.ones((15, 15), np.uint8))
    Ld = cv2.bilateralFilter(L, 7, 0.04, 5)
    chro = I / (L[..., None] + 1e-4)
    gx = cv2.Sobel(Ld, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(Ld, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.sqrt(gx * gx + gy * gy)
    out = np.zeros((H, W, 3), np.float32)
    clean_all = np.zeros((H, W), np.float32)
    levels = {}
    for di, labid in ((0, WALL), (1, CEIL)):
        inD = dom == di
        if inD.sum() < 500: continue
        cand = inD & (np.isin(lab, [WALL, FLOOR]) if di == 0 else (lab == labid)) & ~person & (shad < 0.03)
        Lp = np.where(cand, Ld, 0).astype(np.float32)
        up = cv2.GaussianBlur(cv2.dilate(Lp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35))), (0, 0), 12)
        devup = (up - Ld) / (up + 1e-3)
        cand = cand & (devup < (0.10 if di != 1 else 0.45))
        if di != 1 and cand.sum() > 1000:
            cand = cand & (Ld > 0.58 * np.median(Ld[cand]))
        w = cand.astype(np.float32)
        for it in range(4):
            M = cv2.GaussianBlur(pushpull(Ld, w), (0, 0), 10)
            Cm = cv2.GaussianBlur(pushpull(chro, w), (0, 0), 14)
            dev = np.abs(Ld - M) / (M + 1e-3)
            cdev = np.abs(chro - Cm).max(2)
            Mbig = cv2.GaussianBlur(pushpull(Ld, w), (0, 0), 60)
            ok = cand & (Ld > (0.85 if di != 1 else 0.5) * Mbig) & (dev < (0.09 if di != 1 else 0.30)) & (cdev < 0.10) & (grad < 0.10)
            ok = cv2.erode(ok.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0     # keep away from object edges
            w = ok.astype(np.float32)
        soft = cv2.GaussianBlur(w, (0, 0), 2.0)
        if di == 1:   # ceiling: repaint white, drop the wood texture, keep its light gradient
            Lr = cv2.GaussianBlur(pushpull(Ld, w), (0, 0), 25)
        else:
            # a plain painted wall carries only light: smooth illumination fitted on clean wall pixels,
            # fitted separately on each side of real wall corners so the room keeps its edges
            bar = corner_lines(Ld, w, inD)
            reg = (inD & (bar == 0)).astype(np.uint8)
            n, labr = cv2.connectedComponents(reg)
            Lr = np.zeros_like(Ld); acc = np.zeros_like(Ld)
            for r in range(1, n):
                R = labr == r
                if R.sum() < 400: continue
                wr = w * R
                if wr.sum() < 200: continue
                Rf = cv2.GaussianBlur(R.astype(np.float32), (0, 0), 1.0)
                Lr += masked_blur(pushpull(Ld, wr), R, 16) * Rf; acc += Rf
            Lr = np.where(acc > 1e-3, Lr / acc.clip(1e-3), cv2.GaussianBlur(pushpull(Ld, w), (0, 0), 16))
        levels[di] = (Lr, inD, w)
        clean_all += soft * inD
    # wall paint level; ceiling painted the same white, sitting a touch darker than the wall at the junction
    for di, (Lr, inD, w) in levels.items():
        if di == 0:
            col = shoulder(Lr * GAIN)[..., None] * TINT
        elif di == 1:
            ref = np.median(levels[0][0][levels[0][1]]) if 0 in levels else 0.45
            col = shoulder(Lr / (np.median(Lr[inD]) + 1e-3) * ref * GAIN * 0.86)[..., None] * TINT
        else:   # floor keeps its own colour, objects removed
            col = pushpull(cv2.GaussianBlur(I, (0, 0), 1), w)
            col = np.where(w[..., None] > 0.5, I, col)
        out += col * cv2.GaussianBlur(inD.astype(np.float32), (0, 0), 1.2)[..., None]
    norm = sum(cv2.GaussianBlur((dom == d).astype(np.float32), (0, 0), 1.2) for d in levels)
    out /= norm[..., None].clip(1e-3)
    return np.clip(out, 0, 1), clean_all

if __name__ == '__main__':
    os.makedirs('bg', exist_ok=True)
    frames = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else range(1, 346)
    for k in frames:
        if not os.path.exists(f'seg/{k:04d}_p.npy'): print('noseg', k); continue
        b, cl = build(k)
        cv2.imwrite(f'bg/{k:04d}.png', (b * 65535).astype(np.uint16))
        print(k, flush=True)
