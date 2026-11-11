# Stage 16A Acceptance Record: USB High-Speed Minimal Link

Scope: firmware `make HS=1` (image `firmware/src/build_hs/HJS-Workbench-HS.hex`).
Acceptance is performed on real hardware by an independent reviewer; the
builder's own report is not a substitute. Every step is recorded in the
tables below.

## 0. Prerequisites

- Board: nanoCH32H417, WCH-Link debugger, USB3 Type-A cable.
- Host port: a USB3 Type-A port (the Type-C OTG port must NOT be used;
  it is wired to the separate Full-Speed controller).
- Debug UART console on the board UART pins at 921600 baud (optional but
  recommended; the firmware prints
  `USBHS minimal link on PB8/PB9` and `USBHS device enabled`).

## 1. Flash the HS image

Flash `firmware/src/build_hs/HJS-Workbench-HS.hex` with WCH-Link (OpenOCD
or the MounRiver download tool), then power-cycle the board.

| Step | Result (pass/fail) | Notes |
|---|---|---|
| Flash reported success / `Verified OK` | pass | OpenOCD via WCH-Link: `Programming Finished`, `Verified OK`, `Resetting Target`, exit code 0. The trailing work-area restore error at 0x20000000 is a known harmless message. |
| Debug UART prints `USBHS minimal link on PB8/PB9` | pass | Link starts on PB8/PB9 after SWJ disable. |
| Debug UART prints `USBHS device enabled` | pass | USBHS device initialized and the pattern task runs. |

## 2. High-Speed enumeration

Connect the board's **USB3 Type-A port** to a USB3 Type-A host port with a
USB3 Type-A cable. Open Device Manager (or `lsusb -t` on Linux):

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| CDC serial port appears with VID/PID `1A86:FE0C` | present | pass | Enumerated as COM8 over the USB3 Type-A cable, serial number 0123456789. The FS OTG port COM4 disappears because the HS firmware does not initialize the FS controller. |
| Connection speed is High-Speed | 480 Mbps (Device Manager: "High-Speed" in the device's USB view; `lsusb -t` shows 480M) | pass | Parent node is the USB3 root hub; `DEVPKEY_Device_BiosDeviceName` = `_SB.PC00.XHCI.RHUB.HS08` (a high-speed port). The direct Speed property is not exposed on this host, so section 3 throughput provides the hard evidence. |
| COM port opens without error | opens | pass | COM8 opened and streamed data without error. |

A connection at Full-Speed (12 Mbps) or on the wrong port means the check
fails even if the port enumerates.

## 3. Pattern packet integrity

Open the COM port and read data. EP3 IN streams 512-byte packets in an
endless loop; for every packet n:

- bytes 0..3 = little-endian packet counter, first packet is 0;
- bytes 4..511 = `(i & 0xFF)` (i is the byte index).

Read at least 5000 packets (about 2.5 MB) and verify every byte. Any byte
error, any counter gap or any truncated packet fails this check.

Reference checker (run with the COM port number):

```python
import serial
port = serial.Serial("COMx", timeout=2)
expect = 0
rounds = 0
while rounds < 5000:
    pkt = port.read(512)
    if len(pkt) != 512:
        raise SystemExit("short packet: %d bytes" % len(pkt))
    cnt = pkt[0] | pkt[1] << 8 | pkt[2] << 16 | pkt[3] << 24
    if cnt != expect:
        raise SystemExit("counter gap: got %d expected %d" % (cnt, expect))
    for i in range(4, 512):
        if pkt[i] != (i & 0xFF):
            raise SystemExit("pattern error at offset %d" % i)
    expect += 1
    rounds += 1
print("OK: %d packets verified" % rounds)
```

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| 5000 packets, 0 byte errors | pass | pass | First run: 5000 packets, 0 byte errors, measured throughput 8.300 MB/s. |
| Counter sequence contiguous | no gaps/duplicates | pass | Little-endian counters contiguous across all 5000 packets; no gaps, duplicates or truncated packets. |
| Second run after re-plugging the cable | pass again | pass | After re-plug: 5000 packets, 0 byte errors, throughput 8.729 MB/s. First counter was 5088 because the board stayed powered through WCH-Link and the counter did not reset; the sequence stayed contiguous. |

The Full-Speed physical limit is about 1.5 MB/s. The measured 8.300 to 8.729 MB/s is far above that ceiling, which is hard evidence that the link negotiates High-Speed (480 Mbps), not Full-Speed.

## 4. SWJ-disable re-flash recovery (mandatory record)

The HS firmware disables SWJ to free PB8/PB9. Prove the board is not
bricked by flashing a different image afterwards.

Procedure:

1. Prepare the rollback image `firmware/UART_10kHz.hex` (or any other
   known-good image).
2. Disconnect the USB3 cable, connect WCH-Link.
3. Start the flash operation in the reset phase: apply power / press
   reset and start flashing immediately, or hold the connect attempt and
   power-cycle the board. Retry up to three times if needed.
4. After a successful flash, power-cycle and confirm the firmware runs
   (for the FS rollback image: the debug UART prints `SystemClk` and the
   signal generator resumes; the Type-C OTG port enumerates the original
   COM port again).
5. Repeat steps 3-4 once more from the HS image to prove the loop is
   repeatable.

| Attempt | Image flashed | Flash result | Firmware runs after reset | Notes |
|---|---|---|---|---|
| 1 | `firmware/UART_10kHz.hex` | pass, `Verified OK` | pass | Direct connect and `reset_config srst_only` both failed while the HS firmware ran (SWJ pins given to USBHS). Holding RESET returns the pins to SWJ; the auto-retry script (`retry_flash.ps1`, 0.7 s interval, budget 20) connected on attempt 6. COM4 re-enumerated after reset. |
| 2 | `firmware/UART_10kHz.hex` | pass, `Verified OK` | pass | Full loop repeated: HS image flashed first, then rollback. Quick taps and single launches missed the window; the fast retry script (`retry_flash_fast.ps1`, 0.3 s interval, budget 40) with RESET held connected on attempt 20. COM4 re-enumerated and the firmware runs. |

Failure of this check (board unrecoverable, repeated flash timeouts with
no connection in the reset phase) is a blocking defect for Stage 16.

## 5. Rollback to the Full-Speed firmware

| Check | Expected | Result (pass/fail) | Notes |
|---|---|---|---|
| `firmware/UART_10kHz.hex` flashed back | `Verified OK` | pass | Both recovery loops flashed the rollback image with `Verified OK`; COM4 (Type-C OTG, VID/PID 1A86:FE0C) re-enumerated. |
| Original 10 kHz capture + signal generator work on the Type-C port | works as in 0.6.0 | pass | Capture of 3000 points succeeded on both rollbacks; signal generator command `S1000` measured 1000.0 Hz at 50% duty cycle. |

## Result summary

| Criterion | Result |
|---|---|
| HS enumeration on the USB3 Type-A port | pass |
| 512-byte pattern packets, multi-round, no byte errors | pass |
| SWJ-disable re-flash recovery proven and recorded | pass |
| Original FS firmware retained and flashable | pass |

Overall: PASS

Reviewer: independent hardware reviewer  Date: 2026-11-10
