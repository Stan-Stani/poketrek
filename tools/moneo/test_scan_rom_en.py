#!/usr/bin/env python3
"""Golden-string tests for the EN ROM decoder.

Lightweight — no ROM dependency. Build a few bytes in-memory and assert
that `read_message` and `decode_string` produce the right text. Run with
`python3 -m unittest tools/moneo/test_scan_rom_en.py` or invoke
directly.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rom_config_en import EN_CHARMAP, EN_END_MARKER  # noqa: E402
import build_name_table_decks_en as nt  # noqa: E402
import scan_rom_en as scanner  # noqa: E402


INV = {v: k for k, v in EN_CHARMAP.items()}


def encode(s: str) -> bytes:
    """Encode a printable ASCII string using the Gen 3 EN charset.

    Useful only for known characters in our charmap — fixture text.
    """
    return bytes(INV[c] for c in s)


class NameTableDecoderTest(unittest.TestCase):
    def test_decode_pound(self):
        buf = bytearray(16)
        body = encode("POUND") + bytes([EN_END_MARKER])
        buf[0:len(body)] = body
        self.assertEqual("POUND", nt.decode_string(bytes(buf), 0, 13))

    def test_titlecase_keeps_pokemon_glyph(self):
        # No glyph in the fixture — just verify titlecase mechanics.
        self.assertEqual("Master Ball", nt.titlecase("MASTER BALL"))
        self.assertEqual("Doubleslap", nt.titlecase("DOUBLESLAP"))

    def test_decode_stops_at_terminator(self):
        body = encode("HI") + bytes([EN_END_MARKER]) + encode("LATER")
        self.assertEqual("HI", nt.decode_string(body, 0, len(body)))


class ScanRomReadMessageTest(unittest.TestCase):
    def test_simple_message(self):
        body = encode("Hello world") + bytes([EN_END_MARKER])
        msg = scanner.read_message(body, 0, hard_end=len(body))
        self.assertIsNotNone(msg)
        self.assertEqual("Hello world", msg["text"])
        self.assertEqual(10, msg["letters"])  # 10 letters, 1 space (space is non-letter)

    def test_message_with_newline(self):
        body = encode("Line1") + bytes([0xFE]) + encode("Line2") + bytes([EN_END_MARKER])
        msg = scanner.read_message(body, 0, hard_end=len(body))
        self.assertIsNotNone(msg)
        self.assertEqual("Line1\nLine2", msg["text"])

    def test_rejects_random_bytes(self):
        body = bytes(b"\xAA\xBB\xCD\xEF\x12\x34")  # mostly junk
        msg = scanner.read_message(body, 0, hard_end=len(body))
        # Not enough consecutive letters → reject as a message
        self.assertIsNone(msg)

    def test_two_byte_control_consumes_one_arg(self):
        # 0xFD <arg> is a buffer-variable insertion; should emit a placeholder
        # and continue rather than crashing.
        body = encode("Hi") + bytes([0xFD, 0x01]) + encode("there") + bytes([EN_END_MARKER])
        msg = scanner.read_message(body, 0, hard_end=len(body))
        self.assertIsNotNone(msg)
        self.assertIn("Hi", msg["text"])
        self.assertIn("there", msg["text"])
        self.assertIn("{var:01}", msg["text"])


if __name__ == "__main__":
    unittest.main()
