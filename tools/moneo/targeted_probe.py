#!/usr/bin/env python3
"""Targeted brute-force: ROM (page=3, idx=92) -> fingerprint '6b7baa8bd58a7f81' for '상'.

Search all reasonable 2bpp->4bpp transforms + sub-tile permutations + palette
remappings until one hits the known fingerprint, then validate on the other 44
ko_charmap entries via ksx1001-charmap.json's (page,idx) lookup.
"""
import hashlib, json, itertools, sys
from pathlib import Path

ROM = Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes()
KO  = json.loads(Path("app/src/main/assets/moneo/ko_charmap.json").read_text())
KS  = json.loads(Path(".moneo-artifacts/ksx1001-charmap.json").read_text())

FONT_BASE = 0x780000
PAGE_SZ   = 0x4000

# char -> fingerprint (the known map)
char_to_fp = {}
for fp, ch in KO.items():
    char_to_fp.setdefault(ch.strip(), fp)

# Build (page,idx) -> fp for chars that exist in both
ground = []  # list of (page, idx, fp, char)
for key, ch in KS.items():
    if ch in char_to_fp:
        p, i = key.split(",")
        ground.append((int(p[1:]), int(i), char_to_fp[ch], ch))
ground = list({(p,i,fp):(p,i,fp,c) for p,i,fp,c in ground}.values())
print(f"Ground truth pairs: {len(ground)}")
for g in ground[:8]: print(" ", g)

# ---- ROM glyph fetch (pokefirered 16x32 grid, 16x16 glyphs) -----------------
def get_subtiles(page, idx):
    """Return [TL, TR, BL, BR] each 16 bytes 2bpp."""
    base = FONT_BASE + (page-1)*PAGE_SZ
    row, col = idx // 16, idx % 16
    off = base + 0x200*row + 0x20*col
    return [
        bytes(ROM[off:off+16]),
        bytes(ROM[off+16:off+32]),
        bytes(ROM[off+256:off+272]),
        bytes(ROM[off+272:off+288]),
    ]

# ---- pixel extraction variants ----
# Each row of 8 px in 2bpp = 2 bytes. Variants over: byte order (swap?), bit order.
def extract_pixels(src16, byte_swap, bit_msb_first):
    """Return list[64] of 0..3 in row-major (8 rows × 8 px)."""
    out = []
    for row in range(8):
        if byte_swap:
            b0 = src16[row*2+1]; b1 = src16[row*2+0]
        else:
            b0 = src16[row*2+0]; b1 = src16[row*2+1]
        for b in (b0, b1):
            if bit_msb_first:
                out += [(b>>6)&3,(b>>4)&3,(b>>2)&3,(b>>0)&3]
            else:
                out += [(b>>0)&3,(b>>2)&3,(b>>4)&3,(b>>6)&3]
    return out

def pack_4bpp(pixels, palette, low_nibble_left):
    """pixels: list[64] of 0..3 -> 32 bytes 4bpp."""
    mapped = [palette[p] for p in pixels]
    out = bytearray(32)
    for row in range(8):
        for i in range(4):
            a = mapped[row*8 + 2*i]      # left pixel
            b = mapped[row*8 + 2*i + 1]  # right pixel
            if low_nibble_left:
                out[row*4+i] = (a & 0xF) | ((b & 0xF) << 4)
            else:
                out[row*4+i] = ((a & 0xF) << 4) | (b & 0xF)
    return bytes(out)

# Sub-tile orderings: standard is (TL,TR,BL,BR). Try all 24 perms.
SUBTILE_PERMS = list(itertools.permutations(range(4)))

# Palettes to try. Each maps 2bpp value (0..3) -> 4bpp value (0..15).
# Common patterns: identity, swap-1-2, with shadow at 2 etc.
def gen_palettes():
    pals = []
    # Identity-style (small index range)
    for perm in itertools.permutations(range(4)):
        pals.append(list(perm))
    # Common pokemon text palettes (with values outside 0..3)
    common = [
        [0,1,2,3],
        [0,2,1,3],
        [0,15,14,13],
        [0,1,3,2],
        [0,2,3,1],
        [0,3,2,1],
        [0,3,1,2],
        # Pokefirered-style (transparent, white, shadow=8, dark=15):
        [0,1,8,15],
        [0,8,1,15],
        [0,15,8,1],
        [0,2,15,1],
        [0,1,15,2],
    ]
    for c in common:
        if c not in pals:
            pals.append(c)
    return pals

PALETTES = gen_palettes()
print(f"Trying {len(PALETTES)} palettes × 24 subtile perms × 2 byteswap × 2 bitorder × 2 nibble = {len(PALETTES)*24*8} configs per glyph")

def fp_of(parts4_32bytes):
    return hashlib.sha256(b"".join(parts4_32bytes)).hexdigest()[:16]

# Target: page=3, idx=92, fp='6b7baa8bd58a7f81' (상)
TARGET_PAGE, TARGET_IDX, TARGET_FP, TARGET_CH = 3, 92, char_to_fp['상'], '상'
src_subs = get_subtiles(TARGET_PAGE, TARGET_IDX)
if all(b==0 for t in src_subs for b in t):
    print(f"!!! ROM at F{TARGET_PAGE},{TARGET_IDX} is BLANK"); sys.exit(2)

print(f"\nSearching for fingerprint of {TARGET_CH!r} = {TARGET_FP} at F{TARGET_PAGE},{TARGET_IDX}")
hits = []
for byte_swap in (False, True):
    for bit_msb in (False, True):
        for low_nib_left in (False, True):
            for pal in PALETTES:
                # extract pixels per subtile
                px_per_sub = [extract_pixels(t, byte_swap, bit_msb) for t in src_subs]
                packed = [pack_4bpp(px, pal, low_nib_left) for px in px_per_sub]
                # Try each sub-tile permutation
                for perm in SUBTILE_PERMS:
                    out = [packed[perm[0]], packed[perm[1]], packed[perm[2]], packed[perm[3]]]
                    if fp_of(out) == TARGET_FP:
                        hits.append((byte_swap, bit_msb, low_nib_left, pal, perm))

print(f"Hits: {len(hits)}")
for h in hits[:5]:
    print(" ", h)

if not hits:
    print("\nNo configuration matched. The transform must involve more than\n"
          "  byteswap × bitorder × nibble-half × 4-element palette × subtile-perm.\n"
          "Path 1 fully exhausted statically; switch to GDB Path 2.")
    sys.exit(1)

# Validate on other ground-truth pairs
print("\n--- Validating winning config(s) on all ground truth ---")
def render(page, idx, byte_swap, bit_msb, low_nib_left, pal, perm):
    subs = get_subtiles(page, idx)
    if all(b==0 for t in subs for b in t): return None
    px = [extract_pixels(t, byte_swap, bit_msb) for t in subs]
    pk = [pack_4bpp(p, pal, low_nib_left) for p in px]
    return fp_of([pk[perm[0]], pk[perm[1]], pk[perm[2]], pk[perm[3]]])

best = None
for cfg in hits:
    correct = 0; tested = 0
    for p,i,fp_exp,ch in ground:
        fp_got = render(p, i, *cfg)
        tested += 1
        if fp_got == fp_exp: correct += 1
    print(f"  {cfg} : {correct}/{tested}")
    if best is None or correct > best[1]:
        best = (cfg, correct, tested)

print(f"\nBest config: {best[0]} → {best[1]}/{best[2]} ground truth pairs match")
Path(".moneo-artifacts/transform-config.json").write_text(json.dumps({
    "config": {
        "byte_swap": best[0][0], "bit_msb_first": best[0][1],
        "low_nibble_left": best[0][2], "palette": best[0][3], "subtile_perm": list(best[0][4]),
    },
    "validation": {"correct": best[1], "total": best[2]},
}, indent=2))
print("Saved .moneo-artifacts/transform-config.json")
