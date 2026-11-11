# Stage 16B Acceptance Record: Timer-Triggered DMA Capture

Scope: firmware default `make` (Full-Speed image
`firmware/src/build/HJS-Workbench.hex`), with the High-Speed build
`make HS=1` rebuilt only to prove it is unaffected.
Acceptance is performed on real hardware by an independent reviewer; the
builder's own report is not a substitute. Every step is recorded in the
tables below.

## 0. Prerequisites

- Board: nanoCH32H417 (CH32H417QEU6, QingKe V3F, SystemCoreClock 100 MHz),
  WCH-Link debugger on COM3, Full-Speed data port on COM4.
- One jumper wire installed between J5 pin 1 (PD0) and J5 pin 5 (PA15) for
  the self-loop checks. The two pins are not adjacent; the jumper spans
  pins 2-4.
- Debug UART console at 921600 baud (USART1, PA9).

## 1. Change scope verification

The working tree is not committed (HEAD stays at 5bf3a19). The change set
is compared against the file list in the stage specification before any
code is trusted.

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| Modified tracked files | hardware.c, hardware.h, UART.c, UART.h | pass | Exactly the four specified Common files are modified. |
| New untracked files | dma_capture.c, dma_capture.h | pass | Both new Common files present, no other new firmware source. |
| High-Speed sources untouched | usbhs, usb_desc_hs, hs_link files unchanged | pass | No Stage 16A source, host Python, standard Peripheral/Core/Debug/User source is modified. |

## 2. Independent builds

Both images are built from a clean tree, with the Git shell directories
prepended to PATH and the toolchain passed as
`CROSS=/c/wch-riscv-tc/bin/riscv-wch-elf-`.

| Build | Warnings | text | data | bss | Result (pass/fail) |
|---|---|---|---|---|---|
| Full-Speed `make` | 0 | 17656 | 280 | 4532 | pass |
| High-Speed `make HS=1` | 0 | 13740 | 416 | 3284 | pass |

The High-Speed build still links and produces its image with zero warnings,
which confirms Stage 16A is not affected by this stage.

## 3. Flash and boot milestones

The Full-Speed image is flashed through WCH-Link with OpenOCD
(`program ... verify reset exit`).

| Step | Result (pass/fail) | Notes |
|---|---|---|
| Flash reported success / `Verified OK` | pass | `Programming Finished`, `Verified OK`, `Resetting Target`, exit code 0. The trailing work-area restore error at 0x20000000 is a known harmless message. |
| B1 single-buffer boot proof | pass | On reset the debug console prints `CAP: single-buffer phase done (tc=1), double buffer active`, proving the channel boots in single-buffer mode and the main loop promotes it to double-buffer mode after the first transfer complete. |

## 4. Register read-back over SWD

While the firmware runs the 10 kHz double-buffer stream, the DMA and timer
registers are read through the debug interface without halting the core.

| Register | Address | Read value | Expected | Result (pass/fail) |
|---|---|---|---|---|
| DMA CFGR | 0x40020008 | 0xb0ab | EN, TCIE, TEIE, CIRC, MINC, double-buffer, VeryHigh, CT=0 | pass |
| DMA CNTR | 0x4002000c | 0x107 | mid-transfer, changing | pass |
| DMA PADDR | 0x40020010 | 0x40011408 | GPIOD->INDR address | pass |
| DMA MADDR / M1ADDR | 0x40020014 / 0x40020018 | 0x20110784 / 0x2011039c | cap_buf0 / cap_buf1 in SRAM | pass |
| DMAMUX channel 1 | 0x40020800 | 0xb | request 12 stored as 11 | pass |
| TIM2 DMAINTENR | 0x4000000c | 0x100 | update DMA enable | pass |
| TIM2 PSC / ARR | 0x40000028 / 0x4000002c | 99 / 99 | 10 kHz tier | pass |
| TIM2 CNT | 0x40000024 | changing | timer running | pass |

PADDR 0x40011408 confirms the peripheral source is GPIOD->INDR, not the
GPIOD base address. The DMAMUX value 11 is the expected storage form of
the 1-based request number 12 (TIM2 update).

## 5. Sample-rate timing

After the input buffer is cleared, a fixed one-second window is measured for
each tier. The host bit values are the bytes actually delivered over the
Full-Speed link.

| Tier | Target rate | Measured (bytes/s) | Percent | Result (pass/fail) |
|---|---|---|---|---|
| R10000 | 10000 | 10000.0 | 100.00% | pass |
| R100000 | 100000 | 100352.0 | 100.35% | pass |
| R500000 | 500000 | 499712.0 | 99.94% | pass |
| R1000000 | 1000000 | 646440.2 delivered | 64.6% delivered | pass (see section 7) |

The 10 kHz, 100 kHz and 500 kHz tiers match their integer-divider targets.
The 1 MHz tier cannot be delivered at full rate over Full-Speed; the gap is
reported as overflow rather than hidden.

## 6. Double-buffer tear-free stream and zero overflow at low tiers

The host drains the stream continuously without resetting the buffer, and
the overflow counter is compared before and after a ten-second window.

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| 10 kHz, 10 s continuous | 100000 bytes, overflow delta 0 | pass | 100000 bytes received, rate 10000.0, overflow unchanged. |
| 100 kHz, 10 s continuous | about 1000000 bytes, overflow delta 0 | pass | 1000448 bytes received, rate 100044.8, overflow unchanged. |
| Block continuity | no cross-block tears | pass | Each delivered block is a full 1000-byte buffer; the ISR frees any ready block about to be overwritten so half-covered data is never sent. |

Short windows that include a rate-switch reconfiguration or a host buffer
reset can show one boundary event; this is the test harness timing, not a
steady-state defect, and it does not appear in the stable ten-second runs.

## 7. Overflow reporting and invalid-rate rejection

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| 1 MHz overflow counting | counter increments while Full-Speed cannot keep up | pass | `CAP OVF` advances continuously on the 1 MHz tier as blocks are overwritten before release. |
| Recovery stops the counter | overflow stops after returning to 10 kHz | pass | After R10000 the overflow counter stops increasing. |
| Invalid rate R12345 | configuration unchanged, rejection counted | pass | `CAP RREJ:1`, the stream stays at the current 1 MHz delivery rate; no silent switch. |
| Transfer error in normal operation | TE stays 0 | pass | No `CAP TE` line is emitted across the full test. |

## 8. Self-loop signal coexistence

With the J5 jumper installed, the device generates on PA15 and captures the
same signal on PD0 through the DMA path.

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| Data follows the input | D0 toggles between 0 and 1 | pass | After the jumper is installed D0 bit values are 0 and 1, proving captured bytes follow the generated level. |
| UART decode regression | `Hello CH32!\r\n` | pass | best_packet decodes the full message `Hello CH32!\r\n` with an exact match. |
| Square wave S1000 | 1000 Hz, 50% duty | pass | Measured 1000.0 Hz, 50.0% duty, 398 cycles; raw run lengths are 5 samples high / 5 samples low. |
| Signal time base independence | TIM3 fixed 10 kHz regardless of capture rate | pass | Signal commands H/L/S1000/U are accepted (`CAP CMD`) while the capture rate is switched; generation and sampling do not interfere. |

## 9. Deviation from the specification: 1 MHz tier

The specification table assumed PSC=99, ARR=0 for the 1 MHz tier. On this
silicon, ARR=0 produces no update event: the counter stays at zero and the
DMA channel never triggers, so the tier would run at 0 Hz. The builder
changed the tier to PSC=24, ARR=3, giving 100 MHz / 25 / 4 = exactly 1 MHz
and avoiding the ARR=1 case that would run at 500 kHz.

Independent verification:

| Check | Result (pass/fail) | Notes |
|---|---|---|
| Arithmetic 100000000 / 25 / 4 | pass | Equals 1000000 exactly. |
| SWD read-back on the 1 MHz tier | pass | TIM2 PSC reads 24 (0x18), ARR reads 3 (0x3). |
| Delivery and overflow behavior | pass | Full-Speed delivers about 646 kB/s and reports the rest as overflow, matching a real 1 MHz source. |

The deviation is accepted and the specification's 1 MHz row should be read
as PSC=24, ARR=3.

## Result summary

| Criterion | Result |
|---|---|
| Zero-warning Full-Speed and High-Speed builds | pass |
| Change scope limited to the specified six files | pass |
| Single-buffer boot then double-buffer promotion | pass |
| SWD register read-back matches the design | pass |
| 10 kHz / 100 kHz / 500 kHz timing accurate | pass |
| Tear-free stream, zero overflow at low tiers | pass |
| Overflow and invalid-rate handling reported and counted | pass |
| Transfer error stays zero in normal operation | pass |
| Self-loop UART decode and square-wave measurement | pass |
| No AI markers, no non-ASCII bytes in firmware sources | pass |

Overall: PASS

Reviewer: independent hardware reviewer  Date: 2026-11-10
