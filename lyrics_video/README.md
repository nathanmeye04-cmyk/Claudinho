# « Où est Dieu ? » — Leobenjo x Nathan · Lyrics video VHS / CRT

Lyrics video vertical pour Instagram Reels et TikTok, 1080 × 1920, 30 i/s, durée 2 min 51.

| Fichier | Contenu |
|---|---|
| `lyrics_video_ou_est_dieu_1080x1920.mp4` | vidéo finale (H.264 + AAC) |
| `paroles.txt` | paroles originales, reprises sans aucune modification |
| `sync_paroles.json` | synchronisation mot par mot (début et fin de chaque mot, en secondes) |
| `src/transcribe.py` | détection de la voix (faster-whisper medium, horodatage par mot) |
| `src/align.py` | calage des paroles originales sur la voix détectée |
| `src/render.py` | moteur de rendu : montage, étalonnage, VHS/CRT, typographie, contrôle qualité |
| `fonts/` | Instrument Serif (romain + italique), Antonio, VT323 (licence SIL OFL) |

## Intention

Le montage ne suit pas un schéma imposé : chaque image est choisie pour ce que dit la phrase à ce moment-là. On trouve la pluie et la vitre pendant l'attente, un regard pour « je dois reconnaître », le paysage qui défile sur « je partage ce que j'ai vu », un père et son fils sur « un enfant qui fuit son père », un oiseau en vol sur « je me serais envolé », les pas d'un marcheur sur « la lumière qui guide chacun de mes pas ». La pluie, la ville, les visages, les routes et les paysages alternent sans enchaîner les images tristes, et sans clichés religieux (ni bougies, ni croix, ni mains jointes).

**30 plans** pour 2 min 51 : un plan dure en moyenne environ 6 s, soit deux mesures du morceau (≈ 88 BPM). On change d'image quand le sens change, pas à chaque phrase.

## Direction artistique

- **Étalonnage unique**, identique sur tout le clip : noirs délavés brun-bleuté, désaturation légère (58 %), contraste doux, hautes lumières beige vieilli.
- **Signal VHS** : luminance légèrement molle, chrominance baveuse et décalée de 4 à 5 px (signal composite), grain analogique, lignes de balayage CRT très discrètes, vignettage, bruit de changement de tête en bas de l'image (dans la zone d'interface, sans paroles).
- **Défauts de tracking** (bande qui roule, décalage horizontal) seulement aux débuts de parties : 0,5 s, 20,0 s, 42,3 s, 53,8 s, 85,8 s, 117,3 s, 138,8 s. Une micro-imperfection d'une image apparaît de temps en temps.
- **Affichage du caméscope** (VT323) : PLAY / SP au démarrage de la cassette, date et heure sur l'archive familiale (42,3 s), STOP à la fin.
- Mouvement lent sur chaque plan (zoom de 7,5 % vers l'avant ou l'arrière) ; fondus enchaînés sur les passages contemplatifs ; coupes franches calées sur les mesures.

## Typographie

- **Paroles : Instrument Serif**, un sérif étroit au contraste marqué, dans l'esprit des titrages de clips et des pochettes d'albums des années 90. Couleur crème, ombre douce, légère frange chromatique pour s'intégrer à l'image VHS.
- **Mots porteurs de sens : Instrument Serif Italique, doré**, uniquement quand ils sont dans les paroles : *Dieu*, *Jésus*, *Toi*, *lumière*, *foi*, *amour*, *gloire*.
- **« Où est Dieu ? »** : dans chaque refrain, ces trois mots sont mis en avant en grand italique, sur une ligne à part.
- **Crédits : Antonio** en capitales espacées, à la manière d'un générique télé.
- **Apparitions** : mot par mot dans les passages posés, par groupes de mots dans les refrains et le couplet rapide. Chaque mot entre en fondu avec une légère remontée de 14 px, environ 0,06 s avant qu'il soit chanté.
- **Lisibilité** : un voile sombre très doux apparaît derrière chaque bloc de texte. La taille de base est de 86 px et se réduit automatiquement si une phrase ne tient pas dans la zone sûre.

## Zones de sécurité

D'après `references/instagram/gabarit_zones_reels_1080x1920.png`, la zone libre va de x = 0 à 940 et de y = 220 à 1500. Les paroles sont placées dans un cadre plus strict, **x de 110 à 910 et y de 300 à 1430**, et centrées en x = 520 (décalées à gauche, à l'écart de la colonne de boutons). Ce cadre convient aussi à TikTok (légende en bas, boutons à droite) et au recadrage 4:5 de la grille du profil.

## Contrôle qualité (`python3 src/render.py qc`)

1. **Paroles complètes et fidèles** : 56 lignes sur 56 identiques au texte fourni, aucune reformulation.
2. **Synchronisation** : 506 mots sur 510 sont calés directement sur la voix détectée, les 4 restants par interpolation entre leurs voisins. Les débuts de lignes tombent sur la grille des mesures.
3. **Phrases entièrement visibles** : 0 carton hors zone, chacun est vérifié au pixel près.
4. **Aucun chevauchement** : un carton disparaît avant que le suivant n'apparaisse.
5. **Taille et contraste** : texte crème sur voile sombre ; l'exposition du plan de neige (96 s) a été baissée.
6. **Images et sens** : voir la liste des plans ci-dessous.
7. **Identité vintage** : même traitement VHS/CRT et même étalonnage du début à la fin.
8. **Espérance** : les images s'ouvrent peu à peu (fenêtre, ciel, routes au lever du jour, horizon), au rythme de ce que disent les paroles.

## Liste des plans (sources : Mixkit, licence libre)

| Début | Paroles | Plan (id Mixkit) |
|---|---|---|
| 0,0 | intro | pluie sur une vitre, feu rouge flou (2846) |
| 9,5 | intro + titre | profil d'une femme derrière la vitre mouillée (33379) |
| 20,0 | « En vrai, je dois reconnaître… » | regard à travers les stores (41420) |
| 25,8 | « …Tu es vrai / la relation » | marche de nuit en ville (40746) |
| 31,2 | « Je partage ce que j'ai vu… » | homme pensif à la fenêtre d'un train (25251) |
| 36,6 | « …une conclusion / des cœurs » | brume vue du train (26140) |
| 42,3 | « un enfant de Dieu / qui fuit son père » | père et fils, archive familiale datée (4542) |
| 48,6 | « dans ma chambre… je lève les yeux » | enfant à la fenêtre (32187) |
| 53,8 | « Les années passent… Où est Dieu ? » | jeune femme sous la pluie, regard levé (46707) |
| 59,0 | « je me serais envolé… » | mouette en vol (45246) |
| 64,2 | « marcher dans le noir » | route de nuit dans le brouillard (9678) |
| 67,1 | « la lumière qui guide chacun de mes pas » | pas d'un marcheur (4893) |
| 69,5 | « j'ai besoin de Toi… fortifie ma foi » | homme, les yeux fermés, qui relève la tête (9018) |
| 74,9 | refrain 2 | silhouette qui ouvre une fenêtre (924) |
| 80,3 | « …envolé / pour te voir » | rayons de soleil dans les nuages (9673) |
| 85,8 | « je ne vois pas la fin » | route sinueuse dans le brouillard (48490) |
| 88,2 | « ta gloire… pas la fame » | tours de la ville la nuit (40654) |
| 91,0 | « c'est dur / mes choix » | homme, la tête baissée (4701) |
| 96,3 | « peu studieux / mes erreurs / mes douleurs » | marche sur une voie ferrée enneigée (31942) |
| 101,7 | « failles / fights / femmes » | rue de nuit, néons sous la pluie (4331) |
| 106,6 | « J'ai vécu ton amour… près de Toi » | lumière à travers les arbres (34372) |
| 111,9 | « Mon cœur t'appartient… crazy » | main qui effleure les blés dorés (8864) |
| 117,3 | refrain 3 | marcheur sur un chemin entre les champs (35830) |
| 123,3 | « …envolé / pour te voir » | mouettes au coucher du soleil (9317) |
| 128,2 | « marcher dans le noir / la lumière » | route au lever du jour (52452) |
| 133,5 | « j'ai besoin de Toi… » | jeune homme face à l'horizon (35873) |
| 138,8 | refrain 4 | silhouette qui marche au coucher du soleil (4629) |
| 144,5 | « …envolé / le plus grand de mes vœux » | homme les bras levés, en montagne (36985) |
| 149,6 | outro | lever de soleil sur l'océan (1086) |
| 160,0 | outro + titre | lever de soleil doré (21168) |

## Refaire le rendu

```bash
cd lyrics_video
./fetch_clips.sh                 # retélécharge les plans Mixkit dans clips/
python3 src/render.py qc          # contrôle des zones de sécurité et des paroles
for k in 0 1 2 3; do python3 src/render.py chunk $k 4 & done; wait
./assemble.sh                     # assemblage et ajout de l'audio
```
