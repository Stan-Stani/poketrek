"""Schema for the audit_kit framework.

A single source of truth for what an auditor (LLM or human) emits and what
the validator / aggregator / applier consume. Datasets are decoupled from the
audit records: a dataset is *any* JSON document with a list of entries; a flag
record points at one entry by `key`.

The framework is deliberately strict about evidence: every flag must declare
an Evidence object (`url` / `corpus-rule` / `in-game-canon`). The validator
rejects flags missing it. See README.md for the rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# --- Evidence ---------------------------------------------------------------

EVIDENCE_TYPES = ("url", "corpus-rule", "in-game-canon")


@dataclass
class Evidence:
    type: str
    value: str
    note: str | None = None

    def validate(self, allowed_types: tuple[str, ...] = EVIDENCE_TYPES,
                 disallowed_hosts: tuple[str, ...] = ()) -> list[str]:
        errs: list[str] = []
        if self.type not in allowed_types:
            errs.append(f"evidence.type={self.type!r} not in {allowed_types}")
        if not self.value or not str(self.value).strip():
            errs.append("evidence.value is empty")
        if self.type == "url":
            v = str(self.value)
            if not (v.startswith("http://") or v.startswith("https://")):
                errs.append(f"evidence.value for type=url must be http(s): {v!r}")
            for bad in disallowed_hosts:
                if bad and bad in v:
                    errs.append(f"evidence.value host {bad!r} is disallowed (e.g. AI Overview snippets)")
        return errs


# --- Flag records -----------------------------------------------------------

@dataclass
class FlagRecord:
    """One flag emitted by an auditor against one entry."""
    key: str                          # value of the dataset's keyField
    verdict: str                      # one of the preset's verdict taxonomy
    issue: str                        # short prose explanation
    evidence: Evidence
    suggestion: str | None = None     # proposed replacement text or "regloss to ..."
    originalValue: dict[str, Any] | None = None   # snapshot of audited fields
    proposedValue: dict[str, Any] | None = None   # structured replacement (preferred over `suggestion`)
    sourceShard: str | None = None
    hadPriorAuditFix: bool = False
    auditor: str | None = None        # e.g. "llm-claude-opus-4-7", "human:stan"
    confidence: float | None = None   # 0..1, optional

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Drop Nones to keep the JSON tidy
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ShardFlagFile:
    """The artifact a single auditor emits for one shard."""
    shardFile: str           # relative path of the dataset shard was drawn from
    range: tuple[int, int]   # [start, end) over the dataset's entry list
    inspected: int
    flagged: list[FlagRecord]
    auditor: str | None = None
    auditedAt: str | None = None     # ISO date

    def to_dict(self) -> dict[str, Any]:
        return {
            "shardFile": self.shardFile,
            "range": list(self.range),
            "inspected": self.inspected,
            "flagged": [f.to_dict() for f in self.flagged],
            **({"auditor": self.auditor} if self.auditor else {}),
            **({"auditedAt": self.auditedAt} if self.auditedAt else {}),
        }


# --- Decisions (from the reviewer UI) ---------------------------------------

@dataclass
class Decision:
    """Reviewer's call on a single flag."""
    key: str
    action: str               # "accept" | "reject" | "edit" | "defer"
    override: dict[str, Any] | None = None   # used when action == "edit"
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {"key": self.key, "action": self.action}
        if self.override is not None: d["override"] = self.override
        if self.note: d["note"] = self.note
        return d


# --- Validators -------------------------------------------------------------

VALID_ACTIONS = ("accept", "reject", "edit", "defer")


def validate_flag(rec: dict[str, Any], *, verdicts: list[str],
                  allowed_evidence_types: tuple[str, ...] = EVIDENCE_TYPES,
                  disallowed_hosts: tuple[str, ...] = ()) -> list[str]:
    errs: list[str] = []
    for required in ("key", "verdict", "issue", "evidence"):
        if required not in rec or rec[required] in (None, "", []):
            errs.append(f"missing required field: {required}")
    if "verdict" in rec and rec["verdict"] not in verdicts:
        errs.append(f"verdict={rec['verdict']!r} not in preset verdicts {verdicts}")
    if "evidence" in rec and isinstance(rec["evidence"], dict):
        ev = rec["evidence"]
        e = Evidence(type=ev.get("type", ""), value=ev.get("value", ""), note=ev.get("note"))
        errs.extend(e.validate(allowed_evidence_types, disallowed_hosts))
    elif "evidence" in rec:
        errs.append("evidence must be an object {type,value,note?}")
    return errs


def validate_decision(rec: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not rec.get("key"):
        errs.append("missing key")
    if rec.get("action") not in VALID_ACTIONS:
        errs.append(f"action={rec.get('action')!r} not in {VALID_ACTIONS}")
    if rec.get("action") == "edit" and not rec.get("override"):
        errs.append("action=edit requires override")
    return errs
