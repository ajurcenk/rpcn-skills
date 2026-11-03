---
title: 'Skill validator with the base rules'
type: 'feature'
ticket: '9'
created: '2026-11-03'
status: done
baseline_revision: '570732bb1c492996697818806cd5031f134f5107'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Nothing checks a skill's shape before it merges. A skill could take a name that clashes with `/rpcn:*` or `/redpanda:*`, reuse a retired name, break the AD-9 description format, name a reference file that doesn't exist, or drop its Next step, and CI would stay green.

**Approach:** Add `tools/validate_skills.py`. It checks every `skills/*/` folder against the AD-9 and AD-10 base rules, using `tools/clash-list.txt` and a new `retired.toml`, and names the rule each failure breaks. It runs as the first CI step, and its unit tests run in CI too. `rpcn-test` must pass as it is, so nothing under `skills/` changes and no new eval record is needed.

## Boundaries & Constraints

**Always:**
- Output is one JSON object: `{"ok", "skills": [{"skill", "errors": [{"rule", "message"}], "warnings": [{"rule", "message"}]}], "errors": [str]}`.
- Exit codes:
  - 0: there are no rule errors (warnings are allowed).
  - 1: some skill breaks a rule.
  - 2: the validator can't run, because `clash-list.txt` or `retired.toml` is missing or malformed, or `skills/` is absent.
- `--root <dir>` is supported for tests, as in `sync_shared.py`.
- The rule ids are `name`, `clash`, `retired`, `frontmatter`, `description`, `size`, `file-refs`, `next` and `stray-files`.

**Never:**
- Epic 4's checks: the version stamps against `plugin.json`, and the deprecated-component scan.
- Checking eval case folders.
- Editing anything under `skills/`.
- Fetching the reference repos at run time. The clash list is a committed file.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Current repo | `skills/rpcn-test` as is | exit 0. Warnings: `size` (about 1,280 tokens > 1,200) and `file-refs` (an orphan `references/design-format.md`) | none |
| Bad name | folder `rpcn-x`, but frontmatter `name: rpcn-y`; or a name without the `rpcn-` prefix, with upper case, or longer than 64 characters | `name` error | exit 1 |
| Clash | `rpcn-search` (it matches `rpcn:search`), or a `rpcn-connect` whose part after the prefix is in the list | `clash` error | exit 1 |
| Retired | the name is listed in `retired.toml` | `retired` error | exit 1 |
| Frontmatter | missing `name`/`description`, a key outside the spec set, or YAML that doesn't parse | `frontmatter` error | exit 1 |
| Description | longer than 1,024 characters, no `Use when the user says "…"` with a quoted phrase, or `use rpcn-<x>` naming a skill that doesn't exist | `description` error | exit 1 |
| Size | estimated tokens (characters ÷ 4) above 1,200 | `size` warning only | exit 0 |
| File refs | `references/…` or `scripts/…` named in SKILL.md but missing, or a nested `references/a/b.md` | `file-refs` error. A reference file SKILL.md never names is only a warning. | exit 1 |
| Next | no `## Next` heading, or a `## Step` heading after it | `next` error | exit 1 |
| Stray files | `__pycache__/`, `*.pyc` or `.DS_Store` inside a skill | `stray-files` error | exit 1 |
| Setup | `clash-list.txt` or `retired.toml` is missing or malformed | `errors` lists why | exit 2 |

**Decision (2026-11-03):** `shared.txt` stays in each skill folder, where AD-2 and the spine layout put it. The validator neither fails nor warns on it.

</frozen-after-approval>

## Code Map

- `tools/sync_shared.py`: copy its PEP 723 header, docstring style, `--root`, JSON print and exit codes. Don't modify it.
- `tools/tests/test_sync_shared.py`: follow its unittest style, which runs the script in a subprocess against temp trees.
- `skills/rpcn-test/SKILL.md`: frontmatter keys `name`, `description`, `compatibility`, `license` and `metadata`. It has `## Next` followed by `## Status block (headless only)`, with no step after Next. The description is single-quoted YAML with embedded `"…"` phrases. It's 5,124 characters.
- The spec frontmatter keys are `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`.
- Sources for the clash list:
  - **Connect plugin:** `~/projects/redpanda-replicator/v4.112.0/connect/.claude-plugin/plugins/redpanda-connect`, at `f15e3064a4e4aa4edc47f3b0f87c53d1572189fc`. Its plugin is `redpanda-connect` and its marketplace `redpanda-connect-plugins`. Its skills are `bloblang-authoring`, `component-search` and `pipeline-assistant`, and its commands are `rpcn:search`, `rpcn:blobl` and `rpcn:pipeline`.
  - **Skills repo:** `~/projects/skills`, at `a4562333b774d963066e11dfa1282646b8490550`. Its plugin is `redpanda` and its marketplace `redpanda-skills`. Its 33 skills are under `skills/*/SKILL.md` (`adp`, `cloud-*`, `connect`, `connect-cdc-*`, `connect-debugging`, `rpk*`, `sql*`, `streaming*`). It has no commands.
- `.github/workflows/ci.yml`: add the validator as the first step, before the drift check (spine CI order), and add the validator's tests after the `eval_record` tests.

## Tasks & Acceptance

**Execution:**
- [x] `tools/clash-list.txt`: one name per line, with `#` comments. The header names each source repo and its commit, and how to refresh the list.
- [x] `retired.toml`: a comment that documents `[[retired]] name / replaced_by / version`, and no entries yet.
- [x] `tools/validate_skills.py`: the rules from the matrix. It uses PEP 723 with `requires-python >=3.11` (for `tomllib`) and `pyyaml` for frontmatter.
- [x] `tools/tests/test_validate_skills.py`: a temp-tree fixture per matrix row, each asserting the exit code and the rule id. Add one test that runs against the real repo and expects exit 0.
- [x] `.github/workflows/ci.yml`: add the two steps.

**Acceptance Criteria:**
- Given this repo, when `uv run tools/validate_skills.py` runs, then it exits 0 and reports `rpcn-test` with no errors.
- Given a pull request whose skill breaks any rule, when CI runs, then the validator step fails and names the rule.

## Implementation Notes

- **Skills repo count:** the skills repo has 32 skills at `a4562333`, not 33. The clash list holds all 32, plus the plugin and marketplace names of both sets.
- **`${CLAUDE_SKILL_DIR}/scripts/…`:** a path written after this variable still matches as a skill-relative path, so a missing script is still caught after the lookbehind fix.
- **Results:** 49 validator tests pass. On the real repo the validator exits 0, with the two expected warnings.

## Review Triage Log

Pass 1 (quick): 0 high, 1 medium, 4 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `REF_RE` matches a `scripts/` or `references/` segment inside URLs and longer paths, and keeps a `#fragment` | medium | patch | Confirmed: `https://…/scripts/foo.sh` gave `scripts/foo.sh`, and `references/x.md#codes` kept its `#codes`. Fixed by extending the lookbehind, with a `${CLAUDE_SKILL_DIR}/` exception, and by dropping fragments. Three tests added. |
| The real-repo test does not assert the two expected warnings | low | patch | Matrix row "Current repo" names both. The fix is a direct assertion, now added. |
| Frontmatter that opens but never closes is reported as "does not open" | low | patch | Confirmed: `split_frontmatter('---\nname: x\n')` returns `(None, …)`. The message is fixed and a test added. |
| Nested or info-string fences can mis-toggle the fence state in `headings()` | low | reject | Unlikely in a SKILL.md that is about 800 tokens long, and a fix needs CommonMark fence-length tracking, which adds complexity. |
| Non-skill dirs or files directly under `skills/` (`__pycache__`, `.DS_Store`) aren't reported as `stray-files` | low | reject | Unlikely: `__pycache__` is gitignored, and nothing runs Python from `skills/`. A fix adds a new top-level branch. |

## Design Notes

- **Normalizing names for the clash check:** lower-case each name and replace `:` and `_` with `-`. Then check both the full name and the part after `rpcn-`. So `rpcn-search` clashes with `rpcn:search`, and `rpcn-connect` with the skills repo's `connect`. None of the planned jobs (design, author, test, tune, scale, deploy, migrate) is in the list.
- **The `size` rule is only a warning**, because AD-9 says "warns". The ÷ 4 estimate puts `rpcn-test` at about 1,280 tokens, so it warns today. That's true and harmless.
- **Python 3.11:** the spine's `>=3.10` floor binds the shipped `rpcn_check`. This tool is developer-only, so 3.11 is fine.

## Verification

**Commands:**
- `uv run tools/validate_skills.py`: exits 0, with `rpcn-test` errors `[]`.
- `uv run tools/tests/test_validate_skills.py`: all pass.
- `uv run tools/sync_shared.py --check && uv run tools/eval_record_check.py`: still green, with `skills/` untouched.
