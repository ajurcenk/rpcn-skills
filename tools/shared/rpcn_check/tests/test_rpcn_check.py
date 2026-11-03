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
    fmt: str = "test-report@1",
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
                "format": "test-report@1",
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

    def test_unknown_major(self) -> None:
        report = self.write("orders.test-report.md", handoff(fmt="test-report@2"))
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
        for status, want in (("ready", 0), ("draft", 1)):
            with self.subTest(status=status):
                report = self.write("orders.test-report.md", handoff(status=status))
                code, out = self.check(report)
                self.assertEqual(code, want, out)
                self.assertEqual(out["data"]["inputs"], [])
                self.assertEqual(out["data"]["ready"], want == 0)

    def test_bare_inputs_key_with_no_items(self) -> None:
        text = handoff().replace("inputs: []", "inputs:")
        report = self.write("orders.test-report.md", text)
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
        text = handoff().replace("status: ready", "status: 'ready'").replace(
            "format: test-report@1", 'format: "test-report@1"'
        )
        report = self.write("orders.test-report.md", text)
        code, out = self.check(report)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["data"]["format"], "test-report@1")

    def test_body_after_header_is_ignored(self) -> None:
        text = handoff() + "\n---\nartifact: nonsense\n"
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
        self.assertEqual(code, 0, out)
        self.assertFalse(out["data"]["pipeline_ready"])

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
    fh.write(json.dumps({"argv": args, "stdin": stdin, "no_color": os.environ.get("NO_COLOR")}) + "\\n")
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
        self.assertEqual(out["data"], {"config": c, "outputs": ['{"n":1}', '{"n":2}'], "exit": 0})
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
    """blobl, list, fields, run and test on each binary in RPCN_TEST_BINARIES."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def check(self, binary: str, *args: str, timeout: int = 120) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            cwd=FIXTURES,
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
            code, out = self.check(b, "run", "stdin_pipeline.yaml", "--input", "samples.jsonl")
            self.assertEqual(code, 0, out)
            self.assertEqual(out["data"]["exit"], 0)
            self.assertIn('{"doubled":2}', out["data"]["outputs"])
            self.assertIn('{"doubled":6}', out["data"]["outputs"])

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

    def test_missing_file_not_passed_to_binary(self) -> None:
        for b in self.each():
            for args in (["blobl", "nope.blobl"], ["run", "nope.yaml"], ["test", "nope.yaml"],
                         ["run", "stdin_pipeline.yaml", "--input", "nope.jsonl"]):
                code, out = self.check(b, *args)
                self.assertEqual(code, 2, out)
                self.assertIsNone(out["binary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
