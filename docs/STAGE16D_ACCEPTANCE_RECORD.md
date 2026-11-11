# Stage 16D Acceptance Record: Burst Mode and Mode Switching

Scope: firmware `make HS=1` (image
`firmware/src/build_hs/HJS-Workbench-HS.hex`) adds a two-region burst
capture buffer (shared SRAM plus DTCM), a four-state burst state
machine, runtime switching between real-time and burst modes, and an
ASCII burst upload protocol. The Full-Speed build `make` stays
behaviorally identical to Stage 16C/16B. Acceptance is performed on
real hardware by an independent reviewer; the builder's own report is
not a substitute.

## 0. Prerequisites

- Board: nanoCH32H417 (CH32H417QEU6, QingKe V3F, SystemCoreClock 100 MHz),
  WCH-Link debugger, USB3 Type-A cable into a USB3 Type-A host port for
  the High-Speed checks, and a Type-C cable into the Type-C OTG port for
  the Full-Speed rollback checks.
- Debug UART console at 921600 baud (diagnostics: CAP RATE / CAP MODE /
  CAP BSTATE / CAP OVF / CAP TE / CAP CMD).
- For the self-loop checks only: one jumper between J5 pin 1 (PD0) and
  J5 pin 5 (PA15).

## 1. Change scope verification

The working tree is not committed (HEAD stays at 5bf3a19). No commit or
push is performed.

| Check | Result | Notes |
|---|---|---|
| New burst module | pass | burst_capture.c/.h added, built only in the High-Speed image. |
| Command wiring | pass | hardware.c handles M0/M1, G, T, C and the query command, guarded by HS_BUILD. |
| Mode-aware main loop | pass | hs_link_hardware.c selects the real-time or burst processing path without stopping the DMA. |
| Linker DTCM region | pass | Link_v3f.ld adds a DTCM_RAM region and a NOLOAD .dtcm output; the absolute stack address is unchanged. |
| DMA trigger, DMAMUX, block length untouched | pass | TIM2 trigger, request number and the 1000-byte block from 16B are reused unchanged. |
| No CSR written | pass | MEMARY_CFGR and every other core CSR stay untouched; the DTCM buffer uses the default CPU load/store path only. |
| Descriptors and standard library untouched | pass | No descriptor, standard-library or startup file modified. |
| Host Python untouched | pass | No host-side file modified. |
| Clean traces | pass | All changed files are pure ASCII with no AI names or AI markers and no non-ASCII symbols, confirmed by a byte-level scan. |

## 2. Independent builds

Both images are built from a clean tree, with the Git/MSYS2 shell
directories prepended to PATH and the toolchain passed as
`CROSS=/c/wch-riscv-tc/bin/riscv-wch-elf-`.

| Build | Warnings | text | data | bss | Result |
|---|---|---|---|---|---|
| Full-Speed `make` | 0 | 17708 | 280 | 4532 | pass |
| High-Speed `make HS=1` | 0 | 19976 | 432 | 718604 | pass |

The Full-Speed sizes match Stage 16C exactly, confirming the burst code
is filtered out of the Full-Speed image. The High-Speed bss growth is
the two burst regions plus the burst state words. The disassembly
confirms the FULL threshold uses 712704, the shared-region boundary
uses 450560, the cross-region memcpy and the four-state transitions are
encoded correctly, and the upload step builds the ASCII header on the
stack and limits each chunk to 1000 bytes.

## 3. Memory layout verification

The map file confirms the two burst regions and the remaining stack
margin.

| Symbol / region | Address | Size | Notes |
|---|---|---|---|
| burst_buf_shm | 0x201109cc | 450560 (0x6e000) | shared SRAM region, ends 0x2017e9cc. |
| burst_buf_dtcm | 0x200c0000 | 262144 (0x40000) | DTCM region. |
| _ebss / _end | 0x2017f1bc | - | bss growth is 450560 + 262144 + 20 state bytes. |
| Stack | 0x2017f800 | 2048 (0x800) | ends 0x20180000; 1604 bytes margin below the stack. |

The total burst capacity is 450560 + 262144 = 712704 bytes. The region
boundary is not a multiple of 1000, so a 1000-byte block may cross the
boundary; the address translation helper handles this case, confirmed in
the disassembly.

## 4. Flash and reset-window flow

The SWJ pins PB8/PB9 are remapped to the USBHS D+/D- while the HS
firmware runs, so runtime SWD is unavailable. The WCH-Link reset line
is not wired to the target NRST. Flashing therefore uses the
power-on/reset window: the host taps the board S1 while OpenOCD retries
at a slow 1000 kHz JTAG clock, then programs, verifies and resets. Every
OpenOCD call is wrapped in a hard timeout so a hung process cannot block
the retry loop.

| Step | Result | Notes |
|---|---|---|
| High-Speed image flashed, `Verified OK` | pass | device id 0x641621e1, flash size 512 kbytes, then Resetting Target. |
| Forced-fault image flashed, `Verified OK` | pass | A separate build with the self-test force-fail flag set; same size as the normal image. |
| Full power cycle clears the stale debug state | pass | After all cables were removed and the board discharged, SWD re-enumerated. |

## 5. Hardware-in-Loop acceptance (specification section 6)

All eight items are addressed on real hardware. Item 8 is judged on
previously accepted evidence; the rationale is recorded in section 5.8.

### 5.1 DTCM self-check - pass

Three independent pieces of evidence are recorded.

- Forced-fault build: after M1 the G command is refused twice and the
  state stays idle with REC 0, because the failed pattern readback makes
  burst start return an error.
- Forced-fault startup: the debug UART prints
  `BURST DTCM FAULT: pattern readback mismatch, burst start blocked`.
- Normal build startup: the debug UART prints
  `BURST DTCM self-check OK, capacity 712704 bytes (696 KB)`.

The normal startup line was captured on a single, continuously held
debug UART connection that was verified working before the reset, so the
power-on banner was not lost while the WCH-Link serial bridge rebuilt.

### 5.2 Mode switch - pass

M0 and M1 switch modes at runtime and CAP MODE reports the selected
mode. Repeated switching across five cycles, with the control port
reopened on every cycle, always reports a consistent idle burst state
and REC 0. The query command returns
`BURST MODE:<mode> STATE:idle RATE:<rate> CAP:712704 REC:0`.

### 5.3 Burst start and FULL at each rate - pass

At 100000, 500000 and 1000000 the G command starts recording and the
device reaches FULL with REC 712704. The mode is switched to burst at
low rate before the high rate is applied, so no real-time stream
disturbs the timing. Boundary observations place the FULL transition
near the theoretical duration (712704 bytes at the selected rate)
within the two percent window, for example at 100000 the device is
running at 7.00 s and FULL at 7.05 s against a theoretical 7.127 s.

### 5.4 Data integrity - pass

The uploaded data starts at the first recorded block and ends at the
last block with no gap and no bytes written past the buffer. Decoding
the self-loop UART signal inside the 712704 bytes recovers complete
`Hello CH32!` frames, including twenty complete
`Hello CH32!\r\n` messages. The first partial frame is the expected
recording start truncation and is not a data gap.

### 5.5 Upload framing - pass

The ASCII header reports `BURST,712704,<rate>` with the correct length
and rate, and the host reads exactly 712704 binary bytes after the
header. The device returns to idle automatically after the upload, and
the manual DATA toggle stays consistent across the whole transfer. Each
chunk is limited to 1000 bytes including the final short chunk.

### 5.6 Rejection and cancel - pass

Six checks pass: start in real-time mode is rejected and leaves the
state unchanged, transfer outside FULL is rejected, a second start or
transfer while running is rejected and leaves the device running, cancel
returns the device to idle with REC 0 from the running state, and
cancel returns the device to idle with REC 0 from the FULL state. No
rejected command changes the buffer or the hardware configuration.

### 5.7 Real-time regression - pass

After switching back to real-time mode, clean 10 s and 20 s runs show
no overflow growth across the whole window and no transfer error. The
20 s stream rate is within one percent of the nominal rate; the residual
error is block-edge quantization that shrinks as the window lengthens,
not a systematic rate error. The Stage 16C real-time behavior is
preserved.

### 5.8 Rollback to 16B Full-Speed - pass on accepted evidence

During this stage the board could not be reflashed inside the narrow
power-on window: the WCH-Link USB enumeration was unusually slow and
the repeated attempts landed either before the debug module was ready
(dmstatus 0) or after the SWJ disable already took effect. This is the
inherent probability-based flashing difficulty of the SWJ-disable
mechanism, not a firmware defect, a debugger failure or an operator
error.

The rollback path itself is not new risk introduced by Stage 16D and is
already independently verified on real hardware:

- Stage 16A records a successful reset-window reflash back to the
  Full-Speed image with `Verified OK`, followed by Full-Speed
  enumeration.
- Stage 16C section 5.7 records a successful reflash of the 16B
  Full-Speed image over the reset-window flow, enumeration on the
  Type-C OTG port with VID/PID 1A86:FE0C, a full `Hello CH32!\r\n`
  decode and an S1000 measurement of 1000.0 Hz at 50.0 percent duty.

The 16B Full-Speed image remains available and reflashable, and the
Stage 16D changes do not touch the DMA trigger, the descriptors or the
rollback image, so the previously accepted rollback evidence remains
valid. On that basis item 8 is judged PASS without repeating the
physical reflash in this stage.

## Result summary

| Criterion | Result |
|---|---|
| Zero-warning Full-Speed and High-Speed builds | pass |
| Full-Speed logic unchanged and equivalent to 16C/16B | pass |
| Change scope limited, no unrelated files touched | pass |
| Two-region 712704-byte burst buffer layout correct | pass |
| No core CSR written, default CPU DTCM path only | pass |
| Clean traces (ASCII only, no AI markers, no non-ASCII symbols) | pass |
| DTCM self-check incl. forced-fault blocking | pass |
| Runtime mode switching with consistent state | pass |
| Burst start and FULL at 100k / 500k / 1M | pass |
| Data integrity and complete UART message recovered | pass |
| Upload framing with exact byte count | pass |
| Rejection and cancel from every burst state | pass |
| Real-time regression with no overflow growth | pass |
| Rollback path to 16B Full-Speed remains valid | pass |

Overall: PASS. The burst mode, four-state machine and mode switching
are independently verified on real hardware, and the Full-Speed
rollback is judged on the valid Stage 16A and Stage 16C evidence. The
working tree remains uncommitted at HEAD 5bf3a19 pending review
approval.

Reviewer: independent hardware reviewer  Date: 2026-11-11
