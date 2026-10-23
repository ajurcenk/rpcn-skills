# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Copy shared files from tools/shared/ into each skill, or check the copies (AD-2).

Each skill folder `skills/<skill>/` may hold a manifest, `shared.txt`, with one
mapping per line:

    <source> <dest>

`<source>` is relative to `tools/shared/` and `<dest>` is relative to the skill
folder. `#` starts a comment, and blank lines are ignored. Skills without a
manifest are skipped and reported with state `no-manifest`.

Modes:
  sync (default)  copy every listed file byte-for-byte, creating folders as
                  needed, with the executable bit off. Exit 0.
  --check         change nothing; report each copy as `ok`, `missing` or
                  `differs`. Exit 1 when any copy has drifted.

An invalid manifest (a source that does not exist, a dest outside the skill
folder, a dest listed twice, a malformed line) is an error: exit 2, and
nothing is written in either mode.

Prints one JSON object:
  {"ok": bool, "mode": "sync"|"check",
   "copies": [{"skill", "source", "dest", "state"}], "errors": [str]}

Run: uv run tools/sync_shared.py [--check] [--root <dir>]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = "shared.txt"
FILE_MODE = 0o644


@dataclass(frozen=True)
class Mapping:
    skill: str
    source: str  # as written, relative to tools/shared/
    dest: str  # as written, relative to the skill folder
    source_path: Path
    dest_path: Path


def _is_escaping(rel: str) -> bool:
    p = PurePosixPath(rel)
    return p.is_absolute() or rel.startswith("~") or ".." in p.parts


def _inside(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        return False
    return True


def parse_manifest(
    skill_dir: Path, shared_dir: Path, root: Path
) -> tuple[list[Mapping], list[str]]:
    """Parse and validate one skill's manifest. Returns (mappings, errors)."""
    manifest = skill_dir / MANIFEST
    label = manifest.relative_to(root).as_posix()
    mappings: list[Mapping] = []
    errors: list[str] = []
    seen: dict[str, int] = {}

    for lineno, raw in enumerate(manifest.read_text().splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        where = f"{label}:{lineno}"
        fields = line.split()
        if len(fields) != 2:
            errors.append(
                f"{where}: malformed line, expected '<source> <dest>', "
                f"got {len(fields)} field(s): {raw.strip()!r}"
            )
            continue
        source, dest = fields

        if _is_escaping(source):
            errors.append(f"{where}: source {source!r} must be relative to tools/shared/")
            continue
        source_path = shared_dir / source
        if not source_path.is_file() or not _inside(source_path, shared_dir):
            errors.append(
                f"{where}: skill {skill_dir.name}: source {source!r} does not exist "
                "in tools/shared/"
            )
            continue

        dest_path = skill_dir / dest
        if _is_escaping(dest) or not _inside(dest_path, skill_dir):
            errors.append(
                f"{where}: dest {dest!r} is outside the skill folder "
                "(absolute or using '..')"
            )
            continue
        if dest_path.resolve() == skill_dir.resolve():
            errors.append(f"{where}: dest {dest!r} names the skill folder itself")
            continue
        if dest_path.is_dir():
            errors.append(f"{where}: dest {dest!r} is a folder, not a file")
            continue

        key = PurePosixPath(os.path.normpath(dest)).as_posix()
        if key in seen:
            errors.append(
                f"{where}: duplicate dest {dest!r} (first listed on line {seen[key]})"
            )
            continue
        seen[key] = lineno

        mappings.append(Mapping(skill_dir.name, source, dest, source_path, dest_path))

    return mappings, errors


def copy_state(m: Mapping) -> str:
    if not m.dest_path.is_file():
        return "missing"
    if m.dest_path.read_bytes() != m.source_path.read_bytes():
        return "differs"
    return "ok"


def write_copy(m: Mapping) -> None:
    """Write the copy atomically, byte-for-byte, with the executable bit off."""
    m.dest_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=m.dest_path.parent, prefix=f".{m.dest_path.name}.")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(m.source_path.read_bytes())
        os.chmod(tmp, FILE_MODE)
        os.replace(tmp, m.dest_path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def run(root: Path, check: bool) -> tuple[dict, int]:
    mode = "check" if check else "sync"
    shared_dir = root / "tools" / "shared"
    skills_dir = root / "skills"
    copies: list[dict] = []
    errors: list[str] = []
    plan: list[Mapping] = []

    if not skills_dir.is_dir():
        errors.append(f"no skills folder at {skills_dir}")
    else:
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            if not (skill_dir / MANIFEST).is_file():
                copies.append(
                    {"skill": skill_dir.name, "source": None, "dest": None,
                     "state": "no-manifest"}
                )
                continue
            mappings, errs = parse_manifest(skill_dir, shared_dir, root)
            plan.extend(mappings)
            errors.extend(errs)

    if errors:
        # Invalid manifests: report and write nothing.
        return {"ok": False, "mode": mode, "copies": copies, "errors": errors}, 2

    drift = False
    for m in plan:
        state = copy_state(m)
        if state != "ok":
            if check:
                drift = True
            else:
                write_copy(m)
                state = "written"
        copies.append({"skill": m.skill, "source": m.source, "dest": m.dest, "state": state})

    copies.sort(key=lambda c: (c["skill"], c["dest"] or ""))
    return {"ok": not drift, "mode": mode, "copies": copies, "errors": []}, 1 if drift else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy tools/shared/ files into skills as listed in each shared.txt (AD-2)."
    )
    parser.add_argument(
        "--check", action="store_true",
        help="change nothing; exit 1 if any copy is missing or differs",
    )
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help="repo root holding skills/ and tools/shared/ (default: this repo)",
    )
    args = parser.parse_args(argv)
    result, code = run(args.root.resolve(), args.check)
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
