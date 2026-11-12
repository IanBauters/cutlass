# Cutlass

Drive a Cricut with your own G-code, without Design Space.

Cutlass is a browser app that turns G-code into the cut geometry a Cricut
needs, previews it, and (experimentally) connects to the machine over
Bluetooth. It runs entirely client-side — no install, no account, no Python.

**Live app:** enable GitHub Pages on this repo (Settings → Pages → deploy from
`main`, root) and open `https://<you>.github.io/cutlass/` in **Chrome or Edge**.
Web Bluetooth needs a top-level HTTPS page, which Pages provides; it does **not**
work in Safari or inside an embedded frame.

## What works today

- **G-code → cut paths.** `G0/G1` moves, `G2/G3` arcs, `G20/21` units,
  `G90/91` absolute/relative, `M3/M5` and `Z` for tool up/down, `F` feed.
  Comments and unknown words are ignored, so real Inkscape/LightBurn files load.
- **Live SVG preview** of the cut, with optional drag-knife corner compensation.
- **Export** the preview SVG or the path data (`M`/`L`/`Z`, absolute,
  space-separated — the dialect a driver-reuse backend accepts).
- **Machine panel.** Connect to the machine over Web Bluetooth, enumerate its
  GATT, and exchange the plain-text status frames. **Confirmed working on a
  Cricut Explore 5** (device `Cricut-A2D7`): the status poll round-trips live.

## Confirmed protocol (Explore 5)

- **Transport:** ISSC/Microchip Transparent UART service
  `49535343-fe7d-4ae5-8fa9-9fafd205e455`
  - write (host→machine): `49535343-8841-43f4-a8d4-ecbe34729bb3` (writeNR)
  - notify (machine→host): `49535343-1e4d-4bd9-ba61-23c647249616`
  - (`…6daa…` on the same service is a control characteristic, not the data pipe.)
- **Frame:** `02 01 · seq(2 bytes) · 13 · payload · 00`. A request and its reply
  share the seq value.
- **Status handshake (plain text):** host sends payload `92 0d 01`, machine
  replies `9a 0d 01`. Verified over BLE from the browser.

## What doesn't work yet

Sending an actual cut. The status/housekeeping frames are plain text, but the
**cut geometry is encrypted with a static key** — repeated ciphertext blocks
appear identically across two separate capture sessions, the signature of a
fixed-key, ECB-style scheme rather than a per-session handshake. The link and
the plain-text protocol are solved; driving geometry needs that key, which is
the circumvention boundary (see below).

## Layout

```
index.html      the app — this is what GitHub Pages serves
examples/       sample .gcode files
core/           tested reference implementation of the translator (Python);
                not needed to run the app, kept for clarity and testing
```

The `core/` Python package mirrors the translator logic in the page and has a
test suite (`python core/tests/test_gcut.py`, no dependencies). The app is the
product; `core/` is the spec.

## Status & notes

- Knife-offset compensation is the standard hobby-cutter approximation — tune
  the offset against real cuts; `0` disables it.
- Reverse engineering for interoperability with your own device. No Cricut code
  or keys are included. Not affiliated with Cricut, Inc.
- No licence yet — add one before sharing if you intend others to reuse it.

## Routes to actual cutting

Two honest paths, now that the transport is solved:

1. **Driver-reuse (no key-breaking).** Export paths from this app and let
   Cricut's own installed software do the encryption, as the `slicebug` project
   does. Sidesteps the key entirely; needs a desktop helper, not just the
   browser.
2. **Direct, in the browser.** Would require supplying the static key so the
   page can encrypt geometry frames itself. That key sits inside Cricut's
   software; recovering it is the circumvention step, and is out of scope for
   this repo.
