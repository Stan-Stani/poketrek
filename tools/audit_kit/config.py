"""AuditConfig loader.

A preset is a JSON file describing one or more datasets and the verdict/
evidence policy for a coordinated audit run. Presets live in `presets/` and
are referenced by name (`--preset moneo-sentences-ko`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PRESETS_DIR = Path(__file__).resolve().parent / "presets"


@dataclass
class DatasetSpec:
    name: str                # short id, e.g. "themed-mined"
    path: str                # path relative to repo root
    entriesPath: str = "entries"   # dotted path inside the JSON (or "" for root list)
    keyField: str = "vocabId"      # which field uniquely identifies an entry
    auditFields: dict[str, str] = field(default_factory=dict)  # logical -> field name


@dataclass
class EvidencePolicy:
    required: bool = True
    allowedTypes: tuple[str, ...] = ("url", "corpus-rule", "in-game-canon")
    disallowedHosts: tuple[str, ...] = ()


@dataclass
class AuditConfig:
    name: str
    datasets: list[DatasetSpec]
    verdicts: list[str]
    evidencePolicy: EvidencePolicy
    promptTemplate: str | None = None    # relative path to prompt template
    shardSize: int = 200
    auditFixField: str = "auditFix"      # field appended to each applied entry


def load_preset(name_or_path: str) -> AuditConfig:
    p = Path(name_or_path)
    if not p.exists():
        # Treat as preset name
        cand = PRESETS_DIR / f"{name_or_path}.json"
        if not cand.exists():
            raise FileNotFoundError(
                f"preset {name_or_path!r} not found; looked for {p} and {cand}"
            )
        p = cand
    raw = json.loads(p.read_text(encoding="utf-8"))
    ev = raw.get("evidencePolicy", {})
    return AuditConfig(
        name=raw.get("name", p.stem),
        datasets=[DatasetSpec(**d) for d in raw["datasets"]],
        verdicts=list(raw["verdicts"]),
        evidencePolicy=EvidencePolicy(
            required=ev.get("required", True),
            allowedTypes=tuple(ev.get("allowedTypes", EvidencePolicy.allowedTypes)),
            disallowedHosts=tuple(ev.get("disallowedHosts", ())),
        ),
        promptTemplate=raw.get("promptTemplate"),
        shardSize=int(raw.get("shardSize", 200)),
        auditFixField=raw.get("auditFixField", "auditFix"),
    )


def get_entries(doc: Any, entries_path: str) -> list[dict[str, Any]]:
    if not entries_path:
        if not isinstance(doc, list):
            raise ValueError("entriesPath is empty but document is not a list")
        return doc
    cursor: Any = doc
    for part in entries_path.split("."):
        if not isinstance(cursor, dict):
            raise ValueError(f"entries path {entries_path!r} traversal failed at {part!r}")
        cursor = cursor[part]
    if not isinstance(cursor, list):
        raise ValueError(f"entries path {entries_path!r} did not resolve to a list")
    return cursor


def set_entries(doc: Any, entries_path: str, new_entries: list[dict[str, Any]]) -> Any:
    if not entries_path:
        return new_entries
    parts = entries_path.split(".")
    cursor: Any = doc
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = new_entries
    return doc
