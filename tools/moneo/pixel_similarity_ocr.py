#!/usr/bin/env python3
"""Build ROM -> Korean char mapping using pixel similarity against a reference font.

Strategy:
1. Render each ROM glyph (16×16) using the render_dialogue formula
2. Render all Korean chars in the game font using system Apple SD Gothic Neo
3. For each ROM glyph, find the best-matching Korean char by pixel similarity
4. Use known-correct mappings to calibrate the similarity threshold
"""
import json
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from pathlib import Path

ROM = bytearray(Path("Pocket Monsters - LeafGreen (Korean).gba").read_bytes())
FONT_BASE = 0x780000
BRIGHTNESS = [0, 80, 160, 255]

def render_rom_glyph(rom_page, idx_byte):
    """Render ROM glyph as 16×16 binary image."""
    off = FONT_BASE + rom_page * 0x2000 + idx_byte * 32
    img = Image.new("L", (16, 16), 0)
    p = img.load()
    for row_half in range(2):
        base = off + row_half * 0x100
        for col_half in range(2):
            tile_off = base + col_half * 0x10
            for row in range(8):
                byte_off = tile_off + row * 2
                if byte_off + 1 >= len(ROM): continue
                for half in range(2):
                    b = ROM[byte_off + (1 - half)]
                    for px in range(4):
                        v = (b >> ((3 - px) * 2)) & 0x3
                        if v: p[col_half*8 + half*4 + px, row_half*8 + row] = 255
    return img

def render_ref_glyph(char, font):
    """Render a Korean char at 16×16 using the reference font."""
    img = Image.new("L", (16, 16), 0)
    draw = ImageDraw.Draw(img)
    # Center the char
    bbox = font.getbbox(char)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = max(0, (16 - w) // 2 - bbox[0])
    y = max(0, (16 - h) // 2 - bbox[1])
    draw.text((x, y), char, fill=255, font=font)
    return img

def img_similarity(a, b):
    """Compute pixel similarity between two 16×16 binary images."""
    arr_a = np.array(a) > 128
    arr_b = np.array(b) > 128
    # Intersection over Union
    intersection = (arr_a & arr_b).sum()
    union = (arr_a | arr_b).sum()
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return float(intersection) / float(union)

# Load reference font
try:
    font = ImageFont.truetype('/System/Library/Fonts/AppleSDGothicNeo.ttc', 12)
except:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/AppleGothic.ttf', 12)

# Chars to identify (ko_charmap + likely game text chars)
target_chars = list('가나다라마바사아자차카타파하거너더러머버서어저처허갈날달랄말발살알잘찰할결넬댈렬멜벨셀엘젤첼헬경녕덩렁멍벙성엉정청헝고노도로모보소오조초코토포호곤논돈론몬본손온존촌콘톤폰혼골놀돌롤몰볼솔올졸촐콜톨폴홀공농동롱몽봉송옹종총콩통퐁홍과놔좌뢰뫄봐솨좌쾌탸')

# Get unique chars
all_target = sorted(set(target_chars))

# Also include the known ko_charmap chars
ko = json.load(open('app/src/main/assets/moneo/ko_charmap.json'))
all_target = sorted(set(all_target) | set(ko.values()) - {'。'})

print(f"Building reference images for {len(all_target)} chars...")
ref_imgs = {}
for ch in all_target:
    try:
        img = render_ref_glyph(ch, font)
        ref_imgs[ch] = img
    except:
        pass

print(f"Reference images built for {len(ref_imgs)} chars")

# Now: for the 13 missing ko_charmap chars, find their ROM positions
# Known from analysis: these positions are from glyph_table where OCR failed
# Let me find them by searching all ROM tokens
raw = json.load(open('.moneo-artifacts/rom-text-ko-raw.json'))
tokens = {}
for rec in raw['records']:
    bs = bytes.fromhex(rec['hex'])
    i = 0
    while i < len(bs):
        b = bs[i]
        if b == 0xFF: break
        if 0xF1 <= b <= 0xF6 and i+1 < len(bs):
            p = b - 0xF0
            idx = bs[i+1]
            tokens[(p, idx)] = tokens.get((p, idx), 0) + 1
            i += 2
        elif b in (0xFC, 0xFD) and i+1 < len(bs): i += 2
        else: i += 1

print(f"\nMatching {len(tokens)} ROM tokens against reference chars...")

# For each ROM token, compute similarity to all reference chars
token_to_char = {}
for (rom_page, idx_byte), cnt in sorted(tokens.items()):
    rom_img = render_rom_glyph(rom_page, idx_byte)
    rom_arr = np.array(rom_img)
    
    if rom_arr.max() == 0:  # blank glyph
        continue
    
    best_char = None
    best_score = 0.0
    
    for ch, ref_img in ref_imgs.items():
        score = img_similarity(rom_img, ref_img)
        if score > best_score:
            best_score = score
            best_char = ch
    
    if best_char and best_score >= 0.3:  # threshold
        token_to_char[(rom_page, idx_byte)] = (best_char, best_score)

print(f"Matched {len(token_to_char)} tokens with score >= 0.3")

# Verify against known correct mappings
print("\nVerification against known correct mappings:")
known = {
    '하': (1, 178),
    '가': (1, 102),
    '나': (1, 91),
    '로': (2, 38),
    '이': (1, 98),
}
for ch, (p, idx) in known.items():
    matched = token_to_char.get((p, idx))
    if matched:
        print(f"  {ch}: matched={matched[0]!r} (score={matched[1]:.3f}) {'✓' if matched[0]==ch else '✗'}")
    else:
        print(f"  {ch}: NO MATCH")

# For the missing ko_charmap chars, find their best position
missing = ['상', '선', '좌', '직', '택', '항', '합', '아', '용', '움', '정', '계']
print("\nBest ROM positions for missing chars:")
for target_ch in missing:
    # Find all tokens where this char is the best match
    matches = [(p, idx, score) for (p,idx), (ch, score) in token_to_char.items() if ch == target_ch]
    matches.sort(key=lambda x: -x[2])
    print(f"  {target_ch!r}: {[(f'({p},{idx})', f'{s:.3f}') for p,idx,s in matches[:3]]}")

# Save the token_to_char mapping
out = {f"F{p},{idx}": (ch, round(float(score), 3)) for (p,idx),(ch,score) in token_to_char.items()}
import json
Path('.moneo-artifacts/pixel-similarity-map.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1)
)
print("\nSaved pixel-similarity-map.json")
