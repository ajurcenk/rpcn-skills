# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Check every skill folder against the base shape rules (AD-9, AD-10).

Each folder `skills/<skill>/` is checked, and each failure names its rule:

  name         the frontmatter `name` equals the folder name, which is
               `rpcn-<job>`: lower-case letters, digits and single hyphens,
               at most 64 characters
  clash        the name, or its part after `rpcn-`, is in tools/clash-list.txt
               (names lower-cased, `:` and `_` read as `-`)
  retired      the name is listed in retired.toml
  frontmatter  SKILL.md opens with YAML frontmatter that parses, has `name`
               and `description`, and uses only the spec keys
  description  at most 1,024 characters, has `Use when the user says "…"`
               with a quoted phrase, and every `use rpcn-<x>` names a skill
               that exists
  size         warning only: estimated tokens (characters / 4) above 1,200
  file-refs    every `references/…` and `scripts/…` path SKILL.md names
               exists, and references are one level deep; a reference file
               SKILL.md never names is a warning
  next         a `## Next` heading, with no `## Step` heading after it
  stray-files  no `__pycache__/`, `*.pyc` or `.DS_Store` inside the skill

Prints one JSON object:
  {"ok": bool,
   "skills": [{"skill", "errors": [{"rule", "message"}],
               "warnings": [{"rule", "message"}]}],
   "errors": [str]}

Exit 0 when no skill breaks a rule (warnings allowed), 1 when one does, and
2 when the validator can't run: tools/clash-list.txt or retired.toml is
missing or malformed, or skills/ is absent.

Run: uv run tools/validate_skills.py [--root <dir>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
CLASH_LIST = Path("tools") / "clash-list.txt"
RETIRED = Path("retired.toml")

PREFIX = "rpcn-"
MAX_NAME = 64
NAME_RE = re.compile(r"^rpcn-[a-z0-9]+(?:-[a-z0-9]+)*$")
SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
MAX_DESCRIPTION = 1024
MAX_TOKENS = 1200
CLASH_ENTRY_RE = re.compile(r"^[A-Za-z0-9:_-]+$")

USE_WHEN_RE = re.compile(r'Use when the user says\s+"[^"]+"')
SIBLING_RE = re.compile(r"\buse\s+(rpcn-[a-z0-9-]*[a-z0-9])", re.IGNORECASE)
# A path at the start of a word, or right after ${CLAUDE_SKILL_DIR}/; never a
# segment inside a longer path or URL.
REF_RE = re.compile(
    r"(?:(?<![\w./-])|(?<=\$\{CLAUDE_SKILL_DIR\}/))"
    r"((?:references|scripts)/[^\s`'\"()\[\],;:]*)"
)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
STRAY_DIRS = {"__pycache__"}
STRAY_FILES = {".DS_Store"}
STRAY_SUFFIXES = {".pyc"}


class SetupError(Exception):
    pass


def normalize(name: str) -> str:
    return name.lower().replace(":", "-").replace("_", "-")


def load_clash_list(root: Path) -> set[str]:
    path = root / CLASH_LIST
    if not path.is_file():
        raise SetupError(f"clash list {CLASH_LIST.as_posix()} is missing")
    names: set[str] = set()
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if not CLASH_ENTRY_RE.match(line):
            raise SetupError(
                f"{CLASH_LIST.as_posix()}:{lineno}: malformed entry {raw.strip()!r}, "
                "expected one name per line (letters, digits, '-', '_', ':')"
            )
        names.add(normalize(line))
    if not names:
        raise SetupError(f"clash list {CLASH_LIST.as_posix()} lists no names")
    return names


def load_retired(root: Path) -> set[str]:
    path = root / RETIRED
    if not path.is_file():
        raise SetupError(f"retired list {RETIRED.as_posix()} is missing")
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise SetupError(f"{RETIRED.as_posix()}: not valid TOML: {exc}") from exc
    extra = sorted(set(data) - {"retired"})
    if extra:
        raise SetupError(f"{RETIRED.as_posix()}: unknown top-level key(s) {extra}")
    entries = data.get("retired", [])
    if not isinstance(entries, list):
        raise SetupError(f"{RETIRED.as_posix()}: 'retired' must be an array of tables ([[retired]])")
    names: set[str] = set()
    for i, entry in enumerate(entries, start=1):
        where = f"{RETIRED.as_posix()}: [[retired]] #{i}"
        if not isinstance(entry, dict):
            raise SetupError(f"{where} is not a table")
        if not isinstance(entry.get("name"), str) or not entry["name"].strip():
            raise SetupError(f"{where} has no string 'name'")
        for key in ("replaced_by", "version"):
            if key in entry and not isinstance(entry[key], str):
                raise SetupError(f"{where}: '{key}' must be a string")
        unknown = sorted(set(entry) - {"name", "replaced_by", "version"})
        if unknown:
            raise SetupError(f"{where}: unknown key(s) {unknown}")
        names.add(normalize(entry["name"].strip()))
    return names


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter, body); frontmatter is None when there is none."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return None, text


def headings(body: str) -> list[tuple[int, str]]:
    """Markdown headings outside fenced code blocks, as (level, text)."""
    found: list[tuple[int, str]] = []
    fence: str | None = None
    for line in body.splitlines():
        m = FENCE_RE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            continue
        if fence is not None:
            continue
        h = HEADING_RE.match(line)
        if h:
            found.append((len(h.group(1)), h.group(2)))
    return found


class Report:
    def __init__(self, skill: str) -> None:
        self.skill = skill
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def error(self, rule: str, message: str) -> None:
        self.errors.append({"rule": rule, "message": message})

    def warn(self, rule: str, message: str) -> None:
        self.warnings.append({"rule": rule, "message": message})

    def as_dict(self) -> dict:
        return {"skill": self.skill, "errors": self.errors, "warnings": self.warnings}


def check_name(r: Report, folder: str, clash: set[str], retired: set[str]) -> None:
    if not folder.startswith(PREFIX):
        r.error("name", f"name {folder!r} does not start with {PREFIX!r}")
    elif folder != folder.lower():
        r.error("name", f"name {folder!r} has upper-case letters")
    elif len(folder) > MAX_NAME:
        r.error("name", f"name {folder!r} is {len(folder)} characters, over {MAX_NAME}")
    elif not NAME_RE.match(folder):
        r.error(
            "name",
            f"name {folder!r} must be 'rpcn-<job>': lower-case letters, digits "
            "and single hyphens",
        )

    full = normalize(folder)
    candidates = [full]
    if full.startswith(PREFIX) and len(full) > len(PREFIX):
        candidates.append(full[len(PREFIX):])
    for candidate in candidates:
        if candidate in clash:
            r.error(
                "clash",
                f"name {folder!r} clashes with {candidate!r} in {CLASH_LIST.as_posix()}",
            )
            break

    if full in retired:
        r.error("retired", f"name {folder!r} is retired in {RETIRED.as_posix()} and can't be reused")


def check_frontmatter(r: Report, folder: str, text: str) -> dict | None:
    raw, _ = split_frontmatter(text)
    if raw is None:
        if text.splitlines()[:1] == ["---"]:
            r.error("frontmatter", "SKILL.md frontmatter opens with '---' but is never closed")
        else:
            r.error("frontmatter", "SKILL.md does not open with '---' YAML frontmatter")
        return None
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        r.error("frontmatter", f"frontmatter is not valid YAML: {exc}".replace("\n", " "))
        return None
    if not isinstance(data, dict):
        r.error("frontmatter", "frontmatter is not a YAML mapping")
        return None
    for key in ("name", "description"):
        if key not in data:
            r.error("frontmatter", f"frontmatter has no {key!r}")
        elif not isinstance(data[key], str) or not data[key].strip():
            r.error("frontmatter", f"frontmatter {key!r} must be a non-empty string")
    extra = sorted(str(k) for k in set(data) - SPEC_KEYS)
    if extra:
        r.error(
            "frontmatter",
            f"frontmatter key(s) {extra} are outside the spec set {sorted(SPEC_KEYS)}",
        )
    name = data.get("name")
    if isinstance(name, str) and name != folder:
        r.error("name", f"frontmatter name {name!r} does not match folder {folder!r}")
    return data


def check_description(r: Report, description: str, skills: set[str]) -> None:
    if len(description) > MAX_DESCRIPTION:
        r.error(
            "description",
            f"description is {len(description)} characters, over {MAX_DESCRIPTION}",
        )
    if not USE_WHEN_RE.search(description):
        r.error(
            "description",
            'description has no \'Use when the user says "…"\' with a quoted phrase',
        )
    for m in SIBLING_RE.finditer(description):
        sibling = m.group(1).lower()
        if sibling not in skills:
            r.error("description", f"description says 'use {sibling}', but no skill {sibling!r} exists")


def check_size(r: Report, text: str) -> None:
    tokens = len(text) // 4
    if tokens > MAX_TOKENS:
        r.warn(
            "size",
            f"SKILL.md is about {tokens} tokens ({len(text)} characters / 4), "
            f"over {MAX_TOKENS}",
        )


def check_file_refs(r: Report, skill_dir: Path, text: str) -> None:
    named: set[str] = set()
    for m in REF_RE.finditer(text):
        ref = m.group(1).split("#", 1)[0].rstrip(".")
        if any(c in ref for c in "<>*{}$") or ref.endswith("/"):
            continue  # a pattern or a folder, not a file
        if ref in named:
            continue
        named.add(ref)
        parts = PurePosixPath(ref).parts
        if ".." in parts:
            r.error("file-refs", f"SKILL.md names {ref!r}, which leaves the skill folder")
            continue
        if parts[0] == "references" and len(parts) > 2:
            r.error("file-refs", f"SKILL.md names {ref!r}: references must be one level deep")
            continue
        if not (skill_dir / ref).is_file():
            r.error("file-refs", f"SKILL.md names {ref!r}, which does not exist")

    refs_dir = skill_dir / "references"
    if refs_dir.is_dir():
        for path in sorted(refs_dir.rglob("*")):
            rel = path.relative_to(skill_dir).as_posix()
            if path.is_dir():
                if path.name not in STRAY_DIRS:
                    r.error("file-refs", f"{rel}/ is nested: references must be one level deep")
                continue
            if path.name in STRAY_FILES or path.suffix in STRAY_SUFFIXES:
                continue  # reported by stray-files
            if path.parent != refs_dir:
                continue  # its folder is already reported
            if rel not in named:
                r.warn("file-refs", f"{rel} is never named in SKILL.md")


def check_next(r: Report, body: str) -> None:
    heads = headings(body)
    next_at = next(
        (i for i, (level, text) in enumerate(heads) if level == 2 and re.match(r"Next\b", text)),
        None,
    )
    if next_at is None:
        r.error("next", "SKILL.md has no '## Next' heading")
        return
    for level, text in heads[next_at + 1:]:
        if level == 2 and re.match(r"Step\b", text):
            r.error("next", f"'## {text}' comes after '## Next': Next must be the last step")


def check_stray(r: Report, skill_dir: Path) -> None:
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir).as_posix()
        if path.is_dir() and path.name in STRAY_DIRS:
            r.error("stray-files", f"{rel}/ must not be in the skill")
        elif path.is_file() and (path.name in STRAY_FILES or path.suffix in STRAY_SUFFIXES):
            if "__pycache__" in path.relative_to(skill_dir).parts[:-1]:
                continue  # its folder is already reported
            r.error("stray-files", f"{rel} must not be in the skill")


def check_skill(skill_dir: Path, clash: set[str], retired: set[str], skills: set[str]) -> Report:
    folder = skill_dir.name
    r = Report(folder)
    check_name(r, folder, clash, retired)
    check_stray(r, skill_dir)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        r.error("frontmatter", "the skill has no SKILL.md")
        return r
    text = skill_md.read_text(encoding="utf-8")
    _, body = split_frontmatter(text)

    data = check_frontmatter(r, folder, text)
    if data is not None and isinstance(data.get("description"), str):
        check_description(r, data["description"], skills)
    check_size(r, text)
    check_file_refs(r, skill_dir, body)
    check_next(r, body)
    return r


def run(root: Path) -> tuple[dict, int]:
    errors: list[str] = []
    clash: set[str] = set()
    retired: set[str] = set()
    for loader in (load_clash_list, load_retired):
        try:
            result = loader(root)
        except SetupError as exc:
            errors.append(str(exc))
            continue
        if loader is load_clash_list:
            clash = result
        else:
            retired = result

    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        errors.append(f"no skills folder at {skills_dir}")
    if errors:
        return {"ok": False, "skills": [], "errors": errors}, 2

    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    names = {p.name for p in skill_dirs}
    reports = [check_skill(p, clash, retired, names) for p in skill_dirs]
    failed = any(r.errors for r in reports)
    return {"ok": not failed, "skills": [r.as_dict() for r in reports], "errors": []}, 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check every skills/*/ folder against the base rules (AD-9, AD-10)."
    )
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT,
        help="repo root holding skills/, tools/clash-list.txt and retired.toml "
        "(default: this repo)",
    )
    args = parser.parse_args(argv)
    result, code = run(args.root.resolve())
    print(json.dumps(result, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
