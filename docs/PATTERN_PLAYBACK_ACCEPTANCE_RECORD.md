# Pattern Playback Decoder Verification - Independent Acceptance Record

Task: 110, real-hardware decode verification of the 19 protocol decoders.
Acceptance executed independently by Doubao on 2026-11-14. The conclusion
below comes from an independently written run on the real board, not from
the construction logs.

## 1. Scope and method

The firmware gains a loadable pattern playback source (sig_mode 5). The host
sends a level sequence over the command channel, the firmware drives real
GPO pins at one byte per 100us TIM3 tick, and the real capture path reads
PD0-7 back through jumper wires. Each decoder runs on the bytes read from
the real data port.

The acceptance script was written independently for verification. It does
not import the construction loader (core/hal/pattern): the W/K/L commands,
chunk transfer and reads are re-implemented, and the value passed to each
decoder is always the captured byte stream, never the generated waveform.

## 2. Commit and change boundary

- Commit: 25747f4 "Add loadable pattern playback to the signal generator".
- Files changed: firmware/src/Common/hardware.c and the new
  core/hal/pattern.py only. hardware.h is untouched. No other file changed.
- The working tree is clean and the code matches the task specification
  sections 3.1-3.9 and 4. Shared state is declared volatile and the GPO
  pins are changed through BSHR/BCR.

## 3. Build evidence

Clean build with make HS=1. Exit code 0. No warning or error line appears
in the build log. Size: text=18888 data=424 bss=13880. The HS binary is
19312 bytes. The 8000-byte pattern buffer fits in RAM with headroom.

## 4. Real hardware-in-loop result

Physical setup: six jumpers, PA15 to PD0 and PC7-PC11 to PD1-PD5. Data
port discovered by VID:PID 1A86:FE0C (COM8). Sample rate 10000.

Independent run result: 17/17 decoder checks passed. For every decoder the
captured byte count reached the required count (no short-data decode), the
capture is not a copy of the generated waveform, and a middle slice of the
channel-0 logic is found inside the real capture.

- Single-channel group (8): manchester, dht11, nec, onewire, rc5, sirc,
  modbus, nmea - all passed.
- Multi-channel group (9): ds1302, i2c, encoder, hd44780, spi, stepper,
  swd, ultrasonic, wiegand - all passed.

## 5. Data reality checks

The real capture carries a constant high level on the unused high input
channels (a fixed 0xC0 pattern on this board) and a front pre-roll offset
before the waveform begins, so the captured bytes are not byte-identical to
the generated table. After masking to channel 0 the protocol logic matches
exactly at the measured offset, and every decoder produces its expected
events. This confirms the data round-tripped through real pins, real
voltage levels and the real capture path rather than through a software
replay.

## 6. Fan and servo regression

The fan and servo decoders were re-run independently on the new firmware:
2/2 passed. Fan reads 3000 RPM and the servo reads a 1400us pulse at 72.0
degrees, matching the expected values. The firmware change introduces no
regression.

## 7. Compliance

Both committed files are pure ASCII and contain no AI name, no AI-generated
or AI-assisted marker, and no emoji.

## 8. Conclusion

Independent verification on real hardware: 19/19 decoders passed (17 via
pattern playback plus the fan and servo re-run). The result is accepted.
