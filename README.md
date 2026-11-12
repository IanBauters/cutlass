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
- **Machine panel (experimental).** Connect to the machine over Web Bluetooth,
  list its GATT services/characteristics, and exchange the plain-text status
  frames seen in packet captures. This confirms the link.

## What doesn't work yet

Sending an actual cut. On the captures so far, the Explore 5's BLE link carries
its cut data encrypted with a **static key** (repeated ciphertext blocks appear
identically across two separate sessions — the signature of a fixed-key,
ECB-style scheme, not a per-session handshake). The plain-text housekeeping
frames go through fine; the encrypted geometry does not, pending that key.

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
