# audit_kit — sentence/translation audit framework

A small framework for auditing JSON datasets of sentences, translations, and
glosses. LLM agents (or humans) emit structured **flag records** with required
evidence; the framework validates them, aggregates them into an apply-list,
hands them to a static HTML reviewer for accept/reject/edit, and applies the
approved fixes back into the dataset.

Designed against the existing moneo pipeline (`audit/`, `audit-v2/`,
`audit-vocab/`) and shipped with a moneo preset, but the core is dataset-
agnostic — point a preset at any JSON document and the same lifecycle runs.

## The lifecycle

```
                    presets/<name>.json
                            │
                            ▼
     ┌────────────────┐  shard   ┌────────────────┐
     │ source dataset │ ───────▶ │  shard-*.json  │ ──┐
     └────────────────┘          │  prompt-*.md   │   │ parallel
                                 └────────────────┘   │ LLM auditors
                                                      ▼
                                              flag-*.json (one per shard)
                                                      │
                                                      ▼
                                              validate (evidence policy)
                                                      │
                                                      ▼
                                              aggregate
                                                      │
                                                      ▼
                                  ┌─── audit-results.json (stats + rejects)
                                  └─── apply-list.json
                                                      │
                                                      ▼
                                            viewer/index.html
                                          (accept/reject/edit per flag)
                                                      │
                                                      ▼
                                              decisions.json
                                                      │
                                                      ▼
                                       apply → mutated dataset(s)
                                       (each entry gets an `auditFix`)
```

## Lifecycle commands

```bash
# 1. Bootstrap a run: write shards/, prompts/, flags/ skeleton.
python3 -m tools.audit_kit init-run \
    --preset moneo-sentences-ko \
    --out tools/moneo/audit-2026-05-14

# 2. Hand each prompt to an LLM auditor; collect outputs as flag-*.json
#    into the run's flags/ directory. (See "Auditor contract" below.)

# 3. Validate every flag — fails fast on missing evidence, unknown verdicts,
#    or banned hosts (e.g. AI Overview snippets).
python3 -m tools.audit_kit validate \
    --preset moneo-sentences-ko \
    --flags tools/moneo/audit-2026-05-14/flags

# 4. Aggregate into audit-results.json (stats) + apply-list.json.
python3 -m tools.audit_kit aggregate \
    --preset moneo-sentences-ko \
    --flags tools/moneo/audit-2026-05-14/flags \
    --out   tools/moneo/audit-2026-05-14

# 5. Review in the browser. Open viewer/index.html, load apply-list.json,
#    accept/reject/edit each flag, then "Export decisions.json".

# 6. Apply approved fixes to the dataset (with --dry-run first).
python3 -m tools.audit_kit apply \
    --preset moneo-sentences-ko \
    --apply-list tools/moneo/audit-2026-05-14/apply-list.json \
    --decisions  tools/moneo/audit-2026-05-14/decisions.json \
    --dry-run
```

If you omit `--decisions`, every flag is treated as `accept`.

## Preset format

A preset is a JSON file in `presets/`. Two ship out of the box:

- `moneo-sentences-ko.json` — the four `sentences-ko-themed*.json` decks
- `moneo-vocab-ko.json` — the `seed-vocab-ko*.json` decks

To audit something else, drop a sibling preset:

```json
{
  "name": "my-dataset",
  "datasets": [
    {
      "name": "main",
      "path": "path/to/dataset.json",
      "entriesPath": "entries",
      "keyField": "id",
      "auditFields": {"text": "text", "translation": "translation"}
    }
  ],
  "verdicts": ["mistranslation", "ungrammatical", "uncertain"],
  "evidencePolicy": {
    "required": true,
    "allowedTypes": ["url", "corpus-rule"],
    "disallowedHosts": ["google.com/aio"]
  },
  "shardSize": 200,
  "auditFixField": "auditFix"
}
```

Set `entriesPath: ""` if your document is a top-level JSON array.

## Auditor contract

Each LLM (or human) auditor processes one shard and emits one JSON object:

```json
{
  "shardFile": "app/src/main/assets/moneo/sentences-ko-themed.json",
  "range": [0, 200],
  "inspected": 200,
  "auditor": "llm-claude-opus-4-7",
  "auditedAt": "2026-05-14",
  "flagged": [
    {
      "key": "<value of the dataset's keyField>",
      "verdict": "<one of the preset's verdicts>",
      "issue": "<concise prose>",
      "suggestion": "<replacement text or 'regloss to ...'>",
      "evidence": {
        "type": "url|corpus-rule|in-game-canon",
        "value": "<URL or rule text>",
        "note": "<optional>"
      },
      "originalValue": {"korean": "...", "gloss": "..."},
      "proposedValue": {"gloss": "..."},
      "hadPriorAuditFix": false
    }
  ]
}
```

Empty `flagged` is fine — "nothing wrong with this shard" is a valid result.
Auditors should **not** flag anything they can't back with direct-source
evidence; the validator drops such flags.

Save these files into the run's `flags/` directory as
`flag-<shard-id>.json`. The aggregator picks up anything matching
`flag-*.json` glob.

## Evidence policy

`evidencePolicy.required: true` (the default) means every flag must carry an
`evidence` object. Three types are accepted:

- `url` — must be `http(s)://...` and not in `disallowedHosts`. The moneo
  preset blocks Google AI Overview and Bing search-snippet URLs because
  those are AI-generated summaries, not primary sources.
- `corpus-rule` — a stated rule (e.g. *"noun-noun compound, no internal
  space"*). Use when no canonical URL fits the point being made.
- `in-game-canon` — a ROM-anchored fact (e.g. *"Struggle fires automatically
  when PP is exhausted"*).

Anything missing or violating the policy is **dropped** by the aggregator
and listed under `rejected` in `audit-results.json` so the omission is
visible.

## Output of `apply`

When a flag is `accept`ed (or `edit`ed via the reviewer), the matching entry
is mutated in two ways:

1. Each `proposedValue` field (or the reviewer's `override`) is written onto
   the entry.
2. A sidecar `auditFix` field is appended, recording the verdict, issue,
   evidence, auditor, and reviewer action. This mirrors how moneo's
   `audit-v2` already annotates fixes and lets future audits see what's
   been touched.

`reject` and `defer` decisions leave the dataset alone but show up in the
run log so nothing disappears silently.

## Why this exists

Three rounds of ad-hoc audits (`audit/`, `audit-v2/`, `audit-vocab/`) had
already converged on this shape — shard → parallel LLM → flag files →
aggregate → apply — but each round re-implemented the schema, the verdict
taxonomy, and the evidence policy by hand. This package freezes the schema,
makes the evidence policy machine-checkable, and turns the human review
step into a real UI instead of editing JSON.

## Layout

```
tools/audit_kit/
├── README.md             ← you are here
├── schema.py             ← FlagRecord/Evidence/Decision + validators
├── config.py             ← AuditConfig + preset loader
├── shard.py              ← dataset → shard manifests
├── prompt.py             ← shard manifest → auditor prompt
├── validate.py           ← flag-*.json → policy check
├── aggregate.py          ← flag-*.json → audit-results + apply-list
├── apply.py              ← apply-list + decisions → mutated datasets
├── cli.py                ← `python -m tools.audit_kit ...`
├── presets/
│   ├── moneo-sentences-ko.json
│   └── moneo-vocab-ko.json
└── viewer/
    └── index.html        ← static reviewer (file:// is fine)
```
