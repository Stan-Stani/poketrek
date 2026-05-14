"""Slice a dataset into shard manifests for parallel auditors."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AuditConfig, DatasetSpec, get_entries, ROOT


def shard_dataset(ds: DatasetSpec, shard_size: int) -> list[dict[str, Any]]:
    p = ROOT / ds.path
    doc = json.loads(p.read_text(encoding="utf-8"))
    entries = get_entries(doc, ds.entriesPath)
    out: list[dict[str, Any]] = []
    n = len(entries)
    for start in range(0, n, shard_size):
        end = min(start + shard_size, n)
        out.append({
            "dataset": ds.name,
            "shardFile": ds.path,
            "range": [start, end],
            "count": end - start,
            "keyField": ds.keyField,
            "entries": entries[start:end],
        })
    return out


def shard_config(cfg: AuditConfig) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ds in cfg.datasets:
        out.extend(shard_dataset(ds, cfg.shardSize))
    return out


def write_shards(cfg: AuditConfig, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for s in shard_config(cfg):
        start, end = s["range"]
        fname = f"shard-{s['dataset']}-{start:05d}-{end:05d}.json"
        path = out_dir / fname
        path.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(path)
    return paths
