# Attribution

Project Rocky is a derivative work built on top of two upstream projects by
**Dorian Todd** (GitHub: [`dorianborian`](https://github.com/dorianborian)).
Both upstream projects are licensed under Apache License 2.0.

## Upstream: Sesame Robot

- **Source:** https://github.com/dorianborian/sesame-robot
- **Author:** Dorian Todd
- **License:** Apache License 2.0

The following directories/files in this repository are either unchanged or
lightly modified from Sesame Robot. Copyright remains with Dorian Todd;
modifications in this fork are © 2026 Dhruv Manral and are also distributed
under Apache 2.0.

- `hardware/` — CAD, STL, PCB design files
- `firmware/` — ESP32 firmware (Arduino / C++). Modifications:
  - ESP32-S3 Mini pin remap for the Rocky build (see
    `firmware/sesame-firmware-main.ino` lines 42–44 and `servoPins[]`)
  - GPIO 3 strapping-pin fix: servo R4 moved from GPIO 3 to GPIO 7
- `firmware/captive-portal.h` — on-device web control UI
- `docs/`, `software/` — build guides, animation composer
- The base `README.md`, trimmed and prepended with a fork notice
- `LICENSE` — unchanged

## Upstream: Sesame Companion App

- **Source:** https://github.com/dorianborian/sesame-companion-app
- **Author:** Dorian Todd
- **License:** Apache License 2.0

We do not vendor code from this repo, but the **talking-face viseme animation**
in `rocky-agent/face_animator.py` is conceptually derived from
`sesame_companion.py`'s `_animate_with_audio_monitoring` /
`_animate_time_based` functions. The toggle pattern (`talk_<face>` when the
RMS is above threshold, `<face>` when below) is Dorian's; our implementation
computes the RMS timeline directly from the synthesized PCM buffer (instead
of reading it back from the system mic) so the toggles can be scheduled
ahead of time and stay perfectly in sync with playback.

## New work in this fork

Unless noted above, the following directories are original to Project Rocky
and © 2026 Dhruv Manral, Apache 2.0:

- `rocky-agent/` — voice agent + web control panel
- `rocky-cli/` — command-line client
- `WIRING-PLAN.md`, `WIRING-REVIEW.md`, `PARTS-INDIA.md` — build notes
  specific to the Rocky (ESP32-S3 Mini, India sourcing) variant
