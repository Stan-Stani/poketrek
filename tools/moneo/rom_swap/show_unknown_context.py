#!/usr/bin/env python3
"""For each top-N unknown codepoint, print:
  - cp, occurrence count
  - LIS bracket + the constrained Unicode candidate set
  - up to N sentences from the corpus where it appears, with the cp
    marked as <<>> for visibility
  - path to the rendered atlas glyph

Goal: a Korean reader can decide each unknown's syllable from
context + glyph shape + collation constraint in seconds.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROM_PATH = Path(__file__).resolve().parent / "leafgreen_J-K_2024.gba"
GBA_BASE = 0x08000000
ATLAS1_BASE = 0x08f18800
KNOWN_MAP = Path(__file__).resolve().parent / "codepoint_map.json"
CORPUS = Path(__file__).resolve().parents[1] / "corpus.ko.2024.json"
UNKNOWNS = Path(__file__).resolve().parents[1] / "codepoint_unknowns_2024.json"

HANGUL_LO = 0xAC00
HANGUL_HI = 0xD7A3


def lis_by_uni(anchors):
    n = len(anchors)
    if n == 0: return []
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if anchors[j][2] < anchors[i][2] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    end = max(range(n), key=lambda i: dp[i])
    seq = []
    while end != -1:
        seq.append(anchors[end])
        end = prev[end]
    return list(reversed(seq))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=80,
                    help="how many top-frequency unknowns to inspect")
    ap.add_argument("--per-cp", type=int, default=8,
                    help="max example sentences per cp")
    ap.add_argument("--max-bracket", type=int, default=999,
                    help="skip cps whose candidate window is wider than this")
    ap.add_argument("--out", default="/tmp/poketrek_trace/decode_by_context.txt")
    args = ap.parse_args()

    raw = json.load(open(KNOWN_MAP))
    corpus = json.load(open(CORPUS))
    unks = json.load(open(UNKNOWNS))["unknowns"]

    anchors = sorted([(int(k, 16), v, ord(v)) for k, v in raw.items()])
    lis = lis_by_uni(anchors)

    def find_brackets(cp):
        prev_a, next_a = None, None
        for a in lis:
            if a[0] < cp:
                prev_a = a
            elif a[0] > cp and next_a is None:
                next_a = a; break
        lo = (prev_a[2] + 1) if prev_a else HANGUL_LO
        hi = (next_a[2] - 1) if next_a else HANGUL_HI
        return prev_a, next_a, lo, hi

    out = open(args.out, "w")
    n_with_brackets = 0
    n_skipped_wide = 0

    for u in unks[:args.top]:
        cp_hex = u["codepoint"][2:]
        cp = int(cp_hex, 16)
        if cp_hex in raw:
            continue
        prev_a, next_a, lo_uni, hi_uni = find_brackets(cp)
        bracket_size = hi_uni - lo_uni + 1
        if bracket_size > args.max_bracket:
            n_skipped_wide += 1
            continue
        n_with_brackets += 1
        cands_chars = [chr(u_) for u_ in range(lo_uni, hi_uni + 1)]
        out.write("=" * 72 + "\n")
        out.write(f"cp 0x{cp_hex}  occurrences={u['occurrences']}\n")
        if prev_a:
            out.write(f"  prev anchor: 0x{prev_a[0]:04X}={prev_a[1]} "
                      f"(U+{prev_a[2]:04X})\n")
        if next_a:
            out.write(f"  next anchor: 0x{next_a[0]:04X}={next_a[1]} "
                      f"(U+{next_a[2]:04X})\n")
        out.write(f"  candidates ({bracket_size}): "
                  f"{''.join(cands_chars[:60])}"
                  f"{'...' if len(cands_chars) > 60 else ''}\n")

        # Example sentences containing this cp
        marker = f"[{cp_hex}]"
        n_examples = 0
        for r in corpus["records"]:
            if marker in r["text"]:
                snippet = r["text"]
                # Highlight the cp as <<>>
                hi = snippet.replace(marker, f"《{marker}》")
                # Trim each line to ~120 chars
                lines = [ln[:140] for ln in hi.split("\n")]
                snippet = "\n      ".join(lines)
                out.write(f"  rec {r['id']:5d} (0x{r['offset']:06X}): "
                          f"{snippet}\n")
                n_examples += 1
                if n_examples >= args.per_cp:
                    break

    out.close()
    print(f"wrote {args.out}")
    print(f"  unknowns considered: {args.top}")
    print(f"  emitted with brackets: {n_with_brackets}")
    print(f"  skipped (window > {args.max_bracket}): {n_skipped_wide}")


if __name__ == "__main__":
    main()
