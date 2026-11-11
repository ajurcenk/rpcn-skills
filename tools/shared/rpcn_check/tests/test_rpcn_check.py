# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Unit tests for rpcn_check.py, using fake binaries and a controlled PATH.

Run: uv run tools/shared/rpcn_check/tests/test_rpcn_check.py
No real Redpanda Connect binary is needed. The real-binary tests run only when
RPCN_TEST_BINARIES lists binary paths (separated by `:`), for example the ones
printed by `uv run tools/fetch_rpcn.py`; otherwise they are skipped.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "rpcn_check.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
FORMATS = Path(__file__).resolve().parents[2] / "formats"
FIXED_LINT_ARGS = ["lint", "--deprecated", "--skip-env-var-check"]
# Fake binaries run with a PATH holding only fakes, so they call these by path.
CAT = shutil.which("cat") or "/bin/cat"
SLEEP = shutil.which("sleep") or "/bin/sleep"


def write_exe(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text("#!/bin/sh\n" + textwrap.dedent(body))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def fake_rpk(directory: Path, version_line: str | None) -> Path:
    """An `rpk` whose `connect --version` prints version_line, or fails when None."""
    if version_line is None:
        body = """\
            echo "unknown command \\"connect\\" for \\"rpk\\"; run rpk connect install" >&2
            exit 1
            """
    else:
        body = f"""\
            if [ "$1" = "connect" ] && [ "$2" = "--version" ]; then
              echo "{version_line}"
              echo "Date: 2026-10-02T08:48:17Z"
              exit 0
            fi
            exit 1
            """
    return write_exe(directory, "rpk", body)


def fake_rpcn(directory: Path, version_line: str, name: str = "redpanda-connect") -> Path:
    body = f"""\
        if [ "$1" = "--version" ]; then
          echo "{version_line}"
          echo "Date: 2026-07-15T14:30:13Z"
          exit 0
        fi
        exit 1
        """
    return write_exe(directory, name, body)


class CheckTestBase(unittest.TestCase):
    """A temp PATH holding only fake binaries, and helpers to run the script."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.path_dir = root / "path"
        self.other_dir = root / "other"
        self.path_dir.mkdir()
        self.other_dir.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_check(
        self, *args: str, env: dict[str, str] | None = None, cwd: str | Path | None = None
    ) -> tuple[int, dict]:
        full_env = {"PATH": str(self.path_dir), "HOME": self._tmp.name}
        full_env.update(env or {})
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=full_env,
            timeout=60,
            cwd=cwd,
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not one JSON object:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        return proc.returncode, out

    def assertEnvelope(self, out: dict, command: str) -> None:
        self.assertEqual(
            set(out), {"schema", "ok", "command", "binary", "errors", "data"}, out
        )
        self.assertEqual(out["schema"], 1)
        self.assertEqual(out["command"], command)
        self.assertIsInstance(out["errors"], list)
        for err in out["errors"]:
            self.assertEqual(set(err), {"file", "line", "column", "message"})
            self.assertIsInstance(err["message"], str)

    def assertBinaryData(self, out: dict, headless: bool = False) -> None:
        self.assertEqual(
            out["data"],
            {
                "plugin_version": "0.1.0",
                "refs_version": None,
                "newer_than_refs": False,
                "headless": headless,
            },
        )


class RpcnCheckTest(CheckTestBase):
    """`binary` and the shared argument handling."""

    # --- matrix rows -------------------------------------------------------

    def test_rpk_present(self) -> None:
        rpk = fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check("binary")
        self.assertEqual(code, 0, out)
        self.assertEnvelope(out, "binary")
        self.assertTrue(out["ok"])
        self.assertEqual(out["binary"], {"path": str(rpk), "version": "4.112.0"})
        self.assertEqual(out["errors"], [])
        self.assertBinaryData(out)

    def test_override_wins_over_path(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        override = fake_rpcn(self.other_dir, "Version: v4.100.0")
        code, out = self.run_check("binary", env={"RPCN_BINARY": str(override)})
        self.assertEqual(code, 0, out)
        self.assertTrue(out["ok"])
        self.assertEqual(out["binary"], {"path": str(override), "version": "4.100.0"})

    def test_eval_override(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        override = fake_rpcn(self.other_dir, "Version: v4.105.1")
        code, out = self.run_check("binary", env={"EVAL_RPCN_BINARY": str(override)})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["binary"], {"path": str(override), "version": "4.105.1"})

    def test_rpcn_binary_beats_eval_override(self) -> None:
        first = fake_rpcn(self.other_dir, "Version: 4.101.0", name="first")
        second = fake_rpcn(self.other_dir, "Version: 4.102.0", name="second")
        code, out = self.run_check(
            "binary", env={"RPCN_BINARY": str(first), "EVAL_RPCN_BINARY": str(second)}
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(out["binary"]["path"], str(first))

    def test_override_to_rpk_runs_connect(self) -> None:
        rpk = fake_rpk(self.other_dir, "Version: 4.110.0")
        code, out = self.run_check("binary", env={"RPCN_BINARY": str(rpk)})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["binary"], {"path": str(rpk), "version": "4.110.0"})

    def test_broken_override_is_env_error(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check(
            "binary", env={"RPCN_BINARY": str(self.other_dir / "missing")}
        )
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertIn("RPCN_BINARY", out["errors"][0]["message"])

    def test_fallback_to_redpanda_connect(self) -> None:
        rpcn = fake_rpcn(self.path_dir, "Version: v4.100.0")
        code, out = self.run_check("binary")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["binary"], {"path": str(rpcn), "version": "4.100.0"})

    def test_too_old(self) -> None:
        rpk = fake_rpk(self.path_dir, "Version: 4.99.0")
        code, out = self.run_check("binary")
        self.assertEqual(code, 2, out)
        self.assertEnvelope(out, "binary")
        self.assertFalse(out["ok"])
        self.assertEqual(out["binary"], {"path": str(rpk), "version": "4.99.0"})
        self.assertIn("4.100.0", out["errors"][0]["message"])
        self.assertBinaryData(out)

    def test_missing(self) -> None:
        code, out = self.run_check("binary")
        self.assertEqual(code, 2, out)
        self.assertEnvelope(out, "binary")
        self.assertFalse(out["ok"])
        self.assertIsNone(out["binary"])
        message = out["errors"][0]["message"]
        self.assertIn("install", message.lower())
        self.assertIn("rpk connect install", message)

    def test_rpk_without_connect_falls_back(self) -> None:
        fake_rpk(self.path_dir, None)
        rpcn = fake_rpcn(self.path_dir, "Version: 4.104.0")
        code, out = self.run_check("binary")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["binary"], {"path": str(rpcn), "version": "4.104.0"})

    def test_rpk_without_connect_and_no_fallback(self) -> None:
        fake_rpk(self.path_dir, None)
        code, out = self.run_check("binary")
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertIsNone(out["binary"])
        self.assertIn("rpk connect install", out["errors"][0]["message"])

    def test_rpk_prints_help_when_connect_is_missing(self) -> None:
        # Real rpk (v26.2.2) with no Connect plugin on PATH: `rpk connect
        # --version` prints its usage text and exits 0, without downloading.
        write_exe(self.path_dir, "rpk", """\
            echo "Usage:"
            echo "  rpk connect [command]"
            exit 0
            """)
        code, out = self.run_check("binary")
        self.assertEqual(code, 2, out)
        self.assertIsNone(out["binary"])
        message = out["errors"][0]["message"]
        self.assertIn("`rpk connect --version` failed (printed no `Version:` line)", message)
        self.assertIn("rpk connect install", message)

    def test_headless_eval_var(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check("binary", env={"EVAL_RPCN_HEADLESS": "1"})
        self.assertEqual(code, 0, out)
        self.assertBinaryData(out, headless=True)

    def test_headless_rpcn_var(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check("binary", env={"RPCN_HEADLESS": "1"})
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["headless"])

    def test_headless_reported_when_binary_missing(self) -> None:
        code, out = self.run_check("binary", env={"RPCN_HEADLESS": "1"})
        self.assertEqual(code, 2, out)
        self.assertTrue(out["data"]["headless"])

    def test_headless_other_values_are_false(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check("binary", env={"RPCN_HEADLESS": "0"})
        self.assertEqual(code, 0, out)
        self.assertFalse(out["data"]["headless"])

    def test_unknown_subcommand(self) -> None:
        code, out = self.run_check("frobnicate")
        self.assertEqual(code, 2, out)
        self.assertEnvelope(out, "frobnicate")
        self.assertFalse(out["ok"])
        self.assertIsNone(out["binary"])
        self.assertIn("usage:", out["errors"][0]["message"])

    def test_no_subcommand(self) -> None:
        code, out = self.run_check()
        self.assertEqual(code, 2, out)
        self.assertEnvelope(out, "")
        self.assertIn("usage:", out["errors"][0]["message"])

    def test_too_old_prerelease_of_floor(self) -> None:
        rpk = fake_rpk(self.path_dir, "Version: 4.100.0-rc1")
        code, out = self.run_check("binary")
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertEqual(out["binary"], {"path": str(rpk), "version": "4.100.0-rc1"})
        self.assertIn("4.100.0", out["errors"][0]["message"])

    def run_raw(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env={"PATH": str(self.path_dir), "HOME": self._tmp.name},
            timeout=60,
        )

    def test_help_goes_to_stderr(self) -> None:
        for args in (["--help"], ["-h"], ["binary", "--help"], ["binary", "-h"]):
            with self.subTest(args=args):
                proc = self.run_raw(*args)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertIn("usage:", proc.stderr)

    def test_extra_argument(self) -> None:
        fake_rpk(self.path_dir, "Version: 4.112.0")
        code, out = self.run_check("binary", "--bogus")
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertIn("usage:", out["errors"][0]["message"])



def fake_lint_rpk(
    directory: Path,
    log_dir: Path,
    output: str = "",
    exit_code: int = 0,
    stream: str = "stderr",
    sleep: int = 0,
) -> Path:
    """An `rpk` at 4.112.0 whose `connect lint` prints canned output and exits exit_code.

    It writes its argv (one argument per line) to log_dir/argv and NO_COLOR to
    log_dir/no_color, so tests can assert exactly how it was called.
    """
    (log_dir / "output").write_text(output)
    redirect = ">&2" if stream == "stderr" else ""
    body = f"""\
        if [ "$1" = "connect" ] && [ "$2" = "--version" ]; then
          echo "Version: 4.112.0"
          exit 0
        fi
        : > "{log_dir}/argv"
        for a in "$@"; do printf '%s\\n' "$a" >> "{log_dir}/argv"; done
        printf '%s' "${{NO_COLOR-unset}}" > "{log_dir}/no_color"
        if [ {sleep} -gt 0 ]; then exec "{SLEEP}" {sleep}; fi
        "{CAT}" "{log_dir}/output" {redirect}
        exit {exit_code}
        """
    return write_exe(directory, "rpk", body)


class LintTest(CheckTestBase):
    """`lint` against a fake `rpk`: parsing, exit codes and the exact argv."""

    def setUp(self) -> None:
        super().setUp()
        self.work = Path(self._tmp.name) / "work"
        self.log = Path(self._tmp.name) / "log"
        self.work.mkdir()
        self.log.mkdir()

    def make(self, name: str, text: str = "input:\n  stdin: {}\n") -> str:
        path = self.work / name
        path.write_text(text)
        return str(path)

    def argv(self) -> list[str] | None:
        f = self.log / "argv"
        return f.read_text().splitlines() if f.exists() else None

    def lint(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        code, out = self.run_check("lint", *args, env=env)
        self.assertEnvelope(out, "lint")
        return code, out

    def test_valid(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        f = self.make("p.yaml")
        code, out = self.lint(f)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["ok"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["data"], {"files": [f], "error_count": 0})
        self.assertEqual(out["binary"]["version"], "4.112.0")

    def test_several_errors_sorted(self) -> None:
        f = self.make("p.yaml")
        output = (
            f"{f}(18,1) field wrong_key not recognised\n"
            f"{f}(5,1) field not_a_field not recognised\n"
            f"{f}(13,1) field bogus_option not recognised\n"
            f"{f}(9,29) required: expected method or field path\n"
        )
        fake_lint_rpk(self.path_dir, self.log, output, exit_code=1)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["ok"])
        self.assertEqual(
            [(e["file"], e["line"], e["column"]) for e in out["errors"]],
            [(f, 5, 1), (f, 9, 29), (f, 13, 1), (f, 18, 1)],
        )
        self.assertEqual(out["errors"][0]["message"], "field not_a_field not recognised")
        self.assertEqual(out["data"], {"files": [f], "error_count": 4})

    def test_errors_on_stdout_are_parsed_too(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{f}(2,1) component kafka is deprecated\n", 1, "stdout")
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["errors"][0]["message"], "component kafka is deprecated")

    def test_several_files_sorted_by_file(self) -> None:
        a, b = self.make("a.yaml"), self.make("b.yaml")
        output = f"{b}(3,1) field x not recognised\n{a}(1,1) yaml: line 1: did not find expected key\n"
        fake_lint_rpk(self.path_dir, self.log, output, exit_code=1)
        code, out = self.lint(b, a)
        self.assertEqual(code, 1, out)
        self.assertEqual([e["file"] for e in out["errors"]], [a, b])
        self.assertEqual(out["data"], {"files": [b, a], "error_count": 2})

    def test_unparsed_line_is_fileless_error(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, "something went wrong\n\n", exit_code=1)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"],
            [{"file": None, "line": None, "column": None, "message": "something went wrong"}],
        )
        self.assertEqual(out["data"]["error_count"], 1)

    def test_unparsed_lines_sort_after_file_errors(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"oops\n{f}(1,1) bad\n", exit_code=1)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual([e["file"] for e in out["errors"]], [f, None])

    def test_output_with_exit_zero_is_failure(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{f}(1,1) bad\n", exit_code=0)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["ok"])

    NOTICE = (
        "A new version of rpk is available (v25.3.1). To update, run:\n"
        "  rpk upgrade\n"
    )

    def test_notice_with_exit_zero_is_ok(self) -> None:
        f = self.make("p.yaml")
        for stream in ("stderr", "stdout"):
            with self.subTest(stream=stream):
                fake_lint_rpk(self.path_dir, self.log, self.NOTICE, exit_code=0, stream=stream)
                code, out = self.lint(f)
                self.assertEqual(code, 0, out)
                self.assertTrue(out["ok"])
                self.assertEqual(out["errors"], [])
                self.assertEqual(out["data"], {"files": [f], "error_count": 0})

    def test_notice_and_error_with_exit_zero_keeps_only_the_error(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{self.NOTICE}{f}(3,5) field x not recognised\n", 0)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"],
            [{"file": f, "line": 3, "column": 5, "message": "field x not recognised"}],
        )
        self.assertEqual(out["data"]["error_count"], 1)

    def test_notice_with_nonzero_exit_is_fileless_error(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, "A new version of rpk is available\n", exit_code=1)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"],
            [{"file": None, "line": None, "column": None,
              "message": "A new version of rpk is available"}],
        )

    def test_invalid_utf8_output(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, "", exit_code=1)
        (self.log / "output").write_bytes(f"{f}(1,1) bad\n".encode() + b"\xff\xfe not utf-8\n")
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["errors"][0]["line"], 1)
        self.assertIn("\ufffd", out["errors"][1]["message"])

    def test_duplicate_targets_linted_once(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{f}(1,1) bad\n", exit_code=1)
        code, out = self.lint(f, f)
        self.assertEqual(code, 1, out)
        self.assertEqual(self.argv(), ["connect", *FIXED_LINT_ARGS, f])
        self.assertEqual(out["data"], {"files": [f, f], "error_count": 1})

    def test_path_with_parentheses(self) -> None:
        f = self.make("p(1,2).yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{f}(7,3) field x not recognised\n", exit_code=1)
        code, out = self.lint(f)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"],
            [{"file": f, "line": 7, "column": 3, "message": "field x not recognised"}],
        )

    def test_silent_failure(self) -> None:
        f = self.make("p.yaml")
        fake_lint_rpk(self.path_dir, self.log, "", exit_code=3)
        code, out = self.lint(f)
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertIn("exited 3", out["errors"][0]["message"])

    def test_missing_target(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        good = self.make("p.yaml")
        missing = str(self.work / "nope.yaml")
        code, out = self.lint(good, missing)
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["errors"]), 1)
        self.assertEqual(out["errors"][0]["file"], missing)
        self.assertIn(missing, out["errors"][0]["message"])
        self.assertIsNone(self.argv(), "binary must not run")

    def test_missing_resources_file(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        f = self.make("p.yaml")
        missing = str(self.work / "res.yaml")
        code, out = self.lint(f, "--resources", missing)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["errors"][0]["file"], missing)
        self.assertIsNone(self.argv(), "binary must not run")

    def test_missing_env_file(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        f = self.make("p.yaml")
        missing = str(self.work / ".env")
        code, out = self.lint(f, "--env-file", missing)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["errors"][0]["file"], missing)
        self.assertIsNone(self.argv(), "binary must not run")

    def test_no_targets(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        code, out = self.lint()
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertIn("usage:", out["errors"][0]["message"])
        self.assertIsNone(self.argv())

    def test_no_binary(self) -> None:
        f = self.make("p.yaml")
        code, out = self.lint(f)
        self.assertEqual(code, 2, out)
        self.assertIsNone(out["binary"])
        self.assertIn("rpk connect install", out["errors"][0]["message"])

    def test_old_binary(self) -> None:
        rpk = fake_rpk(self.path_dir, "Version: 4.99.0")
        f = self.make("p.yaml")
        code, out = self.lint(f)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["binary"], {"path": str(rpk), "version": "4.99.0"})
        self.assertIn("4.100.0", out["errors"][0]["message"])

    def test_flags_exact(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        a, b = self.make("a.yaml"), self.make("b.yaml")
        r1, r2 = self.make("r1.yaml"), self.make("r2.yaml")
        env = self.make(".env", "LIMIT=3\n")
        code, out = self.lint(
            a, "--resources", r1, "--env-file", env, "--resources", r2, b, "--resources", r1
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(
            self.argv(),
            ["connect", *FIXED_LINT_ARGS, "--resources", r1, "--resources", r2, "--env-file", env, a, b],
        )
        self.assertEqual(out["data"]["files"], [a, b])
        self.assertEqual((self.log / "no_color").read_text(), "1")

    def test_flags_minimal(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        f = self.make("p.yaml")
        code, out = self.lint(f)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.argv(), ["connect", *FIXED_LINT_ARGS, f])

    def test_redpanda_connect_runs_without_connect(self) -> None:
        f = self.make("p.yaml")
        body = f"""\
            if [ "$1" = "--version" ]; then echo "Version: v4.100.0"; exit 0; fi
            for a in "$@"; do printf '%s\\n' "$a" >> "{self.log}/argv"; done
            exit 0
            """
        write_exe(self.path_dir, "redpanda-connect", body)
        code, out = self.lint(f)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.argv(), [*FIXED_LINT_ARGS, f])

    def test_glob_characters_escaped(self) -> None:
        f = self.make("a[1].yaml")
        star = self.make("b*?{x}.yaml")
        fake_lint_rpk(self.path_dir, self.log, f"{f}(5,1) field x not recognised\n", exit_code=1)
        code, out = self.lint(f, star)
        self.assertEqual(code, 1, out)
        work = str(self.work)
        self.assertEqual(
            self.argv()[-2:], [f"{work}/a\\[1\\].yaml", f"{work}/b\\*\\?\\{{x\\}}.yaml"]
        )
        self.assertEqual(out["errors"][0]["file"], f)
        self.assertEqual(out["data"]["files"], [f, star])

    def test_never_passes_banned_flags(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        f = self.make("p.yaml")
        self.lint(f, "--resources", self.make("r.yaml"))
        for banned in ("-v", "--verbose", "-", "--chilled"):
            self.assertNotIn(banned, self.argv())

    def test_unknown_lint_flag(self) -> None:
        fake_lint_rpk(self.path_dir, self.log)
        code, out = self.lint(self.make("p.yaml"), "--verbose")
        self.assertEqual(code, 2, out)
        self.assertIn("usage:", out["errors"][0]["message"])
        self.assertIsNone(self.argv())

    def test_timeout(self) -> None:
        """Runs in-process with a 1 s timeout instead of the real 60 s."""
        fake_lint_rpk(self.path_dir, self.log, sleep=30)
        f = self.make("p.yaml")
        spec = importlib.util.spec_from_file_location("rpcn_check_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.LINT_TIMEOUT_S = 1
        out_buf = io.StringIO()
        saved = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update({"PATH": str(self.path_dir), "HOME": self._tmp.name})
            with contextlib.redirect_stdout(out_buf):
                code = module.main(["lint", f])
        finally:
            os.environ.clear()
            os.environ.update(saved)
        out = json.loads(out_buf.getvalue())
        self.assertEqual(code, 2, out)
        self.assertEnvelope(out, "lint")
        self.assertFalse(out["ok"])
        self.assertIn("timed out", out["errors"][0]["message"])
        self.assertEqual(module.LINT_TIMEOUT_S, 1)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def handoff(
    inputs: list[tuple[str, str]] | None = None,
    artifact: str = "test-report",
    fmt: str = "test-report@2",
    status: str = "ready",
    body: str = "# orders: test report\n",
) -> str:
    lines = [
        "---",
        f"artifact: {artifact}",
        f"format: {fmt}",
        "pipeline: orders",
        f"status: {status}",
        "produced_by: rpcn-test@0.1.0",
        "rpcn_version: 4.115.0",
    ]
    if inputs:
        lines.append("inputs:")
        for file, digest in inputs:
            lines += [f"  - file: {file}", f"    sha256: {digest}"]
    else:
        lines.append("inputs: []")
    lines += ["updated: 2026-10-23", "---", ""]
    return "\n".join(lines) + body


def doc_examples(doc: Path) -> dict[str, str]:
    """The `<!-- example-file: NAME -->` fenced blocks of a format doc, by file name."""
    pattern = re.compile(r"^<!-- example-file: (\S+) -->\n(`{3,})\w*\n(.*?)^\2$", re.M | re.S)
    return {m.group(1): m.group(3) for m in pattern.finditer(doc.read_text())}


class HashTest(CheckTestBase):
    """`hash`: file hashes and the hand-off check. The PATH holds no binary at all."""

    PIPE = "input:\n  stdin: {}\n"

    def setUp(self) -> None:
        super().setUp()
        self.work = Path(self._tmp.name) / "work"
        self.work.mkdir()

    def write(self, name: str, text: str) -> Path:
        path = self.work / name
        path.write_text(text)
        return path

    def hash(self, *args: str, cwd: str | Path | None = None) -> tuple[int, dict]:
        code, out = self.run_check("hash", *args, cwd=cwd)
        self.assertEnvelope(out, "hash")
        self.assertIsNone(out["binary"])
        self.assertEqual(out["ok"], code == 0, out)
        return code, out

    def check(self, report: Path, cwd: str | Path | None = None) -> tuple[int, dict]:
        return self.hash("--check", str(report), cwd=cwd)

    def assertBadHeader(self, text: str, line: int, fragment: str) -> None:
        report = self.write("orders.test-report.md", text)
        code, out = self.check(report)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {})
        self.assertEqual(len(out["errors"]), 1, out)
        err = out["errors"][0]
        self.assertEqual(err["file"], str(report))
        self.assertEqual(err["line"], line, err)
        self.assertIn(fragment, err["message"])

    # --- hash <file>... ------------------------------------------------------

    def test_hash_files_in_order(self) -> None:
        a = self.write("a.yaml", "a: 1\n")
        b = self.write("b.yaml", "b: 2\n")
        code, out = self.hash(str(b), str(a))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["errors"], [])
        self.assertEqual(
            out["data"],
            {"hashes": [{"file": str(b), "sha256": sha("b: 2\n")},
                        {"file": str(a), "sha256": sha("a: 1\n")}]},
        )

    def test_hash_relative_path_as_given(self) -> None:
        self.write("a.yaml", "a: 1\n")
        code, out = self.hash("a.yaml", cwd=self.work)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["hashes"], [{"file": "a.yaml", "sha256": sha("a: 1\n")}])

    def test_hash_missing_file(self) -> None:
        a = self.write("a.yaml", "a: 1\n")
        missing = str(self.work / "nope.yaml")
        code, out = self.hash(str(a), missing)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {"hashes": []})
        self.assertEqual([e["file"] for e in out["errors"]], [missing])
        self.assertIn(missing, out["errors"][0]["message"])

    def test_hash_folder_is_not_a_file(self) -> None:
        code, out = self.hash(str(self.work))
        self.assertEqual(code, 2, out)
        self.assertIn("not a file", out["errors"][0]["message"])

    def test_hash_needs_arguments(self) -> None:
        code, out = self.hash()
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {})

    def test_hash_files_and_check_together(self) -> None:
        a = self.write("a.yaml", "a: 1\n")
        code, out = self.hash(str(a), "--check", str(a))
        self.assertEqual(code, 2, out)
        self.assertIn("not both", out["errors"][0]["message"])

    # --- hash --check: the matrix --------------------------------------------

    def test_fresh_report(self) -> None:
        self.write("orders.yaml", self.PIPE)
        report = self.write("orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))]))
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["errors"], [])
        self.assertEqual(
            out["data"],
            {
                "artifact": "test-report",
                "status": "ready",
                "format": "test-report@2",
                "format_known": True,
                "inputs": [{"file": "orders.yaml", "recorded": sha(self.PIPE),
                            "current": sha(self.PIPE), "state": "match"}],
                "ready": True,
                "verdict": None,
                "pipeline_ready": False,
            },
        )

    def test_stale_report(self) -> None:
        self.write("orders.yaml", self.PIPE)
        report = self.write("orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))]))
        changed = self.PIPE + "output:\n  stdout: {}\n"
        self.write("orders.yaml", changed)
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertEqual(
            out["data"]["inputs"],
            [{"file": "orders.yaml", "recorded": sha(self.PIPE), "current": sha(changed),
              "state": "changed"}],
        )
        self.assertEqual(out["errors"][0]["file"], str(self.work / "orders.yaml"))
        self.assertIn("changed", out["errors"][0]["message"])

    def test_input_deleted(self) -> None:
        report = self.write("orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))]))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertEqual(out["data"]["inputs"][0]["state"], "missing")
        self.assertIsNone(out["data"]["inputs"][0]["current"])

    def test_draft(self) -> None:
        self.write("orders.yaml", self.PIPE)
        report = self.write(
            "orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))], status="draft")
        )
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertEqual(out["data"]["status"], "draft")
        self.assertEqual(out["data"]["inputs"][0]["state"], "match")
        self.assertEqual(out["errors"][0]["line"], 5)

    def test_superseded(self) -> None:
        report = self.write("orders.test-report.md", handoff(status="superseded"))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])

    def test_old_major_still_read(self) -> None:
        """test-report@1 (no Dry run section) stays readable after the bump to @2."""
        self.write("orders.yaml", self.PIPE)
        body = "# orders: test report\n\n## Summary\n\n**Verdict:** pass\n"
        report = self.write(
            "orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))], fmt="test-report@1", body=body)
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["format_known"])
        self.assertTrue(out["data"]["pipeline_ready"])

    def test_design_major_2_unknown(self) -> None:
        report = self.write("orders.design.md", handoff(artifact="design", fmt="design@2"))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["format_known"])

    def test_unknown_major(self) -> None:
        self.write("orders.yaml", self.PIPE)
        report = self.write(
            "orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))], fmt="test-report@3")
        )
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["format_known"])
        self.assertFalse(out["data"]["ready"])
        self.assertEqual(out["errors"][0]["line"], 3)

    def test_unknown_artifact(self) -> None:
        report = self.write("orders.capacity.md", handoff(artifact="capacity", fmt="capacity@1"))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["artifact"], "capacity")
        self.assertFalse(out["data"]["format_known"])

    def test_format_naming_another_artifact(self) -> None:
        report = self.write("orders.test-report.md", handoff(fmt="design@1"))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["format_known"])

    def test_malformed_format_is_unknown(self) -> None:
        report = self.write("orders.test-report.md", handoff(fmt="test-report"))
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["format_known"])

    def test_known_design_format(self) -> None:
        report = self.write("orders.design.md", handoff(artifact="design", fmt="design@1"))
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["format_known"])

    def test_no_inputs(self) -> None:
        # A design may have no inputs; a test report must start with its pipeline.
        report = self.write("orders.design.md", handoff(artifact="design", fmt="design@1"))
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["inputs"], [])
        for status in ("ready", "draft"):
            with self.subTest(status=status):
                report = self.write("orders.test-report.md", handoff(status=status))
                code, out = self.check(report)
                self.assertEqual(code, 1, out)
                self.assertEqual(out["data"]["inputs"], [])
                self.assertFalse(out["data"]["ready"])
                self.assertFalse(out["data"]["pipeline_ready"])
                inputs_err = [e for e in out["errors"] if "first input" in e["message"]]
                self.assertEqual(len(inputs_err), 1, out)
                self.assertEqual(inputs_err[0]["line"], 8)
                self.assertEqual(inputs_err[0]["file"], str(report))
                self.assertIn("inputs is empty", inputs_err[0]["message"])

    def test_test_report_first_input_must_be_pipeline(self) -> None:
        self.write("orders.yaml", self.PIPE)
        self.write("resources.yaml", "cache_resources: []\n")
        for first in ("resources.yaml", "pipes/orders.yaml", "orders.json"):
            with self.subTest(first=first):
                inputs = [(first, sha("x\n")), ("orders.yaml", sha(self.PIPE))]
                report = self.write(
                    "orders.test-report.md", handoff(inputs, body="**Verdict:** pass\n")
                )
                code, out = self.check(report)
                self.assertEqual(code, 1, out)
                self.assertFalse(out["data"]["ready"])
                self.assertFalse(out["data"]["pipeline_ready"])
                inputs_err = [e for e in out["errors"] if "first input" in e["message"]]
                self.assertEqual(len(inputs_err), 1, out)
                self.assertEqual(inputs_err[0]["line"], 8)
                self.assertIn(repr(first), inputs_err[0]["message"])

    def test_test_report_first_input_normalised(self) -> None:
        self.write("orders.yaml", self.PIPE)
        report = self.write(
            "orders.test-report.md",
            handoff([("./orders.yaml", sha(self.PIPE))], body="**Verdict:** pass\n"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["pipeline_ready"])

    def test_shared_resources_input_changed(self) -> None:
        (self.work / "pipes").mkdir()
        self.write("pipes/orders.yaml", self.PIPE)
        self.write("resources.yaml", "cache_resources: []\n")
        report = self.write(
            "pipes/orders.test-report.md",
            handoff([("orders.yaml", sha(self.PIPE)),
                     ("../resources.yaml", sha("cache_resources: []\n"))],
                    body="**Verdict:** pass\n"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["pipeline_ready"])
        self.write("resources.yaml", "cache_resources: [{label: c, memory: {}}]\n")
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertFalse(out["data"]["pipeline_ready"])
        self.assertEqual([i["state"] for i in out["data"]["inputs"]], ["match", "changed"])

    def test_bare_inputs_key_with_no_items(self) -> None:
        text = handoff(artifact="design", fmt="design@1").replace("inputs: []", "inputs:")
        report = self.write("orders.design.md", text)
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["inputs"], [])

    def test_several_inputs_one_changed(self) -> None:
        self.write("orders.yaml", self.PIPE)
        self.write("orders.design.md", "design\n")
        report = self.write(
            "orders.test-report.md",
            handoff([("orders.yaml", sha(self.PIPE)), ("orders.design.md", sha("old\n"))]),
        )
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertEqual([i["state"] for i in out["data"]["inputs"]], ["match", "changed"])

    def test_relative_paths_resolve_against_handoff_folder(self) -> None:
        self.write("orders.yaml", self.PIPE)
        (self.work / "res").mkdir()
        self.write("res/shared.yaml", "cache_resources: []\n")
        report = self.write(
            "orders.test-report.md",
            handoff([("orders.yaml", sha(self.PIPE)),
                     ("res/shared.yaml", sha("cache_resources: []\n"))]),
        )
        # Run from another folder that has its own, different orders.yaml.
        (self.other_dir / "orders.yaml").write_text("something else\n")
        code, out = self.check(report, cwd=self.other_dir)
        self.assertEqual(code, 0, out)
        self.assertEqual([i["state"] for i in out["data"]["inputs"]], ["match", "match"])
        # And with the hand-off given as a relative path.
        code, out = self.hash("--check", "work/orders.test-report.md", cwd=self._tmp.name)
        self.assertEqual(code, 0, out)

    def test_quoted_values(self) -> None:
        self.write("orders.yaml", self.PIPE)
        text = handoff([("orders.yaml", sha(self.PIPE))]).replace("status: ready", "status: 'ready'").replace(
            "format: test-report@2", 'format: "test-report@2"'
        )
        report = self.write("orders.test-report.md", text)
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["format"], "test-report@2")

    def test_body_after_header_is_ignored(self) -> None:
        self.write("orders.yaml", self.PIPE)
        text = handoff([("orders.yaml", sha(self.PIPE))]) + "\n---\nartifact: nonsense\n"
        report = self.write("orders.test-report.md", text)
        code, out = self.check(report)
        self.assertEqual(code, 0, out)

    # --- hash --check: verdict and pipeline_ready (decision B) --------------

    def report_with_verdict(self, verdict_line: str | None) -> Path:
        self.write("orders.yaml", self.PIPE)
        body = "# orders: test report\n\n## Summary\n\n"
        if verdict_line is not None:
            body += verdict_line + "\n"
        return self.write(
            "orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))], body=body)
        )

    def test_verdict_pass_pipeline_ready(self) -> None:
        code, out = self.check(self.report_with_verdict("**Verdict:** pass"))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["verdict"], "pass")
        self.assertTrue(out["data"]["pipeline_ready"])

    def test_verdict_fail_report_ready_pipeline_not(self) -> None:
        code, out = self.check(self.report_with_verdict("**Verdict:** fail"))
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["ready"])
        self.assertEqual(out["data"]["verdict"], "fail")
        self.assertFalse(out["data"]["pipeline_ready"])

    def test_verdict_absent(self) -> None:
        for line in (None, "**Verdict:** maybe", "Verdict: pass"):
            with self.subTest(line=line):
                code, out = self.check(self.report_with_verdict(line))
                self.assertEqual(code, 0, out)
                self.assertIsNone(out["data"]["verdict"])
                self.assertFalse(out["data"]["pipeline_ready"])

    def test_verdict_stale_pipeline(self) -> None:
        report = self.report_with_verdict("**Verdict:** pass")
        self.write("orders.yaml", self.PIPE + "output:\n  stdout: {}\n")
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["verdict"], "pass")
        self.assertFalse(out["data"]["pipeline_ready"])

    def test_verdict_without_pipeline_input(self) -> None:
        self.write("other.yaml", self.PIPE)
        report = self.write(
            "orders.test-report.md",
            handoff([("other.yaml", sha(self.PIPE))], body="**Verdict:** pass\n"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertFalse(out["data"]["pipeline_ready"])
        self.assertEqual(out["errors"][0]["line"], 8)
        self.assertIn("first input", out["errors"][0]["message"])

    def test_verdict_pass_yml_pipeline_ready(self) -> None:
        self.write("orders.yml", self.PIPE)
        report = self.write(
            "orders.test-report.md",
            handoff([("orders.yml", sha(self.PIPE))], body="**Verdict:** pass\n"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["ready"])
        self.assertTrue(out["data"]["pipeline_ready"])

    def test_design_with_yml_pipeline_input(self) -> None:
        self.write("orders.yml", self.PIPE)
        report = self.write(
            "orders.design.md",
            handoff([("orders.yml", sha(self.PIPE))], artifact="design", fmt="design@1"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["ready"])

    def test_verdict_only_for_test_reports(self) -> None:
        report = self.write(
            "orders.design.md",
            handoff(artifact="design", fmt="design@1", body="**Verdict:** pass\n"),
        )
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertIsNone(out["data"]["verdict"])
        self.assertFalse(out["data"]["pipeline_ready"])

    @unittest.skipIf(os.geteuid() == 0, "root can read any file")
    def test_unreadable_input(self) -> None:
        pipe = self.write("orders.yaml", self.PIPE)
        report = self.write("orders.test-report.md", handoff([("orders.yaml", sha(self.PIPE))]))
        pipe.chmod(0)
        try:
            code, out = self.check(report)
        finally:
            pipe.chmod(0o644)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {})
        self.assertEqual(out["errors"][0]["file"], str(pipe))
        self.assertIn("cannot read", out["errors"][0]["message"])

    # --- hash --check: bad headers (exit 2, with the line) -------------------

    def test_missing_handoff(self) -> None:
        missing = str(self.work / "orders.test-report.md")
        code, out = self.check(Path(missing))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {})
        self.assertEqual(out["errors"][0]["file"], missing)
        self.assertIn("not found", out["errors"][0]["message"])

    def test_no_frontmatter(self) -> None:
        self.assertBadHeader("# orders: test report\n", 1, "no frontmatter")

    def test_empty_file(self) -> None:
        self.assertBadHeader("", 1, "no frontmatter")

    def test_unclosed_frontmatter(self) -> None:
        text = handoff().split("\n---\n")[0] + "\n"
        self.assertBadHeader(text, 9, "not closed")

    def test_input_item_bad_indent(self) -> None:
        text = handoff([("orders.yaml", sha(self.PIPE))]).replace(
            "  - file: orders.yaml", "   - file: orders.yaml"
        )
        self.assertBadHeader(text, 9, "inputs")

    def test_input_item_without_sha(self) -> None:
        text = handoff([("orders.yaml", sha(self.PIPE))]).replace(
            f"    sha256: {sha(self.PIPE)}\n", ""
        )
        self.assertBadHeader(text, 10, "sha256")

    def test_input_item_flow_style(self) -> None:
        text = handoff().replace(
            "inputs: []", "inputs: [{file: orders.yaml, sha256: " + sha(self.PIPE) + "}]"
        )
        self.assertBadHeader(text, 8, "inputs")

    def test_bad_hash(self) -> None:
        for bad in ("abc", sha(self.PIPE).upper(), sha(self.PIPE)[:-1] + "g"):
            with self.subTest(hash=bad):
                self.assertBadHeader(handoff([("orders.yaml", bad)]), 10, "sha256")

    def test_absolute_input_path(self) -> None:
        text = handoff([(str(self.work / "orders.yaml"), sha(self.PIPE))])
        self.assertBadHeader(text, 9, "relative")

    def test_unknown_key(self) -> None:
        text = handoff().replace("pipeline: orders", "pipeline: orders\nowner: me")
        self.assertBadHeader(text, 5, "unknown key")

    def test_duplicate_key(self) -> None:
        text = handoff().replace("pipeline: orders", "pipeline: orders\npipeline: other")
        self.assertBadHeader(text, 5, "duplicate")

    def test_missing_key(self) -> None:
        text = handoff().replace("rpcn_version: 4.115.0\n", "")
        self.assertBadHeader(text, 9, "rpcn_version")

    def test_bad_status(self) -> None:
        self.assertBadHeader(handoff(status="done"), 5, "status")

    def test_not_key_value(self) -> None:
        text = handoff().replace("pipeline: orders", "pipeline orders")
        self.assertBadHeader(text, 4, "key: value")

    def test_empty_value(self) -> None:
        text = handoff().replace("pipeline: orders", "pipeline:")
        self.assertBadHeader(text, 4, "no value")

    # --- the format docs' examples ------------------------------------------

    def test_doc_example_report_is_ready_then_stale(self) -> None:
        report_ex = doc_examples(FORMATS / "test-report-format.md")
        design_ex = doc_examples(FORMATS / "design-format.md")
        self.assertEqual(set(report_ex), {"orders.yaml", "orders.test-report.md"})
        self.assertEqual(set(design_ex), {"orders.design.md"})
        for name, text in {**report_ex, **design_ex}.items():
            self.write(name, text)

        code, out = self.check(self.work / "orders.test-report.md")
        self.assertEqual(code, 0, out)
        self.assertTrue(out["data"]["ready"])
        self.assertEqual(out["data"]["verdict"], "pass")
        self.assertTrue(out["data"]["pipeline_ready"])
        self.assertEqual(
            [(i["file"], i["state"]) for i in out["data"]["inputs"]],
            [("orders.yaml", "match"), ("orders.design.md", "match")],
        )
        code, out = self.check(self.work / "orders.design.md")
        self.assertEqual(code, 0, out)

        self.write("orders.yaml", report_ex["orders.yaml"].replace("max_in_flight: 8", "max_in_flight: 1"))
        code, out = self.check(self.work / "orders.test-report.md")
        self.assertEqual(code, 1, out)
        self.assertFalse(out["data"]["ready"])
        self.assertEqual(out["data"]["inputs"][0]["state"], "changed")
        self.assertFalse(out["data"]["pipeline_ready"])

    def test_header_doc_example_matches_report_example(self) -> None:
        report = doc_examples(FORMATS / "test-report-format.md")["orders.test-report.md"]
        header = report.split("\n---\n", 1)[0] + "\n---\n"
        self.assertIn(header, (FORMATS / "handoff-header.md").read_text())



# --- blobl, list, fields, run, test: fake binary ------------------------------

_FAKE_TOOL = """\
import json, os, re, sys, time
log = sys.argv[1]
args = sys.argv[2:]
if args[:2] == ["connect", "--version"]:
    print("Version: 4.112.0")
    sys.exit(0)
stdin = "" if sys.stdin is None or sys.stdin.closed else sys.stdin.read()
with open(os.path.join(log, "calls.jsonl"), "a") as fh:
    input_text = None
    if "--input" in args:
        with open(args[args.index("--input") + 1]) as inp:
            input_text = inp.read()
    fh.write(json.dumps({"argv": args, "stdin": stdin, "input_text": input_text,
                         "no_color": os.environ.get("NO_COLOR")}) + "\\n")
with open(os.path.join(log, "spec.json")) as fh:
    spec = json.load(fh)
joined = " ".join(args[1:])
for rule in spec:
    if re.search(rule["match"], joined):
        for stream, text in rule.get("out", []):
            out = sys.stdout if stream == "O" else sys.stderr
            out.write(text)
            out.flush()
        if rule.get("echo_stdin"):
            sys.stdout.write(stdin)
            sys.stdout.flush()
        if rule.get("sleep"):
            time.sleep(rule["sleep"])
        sys.exit(rule.get("exit", 0))
sys.stderr.write("fake: no rule for " + joined + "\\n")
sys.exit(99)
"""


def fake_tool_rpk(directory: Path, log_dir: Path, spec: list[dict]) -> Path:
    """An `rpk` at 4.112.0 that answers `connect <...>` from spec rules.

    Each rule is {"match": regex on the args after `connect`, "out": [["O"|"E",
    text], ...], "exit": int, "sleep": seconds, "echo_stdin": bool}; the first
    match wins. Every call is logged to log_dir/calls.jsonl with argv, stdin
    and NO_COLOR.
    """
    (log_dir / "spec.json").write_text(json.dumps(spec))
    script = log_dir / "fake_tool.py"
    script.write_text(_FAKE_TOOL)
    return write_exe(directory, "rpk", f'exec "{sys.executable}" -I "{script}" "{log_dir}" "$@"\n')


def _json_full(category: str, components: list[dict]) -> str:
    return json.dumps({"version": "4.112.0", "date": "x", "config": [], category: components, "outputs": []})


GENERATE_JSON_FULL = {
    "name": "generate",
    "type": "input",
    "status": "stable",
    "config": {
        "name": "",
        "type": "object",
        "kind": "scalar",
        "children": [
            {"name": "mapping", "type": "string", "kind": "scalar", "description": "A mapping.\nMore text.", "bloblang": True},
            {"name": "interval", "type": "string", "kind": "scalar", "description": "The interval.", "default": "1s"},
            {"name": "count", "type": "int", "kind": "scalar", "description": "", "default": 0, "is_advanced": True},
            {"name": "label", "type": "string", "kind": "scalar", "description": "x", "is_optional": True},
        ],
    },
}
NESTED_JSON_FULL = {
    "name": "http_client",
    "type": "input",
    "status": "beta",
    "config": {
        "type": "object",
        "kind": "scalar",
        "children": [
            {"name": "url", "type": "string", "kind": "scalar", "description": "URL"},
            {
                "name": "tls", "type": "object", "kind": "scalar", "description": "TLS", "is_advanced": True,
                "children": [
                    {"name": "enabled", "type": "bool", "kind": "scalar", "description": "On", "default": False},
                    {
                        "name": "client_certs", "type": "object", "kind": "array", "default": [],
                        "children": [
                            {"name": "password", "type": "string", "kind": "scalar", "default": "", "is_secret": True},
                        ],
                    },
                ],
            },
            {
                "name": "headers", "type": "object", "kind": "map",
                "children": [{"name": "value", "type": "string", "kind": "scalar", "is_deprecated": True}],
            },
        ],
    },
}


# Answers the unfiltered `list --format json` that `list` and `fields` use to check the category.
CATEGORIES_RULE = {
    "match": "^list --format json$",
    "out": [["O", json.dumps({"inputs": [], "outputs": [], "processors": []})]],
}


class ToolCheckBase(CheckTestBase):
    def setUp(self) -> None:
        super().setUp()
        self.work = Path(self._tmp.name) / "work"
        self.log = Path(self._tmp.name) / "log"
        self.work.mkdir()
        self.log.mkdir()

    def make(self, name: str, text: str = "x\n") -> str:
        path = self.work / name
        path.write_text(text)
        return str(path)

    def fake(self, *rules: dict) -> None:
        fake_tool_rpk(self.path_dir, self.log, [*rules, CATEGORIES_RULE])

    def run_in_process(self, *args: str, **constants: object) -> tuple[int, dict]:
        """Run main() in-process with module constants overridden (for short timeouts)."""
        spec = importlib.util.spec_from_file_location("rpcn_check_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, value in constants.items():
            setattr(module, name, value)
        out_buf = io.StringIO()
        saved = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update({"PATH": str(self.path_dir), "HOME": self._tmp.name})
            with contextlib.redirect_stdout(out_buf):
                code = module.main(list(args))
        finally:
            os.environ.clear()
            os.environ.update(saved)
        out = json.loads(out_buf.getvalue())
        self.assertEnvelope(out, args[0])
        return code, out

    def calls(self) -> list[dict]:
        f = self.log / "calls.jsonl"
        return [json.loads(line) for line in f.read_text().splitlines()] if f.exists() else []

    def cmd(self, command: str, *args: str) -> tuple[int, dict]:
        code, out = self.run_check(command, *args)
        self.assertEnvelope(out, command)
        self.assertEqual(out["ok"], code == 0, out)
        return code, out

    def assertNoForbiddenFlags(self) -> None:
        for call in self.calls():
            for flag in ("-v", "--verbose", "-", "--chilled"):
                self.assertNotIn(flag, call["argv"])
            self.assertEqual(call["no_color"], "1")


class BloblTest(ToolCheckBase):
    def test_ok(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", '{"doubled":2}\n']]})
        m = self.make("double.blobl", "root.doubled = this.n * 2\n")
        i = self.make("one.jsonl", '{"n":1}\n')
        code, out = self.cmd("blobl", m, "--input", i)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out["data"], {"mapping": m, "results": [{"line": 1, "output": '{"doubled":2}', "error": None}]}
        )
        self.assertEqual(self.calls()[0]["argv"], ["connect", "blobl", "--file", m, "--input", i])
        self.assertNoForbiddenFlags()

    def test_bad_line(self) -> None:
        self.fake(
            {
                "match": "^blobl",
                "out": [
                    ["O", '{"doubled":2}\n'],
                    ["E", "failed to execute map: parse as json: invalid character\n"],
                    ["O", '{"doubled":6}\n'],
                ],
            }
        )
        m = self.make("double.blobl")
        i = self.make("samples.jsonl", '{"n":1}\nnotjson\n{"n":3}\n')
        code, out = self.cmd("blobl", m, "--input", i)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["data"]["results"],
            [
                {"line": 1, "output": '{"doubled":2}', "error": None},
                {"line": 2, "output": None, "error": "parse as json: invalid character"},
                {"line": 3, "output": '{"doubled":6}', "error": None},
            ],
        )
        self.assertEqual(
            out["errors"],
            [{"file": i, "line": 2, "column": None, "message": "parse as json: invalid character"}],
        )

    def test_bad_mapping(self) -> None:
        self.fake(
            {
                "match": "^blobl",
                "out": [["E", "failed to parse mapping: line 2 char 1: required: expected query\n  |\n2 | x\n  | ^---\n"]],
                "exit": 1,
            }
        )
        m = self.make("bad.blobl")
        code, out = self.cmd("blobl", m)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"], [{"file": m, "line": 2, "column": 1, "message": "required: expected query"}]
        )
        self.assertEqual(out["data"], {"mapping": m, "results": []})

    def test_no_input_stdin_empty(self) -> None:
        self.fake({"match": "^blobl", "out": []})
        m = self.make("double.blobl")
        env = self.make("x.env", "A=1\n")
        code, out = self.cmd("blobl", m, "--env-file", env)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["results"], [])
        call = self.calls()[0]
        self.assertEqual(call["argv"], ["connect", "blobl", "--env-file", env, "--file", m])
        self.assertEqual(call["stdin"], "")

    def test_multiline_output_falls_back_to_one_run_per_line(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", "a\nb\n"]]})
        m = self.make("nl.blobl")
        # The fake prints two lines per run, so three input lines cannot be matched by position.
        i = self.make("three.jsonl", '{"n":1}\n{"n":2}\n{"n":3}')
        code, out = self.cmd("blobl", m, "--input", i)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out["data"]["results"],
            [{"line": n, "output": "a\nb", "error": None} for n in (1, 2, 3)],
        )
        calls = self.calls()
        self.assertEqual(len(calls), 4)
        self.assertEqual([c["stdin"] for c in calls[1:]], ['{"n":1}\n', '{"n":2}\n', '{"n":3}\n'])
        self.assertNotIn("--input", calls[1]["argv"])

    def test_fallback_shares_one_budget(self) -> None:
        """The first run and the per-line re-runs share one CHECK_TIMEOUT_S budget."""
        self.fake({"match": "^blobl", "out": [["O", "a\nb\n"]], "sleep": 1.2})
        m = self.make("nl.blobl")
        i = self.make("one.jsonl", '{"n":1}\n')
        started = time.monotonic()
        code, out = self.run_in_process("blobl", m, "--input", i, CHECK_TIMEOUT_S=2)
        self.assertLess(time.monotonic() - started, 3.5)
        self.assertEqual(code, 2, out)
        self.assertIn("timed out after 2s", out["errors"][0]["message"])

    def test_fallback_nonzero_exit_is_line_error(self) -> None:
        self.fake(
            {"match": "^blobl --file \\S+ --input", "out": [["O", "a\nb\n"]]},
            {"match": "^blobl", "out": [["E", "panic: boom\n"]], "exit": 2},
        )
        m = self.make("nl.blobl")
        i = self.make("one.jsonl", '{"n":1}\n')
        code, out = self.cmd("blobl", m, "--input", i)
        self.assertEqual(code, 1, out)
        result = out["data"]["results"][0]
        self.assertIsNone(result["output"])
        self.assertIn("exited 2", result["error"])
        self.assertIn("panic: boom", result["error"])
        self.assertEqual((out["errors"][0]["file"], out["errors"][0]["line"]), (i, 1))

    def test_silent_failure(self) -> None:
        self.fake({"match": "^blobl", "exit": 3})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m)
        self.assertEqual(code, 2, out)
        self.assertIn("exited 3 with no output", out["errors"][0]["message"])
        self.assertEqual(out["errors"][0]["file"], m)

    def test_missing_files(self) -> None:
        self.fake({"match": "^blobl"})
        m = self.make("double.blobl")
        for args in ([str(self.work / "nope.blobl")], [m, "--input", str(self.work / "no.jsonl")],
                     [m, "--env-file", str(self.work / "no.env")]):
            with self.subTest(args=args):
                code, out = self.cmd("blobl", *args)
                self.assertEqual(code, 2, out)
                self.assertIsNone(out["binary"])
                self.assertIn("not found", out["errors"][0]["message"])
                self.assertTrue(out["errors"][0]["file"].startswith(str(self.work)))
        self.assertEqual(self.calls(), [], "binary must not run")


def _load_module():
    spec = importlib.util.spec_from_file_location("rpcn_check_samples", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _samples_doc(samples: list | None = None, key: str = "m.blobl", **top: object) -> dict:
    doc = {
        "format": "samples@1",
        "pipeline": "orders",
        "mappings": {key: samples if samples is not None else [{"name": "one", "input": {"n": 1}, "output": {"d": 2}}]},
    }
    doc.update(top)
    return doc


class ParseSamplesTest(unittest.TestCase):
    """parse_samples: the samples-format.md parser (story 2.7)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.m = _load_module()

    def bad(self, text: str, fragment: str, line: int | None = None) -> None:
        with self.assertRaises(self.m.SamplesError) as ctx:
            self.m.parse_samples(text)
        self.assertIn(fragment, str(ctx.exception))
        self.assertEqual(ctx.exception.line, line)

    def bad_doc(self, doc: object, fragment: str) -> None:
        self.bad(json.dumps(doc), fragment)

    def test_doc_example_parses(self) -> None:
        ex = doc_examples(FORMATS / "samples-format.md")
        self.assertEqual(set(ex), {"orders.enrich.blobl", "orders.samples.json"})
        doc = self.m.parse_samples(ex["orders.samples.json"])
        self.assertEqual(doc["pipeline"], "orders")
        self.assertEqual(list(doc["mappings"]), ["orders.enrich.blobl"])
        self.assertEqual(len(doc["mappings"]["orders.enrich.blobl"]), 2)

    def test_deleted_sample(self) -> None:
        doc = self.m.parse_samples(json.dumps(_samples_doc([{"name": "drop", "input": 1, "deleted": True}])))
        self.assertTrue(doc["mappings"]["m.blobl"][0]["deleted"])

    def test_any_json_input_and_output(self) -> None:
        samples = [{"name": f"s{i}", "input": v, "output": v} for i, v in enumerate(["x", 0, None, [1], False])]
        self.m.parse_samples(json.dumps(_samples_doc(samples)))

    def test_syntax_error_names_the_line(self) -> None:
        self.bad('{\n  "format": "samples@1",\n  "pipeline": \n}\n', "not valid JSON", line=4)

    def test_not_an_object(self) -> None:
        self.bad("[]", "one JSON object")

    def test_top_level_keys(self) -> None:
        self.bad_doc(_samples_doc(extra=1), "extra: unknown key")
        doc = _samples_doc()
        del doc["pipeline"]
        self.bad_doc(doc, "pipeline: required key is missing")
        self.bad_doc(_samples_doc(format="samples@2"), "format: must be 'samples@1'")
        self.bad_doc(_samples_doc(pipeline=" "), "pipeline: must be a non-empty string")
        self.bad_doc(_samples_doc(mappings={}), "mappings: must be a non-empty object")
        self.bad_doc(_samples_doc(mappings=[]), "mappings: must be a non-empty object")

    def test_mapping_keys(self) -> None:
        for key in ("pipes/m.blobl", "m.yaml", ".blobl", "a\\m.blobl"):
            with self.subTest(key=key):
                self.bad_doc(_samples_doc(key=key), "must be a bare .blobl file name")
        self.bad_doc(_samples_doc([]), 'mappings["m.blobl"]: must be a non-empty array')
        self.bad_doc(_samples_doc(key="m.blobl", mappings={"m.blobl": {}}), "non-empty array")

    def test_sample_rules(self) -> None:
        cases = [
            (["x"], '[0]: must be an object'),
            ([{"name": "a", "input": 1, "output": 1, "meta": {}}], "[0].meta: unknown key"),
            ([{"input": 1, "output": 1}], "[0].name: must be a non-empty string"),
            ([{"name": "", "input": 1, "output": 1}], "[0].name: must be a non-empty string"),
            ([{"name": "a", "input": 1, "output": 1}, {"name": "a", "input": 2, "output": 2}],
             "[1].name: 'a' is used twice"),
            ([{"name": "a", "output": 1}], "[0].input: required key is missing"),
            ([{"name": "a", "input": 1}], "[0]: needs exactly one of output and deleted"),
            ([{"name": "a", "input": 1, "output": 1, "deleted": True}], "needs exactly one of output and deleted"),
            ([{"name": "a", "input": 1, "deleted": False}], "[0].deleted: must be true"),
        ]
        for samples, fragment in cases:
            with self.subTest(fragment=fragment):
                self.bad_doc(_samples_doc(samples), fragment)

    def test_nan_and_infinity_rejected(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                text = json.dumps(_samples_doc()).replace('"output": {"d": 2}', f'"output": {{"d": {constant}}}')
                self.assertIn(constant, text)
                self.bad(text, f'mappings["m.blobl"][0].output.d: {constant} is not a JSON value')

    def test_repeated_key(self) -> None:
        self.bad('{"format": "samples@1", "format": "samples@1", "pipeline": "p", "mappings": {}}',
                 "duplicate key 'format'")

    def test_json_equal(self) -> None:
        eq = self.m.json_equal
        self.assertTrue(eq({"a": 1, "b": [1.0, "x"]}, {"b": [1, "x"], "a": 1.0}))
        self.assertFalse(eq(True, 1))
        self.assertFalse(eq(1, True))
        self.assertFalse(eq("1", 1))
        self.assertFalse(eq({"a": 1}, {"a": 1, "b": None}))
        self.assertFalse(eq([1, 2], [2, 1]))
        self.assertTrue(eq(None, None))
        self.assertFalse(eq(None, 0))


class BloblSamplesTest(ToolCheckBase):
    """`blobl --samples`: run a mapping's samples and compare (fake binary)."""

    def samples(self, doc: dict, name: str = "orders.samples.json") -> str:
        return self.make(name, json.dumps(doc))

    def test_all_pass(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", '{"d":2}\n'], ["O", '{"d":4}\n']]})
        m = self.make("m.blobl")
        s = self.samples(_samples_doc([
            {"name": "one", "input": {"n": 1, "a": "x"}, "output": {"d": 2.0}},
            {"name": "two", "input": {"n": 2}, "output": {"d": 4}},
        ]))
        code, out = self.cmd("blobl", m, "--samples", s)
        self.assertEqual(code, 0, out)
        data = out["data"]
        self.assertEqual((data["mapping"], data["samples_file"], data["passed"], data["failed"]), (m, s, 2, 0))
        self.assertEqual(data["samples"][0], {
            "name": "one", "input": '{"a":"x","n":1}', "expected": '{"d":2.0}', "deleted": False,
            "actual": '{"d":2}', "error": None, "result": "pass",
        })
        self.assertEqual([r["line"] for r in data["results"]], [1, 2])
        call = self.calls()[0]
        self.assertEqual(call["argv"][:4], ["connect", "blobl", "--file", m])
        self.assertEqual(call["argv"][4], "--input")
        self.assertEqual(call["input_text"], '{"a":"x","n":1}\n{"n":2}\n')
        self.assertFalse(os.path.exists(call["argv"][5]), "the temp input file is removed")
        self.assertNoForbiddenFlags()

    def test_mismatch_names_expected_and_actual(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", '{"d":3}\n'], ["O", '{"d":4}\n']]})
        m = self.make("m.blobl")
        s = self.samples(_samples_doc([
            {"name": "one", "input": {"n": 1}, "output": {"d": 2}},
            {"name": "two", "input": {"n": 2}, "output": {"d": 4}},
        ]))
        before = Path(s).read_bytes()
        code, out = self.cmd("blobl", m, "--samples", s)
        self.assertEqual(code, 1, out)
        self.assertEqual((out["data"]["passed"], out["data"]["failed"]), (1, 1))
        first = out["data"]["samples"][0]
        self.assertEqual((first["expected"], first["actual"], first["result"]), ('{"d":2}', '{"d":3}', "fail"))
        self.assertEqual(out["errors"], [
            {"file": s, "line": None, "column": None, "message": "sample 'one': expected {\"d\":2}, got {\"d\":3}"}
        ])
        self.assertEqual(Path(s).read_bytes(), before, "the samples file is never changed")

    def test_bool_is_not_a_number(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", "1\n"]]})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--samples", self.samples(_samples_doc(
            [{"name": "flag", "input": {}, "output": True}])))
        self.assertEqual(code, 1, out)

    def test_raw_string_output(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", "hello world\n"]]})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--samples", self.samples(_samples_doc(
            [{"name": "greet", "input": {}, "output": "hello world"}])))
        self.assertEqual(code, 0, out)

    def test_string_expected_compares_the_raw_text(self) -> None:
        """A string root prints without quotes, so "123", "true" and JSON text compare as printed."""
        self.fake({"match": "^blobl", "out": [["O", "123\n"], ["O", "true\n"], ["O", '{"a":1}\n'],
                                               ["O", "123\n"], ["O", '{"a": 1}\n']]})
        m = self.make("m.blobl")
        s = self.samples(_samples_doc([
            {"name": "digits", "input": {}, "output": "123"},
            {"name": "word true", "input": {}, "output": "true"},
            {"name": "json text", "input": {}, "output": '{"a":1}'},
            {"name": "number", "input": {}, "output": 123},
            {"name": "json text spaced differently", "input": {}, "output": '{"a":1}'},
        ]))
        code, out = self.cmd("blobl", m, "--samples", s)
        self.assertEqual(code, 1, out)
        self.assertEqual([e["result"] for e in out["data"]["samples"]], ["pass", "pass", "pass", "pass", "fail"])
        self.assertEqual(out["data"]["samples"][0]["expected"], '"123"')

    def test_deleted(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", "\n"], ["O", '{"a":1}\n'], ["O", "\n"]]})
        m = self.make("m.blobl")
        s = self.samples(_samples_doc([
            {"name": "dropped", "input": {"x": 1}, "deleted": True},
            {"name": "kept but should drop", "input": {"x": 2}, "deleted": True},
            {"name": "dropped but should keep", "input": {"x": 3}, "output": {"a": 1}},
        ]))
        code, out = self.cmd("blobl", m, "--samples", s)
        self.assertEqual(code, 1, out)
        self.assertEqual([e["result"] for e in out["data"]["samples"]], ["pass", "fail", "fail"])
        self.assertIsNone(out["data"]["samples"][0]["expected"])
        self.assertTrue(out["data"]["samples"][0]["deleted"])
        messages = [e["message"] for e in out["errors"]]
        self.assertIn("expected the message deleted", messages[0])
        self.assertIn("got a deleted message", messages[1])

    def test_line_error_is_a_failed_sample(self) -> None:
        self.fake({"match": "^blobl", "out": [["E", "failed to execute map: expected number value\n"]]})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--samples", self.samples(_samples_doc()))
        self.assertEqual(code, 1, out)
        entry = out["data"]["samples"][0]
        self.assertEqual((entry["actual"], entry["error"], entry["result"]), (None, "expected number value", "fail"))
        self.assertEqual(out["errors"][0]["message"], "sample 'one': expected number value")

    def test_mapping_that_does_not_parse_is_a_check_failure(self) -> None:
        self.fake({"match": "^blobl", "out": [["E", "failed to parse mapping: line 2 char 1: required: expected query\n"]],
                   "exit": 1})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--samples", self.samples(_samples_doc()))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["errors"], [{"file": m, "line": 2, "column": 1, "message": "required: expected query"}])
        self.assertEqual((out["data"]["samples"], out["data"]["passed"], out["data"]["failed"]), ([], 0, 0))

    def test_mapping_matched_by_file_name(self) -> None:
        self.fake({"match": "^blobl", "out": [["O", '{"d":2}\n']]})
        sub = self.work / "pipes"
        sub.mkdir()
        m = sub / "orders.enrich.blobl"
        m.write_text("x\n")
        s = self.samples(_samples_doc(key="orders.enrich.blobl"))
        code, out = self.cmd("blobl", str(m), "--samples", s)
        self.assertEqual(code, 0, out)

    def test_no_entry_for_the_mapping(self) -> None:
        self.fake({"match": "^blobl"})
        m = self.make("other.blobl")
        s = self.samples(_samples_doc())
        code, out = self.cmd("blobl", m, "--samples", s)
        self.assertEqual(code, 2, out)
        self.assertIn("no samples for 'other.blobl'", out["errors"][0]["message"])
        self.assertIn("m.blobl", out["errors"][0]["message"])
        self.assertEqual(out["errors"][0]["file"], s)
        self.assertEqual(self.calls(), [], "binary must not run")

    def test_invalid_samples_file(self) -> None:
        self.fake({"match": "^blobl"})
        m = self.make("m.blobl")
        cases = [
            ('{"format": "samples@1",\n "pipeline": "p",\n "mappings": {,}}\n', 3, "not valid JSON"),
            (json.dumps(_samples_doc([{"name": "a", "input": 1}])), None, 'mappings["m.blobl"][0]: needs exactly one'),
        ]
        for text, line, fragment in cases:
            with self.subTest(fragment=fragment):
                s = self.make("bad.samples.json", text)
                code, out = self.cmd("blobl", m, "--samples", s)
                self.assertEqual(code, 2, out)
                self.assertIsNone(out["binary"])
                self.assertEqual(len(out["errors"]), 1)
                err = out["errors"][0]
                self.assertEqual((err["file"], err["line"]), (s, line))
                self.assertIn(fragment, err["message"])
                self.assertEqual(out["data"], {"mapping": m, "results": [], "samples_file": s,
                                               "samples": [], "passed": 0, "failed": 0})
        self.make("latin.samples.json", "")
        (self.work / "latin.samples.json").write_bytes(b'{"pipeline": "\xff"}')
        code, out = self.cmd("blobl", m, "--samples", str(self.work / "latin.samples.json"))
        self.assertEqual(code, 2, out)
        self.assertIn("cannot read samples file", out["errors"][0]["message"])
        self.assertEqual(self.calls(), [], "binary must not run")

    def test_missing_samples_file(self) -> None:
        self.fake({"match": "^blobl"})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--samples", str(self.work / "nope.samples.json"))
        self.assertEqual(code, 2, out)
        self.assertIn("samples file not found", out["errors"][0]["message"])
        self.assertEqual(self.calls(), [])

    def test_input_and_samples_together_is_usage_error(self) -> None:
        self.fake({"match": "^blobl"})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m, "--input", self.make("i.jsonl"), "--samples", self.samples(_samples_doc()))
        self.assertEqual(code, 2, out)
        self.assertEqual(out["data"], {})
        self.assertIn("not allowed with argument", out["errors"][0]["message"])

    def test_without_samples_the_shape_is_unchanged(self) -> None:
        self.fake({"match": "^blobl", "out": []})
        m = self.make("m.blobl")
        code, out = self.cmd("blobl", m)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"], {"mapping": m, "results": []})


class ListTest(ToolCheckBase):
    def test_list(self) -> None:
        self.fake({"match": "inputs$", "out": [["O", json.dumps({"inputs": ["generate", "stdin"]})]]})
        code, out = self.cmd("list", "inputs")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"], {"category": "inputs", "components": ["generate", "stdin"]})
        self.assertEqual(self.calls()[-1]["argv"], ["connect", "list", "--format", "json", "inputs"])
        self.assertNoForbiddenFlags()

    def test_status(self) -> None:
        self.fake({"match": "inputs$", "out": [["O", json.dumps({"inputs": ["subprocess"]})]]})
        code, out = self.cmd("list", "inputs", "--status", "beta")
        self.assertEqual(code, 0, out)
        self.assertEqual(
            self.calls()[-1]["argv"], ["connect", "list", "--format", "json", "--status", "beta", "inputs"]
        )

    def test_valid_category_absent_from_filtered_output(self) -> None:
        self.fake({"match": "--status experimental outputs$", "out": [["O", "{}"]]})
        code, out = self.cmd("list", "outputs", "--status", "experimental")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"], {"category": "outputs", "components": []})
        self.assertEqual(self.calls()[0]["argv"], ["connect", "list", "--format", "json"])

    def test_bad_status_is_usage_error(self) -> None:
        self.fake({"match": "."})
        code, out = self.run_check("list", "inputs", "--status", "nope")
        self.assertEqual(code, 2, out)
        self.assertEqual(self.calls(), [])

    def test_bad_category(self) -> None:
        self.fake(
            {"match": "nope$", "out": [["O", "{}"]]},
            {"match": "json$", "out": [["O", json.dumps({"inputs": [], "outputs": []})]]},
        )
        code, out = self.cmd("list", "nope")
        self.assertEqual(code, 2, out)
        self.assertIn("unknown category 'nope'", out["errors"][0]["message"])
        self.assertIn("inputs, outputs", out["errors"][0]["message"])
        self.assertEqual(out["data"], {"category": "nope", "components": []})

    def test_invalid_json(self) -> None:
        self.fake({"match": ".", "out": [["O", "not json"]]})
        code, out = self.cmd("list", "inputs")
        self.assertEqual(code, 2, out)
        self.assertIn("invalid JSON", out["errors"][0]["message"])


class FieldsTest(ToolCheckBase):
    def test_known(self) -> None:
        self.fake({"match": "json-full inputs$", "out": [["O", _json_full("inputs", [GENERATE_JSON_FULL])]]})
        code, out = self.cmd("fields", "inputs", "generate")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["category"], "inputs")
        self.assertEqual(out["data"]["component"], "generate")
        self.assertEqual(out["data"]["status"], "stable")
        f = {x["path"]: x for x in out["data"]["fields"]}
        self.assertEqual(
            f["mapping"],
            {"path": "mapping", "type": "string", "kind": "scalar", "required": True,
             "advanced": False, "deprecated": False, "secret": False, "description": "A mapping."},
        )
        self.assertEqual(f["interval"]["default"], "1s")
        self.assertFalse(f["interval"]["required"])
        self.assertEqual(f["count"]["default"], 0)
        self.assertTrue(f["count"]["advanced"])
        self.assertFalse(f["label"]["required"])
        self.assertNotIn("default", f["label"])
        self.assertEqual(
            self.calls()[-1]["argv"], ["connect", "list", "--format", "json-full", "inputs"]
        )

    def test_nested(self) -> None:
        self.fake({"match": "json-full inputs$", "out": [["O", _json_full("inputs", [NESTED_JSON_FULL])]]})
        code, out = self.cmd("fields", "inputs", "http_client")
        self.assertEqual(code, 0, out)
        paths = [x["path"] for x in out["data"]["fields"]]
        self.assertEqual(
            paths,
            ["url", "tls", "tls.enabled", "tls.client_certs", "tls.client_certs[].password",
             "headers", "headers.*.value"],
        )
        f = {x["path"]: x for x in out["data"]["fields"]}
        self.assertTrue(f["tls.client_certs[].password"]["secret"])
        self.assertTrue(f["headers.*.value"]["deprecated"])
        self.assertTrue(f["url"]["required"])
        self.assertEqual(f["tls.enabled"]["default"], False)

    def test_unknown(self) -> None:
        comps = [{"name": n, "config": {}} for n in ("kafka", "kafka_franz", "stdin")]
        self.fake({"match": "json-full inputs$", "out": [["O", _json_full("inputs", comps)]]})
        code, out = self.cmd("fields", "inputs", "nope")
        self.assertEqual(code, 1, out)
        self.assertIn("not found", out["errors"][0]["message"])
        self.assertEqual(out["data"]["components"], [])
        code, out = self.cmd("fields", "inputs", "kafka_fr")
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["components"], ["kafka_franz", "kafka"])

    def test_unknown_category(self) -> None:
        self.fake(
            {"match": "json-full", "out": [["O", _json_full("inputs", [])]]},
            {"match": "json$", "out": [["O", json.dumps({"inputs": []})]]},
        )
        for category in ("nope", "config"):
            with self.subTest(category=category):
                code, out = self.cmd("fields", category, "x")
                self.assertEqual(code, 2, out)
                self.assertIn("unknown category", out["errors"][0]["message"])
                self.assertEqual(
                    out["data"], {"category": category, "component": "x", "status": None, "fields": []}
                )


class RunTest(ToolCheckBase):
    def test_ok(self) -> None:
        self.fake({"match": "^run", "echo_stdin": True, "out": [["E", 'level=info msg="Launching"\n']]})
        c = self.make("p[1].yaml")
        i = self.make("in.jsonl", '{"n":1}\n{"n":2}\n')
        r = self.make("r[1].yaml")
        e = self.make("x.env")
        code, out = self.cmd("run", c, "--input", i, "--resources", r, "--resources", r, "--env-file", e)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out["data"], {"config": c, "outputs": ['{"n":1}', '{"n":2}'], "exit": 0, "runtime_errors": []}
        )
        call = self.calls()[0]
        self.assertEqual(
            call["argv"],
            ["connect", "run", "--set", "http.enabled=false", "--resources",
             str(self.work / "r\\[1\\].yaml"), "--env-file", e, c],
        )
        self.assertEqual(call["stdin"], '{"n":1}\n{"n":2}\n')
        self.assertNoForbiddenFlags()

    def test_no_input_stdin_empty(self) -> None:
        self.fake({"match": "^run"})
        code, out = self.cmd("run", self.make("p.yaml"))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.calls()[0]["stdin"], "")
        self.assertEqual(out["data"]["outputs"], [])

    def test_lint_error(self) -> None:
        c = self.make("p.yaml")
        line = (
            'time="t" level=error msg="Config lint error" @service=redpanda-connect '
            f'lint="{c}(5,28) required: expected \\"x\\""\n'
        )
        self.fake({"match": "^run", "out": [["E", line + 'level=error msg="shutting down"\n']], "exit": 1})
        code, out = self.cmd("run", c)
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["errors"], [{"file": c, "line": 5, "column": 28, "message": 'required: expected "x"'}]
        )
        self.assertEqual(out["data"]["exit"], 1)

    def test_other_failure_carries_stderr_tail(self) -> None:
        self.fake({"match": "^run", "out": [["E", "boom one\nboom two\n"]], "exit": 3})
        code, out = self.cmd("run", self.make("p.yaml"))
        self.assertEqual(code, 1, out)
        self.assertIn("exited 3", out["errors"][0]["message"])
        self.assertIn("boom two", out["errors"][0]["message"])
        self.assertEqual(out["data"]["exit"], 3)

    def test_timeout(self) -> None:
        self.fake({"match": "^run", "out": [["O", "first\nsecond\n"]], "sleep": 30})
        code, out = self.cmd("run", self.make("p.yaml"), "--timeout", "2")
        self.assertEqual(code, 2, out)
        self.assertIn("timed out after 2s", out["errors"][0]["message"])
        self.assertEqual(out["data"]["outputs"], ["first", "second"])
        self.assertIsNone(out["data"]["exit"])

    def test_bounded_replaces_input_and_output(self) -> None:
        self.fake({"match": "^run", "echo_stdin": True})
        c = self.make("p.yaml")
        i = self.make("in.jsonl", '{"n":1}\n')
        r = self.make("r.yaml")
        code, out = self.cmd("run", c, "--bounded", "--input", i, "--resources", r)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["outputs"], ['{"n":1}'])
        call = self.calls()[0]
        marker = (
            'output.processors=[{"mapping":"if errored() {\\n  root = {}\\n'
            '  root.__rpcn_check_unhandled_error__.error = error()\\n'
            '  root.__rpcn_check_unhandled_error__.input = content().string()\\n}"}]'
        )
        self.assertEqual(
            call["argv"],
            ["connect", "run", "--set", "http.enabled=false", "--set", 'input={"stdin":{}}',
             "--set", 'output={"stdout":{}}', "--set", "logger.format=logfmt", "--set", "logger.level=info",
             "--set", marker, "--resources", r, c],
        )
        # the binary splits a --set value on commas, so no bounded value has one
        for value in call["argv"][5:15:2]:
            self.assertNotIn(",", value)
        self.assertEqual(call["stdin"], '{"n":1}\n')

    def test_bounded_needs_input(self) -> None:
        self.fake({"match": "."})
        code, out = self.cmd("run", self.make("p.yaml"), "--bounded")
        self.assertEqual(code, 2, out)
        self.assertIn("--bounded needs --input", out["errors"][0]["message"])
        self.assertEqual(out["data"], {})
        self.assertIsNone(out["binary"])
        self.assertEqual(self.calls(), [])

    RUNTIME_LOG = (
        'time="t" level=info msg="Input type stdin is now active" @service=redpanda-connect label="" path=root.input\n'
        'time="t" level=error msg="failed assignment (line 2): cannot multiply types string (from field '
        '`this.total`) and number (from number literal)" @service=redpanda-connect label=enrich '
        'path=root.pipeline.processors.0\n'
        'time="t" level=error msg="no path on this one" @service=redpanda-connect\n'
        'time="t" level=info msg="Pipeline has terminated. Shutting down the service" @service=redpanda-connect\n'
    )
    RUNTIME_MSG = ("failed assignment (line 2): cannot multiply types string (from field `this.total`) "
                   "and number (from number literal)")
    RUNTIME_ERROR = {"path": "root.pipeline.processors.0", "message": RUNTIME_MSG, "input": None}

    @staticmethod
    def marker(error: str, message: str) -> str:
        return json.dumps({"__rpcn_check_unhandled_error__": {"error": error, "input": message}}) + "\n"

    def test_runtime_error_without_bounded_is_read_from_the_log(self) -> None:
        self.fake({"match": "^run", "out": [["O", '{"a":1}\n{"b":"x"}\n'], ["E", self.RUNTIME_LOG]]})
        c = self.make("p.yaml")
        code, out = self.cmd("run", c, "--input", self.make("in.jsonl", "{}\n"))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["exit"], 0)
        self.assertEqual(out["data"]["runtime_errors"], [self.RUNTIME_ERROR])
        self.assertEqual(out["data"]["outputs"], ['{"a":1}', '{"b":"x"}'])
        self.assertEqual(
            out["errors"],
            [{"file": c, "line": None, "column": None,
              "message": "root.pipeline.processors.0: " + self.RUNTIME_MSG}],
        )

    def test_bounded_unhandled_error_is_a_marker_line(self) -> None:
        bad = '{"b":"x"}'
        stdout = '{"a":1}\n' + self.marker(self.RUNTIME_MSG, bad) + self.marker("other error", "raw, text")
        self.fake({"match": "^run", "out": [["O", stdout], ["E", self.RUNTIME_LOG]]})
        c = self.make("p.yaml")
        code, out = self.cmd("run", c, "--bounded", "--input", self.make("in.jsonl", "{}\n"))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["exit"], 0)
        self.assertEqual(out["data"]["outputs"], ['{"a":1}'])
        self.assertEqual(
            out["data"]["runtime_errors"],
            [{"path": "root.pipeline.processors.0", "message": self.RUNTIME_MSG, "input": bad},
             {"path": None, "message": "other error", "input": "raw, text"}],
        )
        self.assertEqual(
            [e["message"] for e in out["errors"]],
            ["root.pipeline.processors.0: " + self.RUNTIME_MSG, "other error"],
        )

    def test_bounded_logged_but_caught_error_passes(self) -> None:
        self.fake({"match": "^run", "out": [["O", '{"a":1}\n{"b":"x","dlq":true}\n'], ["E", self.RUNTIME_LOG]]})
        code, out = self.cmd("run", self.make("p.yaml"), "--bounded", "--input", self.make("in.jsonl", "{}\n"))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["runtime_errors"], [])
        self.assertEqual(out["data"]["outputs"], ['{"a":1}', '{"b":"x","dlq":true}'])

    def test_marker_lookalikes_stay_outputs(self) -> None:
        lines = ['{"__rpcn_check_unhandled_error__":{"error":1}}',
                 '{"__rpcn_check_unhandled_error__":{"error":"e"},"x":1}', "not json"]
        self.fake({"match": "^run", "out": [["O", "\n".join(lines) + "\n"]]})
        code, out = self.cmd("run", self.make("p.yaml"), "--bounded", "--input", self.make("in.jsonl", "{}\n"))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["outputs"], lines)

    def test_info_lines_with_path_are_not_errors(self) -> None:
        log = 'level=info msg="Output type stdout is now active" path=root.output\nlevel=warn msg="w" path=root.input\n'
        self.fake({"match": "^run", "out": [["E", log]]})
        code, out = self.cmd("run", self.make("p.yaml"))
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["runtime_errors"], [])

    def test_runtime_error_kept_on_timeout(self) -> None:
        stdout = "first\n" + self.marker(self.RUNTIME_MSG, "m")
        self.fake({"match": "^run", "out": [["O", stdout], ["E", self.RUNTIME_LOG]], "sleep": 30})
        code, out = self.cmd("run", self.make("p.yaml"), "--bounded", "--input", self.make("in.jsonl", "{}\n"),
                             "--timeout", "2")
        self.assertEqual(code, 2, out)
        self.assertIn("timed out after 2s", out["errors"][0]["message"])
        self.assertEqual(out["data"]["runtime_errors"],
                         [{"path": "root.pipeline.processors.0", "message": self.RUNTIME_MSG, "input": "m"}])
        self.assertEqual(out["data"]["outputs"], ["first"])

    def test_runtime_error_with_nonzero_exit_keeps_both(self) -> None:
        self.fake({"match": "^run", "out": [["E", self.RUNTIME_LOG]], "exit": 3})
        code, out = self.cmd("run", self.make("p.yaml"))
        self.assertEqual(code, 1, out)
        self.assertEqual(len(out["errors"]), 1)
        self.assertEqual(out["data"]["runtime_errors"], [self.RUNTIME_ERROR])
        self.assertEqual(out["data"]["exit"], 3)

    def test_parse_logfmt(self) -> None:
        spec = importlib.util.spec_from_file_location("rpcn_check_logfmt", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.parse_logfmt('time="a b" level=error msg="say \\"hi\\"" label="" path=root.x'),
            {"time": "a b", "level": "error", "msg": 'say "hi"', "label": "", "path": "root.x"},
        )

    def test_bad_timeout(self) -> None:
        self.fake({"match": "."})
        for value in ("0", "-1", "abc"):
            with self.subTest(value=value):
                code, out = self.run_check("run", self.make("p.yaml"), "--timeout", value)
                self.assertEqual(code, 2, out)
        self.assertEqual(self.calls(), [])

    def test_missing_files(self) -> None:
        self.fake({"match": "."})
        c = self.make("p.yaml")
        nope = str(self.work / "nope")
        for args in ([nope], [c, "--input", nope], [c, "--resources", nope], [c, "--env-file", nope]):
            with self.subTest(args=args):
                code, out = self.cmd("run", *args)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["errors"][0]["file"], nope)
                self.assertIsNone(out["binary"])
        self.assertEqual(self.calls(), [])


_ESC = "\x1b[0;33m"
_RST = "\x1b[0m"
TEST_FAIL_OUT = (
    "Test 'p.yaml' failed\n\nFailures:\n\n--- p.yaml ---\n\n"
    "wrong [line 7]:\nbatch 0 message 0: json_equals: JSON content mismatch\n"
    f'{{\n    "doubled": {_ESC}4 => 5{_RST}\n}}\n'
)


class TestCmdTest(ToolCheckBase):
    def test_pass_fail(self) -> None:
        self.fake({"match": "^test", "out": [["O", TEST_FAIL_OUT]], "exit": 1})
        t = self.make("p_benthos_test.yaml")
        code, out = self.cmd("test", t)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["targets"], [{"file": "p.yaml", "passed": False}])
        self.assertEqual(out["data"]["passed"], 0)
        self.assertEqual(out["data"]["failed"], 1)
        self.assertEqual(
            out["data"]["failures"],
            [{"target": "p.yaml", "case": "wrong", "line": 7,
              "message": 'batch 0 message 0: json_equals: JSON content mismatch\n{\n    "doubled": 4 => 5\n}'}],
        )
        self.assertEqual(out["errors"][0]["file"], "p.yaml")
        self.assertIn("wrong [line 7]", out["errors"][0]["message"])
        self.assertNoForbiddenFlags()

    def test_several_targets_and_cases(self) -> None:
        text = (
            "Test 'a.yaml' succeeded\nTest 'p.yaml' failed\nTest 'q.yaml' failed\n\nFailures:\n\n"
            "--- p.yaml ---\n\nwrong [line 7]:\ndetail p\n\n"
            "--- q.yaml ---\n\none [line 2]:\ndetail one\n\ntwo:\nwrong batch count\nsecond line\n"
        )
        self.fake({"match": "^test", "out": [["O", text]], "exit": 1})
        code, out = self.cmd("test", self.make("t.yaml"))
        self.assertEqual(code, 1, out)
        self.assertEqual(
            out["data"]["targets"],
            [{"file": "a.yaml", "passed": True}, {"file": "p.yaml", "passed": False},
             {"file": "q.yaml", "passed": False}],
        )
        self.assertEqual((out["data"]["passed"], out["data"]["failed"]), (1, 2))
        self.assertEqual(
            [(f["target"], f["case"], f["line"], f["message"]) for f in out["data"]["failures"]],
            [("p.yaml", "wrong", 7, "detail p"), ("q.yaml", "one", 2, "detail one"),
             ("q.yaml", "two", None, "wrong batch count\nsecond line")],
        )

    def test_all_pass(self) -> None:
        self.fake({"match": "^test", "out": [["O", "Test 'ok.yaml' succeeded\n"]]})
        r = self.make("r[1].yaml")
        e = self.make("x.env")
        t = self.make("ok[1]_benthos_test.yaml")
        code, out = self.cmd("test", t, "--resources", r, "--env-file", e)
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out["data"],
            {"targets": [{"file": "ok.yaml", "passed": True}], "failures": [], "passed": 1, "failed": 0},
        )
        self.assertEqual(
            self.calls()[0]["argv"],
            ["connect", "test", "--resources", str(self.work / "r\\[1\\].yaml"), "--env-file", e,
             str(self.work / "ok\\[1\\]_benthos_test.yaml")],
        )

    def test_init_failure(self) -> None:
        self.fake(
            {"match": "^test", "out": [["E", "Failed to execute test target 'p.yaml': test case 0 failed: boom\n"]],
             "exit": 1}
        )
        code, out = self.cmd("test", self.make("p_benthos_test.yaml"))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["data"]["targets"], [{"file": "p.yaml", "passed": False}])
        self.assertEqual(out["data"]["failed"], 1)
        self.assertEqual(out["errors"][0]["file"], "p.yaml")
        self.assertIn("boom", out["errors"][0]["message"])

    def test_none(self) -> None:
        self.fake({"match": "^test", "out": [["O", "No tests were found\n"]], "exit": 1})
        t = self.make("p.yaml")
        code, out = self.cmd("test", t)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["errors"], [{"file": t, "line": None, "column": None, "message": "No tests were found"}])

    def test_silent_failure(self) -> None:
        self.fake({"match": "^test", "exit": 4})
        code, out = self.cmd("test", self.make("p.yaml"))
        self.assertEqual(code, 2, out)
        self.assertIn("exited 4", out["errors"][0]["message"])

    def test_missing_files(self) -> None:
        self.fake({"match": "."})
        t = self.make("p.yaml")
        nope = str(self.work / "nope")
        for args in ([nope], [t, "--resources", nope], [t, "--env-file", nope]):
            with self.subTest(args=args):
                code, out = self.cmd("test", *args)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["errors"][0]["file"], nope)
                self.assertIsNone(out["binary"])
        self.assertEqual(self.calls(), [])


class NewCommandsEnvTest(ToolCheckBase):
    """The shared lookup and version floor apply to every new subcommand."""

    def test_too_old_and_missing_binary(self) -> None:
        m = self.make("m.blobl")
        cases = [("blobl", m), ("list", "inputs"), ("fields", "inputs", "generate"), ("run", m), ("test", m)]
        fake_rpk(self.path_dir, "Version: 4.99.0")
        for args in cases:
            with self.subTest(args=args, binary="too old"):
                code, out = self.cmd(*args)
                self.assertEqual(code, 2, out)
                self.assertEqual(out["binary"]["version"], "4.99.0")
        (self.path_dir / "rpk").unlink()
        for args in cases:
            with self.subTest(args=args, binary="none"):
                code, out = self.cmd(*args)
                self.assertEqual(code, 2, out)
                self.assertIsNone(out["binary"])


def _real_binaries() -> list[str]:
    raw = os.environ.get("RPCN_TEST_BINARIES", "")
    return [os.path.abspath(p) for p in raw.split(os.pathsep) if p.strip()]


# Expected results for each fixture: (file, line, column, message substring).
# The same sorted list must come back from every tested binary.
_MULTI = [
    (5, 1, "not_a_field"),
    (9, 29, "expected method or field path"),
    (13, 1, "bogus_option"),
    (18, 1, "wrong_key"),
]
REAL_CASES: dict[str, tuple[list[str], int, list[tuple[str, int, int, str]]]] = {
    "valid": (["valid.yaml"], 0, []),
    "multi_error": (["multi_error.yaml"], 1, [("multi_error.yaml", *e) for e in _MULTI]),
    "deprecated": (["deprecated.yaml"], 1, [("deprecated.yaml", 2, 1, "component kafka is deprecated")]),
    "bad_yaml": (["bad_yaml.yaml"], 1, [("bad_yaml.yaml", 1, 1, "yaml")]),
    "several_files": (
        ["multi_error.yaml", "bad_yaml.yaml"],
        1,
        [("bad_yaml.yaml", 1, 1, "yaml")] + [("multi_error.yaml", *e) for e in _MULTI],
    ),
    "env_var": (["env_var.yaml"], 0, []),
    "glob_name": (["a[1].yaml"], 1, [("a[1].yaml", *e) for e in _MULTI]),
}


@unittest.skipUnless(
    _real_binaries(),
    "real-binary tests skipped: set RPCN_TEST_BINARIES to binary paths (see tools/fetch_rpcn.py)",
)
class RealBinaryLintTest(unittest.TestCase):
    """Runs the fixtures through `lint` on each binary in RPCN_TEST_BINARIES."""

    def lint(self, binary: str, files: list[str]) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "lint", *files],
            capture_output=True,
            text=True,
            cwd=FIXTURES,
            env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "RPCN_BINARY": binary},
            timeout=120,
        )
        try:
            return proc.returncode, json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON:\n{proc.stdout}\nstderr:\n{proc.stderr}")

    def test_fixtures(self) -> None:
        binaries = _real_binaries()
        for name, (files, want_code, want) in REAL_CASES.items():
            per_binary = {}
            for binary in binaries:
                with self.subTest(fixture=name, binary=binary):
                    code, out = self.lint(binary, files)
                    self.assertEqual(code, want_code, out)
                    self.assertEqual(out["ok"], want_code == 0)
                    self.assertEqual(out["binary"]["path"], binary)
                    folder = re.search(r"/\.cache/rpcn/([^/]+)/[^/]+$", binary)
                    if folder:
                        self.assertEqual(out["binary"]["version"], folder.group(1))
                    got = out["errors"]
                    self.assertEqual(
                        [(e["file"], e["line"], e["column"]) for e in got],
                        [(f, line, col) for f, line, col, _ in want],
                        got,
                    )
                    for err, (_, _, _, fragment) in zip(got, want):
                        self.assertIn(fragment, err["message"])
                    self.assertEqual(out["data"], {"files": files, "error_count": len(want)})
                    per_binary[binary] = got
            if len(per_binary) > 1:
                with self.subTest(fixture=name, check="same errors on every binary"):
                    first, *rest = per_binary.values()
                    for other in rest:
                        self.assertEqual(other, first)

    def test_missing_file_not_passed_to_binary(self) -> None:
        for binary in _real_binaries():
            with self.subTest(binary=binary):
                code, out = self.lint(binary, ["valid.yaml", "does-not-exist.yaml"])
                self.assertEqual(code, 2, out)
                self.assertEqual(out["errors"][0]["file"], "does-not-exist.yaml")
                self.assertIsNone(out["binary"], "binary must not run")



@unittest.skipUnless(
    _real_binaries(),
    "real-binary tests skipped: set RPCN_TEST_BINARIES to binary paths (see tools/fetch_rpcn.py)",
)
class RealBinaryCommandsTest(unittest.TestCase):
    """blobl (with --samples), list, fields, run and test on each binary in RPCN_TEST_BINARIES, and `from` paths."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def check(self, binary: str, *args: str, timeout: int = 120, cwd: Path = FIXTURES) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=cwd,
            env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""), "RPCN_BINARY": binary},
            timeout=timeout,
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"stdout is not JSON:\n{proc.stdout}\nstderr:\n{proc.stderr}")
        self.assertEqual(out["command"], args[0])
        self.assertEqual(out["ok"], proc.returncode == 0, out)
        return proc.returncode, out

    def each(self):
        for binary in _real_binaries():
            with self.subTest(binary=binary):
                yield binary

    def test_blobl(self) -> None:
        one = self.tmp / "one.jsonl"
        one.write_text('{"n":21}\n')
        for b in self.each():
            code, out = self.check(b, "blobl", "double.blobl", "--input", str(one))
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["results"], [{"line": 1, "output": '{"doubled":42}', "error": None}])

            code, out = self.check(b, "blobl", "double.blobl", "--input", "samples.jsonl")
            self.assertEqual(code, 1, out)
            results = out["data"]["results"]
            self.assertEqual([r["line"] for r in results], [1, 2, 3])
            self.assertEqual(results[0]["output"], '{"doubled":2}')
            self.assertIsNone(results[1]["output"])
            self.assertIn("json", results[1]["error"])
            self.assertEqual(results[2]["output"], '{"doubled":6}')
            self.assertEqual([(e["file"], e["line"]) for e in out["errors"]], [("samples.jsonl", 2)])

            code, out = self.check(b, "blobl", "bad.blobl")
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out["errors"]), 1)
            err = out["errors"][0]
            self.assertEqual((err["file"], err["line"]), ("bad.blobl", 2))
            self.assertIsInstance(err["column"], int)

            code, out = self.check(b, "blobl", "double.blobl")
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["results"], [])

    def test_blobl_samples(self) -> None:
        ex = doc_examples(FORMATS / "samples-format.md")
        good = self.tmp / "orders.enrich.blobl"
        good.write_text(ex["orders.enrich.blobl"])
        samples = self.tmp / "orders.samples.json"
        samples.write_text(ex["orders.samples.json"])
        buggy_dir = self.tmp / "buggy"
        buggy_dir.mkdir()
        buggy = buggy_dir / "orders.enrich.blobl"
        buggy.write_text(ex["orders.enrich.blobl"].replace("* 100", "* 10"))
        broken_dir = self.tmp / "broken"
        broken_dir.mkdir()
        broken = broken_dir / "orders.enrich.blobl"
        broken.write_text(ex["orders.enrich.blobl"] + "root.half =\n")
        # Output facts (SOURCES.md): a string root prints raw, without quotes, and a
        # deleted message prints an empty line.
        facts = self.tmp / "facts.blobl"
        facts.write_text(
            'root = if this.k == "s" { "123" } else if this.k == "d" { deleted() }'
            ' else { {"a": 1}.format_json(no_indent: true) }\n'
        )
        facts_samples = self.tmp / "facts.samples.json"
        facts_samples.write_text(json.dumps({"format": "samples@1", "pipeline": "facts", "mappings": {"facts.blobl": [
            {"name": "string root", "input": {"k": "s"}, "output": "123"},
            {"name": "deleted", "input": {"k": "d"}, "deleted": True},
            {"name": "json text", "input": {"k": "j"}, "output": '{"a":1}'},
        ]}}))
        for b in self.each():
            code, out = self.check(b, "blobl", str(good), "--samples", str(samples))
            self.assertEqual(code, 0, out)
            self.assertEqual((out["data"]["passed"], out["data"]["failed"]), (2, 0))

            code, out = self.check(b, "blobl", str(buggy), "--samples", str(samples))
            self.assertEqual(code, 1, out)
            self.assertEqual((out["data"]["passed"], out["data"]["failed"]), (0, 2))
            first = out["data"]["samples"][0]
            self.assertIn('"total_cents":1250', first["expected"])
            self.assertIn('"total_cents":125}', first["actual"])
            self.assertEqual(samples.read_text(), ex["orders.samples.json"])

            code, out = self.check(b, "blobl", str(facts), "--samples", str(facts_samples))
            self.assertEqual(code, 0, out)
            self.assertEqual([r["output"] for r in out["data"]["results"]], ["123", "", '{"a":1}'])
            self.assertEqual(out["data"]["passed"], 3)

            code, out = self.check(b, "blobl", str(broken), "--samples", str(samples))
            self.assertEqual(code, 1, out)
            self.assertEqual((out["errors"][0]["file"], out["errors"][0]["line"]), (str(broken), 5))
            self.assertEqual(out["data"]["samples"], [])

    def test_from_resolves_against_the_working_directory(self) -> None:
        """A pipeline's `from "<path>"` is read from the process's working directory,
        not the config's folder (SOURCES.md; rpcn-author's pipeline-files.md)."""
        pipes = self.tmp / "pipes"
        pipes.mkdir()
        (pipes / "p.double.blobl").write_text("root = this\nroot.doubled = this.n * 2\n")
        (pipes / "p.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - label: double\n      mapping: 'from \"./pipes/p.double.blobl\"'\n"
            "output:\n  stdout: {}\n"
        )
        (self.tmp / "in.jsonl").write_text('{"n":21}\n')
        for b in self.each():
            code, out = self.check(b, "lint", "pipes/p.yaml", cwd=self.tmp)
            self.assertEqual(code, 0, out)
            code, out = self.check(b, "run", "pipes/p.yaml", "--input", "in.jsonl", cwd=self.tmp)
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["outputs"], ['{"doubled":42,"n":21}'])
            # From the config's own folder the same path is not found.
            code, out = self.check(b, "lint", "p.yaml", cwd=pipes)
            self.assertEqual(code, 1, out)
            self.assertIn("failed to read import", out["errors"][0]["message"])
            self.assertIn("pipes/pipes/p.double.blobl", out["errors"][0]["message"])

    def test_list(self) -> None:
        for b in self.each():
            code, out = self.check(b, "list", "inputs")
            self.assertEqual(code, 0, out)
            self.assertIn("generate", out["data"]["components"])
            self.assertIn("stdin", out["data"]["components"])
            code, out = self.check(b, "list", "inputs", "--status", "stable")
            self.assertEqual(code, 0, out)
            self.assertIn("generate", out["data"]["components"])
            code, out = self.check(b, "list", "nope")
            self.assertEqual(code, 2, out)
            self.assertIn("inputs", out["errors"][0]["message"])

    def test_fields(self) -> None:
        for b in self.each():
            code, out = self.check(b, "fields", "inputs", "generate")
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["status"], "stable")
            f = {x["path"]: x for x in out["data"]["fields"]}
            self.assertTrue(f["mapping"]["required"])
            self.assertEqual(f["interval"]["default"], "1s")
            self.assertFalse(f["interval"]["required"])

            code, out = self.check(b, "fields", "inputs", "http_client")
            self.assertEqual(code, 0, out)
            f = {x["path"]: x for x in out["data"]["fields"]}
            self.assertIn("tls.enabled", f)
            self.assertTrue(f["tls.enabled"]["advanced"])
            self.assertTrue(f["tls.client_certs[].password"]["secret"])

            code, out = self.check(b, "fields", "inputs", "nope")
            self.assertEqual(code, 1, out)
            self.assertIn("not found", out["errors"][0]["message"])

    def test_run(self) -> None:
        forever = self.tmp / "forever.yaml"
        forever.write_text(
            "input:\n  generate:\n    interval: 100ms\n    mapping: 'root = {\"n\": counter()}'\n"
            "output:\n  stdout:\n    codec: lines\n"
        )
        for b in self.each():
            # samples.jsonl's line 2 is not JSON: the binary exits 0, the log names the processor
            code, out = self.check(b, "run", "stdin_pipeline.yaml", "--input", "samples.jsonl")
            self.assertEqual(code, 1, out)
            self.assertEqual(out["data"]["exit"], 0)
            self.assertIn('{"doubled":2}', out["data"]["outputs"])
            self.assertIn('{"doubled":6}', out["data"]["outputs"])
            self.assertEqual([e["path"] for e in out["data"]["runtime_errors"]], ["root.pipeline.processors.0"])

            code, out = self.check(b, "run", "multi_error.yaml")
            self.assertEqual(code, 1, out)
            self.assertEqual(
                [(e["file"], e["line"], e["column"]) for e in out["errors"]],
                [("multi_error.yaml", line, col) for line, col, _ in _MULTI],
            )

            code, out = self.check(b, "run", str(forever), "--timeout", "2")
            self.assertEqual(code, 2, out)
            self.assertIn("timed out after 2s", out["errors"][0]["message"])
            self.assertIsNone(out["data"]["exit"])
            self.assertIn('{"n":1}', out["data"]["outputs"])

    def test_run_bounded(self) -> None:
        """Binary facts (SOURCES.md), on each binary:
        - `--set` with an object replaces the whole input and output, so a Kafka
          pipeline runs on stdin and stdout with no broker;
        - a mapping error logs `level=error ... path=<processor>` and the binary
          exits 0, and the same line is logged when a later `catch` handles it;
        - `errored()` still holds at the output for an uncaught error, so the
          `--bounded` marker processor reports it (and not the caught one), even
          when the config sets a JSON logger at level none."""
        mapping = (
            "    - label: enrich\n      mapping: |\n"
            "        root = this\n        root.total_cents = this.total * 100\n"
        )
        kafka = self.tmp / "orders.yaml"
        kafka.write_text(
            "input:\n  kafka:\n    addresses: [ \"localhost:1\" ]\n    topics: [ orders ]\n"
            "    consumer_group: g\n"
            "pipeline:\n  processors:\n" + mapping +
            "output:\n  kafka:\n    addresses: [ \"localhost:1\" ]\n    topic: out\n"
        )
        caught = self.tmp / "caught.yaml"
        caught.write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n" + mapping +
            "    - label: dlq\n      catch:\n        - mapping: 'root = this.merge({\"dlq\": true})'\n"
            "output:\n  stdout: {}\n"
        )
        quiet = self.tmp / "quiet.yaml"
        quiet.write_text(
            "logger:\n  level: none\n  format: json\n"
            "input:\n  stdin: {}\npipeline:\n  processors:\n" + mapping + "output:\n  stdout: {}\n"
        )
        good = self.tmp / "good.jsonl"
        good.write_text('{"id":"a","total":2}\n')
        bad = self.tmp / "bad.jsonl"
        bad.write_text('{"id":"a","total":2}\n{"id":"b","total":"x"}\n')
        for b in self.each():
            code, out = self.check(b, "run", str(kafka), "--bounded", "--input", str(good), timeout=60)
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["outputs"], ['{"id":"a","total":2,"total_cents":200}'])
            self.assertEqual(out["data"]["runtime_errors"], [])

            for config in (kafka, quiet):
                code, out = self.check(b, "run", str(config), "--bounded", "--input", str(bad), timeout=60)
                self.assertEqual(code, 1, out)
                self.assertEqual(out["data"]["exit"], 0, "the binary exits 0 on a mapping error")
                self.assertEqual(len(out["data"]["runtime_errors"]), 1, out)
                err = out["data"]["runtime_errors"][0]
                self.assertEqual(err["path"], "root.pipeline.processors.0")
                self.assertIn("cannot multiply types string", err["message"])
                self.assertEqual(err["input"], '{"id":"b","total":"x"}')
                # the marker line is moved out of the outputs
                self.assertEqual(out["data"]["outputs"], ['{"id":"a","total":2,"total_cents":200}'])

            # caught: the error is still logged (seen without --bounded), but the message
            # leaves the catch no longer errored, so the bounded run passes
            code, out = self.check(b, "run", str(caught), "--input", str(bad), timeout=60)
            self.assertEqual(code, 1, out)
            self.assertEqual([e["path"] for e in out["data"]["runtime_errors"]], ["root.pipeline.processors.0"])
            code, out = self.check(b, "run", str(caught), "--bounded", "--input", str(bad), timeout=60)
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["runtime_errors"], [])
            self.assertIn('{"dlq":true,"id":"b","total":"x"}', out["data"]["outputs"])

    def test_test(self) -> None:
        for b in self.each():
            code, out = self.check(b, "test", "stdin_pipeline_benthos_test.yaml")
            self.assertEqual(code, 1, out)
            self.assertEqual(out["data"]["targets"], [{"file": "stdin_pipeline.yaml", "passed": False}])
            self.assertEqual((out["data"]["passed"], out["data"]["failed"]), (0, 1))
            self.assertEqual(len(out["data"]["failures"]), 1)
            failure = out["data"]["failures"][0]
            self.assertEqual(failure["target"], "stdin_pipeline.yaml")
            self.assertEqual(failure["case"], "expects the wrong value")
            self.assertEqual(failure["line"], 8)
            self.assertIn("4 => 5", failure["message"])
            self.assertNotIn("\x1b", failure["message"])

            code, out = self.check(b, "test", "valid.yaml")
            self.assertEqual(code, 1, out)
            self.assertIn("No tests were found", out["errors"][0]["message"])

    def test_test_all_pass(self) -> None:
        shutil.copy(FIXTURES / "stdin_pipeline.yaml", self.tmp / "ok.yaml")
        text = (FIXTURES / "stdin_pipeline_benthos_test.yaml").read_text()
        (self.tmp / "ok_benthos_test.yaml").write_text(text.split("\n\n  - name: expects")[0] + "\n")
        for b in self.each():
            code, out = self.check(b, "test", str(self.tmp / "ok_benthos_test.yaml"))
            self.assertEqual(code, 0, out)
            self.assertEqual(
                out["data"],
                {"targets": [{"file": str(self.tmp / "ok.yaml"), "passed": True}], "failures": [],
                 "passed": 1, "failed": 0},
            )

    def test_test_unit_case_facts(self) -> None:
        """Binary facts rpcn-test's unit tests rely on (SOURCES.md), on each binary:
        - `test pipes/<name>.yaml` finds the sibling `pipes/<name>_benthos_test.yaml`;
        - `json_equals` and `json_contains` work, and a `json_contains` mismatch is a
          failing case with its line;
        - `mocks` replace a processor by its label, or by its path when it has none;
        - an unset `${VAR}` in the pipeline does not stop a test;
        - `from "<path>"` is read from the working directory."""
        pipes = self.tmp / "pipes"
        pipes.mkdir()
        (pipes / "orders.enrich.blobl").write_text("root = this\nroot.total_cents = (this.total * 100).round()\n")
        (pipes / "orders.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - label: enrich\n      mapping: 'from \"./pipes/orders.enrich.blobl\"'\n"
            "    - label: lookup\n      http:\n        url: ${LOOKUP_URL_UNSET_P29}\n        verb: GET\n"
            "    - http:\n        url: http://localhost:1/unlabelled\n        verb: GET\n"
            "    - mapping: 'root = this.merge({\"at\": now()})'\n"
            "output:\n  stdout: {}\n"
        )
        case = (
            "  - name: {name}\n    target_processors: /pipeline/processors\n"
            "    mocks:\n      lookup:\n        mapping: 'root = this.merge({{\"looked_up\": true}})'\n"
            "      /pipeline/processors/2:\n        mapping: 'root = this.merge({{\"second\": true}})'\n"
            "    input_batch:\n      - content: '{{\"id\":\"o1\",\"total\":12.5}}'\n"
            "    output_batches:\n      - - {check}\n"
        )
        passing = "tests:\n" + case.format(
            name="contains cents",
            check='json_contains: {"id": "o1", "total_cents": 1250, "looked_up": true, "second": true}'
        )
        for b in self.each():
            (pipes / "orders_benthos_test.yaml").write_text(passing)
            code, out = self.check(b, "test", "pipes/orders.yaml", cwd=self.tmp)
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["targets"], [{"file": "pipes/orders.yaml", "passed": True}])

            # json_equals on a deterministic copy of the pipeline (no now())
            det = (pipes / "orders.yaml").read_text().replace(
                "    - mapping: 'root = this.merge({\"at\": now()})'\n", ""
            )
            (pipes / "det.yaml").write_text(det)
            (pipes / "det_benthos_test.yaml").write_text("tests:\n" + case.format(
                name="equals",
                check='json_equals: {"id": "o1", "total": 12.5, "total_cents": 1250, "looked_up": true, "second": true}',
            ))
            code, out = self.check(b, "test", "pipes/det.yaml", cwd=self.tmp)
            self.assertEqual(code, 0, out)

            (pipes / "orders_benthos_test.yaml").write_text(passing + case.format(
                name="wrong cents", check='json_contains: {"id": "o1", "total_cents": 125}'
            ))
            code, out = self.check(b, "test", "pipes/orders.yaml", cwd=self.tmp)
            self.assertEqual(code, 1, out)
            self.assertEqual(len(out["data"]["failures"]), 1, out)
            failure = out["data"]["failures"][0]
            self.assertEqual((failure["target"], failure["case"], failure["line"]),
                             ("pipes/orders.yaml", "wrong cents", 13))
            self.assertIn("json_contains", failure["message"])
            self.assertIn("1250 => 125", failure["message"])

            # without the mocks the http processors run: no merged fields, so the case fails
            (pipes / "orders_benthos_test.yaml").write_text(
                re.sub(r"    mocks:\n(      .*\n        .*\n)+", "", passing)
            )
            self.assertNotIn("mocks", (pipes / "orders_benthos_test.yaml").read_text())
            code, out = self.check(b, "test", "pipes/orders.yaml", cwd=self.tmp)
            self.assertEqual(code, 1, out)
            # a failing case, not a target that failed to start: the unset ${VAR} didn't stop it
            self.assertEqual([f["case"] for f in out["data"]["failures"]], ["contains cents"], out)

    def test_test_content_equals_branch_mock_and_resources(self) -> None:
        """More facts unit-tests.md relies on (SOURCES.md), on each binary:
        - `content_equals` checks non-JSON output;
        - a mock keyed by a nested JSON-pointer path replaces a processor inside a `branch`;
        - a cache resource defined in a resources file stops the target from starting
          without `--resources` and works with it."""
        (self.tmp / "lines.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - mapping: 'root = content().uppercase()'\n"
            "output:\n  stdout: {}\n"
        )
        (self.tmp / "lines_benthos_test.yaml").write_text(
            "tests:\n  - name: upper\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: 'hello'\n"
            "    output_batches:\n      - - content_equals: HELLO\n"
            "  - name: wrong\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: 'hello'\n"
            "    output_batches:\n      - - content_equals: hello\n"
        )
        (self.tmp / "br.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - branch:\n        request_map: 'root = this'\n"
            "        processors:\n          - http:\n              url: http://localhost:1/x\n              verb: GET\n"
            "        result_map: 'root.tier = this.tier'\n"
            "output:\n  stdout: {}\n"
        )
        (self.tmp / "br_benthos_test.yaml").write_text(
            "tests:\n  - name: tier\n    target_processors: /pipeline/processors\n"
            "    mocks:\n      /pipeline/processors/0/branch/processors/0:\n"
            "        mapping: 'root = {\"tier\": \"gold\"}'\n"
            "    input_batch:\n      - content: '{\"id\":1}'\n"
            "    output_batches:\n      - - json_equals: {\"id\": 1, \"tier\": \"gold\"}\n"
        )
        (self.tmp / "dedupe.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - cache:\n        resource: seen\n        operator: set\n"
            "        key: '${! json(\"id\") }'\n        value: '${! content() }'\n"
            "output:\n  stdout: {}\n"
        )
        (self.tmp / "dedupe.resources.yaml").write_text("cache_resources:\n  - label: seen\n    memory: {}\n")
        (self.tmp / "dedupe_benthos_test.yaml").write_text(
            "tests:\n  - name: passes through\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: '{\"id\":1}'\n"
            "    output_batches:\n      - - json_equals: {\"id\": 1}\n"
        )
        for b in self.each():
            code, out = self.check(b, "test", "lines.yaml", cwd=self.tmp)
            self.assertEqual(code, 1, out)
            self.assertEqual([f["case"] for f in out["data"]["failures"]], ["wrong"], out)

            code, out = self.check(b, "test", "br.yaml", cwd=self.tmp)
            self.assertEqual(code, 0, out)

            code, out = self.check(b, "test", "dedupe.yaml", cwd=self.tmp)
            self.assertEqual(code, 1, out)
            self.assertEqual(out["data"]["failures"], [])
            self.assertIn("cache resource 'seen' was not found", out["errors"][0]["message"])
            code, out = self.check(b, "test", "--resources", "dedupe.resources.yaml", "dedupe.yaml", cwd=self.tmp)
            self.assertEqual(code, 0, out)

    def test_test_dropped_messages(self) -> None:
        """A dropped message has no output entry, and a case whose every message is
        dropped passes with `output_batches: []` (SOURCES.md)."""
        (self.tmp / "d.yaml").write_text(
            "input:\n  stdin: {}\npipeline:\n  processors:\n"
            "    - mapping: 'root = if this.drop { deleted() } else { this }'\n"
            "output:\n  stdout: {}\n"
        )
        (self.tmp / "d_benthos_test.yaml").write_text(
            "tests:\n"
            "  - name: all dropped\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: '{\"drop\":true}'\n    output_batches: []\n"
            "  - name: one dropped\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: '{\"drop\":true}'\n      - content: '{\"drop\":false,\"a\":1}'\n"
            "    output_batches:\n      - - json_equals: {\"drop\": false, \"a\": 1}\n"
            "  - name: dropped but expected\n    target_processors: /pipeline/processors\n"
            "    input_batch:\n      - content: '{\"drop\":true}'\n"
            "    output_batches:\n      - - json_equals: {\"drop\": true}\n"
        )
        for b in self.each():
            code, out = self.check(b, "test", "d.yaml", cwd=self.tmp)
            self.assertEqual(code, 1, out)
            self.assertEqual([f["case"] for f in out["data"]["failures"]], ["dropped but expected"])
            self.assertIn("wrong batch count", out["data"]["failures"][0]["message"])

    def test_missing_file_not_passed_to_binary(self) -> None:
        for b in self.each():
            for args in (["blobl", "nope.blobl"], ["run", "nope.yaml"], ["test", "nope.yaml"],
                         ["run", "stdin_pipeline.yaml", "--input", "nope.jsonl"]):
                code, out = self.check(b, *args)
                self.assertEqual(code, 2, out)
                self.assertIsNone(out["binary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
