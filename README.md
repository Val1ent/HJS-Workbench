# HJS-Workbench

**English** | [Français](README.fr.md) | [Deutsch](README.de.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [العربية](README.ar.md)

A portable, cross-hardware digital debug workbench that combines **logic
analysis, signal generation, and measurement** in one shared core, delivered
through both a graphical application and a command-line interface.

The software is written to be hardware-independent. It talks to real boards
through a small backend interface, so the same core and the same two front-ends
can drive any device that provides a backend. The first fully supported device
is the WCH CH32H417; the Hardware support section below explains the current
scope and the reason it is documented this way.

## Architecture: one core, two front-ends

```
core/   shared, hardware-independent logic: capture, model, measurement,
         19 protocol decoders, UART decode, i18n, config, and the HAL
  cli/   command-line interface with its own version number
  gui/   PySide6 desktop application with its own version number
```

The CLI and the GUI are thin front-ends over the same core. They hold no
protocol or acquisition logic of their own, so a fix or a new decoder in the
core becomes available to both immediately. The two applications are released
independently and keep separate version numbers.

## Hardware support

The core never accesses a board directly. It works against a backend contract
(the hardware abstraction layer in `core/hal/`). Each backend declares its real
capabilities - channel count and names, supported sample rates, byte modes, and
baud rates. The GUI and CLI only present options the selected backend declares,
and reject configuration outside those capabilities rather than silently
guessing.

At the time of writing, **one real backend is implemented and verified on
physical hardware: the WCH CH32H417**. The reference firmware under
`firmware/` is therefore specific to that MCU. The software is designed for many
boards, but the supported list is deliberately limited to hardware that has
actually been built and tested, for the following reasons:

- **No simulated or mock devices.** The project does not bundle fake backends.
  A board is listed only after its backend is written against the official
  datasheet and exercised on the real device, so every "supported" claim can be
  trusted and reproduced.
- **Extending support does not touch the core.** Adding a board means adding a
  self-contained backend adapter and its declared capabilities. The existing
  CLI and GUI then drive the new board without any changes to their code.
- **Announcing support ahead of validation would be inaccurate.** Until a
  second board is physically available and verified, claiming broader
  compatibility would overstate what the project can do, so the documentation
  stays limited to the tested device.

The reference hardware below is the current backend, not a boundary of the
design. Additional backends are tracked on the roadmap and follow the same
datasheet-plus-physical-verification rule.

## Features

- **Graphical application** - capture, view waveforms, decode, and measure with
  the mouse (PySide6 + pyqtgraph); no terminal commands needed.
- **Command-line interface** - a unified menu for capture, live analysis, live
  measurement, protocol decoding, signal generation, and offline tools.
- **One-shot and continuous capture** - capture an exact number of points, or
  stream a rolling window that refreshes every 100-200 ms. The two modes share
  one data port and are mutually exclusive.
- **Multi-rate and burst capture** - on the CH32 High-Speed backend, select
  10 kHz, 100 kHz, 500 kHz, or 1 MHz, and choose realtime streaming or a
  712704-byte burst buffer; the rate and mode persist across sessions and fall
  back to the backend defaults when unsupported.
- **Waveform zoom controls** - Zoom in, Zoom out, and Fit buttons above the
  waveform plot, alongside the mouse wheel zoom and drag panning.
- **Multi-file import** - an Import action registers multiple `.sr`/`.bin`
  capture files in-app for switching between them; Remove drops only the
  in-app entry and never touches the file on disk.
- **Self-contained decoding** - 19 protocol decoders plus UART-to-text decoding
  directly in Python, with CSV logging; no external decoder application is
  required.
- **Signal generator** - a software-UART test message, square wave, PWM
  (frequency and duty), burst (frequency and pulse count), and forced high/low
  levels. Loop the generator output back to an input to capture and decode the
  device's own signal in a closed loop.
- **Real-time measurement** - frequency, period, high/low pulse width, duty,
  jitter (min/max), across channels.
- **Edge trigger and counting** - rising/falling edge detection and counting per
  channel.
- **Settings dialog** - language and light/dark theme preferences in one modal
  dialog (OK / Apply / Cancel), applied immediately without restarting; the
  toolbar is grouped into connection, acquisition, file, and settings areas.
- **Internationalization** - English, Français, Deutsch, 简体中文, and
  繁體中文. The language is chosen on the first run, remembered in the user
  config, and switchable at runtime. Decoder data, CSV headers, and sigrok
  metadata stay English in every language.
- **Onboarding** - a first-run step-by-step wizard that can be skipped and never
  reappears on its own, plus a re-openable Quick Start Guide in both front-ends.

The concrete channel count, sample rate, and generator pin listed in the
reference hardware section are the declared capabilities of the current CH32
backend. Other backends may report different values, and the applications adapt
to whatever the selected backend declares.

## Data path

```
GPIO sampling -> USB CDC bulk upload -> Python receive -> display / decode / log
```

## Reference hardware (current backend)

| Item | Spec |
|---|---|
| Board | MuseLab nanoCH32H417 (CH32H417QEU6) |
| Core | WCH QingKe V3F RISC-V, single core, 100 MHz |
| Inputs | 8 channels (PD0-PD7), selectable 10 kHz/100 kHz/500 kHz/1 MHz |
| Data ports | USB2.0 Full-Speed on the Type-C OTG port, or High-Speed 480 Mbps on the USB3 Type-A port |
| Burst buffer | 712704 bytes (696 KB), realtime and burst capture modes |
| Closed loop | PA15 (generator) wired back to PD0 (sampler) |

## Quick start

1. Flash a prebuilt firmware image from `firmware/` (for example
   `HJS-Workbench.hex`) with OpenOCD or the WCH toolchain via WCH-Link.
2. Connect **PA15 -> PD0** with a jumper wire for the closed-loop demo.
3. Run the graphical application (Python 3.12):

```bash
pip install -r gui/requirements.txt
python -m gui
```

The command-line interface covers the same functionality:

```bash
pip install pyserial
python -m cli    # menu 6 then 1 runs the 19/19 offline self-test
```

On the first GUI start a short onboarding wizard walks through connecting the
device, port selection, capture, waveform/decode/measurement, and the signal
generator. It can be skipped and reopened later via the Quick Start button (GUI)
or the Quick Start guide menu entry (CLI).

## Installation

Prebuilt installation paths exist for both editions:

- **Windows Setup (GUI)**: a single Setup executable that asks for the
  installer language first, then the install location, then installs the full
  GUI application with shortcuts and a registered uninstaller.
- **Terminal script (CLI)**: a one-line bash command for Ubuntu, WSL, and
  macOS that asks for language first, then the install directory, and
  downloads the matching platform binary. The default directory
  (`~/.local/bin`) needs no root.

Both flows ask for the language before any path or install prompt. The
installer language is its own; the installed application keeps its separate
in-app language setting. See [docs/INSTALL.md](docs/INSTALL.md) for the full
guide, the PATH note, and the build prerequisites.

## Protocol decoders

The decoders are grouped by function. Each one is built for real hardware and
states its timing in its docstring.

### Serial buses and protocols

| Protocol | Decodes | Typical use |
|---|---|---|
| UART | start/data/stop bits -> characters | serial debug |
| I2C (slow) | start/stop, address, data, ACK | sensors / OLED |
| SPI (slow) | CS, MOSI/MISO, CPOL/CPHA | memory / display |
| 1-Wire DS18B20 | reset/presence, ROM, scratchpad, CRC, temperature | temperature bus |
| Modbus RTU | address, function code, data, CRC-16 | RS-485 industrial bus |
| Manchester | bit stream and bytes (IEEE 802.3 convention) | encoded links |

### Infrared remote control

| Protocol | Decodes | Typical use |
|---|---|---|
| NEC IR | address, command, repeat code | remote control |
| RC-5 IR | address, command, toggle bit | European remote |
| Sony SIRC | address, command (12/15/20 bits) | IR remote |

### Motor and motion control

| Protocol | Decodes | Typical use |
|---|---|---|
| Servo PWM/PPM | pulse width, angle, multi-channel | RC / robotics |
| Stepper | steps, direction, speed, position | CNC / 3D printing |
| Quadrature encoder | 4x count, direction, RPM, index | motor loop / knob |
| Fan TACH | pulse interval, RPM | fan monitoring |

### Sensors and measurement

| Protocol | Decodes | Typical use |
|---|---|---|
| DHT11 | start/response, 40 data bits, checksum, humidity, temperature | humidity / temperature |
| HC-SR04 ultrasonic | echo time, distance | ranging / obstacle |
| NMEA 0183 | $...*XX sentences, checksum result | GPS |

### Display, timing and special interfaces

| Protocol | Decodes | Typical use |
|---|---|---|
| HD44780 | 4-bit bus commands and characters | character LCD |
| DS1302 | CE/SCLK/IO register reads and writes | real-time clock |
| SWD | line reset, ACK, register read/write with parity | debug port |
| Wiegand | 26/34-bit frames, parity, card number | access control |

> The default realtime rate is 10 kHz, and the High-Speed port adds up to
> 1 MHz capture for fast timing. I2C, SPI, and several decoders are still
> designed for slow signals; each decoder states its real hardware timing in
> its docstring.

## Repository layout

```
core/              shared core: capture I/O, data model, measurement, 19
                   decoders, UART decode, i18n, config, and the HAL
cli/               command-line interface (python -m cli)
gui/               graphical application (python -m gui), including the
                   continuous-capture worker, signal panel, and onboarding
assets/            application icon set and multi-size .ico
locales/           gettext catalogs: fr / de / zh_CN / zh_TW (.po sources + .mo)
scripts/           catalog compiler (compile_mo.py) and the CLI install
                   script (install.sh)
packaging/         PyInstaller spec files, Inno Setup script, build docs
examples/          sample .sr captures and a CSV log example
firmware/          prebuilt firmware images (.hex/.bin)
firmware/src/      firmware C source with a standalone Makefile
docs/              BOM, install guide, and documentation
```

## Build from source

The firmware source is in `firmware/src/`. With the WCH RISC-V toolchain (bundled
with MounRiver Studio) on the `PATH`:

```bash
cd firmware/src
make
```

The build produces `HJS-Workbench.elf`, `.hex`, and `.bin`. See
[firmware/src/BUILD.md](firmware/src/BUILD.md) for the full guide. The desktop
packages are built with PyInstaller; see [packaging/BUILD.md](packaging/BUILD.md).

## Roadmap

- **More real board backends** - additional HAL adapters, each backed by the
  official datasheet and physical-board measurements, never simulated data.
- **Universal protocol encoder** - multi-channel firmware output driven by
  timer, DMA, and GPIO hardware playback, with symmetric encode/decode in the
  core and closed-loop generate-capture-decode verification.
- **Native installers** - macOS and Linux installers alongside the Windows
  Setup; the cross-platform CLI install script becomes end-to-end on each
  platform once that platform's CLI binary is published.
- **Hardware** - more channels, higher sampling rates, faster upload, and a
  burst sampling architecture.

## License

Released under the **GNU General Public License v3.0 (GPL-3.0)**. See
[LICENSE](LICENSE).
