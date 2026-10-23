---
title: 'Shared files synced into each skill with a drift check'
type: 'feature'
ticket: '3'
created: '2026-10-23'
status: done
baseline_revision: '9cb2ad170a674b6b25d110850f9ad3f775a81610'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `skills/rpcn-test/scripts/rpcn_check.py` is a hand copy, kept in step only by a `cmp` line in CI. Every new skill and shared file (formats in story 4, generated references in epic 4) would need another hand copy and another CI line.

**Approach:** One manifest per skill, `skills/<skill>/shared.txt`, lists which files from `tools/shared/` the skill carries and where. `tools/sync_shared.py` copies them byte-for-byte, and `--check` reports any copy that is missing or different without writing. CI runs `--check` instead of `cmp` (AD-2).

## Boundaries & Constraints

**Always:**
- **`shared.txt` format:** one mapping per line, `<source> <dest>`.
  - `<source>` is relative to `tools/shared/`, and `<dest>` is relative to the skill folder.
  - `#` starts a comment, and blank lines are ignored.
  - `rpcn-test` gets `rpcn_check/rpcn_check.py scripts/rpcn_check.py`.
- **Copying:** `sync_shared.py` copies byte-for-byte, creates destination folders, and keeps the executable bit off.
- **`--check`** changes nothing. It reports each drifted copy (`missing` or `differs`) and exits 1 when there is any drift.
- **Invalid manifest:** these are errors, exit 2, and nothing is written:
  - a source that does not exist
  - a destination outside the skill folder (absolute, or using `..`)
  - the same destination listed twice
  - a malformed line
- **Output:** a PEP 723 script, standard library only, run with `uv run` (AD-3). It prints one JSON object, `{"ok": bool, "mode": "sync"|"check", "copies": [{"skill","source","dest","state"}], "errors": [str]}`. `state` is `ok`, `missing`, `differs` or `written`.
- **`--root <dir>`** defaults to the repo root (the parent of `tools/`), so the tests can run against a temporary tree.
- **Skills without a manifest** are skipped, and listed in the output with `state` set to `no-manifest`.

**Never:**
- copying anything that isn't listed
- deleting files from skills
- touching `rpcn_check.py`'s code
- editing a copy by hand to fix drift: the fix is always `sync_shared.py`

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| In sync | copy identical to its source | `--check` exits 0, state `ok` | — |
| Edited copy | one byte changed in the skill copy | `--check` exits 1, state `differs` | — |
| Missing copy | the destination file was deleted | `--check` exits 1, state `missing` | — |
| Sync repairs | after an edit or a deletion | sync exits 0 with state `written`, and a later `--check` exits 0 | — |
| Bad source | `shared.txt` names a source that does not exist | exits 2, nothing written | error names the skill and the line |
| Escaping dest | `../x` or `/tmp/x` | exits 2, nothing written | error names the line |
| Duplicate dest | the same dest listed twice | exits 2 | error names the dest |
| Malformed line | one field, or three | exits 2 | error names the line number |
| Comments and blanks | `# note` and empty lines | ignored | — |
| No manifest | a skill folder with no `shared.txt` | skipped, state `no-manifest`, exit 0 | — |

</frozen-after-approval>

## Code Map

- **`skills/rpcn-test/scripts/rpcn_check.py`:** the current hand copy, byte-identical to `tools/shared/rpcn_check/rpcn_check.py`. `sync_shared.py` adopts it unchanged.
- **`tools/shared/rpcn_check/SCHEMA.md` and `tests/`:** stay in `tools/shared` and are not listed in any manifest. Only `rpcn_check.py` ships.
- **`.github/workflows/ci.yml`:** replace the step "Skill copies match the canonical rpcn_check.py" (`cmp …`) with `uv run tools/sync_shared.py --check`, and add a step for the new unit tests. Keep the other steps as they are.
- **`tools/fetch_rpcn.py`:** an example of the existing tool-script style (PEP 723 header, docstring, `uv run`).
- **`tools/shared/rpcn_check/tests/test_rpcn_check.py`:** the test style to follow (a unittest PEP 723 script, temporary directories, `subprocess` on `sys.executable`).
- **`README.md` "Development":** replace the "byte-identical copy" sentence with the sync command.

## Tasks & Acceptance

**Execution:**
- [x] `skills/rpcn-test/shared.txt` -- one mapping, `rpcn_check/rpcn_check.py scripts/rpcn_check.py`, with a comment header -- the first manifest
- [x] `tools/sync_shared.py` -- the sync and `--check` modes, validation, JSON output and `--root` -- the AD-2 sync
- [x] `tools/tests/test_sync_shared.py` -- a unittest PEP 723 script that builds temporary trees and covers every matrix row -- tests
- [x] `.github/workflows/ci.yml` -- drift check and sync tests in place of `cmp` -- CI enforces the copies
- [x] `README.md` -- the development note shows `uv run tools/sync_shared.py` and `--check` -- contributor guidance

**Acceptance Criteria:**
- Given the repo as committed, when `uv run tools/sync_shared.py --check` runs, then it exits 0 with `rpcn-test`'s copy in state `ok`.
- Given an edited `skills/rpcn-test/scripts/rpcn_check.py`, when CI runs, then the drift step fails; after `uv run tools/sync_shared.py`, it passes.

## Implementation Notes

- All manifests are parsed and validated before anything is written, so an error in any skill's `shared.txt` blocks writes for every skill (exit 2 in both modes).
- `#` strips to end of line, so trailing comments after a mapping are allowed; paths containing `#` are not supported.
- Sources are also rejected when absolute or using `..`, and must be files (not folders). A dest that is an existing folder is an error.
- Sync reports `ok` for copies already identical and `written` only for ones it rewrote. Writes are atomic (temp file + rename) with mode 0644.
- `no-manifest` entries carry `source: null, dest: null`.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 1 entry → patch (2 findings with one root cause), 5 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | The acceptance criterion's drift step is skipped, because the repo-state unit test fails first | low | patch | It shares a root cause with #2: the drift step runs last. The fix is to reorder the steps. |
| 2 | The drift step runs after fetch and the version tests, unlike the architecture's CI order | low | patch | AD-14 puts the drift check before the `rpcn_check` tests. A fetch failure would hide drift. |
| 3 | The executable bit isn't cleared on a copy whose bytes already match | low | reject | It only happens if someone runs chmod on the copy by hand. Comparing modes adds a branch. |
| 4 | A dest whose parent is an existing file crashes at write time | low | reject | It needs a deliberately odd manifest such as `SKILL.md/x`. Guarding against it adds a check. |
| 5 | I/O and argparse errors produce tracebacks, not JSON | low | reject | These are failures of the environment, not the manifest, and they fail loudly. Handling them adds branches. |
| 6 | A dest can overwrite `shared.txt` or `SKILL.md` | low | reject | It needs a manifest written that way on purpose. It would be caught in review, and the fix adds a guard. |
| 7 | Non-skill folders are reported as `no-manifest` | low | reject | Cosmetic. `skills/` holds only skill folders, and caches are gitignored. |

## Verification

**Commands:**
- `uv run tools/tests/test_sync_shared.py` -- expected: all pass
- `uv run tools/sync_shared.py --check` -- expected: exit 0
- `echo '#' >> skills/rpcn-test/scripts/rpcn_check.py && uv run tools/sync_shared.py --check; echo $?` -- expected: 1, state `differs`; then `uv run tools/sync_shared.py && uv run tools/sync_shared.py --check` -- expected: exit 0
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py` -- expected: still passes
