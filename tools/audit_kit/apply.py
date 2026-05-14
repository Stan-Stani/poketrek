"""Apply reviewer decisions to dataset(s).

Input:
  - apply-list.json (from aggregate)
  - decisions.json  (from the HTML reviewer; optional — if omitted, every
    flag is treated as `accept` for the original suggestion)

For each accepted flag the entry is mutated in-place and an `auditFix`
sidecar is recorded inside the entry (mirrors how moneo's audit-v2 already
annotates fixes). `reject` and `defer` are no-ops on the dataset but are
recorded in the run log. `edit` uses the reviewer's override.

The applier is idempotent: re-running with the same decisions yields the
same dataset bytes.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AuditConfig, DatasetSpec, ROOT, get_entries
from .schema import validate_decision


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, doc: Any) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ds_by_shard(cfg: AuditConfig) -> dict[str, DatasetSpec]:
    return {ds.path: ds for ds in cfg.datasets}


def apply(cfg: AuditConfig, apply_list_path: Path,
          decisions_path: Path | None = None,
          dry_run: bool = False,
          audited_at: str | None = None) -> dict[str, Any]:
    apply_doc = _load(apply_list_path)
    flags: list[dict[str, Any]] = apply_doc["applyList"]

    decisions: dict[str, dict[str, Any]] = {}
    if decisions_path is not None:
        dec_doc = _load(decisions_path)
        for d in dec_doc.get("decisions", []):
            errs = validate_decision(d)
            if errs:
                raise ValueError(f"invalid decision {d!r}: {errs}")
            decisions[d["key"]] = d

    ds_by_shard = _ds_by_shard(cfg)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for f in flags:
        key = f.get("sourceShard") or ""
        grouped.setdefault(key, []).append(f)

    audited_at = audited_at or datetime.now(timezone.utc).date().isoformat()

    log = {
        "preset": cfg.name,
        "auditedAt": audited_at,
        "dryRun": dry_run,
        "applied": 0, "rejected": 0, "deferred": 0, "edited": 0, "skipped": 0,
        "perDataset": {},
    }

    for shard_path, shard_flags in grouped.items():
        if shard_path not in ds_by_shard:
            log["skipped"] += len(shard_flags)
            continue
        ds = ds_by_shard[shard_path]
        full_path = ROOT / ds.path
        doc = _load(full_path)
        entries = get_entries(doc, ds.entriesPath)
        by_key: dict[str, dict[str, Any]] = {}
        for e in entries:
            k = e.get(ds.keyField)
            if k is not None:
                by_key[str(k)] = e

        ds_log = log["perDataset"].setdefault(ds.name, {
            "applied": 0, "rejected": 0, "deferred": 0, "edited": 0, "missing": 0,
        })

        for f in shard_flags:
            key = str(f.get("key"))
            decision = decisions.get(key, {"key": key, "action": "accept"})
            action = decision["action"]
            if action == "reject":
                log["rejected"] += 1; ds_log["rejected"] += 1; continue
            if action == "defer":
                log["deferred"] += 1; ds_log["deferred"] += 1; continue
            entry = by_key.get(key)
            if entry is None:
                ds_log["missing"] += 1
                continue

            proposed = (decision.get("override") if action == "edit" else None) or f.get("proposedValue") or {}
            for field_name, value in proposed.items():
                entry[field_name] = value

            entry[cfg.auditFixField] = {
                "verdict": f.get("verdict"),
                "issue": f.get("issue"),
                "evidence": f.get("evidence"),
                "suggestion": f.get("suggestion"),
                "auditor": f.get("auditor"),
                "auditedAt": audited_at,
                "reviewerAction": action,
                "reviewerNote": decision.get("note"),
            }
            if action == "edit":
                log["edited"] += 1; ds_log["edited"] += 1
            else:
                log["applied"] += 1; ds_log["applied"] += 1

        if not dry_run:
            _save(full_path, doc)

    return log
