#!/usr/bin/env python3
"""User-supplied labels for the final 9 remaining unknown codepoints.

Stan inspected the rendered atlas glyphs alongside corpus contexts
and identified each syllable directly. All 9 read cleanly in their
sentences:

  0x3F3C = 퀵  ("Quick" item/adverb; contexts:
                "퀵 관해서라면" = "as for Quick",
                "퀵 받았다" / "퀵 주라고" — Quick Claw/Quick Ball
                item transfer dialog,
                "몸이 퀵 딱딱해지기" = "body quickly hardens" —
                Slugma Pokédex)
  0x3F3A = 퀭  ("hollow/sunken"; "주변을 퀭 슬..." = "look around
                with sunken eyes", "구성은 퀭 돌이나" = "composition
                is hollow rock-like")
  0x3FA0 = 튄  ("splashes/pops"; "몸이 튄다 매일 톤의 먹는다" —
                Pokédex body description)
  0x373E = 겪  ("experience/undergo"; "휩 전기 겪 전격파" =
                "experiences thunderwave swept by electricity",
                "낚싯대는 못 겪" = "rod cannot experience")
  0x3786 = 궐  (font-dump record only; pixel-confirmed by user)
  0x3C93 = 씌  ("cover/put on"; "하 씌 어서 잘 부렸었네")
  0x3820 = 뀨  (animal-cry onomatopoeia; "사랑스런 뀨우 하 울어"
                = "lovely 'kyu-u', cries")
  0x3884 = 놨  ("have done/placed"; "조수에게 보내놨단다 받아"
                = "I've sent it to the assistant, take it")
  0x3C6C = 쏟  ("pour out"; "빛을 쏟아" = "pour out light" —
                Pokémon move description)
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAP = HERE / "codepoint_map.json"

LABELS = {
    "3F3C": "퀵",
    "3F3A": "퀭",
    "3FA0": "튄",
    "373E": "겪",
    "3786": "궐",
    "3C93": "씌",
    "3820": "뀨",
    "3884": "놨",
    "3C6C": "쏟",
}


def main():
    raw = json.load(open(MAP))
    before = len(raw)
    added = 0
    for cp_hex, ch in LABELS.items():
        if cp_hex in raw:
            print(f"  CONFLICT in map {cp_hex}: was {raw[cp_hex]!r} -> {ch!r}")
            continue
        raw[cp_hex] = ch
        added += 1
    out_sorted = {k: raw[k] for k in sorted(raw, key=lambda h: int(h, 16))}
    MAP.write_text(json.dumps(out_sorted, indent=2, ensure_ascii=False) + "\n")
    print(f"codepoint_map: {before} -> {len(out_sorted)} (+{added})")


if __name__ == "__main__":
    main()
