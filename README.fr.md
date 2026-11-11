# HJS-Workbench

[English](README.md) | **Français** | [Deutsch](README.de.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [العربية](README.ar.md)

Un poste de travail de débogage numérique portable et multi-matériels qui
réunit **l'analyse logique, la génération de signaux et la mesure** dans un
noyau partagé, accessible via une application graphique et une interface en
ligne de commande.

Le logiciel est conçu pour être indépendant du matériel. Il communique avec les
cartes réelles au travers d'une petite interface de backend, de sorte que le
même noyau et les deux interfaces peuvent piloter tout appareil fournissant un
backend. Le premier appareil entièrement pris en charge est le WCH CH32H417 ;
la section Prise en charge matérielle ci-dessous explique le périmètre actuel et
la raison de cette documentation.

## Architecture : un noyau, deux interfaces

```
core/   logique partagée et indépendante du matériel : acquisition, modèle,
         mesure, 19 décodeurs de protocoles, décodage UART, i18n, config, HAL
  cli/   interface en ligne de commande avec son propre numéro de version
  gui/   application de bureau PySide6 avec son propre numéro de version
```

La CLI et la GUI sont des interfaces légères sur le même noyau. Elles ne
contiennent aucune logique de protocole ou d'acquisition propre, donc une
correction ou un nouveau décodeur dans le noyau devient immédiatement disponible
pour les deux. Les deux applications sont publiées séparément et gardent des
numéros de version distincts.

## Prise en charge matérielle

Le noyau n'accède jamais directement à une carte. Il travaille avec un contrat
de backend (la couche d'abstraction matérielle dans `core/hal/`). Chaque backend
déclare ses capacités réelles : nombre et noms de canaux, taux d'échantillonnage
pris en charge, modes d'octets et débits. La GUI et la CLI ne présentent que les
options déclarées par le backend sélectionné, et rejettent les configurations en
dehors de ces capacités plutôt que de deviner en silence.

À ce jour, **un seul backend réel est implémenté et vérifié sur matériel : le WCH
CH32H417**. Le micrologiciel de référence sous `firmware/` est donc spécifique à
ce microcontrôleur. Le logiciel est conçu pour de nombreuses cartes, mais la
liste prise en charge est délimitée au matériel réellement construit et testé,
pour les raisons suivantes :

- **Aucun appareil simulé ou factice.** Le projet n'inclut pas de faux backends.
  Une carte n'est listée qu'après l'écriture de son backend d'après la fiche
  technique officielle et des tests sur l'appareil réel, afin que chaque mention
  « pris en charge » soit fiable et reproductible.
- **Étendre la prise en charge ne touche pas au noyau.** Ajouter une carte
  consiste à ajouter un adaptateur backend autonome et ses capacités. La CLI et
  la GUI existantes pilotent ensuite la nouvelle carte sans modifier leur code.
- **Annoncer une prise en charge avant validation serait inexact.** Tant qu'une
  deuxième carte n'est pas disponible et vérifiée, prétendre une compatibilité plus
  large surestimerait les capacités du projet ; la documentation reste donc limitée
  à l'appareil testé.

Le matériel de référence ci-dessous est le backend actuel, pas une limite de
conception. D'autres backends sont prévus dans la feuille de route et suivent la
même règle fiche technique plus vérification physique.

## Fonctionnalités

- **Application graphique** - acquérir, afficher les formes d'onde, décoder et
  mesurer à la souris (PySide6 + pyqtgraph), sans commande de terminal.
- **Interface en ligne de commande** - un menu unifié pour l'acquisition,
  l'analyse en direct, la mesure en direct, le décodage de protocoles, la
  génération de signaux et les outils hors ligne.
- **Acquisition unique et continue** - acquérir un nombre exact de points, ou
  diffuser une fenêtre glissante rafraîchie toutes les 100-200 ms. Les deux modes
  partagent un port de données et sont mutuellement exclusifs.
- **Acquisition multi-taux et par rafales** - sur le backend haute vitesse CH32,
  choisir 10 kHz, 100 kHz, 500 kHz ou 1 MHz, et le flux en temps réel ou un
  tampon de rafale de 712704 octets ; le taux et le mode persistent entre les
  sessions et reviennent aux valeurs par défaut si non pris en charge.
- **Contrôles de zoom** - boutons Zoom avant, Zoom arrière et Ajuster au-dessus du
  graphique, avec le zoom molette et le panoramique par glisser.
- **Import multi-fichiers** - une action Import enregistre plusieurs fichiers
  `.sr`/`.bin` pour basculer entre eux ; Retirer ne supprime que l'entrée interne et
  ne touche jamais au fichier sur le disque.
- **Décodage autonome** - 19 décodeurs de protocoles plus le décodage UART en
  texte directement en Python, avec journal CSV ; aucune application de décodage
  externe n'est nécessaire.
- **Générateur de signaux** - message de test UART logiciel, onde carrée, PWM
  (fréquence et rapport cyclique), rafale (fréquence et nombre d'impulsions) et
  niveaux forcés haut/bas. Reboucler la sortie du générateur vers une entrée pour
  acquérir et décoder le signal de l'appareil lui-même en boucle fermée.
- **Mesure en temps réel** - fréquence, période, largeur d'impulsion haut/bas,
  rapport cyclique, gigue (min/max), sur tous les canaux.
- **Déclenchement et comptage** - détection de front montant/descendant et comptage
  par canal.
- **Boîte de paramètres** - préférences de langue et de thème clair/sombre dans une
  boîte modale (OK / Appliquer / Annuler), appliquées immédiatement sans
  redémarrage ; la barre d'outils est organisée en zones connexion, acquisition,
  fichier et paramètres.
- **Internationalisation** - English, Français, Deutsch, 简体中文 et 繁體中文. La
  langue est choisie au premier lancement, mémorisée dans la configuration et
  commutable à l'exécution. Les données des décodeurs, les en-têtes CSV et les
  métadonnées sigrok restent en anglais dans toutes les langues.
- **Guide d'accueil** - un assistant initial étape par étape qui peut être ignoré
  et ne réapparaît jamais seul, ainsi qu'un guide de démarrage rapide rouvrable dans
  les deux interfaces.

Le nombre de canaux, le taux d'échantillonnage et la broche du générateur listés
dans la section matériel de référence sont les capacités du backend CH32 actuel.
D'autres backends peuvent déclarer des valeurs différentes, et les applications
s'adaptent aux capacités du backend sélectionné.

## Chemin des données

```
Échantillonnage GPIO -> transfert USB CDC en masse -> réception Python -> affichage / décodage / journal
```

## Matériel de référence (backend actuel)

| Élément | Spécification |
|---|---|
| Carte | MuseLab nanoCH32H417 (CH32H417QEU6) |
| Cœur | WCH QingKe V3F RISC-V, monocœur, 100 MHz |
| Entrées | 8 canaux (PD0-PD7), au choix 10 kHz/100 kHz/500 kHz/1 MHz |
| Ports de données | USB2.0 plein débit sur le port Type-C OTG, ou haut débit 480 Mbps sur le port USB3 Type-A |
| Tampon de rafale | 712704 octets (696 Ko), modes temps réel et rafale |
| Boucle fermée | PA15 (générateur) rebouclé sur PD0 (échantillonneur) |

## Démarrage rapide

1. Flasher une image de micrologiciel préconstruite depuis `firmware/` (par exemple
   `HJS-Workbench.hex`) avec OpenOCD ou la chaîne WCH via WCH-Link.
2. Connecter **PA15 -> PD0** avec un fil de liaison pour la démonstration en
   boucle fermée.
3. Lancer l'application graphique (Python 3.12) :

```bash
pip install -r gui/requirements.txt
python -m gui
```

L'interface en ligne de commande couvre les mêmes fonctionnalités :

```bash
pip install pyserial
python -m cli    # menu 6 puis 1 exécute l'auto-test hors ligne 19/19
```

Au premier lancement de la GUI, un assistant d'accueil détaille la connexion de
l'appareil, le choix du port, l'acquisition, les formes d'onde/décodage/mesure et
le générateur de signaux. Il peut être ignoré et rouvert plus tard via le bouton
Démarrage rapide (GUI) ou l'entrée de menu Guide de démarrage (CLI).

## Installation

Des chemins d'installation préconstruits existent pour les deux éditions :

- **Setup Windows (GUI)** : un exécutable Setup unique qui demande d'abord la
  langue de l'installateur, puis l'emplacement, puis installe la complète
  application GUI avec raccourcis et un programme de désinstallation enregistré.
- **Script terminal (CLI)** : une commande bash unique pour Ubuntu, WSL et macOS
  qui demande d'abord la langue, puis le répertoire d'installation, et télécharge
  le binaire de la plateforme. Le répertoire par défaut (`~/.local/bin`) ne
  nécessite pas de droits administrateur.

Les deux flux demandent la langue avant toute invite de chemin. La langue de
l'installateur est propre ; l'application installée garde son réglage de langue
interne distinct. Voir [docs/INSTALL.md](docs/INSTALL.md) pour le guide complet,
la note PATH et les prérequis de construction.

## Décodeurs de protocoles

Les décodeurs sont groupés par fonction. Chacun est conçu pour le matériel réel et
indique son timing dans sa docstring.

### Bus série et protocoles

| Protocole | Décode | Usage typique |
|---|---|---|
| UART | bits start/données/stop -> caractères | débogage série |
| I2C (lent) | start/stop, adresse, données, ACK | capteurs / OLED |
| SPI (lent) | CS, MOSI/MISO, CPOL/CPHA | mémoire / affichage |
| 1-Wire DS18B20 | reset/présence, ROM, scratchpad, CRC, température | bus de température |
| Modbus RTU | adresse, code fonction, données, CRC-16 | bus industriel RS-485 |
| Manchester | flux de bits et octets (convention IEEE 802.3) | liaisons encodées |

### Télécommandes infrarouge

| Protocole | Décode | Usage typique |
|---|---|---|
| NEC IR | adresse, commande, code de répétition | télécommande |
| RC-5 IR | adresse, commande, bit de bascule | télécommande européenne |
| Sony SIRC | adresse, commande (12/15/20 bits) | télécommande IR |

### Moteurs et contrôle de mouvement

| Protocole | Décode | Usage typique |
|---|---|---|
| Servo PWM/PPM | largeur d'impulsion, angle, multi-canaux | RC / robotique |
| Stepper | pas, direction, vitesse, position | CNC / impression 3D |
| Quadrature encoder | comptage 4x, direction, RPM, index | boucle moteur / bouton |
| Fan TACH | intervalle d'impulsion, RPM | surveillance des ventilateurs |

### Capteurs et mesure

| Protocole | Décode | Usage typique |
|---|---|---|
| DHT11 | start/réponse, 40 bits de données, checksum, humidité, température | humidité / température |
| HC-SR04 ultrasonic | temps d'écho, distance | télémétrie / obstacle |
| NMEA 0183 | phrases $...*XX, résultat du checksum | GPS |

### Affichage, horloge et interfaces spéciales

| Protocole | Décode | Usage typique |
|---|---|---|
| HD44780 | commandes et caractères sur bus 4 bits | écran LCD à caractères |
| DS1302 | lectures et écritures de registres CE/SCLK/IO | horloge temps réel |
| SWD | reset de ligne, ACK, lecture/écriture de registres avec parité | port de débogage |
| Wiegand | trames 26/34 bits, parité, numéro de carte | contrôle d'accès |

> Le taux temps réel par défaut est 10 kHz, et le port haute vitesse ajoute
> jusqu'à 1 MHz pour les timings rapides. I2C, SPI et plusieurs décodeurs restent
> conçus pour des signaux lents ; chaque décodeur indique son timing matériel réel
> dans sa docstring.

## Organisation du dépôt

```
core/              noyau partagé : E/S d'acquisition, modèle de données, mesure,
                   19 décodeurs, décodage UART, i18n, config, HAL
cli/               interface en ligne de commande (python -m cli)
gui/               application graphique (python -m gui), incluant le travailleur
                   d'acquisition continue, le panneau de signaux et le guide
assets/            jeu d'icônes et .ico multi-tailles
locales/           catalogues gettext : fr / de / zh_CN / zh_TW (.po sources + .mo)
scripts/           compilateur de catalogues (compile_mo.py) et le script
                   d'installation CLI (install.sh)
packaging/         fichiers spec PyInstaller, script Inno Setup, docs de build
examples/          exemples de captures .sr et un exemple de journal CSV
firmware/          images de micrologiciel préconstruites (.hex/.bin)
firmware/src/      source C du micrologiciel avec Makefile autonome
docs/              BOM, guide d'installation et documentation
```

## Construire depuis les sources

La source du micrologiciel est dans `firmware/src/`. Avec la chaîne WCH RISC-V
(fournie avec MounRiver Studio) sur le `PATH` :

```bash
cd firmware/src
make
```

La construction produit `HJS-Workbench.elf`, `.hex` et `.bin`. Voir
[firmware/src/BUILD.md](firmware/src/BUILD.md) pour le guide complet. Les paquets
de bureau sont construits avec PyInstaller ; voir
[packaging/BUILD.md](packaging/BUILD.md).

## Feuille de route

- **Plus de backends réels** - adaptateurs HAL supplémentaires, chacun appuyé par
  la fiche technique et des mesures physiques, jamais de données simulées.
- **Encodeur de protocoles universel** - sortie micrologiciel multi-canaux pilotée
  par lecture matérielle timer, DMA et GPIO, avec encodage/décodage symétrique
  dans le noyau et vérification en boucle fermée.
- **Installateurs natifs** - installateurs macOS et Linux aux côtés du Setup
  Windows ; le script d'installation CLI devient de bout en bout sur chaque
  plateforme une fois le binaire CLI publié.
- **Matériel** - plus de canaux, des taux plus élevés, un transfert plus rapide et
  une architecture d'échantillonnage par rafales.

## Licence

Publié sous la **licence publique générale GNU v3.0 (GPL-3.0)**. Voir
[LICENSE](LICENSE).
