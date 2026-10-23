# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Unit tests for tools/sync_shared.py, run against temporary repo trees.

Run: uv run tools/tests/test_sync_shared.py
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "sync_shared.py"
REPO_ROOT = SCRIPT.parent.parent

SOURCE_BYTES = b"#!/usr/bin/env python\nprint('canonical')\n"


def run_sync(root: Path, *args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True, text=True, timeout=60,
    )
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout is not JSON: {proc.stdout!r} {proc.stderr!r}") from exc
    return proc.returncode, out


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class TreeCase(unittest.TestCase):
    """A temporary repo with tools/shared/rpcn_check/rpcn_check.py and one skill."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.shared = self.root / "tools" / "shared"
        (self.shared / "rpcn_check").mkdir(parents=True)
        self.source = self.shared / "rpcn_check" / "rpcn_check.py"
        self.source.write_bytes(SOURCE_BYTES)
        self.source.chmod(0o755)  # the copy must still come out non-executable
        (self.shared / "rpcn_check" / "SCHEMA.md").write_text("not listed\n")
        self.skill = self.root / "skills" / "rpcn-test"
        self.skill.mkdir(parents=True)
        self.copy = self.skill / "scripts" / "rpcn_check.py"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def manifest(self, text: str, skill: Path | None = None) -> None:
        ((skill or self.skill) / "shared.txt").write_text(text)

    def copy_entries(self, out: dict) -> list[dict]:
        return [c for c in out["copies"] if c["state"] != "no-manifest"]

    def assert_invalid(self, *needles: str) -> dict:
        before = snapshot(self.root)
        for mode in ([], ["--check"]):
            code, out = run_sync(self.root, *mode)
            self.assertEqual(code, 2, out)
            self.assertFalse(out["ok"])
            self.assertTrue(out["errors"], out)
            joined = "\n".join(out["errors"])
            for needle in needles:
                self.assertIn(needle, joined)
        self.assertEqual(snapshot(self.root), before, "an invalid manifest wrote files")
        return out


class SyncAndCheck(TreeCase):
    def setUp(self) -> None:
        super().setUp()
        self.manifest("rpcn_check/rpcn_check.py scripts/rpcn_check.py\n")

    def test_sync_creates_copy_byte_for_byte_without_exec_bit(self) -> None:
        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["mode"], "sync")
        self.assertTrue(out["ok"])
        self.assertEqual(out["errors"], [])
        self.assertEqual(
            self.copy_entries(out),
            [{"skill": "rpcn-test", "source": "rpcn_check/rpcn_check.py",
              "dest": "scripts/rpcn_check.py", "state": "written"}],
        )
        self.assertEqual(self.copy.read_bytes(), SOURCE_BYTES)
        self.assertEqual(self.copy.stat().st_mode & 0o111, 0)

    def test_only_listed_files_are_copied(self) -> None:
        run_sync(self.root)
        files = sorted(p.relative_to(self.skill).as_posix() for p in self.skill.rglob("*") if p.is_file())
        self.assertEqual(files, ["scripts/rpcn_check.py", "shared.txt"])

    def test_in_sync_check_is_ok(self) -> None:
        run_sync(self.root)
        code, out = run_sync(self.root, "--check")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["mode"], "check")
        self.assertTrue(out["ok"])
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["ok"])

    def test_sync_when_in_sync_reports_ok(self) -> None:
        run_sync(self.root)
        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["ok"])

    def test_edited_copy_differs_then_sync_repairs(self) -> None:
        run_sync(self.root)
        data = bytearray(self.copy.read_bytes())
        data[0] ^= 1  # one byte changed
        self.copy.write_bytes(bytes(data))
        code, out = run_sync(self.root, "--check")
        self.assertEqual(code, 1, out)
        self.assertFalse(out["ok"])
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["differs"])
        self.assertEqual(self.copy.read_bytes(), bytes(data), "--check wrote a file")

        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["written"])
        code, out = run_sync(self.root, "--check")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.copy.read_bytes(), SOURCE_BYTES)

    def test_missing_copy_then_sync_repairs(self) -> None:
        code, out = run_sync(self.root, "--check")
        self.assertEqual(code, 1, out)
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["missing"])
        self.assertFalse(self.copy.exists(), "--check wrote a file")
        self.assertFalse(self.copy.parent.exists(), "--check created a folder")

        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["written"])
        code, _ = run_sync(self.root, "--check")
        self.assertEqual(code, 0)

    def test_sync_clears_exec_bit_on_existing_copy(self) -> None:
        self.copy.parent.mkdir()
        self.copy.write_bytes(b"old")
        self.copy.chmod(0o755)
        run_sync(self.root)
        self.assertEqual(self.copy.stat().st_mode & stat.S_IXUSR, 0)

    def test_sync_does_not_delete_unlisted_skill_files(self) -> None:
        extra = self.skill / "scripts" / "own.py"
        extra.parent.mkdir()
        extra.write_text("mine\n")
        run_sync(self.root)
        self.assertEqual(extra.read_text(), "mine\n")


class ManifestParsing(TreeCase):
    def test_comments_and_blank_lines_ignored(self) -> None:
        self.manifest(
            "# header comment\n"
            "\n"
            "   \n"
            "rpcn_check/rpcn_check.py scripts/rpcn_check.py  # trailing note\n"
            "# another\n"
        )
        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual([c["state"] for c in self.copy_entries(out)], ["written"])

    def test_nested_dest_folders_created(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py a/b/c/check.py\n")
        code, out = run_sync(self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual((self.skill / "a/b/c/check.py").read_bytes(), SOURCE_BYTES)

    def test_bad_source(self) -> None:
        self.manifest("# c\nrpcn_check/nope.py scripts/nope.py\n")
        self.assert_invalid("rpcn-test", "shared.txt:2", "nope.py")

    def test_source_that_is_a_folder_is_bad(self) -> None:
        self.manifest("rpcn_check scripts/rpcn_check\n")
        self.assert_invalid("shared.txt:1")

    def test_bad_source_writes_nothing_for_valid_lines(self) -> None:
        self.manifest(
            "rpcn_check/rpcn_check.py scripts/rpcn_check.py\n"
            "rpcn_check/nope.py scripts/nope.py\n"
        )
        self.assert_invalid("shared.txt:2")
        self.assertFalse(self.copy.exists())

    def test_escaping_dest_dotdot(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py ../x\n")
        self.assert_invalid("shared.txt:1", "../x")
        self.assertFalse((self.root / "skills" / "x").exists())

    def test_escaping_dest_dotdot_inside_path(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py scripts/../../x\n")
        self.assert_invalid("shared.txt:1")

    def test_escaping_dest_absolute(self) -> None:
        target = self.root / "abs-target"
        self.manifest(f"rpcn_check/rpcn_check.py {target}\n")
        self.assert_invalid("shared.txt:1", str(target))
        self.assertFalse(target.exists())

    def test_escaping_dest_tmp(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py /tmp/x\n")
        self.assert_invalid("shared.txt:1", "/tmp/x")

    def test_escaping_source(self) -> None:
        (self.root / "outside.py").write_text("x\n")
        self.manifest("../../outside.py scripts/outside.py\n")
        self.assert_invalid("shared.txt:1")

    def test_duplicate_dest(self) -> None:
        (self.shared / "other.md").write_text("other\n")
        self.manifest(
            "rpcn_check/rpcn_check.py scripts/rpcn_check.py\n"
            "other.md ./scripts/rpcn_check.py\n"
        )
        self.assert_invalid("duplicate dest", "scripts/rpcn_check.py")

    def test_malformed_one_field(self) -> None:
        self.manifest("# c\n\nrpcn_check/rpcn_check.py\n")
        self.assert_invalid("shared.txt:3", "malformed")

    def test_malformed_three_fields(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py scripts/a.py extra\n")
        self.assert_invalid("shared.txt:1", "malformed")

    def test_error_in_one_skill_blocks_all_writes(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py scripts/rpcn_check.py\n")
        other = self.root / "skills" / "rpcn-other"
        other.mkdir()
        self.manifest("missing.py scripts/missing.py\n", skill=other)
        self.assert_invalid("rpcn-other")
        self.assertFalse(self.copy.exists())


class NoManifest(TreeCase):
    def test_skill_without_manifest_is_skipped(self) -> None:
        self.manifest("rpcn_check/rpcn_check.py scripts/rpcn_check.py\n")
        bare = self.root / "skills" / "rpcn-bare"
        bare.mkdir()
        (bare / "SKILL.md").write_text("x\n")
        run_sync(self.root)
        for mode in ([], ["--check"]):
            code, out = run_sync(self.root, *mode)
            self.assertEqual(code, 0, out)
            self.assertTrue(out["ok"])
            self.assertIn(
                {"skill": "rpcn-bare", "source": None, "dest": None, "state": "no-manifest"},
                out["copies"],
            )
        self.assertEqual(sorted(p.name for p in bare.iterdir()), ["SKILL.md"])

    def test_only_skills_without_manifest(self) -> None:
        code, out = run_sync(self.root, "--check")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["copies"], [
            {"skill": "rpcn-test", "source": None, "dest": None, "state": "no-manifest"}
        ])


class RepoAsCommitted(unittest.TestCase):
    def test_repo_copies_in_sync(self) -> None:
        code, out = run_sync(REPO_ROOT, "--check")
        self.assertEqual(code, 0, out)
        states = {(c["skill"], c["dest"]): c["state"] for c in out["copies"]}
        self.assertEqual(states.get(("rpcn-test", "scripts/rpcn_check.py")), "ok")


if __name__ == "__main__":
    unittest.main(verbosity=2)
