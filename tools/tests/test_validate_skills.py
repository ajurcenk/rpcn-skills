# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""Unit tests for tools/validate_skills.py, run against temporary repo trees.

Run: uv run tools/tests/test_validate_skills.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "validate_skills.py"
REPO_ROOT = SCRIPT.parent.parent

CLASH_LIST = """\
# test clash list
redpanda-connect
rpcn:search
component_search
connect
"""

RETIRED = """\
[[retired]]
name = "rpcn-old"
replaced_by = "rpcn-test"
version = "0.1.0"
"""

DESCRIPTION = (
    'Checks pipelines. Use when the user says "lint my pipeline" or "test it". '
    "Not for writing pipelines."
)

BODY = """\
# {name}

## Step 1: Lint

Read `references/guide.md`, then run:

```bash
uv run ${{CLAUDE_SKILL_DIR}}/scripts/tool.py lint
```

## Next

- Errors found: re-run {name}.
"""


def run_validate(root: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True, timeout=60,
    )
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout is not JSON: {proc.stdout!r} {proc.stderr!r}") from exc
    return proc.returncode, out


def yaml_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


class TreeCase(unittest.TestCase):
    """A temporary repo with a clash list, retired.toml and one valid skill."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "tools").mkdir()
        (self.root / "tools" / "clash-list.txt").write_text(CLASH_LIST)
        (self.root / "retired.toml").write_text(RETIRED)
        (self.root / "skills").mkdir()
        self.skill = self.make_skill("rpcn-test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def make_skill(
        self, folder: str, *, name: str | None = None, description: str = DESCRIPTION,
        body: str | None = None, extra_frontmatter: str = "",
    ) -> Path:
        skill = self.root / "skills" / folder
        (skill / "references").mkdir(parents=True)
        (skill / "scripts").mkdir()
        (skill / "references" / "guide.md").write_text("# guide\n")
        (skill / "scripts" / "tool.py").write_text("print('hi')\n")
        self.write_skill_md(
            skill, name=folder if name is None else name, description=description,
            body=body, extra_frontmatter=extra_frontmatter,
        )
        return skill

    def write_skill_md(
        self, skill: Path, *, name: str, description: str = DESCRIPTION,
        body: str | None = None, extra_frontmatter: str = "",
    ) -> None:
        text = (
            "---\n"
            f"name: {name}\n"
            f"description: {yaml_quote(description)}\n"
            "license: Apache-2.0\n"
            f"{extra_frontmatter}"
            "---\n\n"
            + (BODY.format(name=name) if body is None else body)
        )
        (skill / "SKILL.md").write_text(text)

    def validate(self) -> tuple[int, dict]:
        return run_validate(self.root)

    def report(self, out: dict, skill: str) -> dict:
        for entry in out["skills"]:
            if entry["skill"] == skill:
                return entry
        raise AssertionError(f"no report for {skill!r}: {out}")

    def assert_rule_error(self, skill: str, rule: str, *, fragment: str | None = None) -> dict:
        code, out = self.validate()
        self.assertEqual(code, 1, out)
        self.assertFalse(out["ok"])
        rep = self.report(out, skill)
        hits = [e for e in rep["errors"] if e["rule"] == rule]
        self.assertTrue(hits, f"no {rule!r} error for {skill}: {rep}")
        if fragment is not None:
            self.assertTrue(
                any(fragment in e["message"] for e in hits),
                f"no {rule!r} message containing {fragment!r}: {hits}",
            )
        return rep


class CleanTree(TreeCase):
    def test_valid_skill_passes_with_no_warnings(self) -> None:
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        self.assertEqual(
            out, {"ok": True, "skills": [{"skill": "rpcn-test", "errors": [], "warnings": []}],
                  "errors": []},
        )

    def test_shared_txt_is_neither_error_nor_warning(self) -> None:
        (self.skill / "shared.txt").write_text("rpcn_check/rpcn_check.py scripts/tool.py\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        rep = self.report(out, "rpcn-test")
        self.assertEqual((rep["errors"], rep["warnings"]), ([], []))


class NameRule(TreeCase):
    def test_frontmatter_name_differs_from_folder(self) -> None:
        self.write_skill_md(self.skill, name="rpcn-other")
        self.assert_rule_error("rpcn-test", "name", fragment="does not match folder")

    def test_missing_prefix(self) -> None:
        self.make_skill("tester")
        self.assert_rule_error("tester", "name", fragment="does not start with")

    def test_upper_case(self) -> None:
        self.make_skill("rpcn-Tester")
        self.assert_rule_error("rpcn-Tester", "name", fragment="upper-case")

    def test_longer_than_64(self) -> None:
        long = "rpcn-" + "a" * 60
        self.make_skill(long)
        self.assert_rule_error(long, "name", fragment="over 64")

    def test_bad_characters(self) -> None:
        self.make_skill("rpcn-te--st")
        self.assert_rule_error("rpcn-te--st", "name")


class ClashRule(TreeCase):
    def test_full_name_matches_command(self) -> None:
        self.make_skill("rpcn-search")
        self.assert_rule_error("rpcn-search", "clash", fragment="rpcn-search")

    def test_part_after_prefix_matches(self) -> None:
        self.make_skill("rpcn-connect")
        self.assert_rule_error("rpcn-connect", "clash", fragment="'connect'")

    def test_underscore_normalized(self) -> None:
        self.make_skill("rpcn-component-search")
        self.assert_rule_error("rpcn-component-search", "clash")


class RetiredRule(TreeCase):
    def test_retired_name(self) -> None:
        self.make_skill("rpcn-old")
        self.assert_rule_error("rpcn-old", "retired")


class FrontmatterRule(TreeCase):
    def test_missing_name(self) -> None:
        (self.skill / "SKILL.md").write_text(
            f"---\ndescription: {yaml_quote(DESCRIPTION)}\n---\n\n" + BODY.format(name="rpcn-test")
        )
        self.assert_rule_error("rpcn-test", "frontmatter", fragment="'name'")

    def test_missing_description(self) -> None:
        (self.skill / "SKILL.md").write_text(
            "---\nname: rpcn-test\n---\n\n" + BODY.format(name="rpcn-test")
        )
        self.assert_rule_error("rpcn-test", "frontmatter", fragment="'description'")

    def test_key_outside_spec(self) -> None:
        self.write_skill_md(self.skill, name="rpcn-test", extra_frontmatter="author: me\n")
        self.assert_rule_error("rpcn-test", "frontmatter", fragment="author")

    def test_spec_keys_allowed(self) -> None:
        self.write_skill_md(
            self.skill, name="rpcn-test",
            extra_frontmatter='compatibility: "uv"\nmetadata:\n  plugin-version: "0.1.0"\n'
            "allowed-tools: Bash\n",
        )
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_yaml_does_not_parse(self) -> None:
        (self.skill / "SKILL.md").write_text(
            "---\nname: rpcn-test\ndescription: 'unterminated\n  : [\n---\n\n"
            + BODY.format(name="rpcn-test")
        )
        self.assert_rule_error("rpcn-test", "frontmatter", fragment="not valid YAML")

    def test_frontmatter_never_closed(self) -> None:
        (self.skill / "SKILL.md").write_text(
            f"---\nname: rpcn-test\ndescription: {yaml_quote(DESCRIPTION)}\n\n"
            + BODY.format(name="rpcn-test")
        )
        self.assert_rule_error("rpcn-test", "frontmatter", fragment="never closed")

    def test_no_frontmatter(self) -> None:
        (self.skill / "SKILL.md").write_text(BODY.format(name="rpcn-test"))
        self.assert_rule_error("rpcn-test", "frontmatter")


class DescriptionRule(TreeCase):
    def test_too_long(self) -> None:
        self.write_skill_md(self.skill, name="rpcn-test", description=DESCRIPTION + " x" * 520)
        self.assert_rule_error("rpcn-test", "description", fragment="over 1024")

    def test_no_use_when_phrase(self) -> None:
        self.write_skill_md(self.skill, name="rpcn-test", description="Checks pipelines.")
        self.assert_rule_error("rpcn-test", "description", fragment="Use when the user says")

    def test_use_when_without_quoted_phrase(self) -> None:
        self.write_skill_md(
            self.skill, name="rpcn-test",
            description="Checks pipelines. Use when the user says lint my pipeline.",
        )
        self.assert_rule_error("rpcn-test", "description", fragment="Use when the user says")

    def test_use_names_missing_sibling(self) -> None:
        self.write_skill_md(
            self.skill, name="rpcn-test",
            description=DESCRIPTION + " Not for designing — use rpcn-design.",
        )
        self.assert_rule_error("rpcn-test", "description", fragment="rpcn-design")

    def test_use_names_existing_sibling(self) -> None:
        self.make_skill("rpcn-design")
        self.write_skill_md(
            self.skill, name="rpcn-test",
            description=DESCRIPTION + " Not for designing — use rpcn-design.",
        )
        code, out = self.validate()
        self.assertEqual(code, 0, out)


class SizeRule(TreeCase):
    def test_over_budget_is_warning_only(self) -> None:
        body = BODY.format(name="rpcn-test") + "\nfiller " * 800
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        rep = self.report(out, "rpcn-test")
        self.assertEqual(rep["errors"], [])
        self.assertEqual([w["rule"] for w in rep["warnings"]], ["size"])


class FileRefsRule(TreeCase):
    def test_missing_reference(self) -> None:
        (self.skill / "references" / "guide.md").unlink()
        self.assert_rule_error("rpcn-test", "file-refs", fragment="references/guide.md")

    def test_missing_script(self) -> None:
        (self.skill / "scripts" / "tool.py").unlink()
        self.assert_rule_error("rpcn-test", "file-refs", fragment="scripts/tool.py")

    def test_nested_reference_named(self) -> None:
        nested = self.skill / "references" / "a"
        nested.mkdir()
        (nested / "b.md").write_text("x\n")
        body = BODY.format(name="rpcn-test") + "\nAlso read `references/a/b.md`.\n"
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        self.assert_rule_error("rpcn-test", "file-refs", fragment="one level deep")

    def test_nested_reference_folder_unnamed(self) -> None:
        nested = self.skill / "references" / "a"
        nested.mkdir()
        (nested / "b.md").write_text("x\n")
        self.assert_rule_error("rpcn-test", "file-refs", fragment="nested")

    def test_orphan_reference_is_warning_only(self) -> None:
        (self.skill / "references" / "orphan.md").write_text("x\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        rep = self.report(out, "rpcn-test")
        self.assertEqual(rep["errors"], [])
        self.assertEqual(
            rep["warnings"],
            [{"rule": "file-refs", "message": "references/orphan.md is never named in SKILL.md"}],
        )

    def test_patterns_and_sentence_ends_are_ignored(self) -> None:
        body = BODY.format(name="rpcn-test") + (
            "\nGenerated ones are `references/generated-<kind>.json`. "
            "See references/guide.md.\n"
        )
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)


    def test_url_with_scripts_segment_is_ignored(self) -> None:
        body = BODY.format(name="rpcn-test") + (
            "\nSee https://github.com/x/blob/main/scripts/foo.sh.\n"
        )
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_longer_path_with_scripts_segment_is_ignored(self) -> None:
        body = BODY.format(name="rpcn-test") + (
            "\nIts source is `tools/shared/rpcn_check/scripts/x.py`.\n"
        )
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_link_fragment_is_dropped(self) -> None:
        (self.skill / "references" / "codes.md").write_text("x\n")
        body = BODY.format(name="rpcn-test") + "\nSee [x](references/codes.md#codes).\n"
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)
        rep = self.report(out, "rpcn-test")
        self.assertEqual((rep["errors"], rep["warnings"]), ([], []))


class NextRule(TreeCase):
    def test_no_next_heading(self) -> None:
        body = BODY.format(name="rpcn-test").replace("## Next", "## Then")
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        self.assert_rule_error("rpcn-test", "next", fragment="no '## Next'")

    def test_step_after_next(self) -> None:
        body = BODY.format(name="rpcn-test") + "\n## Step 2: More\n\nText.\n"
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        self.assert_rule_error("rpcn-test", "next", fragment="Step 2")

    def test_other_section_after_next_is_fine(self) -> None:
        body = BODY.format(name="rpcn-test") + (
            "\n## Status block (headless only)\n\n```md\n## Step 9: in a fence\n```\n"
        )
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_next_only_inside_fence_does_not_count(self) -> None:
        body = BODY.format(name="rpcn-test").replace("## Next", "```\n## Next\n```")
        self.write_skill_md(self.skill, name="rpcn-test", body=body)
        self.assert_rule_error("rpcn-test", "next")


class StrayFilesRule(TreeCase):
    def test_pycache(self) -> None:
        cache = self.skill / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "tool.cpython-311.pyc").write_bytes(b"\0")
        rep = self.assert_rule_error("rpcn-test", "stray-files", fragment="__pycache__/")
        self.assertEqual(len([e for e in rep["errors"] if e["rule"] == "stray-files"]), 1)

    def test_pyc(self) -> None:
        (self.skill / "scripts" / "tool.pyc").write_bytes(b"\0")
        self.assert_rule_error("rpcn-test", "stray-files", fragment="tool.pyc")

    def test_ds_store(self) -> None:
        (self.skill / ".DS_Store").write_bytes(b"\0")
        self.assert_rule_error("rpcn-test", "stray-files", fragment=".DS_Store")


class Setup(TreeCase):
    def assert_setup_error(self, fragment: str) -> None:
        code, out = self.validate()
        self.assertEqual(code, 2, out)
        self.assertFalse(out["ok"])
        self.assertTrue(any(fragment in e for e in out["errors"]), out)

    def test_clash_list_missing(self) -> None:
        (self.root / "tools" / "clash-list.txt").unlink()
        self.assert_setup_error("clash-list.txt is missing")

    def test_clash_list_malformed(self) -> None:
        (self.root / "tools" / "clash-list.txt").write_text("connect\ntwo names\n")
        self.assert_setup_error("clash-list.txt:2")

    def test_clash_list_empty(self) -> None:
        (self.root / "tools" / "clash-list.txt").write_text("# nothing\n")
        self.assert_setup_error("lists no names")

    def test_retired_missing(self) -> None:
        (self.root / "retired.toml").unlink()
        self.assert_setup_error("retired.toml is missing")

    def test_retired_not_toml(self) -> None:
        (self.root / "retired.toml").write_text("[[retired]\nname = \n")
        self.assert_setup_error("not valid TOML")

    def test_retired_entry_without_name(self) -> None:
        (self.root / "retired.toml").write_text('[[retired]]\nreplaced_by = "rpcn-x"\n')
        self.assert_setup_error("no string 'name'")

    def test_retired_empty_file_is_fine(self) -> None:
        (self.root / "retired.toml").write_text("# none yet\n")
        code, out = self.validate()
        self.assertEqual(code, 0, out)

    def test_skills_folder_absent(self) -> None:
        import shutil
        shutil.rmtree(self.root / "skills")
        self.assert_setup_error("no skills folder")


class RealRepo(unittest.TestCase):
    def test_repo_passes(self) -> None:
        code, out = run_validate(REPO_ROOT)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["ok"])
        rep = next(s for s in out["skills"] if s["skill"] == "rpcn-test")
        self.assertEqual(rep["errors"], [])
        rules = {w["rule"] for w in rep["warnings"]}
        # Story 2.3 brought SKILL.md under the 1,200-token budget (AD-9).
        self.assertNotIn("size", rules)
        self.assertIn("file-refs", rules)
        self.assertTrue(
            any("references/design-format.md" in w["message"] for w in rep["warnings"]
                if w["rule"] == "file-refs"),
            rep,
        )

    def test_rpcn_author_has_no_warnings(self) -> None:
        # Story 2.4: the new skill is clean, and names its sibling in "Not for".
        code, out = run_validate(REPO_ROOT)
        self.assertEqual(code, 0, out)
        rep = next(s for s in out["skills"] if s["skill"] == "rpcn-author")
        self.assertEqual(rep["errors"], [])
        self.assertEqual(rep["warnings"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
