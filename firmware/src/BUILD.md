# Firmware Build Guide

This directory contains the complete, self-contained firmware source for the
CH32H417 HJS-Workbench. You can rebuild **exactly** the prebuilt
firmware files in `firmware/` from these sources.

## Directory layout

| Path | Contents |
|---|---|
| `Common/` | Application code: sampling + signal generator (`hardware.c`), USB CDC device, descriptors, soft-UART |
| `User/` | `main.c`, interrupt handlers, chip config, system clock |
| `Core/` | RISC-V QingKe core support |
| `Debug/` | Low-level debug / UART printf support |
| `Peripheral/` | WCH standard peripheral library (`inc/` headers + `src/` drivers) |
| `Startup/` | Startup assembly (`startup_ch32h417_v3f.S`) |
| `Ld/V3F/Link_v3f.ld` | Linker script for the QingKe V3F core |
| `Makefile` | Standalone command-line build (no IDE required) |
| `alternative_square_hardware.c` | Square-wave version of `hardware.c` (used automatically by `make SQUARE=1`) |
| `hs_link_hardware.c` | USB High-Speed burst capture main loop (used by `make HS=1`) |
| `Common/ch32h417_usbhs_device.[ch]` | USB High-Speed device stack on the USBHSD register block (PB8/PB9) |
| `Common/usb_desc_hs.[ch]` | HS/FS dual configuration descriptors, device qualifier, BOS descriptor |

## Toolchain

The firmware targets the **QingKe V3F** RISC-V core (RV32 with the WCH XW
extension). Use the toolchain that ships with MounRiver Studio:

- **MounRiver Studio 2** (includes RISC-V Embedded GCC 12, `riscv-wch-elf-gcc`)
- The `bin` folder of the toolchain must be on your `PATH` (it contains
  `riscv-wch-elf-gcc`, `riscv-wch-elf-objcopy`, ...)

## Build from the command line

```bash
cd firmware/src

make            # build the Full-Speed realtime firmware -> build/HJS-Workbench.hex/.bin
make SQUARE=1   # build the 1 kHz square-wave firmware
make HS=1       # build the USB High-Speed burst firmware -> build_hs/HJS-Workbench-HS.hex/.bin
make clean      # remove the build/ output folder
make HS=1 clean # remove the build_hs/ output folder
```

`make` produces `build/HJS-Workbench.hex` and `build/HJS-Workbench.bin`
(the Full-Speed realtime firmware); `make HS=1` produces
`build_hs/HJS-Workbench-HS.hex` and `build_hs/HJS-Workbench-HS.bin`
(the High-Speed burst firmware). `HS=1` and `SQUARE=1` select
alternative application variants and must not be combined in one invocation.

If your toolchain uses a different prefix, override it:

```bash
make CROSS=riscv-none-elf-
```

If the toolchain path contains spaces (the MounRiver Studio default path
does), make splits the command at the spaces. Create a junction to the
toolchain root first and use the junction as `CROSS`:

```
cmd /c mklink /J C:\wch-riscv-tc "E:\...\risc-v embedded gcc12"
make CROSS=/c/wch-riscv-tc/bin/riscv-wch-elf-
```

### Reproducible rebuilds

The firmware embeds `__DATE__` and `__TIME__`, so images rebuilt on
different days differ in bytes even from identical sources. Pin the
timestamp to reproduce a specific release image byte-for-byte:

```bash
make REPRO=1 REPRO_DATE="Nov  8 2026" REPRO_TIME="22:06:15"
```

Two builds with the same pin are byte-identical (verified). Note: the
prebuilt images in `firmware/` were produced by an earlier build session;
a fresh rebuild of the same sources may differ from them by more than the
date string if the build environment differed. When in doubt, use the
freshly built `.hex/.bin` from `build/` or `build_hs/`.

## Build with MounRiver Studio (GUI)

1. Open MounRiver Studio, create a workspace.
2. **File > Open Projects from File System** and import this `src` folder as a
   project (the `.cproject`/`.project` files from the original WCH example are
   not required for the command-line build; for the GUI, create a new
   CH32H417 project and add the `Common/`, `User/`, `Core/`, `Debug/`,
   `Peripheral/`, `Startup/` folders and the `Ld/V3F/Link_v3f.ld` linker
   script).
3. Select the V3F target and click **Build**.

## Flashing

Use the WCH-Link debugger with OpenOCD (also bundled with MounRiver Studio):

```bash
openocd -f wch-riscv.cfg \
  -c "program build/HJS-Workbench.hex verify reset exit"
```

`Verified OK` in the output means flashing succeeded. You can also flash the
`.hex` directly from the MounRiver Studio download tool.

### Flashing the High-Speed firmware and getting SWD back

The High-Speed firmware disables the SWJ remap (PB8/PB9 carry the USBHS
D+/D- signals), so a running HS board cannot be reached over SWD. Flashing
and re-flashing still work because the chip powers up with SWJ enabled and
only the running firmware disables it:

1. Build: `make HS=1`, flash `build_hs/HJS-Workbench-HS.hex` as above.
2. To flash again (back to `build/HJS-Workbench.hex` or a new HS image),
   connect WCH-Link and start the flash operation right after applying
   power / pressing reset, or hold the connection attempt and power-cycle
   the board. The tool grabs the core in the reset phase before the
   firmware disables SWJ.
3. If the board ends up in a state where the first attempt fails, power
   the board off, connect WCH-Link, power the board on and immediately
   start the flash. Repeat once or twice; the reset phase is always
   reachable.

This recovery path was part of the Stage 16A hardware acceptance; the
acceptance record lives in `docs/STAGE16A_ACCEPTANCE_RECORD.md`.

## High-Speed burst firmware (make HS=1)

The HS firmware runs the CDC device on the **USB3 Type-A port** of the
board (PB8/PB9 = USBHS D+/D-). The Type-C OTG port stays on the Full-Speed
controller and is not used by this firmware. Connect the board with a
**USB3 Type-A cable to a USB3 Type-A host port**; the device enumerates as
a CDC serial port at High-Speed (480 Mbps) with the same VID/PID
`1A86:FE0C` as the Full-Speed build.

- Endpoints keep the existing topology: EP1 IN interrupt (reserved), EP2
  OUT bulk (host commands), EP3 IN bulk (data upload).
- Bulk endpoints use 512-byte maximum packets in the HS configuration and
  64-byte packets in the FS configuration. EP2 uses two 512-byte receive
  buffers in ping-pong; after each packet the firmware re-arms the receive
  control register so the next command is never missed.
- The device provides device qualifier, BOS and other-speed descriptors
  in addition to the standard set.
- Two capture modes share one firmware: realtime streaming of raw samples,
  and burst capture into a 712704-byte (696 KB) buffer spread across the
  shared SRAM and the DTCM.
- The sample rate is selectable at 10 kHz, 100 kHz, 500 kHz, or 1 MHz;
  TIM2 triggers DMA1 channel 1 to copy the GPIO port into memory without
  interrupt-driven sampling.
- Burst upload frames the data with an ASCII header `BURST,<length>,<rate>`
  followed by the raw bytes in chunks of at most 1000 bytes.

Running this firmware disables runtime SWD debugging by design. Use the
debug UART (the same 921600 baud console as the FS firmware) to observe
the High-Speed startup and the burst self-check result.

## Key firmware parameters

- 8 capture channels: **PD0-PD7**
- Full-Speed build: USB 2.0 Full-Speed CDC on the Type-C port, fixed 10 kHz
- High-Speed build: USB High-Speed CDC on the USB3 Type-A port, selectable
  10 kHz/100 kHz/500 kHz/1 MHz, with realtime and burst modes
- DMA1 channel 1 copies the GPIO port into memory under TIM2 hardware
  triggers, so USB stalls do not interrupt sampling; the burst buffer holds
  712704 bytes (696 KB)
- Soft-UART test signal: message `"Hello CH32!"`, 1000 baud, 8N1, LSB first
- Square-wave test signal: 1 kHz, 50% duty on PA15

## Signal generator command set

Commands arrive as text on USB endpoint 2 and are parsed character by
character in the endpoint ISR; empty (length 0) packets perform no action.
`<freq>` is 1-5000 Hz, `<duty>` is 1-99 percent, `<count>` is 0-65535
pulses. Values outside the limits are clamped, never extrapolated.

| Command | Effect |
|---|---|
| `U` | Software UART: the board re-sends `Hello CH32!` at 1000 bps, 8N1 |
| `S<freq>` | 50% square wave at `<freq>` Hz |
| `P<freq>,<duty>` | PWM at `<freq>` Hz with `<duty>` percent high time |
| `B<freq>,<count>` | Burst: exactly `<count>` full periods at `<freq>` Hz, then hold the line high |
| `H` | Force the signal line high |
| `L` | Force the signal line low |

The signal is generated in the TIM2 interrupt every 100 us
(`Signal_Tick`); every mode branch is a bounded counter/compare, and the
100 us tick quantizes the duty-cycle resolution (for example a 1 kHz PWM
period is 10 ticks, so the duty steps in 10% increments). The square and
UART modes behave exactly as before. The 1-5000 Hz limit comes from the
10 kHz tick rate, and `Capture_Tick` (the sampling path) is unchanged.

## GUI / CLI signal control

The GUI signal panel writes these commands through the signal connection
at the backend's declared signal baud (921600) and validates the inputs
against the same limits; the CLI signal generator sends square-wave and
UART commands. Loop PA15 (A15) back to PD0 (D0) to capture the generated
signal.
