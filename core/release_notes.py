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
    "0.6.2": [
        "Multi-rate capture: the CH32 board records at 10 kHz, 100 kHz, 500 kHz, or 1 MHz through the USB3 High-Speed data port.",
        "Dual capture modes: realtime streaming plus a 712704-byte burst buffer with a parsed header upload.",
        "Every time axis and every saved .sr file now carries the sample rate that was actually recorded.",
        "Sample-rate and capture-mode selectors in the GUI toolbar and the CLI settings menu, always driven by the current backend capabilities.",
        "Saved rate and mode choices are validated before every capture and fall back to the backend defaults when unsupported or stale.",
        "Live analysis, live measurement, and the GUI continuous capture follow the selected sample rate.",
        "French and German language packs: five languages with runtime switching.",
        "Settings dialog for language and theme, with a reorganized toolbar.",
        "Waveform zoom controls and multi-file import management.",
        "Windows Setup installer and a cross-platform CLI install script.",
    ],
    "0.6.3": [
        "The first-run wizard now includes an application-language picker, and the Quick Start Guide opens from the settings dialog.",
        "The right-side Decode, Measure, and Signal panel can be hidden, and the waveform expands to use the freed space.",
        "Measurement detail values now show their units: Hz, ms, and percent.",
        "The toolbars are reorganized into two rows with clearer drop-down boxes; the overflow menu opens instantly and stays open while you work.",
        "The install-scope question is reworded for clarity, and the finished page shows a centered brand block.",
    ],
    "0.6.4": [
        "New Pattern Playback panel in the GUI: edit a six-channel level sequence and capture the device's own output.",
        "Pattern editor with a clickable grid, adjustable length up to 8000 cells, a clear control, and built-in protocol templates.",
        "Self-contained loop: the device generates the pattern, captures it on the input channels, and decodes it with the real protocol decoders.",
        "The Manchester decoder scans several start transitions, so a spurious head transition no longer breaks alignment.",
        "The playback capture window now covers one full DMA block, keeping the complete waveform even when the trigger lands near a block boundary.",
    ],
}
