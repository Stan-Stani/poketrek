#!/usr/bin/env python3
"""mGBA GDB-remote-protocol client subset.

mGBA exposes a full GDB remote stub on tcp/2345 with `-g`. This module
implements only the packets needed for Korean text-engine tracing:

  - Read all general registers       :  g
  - Read register #N                 :  p<hex>
  - Read memory                      :  m<hex>,<hex>
  - Write memory                     :  M<hex>,<hex>:<bytes>
  - Set hardware breakpoint          :  Z1,<hex>,<kind>
  - Remove breakpoint                :  z1,<hex>,<kind>
  - Continue                         :  c
  - Step                             :  s
  - Stop reason                      :  ? / handled in async
  - Detach                           :  D
  - Kill                             :  k

GDB serial protocol packet format: $<payload>#<chk2>
Acks: '+' / '-'.
"""
from __future__ import annotations
import socket
import time

class GDBClient:
    def __init__(self, host: str = "localhost", port: int = 2345, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buf = b""
        # mGBA defaults to ack-on; we keep it on (no QStartNoAckMode).

    # ---- connection ---------------------------------------------------------
    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self) -> None:
        if self.sock:
            try: self.sock.close()
            finally: self.sock = None

    # ---- low-level packet I/O ----------------------------------------------
    @staticmethod
    def _checksum(payload: bytes) -> bytes:
        s = sum(payload) & 0xFF
        return f"{s:02x}".encode()

    def _send_raw(self, data: bytes) -> None:
        assert self.sock is not None
        self.sock.sendall(data)

    def _recv_until(self, terminator: bytes, max_bytes: int = 1 << 20) -> bytes:
        assert self.sock is not None
        while terminator not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("GDB stub closed connection")
            self.buf += chunk
            if len(self.buf) > max_bytes:
                raise ConnectionError("GDB stub flooded buffer")
        idx = self.buf.index(terminator) + len(terminator)
        out, self.buf = self.buf[:idx], self.buf[idx:]
        return out

    def _read_packet(self) -> bytes:
        # discard until we see '$' or '+' / '-' acks
        while True:
            assert self.sock is not None
            if not self.buf:
                self.buf += self.sock.recv(4096)
                if not self.buf:
                    raise ConnectionError("GDB stub closed")
            c, self.buf = self.buf[:1], self.buf[1:]
            if c in (b"+", b"-"):
                continue
            if c == b"$":
                break
        # read until '#' then 2 hex bytes
        while b"#" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("GDB stub closed")
            self.buf += chunk
        hash_idx = self.buf.index(b"#")
        payload = self.buf[:hash_idx]
        # also need 2 chars after #
        while len(self.buf) < hash_idx + 3:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("GDB stub closed")
            self.buf += chunk
        self.buf = self.buf[hash_idx + 3:]
        # send ack
        self._send_raw(b"+")
        return payload

    def cmd(self, payload: str, expect_reply: bool = True) -> str:
        """Send a command, handle ack, return response payload string."""
        data = payload.encode("ascii")
        pkt = b"$" + data + b"#" + self._checksum(data)
        # retry on '-' ack up to 3 times
        for _ in range(3):
            self._send_raw(pkt)
            # wait for ack
            ack = self._wait_ack()
            if ack == b"+":
                break
            time.sleep(0.05)
        if not expect_reply:
            return ""
        return self._read_packet().decode("ascii", errors="replace")

    def _wait_ack(self) -> bytes:
        assert self.sock is not None
        while True:
            if not self.buf:
                self.buf += self.sock.recv(4096)
                if not self.buf:
                    raise ConnectionError("GDB stub closed")
            c, self.buf = self.buf[:1], self.buf[1:]
            if c in (b"+", b"-"):
                return c
            # If we got '$' the stub is async-replying without ack — stuff back
            self.buf = c + self.buf
            return b"+"

    # ---- high-level helpers -------------------------------------------------
    def read_mem(self, addr: int, length: int) -> bytes:
        # Split into chunks; mGBA stub OK with ~512 bytes per request.
        out = bytearray()
        chunk = 512
        for off in range(0, length, chunk):
            n = min(chunk, length - off)
            reply = self.cmd(f"m{addr+off:x},{n:x}")
            if reply.startswith("E"):
                raise IOError(f"read_mem({addr+off:#x},{n}) failed: {reply}")
            out += bytes.fromhex(reply)
        return bytes(out)

    def write_mem(self, addr: int, data: bytes) -> None:
        hex_data = data.hex()
        reply = self.cmd(f"M{addr:x},{len(data):x}:{hex_data}")
        if not reply.startswith("OK"):
            raise IOError(f"write_mem failed: {reply}")

    def read_regs(self) -> list[int]:
        """ARM7TDMI: r0..r15 + cpsr (mGBA returns 17 32-bit regs little-endian)."""
        reply = self.cmd("g")
        if reply.startswith("E") or len(reply) < 16*8:
            raise IOError(f"read_regs failed: {reply!r}")
        regs = []
        for i in range(0, len(reply), 8):
            word_hex = reply[i:i+8]
            if len(word_hex) < 8: break
            # little-endian hex pairs
            val = int.from_bytes(bytes.fromhex(word_hex), "little")
            regs.append(val)
        return regs

    def set_hw_break(self, addr: int, kind: int = 2) -> None:
        """kind=2 (Thumb) or kind=4 (ARM). mGBA accepts both for hwbreak."""
        reply = self.cmd(f"Z1,{addr:x},{kind}")
        if not reply.startswith("OK"):
            raise IOError(f"set_hw_break({addr:#x}) failed: {reply!r}")

    def clear_hw_break(self, addr: int, kind: int = 2) -> None:
        self.cmd(f"z1,{addr:x},{kind}")

    def cont(self) -> str:
        """Send continue, block waiting for stop reply (T05/S05)."""
        # Continue does not produce an immediate ack-only response; the stub
        # sends a stop packet when the target halts.
        self._send_raw(b"$c#" + self._checksum(b"c"))
        # consume ack
        self._wait_ack()
        return self._read_packet().decode("ascii")

    def step(self) -> str:
        self._send_raw(b"$s#" + self._checksum(b"s"))
        self._wait_ack()
        return self._read_packet().decode("ascii")

    def detach(self) -> None:
        try: self.cmd("D")
        except Exception: pass

    def stop_reason(self) -> str:
        return self.cmd("?")
