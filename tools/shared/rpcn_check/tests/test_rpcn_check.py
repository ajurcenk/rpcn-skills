# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Unit tests for rpcn_check.py, using fake binaries and a controlled PATH.

Run: uv run tools/shared/rpcn_check/tests/test_rpcn_check.py
No real Redpanda Connect binary is needed.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "rpcn_check.py"


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


class RpcnCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.path_dir = root / "path"
        self.other_dir = root / "other"
        self.path_dir.mkdir()
        self.other_dir.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_check(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, dict]:
        full_env = {"PATH": str(self.path_dir), "HOME": self._tmp.name}
        full_env.update(env or {})
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=full_env,
            timeout=60,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
