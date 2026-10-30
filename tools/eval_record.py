# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Shared helpers for eval records (R12, AD-14): the skills hash, and finding
and validating `evals/results/<YYYY-MM-DD>-<skills-hash12>.json` records.

The skills hash is the sha256 over every file under `skills/`, in sorted
repo-relative POSIX path order. Each file contributes

    <path> NUL <sha256 of its bytes, hex> LF

Only files git tracks or could track count: `git ls-files --cached --others
--exclude-standard` (nothing gitignored), and never anything under a
`__pycache__/` folder. Outside a git checkout it falls back to walking
`skills/`, skipping `__pycache__/` and `*.pyc`; inside a checkout
(the root has `.git`) a failing git command raises HashError instead. The hash depends only on paths
and content, never on mtimes or where the repo is checked out.

Used by tools/run_evals.py and tools/eval_record_check.py; not run on its own.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

SCHEMA = 1
SKILLS_DIR = "skills"
RESULTS_DIR = Path("evals") / "results"
PREFIX_LEN = 12
REPO_ROOT = Path(__file__).resolve().parent.parent


class HashError(Exception):
    """The skills hash cannot be computed (a git checkout where git fails)."""


class RecordError(Exception):
    """A record file that is unreadable, not JSON, or the wrong shape."""


def _excluded(rel: str) -> bool:
    parts = rel.split("/")
    return "__pycache__" in parts or rel.endswith(".pyc")


def _git(root: Path, *args: str) -> bytes:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    except OSError as exc:
        raise HashError(f"{root} is a git checkout but git cannot run: {exc}") from exc
    if out.returncode != 0:
        err = out.stderr.decode("utf-8", "replace").strip()
        raise HashError(f"git {' '.join(args)} failed in {root}: {err}")
    return out.stdout


def _git_files(root: Path) -> list[str] | None:
    """Tracked and trackable files under skills/, or None when root is not a git checkout.

    Raises HashError when root is a checkout (it has `.git`) but git fails, so
    the file set never silently changes.
    """
    if not (root / ".git").exists():
        return None
    top = _git(root, "rev-parse", "--show-toplevel").decode("utf-8", "surrogateescape").strip()
    if Path(top).resolve() != root.resolve():
        raise HashError(f"{root} has .git but git reports the checkout root {top}")
    out = _git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", SKILLS_DIR)
    names = {n.decode("utf-8", "surrogateescape") for n in out.split(b"\0") if n}
    # --cached also lists tracked files deleted from the working tree.
    return [n for n in names if (root / n).is_file()]


def _walk_files(root: Path) -> list[str]:
    base = root / SKILLS_DIR
    files = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            files.append((Path(dirpath) / name).relative_to(root).as_posix())
    return files


def skill_files(root: Path = REPO_ROOT) -> list[str]:
    """Sorted repo-relative POSIX paths of every file the skills hash covers."""
    files = _git_files(root)
    if files is None:
        files = _walk_files(root)
    return sorted(f for f in files if not _excluded(f))


def skills_hash(root: Path = REPO_ROOT) -> str:
    """The full sha256 hex digest of the skills content (see the module docstring)."""
    total = hashlib.sha256()
    for rel in skill_files(root):
        digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        total.update(rel.encode("utf-8", "surrogateescape") + b"\0" + digest.encode() + b"\n")
    return total.hexdigest()


def results_dir(root: Path = REPO_ROOT) -> Path:
    return root / RESULTS_DIR


def record_path(root: Path, date: str, full_hash: str) -> Path:
    return results_dir(root) / f"{date}-{full_hash[:PREFIX_LEN]}.json"


def load_record(path: Path) -> dict:
    """Parse and validate one record; raise RecordError naming the file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RecordError(f"{path}: cannot read: {exc.strerror or exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RecordError(f"{path}: not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RecordError(f"{path}: not a JSON object")
    schema = data.get("schema")
    if type(schema) is not int or schema != SCHEMA:
        raise RecordError(f"{path}: schema is {schema!r}, expected {SCHEMA}")
    if not isinstance(data.get("skills_hash"), str):
        raise RecordError(f"{path}: skills_hash missing or not a string")
    if type(data.get("passed")) is not bool:
        raise RecordError(f"{path}: passed missing or not true/false")
    return data


def candidate_records(root: Path, full_hash: str) -> list[Path]:
    """Record files whose name ends in the hash's 12-character prefix."""
    folder = results_dir(root)
    if not folder.is_dir():
        return []
    suffix = f"-{full_hash[:PREFIX_LEN]}.json"
    return sorted(p for p in folder.glob(f"*{suffix}") if p.is_file())


def find_passing(root: Path, full_hash: str) -> Path | None:
    """The newest passing record for exactly this hash, or None.

    Raises RecordError when any candidate (same 12-character prefix) is malformed.
    """
    found = None
    for path in candidate_records(root, full_hash):
        data = load_record(path)
        if data["skills_hash"] == full_hash and data["passed"] is True:
            found = path  # sorted by name, so the last one is the newest date
    return found
