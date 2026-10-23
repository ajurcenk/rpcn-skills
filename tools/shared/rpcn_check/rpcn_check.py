# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""rpcn_check: the only code that runs `rpk connect` (AD-2, AD-4).

Every subcommand prints one JSON envelope (schema 1, see SCHEMA.md) and exits
0 when ok, 1 when a check failed, 2 for a usage or environment error.

Canonical source: tools/shared/rpcn_check/rpcn_check.py. Copies inside
skills/*/scripts/ must stay byte-identical; edit the source, never a copy.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys

SCHEMA_VERSION = 1
PLUGIN_VERSION = "0.1.0"
REFS_VERSION: str | None = None  # set by the release stamp once references exist
MIN_VERSION_STR = "4.100.0"
VERSION_TIMEOUT_S = 10
LINT_TIMEOUT_S = 60
LINT_ARGS = ("lint", "--deprecated", "--skip-env-var-check")  # fixed by AD-4

EXIT_OK = 0
EXIT_CHECK_FAILED = 1
EXIT_ENV = 2

INSTALL_HINT = (
    "Install rpk (https://docs.redpanda.com/current/get-started/rpk-install/) and run "
    "`rpk connect install`, or put a `redpanda-connect` binary on PATH, or set "
    "RPCN_BINARY to its path."
)

_VERSION_RE = re.compile(r"^\s*Version:\s*v?(\d+)\.(\d+)\.(\d+)(\S*)\s*$", re.MULTILINE)
# Greedy file part: a path containing parentheses still splits on the last `(line,col)`.
_LINT_LINE_RE = re.compile(r"^(?P<file>.+)\((?P<line>\d+),(?P<col>\d+)\) (?P<message>.*)$")
_GLOB_CHARS = "\\*?[]{}"


class UsageError(Exception):
    """Bad command-line arguments."""


class EnvError(Exception):
    """The environment cannot run the check (binary missing, too old, ...)."""

    def __init__(self, message: str, binary: dict | None = None) -> None:
        super().__init__(message)
        self.binary = binary


class _ParserExit(Exception):
    """argparse wanted to exit (after --help); main returns this code."""

    def __init__(self, status: int) -> None:
        super().__init__(status)
        self.status = status


class _Parser(argparse.ArgumentParser):
    """stdout carries only JSON: help goes to stderr, and argparse never exits."""

    def error(self, message: str) -> None:
        raise UsageError(f"{message}\n{self.format_usage().strip()}")

    def print_help(self, file=None) -> None:
        super().print_help(sys.stderr if file is None else file)

    def print_usage(self, file=None) -> None:
        super().print_usage(sys.stderr if file is None else file)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            sys.stderr.write(message)
        raise _ParserExit(status)


def _error(message: str, file: str | None = None) -> dict:
    return {"file": file, "line": None, "column": None, "message": message}


def _envelope(command: str, ok: bool, binary: dict | None, errors: list, data: dict) -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "ok": ok,
        "command": command,
        "binary": binary,
        "errors": errors,
        "data": data,
    }


def _emit(env: dict, code: int) -> int:
    sys.stdout.write(json.dumps(env, indent=2) + "\n")
    return code


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip() == "1"


def is_headless() -> bool:
    return _truthy("RPCN_HEADLESS") or _truthy("EVAL_RPCN_HEADLESS")


def parse_version(text: str) -> str | None:
    """Return the version from a `Version:` line, without a leading `v`."""
    m = _VERSION_RE.search(text)
    if not m:
        return None
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}{m.group(4)}"


def _version_key(version: str) -> tuple[int, int, int, int]:
    """Sort key where a pre-release (`4.100.0-rc1`) sorts below its release."""
    major, minor, patch, suffix = re.match(r"(\d+)\.(\d+)\.(\d+)(\S*)", version).groups()
    return int(major), int(minor), int(patch), 0 if suffix.startswith("-") else 1


def _probe(argv: list[str]) -> tuple[str | None, str]:
    """Run `<argv> --version`; return (version or None, a short failure reason)."""
    try:
        proc = subprocess.run(
            [*argv, "--version"],
            capture_output=True,
            text=True,
            timeout=VERSION_TIMEOUT_S,
            check=False,
        )
    except FileNotFoundError:
        return None, "not found"
    except PermissionError:
        return None, "not executable"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {VERSION_TIMEOUT_S}s"
    except OSError as exc:
        return None, str(exc)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        return None, f"exited {proc.returncode}" + (f": {detail[-1]}" if detail else "")
    version = parse_version(proc.stdout) or parse_version(proc.stderr)
    if version is None:
        return None, "printed no `Version:` line"
    return version, ""


def _argv_for(path: str) -> list[str]:
    """`rpk` runs as `rpk connect`; anything else runs directly."""
    if os.path.basename(path) == "rpk":
        return [path, "connect"]
    return [path]


def find_binary() -> dict:
    """Resolve the binary by the AD-4 lookup order.

    Returns {"path", "version", "argv"}; raises EnvError when nothing usable is found.
    """
    for var in ("RPCN_BINARY", "EVAL_RPCN_BINARY"):
        override = os.environ.get(var, "").strip()
        if override:
            path = shutil.which(override) or override
            version, why = _probe(_argv_for(path))
            if version is None:
                raise EnvError(f"{var}={override} is not a usable Redpanda Connect binary ({why}). {INSTALL_HINT}")
            return {"path": path, "version": version, "argv": _argv_for(path)}

    rpk_note = ""
    rpk = shutil.which("rpk")
    if rpk:
        version, why = _probe([rpk, "connect"])
        if version is not None:
            return {"path": rpk, "version": version, "argv": [rpk, "connect"]}
        rpk_note = (
            f"`rpk connect --version` failed ({why}); run `rpk connect install` "
            "to add Redpanda Connect to rpk."
        )

    rpcn = shutil.which("redpanda-connect")
    if rpcn:
        version, why = _probe([rpcn])
        if version is not None:
            return {"path": rpcn, "version": version, "argv": [rpcn]}
        raise EnvError(
            " ".join(filter(None, [rpk_note, f"`{rpcn} --version` failed ({why}).", INSTALL_HINT]))
        )

    if rpk_note:
        raise EnvError(f"{rpk_note} No `redpanda-connect` on PATH either.")
    raise EnvError(f"No Redpanda Connect binary found: neither `rpk` nor `redpanda-connect` is on PATH. {INSTALL_HINT}")


def require_binary() -> dict:
    """find_binary plus the AD-5 version floor."""
    found = find_binary()
    public = {"path": found["path"], "version": found["version"]}
    if _version_key(found["version"]) < _version_key(MIN_VERSION_STR):
        raise EnvError(
            f"Redpanda Connect {found['version']} at {found['path']} is below the supported "
            f"floor {MIN_VERSION_STR}. Upgrade with `rpk connect upgrade` or "
            f"`rpk connect install --connect-version <version>`.",
            binary=public,
        )
    return found


def _newer_than_refs(version: str) -> bool:
    if REFS_VERSION is None:
        return False
    return _version_key(version) > _version_key(REFS_VERSION)


def cmd_binary(_args: argparse.Namespace) -> int:
    data = {
        "plugin_version": PLUGIN_VERSION,
        "refs_version": REFS_VERSION,
        "newer_than_refs": False,
        "headless": is_headless(),
    }
    try:
        found = require_binary()
    except EnvError as exc:
        return _emit(_envelope("binary", False, exc.binary, [_error(str(exc))], data), EXIT_ENV)
    data["newer_than_refs"] = _newer_than_refs(found["version"])
    binary = {"path": found["path"], "version": found["version"]}
    return _emit(_envelope("binary", True, binary, [], data), EXIT_OK)


def escape_glob(path: str) -> str:
    """Escape glob characters so the binary lints exactly this file, not a pattern."""
    return "".join("\\" + ch if ch in _GLOB_CHARS else ch for ch in path)


def parse_lint_output(text: str) -> list[dict]:
    """Turn `rpk connect lint` text into schema-1 errors, sorted by file, line, column.

    A line `<file>(<line>,<col>) <message>` becomes a file-bound error; any other
    non-empty line becomes an error with file, line and column null. Sorting makes
    the order the same on every RPCN version.
    """
    errors = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _LINT_LINE_RE.match(line)
        if m:
            errors.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col")),
                    "message": m.group("message"),
                }
            )
        else:
            errors.append(_error(line.strip()))
    errors.sort(
        key=lambda e: (
            e["file"] is None,
            e["file"] or "",
            e["line"] if e["line"] is not None else -1,
            e["column"] if e["column"] is not None else -1,
            e["message"],
        )
    )
    return errors


def _run_bounded(cmd: list[str], timeout: float, env: dict) -> tuple[int, str, str]:
    """Run cmd in its own process group; on timeout kill the whole group.

    Killing only the direct child could leave a grandchild (for example the
    Connect plugin started by `rpk`) holding the output pipes open.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.communicate()
        raise
    return proc.returncode, stdout, stderr


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def cmd_lint(args: argparse.Namespace) -> int:
    targets: list[str] = args.files
    resources = _unique(args.resources or [])
    env_file: str | None = args.env_file

    def result(ok: bool, binary: dict | None, errors: list, code: int, count: int = 0) -> int:
        return _emit(
            _envelope("lint", ok, binary, errors, {"files": targets, "error_count": count}), code
        )

    # Check files first: the binary reports a missing file as an ordinary lint
    # error (exit 1), which would hide "the check could not run" (exit 2).
    to_check = [("file", t) for t in targets] + [("resources file", r) for r in resources]
    if env_file:
        to_check.append(("env file", env_file))
    missing = [
        _error(f"{kind} not found: {path}", file=path)
        for kind, path in to_check
        if not os.path.exists(path)
    ]
    if missing:
        return result(False, None, missing, EXIT_ENV)

    try:
        found = require_binary()
    except EnvError as exc:
        return result(False, exc.binary, [_error(str(exc))], EXIT_ENV)
    binary = {"path": found["path"], "version": found["version"]}

    cmd = [*found["argv"], *LINT_ARGS]
    for res in resources:
        cmd += ["--resources", escape_glob(res)]
    if env_file:
        cmd += ["--env-file", env_file]
    cmd += [escape_glob(t) for t in _unique(targets)]

    try:
        returncode, stdout, stderr = _run_bounded(cmd, LINT_TIMEOUT_S, {**os.environ, "NO_COLOR": "1"})
    except subprocess.TimeoutExpired:
        return result(False, binary, [_error(f"lint timed out after {LINT_TIMEOUT_S}s")], EXIT_ENV)
    except OSError as exc:
        return result(False, binary, [_error(f"could not run lint: {exc}")], EXIT_ENV)

    errors = parse_lint_output(f"{stdout}\n{stderr}")
    if errors:
        return result(False, binary, errors, EXIT_CHECK_FAILED, len(errors))
    if returncode != 0:
        return result(
            False, binary, [_error(f"lint exited {returncode} with no output")], EXIT_ENV
        )
    return result(True, binary, [], EXIT_OK)


def build_parser() -> _Parser:
    parser = _Parser(
        prog="rpcn_check.py",
        description="Run Redpanda Connect checks and print one JSON envelope (schema 1).",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>", parser_class=_Parser)
    sub.required = True
    p_binary = sub.add_parser("binary", help="find the Redpanda Connect binary and report its version")
    p_binary.set_defaults(func=cmd_binary)
    p_lint = sub.add_parser("lint", help="lint pipeline config files")
    p_lint.add_argument("files", nargs="+", metavar="<file>", help="config files to lint")
    p_lint.add_argument(
        "--resources", action="append", metavar="<file>", help="resources file (repeatable)"
    )
    p_lint.add_argument("--env-file", metavar="<file>", help="dotenv file for interpolations")
    p_lint.set_defaults(func=cmd_lint)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    try:
        args, extra = parser.parse_known_args(argv)
        # `lint a.yaml --resources r.yaml b.yaml`: argparse leaves `b.yaml` over,
        # because positionals are taken in one run. Keep later file arguments.
        if extra and isinstance(getattr(args, "files", None), list) and not any(
            e.startswith("-") for e in extra
        ):
            args.files.extend(extra)
        elif extra:
            parser.error(f"unrecognized arguments: {' '.join(extra)}")
    except _ParserExit as exc:  # --help on any parser: help already on stderr
        return exc.status
    except UsageError as exc:
        command = argv[0] if argv and not argv[0].startswith("-") else ""
        return _emit(_envelope(command, False, None, [_error(str(exc))], {}), EXIT_ENV)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
