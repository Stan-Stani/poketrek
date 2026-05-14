"""Validate a directory of `flag-*.json` files against an AuditConfig.

This is the gate that enforces the evidence policy. Any flag missing
`evidence`, using a disallowed host (e.g. AI Overview snippets), or carrying
an unknown verdict will be reported.

Exit code 0 = clean. Exit code 1 = one or more issues found.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AuditConfig
from .schema import validate_flag


def validate_dir(cfg: AuditConfig, flag_dir: Path) -> tuple[int, list[str]]:
    issues: list[str] = []
    files = sorted(flag_dir.glob("flag-*.json"))
    total_flags = 0
    for fp in files:
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"{fp.name}: invalid JSON ({exc})")
            continue
        for required in ("shardFile", "range", "inspected", "flagged"):
            if required not in doc:
                issues.append(f"{fp.name}: missing top-level {required!r}")
        for i, rec in enumerate(doc.get("flagged", []) or []):
            total_flags += 1
            errs = validate_flag(
                rec,
                verdicts=cfg.verdicts,
                allowed_evidence_types=cfg.evidencePolicy.allowedTypes,
                disallowed_hosts=cfg.evidencePolicy.disallowedHosts,
            )
            for e in errs:
                issues.append(f"{fp.name}#flagged[{i}] key={rec.get('key')!r}: {e}")
    summary = (f"validated {len(files)} flag files, {total_flags} flags, "
               f"{len(issues)} issue(s)")
    return total_flags, [summary] + issues
