# Pattern Playback GUI - Independent Acceptance Record

Acceptance executed independently on 2026-11-21. This record covers turning
the verified pattern playback capability into a GUI product. Every check
below was run against the live product functions and the real device rather
than the construction report.

## 1. Scope and commits

The work was delivered in three commits, each reviewed before the next.

- 30643ae: Add GUI pattern playback (editor panel, playback capture, tests,
  and i18n). Twenty files: the pattern panel, main window integration,
  capture session helpers, six README titles, the four translation catalogs,
  and two new test modules.
- f84678f: Make the Manchester decoder robust against spurious head
  transitions. Three files: the decoder, its status text, and a contrast
  test.
- e10e932: Expand pattern playback capture window to one DMA block. Two
  files: the capture session and its tests.

The firmware, the HAL package, the other eighteen decoders, the translation
catalogs in the final rework, the README files, and the historical acceptance
records were not changed outside the commits above. No simulated or
fabricated data path was added; the panel only replays real samples captured
from the device.

## 2. Pre-release gates

The gates were re-run as a whole on the local machine after every rework.

- ruff check .: All checks passed.
- Unit tests: 104 tests, OK (the original 102 plus the head-glitch test and
  the default-margin test).
- GUI self-check (QT_QPA_PLATFORM=offscreen): Self-check: PASS.

## 3. Hardware-in-the-loop results

The data port is the real CH32 device at VID:PID 1A86:FE0C with the six
GPO-to-input jumpers connected. All runs used the product default
playback_pattern without overriding the margin.

- I2C: ten consecutive runs all decoded the complete four-event transaction
  START, ADDR, DATA, STOP, with DATA carrying 0x55 ACK. Each run captured
  2500 samples.
- Manchester: repeated runs decoded 27 events and the three bytes
  0x55, 0x48, 0x69.
- NEC: repeated runs kept the three events LEADER, NEC, REPEAT, confirming
  no regression.

## 4. Root causes found and fixed during acceptance

Two independent defects were found through hardware-in-the-loop testing and
fixed without changing the firmware.

1. Manchester head glitch: an extra level blip before the real signal made
   the fixed first-transition anchor decode only one bit. The decoder now
   scans the first six candidate start transitions against every half-bit
   candidate and keeps the combination with the highest score
   (complete bytes, total bits, no partial bits). A synthetic test proves the
   old fixed anchor fails on the same input where the new scan succeeds.
2. Capture window truncation: the sampling DMA sends complete 1000-byte
   blocks, so when the trigger lands inside a block up to one whole block of
   prior data precedes the new waveform. The old 300-sample margin cut off
   the tail of the real transaction in about half of the I2C runs. The
   default margin now equals one capture block (PATTERN_CAPTURE_BLOCK =
   1000), after which ten consecutive I2C runs all decoded fully.

## 5. Compliance

All changed files are pure ASCII and use the repository line endings. A
repository-wide scan found no AI name, no AI-generated or AI-assisted
marker, and no emoji in the changed files.
