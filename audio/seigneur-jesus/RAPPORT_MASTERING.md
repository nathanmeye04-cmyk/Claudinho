# Seigneur Jésus — LeoBenjo ft. Nathan · Rapport de mastering

Ce document décrit le traitement appliqué au fichier fourni (mix stéréo WAV, 44,1 kHz, 16 bits, 2 min 51). Tous les constats viennent de **mesures objectives** (volume perçu, spectre, image stéréo, dynamique), pas d'une écoute humaine. Une validation à l'oreille, au casque et sur enceintes, reste indispensable.

## Fichiers livrés

| Fichier | Usage | Volume perçu | Pic réel (true peak) | Dynamique (LRA) |
|---|---|---|---|---|
| `…_MASTER_24bit_44k.wav` | Master principal, à envoyer au distributeur | -11,0 LUFS | -1,1 dBTP | 5,8 LU |
| `…_STREAMING_-14LUFS_24bit_44k.wav` | Version plus dynamique, calée sur la normalisation de Spotify et YouTube | -14,0 LUFS | -1,2 dBTP | 6,4 LU |
| `…_MASTER_320k.mp3` | Écoute et partage, tirée du master principal | -11,0 LUFS | -0,9 dBTP | 5,8 LU |

Les fichiers sont en 24 bits avec un dither TPDF, et gardent la fréquence de 44,1 kHz de la source : rééchantillonner n'apporterait rien. Aucun échantillon ne sature. Le pic réel reste sous -0,9 dBTP, y compris après encodage MP3.

**Quelle version envoyer ?**
- **Master principal** : pour une sortie officielle et une écoute hors plateforme.
- **Version streaming** : son niveau correspond déjà à celui que Spotify applique, donc ces plateformes ne la modifieront pas. Elle garde un peu plus de respiration.

## Analyse du mix d'origine

- **Sources identifiables par la mesure** : un sub ou une basse très présente, avec une note fondamentale vers 39 Hz ; un instrumental riche dans le bas-médium (pic marqué à 250 Hz) ; des voix et instruments mélodiques entre 1 et 4 kHz ; des cymbales et hi-hats vers 8 à 10 kHz. Tempo estimé : environ 89 BPM (178 en double tempo).
- **Séparation des pistes** : volontairement non tentée, comme demandé. Sur un mix déjà assemblé, elle aurait dégradé le son.
- **Problèmes relevés** :
  1. **Volume très bas** : -21,8 LUFS. Le morceau n'avait pas encore été masterisé.
  2. **Sub dominant** vers 40 Hz (+5,5 dB par rapport à la référence) et **corps de la basse en retrait** entre 100 et 200 Hz (-3 dB). Ça gronde sur un gros système et ça disparaît sur un téléphone.
  3. **Accumulation vers 415 Hz**, qui donne un aspect un peu « boîte ».
  4. **Mix sombre** : la zone de présence (2 kHz) et de brillance (4 à 6,3 kHz) est 4 à 6 dB en retrait, ce qui nuit à l'intelligibilité des voix.
  5. **Basses non centrées** : elles sont 1,75 dB plus fortes à gauche et assez larges en stéréo, alors que le médium et les aigus sont bien centrés.
  6. **Fin coupée net** : le son s'arrête brutalement alors que la musique joue encore (environ -20 dBFS dans la dernière demi-seconde).

## Ce que j'ai repris de la référence, et ce que j'ai écarté

La référence est « Libère-moi » de Brother Dave feat. Junior Bsg, fournie en MP3 à **64 kbps**.

**Repris :**
- Un **équilibre tonal** plus ouvert dans le haut du spectre.
- Une **basse ronde et en mono**.
- Une **dynamique** proche : 5,8 LU pour le master, contre 5,9 LU pour la référence.

**Écarté :**
- **Son niveau** : -9,8 LUFS, avec 563 échantillons saturés et des pics à +0,4 dBFS. C'est hors des bonnes pratiques. Mon master est à -11 LUFS, sans aucune saturation.
- **Ses aigus au-dessus de 11 kHz** : ils ont été supprimés par la compression du MP3, donc ils ne sont pas comparables.
- **Sa répartition du sub** : la référence a son énergie à 31 Hz, ton morceau à 40 Hz. C'est une question de tonalité, pas un défaut, et j'ai gardé la note du morceau.
- **Son image stéréo plus étroite** dans le bas-médium : j'ai conservé l'ampleur propre à ton morceau, qui ne perd que 0,5 LU en mono.

## Chaîne de traitement

Le script complet est dans `chaine_mastering.py`. Tout le traitement se fait en virgule flottante 64 bits.

1. **Nettoyage** : suppression de l'offset continu (DC) et filtre passe-haut doux à 22 Hz (infra-graves inaudibles).
2. **Image stéréo (traitement milieu/côtés)** :
   - basses en mono sous 120 Hz, ce qui corrige aussi le déséquilibre gauche/droite (+1,08 dB → -0,08 dB) ;
   - léger élargissement des côtés seulement (+1,5 dB à 3 kHz, +1 dB au-dessus de 8 kHz), sans toucher au centre où se trouvent les voix.
3. **Égalisation** (corrections modérées, environ la moitié de l'écart mesuré) :

   | Fréquence | Réglage | Objectif |
   |---|---|---|
   | 40 Hz | -2 dB | calmer la bosse du sub |
   | 110 Hz | +1,5 dB | redonner du corps à la basse |
   | 415 Hz | -2 dB, étroit | atténuer l'effet « boîte » |
   | 850 Hz | +1 dB | remplir le médium un peu creusé |
   | 2,1 kHz | +1,5 dB | intelligibilité des voix |
   | 3,2 kHz | -1,5 dB | éviter la dureté (zone déjà proéminente) |
   | 5,5 kHz | +2 dB | présence et brillance |
   | aigus (4,5 kHz et 12 kHz) | +1 dB et +0,8 dB | ouverture et air |

4. **De-esser** entre 5 et 9 kHz : il n'agit que sur les pics de sifflantes, environ 3 % du temps, avec au plus -3,8 dB.
5. **Compression du sub** sous 75 Hz (ratio 2:1) : environ 3 dB de réduction sur les pics, pour un grave plus tenu.
6. **Compression de bus « glue »** (ratio 1,4:1, attaque 30 ms, relâchement 250 ms, sans tenir compte du sub pour éviter le pompage) : environ 0,8 dB de réduction en médiane. Volontairement légère pour préserver la construction du morceau.
7. **Écrêteur doux puis limiteur** :
   - écrêteur suréchantillonné ×4 : il n'arrondit que 0,08 % des échantillons (transitoires très brèves) ;
   - limiteur true-peak suréchantillonné ×4, avec anticipation de 1,5 ms : au plus 2,2 dB de réduction ;
   - aucune distorsion mesurable ajoutée : la part d'aigus au-dessus de 10 kHz est identique à celle de la version streaming, qui n'est presque pas écrêtée.
8. **Début et fin** : fondu d'entrée de 10 ms (contre les clics) et fondu de sortie de 3,5 s, suivi de 0,6 s de silence.

## Vérifications faites

- Aucune saturation, aucune valeur invalide (NaN), pic réel sous -0,9 dBTP sur les trois fichiers.
- Volume cohérent du début à la fin : la construction du morceau est conservée (intro → refrains → fin), voir `comparatif.png`.
- Compatibilité mono : perte de 0,5 LU, identique à l'original. Corrélation stéréo de 0,81.
- Gauche et droite équilibrés à ±0,1 dB.

## Limites et recommandations

- **Pistes séparées** : je n'ai travaillé que sur le mix stéréo. Je n'ai donc pas pu traiter séparément la voix de LeoBenjo, celle de Nathan et l'instrumental (niveau relatif des voix, compression, réverbération propre à chacune). Pour aller plus loin, exporte les pistes en WAV 24 bits, toutes démarrant à 0:00, avec au minimum : voix LeoBenjo, voix Nathan, chœurs, instrumental.
- **Fin du morceau** : la source s'arrête net, donc j'ai ajouté un fondu. Si le projet d'origine contient une vraie fin (résonance des instruments, dernière note), ré-exporte le mix en entier.
- **Écoute de contrôle** : valide le résultat sur au moins trois systèmes (casque, téléphone, enceintes). Vérifie en particulier les sifflantes et la place des voix dans les refrains.
