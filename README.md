# HJS-Workbench - CH32H417 Logic Analyzer (Extended)

A pocket-sized **analyze + generate + measure** all-in-one digital debug tool
based on the WCH **CH32H417** (RISC-V, QingKe V3F, 100 MHz).

## Features

- **Graphical Application** - a desktop GUI (PySide6 + pyqtgraph) to capture,
  view waveforms, decode, and measure with the mouse (no terminal commands
  needed).
- **Command-Line Interface** - a unified CLI for capture, live analysis, live
  measurement, protocol decoding, the signal generator, and offline tools.
- **Logic Analyzer** - 8 channels (PD0-PD7), 10 kHz sampling, streamed over
  USB2.0 Full-Speed CDC.
- **One-shot and continuous capture** - capture an exact number of points, or
  stream a rolling window that refreshes the waveform every 100-200 ms; both
  modes share the data port and are mutually exclusive.
- **Self-contained decoding** - 19 protocol decoders plus UART-to-text
  decoding directly in Python (no PulseView needed), with CSV logging.
- **Signal Generator** - software-UART test message, square wave, PWM
  (frequency and duty), burst (frequency and pulse count), and forced
  high/low levels on PA15, driven from the GUI signal panel or the CLI; loop
  A15 back to D0 to capture and decode the device's own signal.
- **Real-time Measurement** - frequency, period, high/low pulse width, duty,
  jitter (min/max), multi-channel.
- **Edge Trigger & Counting** - rising/falling edge detection and counting
  per channel.
- **Internationalization** - the GUI and CLI run in English, 简体中文, or
  繁體中文. The language is picked on the first run, remembered in the user
  config, and switchable at runtime (toolbar selector in the GUI, a Language
  menu entry in the CLI). Decoder data, CSV headers, and sigrok metadata stay
  English in every language.
- **Hardware abstraction layer** - every real development board plugs in
  through one backend interface (`core/hal/`). The CH32 board is the first
  backend; baud rates, channel count and names, byte mode, sample rate, and
  troubleshooting text all come from its declared capabilities, and a Device
  entry in the CLI and the GUI shows them.
- **Onboarding** - a first-run step-by-step wizard (connecting, port
  selection, capture, waveform/decode/measurement, signal generator) that can
  be skipped and never reappears on its own, plus a re-openable Quick Start
  Guide in both the GUI and the CLI.

## Data Path

```
GPIO sampling -> USB2.0 CDC bulk upload -> PC Python receive -> display / decode / log
```

## Hardware

| Item | Spec |
|---|---|
| Board | MuseLab nanoCH32H417 (CH32H417QEU6) |
| Core | WCH QingKe V3F RISC-V, single core, 100 MHz |
| Specs | 8 channels / 10 kHz / USB2.0 Full-Speed CDC |
| Link | A15 (PA15, generator) wired back to D0 (PD0, sampler) |

## Quick Start

1. Flash `firmware/UART_10kHz.hex` (or `.bin`) with MounRiver Studio /
   OpenOCD via WCH-Link.
2. Connect **A15 -> D0** with a jumper wire.
3. Run the graphical application (Python 3.12):

```bash
pip install -r gui/requirements.txt
python -m gui
```

The command-line interface covers the same functionality (serial capture,
live analyzer, live measurement, protocol decoding, signal generator,
offline self-test, and file tools):

```bash
pip install pyserial
python -m cli    # unified CLI menu; path 6 then 1 runs the 19/19 offline self-test
```

On the first GUI start a short onboarding wizard walks through connecting
the device, port selection, capture, waveform/decode/measurement, and the
signal generator; it can be skipped and reopened later via the Quick start
button (GUI) or the Quick start guide menu entry (CLI).

## Protocol Decoders

| Protocol | Decodes | Typical use |
|---|---|---|
| UART | start/data/stop bits -> characters | serial debug |
| NEC IR | address, command, repeat code | remote control |
| RC-5 IR | address, command, toggle bit | European remote |
| Servo PWM/PPM | pulse width, angle, multi-channel | RC / robotics |
| I2C (slow) | start/stop, address, data, ACK | sensors / OLED |
| SPI (slow) | CS, MOSI/MISO, CPOL/CPHA | memory / display |
| Stepper | steps, direction, speed, position | CNC / 3D printing |
| Quadrature Encoder | 4x count, direction, RPM, index | motor loop / knob |
| HC-SR04 Ultrasonic | echo time, distance | ranging / obstacle |
| Fan TACH | pulse interval, RPM | fan monitoring |
| DHT11 | start/response, 40 data bits, checksum, humidity, temperature | humidity / temperature |
| 1-Wire DS18B20 | reset/presence, ROM, scratchpad, CRC, temperature | temperature bus |
| SWD | line reset, ACK, register read/write with parity | ARM debug port |
| Modbus RTU | address, function code, data, CRC-16 | RS-485 industrial bus |
| Wiegand | 26/34-bit frames, parity, card number | access control |
| HD44780 | 4-bit bus commands and characters | character LCD |
| Sony SIRC | address, command (12/15/20 bits) | IR remote |
| DS1302 | CE/SCLK/IO register reads and writes | real-time clock |
| Manchester | bit stream and bytes (IEEE 802.3 convention) | encoded links |
| NMEA 0183 | $...*XX sentences, checksum result | GPS |

> Note: limited by the 10 kHz sampling rate, I2C/SPI and several of the
> new decoders are designed for "slow" signals. Each decoder module states
> its real hardware timing in its docstring; standard rates will be
> supported once the sampling rate is increased.

## Repository Layout

```
core/              shared package: capture I/O, measurement, 19 protocol decoders,
                   plus i18n (core/i18n.py), user config (core/config.py), and the
                   shared quick start guide (core/guide.py)
cli/               unified command-line interface (python -m cli)
gui/               graphical desktop application (python -m gui), including the
                   continuous-capture worker, signal panel, and onboarding wizard
locales/           gettext catalogs: zh_CN / zh_TW (.po sources + compiled .mo)
scripts/           pure-Python catalog compiler (scripts/compile_mo.py)
examples/          sample .sr captures and a CSV log example
firmware/          prebuilt firmware (.hex/.bin)
firmware/src/      complete firmware C source + standalone Makefile (see BUILD.md)
docs/              BOM and documentation
```

## Build from Source

The complete firmware source is in `firmware/src/`. With the WCH RISC-V
toolchain (bundled with MounRiver Studio) on your `PATH`:

```bash
cd firmware/src
make            # UART firmware
make SQUARE=1   # 1 kHz square-wave firmware
```

See [firmware/src/BUILD.md](firmware/src/BUILD.md) for the full guide.

## Roadmap

- **Universal protocol encoder** - multi-channel firmware output driven by
  timer + DMA + GPIO hardware playback (CPU-independent timing), with
  symmetric encode/decode in the core and a closed-loop
  generate-capture-decode verification.
- **More real board backends** - additional HAL adapters, each backed by the
  official datasheet and physical-board measurements (no simulated data).
- **Native installers** - standalone macOS and Linux packages alongside the
  Windows PyInstaller build.
- **Hardware** - 16 channels, higher sampling rates, USB high-speed upload,
  and a burst sampling architecture.

## License

Released under the **GNU General Public License v3.0 (GPL-3.0)**. See
[LICENSE](LICENSE).
