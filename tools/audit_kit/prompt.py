"""Render the audit prompt that an LLM auditor receives for one shard.

The prompt embeds:
- the preset's verdict taxonomy and definitions (from the template)
- the evidence policy (required types, banned hosts)
- the FlagRecord JSON shape it must emit
- the actual entries for this shard

The LLM is expected to emit ONLY a JSON object matching the ShardFlagFile
schema — empty `flagged` list is a valid output ("nothing wrong here").
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import AuditConfig

HERE = Path(__file__).resolve().parent


_FALLBACK_TEMPLATE = """\
# Audit task

You are auditing a shard of {preset} records for translation, grammar,
naturalness, and consistency problems. Your job is to FLAG only entries
with clear, defensible defects, with direct-source evidence for each flag.

## Verdict taxonomy

Use exactly one of: {verdicts}

## Evidence policy

- Every flag MUST carry an `evidence` object: `{{type, value, note?}}`.
- Allowed types: {evidence_types}
- For `type: "url"` value MUST be an http(s) URL to a direct source.
- DO NOT cite AI Overview snippets, AI answer summaries, or generated
  blog content. Naver Korean Dictionary, Standard Korean Dictionary,
  official Pokemon Korea pages, and similar primary sources are OK.
- For `type: "corpus-rule"` value is the rule (e.g. "noun-noun compound,
  no internal space"); use only when an authoritative URL isn't a fit.
- For `type: "in-game-canon"` value is the ROM-anchored fact (e.g.
  "Struggle fires automatically when PP is exhausted").
- Disallowed hosts: {disallowed_hosts}

If you can't produce evidence, DO NOT FLAG — leave the entry alone.

## Output

Emit exactly one JSON object, no prose, matching:

```
{{
  "shardFile": "{shard_file}",
  "range": [{start}, {end}],
  "inspected": {count},
  "flagged": [
    {{
      "key": "<value of the {key_field} field>",
      "verdict": "<one of: {verdicts}>",
      "issue": "<concise prose>",
      "suggestion": "<replacement text or 'regloss to ...'>",
      "evidence": {{"type": "url|corpus-rule|in-game-canon", "value": "...", "note": null}},
      "originalValue": {{"<auditField>": "<snapshot>"}},
      "proposedValue": {{"<dataset field to set>": "<new value>"}}
    }}
  ],
  "auditor": "{auditor_hint}",
  "auditedAt": "<ISO date>"
}}
```

`originalValue` should snapshot the audited fields so the reviewer UI can
diff. `proposedValue` is what the applier will write into the entry if the
reviewer accepts; if you only want to suggest in prose, omit it and put
the suggestion in `suggestion`.

## Shard

Below is the list of {count} entries. For each, decide: leave alone OR
flag with evidence. Be conservative — only flag clear, defensible defects.

```
{entries_json}
```
"""


def render(cfg: AuditConfig, shard_manifest: dict[str, Any], *,
           auditor_hint: str = "llm-claude-opus-4-7") -> str:
    template = _FALLBACK_TEMPLATE
    if cfg.promptTemplate:
        tp = HERE / cfg.promptTemplate
        if tp.exists():
            template = tp.read_text(encoding="utf-8")

    start, end = shard_manifest["range"]
    return template.format(
        preset=cfg.name,
        verdicts=", ".join(cfg.verdicts),
        evidence_types=", ".join(cfg.evidencePolicy.allowedTypes),
        disallowed_hosts=", ".join(cfg.evidencePolicy.disallowedHosts) or "(none)",
        shard_file=shard_manifest["shardFile"],
        start=start, end=end,
        count=shard_manifest["count"],
        key_field=shard_manifest["keyField"],
        auditor_hint=auditor_hint,
        entries_json=json.dumps(shard_manifest["entries"], ensure_ascii=False, indent=2),
    )
