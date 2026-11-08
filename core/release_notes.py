# -*- coding: utf-8 -*-
"""Release notes: one ordered mapping from version to English note lines.

The English source text is stored here only; it is never translated at
import time. The display layer passes each line through ``_()`` when
rendering, so the notes follow the active language and stay static msgids
that can be translated. The lines describe real, shipped changes only.
"""

RELEASE_NOTES = {
    "0.1.0": [
        "Unified CLI and GUI packages built on the shared core.",
        "Nine protocol decoders, measurement, and .sr/.bin file support.",
    ],
    "0.2.0": [
        "Internationalization: English, Simplified Chinese, Traditional Chinese.",
        "First-run language picker in the GUI and the CLI.",
        "Runtime language switching without restarting.",
    ],
    "0.3.0": [
        "A release-notes prompt shows what changed after an update.",
    ],
    "0.4.0": [
        "Hardware abstraction layer: one uniform backend interface for every real development board.",
        "The CH32 board is the first backend; baud rates, channel count, byte mode, sample rate, and troubleshooting text all come from its declared capabilities.",
        "New device configuration entry in the CLI and the GUI.",
    ],
    "0.5.0": [
        "Ten new protocol decoders: DHT11, 1-Wire, SWD, Modbus RTU, Wiegand, HD44780, Sony SIRC, DS1302, Manchester, and NMEA 0183.",
        "Continuous capture mode in the GUI with a rolling waveform, alongside the existing one-shot capture.",
        "Extended firmware signal generator: PWM, burst, and forced high/low commands, driven from the new GUI signal panel.",
        "First-run onboarding wizard and a re-openable Quick Start Guide in the GUI and the CLI.",
    ],
}
