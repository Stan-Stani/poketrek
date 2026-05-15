# Vendored xdelta3 (decode-only subset)

Upstream: <https://github.com/jmacd/xdelta>
Vendored commit: `7508fd2a823443b1f0173ca361620f21d62a7d37`
License: Apache-2.0 (see `LICENSE`) — © Joshua MacDonald.

## Why this is here

Moneo applies the 2024 Korean fan-translation `.xdelta` patch to a
user-supplied Japanese LeafGreen ROM **on-device**, so non-developers
don't need Python, a terminal, or a separate patcher app. The native
side calls `xd3_decode_memory` via JNI (`NativeEmulator.applyXdelta`).

## What was copied (and what wasn't)

Only the files `xdelta3.c` includes for an **in-memory decode** build are
vendored:

```
xdelta3.h  xdelta3.c  xdelta3-internal.h  xdelta3-list.h
xdelta3-hash.h  xdelta3-cfgs.h  xdelta3-decode.h
```

Deliberately **omitted** because the build config gates their `#include`
out (`SECONDARY_*=0`, `XD3_MAIN=0`, `REGRESSION_TEST=0`, and
`NOT_MAIN`/`PYTHON_MODULE`/`SWIG_MODULE` undefined):

- `xdelta3-second.h`, `xdelta3-djw.h`, `xdelta3-fgk.h`, `xdelta3-lzma.h`
  — secondary compressors. **The 2024 LeafGreen patch uses no secondary
  compression** (VCDIFF header `Hdr_Indicator = 0x04`, `VCD_SECONDARY`
  bit clear), verified byte-for-byte against `leafgreen_J-K_2024.gba`
  (CRC `0x4A38A8CB`).
- `xdelta3-main.h` (CLI), `xdelta3-test.h` (regression suite),
  `xdelta3-blkcache.h`, `xdelta3-merge.h` — frontend/merge only.

**If the fan-translation team ever re-releases the patch built with a
secondary compressor** (e.g. `xdelta3 -S lzma`), decoding will fail with
`XD3_INVALID_INPUT`. Recovery is: re-vendor the matching secondary
header(s) and flip the corresponding `SECONDARY_*` define in
`app/src/main/cpp/CMakeLists.txt` (LZMA additionally needs an external
liblzma; DJW/FGK are self-contained).

## Build config

Compiled into `libpoketrek.so` as the static `xdelta3` target in
`app/src/main/cpp/CMakeLists.txt`. The defines there match the
host-side proof that validated this exact patch. Both shipped ABIs
(`arm64-v8a`, `x86_64`) are LP64, so the hardcoded `SIZEOF_*` values
hold.

Do not reformat or hand-edit these sources — re-vendor from upstream
instead so the provenance commit above stays meaningful.
