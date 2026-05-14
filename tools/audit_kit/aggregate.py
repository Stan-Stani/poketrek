"""Aggregate per-shard `flag-*.json` files into:
- audit-results.json — counts by verdict / by shard / by dataset
- apply-list.json    — flat list of flags ready for reviewer + applier

Flags that fail validation are dropped *and* listed in audit-results.json
under `rejected`, so nothing disappears silently.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AuditConfig
from .schema import validate_flag


def aggregate(cfg: AuditConfig, flag_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    files = sorted(flag_dir.glob("flag-*.json"))
    verdict_counts: Counter[str] = Counter()
    shard_stats: dict[str, dict[str, int]] = {}
    dataset_stats: dict[str, dict[str, int]] = {}
    apply_list: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for fp in files:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        shard_id = f"{doc.get('shardFile','?')} {tuple(doc.get('range', []))}"
        shard_stats[shard_id] = {
            "inspected": int(doc.get("inspected", 0)),
            "flagged": 0,
        }
        dataset_name = doc.get("shardFile", "?").split("/")[-1]
        ds = dataset_stats.setdefault(dataset_name, {"inspected": 0, "flagged": 0})
        ds["inspected"] += int(doc.get("inspected", 0))

        for rec in doc.get("flagged", []) or []:
            errs = validate_flag(
                rec,
                verdicts=cfg.verdicts,
                allowed_evidence_types=cfg.evidencePolicy.allowedTypes,
                disallowed_hosts=cfg.evidencePolicy.disallowedHosts,
            )
            if errs and cfg.evidencePolicy.required:
                rejected.append({"file": fp.name, "key": rec.get("key"), "errors": errs})
                continue
            entry = dict(rec)
            entry.setdefault("sourceShard", doc.get("shardFile"))
            apply_list.append(entry)
            verdict_counts[rec.get("verdict", "unknown")] += 1
            shard_stats[shard_id]["flagged"] += 1
            ds["flagged"] += 1

    results = {
        "auditedAt": datetime.now(timezone.utc).date().isoformat(),
        "preset": cfg.name,
        "totalInspected": sum(s["inspected"] for s in shard_stats.values()),
        "totalFlagged": sum(s["flagged"] for s in shard_stats.values()),
        "byVerdict": dict(verdict_counts.most_common()),
        "byDataset": dataset_stats,
        "byShard": shard_stats,
        "rejected": rejected,
    }
    apply_doc = {
        "preset": cfg.name,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "applyList": apply_list,
    }
    return results, apply_doc


def write_outputs(results: dict[str, Any], apply_doc: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rp = out_dir / "audit-results.json"
    ap = out_dir / "apply-list.json"
    rp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ap.write_text(json.dumps(apply_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return rp, ap
