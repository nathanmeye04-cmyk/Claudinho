# « MÊME LES SUPER-HÉROS ONT FAIM »
### Halloween à La Pataterie de Limoges — Storyboard & plan de production
Format maître : **9:16 vertical (1080×1920)**, 24 i/s · Durée cible : **~40 s** · Déclinaison 16:9 prévue

---

## 0. Ce qu'il faut savoir avant de commencer (honnêtement)

1. **Je ne peux pas générer la vidéo moi-même** dans cet environnement (aucun modèle vidéo n'y est disponible). Ce document contient donc le storyboard complet + des prompts plan par plan pour Veo 3 / Kling 2.x / Runway Gen-4 / Sora, ainsi que le montage, le son et les voix.
2. **Ce qui est déjà prêt dans le dépôt :**
   - `references/photos/` : vos 15 photos, renommées par usage (R = lieu, P = plat, L = logo).
   - `references/plates_9x16/` : 7 plaques déjà **corrigées de l'effet fisheye** et **recadrées en 9:16**, à donner comme image de départ (*start frame*) aux outils vidéo.
3. **Ma recommandation n°1 pour un rendu « on y croit » : la méthode hybride.** Vos photos sont prises au fisheye avec un vignettage fort. C'est très bien comme référence, mais limité comme décor animé. Une heure de tournage à l'iPhone (4K, vertical, mode Cinématique) dans le restaurant au crépuscule, sans personne dedans, vous donnerait de **vrais plans en mouvement**. On n'insère alors le héros par IA qu'à ces endroits-là. Le décor et les plats restent 100 % réels, et l'IA ne gère que le personnage. C'est ce qui sépare une pub crédible d'une « vidéo IA ».
4. **Règle d'or pour la nourriture :** on ne génère jamais un plat. Les plats viennent **uniquement** de vos photos P01–P03, animées en parallaxe ou en léger travelling, ou mieux, filmés en vrai. Le héros n'est jamais généré en train de toucher la nourriture en gros plan (c'est là que l'IA déforme mains et aliments).
5. **Règle d'or pour les dialogues :** le casque est **fermé pendant toutes les répliques**. La voix passe par un léger filtre « casque ». Résultat : il n'y a aucun problème de synchronisation labiale, qui est le défaut IA le plus visible. Le visage n'apparaît qu'une fois, de dos ou de trois-quarts arrière, au moment où il mange.

---

## 1. Analyse des photographies fournies

| Réf. | Contenu | Verdict | Usage |
|---|---|---|---|
| R01 | Arrière du bâtiment, conteneurs poubelles | ❌ Ne pas utiliser | Image peu valorisante |
| R02 | Terrasse, bambous, grand « P » blanc lumineux, enseigne drapeau | ✅ Excellent | Arrivée du héros (plan d'ouverture), le « P » sert de repère visuel fort |
| R03 | Façade principale, verrière bois, « LA PATATERIE », auvent « BOIRE ET MANGER » | ✅ Plan d'établissement | Atterrissage. **Recadrer à droite pour exclure l'enseigne voisine « La Boucherie »** (marque concurrente). La plaque 9:16 le fait déjà |
| R04 | Portes vertes de la verrière, vitraux stylisés, affiches | ✅ Avec précaution | Approche de la porte. **Masquer/flouter l'affiche « Édition Printemps-Été »** (hors saison) et les prix « Formule déjeuner » (non vérifiés pour Halloween) |
| R05 | Sas intérieur : portes vertes avec **ruban « DO NOT ENTER! »**, fantôme, citrouille, menu déjeuner à la craie, ardoise blind test, chapeaux disco | ⭐ Pépite comique | Le ruban est **réellement** sur vos portes : gag d'entrée parfait (voir P05) |
| R06 | Hall flou | ❌ Trop flou | Inutilisable, même en référence |
| R07 | Bar carrelage vert, bouteilles, guirlande de fanions Halloween orange, suspensions en verre | ✅ Excellent | Plan « enquête » au bar |
| R08 | Salle sous charpente, toiles d'araignée, table-tonneau avec **tarte aux pommes sous cloche**, ardoise « Tarte aux pommes », suspensions en rotin | ⭐ Plan signature | Plan d'ambiance Halloween le plus fort. La tarte est un vrai produit photographié |
| R09 / R10 | Mur noir avec portraits anciens couverts de toiles d'araignée, grande suspension en rotin, salle en enfilade | ✅ Très cinéma | « Scène de crime » : les portraits « l'observent » |
| R11 | Longue salle, banquette orange, suspensions noires, tables dressées | ✅ | Table du héros et plan large de fin |
| P01 | Cocktail passion/orange, menthe, orange séchée, + boisson framboise + mug cuivré | ✅ | Insert convivialité |
| P02 | Travers laqué, chips de pommes de terre maison, ciboulette, assiette à motifs verts | ⭐ Plat héros | LE plat de la séquence 3 |
| P03 | Gaufre, chantilly, glace chocolat, noisettes, coulis | ✅ | Dessert / plan final appétissant |
| L01 | Logo officiel noir « Restaurant La Pataterie depuis 1996 » | ✅ | Carton final (à passer en blanc sur fond sombre) |

**Décor d'Halloween déjà présent (réel, donc rien à inventer) :** fanions oranges, toiles d'araignée, fantôme suspendu, citrouille, squelette visible derrière la vitre, ruban « DO NOT ENTER ». Il suffit d'ajouter **2 ou 3 vraies citrouilles** (bougies LED) devant la façade si vous tournez. Pas de citrouilles générées par IA dans le décor.

**À ne pas montrer :** La Boucherie, l'affiche Printemps-Été, les prix, la voiture garée (sauf si elle est floue), la plaque d'immatriculation.

---

## 2. Le personnage (bible de continuité)

**Nom : LE COMMANDEUR.** Le nom porte le gag final : « Je prends les commandes. »
**IA embarquée : ÉCHO.** C'est une voix féminine, calme, pince-sans-rire.
> ⚠️ Le brief contient « Jarvis » : c'est le nom de l'IA d'Iron Man (Marvel/Disney). Je l'ai remplacé par **ÉCHO** pour éviter tout risque de marque. Dans la même logique, l'armure ne doit pas ressembler à Iron Man : pas de disque lumineux sur la poitrine, pas de masque à fente en « T », pas de lignes de visage dorées façon Iron Man.

**Design de l'armure (identique dans chaque plan) :**
- Rouge carmin profond, mat satiné, avec des **filets d'or brossé** gravés en chevrons.
- Plaques segmentées façon armure de chevalier moderne : épaulières larges et arrondies, gantelets articulés.
- **Casque** lisse et arrondi, avec une **visière horizontale unique couleur ambre** qui s'illumine quand il parle.
- **Cape courte vert sapin** (le vert de La Pataterie) qui tombe de l'épaule gauche uniquement. C'est un clin d'œil à la marque et un très bon repère de continuité.
- Emblème sur la poitrine : un **chevron doré abstrait** (aucun logo existant).
- Taille : 1,85 m, carrure athlétique, sans exagération.

**Personnalité :** il se croit dans un film d'action alors qu'il est dans un restaurant. Il joue au premier degré, sans jamais faire de clin d'œil caméra. L'humour vient d'ÉCHO et des silences.

**Workflow de cohérence (indispensable) :**
1. Générer d'abord une **fiche personnage** (Midjourney v7 / Flux / Imagen) : face, profil, dos, casque ouvert.
2. Choisir UNE image et l'utiliser comme **référence personnage** dans chaque plan (Runway Gen-4 « References », Kling « Elements », Veo « ingredients »).
3. Pour chaque plan : **image de départ = plaque 9:16 réelle + héros incrusté** (Photoshop IA / Nano Banana / Flux Kontext), puis image→vidéo. On n'utilise jamais le text→vidéo seul.

**Prompt maître du personnage (à coller en tête de chaque prompt) :**
```
CHARACTER "LE COMMANDEUR": a 1.85m athletic superhero in an original sleek armor of deep crimson satin-matte plates with brushed-gold engraved chevron filigree, rounded knight-like shoulder pauldrons, articulated gauntlets, a smooth rounded helmet with a single horizontal amber glowing visor band (no face slits), an abstract golden chevron emblem on the chest (no glowing chest circle), and a short forest-green cape draped over the LEFT shoulder only. Identical design in every shot.
```

**Prompt négatif commun :**
```
no Iron Man, no Marvel, no arc reactor, no T-shaped faceplate, no extra fingers, no deformed hands, no morphing armor, no text, no watermark, no logo distortion, no extra people, no warped food, no fisheye distortion, no cartoon look, no plastic skin
```

---

## 3. Storyboard plan par plan

Timeline totale ≈ **40 s**. Le brief autorise un léger dépassement si c'est utile : les 5 s supplémentaires servent à laisser respirer les silences comiques.

### SÉQUENCE 1 — UNE MISSION INATTENDUE (0:00 – 0:06)

**P01 — L'accroche · 0:00–0:02 (2 s)**
- **Cadrage :** très gros plan sur la visière ambre qui s'allume dans le noir. Reflet de lumières oranges dans la visière.
- **Caméra :** fixe, micro-poussée avant.
- **Action :** la visière s'allume en balayage gauche→droite. Des données HUD défilent en reflet (flou, illisible volontairement).
- **Dialogue (ÉCHO, off) :** « Activité inhabituelle détectée dans ce secteur. »
- **Son :** drone grave, battement de cœur synthétique, « bip » d'allumage.
- **Réf. :** fiche personnage.
- **Transition :** cut sec sur un coup de basse.

**P02 — L'atterrissage · 0:02–0:04 (2 s)**
- **Cadrage :** plan large, contre-plongée, sur la façade (R03). L'enseigne « LA PATATERIE » est éclairée en haut du cadre. Heure bleue, ciel violet-gris.
- **Caméra :** caméra basse au ras du bitume, léger tilt-up.
- **Action :** le héros atterrit genou au sol sur le parking, devant le ponton bois. Un petit souffle soulève 2–3 feuilles mortes, et la cape retombe. **Pas de cratère ni d'explosion** : on reste crédible.
- **Son :** whoosh descendant, impact sourd métallique, cliquetis d'armure.
- **Réf. :** `plates_9x16/R03_facade_parking_9x16.jpg`, passée en nuit (étalonnage bleu + enseigne lumineuse).
- **Transition :** coupe dans le mouvement quand il se relève.

**P03 — La réplique · 0:04–0:06 (2 s)**
- **Cadrage :** plan taille, 3/4 face, en légère contre-plongée. Le grand « P » lumineux (R02) est en arrière-plan flou.
- **Caméra :** lent travelling circulaire de 15°.
- **Action :** il se relève et tourne la tête vers le restaurant. La visière pulse à chaque mot.
- **Dialogue (COMMANDEUR) :** « Enfin une mission à ma hauteur. »
- **Son :** la musique d'action démarre (cuivres + percussions).
- **Réf. :** `plates_9x16/R02_terrasse_logo_P_9x16.jpg`.
- **Transition :** cut sur son premier pas.

### SÉQUENCE 2 — L'ENQUÊTE (0:06 – 0:17)

**P04 — Approche · 0:06–0:08 (2 s)**
- **Cadrage :** plan de dos, sur l'épaule. Il avance vers les portes vertes de la verrière (R04), et les vitraux stylisés sont éclairés de l'intérieur.
- **Caméra :** steadicam qui le suit.
- **Action :** il marche d'un pas assuré sur l'allée en bitume, entre les deux pontons.
- **Son :** pas métalliques, musique tendue.
- **Réf. :** `plates_9x16/R04_entree_verriere_portes_9x16.jpg` (affiches floutées ou remplacées par un aplat sombre).
- **Transition :** match-cut sur la poignée de porte.

**P05 — Le gag du ruban (ajout) · 0:08–0:11 (3 s)**
- **Cadrage :** plan moyen frontal sur les portes intérieures vertes avec le ruban jaune « DO NOT ENTER! » (R05). Le héros entre dans le champ par la droite.
- **Caméra :** fixe, composition symétrique.
- **Action :** il s'arrête net devant le ruban. Il penche légèrement la tête. Pause. Puis il pousse la porte, simplement (le ruban est collé en diagonale et ne le gêne pas).
- **Dialogue (ÉCHO) :** « Accès interdit. » — (COMMANDEUR, imperturbable) : « C'est une décoration. »
- **Son :** la musique coupe d'un coup pendant la pause, puis repart. Grincement de porte.
- **Réf. :** `plates_9x16/R05_sas_portes_do_not_enter_9x16.jpg`.
- **Transition :** la porte s'ouvre et la caméra passe à travers (cut caché sur le battant).
- *Plan optionnel : il peut sauter si la vidéo doit faire 35 s pile.*

**P06 — La « scène de crime » · 0:11–0:13 (2 s)**
- **Cadrage :** plan large du mur aux portraits anciens couverts de toiles d'araignée (R09/R10). Le héros est de profil, il scanne la pièce.
- **Caméra :** panoramique lent gauche→droite.
- **Action :** un fin faisceau ambre balaie les portraits depuis sa visière (effet discret).
- **Son :** bip de scan, ambiance de salle feutrée (couverts, murmures lointains).
- **Réf. :** R10 (de préférence en plaque 9:16 corrigée à faire), R09.
- **Transition :** suivre le faisceau jusqu'au bar.

**P07 — L'interrogatoire · 0:13–0:17 (4 s)**
- **Cadrage :** plan américain au bar (R07). Il est accoudé au comptoir carrelé vert, avec les fanions Halloween oranges au-dessus et les bouteilles éclairées derrière.
- **Caméra :** fixe, puis lent push-in sur la visière.
- **Action :** il se tourne vers la porte de cuisine (hors champ).
- **Dialogue :**
  - COMMANDEUR : « Attendez… toute cette activité vient de la cuisine ? »
  - ÉCHO : « Concentration anormalement élevée de bonnes odeurs. »
  - *(silence d'une seconde, la visière clignote une fois)*
  - COMMANDEUR : « Je prends les commandes. »
- **Son :** la musique s'arrête sur « odeurs ». Le silence porte le gag. Petit « ding » de cuisine juste après « commandes ».
- **Réf. :** `plates_9x16/R07_bar_salle_9x16.jpg`.
- **Transition :** le « ding » de cuisine lance le plan suivant.

### SÉQUENCE 3 — LE REPAS DEVIENT LA PRIORITÉ (0:17 – 0:29)

**P08 — L'arrivée du plat · 0:17–0:20 (3 s)**
- **Cadrage :** gros plan sur le **travers laqué + chips maison** (P02), lumière chaude, faible profondeur de champ.
- **Caméra :** lent travelling avant à hauteur d'assiette, avec une légère vapeur.
- **Action :** l'assiette est posée sur la table (seules les mains d'un serveur sont visibles, ou bien un simple plan fixe animé).
- **Son :** la musique bascule en version « révélation » : les mêmes notes, mais douces, cordes chaudes. On entend la sauce grésiller légèrement.
- **Réf. :** **P02 exclusivement**, en animation 2.5D/parallaxe (CapCut « 3D zoom », Runway « camera control » à mouvement minimal) ou en vrai tournage.
- **Transition :** cut sur le reflet.

**P09 — Le reflet · 0:20–0:22 (2 s)**
- **Cadrage :** très gros plan sur la visière ambre, où se **reflète l'assiette**.
- **Caméra :** fixe.
- **Action :** la visière passe lentement d'ambre à doré chaud, comme des yeux qui s'écarquillent.
- **Son :** petit son « HUD » qui monte d'une octave.
- **Réf. :** fiche personnage + P02 incrustée en reflet.

**P10 — La décision · 0:22–0:26 (4 s)**
- **Cadrage :** plan taille. Il est assis sur la banquette orange (R11), l'assiette devant lui, avec la grande suspension en rotin au-dessus.
- **Caméra :** fixe, cadre centré, très « Wes Anderson ».
- **Action :** il pose les deux mains à plat sur la table, solennel. **Les mains restent immobiles** : c'est un choix de mise en scène qui protège aussi des déformations IA.
- **Dialogue :**
  - COMMANDEUR : « Écho, annule la mission. J'ai trouvé plus important. »
  - ÉCHO : « Vous êtes en train de sauver le monde ? »
- **Son :** ambiance de salle seule, sans musique.
- **Réf. :** `plates_9x16/R11_salle_longue_banquette_9x16.jpg`.

**P11 — La chute · 0:26–0:29 (3 s)**
- **Cadrage :** plan de dos / 3/4 arrière. On voit l'arrière du crâne et une oreille, **jamais le visage de face**.
- **Caméra :** fixe.
- **Action :** il lève le casque à deux mains, avec un sifflement pneumatique, et le pose à côté de l'assiette.
- **Dialogue :** COMMANDEUR, voix désormais **sans filtre**, plus humaine : « Non. Ma soirée. »
- **Son :** « pshhh » de décompression, puis la musique chaleureuse reprend.
- **Réf. :** R11 + fiche personnage « casque retiré, de dos » (cheveux bruns courts, nuque, rien de plus).
- **Transition :** cut sur la fourchette.

### SÉQUENCE 4 — LA CONVIVIALITÉ (0:29 – 0:36)

**P12 — Montage chaleur (4 plans × 1 s) · 0:29–0:33**
1. Fourchette qui croque dans une chip (P02, plan réel ou parallaxe).
2. Cocktail passion qui scintille (P01).
3. Tarte aux pommes sous cloche avec toiles d'araignée (R08).
4. Large de la salle avec suspensions allumées (R11). Si vous avez des **photos de clients avec leur accord**, elles vont ici.
- **Caméra :** micro-mouvements uniquement.
- **Son :** musique chaleureuse, rires et trinquage en ambiance.
- **Réf. :** P01, P02, `R08_salle_tarte_escalier_9x16.jpg`, R11.

**P13 — La morale · 0:33–0:36 (3 s)**
- **Cadrage :** plan moyen. Il est détendu sur la banquette, cape sur le dossier, de 3/4 arrière, avec la gaufre (P03) devant lui.
- **Caméra :** lent travelling arrière.
- **Dialogue (COMMANDEUR, off ou de dos) :** « Pour Halloween, faites-vous peur avec les histoires… pas avec votre faim. »
- **Son :** la musique monte vers la fin.
- **Réf. :** R11 + P03.

### SÉQUENCE 5 — SIGNATURE (0:36 – 0:40)

**P14 — Plan final · 0:36–0:38 (2 s)**
- La façade de nuit (R03), enseigne allumée, citrouilles au sol. Le casque du héros est posé seul sur une table de terrasse : il est resté dîner.
- **Texte animé (police lisible, en surimpression, pas générée par IA) :** « Cet Halloween, vivez votre propre aventure à La Pataterie de Limoges. »

**P15 — Carton logo · 0:38–0:40 (2 s)**
- Fond noir mat, **logo officiel L01 en blanc** (inversé proprement), « Depuis 1996 ».
- **Infos pratiques :** *uniquement celles que vous me confirmerez* (adresse, réservation, dates). Rien n'est inventé.
- **Son :** accord final, puis ÉCHO en voix off chuchotée : « Mission… délicieuse. » *(optionnel)*

---

## 4. Prompts plan par plan (image→vidéo)

> Mode d'emploi : `[CHARACTER]` = prompt maître du §2. Toujours fournir l'**image de départ** (plaque 9:16 + héros incrusté) et la **référence personnage**. Ratio 9:16, 5 s générées pour garder les meilleures 2–4 s. Ajouter le prompt négatif.

**P01**
```
[CHARACTER] Extreme close-up of the helmet's single horizontal amber visor band lighting up left-to-right in near darkness, faint warm orange bokeh reflections on the curved visor, blurred abstract HUD glints, slow push-in, cinematic anamorphic look, shallow depth of field, 24fps, photorealistic.
```
**P02**
```
[CHARACTER] Wide low-angle shot at blue hour in front of the real restaurant facade from the start frame (black corrugated cladding, wooden gabled glass entrance, illuminated "LA PATATERIE" sign). The hero lands on one knee on the asphalt parking lot near the wooden deck, small realistic gust lifts a few dry leaves, cape settles. Camera low near ground, slight tilt up. Keep the building, sign and layout exactly as in the start frame. Realistic weight, no explosion, no crater.
```
**P03**
```
[CHARACTER] Medium shot, slight low angle, hero rises from kneeling and turns his head toward the restaurant; the large white illuminated "P" logo on black cladding softly out of focus behind him, bamboo planters, string lights. Slow 15-degree orbit. Amber visor pulses gently. Dusk, cool ambient vs warm restaurant glow.
```
**P04**
```
[CHARACTER] Over-the-shoulder follow shot from behind, hero walks confidently toward green-framed glass doors under a wooden gable with white stylized stained-glass patterns lit from inside, wooden decking on both sides, warm interior light spilling out. Steadicam, smooth. Keep architecture identical to start frame.
```
**P05**
```
[CHARACTER] Symmetrical frontal medium shot of two green wooden double doors with glass panes crossed by yellow "DO NOT ENTER" tape (as in start frame), dark wood-paneled vestibule, patterned armchair on the right. Hero steps in from the right, stops, tilts his head slightly, holds still for one second, then calmly pushes the door open. Static camera. Do not alter the tape text.
```
**P06**
```
[CHARACTER] Wide shot, hero in profile scanning a dark navy wooden wall covered with antique black-and-white framed portraits draped in fake spider webs, a large woven rattan pendant lamp glowing warm. A thin subtle amber light beam sweeps from his visor across the frames. Slow pan left to right. Moody, warm practical lighting.
```
**P07**
```
[CHARACTER] Medium-wide "american" shot, hero leaning one forearm on a bar counter clad in green square tiles with a steel top, backlit shelves of bottles, orange Halloween pennant garland on wooden beams, ribbed glass pendant lights. He slowly turns his head toward an off-screen kitchen door. Static camera then slow push-in toward the visor. Hands stay still on the counter.
```
**P08** — *ne pas générer de nourriture* : animer `P02_travers_chips.jpg` avec un mouvement de caméra uniquement.
```
Subtle slow dolly-in on the exact still image, preserve the dish exactly (glazed rib, potato chips, chives, green-patterned plate), add only faint rising steam, no changes to food shape, colors or plating.
```
**P09**
```
[CHARACTER] Extreme close-up of the amber visor; in its curved reflection a plate of glazed ribs with golden potato chips. The visor glow shifts slowly from amber to warm gold. Static, shallow depth of field.
```
**P10**
```
[CHARACTER] Centered symmetrical medium shot, hero seated on a burnt-orange velvet banquette at a light wood table set with placemats, a plate in front of him, warm black dome pendant lamps, terracotta herringbone tile floor, long dining room receding. He solemnly places both hands flat on the table and stays still. Static camera. Hands must remain still and anatomically correct.
```
**P11**
```
[CHARACTER] Three-quarter rear shot from behind his right shoulder (face never visible), hero lifts the helmet off with both hands with a small pneumatic hiss of vapor, revealing short dark brown hair and the back of his neck, and sets the helmet on the table beside the plate. Static camera, warm light. Never show the face from the front.
```
**P13**
```
[CHARACTER, helmet off, seen from behind] Relaxed hero leaning back on the orange banquette, green cape over the backrest, a waffle with whipped cream on the table, warm dining room glow with rattan lamps. Slow dolly-out. Calm, cozy.
```
**P14**
```
Night exterior of the restaurant facade from the start frame, illuminated sign, a few real carved pumpkins with warm candle light on the wooden deck, and the hero's crimson helmet with amber visor resting alone on a terrace table. Very slow push-in. Keep building and sign identical.
```

---

## 5. Voix, musique, son

| Élément | Recommandation |
|---|---|
| **Voix du COMMANDEUR** | Homme 35–45 ans, grave, assuré, un peu théâtral. ElevenLabs (voix originale, FR) ou **mieux : un vrai comédien local** enregistré au smartphone en cabine improvisée. Filtre casque : EQ passe-bande 300 Hz–5 kHz + léger reverb métallique (désactivé après P11) |
| **Voix d'ÉCHO** | Femme, posée, pince-sans-rire, tempo lent. Légère modulation numérique |
| **Musique** | Originale ou libre de droits (Artlist, Epidemic, Suno avec licence commerciale). **3 mouvements :** suspense action (0–0:13) → coupure nette → version « révélation » douce aux cordes (0:17–0:29) → thème chaleureux et festif (0:29–fin). Ne jamais imiter un thème Marvel/Avengers |
| **Bruitages** | Servos d'armure discrets, pas métalliques, whoosh, « ding » de cuisine, grésillement, couverts et murmures de salle |
| **Mix** | Dialogues à −12 dB LUFS-short, musique ducking −8 dB sous les voix. **Sous-titres incrustés** obligatoires (85 % des Reels sont vus sans le son) |

---

## 6. Montage & étalonnage

- **Outils :** CapCut Desktop ou Premiere/DaVinci.
- **Rythme :** coupes rapides en Séq. 1 (2 s/plan), puis 3–4 s en Séq. 2–3, avec **1 s de silence** après « bonnes odeurs » et après « sauver le monde ? ». Les rires viennent de ces silences.
- **Étalonnage :** extérieurs en bleu nuit froid, intérieurs en ambre/cuivre chaud. On garde le rouge de l'armure saturé mais pas fluo. On applique le même LUT sur les plans IA et sur les vraies photos, pour qu'ils se fondent.
- **Correction fisheye :** les plaques fournies sont déjà corrigées. Pour d'autres photos, utiliser *Lens correction* dans Lightroom ou DaVinci.
- **Sous-titres :** police sans-serif grasse, blanc avec ombre, dans le tiers central. On évite les 20 % du bas et les 15 % de droite, qui sont recouverts par l'interface TikTok/Instagram.

## 7. Déclinaison 16:9 (YouTube)

Tous les plans sont composés avec le sujet **dans le tiers central**. Pour le 16:9 :
- reprendre les photos d'origine non recadrées (elles sont en 4:3), corrigées du fisheye ;
- refaire générer P02, P04, P10 et P14 en 16:9 avec le même prompt, pour profiter de la largeur de la façade et de la salle ;
- garder les inserts nourriture en 9:16 dans un cadre flouté, ou les recadrer en 16:9 (P01–P03 sont en 2:3, ce qui donne un recadrage serré).

---

## 8. Checklist qualité avant publication

- [ ] L'armure est identique dans tous les plans (cape à **gauche**, visière unique, chevron)
- [ ] Aucun plan ne montre de mains déformées ni d'objet qui traverse une surface
- [ ] Les plats sont strictement identiques aux photos P01–P03
- [ ] La Boucherie, l'affiche Printemps-Été, les prix et les plaques d'immatriculation sont absents
- [ ] Le logo est le fichier officiel, et non une version générée
- [ ] Toutes les répliques ont le casque fermé, sauf « Non. Ma soirée. », dite de dos
- [ ] Les sous-titres sont relus et lisibles
- [ ] **Mention « contenu généré/modifié par IA »** activée sur Instagram/TikTok (obligatoire)
- [ ] Validation par la franchise La Pataterie (charte de marque) avant diffusion
- [ ] Accord écrit des clients et du personnel visibles

## 9. Ce qu'il me manque de votre part

1. **Dates et horaires** de la période Halloween, et s'il y a une **animation réelle** (l'ardoise du sas mentionne un blind test le jeudi soir : est-il maintenu pendant Halloween ?). Rien ne sera affiché sans confirmation.
2. **Modalité de réservation** (téléphone, site, lien) et l'adresse exacte à afficher.
3. Le **logo en vectoriel / PNG transparent** (le JPG fourni a un fond blanc).
4. Idéalement : 1 h de tournage iPhone au crépuscule (liste de plans = P02, P04, P05, P06, P07, P10, P12, P14, pris **sans** le héros).
