# -*- coding: utf-8 -*-
"""Shared quick start guide content for the onboarding wizard and the
re-openable guide in the GUI and the CLI.

Every step is a static msgid pair (title, body lines); the front-ends
pass each string through ``_()`` at display time so the guide follows the
active language. Real port/device names and data stay English. The body
lines deliberately avoid quoting other UI labels, because those labels
are translated independently.
"""

GUIDE_STEPS = [
    (
        "Connect the device",
        [
            "Plug the board into a USB port and check the two USB connectors on the board.",
            "The data port (USB-FS) carries the capture stream; the debug port belongs to the WCH-Link debugger and is only for flashing and debugging.",
            "Capture, measurement, and decoding only work on the data port; a cable in the debug port is not enough.",
        ],
    ),
    (
        "Select the port",
        [
            "In the GUI use the port list and refresh it; in the CLI choose the capture entry or the signal generator and pick the port number from the detected list.",
            "The data port appears as a new serial port when the cable is connected; if no port appears, check the cable and the USB driver.",
            "Make sure no other program (a serial monitor, another capture run) holds the port before connecting.",
        ],
    ),
    (
        "Capture",
        [
            "One-shot capture: choose the sample point count and start the capture; the waveform appears when the transfer completes.",
            "Continuous capture: use the continuous start/stop controls to stream a rolling window that refreshes the waveform every 100-200 ms; stopping releases the port.",
            "One-shot and continuous capture share the data port and cannot run at the same time.",
        ],
    ),
    (
        "Waveform, decode, and measurement",
        [
            "The waveform shows channels D0-D7 at the backend sample rate (10 kHz for the CH32 board).",
            "The decode tab lists the registered protocol decoders; pick one and run it on the captured data.",
            "The measurement tab reports frequency, period, pulse widths, duty, and edge counts per channel.",
        ],
    ),
    (
        "Signal generator",
        [
            "The signal-generator tab drives the real firmware output on PA15 over the signal connection: software UART, square wave, PWM (frequency and duty), burst (frequency and pulse count), and forced high/low.",
            "Loop A15 back to D0 with a jumper wire to capture and decode the generated signal.",
            "Frequency is limited to 1-5000 Hz and duty to 1-99 percent; keep the inputs inside these limits.",
        ],
    ),
]
