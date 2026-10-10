#!/usr/bin/env python3
"""Monte la maquette 9:16 (Instagram Reel) de « Même les super-héros ont faim ».

Les plans du héros sont des emplacements « À GÉNÉRER » posés sur les vraies
photos ; tout le reste (rythme, sous-titres, plats, carton final) est définitif.
Usage : python3 video/build_maquette.py  ->  video/maquette_reel_9x16.mp4
"""
import os
import subprocess
import tempfile
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PH = os.path.join(ROOT, "references", "photos")
PL = os.path.join(ROOT, "references", "plates_9x16")
HERO = os.path.join(ROOT, "references", "personnage")
OUT = os.path.join(ROOT, "video")
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-%s.otf"
TMP = tempfile.mkdtemp(prefix="maquette_")

NIGHT = "eq=brightness=-0.16:saturation=0.75:gamma=0.9,colorbalance=bs=0.18:bm=0.08:rh=-0.05"
WARM = "eq=saturation=1.08,colorbalance=rm=0.05:bm=-0.05"
DEFISH = "lenscorrection=k1=-0.18:k2=-0.03"


def run(cmd):
    subprocess.run(cmd, check=True)


def txt(text):
    """drawtext lit le texte depuis un fichier : pas d'échappement d'apostrophes."""
    path = os.path.join(TMP, "t%d.txt" % abs(hash(text)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def draw(text, y, size=54, weight="Bold", color="white", t0=None, t1=None, box=True):
    en = "" if t0 is None else ":enable='between(t,%s,%s)'" % (t0, t1)
    b = ":box=1:boxcolor=black@0.55:boxborderw=22" if box else ":shadowcolor=black@0.7:shadowx=3:shadowy=3"
    return ("drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=%s:x=(940-text_w)/2+20:y=%d"
            ":line_spacing=10%s%s" % (FONT % weight, txt(text), size, color, y, b, en))


def tag(label):
    """Bandeau d'emplacement pour un plan IA à générer (dans la zone sûre)."""
    return draw("À GÉNÉRER · " + label, 250, size=30, weight="SemiBold", color="0xFFB547")


def clip(name, src, dur, move="push", grade=WARM, label=None, subs=(), pre="", extra=(), zoom=0.10,
         hero=None):
    """move : push (zoom avant), pull (zoom arrière), panx (panoramique), still.
    hero : (pose, hauteur, x, y) — détourage de la fiche personnage incrusté avant le mouvement,
    pour qu'il bouge avec le décor."""
    d = float(dur)
    if move == "push":
        geo = "scale=w='%d*(1.01+%s*t/%s)':h=-2:eval=frame,crop=%d:%d" % (W, zoom, d, W, H)
    elif move == "pull":
        geo = "scale=w='%d*(1.01+%s-%s*t/%s)':h=-2:eval=frame,crop=%d:%d" % (W, zoom, zoom, d, W, H)
    elif move == "panx":
        geo = "scale=-2:%d,crop=%d:%d:x='(iw-%d)*(0.12+0.40*t/%s)':y=0" % (H, W, H, W, d)
    else:
        geo = "scale=%d:%d" % (W, H)
    vf = [f for f in (geo, grade) if f]
    if label:
        vf.append(tag(label))
    for s in subs:
        vf.extend([draw(*s)] if isinstance(s, tuple) else s)
    vf += list(extra)
    vf += ["fade=in:st=0:d=0.12", "fade=out:st=%s:d=0.12" % (d - 0.12), "format=yuv420p"]
    out = os.path.join(TMP, name + ".mp4")
    base = "[0]" + (pre + "," if pre else "")
    if hero:
        pose, hh, hx, hy = hero
        graph = (base + "scale=%d:%d[b];[1]scale=-1:%d[h];[b][h]overlay=%d:%d," % (W, H, hh, hx, hy)
                 + ",".join(vf))
        inputs = ["-i", os.path.join(HERO, pose + ".png")]
    else:
        graph = base + ",".join(vf)
        inputs = []
    run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", str(d),
         "-i", src] + inputs + ["-filter_complex", graph, "-r", str(FPS), "-c:v", "libx264", "-crf", "18",
         "-preset", "medium", "-pix_fmt", "yuv420p", out])
    return out


def sub(text, t0, t1, speaker=None):
    """Sous-titre en zone sûre basse : nom du personnage en orange, réplique dessous (≤ 28 car./ligne)."""
    lines = "\n".join(textwrap.wrap(text.replace("\n", " "), 28))
    out = [draw(lines, 1300, 46, "Bold", "white", t0, t1)]
    if speaker:
        out.insert(0, draw(speaker, 1225, 32, "Black", "0xFF8A1F", t0, t1, box=False))
    return out


def food(src, name):
    """Plat 2:3 -> 9:16 : fond flou de la même photo + photo nette centrée (aucune retouche du plat)."""
    out = os.path.join(TMP, name + ".png")
    f = ("[0]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=40:2,eq=brightness=-0.12[bg];"
         "[0]scale=%d:-2[fg];[bg][fg]overlay=0:(H-h)/2-60" % (W, H, W, H, W))
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-filter_complex", f, out])
    return out


def dark(name, tint="#0f1a12"):
    """Fond sombre pour les gros plans du casque (P01/P09)."""
    out = os.path.join(TMP, name + ".png")
    run(["convert", "-size", "%dx%d" % (W, H), "radial-gradient:%s-#030403" % tint, out])
    return out


def end_card():
    """Carton final : logo officiel en blanc + infos de réservation confirmées."""
    logo = os.path.join(TMP, "logo.png")
    run(["convert", os.path.join(PH, "L01_logo_officiel.jpg"), "-colorspace", "gray", "-negate",
         "-alpha", "copy", "-fill", "white", "-colorize", "100", "-trim", "+repage", "-resize", "680x", logo])
    out = os.path.join(OUT, "carton_final_reservation_1080x1920.png")
    F = lambda w: FONT % w
    run(["convert", "-size", "%dx%d" % (W, H), "radial-gradient:#1e2a22-#0b0d0c", logo,
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
         "-annotate", "-30+1400", "La Pataterie · Limoges", out])
    return out


def soundtrack(total):
    """Ambiance provisoire : drone de suspense, coupure, puis nappe chaleureuse."""
    out = os.path.join(TMP, "bed.wav")
    expr = ("if(lt(t,17),"
            "0.30*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*1.2*t))+0.12*sin(2*PI*110.5*t)"
            "+0.25*exp(-8*mod(t,0.6))*sin(2*PI*48*t),"
            "0.13*(sin(2*PI*220*t)+sin(2*PI*277.2*t)+sin(2*PI*329.6*t))*(0.8+0.2*sin(2*PI*0.5*t)))"
            "*if(between(t,15.0,16.6),0.05,1)*if(gt(t,%s),(%s-t)/2.5,1)" % (total - 2.5, total))
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
         "aevalsrc='%s':s=48000:d=%s" % (expr, total), "-af", "afade=in:d=0.4,lowpass=f=4000,volume=0.8", out])
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    pl = lambda n: os.path.join(PL, n + "_9x16.jpg")
    r10 = os.path.join(TMP, "r10.png")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(PH, "R10_salle_portrait_toiles.jpg"),
         "-vf", DEFISH + ",crop=iw*0.82:ih*0.82", r10])
    rib, cocktail, waffle = (food(os.path.join(PH, f), n) for f, n in
                             (("P02_travers_chips.jpg", "rib"), ("P01_cocktail_passion.jpg", "cocktail"),
                              ("P03_gaufre_chantilly.jpg", "waffle")))
    card = end_card()
    E, C = "ÉCHO", "LE COMMANDEUR"

    shots = [
        clip("p01", dark("d1"), 2, "push", "", "P01 les yeux du casque s'allument", hero=("casque", 1150, 120, 300),
             subs=[sub("Activité inhabituelle détectée dans ce secteur.", 0.2, 2, E)]),
        clip("p02", pl("R03_facade_parking"), 2, "push", NIGHT, "P02 atterrissage du héros", zoom=0.03, hero=("face", 760, 400, 960)),
        clip("p03", pl("R02_terrasse_logo_P"), 2, "push", NIGHT, "P03 le héros se relève", hero=("trois_quarts", 1150, 80, 720),
             subs=[sub("Enfin une mission à ma hauteur.", 0.1, 2, C)]),
        clip("p04", pl("R04_entree_verriere_portes"), 2, "push", NIGHT, "P04 marche vers les portes", hero=("dos", 1250, 380, 820)),
        clip("p05", pl("R05_sas_portes_do_not_enter"), 3, "still", WARM, "P05 arrêt devant le ruban", hero=("trois_quarts", 1350, 560, 560),
             subs=[sub("Accès interdit.", 0.5, 1.6, E), sub("C'est une décoration.", 1.7, 3, C)]),
        clip("p06", r10, 2, "panx", WARM, "P06 scan des portraits"),
        clip("p07", pl("R07_bar_salle"), 4, "push", WARM, "P07 au bar", hero=("face", 1050, 560, 620),
             subs=[sub("Attendez… toute cette activité\nvient de la cuisine ?", 0.1, 1.5, C),
              sub("Concentration anormalement élevée\nde bonnes odeurs.", 1.5, 2.9, E),
              sub("Je prends les commandes.", 3.1, 4, C)]),
        clip("p08", rib, 3, "push", ""),
        clip("p09", dark("d2", "#3a2a10"), 2, "push", "", "P09 reflet de l'assiette sur le casque", hero=("casque", 1150, 120, 300)),
        clip("p10", pl("R11_salle_longue_banquette"), 4, "still", WARM, "P10 assis à table, mains à plat", hero=("face", 980, 280, 640),
             subs=[sub("Écho, annule la mission.\nJ'ai trouvé plus important.", 0.2, 2.2, C),
              sub("Vous êtes en train\nde sauver le monde ?", 2.3, 4, E)]),
        clip("p11", pl("R11_salle_longue_banquette"), 3, "push", WARM, "P11 retire le casque (de dos)", hero=("dos", 1100, 330, 700),
             subs=[sub("Non. Ma soirée.", 1.0, 3, C)]),
        clip("p12a", rib, 1, "pull", ""),
        clip("p12b", cocktail, 1, "push", ""),
        clip("p12c", pl("R08_salle_tarte_escalier"), 1, "push", WARM),
        clip("p12d", pl("R11_salle_longue_banquette"), 1, "pull", WARM, hero=("pouce", 760, 620, 760)),
        clip("p13", waffle, 3, "pull", "", None,
             [sub("Pour Halloween, faites-vous peur\navec les histoires… pas avec votre faim.", 0.1, 3, C)]),
        clip("p14", pl("R03_facade_parking"), 2, "push", NIGHT, "P14 casque posé en terrasse",
             [("Cet Halloween,\nvivez votre propre aventure\nà La Pataterie de Limoges.",
               1150, 52, "Black", "white", 0, 2)], zoom=0.03),
        clip("p15", card, 4, "still", ""),
    ]
    total = 42
    lst = os.path.join(TMP, "list.txt")
    with open(lst, "w") as f:
        f.writelines("file '%s'\n" % s for s in shots)
    silent = os.path.join(TMP, "silent.mp4")
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent])
    final = os.path.join(OUT, "maquette_reel_9x16.mp4")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", silent, "-i", soundtrack(total),
         "-c:v", "libx264", "-crf", "21", "-preset", "medium", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final])
    print(final)


if __name__ == "__main__":
    main()
