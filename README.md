# HJS-Workbench

A portable, cross-hardware digital debug workbench that combines **logic
analysis, signal generation, and measurement** in one shared core, delivered
through both a graphical application and a command-line interface.

The software is written to be hardware-independent. It talks to real boards
through a small backend interface, so the same core and the same two front-ends
can drive any device that provides a backend. The first fully supported device
is the WCH CH32H417; see [Hardware support](#hardware-support) for the current
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
- **Internationalization** - English, 简体中文, and 繁體中文. The language is
  chosen on the first run, remembered in the user config, and switchable at
  runtime. Decoder data, CSV headers, and sigrok metadata stay English in every
  language.
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
| Inputs | 8 channels (PD0-PD7), 10 kHz sampling, USB2.0 Full-Speed CDC |
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

## Protocol decoders

| Protocol | Decodes | Typical use |
|---|---|---|
| UART | start/data/stop bits -> characters | serial debug |
| NEC IR | address, command, repeat code | remote control |
| RC-5 IR | address, command, toggle bit | European remote |
| Servo PWM/PPM | pulse width, angle, multi-channel | RC / robotics |
| I2C (slow) | start/stop, address, data, ACK | sensors / OLED |
| SPI (slow) | CS, MOSI/MISO, CPOL/CPHA | memory / display |
| Stepper | steps, direction, speed, position | CNC / 3D printing |
| Quadrature encoder | 4x count, direction, RPM, index | motor loop / knob |
| HC-SR04 ultrasonic | echo time, distance | ranging / obstacle |
| Fan TACH | pulse interval, RPM | fan monitoring |
| DHT11 | start/response, 40 data bits, checksum, humidity, temperature | humidity / temperature |
| 1-Wire DS18B20 | reset/presence, ROM, scratchpad, CRC, temperature | temperature bus |
| SWD | line reset, ACK, register read/write with parity | debug port |
| Modbus RTU | address, function code, data, CRC-16 | RS-485 industrial bus |
| Wiegand | 26/34-bit frames, parity, card number | access control |
| HD44780 | 4-bit bus commands and characters | character LCD |
| Sony SIRC | address, command (12/15/20 bits) | IR remote |
| DS1302 | CE/SCLK/IO register reads and writes | real-time clock |
| Manchester | bit stream and bytes (IEEE 802.3 convention) | encoded links |
| NMEA 0183 | $...*XX sentences, checksum result | GPS |

> The current backend samples at 10 kHz, so I2C, SPI, and several decoders are
> designed for slow signals. Each decoder states its real hardware timing in its
> docstring. Standard rates become available once a backend with a higher
> sample rate is added.

## Repository layout

```
core/              shared core: capture I/O, data model, measurement, 19
                   decoders, UART decode, i18n, config, and the HAL
cli/               command-line interface (python -m cli)
gui/               graphical application (python -m gui), including the
                   continuous-capture worker, signal panel, and onboarding
assets/            application icon set and multi-size .ico
locales/           gettext catalogs: zh_CN / zh_TW (.po sources + .mo)
scripts/           pure-Python catalog compiler (compile_mo.py)
packaging/         PyInstaller spec files and build documentation
examples/          sample .sr captures and a CSV log example
firmware/          prebuilt firmware images (.hex/.bin)
firmware/src/      firmware C source with a standalone Makefile
docs/              BOM and documentation
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
- **Native installers** - standalone macOS and Linux packages alongside the
  Windows PyInstaller build.
- **Hardware** - more channels, higher sampling rates, faster upload, and a
  burst sampling architecture.

## License

Released under the **GNU General Public License v3.0 (GPL-3.0)**. See
[LICENSE](LICENSE).
