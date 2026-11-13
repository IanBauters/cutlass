# Cutlass — project summary

_Snapshot: 2026-11-13. A web app that turns G-code into Cricut cut paths,
previews them, and talks to an Explore 5 over Bluetooth._

Repo: `IanBauters/cutlass` · Live app: GitHub Pages (`index.html` at root),
open in **Chrome/Edge** (Web Bluetooth needs a top-level HTTPS page).

---

## 1. What we built (and it works)

- **Translator** — G-code → cut geometry, fully in the browser.
  `G0/G1` moves, `G2/G3` arcs, `G20/21` units, `G90/91` absolute/relative,
  `M3/M5` + `Z` for tool up/down, `F` feed. Live SVG preview, optional
  drag-knife corner compensation, SVG/path export. Mirrored by a tested Python
  reference under `core/` (10 passing tests).
- **Transport** — a confirmed, two-way Web Bluetooth link to the machine:
  connect, enumerate GATT, auto-select the data pipe, send/receive framed
  messages, with a log and a heartbeat.
- **Documentation** — `PROTOCOL.md` (the reverse-engineered link) and
  `README.md`.

## 2. Results from the live machine (`Cricut-A2D7`)

**GATT — the real pipe (ISSC / Microchip Transparent UART):**

| Role | UUID |
|------|------|
| Service | `49535343-fe7d-4ae5-8fa9-9fafd205e455` |
| Write (host → machine) | `49535343-8841-43f4-a8d4-ecbe34729bb3` (writeNR) |
| Notify (machine → host) | `49535343-1e4d-4bd9-ba61-23c647249616` |
| Control (not data) | `49535343-6daa-4d02-abf6-19569aca69fe` |

Also present but not carrying the traffic: a dedicated `00000100-…` service, an
OTA-style `00010203-…` service, standard Device Info, and `$$$`/`---` keepalive
chatter from the radio module.

**Status handshake — confirmed live from the browser:**

```
host → machine   02 01 05 0e 13 92 0d 01 00
machine → host   02 01 05 0e 13 9a 0d 01 00
```

A web page we wrote drove a command to the Cricut and got the correct answer —
no Design Space in the loop. Seen 118× each way across the captures.

**Frame shape:** every frame starts `02`, ends `00`, and carries a 2-byte
sequence that the reply echoes. There's a second plaintext channel (`02 03`)
whose replies are themselves encrypted.

**Geometry = encrypted.** The frames carrying cut data are obscured. Two fixed
16-byte blocks recur identically **across two separate sessions** — the
signature of a static-key, ECB-style block cipher.

## 3. Understanding the encryption

Cricut encrypts cut data with a **symmetric block cipher** (almost certainly
AES): one secret key both locks and unlocks, working on 16-byte blocks.

They use **ECB mode** — each 16-byte block is encrypted on its own, with no
randomness mixed in. So the *same* 16 bytes of input always give the *same* 16
bytes of output. That's exactly what we saw, and the fact that identical blocks
appear across different sessions tells us two things:

- the key is **static** — the same every time, embedded in Design Space;
- the scheme is **weak in one specific way** — it leaks the *structure* of the
  data (ECB is the mode famous for not hiding patterns).

The nuance that matters: leaking structure is **not** the same as being
readable. Seeing that blocks repeat is a world away from decrypting them or
forging valid encrypted frames. For either, you need the key — and an AES key
can't be derived by staring at ciphertext.

## 4. Where it stands

Everything **except the key** is open: the transport, the framing, the status
handshake — all mapped and reproducible. The one thing between "send status"
and "send a cut" is that the geometry must be encrypted with that static key
before the machine accepts it.

That key lives inside Design Space. Recovering it and building the
encrypt-the-geometry step is a **circumvention of the device's protection**, and
is deliberately **out of scope** for this project. This document does not cover
how to obtain or apply it.

## 5. Next steps (the legitimate ones)

- **Cut via the official software, automated.** The route that actually cuts
  *without* touching the key: a small local helper takes the SVG Cutlass
  produces, imports it into Design Space, and triggers "Make It" through macOS
  UI automation. Design Space does the encryption and Bluetooth itself, used the
  normal way — just driven for you. Not pure-browser (Design Space must be
  installed and running), but it ends with vinyl getting cut.
- **Sharpen the translator** (useful regardless of how cutting happens):
  Bézier (`C`) passthrough instead of pre-tessellation, a round-trip SVG check
  to compare output against the source, batch/multi-file, UI polish.
- **Extend the safe protocol surface** — more read-only status queries drawn
  from the captures, exposed as buttons; nothing that moves the machine.

## 6. Repo contents

```
index.html     the app (served by GitHub Pages)
README.md      overview + routes to cutting
PROTOCOL.md    reverse-engineered BLE protocol notes
SUMMARY.md     this file
examples/      sample .gcode
core/          tested Python reference translator (not needed to run the app)
```
