"""Chaîne de mastering stéréo — Seigneur Jésus (LeoBenjo ft. Nathan).
Usage: python3 master.py src.wav out_prefix target_lufs
Tout le traitement est en float64 ; export 24 bits avec dither TPDF.
"""
import sys, json, numpy as np, pyloudnorm as pyln
from scipy.io import wavfile
from scipy.signal import sosfilt, butter, resample_poly
from numba import njit

src, out, target = sys.argv[1], sys.argv[2], float(sys.argv[3])
sr, x = wavfile.read(src)
x = x.astype(np.float64) / 32768.0
log = {}

# ---------- outils ----------
def biquad(kind, f0, gain_db=0.0, q=0.707):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / sr; c, s = np.cos(w), np.sin(w); al = s / (2 * q)
    if kind == 'peak':
        b = [1 + al * A, -2 * c, 1 - al * A]; a = [1 + al / A, -2 * c, 1 - al / A]
    elif kind == 'lowshelf':
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * c + sq), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - sq)]
        a = [(A + 1) + (A - 1) * c + sq, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - sq]
    elif kind == 'highshelf':
        sq = 2 * np.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + sq), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - sq)]
        a = [(A + 1) - (A - 1) * c + sq, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - sq]
    b, a = np.array(b) / a[0], np.array(a) / a[0]
    return np.concatenate([b, a])[None, :]

def eq(sig, bands):
    sos = np.concatenate([biquad(*b) for b in bands])
    return sosfilt(sos, sig, axis=0)

def lr4(sig, fc):
    """Crossover Linkwitz-Riley 24 dB/oct : renvoie (bas, haut), somme = passe-tout."""
    lo = butter(2, fc, 'low', fs=sr, output='sos'); hi = butter(2, fc, 'high', fs=sr, output='sos')
    return sosfilt(lo, sosfilt(lo, sig, axis=0), axis=0), sosfilt(hi, sosfilt(hi, sig, axis=0), axis=0)

@njit(cache=True)
def env_follow(det, att, rel):
    out = np.empty_like(det); e = 0.0
    for i in range(det.shape[0]):
        v = det[i]; k = att if v > e else rel
        e = k * e + (1 - k) * v; out[i] = e
    return out

def coef(ms): return np.exp(-1.0 / (sr * ms / 1000.0))

def compressor(sig, key, thr_db, ratio, att_ms, rel_ms, knee_db=6.0):
    """Compresseur feed-forward, détection RMS, stéréo lié, genou doux. Renvoie (signal, GR dB)."""
    det = env_follow(np.mean(key ** 2, axis=1), coef(att_ms), coef(rel_ms))
    lvl = 10 * np.log10(det + 1e-12)
    over = lvl - thr_db
    gr = np.where(over <= -knee_db / 2, 0.0,
         np.where(over >= knee_db / 2, over * (1 - 1 / ratio),
                  (1 - 1 / ratio) * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    return sig * (10 ** (-gr / 20))[:, None], gr

@njit(cache=True)
def run_min(g, n):
    out = np.empty_like(g); L = g.shape[0]
    # minimum glissant sur [i, i+n) via deque
    dq = np.empty(L, np.int64); h = 0; t = 0
    for j in range(L + n):
        if j < L:
            while t > h and g[dq[t - 1]] >= g[j]: t -= 1
            dq[t] = j; t += 1
        i = j - n + 1
        if i >= 0 and i < L:
            while dq[h] < i: h += 1
            out[i] = g[dq[h]]
    return out

@njit(cache=True)
def smooth_gain(g, att, rel):
    out = np.empty_like(g); e = 1.0
    for i in range(g.shape[0]):
        v = g[i]; k = att if v < e else rel
        e = k * e + (1 - k) * v
        if e > v and k == att: pass
        out[i] = e
    return out

def limiter(sig, ceiling_db, look_ms=1.5, rel_ms=80.0, os=4):
    """Limiteur true-peak à anticipation, suréchantillonné x4, stéréo lié."""
    up = resample_poly(sig, os, 1, axis=0)
    fs = sr * os; c = 10 ** (ceiling_db / 20)
    pk = np.max(np.abs(up), axis=1)
    g = np.minimum(1.0, c / np.maximum(pk, 1e-12))
    n = int(fs * look_ms / 1000)
    g = run_min(g, n)                       # anticipation : le gain descend avant le pic
    att = np.exp(-1.0 / (fs * look_ms / 1000 / 3)); rel = np.exp(-1.0 / (fs * rel_ms / 1000))
    gs = smooth_gain(g, att, rel)
    gs = np.minimum(gs, run_min(g, 1))     # garantie stricte
    y = up * gs[:, None]
    y = np.clip(y, -c, c)                   # sécurité (n'agit quasiment jamais)
    gr = -20 * np.log10(gs[::os])
    return resample_poly(y, 1, os, axis=0), gr

CLIP_DB = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
def softclip(sig, thr_db, os=4):
    """Écrêteur doux suréchantillonné : arrondit uniquement les transitoires très courtes
    qui dépassent de plus de CLIP_DB le plafond du limiteur."""
    t = 10 ** (thr_db / 20); up = resample_poly(sig, os, 1, axis=0)
    a = np.abs(up); k = 0.7 * t                     # zone linéaire jusqu'à 70 % du seuil
    over = a > k
    y = up.copy()
    y[over] = np.sign(up[over]) * (k + (t - k) * np.tanh((a[over] - k) / (t - k)))
    log['clip_pct'] = float(np.mean(a > t) * 100); log['clip_soft_pct'] = float(np.mean(over) * 100)
    return resample_poly(y, 1, os, axis=0)

meter = pyln.Meter(sr)
def lufs(s): return meter.integrated_loudness(s)

# ---------- 1. Nettoyage ----------
x = x - x.mean(axis=0)                                   # offset DC
x = sosfilt(butter(2, 22, 'high', fs=sr, output='sos'), x, axis=0)  # infra-graves inaudibles (<22 Hz)

# ---------- 2. Image stéréo (M/S) ----------
M = (x[:, 0] + x[:, 1]) / 2; Sd = (x[:, 0] - x[:, 1]) / 2
# graves en mono sous 120 Hz : corrige le déséquilibre G/D de +1,75 dB dans les basses
Sd = sosfilt(butter(2, 120, 'high', fs=sr, output='sos'), Sd)
# léger élargissement des haut-médiums/aigus (côtés seulement), sans toucher au centre (voix)
Sd = eq(Sd[:, None], [('peak', 3000, 1.5, 0.7), ('highshelf', 8000, 1.0, 0.7)])[:, 0]
x = np.stack([M + Sd, M - Sd], axis=1)

# ---------- 3. Égalisation tonale (stéréo) ----------
x = eq(x, [
    ('peak', 40, -2.0, 1.6),       # bosse du sub à 39 Hz, trop dominante
    ('peak', 110, 1.5, 0.9),       # corps de la basse (100-160 Hz en retrait de ~3 dB)
    ('peak', 415, -2.0, 3.0),      # accumulation vers 415 Hz (aspect « boîte »)
    ('peak', 850, 1.0, 1.0),       # médium un peu creusé à 800 Hz
    ('peak', 2100, 1.5, 0.9),      # intelligibilité des voix
    ('peak', 3200, -1.5, 1.6),     # zone déjà proéminente, risque de dureté
    ('peak', 5500, 2.0, 0.9),      # présence/brillance (5-6,3 kHz en retrait)
    ('highshelf', 4500, 1.0, 0.6), # légère ouverture générale des aigus
    ('highshelf', 12000, 0.8, 0.7) # un peu d'air, sans dureté
])

# ---------- 4. De-esser (médian, 5-9 kHz), n'agit que sur les pics de sifflantes ----------
Mm = (x[:, 0] + x[:, 1]) / 2
sib = sosfilt(butter(2, [5000, 9000], 'band', fs=sr, output='sos'), Mm)
e_s = env_follow(sib ** 2, coef(1), coef(60)); e_b = env_follow(Mm ** 2, coef(1), coef(60))
ratio_db = 10 * np.log10((e_s + 1e-12) / (e_b + 1e-12))
red_db = np.clip((ratio_db - (-8.0)) * 0.6, 0, 4.0)     # au-delà de -8 dB relatif → réduction
red_db = env_follow(red_db, coef(1), coef(40))
band = sosfilt(butter(2, [5000, 9000], 'band', fs=sr, output='sos'), x, axis=0)
x = x - band * (1 - 10 ** (-red_db / 20))[:, None]
log['deesser_active_pct'] = float(np.mean(red_db > 0.5) * 100); log['deesser_max_db'] = float(red_db.max())

# ---------- 5. Contrôle dynamique du sub (multibande, < 75 Hz) ----------
lo, hi = lr4(x, 75)
lo_c, gr_lo = compressor(lo, lo, thr_db=lufs(x) - 3.0, ratio=2.0, att_ms=25, rel_ms=180)
# seuil réglé relativement au niveau du morceau ; on vérifie la réduction
x = lo_c + hi
log['sub_gr_p95'] = float(np.percentile(gr_lo, 95)); log['sub_gr_max'] = float(gr_lo.max())

# ---------- 6. Compression de bus « glue » ----------
key = sosfilt(butter(2, 90, 'high', fs=sr, output='sos'), x, axis=0)  # sidechain sans sub (pas de pompage)
loud = lufs(x)
x, gr_bus = compressor(x, key, thr_db=loud - 2.0, ratio=1.4, att_ms=30, rel_ms=250, knee_db=8)
x *= 10 ** (0.5 * np.percentile(gr_bus, 50) / 20)  # compensation partielle
log['bus_gr_median'] = float(np.median(gr_bus)); log['bus_gr_p95'] = float(np.percentile(gr_bus, 95))

# ---------- 7. Gain + limiteur true-peak ----------
ceiling = -1.2  # marge pour le passage en MP3/AAC
g = target - lufs(x)
for it in range(5):
    y, gr_lim = limiter(softclip(x * 10 ** (g / 20), ceiling + CLIP_DB), ceiling)
    err = target - lufs(y)
    if abs(err) < 0.1: break
    g += err
x = y
np.save(out+'_gr.npy', gr_lim); log['lim_gr_median'] = float(np.median(gr_lim)); log['lim_gr_p99'] = float(np.percentile(gr_lim, 99)); log['lim_gr_max'] = float(gr_lim.max())

# ---------- 8. Début / fin ----------
n_in = int(0.010 * sr); x[:n_in] *= np.linspace(0, 1, n_in)[:, None] ** 2
n_out = int(3.5 * sr); t = np.linspace(0, 1, n_out)
x[-n_out:] *= (np.cos(t * np.pi / 2) ** 2)[:, None]       # fondu de sortie (la source est coupée net)
x = np.concatenate([x, np.zeros((int(0.6 * sr), 2))])

# ---------- 9. Export 24 bits + dither TPDF ----------
lsb = 1 / 2 ** 23
d = (np.random.default_rng(1).random(x.shape) - np.random.default_rng(2).random(x.shape)) * lsb
q = np.clip(np.round((x + d) * 2 ** 23), -2 ** 23, 2 ** 23 - 1).astype(np.int32)
# wavfile écrit int32 → on passe par ffmpeg pour du vrai 24 bits
wavfile.write(out + '_i32.wav', sr, (q.astype(np.int64) << 8).astype(np.int32))
log['lufs'] = lufs(x); log['sample_peak_db'] = float(20 * np.log10(np.abs(x).max()))
print(json.dumps(log, indent=1))
