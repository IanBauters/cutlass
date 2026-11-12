# Cutlass — Explore 5 BLE protocol notes

What's been observed of the Cricut Explore 5 (`Cricut-A2D7`) Bluetooth link,
from two PacketLogger captures plus a live browser session. Confidence is
marked per point: **solid** (seen consistently and reproduced live) or
**provisional** (inferred, not fully pinned).

## Transport — solid

Serial-over-BLE on the ISSC / Microchip Transparent UART service:

| Role | UUID | Properties |
|------|------|------------|
| Service | `49535343-fe7d-4ae5-8fa9-9fafd205e455` | — |
| Write (host → machine) | `49535343-8841-43f4-a8d4-ecbe34729bb3` | write, writeNR |
| Notify (machine → host) | `49535343-1e4d-4bd9-ba61-23c647249616` | notify |
| Control (not the data pipe) | `49535343-6daa-4d02-abf6-19569aca69fe` | write, read |

The chip also emits `$$$` / `---\r\n` on its own timer — Microchip module
housekeeping, not Cricut traffic.

The machine also exposes a dedicated service `00000100-…` (write `…0101`,
notify `…0102`) and an OTA-style service `00010203-…`, neither of which carried
the application traffic in these captures.

## Frame shape — solid at the edges, provisional inside

Every frame starts `02` and ends `00`. It carries a 2-byte sequence that a
reply echoes from its request. Beyond that the internal field layout isn't
fully resolved; the second byte is `01` for the status channel, `03` for the
control channel, and varies on the encrypted data frames.

```
02 | b | seq_hi seq_lo | … | 00
```

## Status handshake — solid

The one fully-decoded, plaintext exchange. Seen 118×/118× across the captures
and reproduced live from the browser:

```
host → machine   02 01 <seq> .. 92 0d 01 00
machine → host   02 01 <seq> .. 9a 0d 01 00
```

A keepalive / "are you there". Harmless to send; it moves nothing. This is what
Cutlass's **Send status poll** and **Heartbeat** use.

## Control channel `02 03` — provisional

```
host → machine   02 03 06 <n> 01 00          (short request)
machine → host   02 03 05 <n> <16 bytes> 00   (16-byte reply, encrypted)
```

Looks like a block read: the host asks, the machine returns a 16-byte block.
The returned block is not readable (see below), so this channel is noted but not
replayed by the app.

## Geometry payloads — encrypted — solid

The frames that carry cut data are obscured and were **not** decoded. Evidence
it's a static-key, ECB-style block cipher:

- Two fixed 16-byte blocks (`4561d543…`, `ec36fa68…`) recur hundreds of times,
  byte-for-byte, **and are identical across two separate connection sessions**.
  A per-session key would make the same plaintext encrypt differently each time;
  it doesn't.
- Repetition at a clean 16-byte boundary is the ECB signature.

Driving geometry therefore needs that static key, which lives inside Cricut's
software. Recovering it is the circumvention boundary and is out of scope for
this project (see README "Routes to actual cutting").

## Summary

Solved: the transport, the frame markers + sequence, and the plaintext status
handshake — enough to hold a live, confirmed, two-way link to the machine from
a web page. Not solved, by design: the encrypted geometry.
