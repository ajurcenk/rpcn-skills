# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Fail unless a passing eval record exists for the current skill content (R12, AD-14).

Computes the skills hash (see tools/eval_record.py) and looks for any
`evals/results/*-<hash12>.json` whose `skills_hash` equals the full hash and
whose `passed` is true. Runs in CI; it never runs an eval itself.

Prints one JSON object:
  {"ok": bool, "skills_hash": str, "record": <path>|null, "reason": str}

Exit codes:
  0  a passing record was found
  1  none was found: run `uv run tools/run_evals.py`, then commit the record
  2  a record with this hash prefix is malformed (not JSON, or schema is not 1),
     or the skills hash cannot be computed (git fails inside the checkout)

Run: uv run tools/eval_record_check.py [--root <dir>]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import eval_record

FIX = "run `uv run tools/run_evals.py`, then commit the record it writes to evals/results/"


def check(root: Path) -> tuple[int, dict]:
    try:
        full = eval_record.skills_hash(root)
    except eval_record.HashError as exc:
        return 2, {"ok": False, "skills_hash": None, "record": None,
                   "reason": f"cannot compute the skills hash: {exc}"}
    out = {"ok": False, "skills_hash": full, "record": None, "reason": ""}
    try:
        found = eval_record.find_passing(root, full)
    except eval_record.RecordError as exc:
        out["reason"] = f"malformed record: {exc}"
        return 2, out
    if found is None:
        candidates = eval_record.candidate_records(root, full)
        what = ("no passing record" if candidates else "no record") + \
            f" for skills hash {full[:eval_record.PREFIX_LEN]}"
        out["reason"] = f"{what}; {FIX}"
        return 1, out
    out["ok"] = True
    out["record"] = found.relative_to(root).as_posix()
    out["reason"] = "passing record matches the current skills"
    return 0, out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=eval_record.REPO_ROOT,
                        help="repo root (default: this repo)")
    args = parser.parse_args(argv)
    code, out = check(args.root.resolve())
    print(json.dumps(out, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
