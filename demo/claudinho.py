# Petite démo : Claudinho, personnage dessiné et animé entièrement en code.
import math, subprocess, os
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 720, 720, 30, 5
OUT = os.path.join(os.path.dirname(__file__), "claudinho_demo.mp4")
SS = 2  # suréchantillonnage pour l'anticrénelage

def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def frame(t):
    s = SS
    im = Image.new("RGB", (W*s, H*s), (250, 240, 228))
    d = ImageDraw.Draw(im)
    # sol
    d.rectangle([0, 560*s, W*s, H*s], fill=(232, 218, 200))
    # rebond
    hop = abs(math.sin(t*math.pi*1.6))
    y = 380 - hop*60
    squash = 1 + (1-hop)**4 * 0.12
    cx = 360
    bw, bh = 150*squash, 170/squash
    # ombre
    sw = 120*(1-hop*0.4)
    d.ellipse([(cx-sw)*s, 548*s, (cx+sw)*s, 572*s], fill=(215, 198, 178))
    # bras gauche (fixe) et bras droit (qui salue)
    body = (217, 119, 87)
    dark = (60, 40, 35)
    ax, ay = cx-bw+10, y+10
    d.line([ax*s, ay*s, (ax-50)*s, (ay+60)*s], fill=body, width=26*s)
    wave = math.sin(t*math.pi*4)*0.6
    bx, by = cx+bw-10, y-10
    ang = -1.0 + wave
    hx, hy = bx+80*math.cos(ang), by+80*math.sin(ang)
    d.line([bx*s, by*s, hx*s, hy*s], fill=body, width=26*s)
    d.ellipse([(hx-20)*s, (hy-20)*s, (hx+20)*s, (hy+20)*s], fill=body)
    # corps
    d.ellipse([(cx-bw)*s, (y-bh)*s, (cx+bw)*s, (y+bh)*s], fill=body)
    # pieds
    for fx in (-60, 60):
        d.ellipse([(cx+fx-35)*s, (y+bh-25)*s, (cx+fx+35)*s, (y+bh+15)*s], fill=(190, 95, 66))
    # yeux (clignement)
    blink = (t % 2.2) > 2.05
    look = math.sin(t*1.3)*8
    for ex in (-48, 48):
        x0, y0 = cx+ex+look, y-40
        if blink:
            d.line([(x0-18)*s, y0*s, (x0+18)*s, y0*s], fill=dark, width=7*s)
        else:
            d.ellipse([(x0-18)*s, (y0-24)*s, (x0+18)*s, (y0+24)*s], fill="white")
            d.ellipse([(x0-9+look*0.4)*s, (y0-10)*s, (x0+9+look*0.4)*s, (y0+14)*s], fill=dark)
    # joues
    for ex in (-90, 90):
        d.ellipse([(cx+ex-18)*s, (y+5)*s, (cx+ex+18)*s, (y+22)*s], fill=(235, 150, 120))
    # bouche qui « parle » pendant la réplique
    talking = 0.8 < t < 3.2
    m = (abs(math.sin(t*math.pi*7))*22 + 6) if talking else 6
    d.chord([(cx-30)*s, (y+15-m*0.2)*s, (cx+30)*s, (y+25+m)*s], 0, 180, fill=dark)
    # bulle
    if 0.6 < t < 4.6:
        txt = "Salut ! Je suis Claudinho," if t < 2.6 else "et Claude m'a animé !"
        f = font(34*s)
        tw = d.textlength(txt, font=f)
        px, py = W*s/2 - tw/2, 70*s
        d.rounded_rectangle([px-30*s, py-25*s, px+tw+30*s, py+60*s], radius=30*s, fill="white", outline=dark, width=4*s)
        d.polygon([(cx*s-10*s, py+60*s), (cx*s+20*s, py+60*s), (cx*s+5*s, py+100*s)], fill="white")
        d.text((px, py), txt, font=f, fill=dark)
    return im.resize((W, H), Image.LANCZOS)

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-crf", "18", OUT], stdin=subprocess.PIPE)
for i in range(FPS*DUR):
    p.stdin.write(frame(i/FPS).tobytes())
p.stdin.close(); p.wait()
frame(1.5).save(os.path.join(os.path.dirname(__file__), "claudinho_apercu.png"))
print("ok", OUT)
