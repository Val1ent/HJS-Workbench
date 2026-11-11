# HJS-Workbench

[English](README.md) | [Français](README.fr.md) | **Deutsch** | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [العربية](README.ar.md)

Eine portable, hardwareunabhängige digitale Debug-Werkbank, die
**Logikanalyse, Signalerzeugung und Messung** in einem gemeinsamen Kern
vereint und sowohl als grafische Anwendung als auch als
Kommandozeilenoberfläche bereitgestellt wird.

Die Software ist hardwareunabhängig konzipiert. Sie kommuniziert mit echten
Platinen über eine kleine Backend-Schnittstelle, sodass derselbe Kern und
dieselben zwei Oberflächen jedes Gerät ansteuern können, das ein Backend
bereitstellt. Das erste vollständig unterstützte Gerät ist der WCH CH32H417;
der Abschnitt Hardware-Unterstützung unten erläutert den aktuellen Umfang und
den Grund für diese Dokumentation.

## Architektur: ein Kern, zwei Oberflächen

```
core/   gemeinsame, hardwareunabhängige Logik: Erfassung, Modell, Messung,
         19 Protokolldecoder, UART-Decodierung, i18n, Konfiguration, HAL
  cli/   Kommandozeilenoberfläche mit eigener Versionsnummer
  gui/   PySide6-Desktopanwendung mit eigener Versionsnummer
```

CLI und GUI sind dünne Oberflächen über demselben Kern. Sie enthalten keine
eigene Protokoll- oder Erfassungslogik, sodass eine Korrektur oder ein neuer
Decoder im Kern sofort für beide verfügbar ist. Die beiden Anwendungen werden
unabhängig veröffentlicht und führen getrennte Versionsnummern.

## Hardware-Unterstützung

Der Kern greift nie direkt auf eine Platine zu. Er arbeitet mit einem
Backend-Vertrag (der Hardware-Abstraktionsschicht in `core/hal/`). Jedes
Backend deklariert seine echten Fähigkeiten: Kanalanzahl und -namen,
unterstützte Abtastraten, Byte-Modi und Baudraten. GUI und CLI zeigen nur die
vom gewählten Backend deklarierten Optionen an und lehnen Konfigurationen
außerhalb dieser Fähigkeiten ab, anstatt im Stillen zu raten.

Zum jetzigen Zeitpunkt ist **ein einziges echtes Backend implementiert und auf
physischer Hardware verifiziert: der WCH CH32H417**. Die Referenz-Firmware
unter `firmware/` ist daher spezifisch für diesen Mikrocontroller. Die Software
ist für viele Platinen konzipiert, aber die Unterstützungsliste ist bewusst auf
tatsächlich gebaute und getestete Hardware beschränkt, aus folgenden Gründen:

- **Keine simulierten oder Scheingeräte.** Das Projekt enthält keine
  Schein-Backends. Eine Platine wird erst gelistet, nachdem ihr Backend anhand
  des offiziellen Datenblatts geschrieben und auf dem echten Gerät erprobt
  wurde, sodass jede „unterstützt"-Angabe vertrauenswürdig und reproduzierbar ist.
- **Die Erweiterung der Unterstützung berührt den Kern nicht.** Das Hinzufügen
  einer Platine bedeutet das Hinzufügen eines in sich geschlossenen
  Backend-Adapters und seiner deklarierten Fähigkeiten. Die bestehenden CLI und
  GUI steuern die neue Platine dann ohne Code-Änderungen an.
- **Eine Unterstützung vor der Validierung anzukündigen wäre ungenau.** Solange
  eine zweite Platine nicht physisch verfügbar und verifiziert ist, würde eine
  breitere Kompatibilitätsangabe die Fähigkeiten des Projekts überzeichnen; die
  Dokumentation bleibt daher auf das getestete Gerät beschränkt.

Die Referenz-Hardware unten ist das aktuelle Backend, nicht die Grenze des
Entwurfs. Weitere Backends sind in der Roadmap vorgesehen und folgen derselben
Regel Datenblatt plus physische Verifizierung.

## Funktionen

- **Grafische Anwendung** - Erfassung, Wellenformanzeige, Decodierung und
  Messung mit der Maus (PySide6 + pyqtgraph), ohne Terminalbefehle.
- **Kommandozeilenoberfläche** - ein einheitliches Menü für Erfassung,
  Live-Analyse, Live-Messung, Protokolldecodierung, Signalerzeugung und
  Offline-Werkzeuge.
- **Einzel- und Dauererfassung** - Erfassen einer genauen Punktzahl oder das
  Streaming eines fortlaufenden Fensters, das alle 100-200 ms aktualisiert wird.
  Die beiden Modi teilen sich einen Datenport und schließen sich gegenseitig aus.
- **Mehrraten- und Burst-Erfassung** - auf dem CH32-High-Speed-Backend
  10 kHz, 100 kHz, 500 kHz oder 1 MHz wählen sowie Echtzeit-Streaming oder einen
  712704-Byte-Burst-Puffer; Rate und Modus bleiben sitzungsübergreifend erhalten
  und fallen bei Nichtunterstützung auf die Backend-Standardwerte zurück.
- **Zoom-Steuerung** - Schaltflächen Vergrößern, Verkleinern und Anpassen über
  dem Diagramm, zusammen mit Mausrad-Zoom und Ziehen-Panoramasteuerung.
- **Mehrdatei-Import** - eine Import-Aktion registriert mehrere `.sr`/`.bin`
  Erfassungsdateien zur Umschaltung; Entfernen löscht nur den In-App-Eintrag und
  berührt nie die Datei auf der Festplatte.
- **In sich geschlossene Decodierung** - 19 Protokolldecoder plus
  UART-Text-Decodierung direkt in Python, mit CSV-Protokollierung; keine externe
  Decoderanwendung erforderlich.
- **Signalgenerator** - Software-UART-Testnachricht, Rechteckwelle, PWM
  (Frequenz und Tastgrad), Burst (Frequenz und Impulsanzahl) sowie erzwungene
  Hoch-/Niedrigpegel. Den Generatorausgang auf einen Eingang zurückschleifen, um
  das eigene Signal des Geräts in einer geschlossenen Schleife zu erfassen und zu
  decodieren.
- **Echtzeitmessung** - Frequenz, Periode, hohe/niedrige Impulsbreite, Tastgrad,
  Jitter (Min/Max), über alle Kanäle.
- **Flankentrigger und Zählung** - steigende/fallende Flankenerkennung und
  Zählung pro Kanal.
- **Einstellungsdialog** - Sprach- und Hell-/Dunkelthema-Einstellungen in einem
  modalen Dialog (OK / Anwenden / Abbrechen), sofort ohne Neustart angewendet;
  die Werkzeugleiste ist in Bereiche Verbindung, Erfassung, Datei und Einstellungen
  gegliedert.
- **Internationalisierung** - English, Français, Deutsch, 简体中文 und 繁體中文.
  Die Sprache wird beim ersten Lauf gewählt, in der Benutzerkonfiguration gemerkt
  und ist zur Laufzeit umschaltbar. Decoderdaten, CSV-Kopfzeilen und
  sigrok-Metadaten bleiben in jeder Sprache auf Englisch.
- **Einrichtungsassistent** - ein schrittweiser Assistent beim ersten Start, der übersprungen werden
  kann und nie von selbst erneut erscheint, sowie ein wieder öffnbarer
  Schnellstart-Leitfaden in beiden Oberflächen.

Die konkrete Kanalanzahl, Abtastrate und Generator-Pin im
Referenz-Hardware-Abschnitt sind die deklarierten Fähigkeiten des aktuellen
CH32-Backends. Andere Backends können andere Werte melden, und die Anwendungen
passen sich den Fähigkeiten des gewählten Backends an.

## Datenpfad

```
GPIO-Abtastung -> USB-CDC-Massenübertragung -> Python-Empfang -> Anzeige / Decodierung / Protokoll
```

## Referenz-Hardware (aktuelles Backend)

| Element | Spezifikation |
|---|---|
| Platine | MuseLab nanoCH32H417 (CH32H417QEU6) |
| Kern | WCH QingKe V3F RISC-V, Einkern, 100 MHz |
| Eingänge | 8 Kanäle (PD0-PD7), wählbar 10 kHz/100 kHz/500 kHz/1 MHz |
| Datenports | USB2.0 Full-Speed am Type-C-OTG-Port oder High-Speed 480 Mbps am USB3-Type-A-Port |
| Burst-Puffer | 712704 Byte (696 KB), Echtzeit- und Burst-Erfassungsmodi |
| Geschlossene Schleife | PA15 (Generator) zurück auf PD0 (Abtaster) verdrahtet |

## Schnellstart

1. Ein vorgefertigtes Firmware-Abbild aus `firmware/` (zum Beispiel
   `HJS-Workbench.hex`) mit OpenOCD oder der WCH-Toolchain über WCH-Link flashen.
2. **PA15 -> PD0** mit einem Jumperdraht für die Closed-Loop-Demo verbinden.
3. Die grafische Anwendung starten (Python 3.12):

```bash
pip install -r gui/requirements.txt
python -m gui
```

Die Kommandozeilenoberfläche deckt dieselben Funktionen ab:

```bash
pip install pyserial
python -m cli    # Menü 6 dann 1 führt den 19/19 Offline-Selbsttest aus
```

Beim ersten GUI-Start führt ein kurzer Einrichtungsassistent durch
Geräteverbindung, Portwahl, Erfassung, Wellenform/Decodierung/Messung und den
Signalgenerator. Er kann übersprungen und später über die Schnellstart-Schaltfläche
(GUI) oder den Menüeintrag Schnellstart-Leitfaden (CLI) wieder geöffnet werden.

## Installation

Für beide Editionen gibt es vorgefertigte Installationspfade:

- **Windows-Setup (GUI)**: ein einzelnes Setup-Programm, das zuerst die
  Installersprache abfragt, dann den Installationsort, und dann die vollständige
  GUI-Anwendung mit Verknüpfungen und einem registrierten Deinstallationsprogramm
  installiert.
- **Terminal-Skript (CLI)**: ein einzeiliger Bash-Befehl für Ubuntu, WSL und
  macOS, der zuerst die Sprache abfragt, dann das Installationsverzeichnis, und die
  passende Plattformbinärdatei herunterlädt. Das Standardverzeichnis
  (`~/.local/bin`) benötigt keine Administratorrechte.

Beide Abläufe fragen die Sprache vor allen Pfad- oder Installationsabfragen ab.
Die Installersprache ist eine eigene; die installierte Anwendung behält ihre
separate In-App-Sprach einstellung. Siehe [docs/INSTALL.md](docs/INSTALL.md)
für das vollständige Handbuch, die PATH-Notiz und die Build-Voraussetzungen.

## Protokolldecoder

Die Decoder sind nach Funktion gruppiert. Jeder ist für echte Hardware gebaut und
gibt sein Timing in seiner Docstring an.

### Serielle Busse und Protokolle

| Protokoll | Decodiert | Typische Verwendung |
|---|---|---|
| UART | Start-/Daten-/Stoppbits -> Zeichen | serielles Debug |
| I2C (langsam) | Start/Stopp, Adresse, Daten, ACK | Sensoren / OLED |
| SPI (langsam) | CS, MOSI/MISO, CPOL/CPHA | Speicher / Anzeige |
| 1-Wire DS18B20 | Reset/Presence, ROM, Scratchpad, CRC, Temperatur | Temperaturbus |
| Modbus RTU | Adresse, Funktionscode, Daten, CRC-16 | RS-485 Industriebus |
| Manchester | Bitstrom und Bytes (IEEE-802.3-Konvention) | codierte Verbindungen |

### Infrarot-Fernbedienung

| Protokoll | Decodiert | Typische Verwendung |
|---|---|---|
| NEC IR | Adresse, Befehl, Wiederholungscode | Fernbedienung |
| RC-5 IR | Adresse, Befehl, Toggle-Bit | europäische Fernbedienung |
| Sony SIRC | Adresse, Befehl (12/15/20 Bits) | IR-Fernbedienung |

### Motor und Bewegungssteuerung

| Protokoll | Decodiert | Typische Verwendung |
|---|---|---|
| Servo PWM/PPM | Impulsbreite, Winkel, Mehrkanal | RC / Robotik |
| Stepper | Schritte, Richtung, Geschwindigkeit, Position | CNC / 3D-Druck |
| Quadrature encoder | 4x-Zählung, Richtung, RPM, Index | Motorschleife / Drehknopf |
| Fan TACH | Pulsintervall, RPM | Lüfterüberwachung |

### Sensoren und Messung

| Protokoll | Decodiert | Typische Verwendung |
|---|---|---|
| DHT11 | Start/Antwort, 40 Datenbits, Checksum, Feuchte, Temperatur | Feuchte / Temperatur |
| HC-SR04 ultrasonic | Echozeit, Entfernung | Entfernungsmessung / Hindernis |
| NMEA 0183 | $...*XX-Sätze, Checksum-Ergebnis | GPS |

### Anzeige, Takt und spezielle Schnittstellen

| Protokoll | Decodiert | Typische Verwendung |
|---|---|---|
| HD44780 | 4-Bit-Bus-Befehle und Zeichen | Zeichen-LCD |
| DS1302 | CE/SCLK/IO-Register-Lese- und Schreibvorgänge | Echtzeituhr |
| SWD | Leitungsreset, ACK, Register-Lesen/Schreiben mit Parität | Debug-Port |
| Wiegand | 26/34-Bit-Rahmen, Parität, Kartennummer | Zutrittskontrolle |

> Die standardmäßige Echtzeitrate beträgt 10 kHz, und der High-Speed-Port fügt
> bis zu 1 MHz Erfassung für schnelle Timings hinzu. I2C, SPI und mehrere Decoder
> sind weiterhin für langsame Signale ausgelegt; jeder Decoder gibt sein echtes
> Hardware-Timing in seiner Docstring an.

## Repository-Aufbau

```
core/              gemeinsamer Kern: Erfassungs-E/A, Datenmodell, Messung, 19
                   Decoder, UART-Decodierung, i18n, Konfiguration, HAL
cli/               Kommandozeilenoberfläche (python -m cli)
gui/               grafische Anwendung (python -m gui), inklusive Dauererfassungs-
                   Worker, Signal-Panel und Einrichtung
assets/            Anwendungssymbol-Satz und mehrgrößiges .ico
locales/           gettext-Kataloge: fr / de / zh_CN / zh_TW (.po-Quellen + .mo)
scripts/           Katalog-Compiler (compile_mo.py) und das CLI-Installationsskript
                   (install.sh)
packaging/         PyInstaller-Spec-Dateien, Inno-Setup-Skript, Build-Dokumentation
examples/          Beispiel-.sr-Erfassungen und ein CSV-Protokollbeispiel
firmware/          vorgefertigte Firmware-Abbilder (.hex/.bin)
firmware/src/      Firmware-C-Quellcode mit eigenständigem Makefile
docs/              BOM, Installationshandbuch und Dokumentation
```

## Build aus dem Quellcode

Der Firmware-Quellcode liegt in `firmware/src/`. Mit der WCH-RISC-V-Toolchain
(im Lieferumfang von MounRiver Studio) auf dem `PATH`:

```bash
cd firmware/src
make
```

Der Build erzeugt `HJS-Workbench.elf`, `.hex` und `.bin`. Siehe
[firmware/src/BUILD.md](firmware/src/BUILD.md) für das vollständige Handbuch. Die
Desktop-Pakete werden mit PyInstaller gebaut; siehe
[packaging/BUILD.md](packaging/BUILD.md).

## Roadmap

- **Weitere echte Board-Backends** - zusätzliche HAL-Adapter, jeweils gestützt
  durch das offizielle Datenblatt und Platinenmessungen, nie simulierte Daten.
- **Universeller Protokoll-Encoder** - mehrkanalige Firmware-Ausgabe, durch
  Timer-, DMA- und GPIO-Hardware-Wiedergabe angetrieben, mit symmetrischer
  Encodierung/Decodierung im Kern und Closed-Loop-Verifizierung.
- **Native Installer** - macOS- und Linux-Installer neben dem Windows-Setup; das
  plattformübergreifende CLI-Installationsskript wird auf jeder Plattform
  durchgängig, sobald deren CLI-Binärdatei veröffentlicht ist.
- **Hardware** - mehr Kanäle, höhere Abtastraten, schnellerer Upload und eine
  Burst-Abtastarchitektur.

## Lizenz

Veröffentlicht unter der **GNU General Public License v3.0 (GPL-3.0)**. Siehe
[LICENSE](LICENSE).
