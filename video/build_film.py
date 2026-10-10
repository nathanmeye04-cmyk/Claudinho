#!/usr/bin/env python3
"""« Même les super-héros ont faim » — version complète animée (Reel 9:16, ~59 s).

Tout est fabriqué ici, sans service externe :
  - décors = vraies photos de La Pataterie (corrigées du fisheye) avec mouvements de caméra ;
  - héros = détourages de la fiche personnage, animés (atterrissage, marche, respiration),
    ombre portée, poussière, brume, yeux lumineux, tremblement de caméra ;
  - voix = synthèse vocale française (Piper : « tom » = Commandeur, « siwis » = ÉCHO) ;
  - musique originale et bruitages synthétisés (numpy), mixés avec ducking sous les voix.

Usage : python3 video/build_film.py   ->  video/film_reel_9x16.mp4
Pour remplacer un plan par une vraie vidéo IA plus tard : changer la source du plan dans SHOTS.
"""
import os
import subprocess
import tempfile
import textwrap

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, butter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = os.path.join(ROOT, "references", "photos")
PL = os.path.join(ROOT, "references", "plates_9x16")
HERO = os.path.join(ROOT, "references", "personnage")
VOX = os.path.join(ROOT, "video", "voix")
OUT = os.path.join(ROOT, "video")
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-%s.otf"
TMP = tempfile.mkdtemp(prefix="film_")

NIGHT = "eq=brightness=-0.17:saturation=0.72:gamma=0.88,colorbalance=bs=0.20:bm=0.10:rh=-0.06:rm=0.03"
WARM = "eq=saturation=1.10:contrast=1.04,colorbalance=rm=0.06:bm=-0.06:rh=0.03"
DEFISH = "lenscorrection=k1=-0.18:k2=-0.03"
ASPECT = {"face": 345 / 914, "trois_quarts": 300 / 889, "dos": 290 / 880, "casque": 189 / 265, "pouce": 110 / 404}


def run(cmd):
    subprocess.run(cmd, check=True)


def magick(*args):
    run(["convert", *args])


# ---------------------------------------------------------------- éléments graphiques

def assets():
    a = {}
    a["shadow"] = os.path.join(TMP, "shadow.png")
    magick("-size", "700x200", "xc:none", "-fill", "black", "-draw", "ellipse 350,100 300,52 0,360",
           "-blur", "0x22", a["shadow"])
    a["dust"] = os.path.join(TMP, "dust.png")
    magick("-size", "1200x520", "plasma:gray60-gray90", "-blur", "0x6",
           "(", "-size", "1200x520", "xc:black", "-fill", "white", "-draw", "ellipse 600,330 560,170 0,360",
           "-blur", "0x60", ")", "-alpha", "off", "-compose", "copy_opacity", "-composite", a["dust"])
    a["fog"] = os.path.join(TMP, "fog.png")
    magick("-size", "1100x980", "plasma:fractal", "-colorspace", "gray", "-blur", "0x30", "-resize", "2200x1960!",
           "-level", "35%,85%", "(", "+clone", "-evaluate", "multiply", "0.35", ")", "-alpha", "off",
           "-compose", "copy_opacity", "-composite", "-fill", "#c9d3e0", "-colorize", "100", a["fog"])
    a["steam"] = os.path.join(TMP, "steam.png")
    magick("-size", "300x450", "plasma:fractal", "-colorspace", "gray", "-blur", "0x12", "-resize", "600x900!",
           "-level", "45%,90%", "(", "-size", "600x900", "radial-gradient:white-black", "-evaluate", "multiply", "0.6",
           ")", "-compose", "multiply", "-composite", "(", "+clone", ")", "-alpha", "off",
           "-compose", "copy_opacity", "-composite", "-fill", "white", "-colorize", "100", a["steam"])
    a["beam"] = os.path.join(TMP, "beam.png")
    magick("-size", "160x1920", "xc:none", "-fill", "#bfffa0", "-draw", "rectangle 74,0 86,1920",
           "-blur", "0x18", "-fill", "#f4ffe8", "-draw", "rectangle 78,0 82,1920", a["beam"])
    # yeux du casque : positions mesurées sur casque.png (189x265) -> (58,134) et (138,135)
    a["glow"] = os.path.join(TMP, "glow.png")
    magick("-size", "756x1060", "xc:none", "-fill", "#eafff0",
           "-draw", "ellipse 232,538 120,70 0,360", "-draw", "ellipse 552,540 120,70 0,360", "-blur", "0x34",
           "-fill", "white", "-draw", "ellipse 232,538 70,34 0,360", "-draw", "ellipse 552,540 70,34 0,360",
           "-blur", "0x6", a["glow"])
    a["dark"] = os.path.join(TMP, "dark.png")
    magick("-size", "%dx%d" % (W, H), "radial-gradient:#14261a-#020302", a["dark"])
    a["darkwarm"] = os.path.join(TMP, "darkwarm.png")
    magick("-size", "%dx%d" % (W, H), "radial-gradient:#3b2a12-#030201", a["darkwarm"])
    a["r10"] = os.path.join(TMP, "r10.png")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(PH, "R10_salle_portrait_toiles.jpg"),
         "-vf", DEFISH + ",crop=iw*0.82:ih*0.82", a["r10"]])
    for f, n in (("P02_travers_chips.jpg", "rib"), ("P01_cocktail_passion.jpg", "cocktail"),
                 ("P03_gaufre_chantilly.jpg", "waffle")):
        a[n] = os.path.join(TMP, n + ".png")
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(PH, f), "-filter_complex",
             "[0]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=40:2,eq=brightness=-0.12[bg];"
             "[0]scale=%d:-2:flags=lanczos,unsharp=5:5:0.6[fg];[bg][fg]overlay=0:(H-h)/2-60" % (W, H, W, H, W),
             a[n]])
    a["card"] = end_card()
    return a


def end_card():
    logo = os.path.join(TMP, "logo.png")
    magick(os.path.join(PH, "L01_logo_officiel.jpg"), "-colorspace", "gray", "-negate", "-alpha", "copy",
           "-fill", "white", "-colorize", "100", "-trim", "+repage", "-resize", "680x", logo)
    out = os.path.join(OUT, "carton_final_reservation_1080x1920.png")
    F = lambda w: FONT % w
    magick("-size", "%dx%d" % (W, H), "radial-gradient:#1e2a22-#0b0d0c", logo,
           "-gravity", "north", "-geometry", "-30+380", "-composite",
           "-gravity", "north", "-font", F("Black"), "-fill", "#FF8A1F", "-pointsize", "112",
           "-annotate", "-30+830", "HALLOWEEN",
           "-font", F("Bold"), "-fill", "white", "-pointsize", "64", "-annotate", "-30+975", "SAMEDI 31 OCTOBRE",
           "-fill", "#2f6b45", "-draw", "roundrectangle 120,1100 900,1360 36,36",
           "-font", F("SemiBold"), "-fill", "white", "-pointsize", "46",
           "-annotate", "-30+1130", "Réservez dès maintenant",
           "-font", F("Medium"), "-pointsize", "38", "-annotate", "-30+1195", "par téléphone",
           "-font", F("Black"), "-pointsize", "80", "-annotate", "-30+1250", "05 55 38 19 10",
           "-font", F("Medium"), "-fill", "#d9d2c3", "-pointsize", "40",
           "-annotate", "-30+1400", "La Pataterie · Limoges", out)
    return out


# ---------------------------------------------------------------- calques animés

def layer(img, w, x, y, fin=None, fout=None, alpha=1.0, extra=""):
    """Calque PNG : largeur, x, y = expressions ffmpeg (variable t = temps du plan)."""
    return dict(img=img, w=w, x=x, y=y, fin=fin, fout=fout, alpha=alpha, extra=extra)


def hero(pose, height, cx, foot, motion="idle", t0=0.0):
    """Héros + ombre portée. motion : idle | drop | walkaway | slidein."""
    img = os.path.join(HERO, pose + ".png")
    a = ASPECT[pose]
    breath = "(1+0.007*sin(2*PI*0.4*t))"
    if motion == "walkaway":
        hgt = "%d*(1-0.22*min(t/2.2,1))" % height
        w = "%s*%s" % (hgt, a)
        y = "%d-90*min(t/2.2,1)-h+10*abs(sin(2*PI*1.7*t))" % foot
        x = "%d-w/2" % cx
        sw = "%s*1.15" % w
        sy = "%d-90*min(t/2.2,1)-h/2" % foot
        sx = "%d-w/2" % cx
    elif motion == "slidein":
        w = "%d*%s" % (height, a)
        x = "%d-w/2+520*pow(max(0,1-t/0.9),2)" % cx
        y = "%d-h+if(lt(t,0.9),10*abs(sin(2*PI*1.8*t)),0)" % foot
        sw, sx, sy = "%d*%s*1.1" % (height, a), x.replace("w/2", "w/2"), "%d-h/2" % foot
    else:
        w = "%d*%s*%s" % (height, a, breath)
        x = "%d-w/2" % cx
        y = "%d-h" % foot
        if motion == "drop":
            y += "-if(lt(t,%s),1900*pow(1-t/%s,2),0)" % (t0 + 0.35, t0 + 0.35)
        sw, sx, sy = "%d*%s*1.15" % (height, a), "%d-w/2" % cx, "%d-h/2" % foot
    shadow = layer(ASSET["shadow"], sw, sx, sy, fin=(t0 + 0.25, 0.15) if motion == "drop" else None, alpha=0.75)
    return [shadow, layer(img, w, x, y)]


def eyes(height, cx, top, t_on=0.4, pulse=True):
    """Halo des yeux posé exactement sur casque.png mis à l'échelle."""
    w = "%d*%s" % (height, ASPECT["casque"])
    return layer(ASSET["glow"], w, "%d-w/2" % cx, str(top), fin=(t_on, 0.35), alpha=0.95)


# ---------------------------------------------------------------- texte

def txtfile(text):
    p = os.path.join(TMP, "t%d.txt" % abs(hash(text)))
    open(p, "w", encoding="utf-8").write(text)
    return p


def draw(text, y, size, weight, color, t0=None, t1=None, box=True):
    en = "" if t0 is None else ":enable='between(t,%.2f,%.2f)'" % (t0, t1)
    b = ":box=1:boxcolor=black@0.55:boxborderw=22" if box else ":shadowcolor=black@0.8:shadowx=3:shadowy=3"
    return ("drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=%s:x=(940-text_w)/2+20:y=%d:line_spacing=10%s%s"
            % (FONT % weight, txtfile(text), size, color, y, b, en))


def sub(text, t0, t1, who="C"):
    """Sous-titre en zone sûre ; ÉCHO en vert clair italique, le Commandeur en blanc."""
    lines = "\n".join(textwrap.wrap(text.replace(" ?", "\u00a0?"), 28))
    if who == "E":
        return draw(lines, 1290, 46, "SemiBoldItalic", "0xB8F59A", t0, t1)
    return draw(lines, 1290, 48, "Bold", "white", t0, t1)


# ---------------------------------------------------------------- plan

def clip(name, src, d, zoom=(1.02, 1.10), pan=None, grade=WARM, layers=(), shake=None, texts=(), fade=0.10):
    """zoom=(début, fin) ; pan=(x0, x1) fraction pour panoramique ; shake=(t, durée, amplitude)."""
    inputs, chain = ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", src], []
    chain.append("[0]scale=%d:%d,setsar=1,format=rgba[c0]" % (W, H) if not pan else
                 "[0]scale=-2:%d,setsar=1,format=rgba[c0]" % H)
    cur = "c0"
    for i, L in enumerate(layers, 1):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", L["img"]]
        f = "[%d]format=rgba,scale=w='%s':h=-1:eval=frame" % (i, L["w"])
        if L["alpha"] < 1:
            f += ",colorchannelmixer=aa=%s" % L["alpha"]
        if L["fin"]:
            f += ",fade=in:st=%s:d=%s:alpha=1" % L["fin"]
        if L["fout"]:
            f += ",fade=out:st=%s:d=%s:alpha=1" % L["fout"]
        if L["extra"]:
            f += "," + L["extra"]
        chain.append(f + "[l%d]" % i)
        chain.append("[%s][l%d]overlay=x='%s':y='%s':eval=frame:format=auto[c%d]" % (cur, i, L["x"], L["y"], i))
        cur = "c%d" % i
    sh = "0"
    if shake:
        st, du, am = shake
        sh = "%s*sin(t*97)*exp(-6*(t-%s))*between(t,%s,%s)" % (am, st, st, st + du)
    if pan:
        geo = ("crop=%d:%d:x='(iw-%d)*(%s+%s*t/%s)':y=0" % (W, H, W, pan[0], pan[1] - pan[0], d))
    else:
        z0, z1 = zoom
        geo = ("scale=w='%d*(%s+%s*t/%s)':h=-2:eval=frame,crop=%d:%d:x='(iw-%d)/2+%s':y='(ih-%d)/2+%s*0.7'"
               % (W, z0, z1 - z0, d, W, H, W, sh, H, sh))
    post = [geo, grade] if grade else [geo]
    post += list(texts)
    post += ["fade=in:st=0:d=%s" % fade, "fade=out:st=%s:d=%s" % (d - fade, fade), "format=yuv420p"]
    chain.append("[%s]%s[v]" % (cur, ",".join(post)))
    out = os.path.join(TMP, name + ".mp4")
    run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[v]",
         "-t", str(d), "-r", str(FPS), "-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-pix_fmt", "yuv420p", out])
    return out


# ---------------------------------------------------------------- audio

def load_voice(name, helmet):
    """Voix Piper -> 48 kHz, traitée (casque fermé = filtre métallique, ÉCHO = voix numérique)."""
    src = os.path.join(VOX, name + ".wav")
    if name.startswith("e"):
        af = "highpass=f=180,chorus=0.6:0.9:22:0.35:0.25:2,aecho=0.8:0.5:30:0.15,volume=1.3"
    elif helmet:
        af = ("highpass=f=140,lowpass=f=5200,equalizer=f=1800:t=q:w=1.2:g=5,"
              "aecho=0.8:0.55:9|17:0.35|0.2,volume=1.5")
    else:
        af = "highpass=f=90,equalizer=f=3000:t=q:w=1:g=2,aecho=0.8:0.6:45:0.1,volume=1.4"
    out = os.path.join(TMP, name + "_fx.wav")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-af", af + ",aresample=48000", "-ac", "1", out])
    sr, x = wavfile.read(out)
    return x.astype(np.float32) / 32768.0


def env(n, a, r):
    e = np.ones(n, np.float32)
    na, nr = int(a * SR), int(r * SR)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def tone(f, d, amp=1.0, decay=0.0, kind="sin"):
    t = np.arange(int(d * SR)) / SR
    ph = 2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR if np.ndim(f) else 2 * np.pi * f * t
    if kind == "saw":
        s = 2 * ((ph / (2 * np.pi)) % 1) - 1
    elif kind == "tri":
        s = 2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1
    else:
        s = np.sin(ph)
    return (amp * s * (np.exp(-decay * t) if decay else 1)).astype(np.float32)


def noise(d, lo=None, hi=None, amp=1.0):
    x = np.random.default_rng(len(str(d)) + int(d * 1000)).standard_normal(int(d * SR)).astype(np.float32)
    if lo and hi:
        x = sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)
    elif hi:
        x = sosfilt(butter(2, hi, "low", fs=SR, output="sos"), x)
    elif lo:
        x = sosfilt(butter(2, lo, "high", fs=SR, output="sos"), x)
    return (amp * x / (np.abs(x).max() + 1e-9)).astype(np.float32)


def put(buf, x, at):
    i = int(at * SR)
    n = min(len(x), len(buf) - i)
    if n > 0:
        buf[i:i + n] += x[:n]


def sfx():
    s = {}
    t = np.arange(int(0.5 * SR)) / SR
    s["whoosh"] = noise(0.5, 300, 3000, 0.5) * np.sin(np.pi * t / 0.5) ** 2
    s["impact"] = (tone(np.linspace(70, 30, int(1.2 * SR)), 1.2, 0.9, 5) + noise(1.2, None, 400, 0.6) *
                   np.exp(-8 * np.arange(int(1.2 * SR)) / SR))
    s["servo"] = tone(np.linspace(500, 1400, int(0.3 * SR)), 0.3, 0.12, 4, "saw") * env(int(0.3 * SR), 0.02, 0.1)
    s["powerup"] = tone(np.linspace(180, 1300, int(0.9 * SR)), 0.9, 0.18) * env(int(0.9 * SR), 0.3, 0.2)
    s["ding"] = tone(1760, 1.8, 0.35, 3) + tone(2640, 1.8, 0.15, 4)
    s["pshh"] = noise(0.9, 2500, None, 0.35) * np.exp(-4 * np.arange(int(0.9 * SR)) / SR)
    b = np.zeros(int(1.4 * SR), np.float32)
    for k in range(5):
        put(b, tone(1250, 0.07, 0.12) * env(int(0.07 * SR), 0.005, 0.02), 0.05 + k * 0.26)
    s["scan"] = b
    s["door"] = noise(0.35, None, 250, 0.4) * np.exp(-10 * np.arange(int(0.35 * SR)) / SR)
    s["step"] = noise(0.18, 80, 900, 0.35) * np.exp(-25 * np.arange(int(0.18 * SR)) / SR)
    s["sizzle"] = noise(3.0, 3000, 9000, 0.06) * env(int(3.0 * SR), 0.4, 0.6)
    s["room"] = noise(1.0, 200, 1500, 0.03)
    return s


def music(total, cut0, cut1, warm_at):
    """Musique originale : ostinato d'action en la mineur, silence comique, puis thème chaleureux en do majeur."""
    m = np.zeros(int(total * SR), np.float32)
    bpm = 120
    eighth = 60 / bpm / 2
    # acte 1 : tension
    tt = 0.0
    seq = [110, 110, 130.8, 110, 146.8, 110, 130.8, 98]
    k = 0
    while tt < cut0:
        f = seq[k % 8]
        put(m, tone(f, 0.24, 0.16, 9, "saw") * env(int(0.24 * SR), 0.005, 0.05), tt)
        if k % 4 == 0:
            put(m, tone(np.linspace(90, 40, int(0.3 * SR)), 0.3, 0.45, 12), tt)  # grosse caisse
        if k % 16 == 8:
            put(m, noise(0.15, 1500, 8000, 0.08) * np.exp(-20 * np.arange(int(0.15 * SR)) / SR), tt)
        tt += eighth
        k += 1
    drone = tone(55, cut0, 0.10) + tone(82.4, cut0, 0.05)
    put(m, drone * env(len(drone), 1.5, 0.15), 0)
    # cuivres synthétiques sur les temps forts
    for at in (3.6, 5.4, 10.6, 17.4):
        if at < cut0:
            br = sum(tone(f, 1.2, 0.07, 1.2, "saw") for f in (220, 261.6, 329.6))
            put(m, sosfilt(butter(2, 1800, "low", fs=SR, output="sos"), br) * env(len(br), 0.04, 0.6), at)
    # acte 2 (après la commande) : chaud, accords C – Am – F – G, arpèges pincés
    chords = [(261.6, 329.6, 392.0), (220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (196.0, 246.9, 293.7)]
    tt, k = warm_at, 0
    while tt < total:
        ch = chords[(k // 1) % 4]
        d = min(2.0, total - tt)
        pad = sum(tone(f, d, 0.05, 0, "tri") + tone(f * 1.003, d, 0.03, 0, "tri") for f in ch)
        put(m, pad * env(len(pad), 0.5, 0.6), tt)
        put(m, tone(ch[0] / 2, d, 0.10, 0.8), tt)
        for j in range(8):
            f = ch[j % 3] * (2 if j >= 3 else 1)
            put(m, tone(f, 0.4, 0.07, 9) , tt + j * 0.25)
        tt += 2.0
        k += 1
    m[int(cut0 * SR):int(cut1 * SR)] *= 0.0
    fade = int(2.5 * SR)
    m[-fade:] *= np.linspace(1, 0, fade)
    return m


def mix(total, cues, sfx_cues, music_args):
    voice = np.zeros(int(total * SR), np.float32)
    for name, at, helmet in cues:
        put(voice, load_voice(name, helmet), at)
    fx = np.zeros_like(voice)
    S = sfx()
    for name, at, g in sfx_cues:
        put(fx, S[name] * g, at)
    mus = music(total, *music_args)
    # ducking : la musique baisse de ~9 dB quand une voix parle
    e = np.abs(voice)
    k = int(0.25 * SR)
    e = np.convolve(e, np.ones(k) / k, mode="same")
    duck = 1 - 0.65 * np.clip(e / 0.03, 0, 1)
    out = voice * 1.0 + fx * 0.9 + mus * duck * 0.9
    out /= max(1.0, np.abs(out).max() / 0.95)
    p = os.path.join(TMP, "mix.wav")
    wavfile.write(p, SR, (np.stack([out, out], 1) * 32767).astype(np.int16))
    return p


# ---------------------------------------------------------------- montage

def main():
    global ASSET
    ASSET = assets()
    A = ASSET
    pl = lambda n: os.path.join(PL, n + "_9x16.jpg")
    fog = lambda a=0.6: layer(A["fog"], "2200", "-560+120*t", "0", alpha=a)
    CH = 1150  # hauteur du casque en gros plan
    casque = lambda: layer(os.path.join(HERO, "casque.png"), "%d*%s" % (CH, ASPECT["casque"]),
                           "540-w/2", "330", fin=(0, 0.5))
    casque_eyes = lambda t_on: eyes(CH, 540, 330, t_on)

    # (nom, source, durée, options) — les temps de sous-titres/voix sont relatifs au plan
    plan = [
        ("p01", A["dark"], 3.2, dict(zoom=(1.0, 1.06), grade="", layers=[casque(), casque_eyes(0.45)],
                                     texts=[sub("Activité inhabituelle détectée dans ce secteur.", 0.3, 3.1, "E")])),
        ("p02", pl("R03_facade_parking"), 2.2, dict(zoom=(1.03, 1.06), grade=NIGHT, shake=(0.35, 0.7, 16),
                                                    layers=[fog(0.5)] + hero("face", 780, 560, 1740, "drop") +
                                                    [layer(A["dust"], "300+900*min(max(t-0.35,0)/0.9,1)",
                                                           "560-w/2", "1740-h*0.7", fin=(0.33, 0.08),
                                                           fout=(0.8, 1.0), alpha=0.8)])),
        ("p03", pl("R02_terrasse_logo_P"), 3.2, dict(zoom=(1.02, 1.09), grade=NIGHT,
                                                     layers=[fog(0.45)] + hero("trois_quarts", 1150, 250, 1870),
                                                     texts=[sub("Enfin. Une mission à ma hauteur.", 0.2, 3.0)])),
        ("p04", pl("R04_entree_verriere_portes"), 2.0, dict(zoom=(1.02, 1.07), grade=NIGHT,
                                                            layers=[fog(0.35)] + hero("dos", 1250, 560, 2050,
                                                                                      "walkaway"))),
        ("p05", pl("R05_sas_portes_do_not_enter"), 4.4, dict(zoom=(1.02, 1.04),
                                                             layers=hero("trois_quarts", 1350, 790, 1930, "slidein"),
                                                             texts=[sub("Accès interdit.", 0.8, 1.9, "E"),
                                                                    sub("C'est une décoration.", 2.3, 4.3)])),
        ("p06", A["r10"], 2.4, dict(pan=(0.10, 0.55),
                                    layers=[layer(A["beam"], "160", "-200+1500*t/2.4", "0", alpha=0.55)])),
        ("p07", pl("R07_bar_salle"), 8.8, dict(zoom=(1.02, 1.12), layers=hero("face", 1050, 740, 1700),
                                               texts=[sub("Attendez… toute cette activité vient de la cuisine ?",
                                                          0.2, 3.2),
                                                      sub("Concentration anormalement élevée… de bonnes odeurs.",
                                                          3.4, 5.9, "E"),
                                                      sub("Je prends les commandes.", 6.8, 8.7)])),
        ("p08", A["rib"], 3.0, dict(zoom=(1.02, 1.12), grade="",
                                    layers=[layer(A["steam"], "620", "230", "620-110*t", fin=(0.2, 0.6),
                                                  fout=(2.2, 0.8), alpha=0.45)])),
        ("p09", A["darkwarm"], 1.8, dict(zoom=(1.04, 1.12), grade="",
                                         layers=[casque(), casque_eyes(0.05)])),
        ("p10", pl("R11_salle_longue_banquette"), 6.6, dict(zoom=(1.02, 1.05), layers=hero("face", 980, 420, 1620),
                                                            texts=[sub("Écho, annule la mission. J'ai trouvé plus important.",
                                                                       0.2, 4.1),
                                                                   sub("Vous êtes en train de sauver le monde ?",
                                                                       4.5, 6.4, "E")])),
        ("p11", pl("R11_salle_longue_banquette"), 3.4, dict(zoom=(1.06, 1.12), layers=hero("dos", 1100, 495, 1800) +
                                                            [layer(A["steam"], "380", "305", "620-140*t",
                                                                   fin=(0.15, 0.15), fout=(0.6, 0.9), alpha=0.6)],
                                                            texts=[sub("Non. Ma soirée.", 1.0, 3.3)])),
        ("p12a", A["rib"], 1.0, dict(zoom=(1.14, 1.04), grade="")),
        ("p12b", A["cocktail"], 1.0, dict(zoom=(1.02, 1.10), grade="")),
        ("p12c", pl("R08_salle_tarte_escalier"), 1.0, dict(zoom=(1.02, 1.10))),
        ("p12d", pl("R11_salle_longue_banquette"), 1.0, dict(zoom=(1.10, 1.03), layers=hero("pouce", 760, 680, 1520))),
        ("p13", A["waffle"], 4.4, dict(zoom=(1.12, 1.02), grade="",
                                       texts=[sub("Pour Halloween, faites-vous peur avec les histoires… "
                                                  "pas avec votre faim.", 0.1, 4.3)])),
        ("p14", pl("R03_facade_parking"), 2.2, dict(zoom=(1.02, 1.05), grade=NIGHT,
                                                    layers=[fog(0.5),
                                                            layer(os.path.join(HERO, "casque.png"), "130", "165",
                                                                  "1085")],
                                                    texts=[draw("Cet Halloween,\nvivez votre propre aventure\n"
                                                                "à La Pataterie de Limoges.", 1150, 52, "Black",
                                                                "white", 0, 2.2, box=False)])),
        ("p15", A["card"], 7.4, dict(zoom=(1.0, 1.03), grade="", fade=0.3)),
    ]
    starts, t = {}, 0.0
    files = []
    for name, src, d, opt in plan:
        starts[name] = t
        files.append(clip(name, src, d, **opt))
        t += d
    total = round(t, 2)
    s = starts
    cues = [("e1", s["p01"] + 0.3, False), ("c1", s["p03"] + 0.2, True), ("e2", s["p05"] + 0.8, False),
            ("c2", s["p05"] + 2.3, True), ("c3", s["p07"] + 0.2, True), ("e3", s["p07"] + 3.4, False),
            ("c4", s["p07"] + 6.8, True), ("c5", s["p10"] + 0.2, True), ("e4", s["p10"] + 4.5, False),
            ("c6", s["p11"] + 1.0, False), ("c7", s["p13"] + 0.1, False), ("e5", s["p15"] + 0.3, False)]
    fxc = [("powerup", s["p01"] + 0.35, 1.0), ("whoosh", s["p02"] + 0.0, 1.0), ("impact", s["p02"] + 0.35, 1.0),
           ("servo", s["p03"] + 0.05, 1.0), ("step", s["p04"] + 0.2, 1), ("step", s["p04"] + 0.8, 1),
           ("step", s["p04"] + 1.4, 1), ("step", s["p05"] + 0.3, 1), ("step", s["p05"] + 0.7, 1),
           ("servo", s["p05"] + 0.9, 0.8), ("door", s["p05"] + 4.1, 1.0), ("scan", s["p06"] + 0.3, 1.0),
           ("ding", s["p07"] + 8.6, 1.0), ("sizzle", s["p08"], 1.0), ("servo", s["p09"] + 0.1, 0.7),
           ("pshh", s["p11"] + 0.15, 1.0)]
    for k in range(int((total - s["p05"]) // 1)):  # ambiance de salle à partir de l'entrée
        if s["p05"] + k < s["p15"]:
            fxc.append(("room", s["p05"] + k, 1.0))
    wav = mix(total, cues, fxc, (s["p07"] + 5.9, s["p07"] + 8.6, s["p08"]))
    lst = os.path.join(TMP, "list.txt")
    open(lst, "w").writelines("file '%s'\n" % f for f in files)
    silent = os.path.join(TMP, "silent.mp4")
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    final = os.path.join(OUT, "film_reel_9x16.mp4")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", silent, "-i", wav,
         "-vf", "noise=alls=5:allf=t,vignette=angle=PI/5,format=yuv420p",
         # débit plafonné : le grain ferait exploser la taille (~25 Mo pour 59 s, idéal Instagram)
         "-c:v", "libx264", "-b:v", "3200k", "-maxrate", "4500k", "-bufsize", "6000k",
         "-preset", "slow", "-profile:v", "high",
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final])
    print(final, total)


if __name__ == "__main__":
    main()
