"""Construit timings/partition.json : le texte exact de la chanson, découpé
en feuilles et en lignes, avec le minutage de chaque mot.

Les minutages viennent de la reconnaissance vocale guidée par le texte
(dossier alignement/). Chaque mot des paroles est apparié au mot reconnu
correspondant ; les mots non reconnus sont interpolés entre leurs voisins.

Annotations dans le texte : mot{drapeau} ou mot{drapeau=valeur}, par ex.
Dior{strike=dior}, nations{drop=villes}, Impacter{heavy=1.3}, côté{ev=flip}."""
import difflib
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
AL = os.path.join(HERE, 'alignement')


def norm(w):
    w = unicodedata.normalize('NFD', w.lower())
    w = ''.join(c for c in w if unicodedata.category(c) != 'Mn')
    return re.sub(r"[^a-z]", '', w)


def tokens(name, a=-1e9, b=1e9):
    out = []
    with open(os.path.join(AL, name), encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^\s*([\d.]+)\s+([\d.]+) (.*)$', line.rstrip('\n'))
            if not m:
                continue
            t0, t1, w = float(m.group(1)), float(m.group(2)), m.group(3)
            if w.startswith(' ') or not out:
                out.append([w.strip(), t0, t1])
            else:
                out[-1][0] += w
                out[-1][2] = t1
    return [o for o in out if a <= o[1] < b]


def parse_text(text):
    """Lignes → [[(mot, drapeaux)]] ; une ligne vide = espace."""
    lines = []
    for raw in text.strip('\n').split('\n'):
        raw = raw.strip()
        if not raw:
            lines.append(None)
            continue
        words = []
        style = None
        if raw.startswith('#'):
            style, raw = raw[1:].split(' ', 1)
        for tok in raw.split():
            m = re.match(r'^(.*?)(\{(.*)\})?$', tok)
            word, flags = m.group(1), {}
            if m.group(3):
                for kv in m.group(3).split(','):
                    k, _, v = kv.partition('=')
                    try:
                        flags[k] = float(v)
                    except ValueError:
                        flags[k] = v if v else True
            words.append((word, flags))
        lines.append((style, words))
    return lines


def align(words, toks):
    """Apparie la liste de mots des paroles aux mots reconnus."""
    a = [norm(w) for w in words]
    b = [norm(t[0]) for t in toks]
    times = [None] * len(words)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            for k in range(i2 - i1):
                times[i1 + k] = (toks[j1 + k][1], toks[j1 + k][2])
        elif op == 'replace' and (i2 - i1) == (j2 - j1):
            for k in range(i2 - i1):
                times[i1 + k] = (toks[j1 + k][1], toks[j1 + k][2])
        elif op == 'replace':
            # n mots ↔ m mots : on répartit l'intervalle reconnu au prorata des longueurs
            t0, t1 = toks[j1][1], toks[j2 - 1][2]
            lens = [max(1, len(a[i])) for i in range(i1, i2)]
            tot, acc = sum(lens), 0
            for k, i in enumerate(range(i1, i2)):
                s = t0 + (t1 - t0) * acc / tot
                acc += lens[k]
                times[i] = (s, t0 + (t1 - t0) * acc / tot)
    # interpolation des mots restés sans minutage
    n = len(words)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        lo = times[i - 1][1] if i > 0 else (times[j][0] - 0.3 * (j - i) if j < n else 0)
        hi = times[j][0] if j < n else lo + 0.3 * (j - i)
        lens = [max(1, len(a[k])) for k in range(i, j)]
        tot, acc = sum(lens), 0
        for k in range(i, j):
            s = lo + (hi - lo) * acc / tot
            acc += lens[k - i]
            times[k] = (s, lo + (hi - lo) * acc / tot)
        i = j
    # pas de chevauchement, durée minimale
    for k in range(n):
        s, e = times[k]
        if k > 0:
            s = max(s, times[k - 1][1])
        times[k] = (s, max(e, s + 0.06))
    return times


def fixed(spec):
    """Minutage saisi à la main : « mot@t0:t1 … »."""
    out = []
    for tok in spec.split():
        w, _, tt = tok.rpartition('@')
        a, b = tt.split(':')
        out.append([w, float(a), float(b)])
    return out


# --- Paroles ---------------------------------------------------------------------

REFRAIN = """
Provoquer réflexion, c'est ça ma mission
La priorité, c'est pas d'être sapé en Christian{strike=dior} Dior{strike=dior}
Impacter ma ville et puis les nations{NATIONS}

Le diable travaille tout le temps
Pendant que le chrétien dort{DORT}
"""
FIN_COURTE = """
Impacter{heavy=1.0,hit=1.0}
Les nations, je dois impacter{heavy=1.3,hit=1.3}
Impacter{heavy=1.6,hit=1.6}
"""
FIN_LONGUE = """
Impacter{heavy=1.0,hit=1.0}
Les nations, je dois impacter{heavy=1.2,hit=1.2}
Impacter{heavy=1.4,hit=1.4}
Les nations, je dois impacter{heavy=1.6,hit=1.6}
"""


def refrain(nations_flag='', fin=FIN_LONGUE, dort=''):
    txt = REFRAIN.replace('{NATIONS}', '{' + nations_flag + '}' if nations_flag else '')
    txt = txt.replace('{DORT}', '{ev=' + dort + '}' if dort else '')
    return txt + '\n' + fin


PAGES = [
    dict(name='p1_refrain1', t_in=0.0, enter='intro', light='bougie', tilt=-0.9, pen=-38,
         text="""
#entete C'est A.L.V.A.N
#entete C'est pour la gloire{ev=gloire} de Dieu
""" + '\n' + refrain('drop=villes', FIN_COURTE, 'dort'),
         src=[('al_intro.txt', 0, 18), ('al_r1.txt', 18, 37)]),
    dict(name='p2_refrain1b', t_in=36.0, enter='glisse', light='bougie', tilt=1.2, pen=-46,
         text=refrain('', FIN_COURTE), src=[('al_r1b.txt', 36, 47.6), ('al_e2.txt', 47.5, 53.0)]),
    dict(name='p3_couplet1', t_in=54.0, enter='glisse_vite', light='bougie', tilt=-1.6, pen=-34,
         text="""
J'ai le respect des meilleurs, et pourtant j'en fais pas partie
En rap, c'est vrai, suis fort, mais parfois ma foi en pâtit
Je{ev=loin} les regardais de loin, maintenant je fais partie de la partie{ev=dedans}

#titre Impact,{ev=titre} titre de ce son.{ev=titre_fin}

J'ai capté
Que ma vie était du mauvais côté
J'ai capté
Que pour réussir, fallait que je change de côté{ev=flip}
""", src=[('al_v1a.txt', 52.3, 64.3), ('al_v1.txt', 64.3, 68.1)]),
    dict(name='p3_verso', t_in=68.02, enter='retourne', light='bougie', tilt=-1.0, pen=-40,
         text="""
J'ai capté
Dans le péché, j'étais enfoncé{ev=enfonce}
Alors{ev=priere} j'ai prié en ayant la foi
Qu'écouté, je serai{ev=priere_fin}

J'ai capté, l'important, c'était pas de faire crier les foules
Ou chaque soir faire trop le fou
Avec des filles qui défilent

J'ai capté que, pour réussir, fallait que je me maintienne
Hier, j'ai choisi le Christ
À demain, je me maintiens

J'ai capté
Que tous mes choix avaient des conséquences{drop=simple}
C'est con, c'est quand je l'ai vécu
Que j'ai compris qu'en vérité

Être chrétien, c'est pas que{heavy=0.5} pour soi
Les prières, c'est pas que{heavy=0.5} le soir
Servir Dieu, c'est pas que{heavy=0.5} ça{underline=ligne}
""", src=[('al_v1.txt', 68.1, 80.95), ('fix', 'me@80.98:81.08 maintiens.@81.08:81.45'), ('al_v1.txt', 81.5, 91)]),
    dict(name='p4_refrain2', t_in=90.95, enter='glisse', light='ville', tilt=0.8, pen=-44,
         text=refrain('drop=simple', FIN_LONGUE, 'dort2'),
         src=[('al_r2.txt', 90, 101.5), ('al_e3.txt', 101.3, 109.0)]),
    dict(name='p5_refrain2b', t_in=108.85, enter='glisse', light='ville', tilt=-2.0, pen=-36,
         text=refrain('', FIN_LONGUE), src=[('al_r2.txt', 108.9, 119.0), ('fix', 'Impacter.@119.56:119.92'), ('al_e4.txt', 120.0, 126.3)]),
    dict(name='p6_couplet2', t_in=126.15, enter='glisse_vite', light='ville', tilt=1.5, pen=-42,
         text="""
Pour la gloire
J'ai fait des bêtises, pardonne-moi
Pour être accepté dans mon quartier, j'ai perdu une part de moi{ev=dechire}
Épargne-moi
Parle,{ev=eau} car si je me noie
Dans mon péché
Personne pourra m'empêcher de perdre le nord{ev=nord}
Je crois en toi{ev=calme}
Et c'est pour ça que je prie encore
Je prie encore
Je prie au cas où le péché{ev=corde} me jette une corde
M'agrippe au cou
Me met dans un coffre{ev=coffre} et me ramène dans mes conneries
Suis sérieux, Père,{ev=pere} si je bé-tom, je vais plus gole-ri
Avec Holy, je rallie les foules
C'est pas qu'une question de force
""", src=[('al_v2.txt', 126.0, 146.55)]),
    dict(name='p7_couplet2b', t_in=146.5, enter='glisse_vite', light='ville', tilt=-1.2, pen=-38,
         text="""
Devant{ev=demons} les démons, je défile, pas peur
Alors ils se cachent dans la foule
Ils prennent peur quand je prêche{heavy=1.0,ev=preche} fort{heavy=1.4}
Et donc ils fuient{ev=fuient} quand je défile, par peur{ev=fuient_fin}

En chasse pour gagner des âmes
Soldat du diable, j'vais désarmer
Pour ça, je prendrai pas des années

Christ, plus puissant que Super Saiyan
J'ai le Saint-Esprit,{ev=esprit} donc ça y est
Devant{ev=releve} moi, les démons s'alignent
Je marcherai pas la tête basse
J'ai le Seigneur, j'ai mon salut.{ev=salut}
""", src=[('al_v2.txt', 146.5, 163)]),
    dict(name='p8_refrain3', t_in=162.6, enter='glisse', light='aube', tilt=0.6, pen=-40,
         text=refrain('drop=villes', FIN_LONGUE), src=[('al_r3.txt', 162.5, 172.9), ('al_e5.txt', 172.8, 180.9)]),
    dict(name='p9_refrain3b', t_in=180.75, enter='glisse', light='aube', tilt=-0.8, pen=-44,
         text=refrain('', FIN_LONGUE) + """

#signature IMPACT{ev=impact_titre}
#signature2 A.L.V.A.N{ev=signe}
""", src=[('al_r3.txt', 180.9, 191.0), ('al_e6.txt', 190.5, 201)],
         extra=fixed('IMPACT@201.4:204.6 A.L.V.A.N@205.2:208.0')),
]


def build():
    out = {'pages': []}
    for p in PAGES:
        lines = parse_text(p['text'])
        flat = [w for ln in lines if ln for w, _ in ln[1]]
        toks = []
        for src in p['src']:
            toks += fixed(src[1]) if src[0] == 'fix' else tokens(*src)
        n_extra = len(p.get('extra', []))
        main = flat[:len(flat) - n_extra]
        times = align(main, toks) + [(e[1], e[2]) for e in p.get('extra', [])]
        k = 0
        page_lines = []
        for ln in lines:
            if ln is None:
                page_lines.append({'blank': True})
                continue
            style, words = ln
            ws = []
            for w, flags in words:
                t0, t1 = times[k]
                k += 1
                ws.append([w, round(t0, 3), round(t1, 3)] + ([flags] if flags else []))
            d = {'words': ws}
            if style:
                d['style'] = style
            page_lines.append(d)
        q = {kk: v for kk, v in p.items() if kk not in ('text', 'src', 'extra')}
        q['lines'] = page_lines
        out['pages'].append(q)
    # le premier mot d'une feuille ne s'écrit qu'une fois la feuille en place
    for pg in out['pages']:
        first = next(l for l in pg['lines'] if not l.get('blank'))
        first['words'][0][1] = max(first['words'][0][1], pg['t_in'] + 0.12)
        first['words'][0][2] = max(first['words'][0][2], first['words'][0][1] + 0.12)
    out['strikes'] = {}
    path = os.path.join(HERE, 'timings', 'partition.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


if __name__ == '__main__':
    o = build()
    for pg in o['pages']:
        print('==', pg['name'], pg['t_in'])
        for l in pg['lines']:
            if l.get('blank'):
                continue
            print('   ', ' '.join(f"{w[0]}[{w[1]:.2f}]" for w in l['words']))
