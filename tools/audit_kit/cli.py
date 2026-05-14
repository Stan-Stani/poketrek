"""audit_kit CLI.

Subcommands:
  shard      Split datasets into per-auditor shard manifests + prompts.
  validate   Check flag-*.json files against the preset's policy.
  aggregate  Build audit-results.json + apply-list.json from flag files.
  apply      Apply (optionally reviewed) flags to the datasets.
  prompt     Print the audit prompt for a single shard (for piping to an LLM).
  init-run   Bootstrap a run directory with shards/, flags/, decisions.json placeholder.

Run order for one audit cycle:
  python -m audit_kit init-run --preset moneo-sentences-ko --out runs/2026-05-14
  # parallel LLM agents each handle one shard and write flag files into flags/
  python -m audit_kit validate  --preset moneo-sentences-ko --flags runs/2026-05-14/flags
  python -m audit_kit aggregate --preset moneo-sentences-ko --flags runs/2026-05-14/flags --out runs/2026-05-14
  # open viewer/index.html, load apply-list.json, export decisions.json
  python -m audit_kit apply     --preset moneo-sentences-ko --apply-list runs/2026-05-14/apply-list.json \
                                --decisions runs/2026-05-14/decisions.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import aggregate as agg
from . import apply as apl
from . import prompt as pr
from . import shard as sh
from . import validate as vd
from .config import load_preset


def cmd_shard(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    out = Path(args.out)
    paths = sh.write_shards(cfg, out)
    print(f"wrote {len(paths)} shard manifests under {out}")
    if args.with_prompts:
        prompts_dir = out.parent / "prompts" if out.name == "shards" else out / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        for sp in paths:
            manifest = json.loads(sp.read_text(encoding="utf-8"))
            txt = pr.render(cfg, manifest)
            (prompts_dir / (sp.stem + ".prompt.md")).write_text(txt, encoding="utf-8")
        print(f"wrote prompts under {prompts_dir}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    total, lines = vd.validate_dir(cfg, Path(args.flags))
    for line in lines: print(line)
    return 0 if len(lines) == 1 else 1


def cmd_aggregate(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    results, apply_doc = agg.aggregate(cfg, Path(args.flags))
    out = Path(args.out)
    rp, ap = agg.write_outputs(results, apply_doc, out)
    print(f"wrote {rp} ({results['totalFlagged']} flags, {len(results['rejected'])} rejected)")
    print(f"wrote {ap}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    decisions = Path(args.decisions) if args.decisions else None
    log = apl.apply(cfg, Path(args.apply_list), decisions, dry_run=args.dry_run)
    print(json.dumps(log, ensure_ascii=False, indent=2))
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    manifest = json.loads(Path(args.shard).read_text(encoding="utf-8"))
    sys.stdout.write(pr.render(cfg, manifest))
    return 0


def cmd_init_run(args: argparse.Namespace) -> int:
    cfg = load_preset(args.preset)
    out = Path(args.out)
    (out / "shards").mkdir(parents=True, exist_ok=True)
    (out / "flags").mkdir(parents=True, exist_ok=True)
    (out / "prompts").mkdir(parents=True, exist_ok=True)
    paths = sh.write_shards(cfg, out / "shards")
    for sp in paths:
        manifest = json.loads(sp.read_text(encoding="utf-8"))
        (out / "prompts" / (sp.stem + ".prompt.md")).write_text(
            pr.render(cfg, manifest), encoding="utf-8"
        )
    (out / "README.md").write_text(
        f"# {cfg.name} audit run\n\n"
        f"- shards/  — one JSON manifest per auditor task ({len(paths)} total)\n"
        f"- prompts/ — rendered audit prompt to feed each LLM auditor\n"
        f"- flags/   — drop the auditors' flag-*.json outputs here\n"
        f"- after auditors finish, run validate → aggregate → reviewer UI → apply\n",
        encoding="utf-8",
    )
    print(f"initialised run at {out} with {len(paths)} shards/prompts")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="audit_kit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("shard");      sp.add_argument("--preset", required=True); sp.add_argument("--out", required=True); sp.add_argument("--with-prompts", action="store_true"); sp.set_defaults(fn=cmd_shard)
    sp = sub.add_parser("validate");   sp.add_argument("--preset", required=True); sp.add_argument("--flags", required=True); sp.set_defaults(fn=cmd_validate)
    sp = sub.add_parser("aggregate");  sp.add_argument("--preset", required=True); sp.add_argument("--flags", required=True); sp.add_argument("--out", required=True); sp.set_defaults(fn=cmd_aggregate)
    sp = sub.add_parser("apply");      sp.add_argument("--preset", required=True); sp.add_argument("--apply-list", required=True); sp.add_argument("--decisions"); sp.add_argument("--dry-run", action="store_true"); sp.set_defaults(fn=cmd_apply)
    sp = sub.add_parser("prompt");     sp.add_argument("--preset", required=True); sp.add_argument("--shard", required=True); sp.set_defaults(fn=cmd_prompt)
    sp = sub.add_parser("init-run");   sp.add_argument("--preset", required=True); sp.add_argument("--out", required=True); sp.set_defaults(fn=cmd_init_run)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.fn(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
