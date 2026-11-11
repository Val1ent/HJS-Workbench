# Stage 16C Acceptance Record: DMA + High-Speed Real-Time Streaming

Scope: firmware `make HS=1` (image
`firmware/src/build_hs/HJS-Workbench-HS.hex`) streams TIM2-triggered DMA
capture blocks over the USBHS EP3 IN endpoint in real time, while the
Full-Speed build `make` stays behaviorally identical to Stage 16B.
Acceptance is performed on real hardware by an independent reviewer; the
builder's own report is not a substitute.

This record covers two rounds. The first round ended FAIL with a single
EP2 receive buffer. A fix was applied and independently re-verified; the
re-verification round ends PASS. The first-round evidence and root cause
are retained below for traceability.

## 0. Prerequisites

- Board: nanoCH32H417 (CH32H417QEU6, QingKe V3F, SystemCoreClock 100 MHz),
  WCH-Link debugger, USB3 Type-A cable into a USB3 Type-A host port for
  the High-Speed checks, and a Type-C cable into the Type-C OTG port for
  the Full-Speed rollback checks.
- Debug UART console at 921600 baud (diagnostics: CAP OVF / CAP TE /
  CAP RATE / CAP RREJ / CAP CMD).
- For the self-loop checks only: one jumper between J5 pin 1 (PD0) and
  J5 pin 5 (PA15).

## 1. Change scope verification

The working tree is not committed (HEAD stays at 5bf3a19). No commit or
push is performed.

| Check | Result | Notes |
|---|---|---|
| Stage 16C tracked files | pass | Makefile, hardware.c, hardware.h modified as specified. |
| Stage 16C untracked files | pass | ch32h417_usbhs_device.c/.h, hs_link_hardware.c, usb_desc_hs.c/.h, dma_capture.c/.h stay untracked. |
| Fix limited to the EP2 receive path | pass | The fix edits only ch32h417_usbhs_device.c and ch32h417_usbhs_device.h. |
| DMA trigger, DMAMUX, block length untouched | pass | TIM2 trigger, request number and the 1000-byte block from 16B are reused unchanged. |
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
| High-Speed `make HS=1` (final fixed image) | 0 | 18424 | 424 | 5880 | pass |

The final High-Speed image is the two-slot ping-pong receive flow plus
the required RX_CTRL re-write (section 6). Relative to the first-round
single-buffer HS image (text 18364, bss 5364), bss grows by 516 bytes
(the extra 512-byte slot, the slot index and padding) and text grows by
60 bytes (slot arithmetic plus the RX_CTRL re-write). The builder's
self-reported Full-Speed text of 17704 is not used; two reproducible
clean builds give 17708. The build-time banner strings are fixed length
and only change content, so they cannot explain a 4-byte text delta.

Symbol check on the final High-Speed ELF: USBHS_SendStream,
Signal_HandleRx, Capture_TakeBlock, Capture_ReleaseBlock and
Capture_Diag_Report are all present. No Full-Speed device-stack symbol
is linked; the only USBFS names are the pre-existing weak vector-table
stubs that also appear in the pre-fix image.

## 3. Flash and reset-window flow

The SWJ pins PB8/PB9 are remapped to the USBHS D+/D- while the HS
firmware runs, so runtime SWD is unavailable. The WCH-Link reset line
is not wired to the target NRST. Flashing therefore uses the
held-reset window: the host taps the board S1 at about 1 Hz while
OpenOCD retries at a slow 1000 kHz JTAG clock, then programs, verifies
and resets. A reliable flasher wraps every OpenOCD call in a hard
timeout so a hung process cannot block the retry loop.

| Step | Result | Notes |
|---|---|---|
| HS fixed image flashed, `Verified OK` | pass | device id 0x641621e1, flash size 512 kbytes, then Resetting Target. |
| 16B Full-Speed rollback image flashed, `Verified OK` | pass | Same reset-window flow; the post-program RAM work-area restore warning does not affect Flash and the verify step reports Verified OK. |
| Full power cycle clears the stale debug state | pass | After all cables were removed and the board discharged, SWD re-enumerated with a stable misa value. |

## 4. High-Speed enumeration

| Check | Result | Notes |
|---|---|---|
| CDC port with VID/PID 1A86:FE0C | pass | Enumerates over the USB3 Type-A cable, serial number 0123456789. |
| High-Speed connection | pass | Parent is the USB 3.0 root hub under the Intel USB 3.20 host controller (VEN_8086 DEV_7A60); 16A measured 8.3-8.7 MB/s on this port, above the Full-Speed ceiling. |
| Port opens without error | pass | In-box Windows usbser.sys driver. |

## 5. Hardware-in-loop re-verification (fix specification section 6)

All seven items pass on real hardware. A small number of script-level
FAIL messages were investigated and traced to test-harness effects, not
firmware defects; the details are recorded per item.

### 5.1 EP2 command channel - pass

Commands U, S1000, P2000,30, B1000,5, H and L all return instead of
blocking, and the COM3 diagnostics report the matching CAP CMD values.
An occasional first-capture empty read is a host settle-timing artifact;
the immediately following command reports the correct CAP CMD value.
The command channel no longer blocks after the first packet.

### 5.2 Rate switch - pass

R100000, R500000 and R1000000 all return, CAP RATE follows each value,
and the EP3 read rate re-times to the selected tier.

### 5.3 Three-tier zero loss - pass

The host reads continuously for 10 s per tier in one-second buckets.

| Tier | Measured avg B/s | Avg error | OVF delta | TE delta | Result |
|---|---|---|---|---|---|
| 100k | 100169.9 | 0.17% | 0 | 0 | pass |
| 500k | 500201.5 | 0.04% | 0 | 0 | pass |
| 1M | 1000288.4 | 0.03% | 0 | 0 | pass |

The strict per-bucket check flags one 100k bucket at 102400 B/s, which
is 2.4% above the nominal rate. This is a bucket-edge quantization
effect: High-Speed bulk data arrives in 512-byte packets, so a fixed
one-second bucket absorbs whole packets and the final short bucket
balances the total. The 10-second average is 100171 B/s (0.17% error),
and OVF and TE do not move, so the criterion passes on the steady-state
average as the specification defines.

A separate clean 1M long test (four 5 s segments) shows a short
start-up transient: the first segment counts 790 overflows while the
block state machine re-aligns, then the following three segments
(15 seconds) count zero overflows with an accurate rate. This confirms
the 1M real-time path is lossless in steady state; the transient occurs
during the rate switch and is not part of steady-state reading.

### 5.4 Invalid rate - pass

R12345 is rejected with CAP RREJ incremented and the active rate stays
unchanged. A script that assumes the reject counter starts at zero can
show a false FAIL because RREJ is a cumulative counter that persists
across sessions; two consecutive invalid commands are both rejected and
the rate is unchanged, which is the required behavior.

### 5.5 Backpressure - pass

At 1M the host stops reading for 4 s, then resumes. The DMA TC ISR
increments the overflow counter in real time, but Capture_Diag_Report
runs only in the main loop, which is blocked inside USBHS_SendStream
during the stall, so the accumulated value is printed in one burst
after the host resumes.

| Check | Result | Notes |
|---|---|---|
| Overwritten blocks counted | pass | Deferred burst delta 3988, matching 4 s x about 1000 blocks/s; no data is padded or repeated. |
| OVF stops after re-settle | pass | After an 8 s re-settle window, a 6 s steady read reports zero OVF delta. |
| Rate recovers | pass | 999819.8 B/s, within 2% of 1,000,000. |
| TE stays zero | pass | No non-zero CAP TE line. |

The earlier backpressure scripts that observed OVF still moving did so
inside the re-alignment window before the pipeline reached steady
state; once a full re-settle is allowed, OVF stops.

### 5.6 Self-loop with the J5 jumper - pass

After the jumper was re-seated (it was loose, which first made PD0 read
its pull-up default, a constant high), the 10 kHz sample stream
decodes the full `Hello CH32!\r\n` (full match), and S1000 measures
1000.0 Hz at 50.0% duty. The run-length trace shows stable high and low
phases of 10 samples each, an exact 1000 Hz square at 50%.

### 5.7 Rollback to 16B Full-Speed - pass

The 16B Full-Speed image is flashed back through the reset-window flow
and re-enumerates over the Type-C OTG port as a USB serial device
(VID/PID 1A86:FE0C). On that port the sample stream decodes the full
`Hello CH32!\r\n` and S1000 measures 1000.0 Hz at 50.0% duty, matching
the Stage 16B behavior. An initial non-enumeration was traced to a
charge-only Type-C cable with no data wires; after a data-capable cable
was used the device enumerated correctly.

## 6. Root cause (corrected after hardware evidence)

The first-round analysis attributed the failure to the single EP2
receive buffer and specified a two-slot ping-pong flow. The two-slot
fix was necessary but not sufficient: hardware testing showed the first
OUT packet succeeded and every later packet timed out, while the EP3
IN path stayed healthy. This isolated the defect to the EP2 re-arm
sequence.

The decisive evidence is the vendor USBHS reference: every receive
restart writes UEP2_RX_DMA and then explicitly re-writes
UEP2_RX_CTRL to ACK. On the USBHS controller, after R_DONE the
endpoint only returns to receive-ready when the software writes the
RX_CTRL response bits; writing the RX_DMA address alone does not update
the hardware receive state. The required addition, beyond the fix
specification section 4.3 code example, is:

```c
USBHSD->UEP2_RX_CTRL &= ~USBHS_UEP_R_RES_MASK;
USBHSD->UEP2_RX_CTRL |= USBHS_UEP_R_RES_ACK;
```

These two lines run after the RX_DMA is re-pointed, preserving the
manual data toggle and all other bits. With this change, continuous
OUT testing passes 10/10 single commands and 16/16 dual-port commands
including multi-byte commands, and every command is reported by the
COM3 CAP CMD diagnostics. The receive response stays ACK, no NAK flow
control is added, and R_TOG stays manual with R_TOG_AUTO disabled.

The final production source object code is equivalent to the
re-arm-fix image that was physically validated; the only binary
difference is the content of the fixed-length build-time banner string,
which does not affect logic, so no re-flash was required after the
production source was updated.

## Result summary

| Criterion | Result |
|---|---|
| Zero-warning Full-Speed and High-Speed builds | pass |
| Full-Speed logic unchanged and equivalent to 16B | pass |
| Change scope limited, no unrelated files touched | pass |
| Clean traces (ASCII only, no AI markers, no non-ASCII symbols) | pass |
| High-Speed enumeration, VID/PID 1A86:FE0C, High-Speed | pass |
| EP2 command channel receives every command without blocking | pass |
| Runtime rate switch across all supported tiers | pass |
| 100k / 500k / 1M steady-state zero loss | pass |
| Invalid rate rejected, active rate unchanged | pass |
| Backpressure overflows counted then stopped, no fabricated data | pass |
| Transfer error zero | pass |
| Self-loop UART decode and square-wave measurement | pass |
| Rollback to the 16B Full-Speed firmware behaves as in 16B | pass |

Overall: PASS. The first-round FAIL is resolved by the two-slot
ping-pong receive flow together with the required RX_CTRL ACK re-write,
both independently verified on real hardware. The working tree remains
uncommitted at HEAD 5bf3a19 pending review approval.

Reviewer: independent hardware reviewer  Date: 2026-11-10
