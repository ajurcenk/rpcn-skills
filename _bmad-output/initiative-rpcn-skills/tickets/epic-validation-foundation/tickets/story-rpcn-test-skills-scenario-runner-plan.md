---
title: 'rpcn-test-skills scenario runner'
type: 'feature'
ticket: '6'
created: '2026-10-29'
status: done
baseline_revision: '651b7bf4f3fb5f30d4bc2e9777025e537784b5b1'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md', '{project-root}/tools/shared/rpcn_check/SCHEMA.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Skills can only be checked by hand, with one-off headless runs, and there's no repeatable way to install them the way a user would, run them unattended, and check what they leave on disk. Long runs also look stuck, because nothing shows progress while they run.

**Approach:** Build the end-to-end test project `../rpcn-test-skills` (AD-13). It contains:
- a scenario format: `prompt.md`, `fixtures/` and `expect.toml`
- `run_scenarios.py`, which for each scenario and each run:
  1. copies the fixtures into a fresh run folder
  2. installs the skills with `npx skills`, from a local path or from a pushed git commit
  3. runs Claude Code headless, isolated from the user's own plugins
  4. prints one live progress line per tool call
  5. checks the results with the *installed* `rpcn_check`

It writes a results file and exits non-zero on any failure. The first scenario covers `rpcn-test` on a broken pipeline.

## Boundaries & Constraints

**Always:**
- **The runner:** `rpcn-test-skills/run_scenarios.py`, a PEP 723 script using only the standard library (it needs `tomllib`, so `requires-python = ">=3.11"`), run with `uv run`. Its options:
  - `--source local:<path>` (the default is `local:../rpcn-skills`) or `--source git:<commit>`
  - `--runs <n>` (default 3)
  - `--scenario <name>` (repeatable; default all)
- **Installing:** into each run folder with `npx -y skills add <src> -s <skills> -a claude-code -y --copy`.
  - `<src>` is the local path, or `https://github.com/ajurcenk/rpcn-skills/tree/<commit>` for `git:`, which was verified to work and records `ref` in `skills-lock.json`.
  - `<skills>` comes from `expect.toml` `install`.
  - The run folder's `skills-lock.json` is saved with the results, so each run records exactly what it tested.
- **Headless Claude:** `claude -p <prompt> --output-format stream-json --verbose --setting-sources project,local --strict-mcp-config --no-session-persistence --allowedTools <from expect.toml> --max-turns <from expect.toml>`, run with the run folder as the working directory.
  - `--setting-sources project,local` and `--strict-mcp-config` drop the user's own plugins, user-level skills and MCP servers. Verified: with them, only `rpcn-test` and Claude Code's built-ins are listed.
  - Each run has a wall-clock timeout (`expect.toml` `timeout_s`, default 300). On timeout the run fails, with the reason `timeout`.
- **Live progress:** one line per event, flushed straight away: `[<scenario> run <i>/<n> +<sec>s] <event>`. Events:
  - `install: ok|failed`
  - `skill: <name>` when the Skill tool is used
  - `tool <name>: <short detail>` for every other tool call
  - `done: turns=<n> cost=$<x>`
  - `check <name>: pass|fail <why>`, one per check
- **`expect.toml` checks:** each check runs only when it is configured.
  - **`skill`:** the expected skill was used (matched on the name, with or without a `plugin:` prefix).
  - **`[status]`:** the reply ends with exactly one fenced `json` block. Its fields match the expected values, for example `status = "complete"` and `checks.lint = "fail"`.
  - **`[[report]]`:** for each listed hand-off file, the installed skill's `rpcn_check.py hash --check <file>` is run, and `ready`, `verdict` and `pipeline_ready` must match.
  - **`[[lint]]`:** the installed skill's `rpcn_check.py lint <file>` is run, and `ok` must match.
  - **`unchanged`:** each listed fixture file is byte-identical after the run, which proves AD-6's "never edit the YAML".
- **Pass rule:** a scenario passes only when all of its runs pass every check.
- **Results:** `runs/<timestamp>/` holds `results.json` (source, commit or path, Claude Code version, per-run checks, turns, cost, duration and errors) and each run's folder, kept for inspection. A summary table goes to stdout. The exit code is 0 when every scenario passes, 1 when any check fails, and 2 for a usage or setup error (no `claude`, `npx` or `uv`, a bad `expect.toml`, or a source that doesn't exist).
- **The first scenario:** `scenarios/rpcn-test__lint_broken/`.
  - `fixtures/multi_error.yaml` is a copy of rpcn-skills' `tools/shared/rpcn_check/tests/fixtures/multi_error.yaml`.
  - The prompt says to lint that file, unattended.
  - `expect.toml` covers: skill `rpcn-test`; status `complete` with `checks.lint = "fail"`; report `multi_error.test-report.md` with `ready = true`, `verdict = "fail"` and `pipeline_ready = false`; lint of `multi_error.yaml` with `ok = false`; and `multi_error.yaml` unchanged.
- **Unit tests:** `tests/test_run_scenarios.py` (a unittest PEP 723 script) covers, with no Claude or npx calls:
  - status-block parsing: none, one, several, malformed JSON, text after the block
  - `expect.toml` validation
  - the skill-name match
  - per-check pass and fail
  - the pass rule
  - progress-line formatting

  It uses canned stream-json lines.
- **The project's own files:** `README.md` (what it is, requirements, how to run, how to add a scenario) and `.gitignore` (`runs/`, `.claude/skills/`, `.agents/skills/`, `__pycache__/`).

- **Decision (user, 2026-10-29), option (a):** `rpcn-test-skills` becomes a local git repository with no remote. Commit the runner, the scenario, the tests, `README.md` and `.gitignore`. The user's manual test files (`orders.yaml`, `orders.test-report.md`, the root `skills-lock.json`) go in `.gitignore` and stay untouched. The root `.claude/skills/` is already ignored. End the story with a local commit in that repository.

**Never:**
- skill source inside `rpcn-test-skills`
- touching the user's existing root files there (`orders.yaml`, `orders.test-report.md`, the root `.claude/skills/` and `skills-lock.json`)
- benchmark arms (story 10) and `run_evals.py` (story 11)
- `jq` or `pip`
- running Claude without the isolating flags

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| All pass | 3 runs, every check passes | summary `PASS 3/3`, exit 0 | — |
| One run fails | the report's verdict is wrong in run 2 | scenario `FAIL 2/3`, `check report: fail` naming the field, exit 1 | — |
| No status block | the reply has no json block | `check status: fail no status block` | — |
| Two status blocks | two fenced json blocks | `check status: fail expected exactly one` | — |
| Malformed block | invalid JSON in the block | `check status: fail` with the parse error | — |
| Wrong skill | a different skill, or none, was used | `check skill: fail` | — |
| Fixture edited | the run changed `multi_error.yaml` | `check unchanged: fail multi_error.yaml` | — |
| Timeout | the run goes past `timeout_s` | run fails with the reason `timeout`, the process is killed | — |
| Install fails | `npx skills add` exits non-zero | run fails at `install: failed` with its output tail, Claude isn't started | — |
| Bad expect.toml | an unknown key or a wrong type | exit 2 before any run, naming the file and key | — |
| Missing tool | `claude`, `npx` or `uv` not on PATH | exit 2 before any run | — |
| Git source | `--source git:<commit>` | the lock file records `ref` equal to `<commit>` | the install fails if the commit doesn't exist |

</frozen-after-approval>

## Code Map

- **Prototype to reuse:** this session's `scratchpad/check_skill.py` (at `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/bd9d3ddf-a468-4735-9b90-5afeab197960/scratchpad/check_skill.py`). It already streams `stream-json`, prints tool calls with elapsed time, reads `result` (`subtype`, `num_turns`, `total_cost_usd`) and runs `hash --check`. Reuse the event handling. Replace `--plugin-dir` with the `npx` install, and add the isolating flags.
- **Verified facts (2026-10-29):**
  - `npx skills add https://github.com/ajurcenk/rpcn-skills/tree/af4c1097e5f0bf920df3ee6e50f94f22e97e9ea8 -s rpcn-test -a claude-code -y --copy` installs into `./.claude/skills/rpcn-test`. The lock file has `"ref": "<sha>"` and `"sourceType": "github"`.
  - A local-path install gives the same `computedHash`.
  - `--setting-sources project,local` removes the user's plugins, user skills and all 73 MCP servers. Built-in skills remain.
  - Inside an installed skill, Claude invokes it as `rpcn-test`; under `--plugin-dir` it was `rpcn-skills:rpcn-test`.
- **The installed check script** in each run folder is `.claude/skills/rpcn-test/scripts/rpcn_check.py`. Use it, not rpcn-skills' copy, so the test checks what was installed.
- **Expected results** come from earlier runs: on `multi_error.yaml` a run took about 50 s and $0.40 over 18 turns, and the status block and report states match the scenario's `expect.toml`.
- **`allowedTools`** for the scenario: `Bash(uv run *)`, `Read`, `Write`, `Edit`, `Skill`.
- **Turns:** `max_turns = 30`.
- **`rpcn-test-skills` today:** it is not a git repository. It holds the user's manual test files (keep them as they are) and nothing else.

## Tasks & Acceptance

**Execution:**
- [x] `rpcn-test-skills/run_scenarios.py` -- runner per the Boundaries -- the AD-13 scenario runner
- [x] `rpcn-test-skills/scenarios/rpcn-test__lint_broken/{prompt.md,expect.toml,fixtures/multi_error.yaml}` -- the first scenario -- proves rpcn-test end to end
- [x] `rpcn-test-skills/tests/test_run_scenarios.py` -- unit tests for every matrix row that needs no Claude, plus parsing -- runner correctness
- [x] `rpcn-test-skills/README.md` -- usage and how to add a scenario -- entry point
- [x] `rpcn-test-skills/.gitignore` -- `runs/`, installed skill folders and the user's manual test files -- no test output or skill copies committed
- [x] `rpcn-test-skills` git -- `git init -b main` and a first local commit of the files above, with no remote -- history for the runner and scenarios

**Acceptance Criteria:**
- Given `uv run run_scenarios.py` (local source, 3 runs), when it finishes, then `rpcn-test__lint_broken` is `PASS 3/3` with live progress lines printed during the runs, and `runs/<ts>/results.json` records each run.
- Given `uv run run_scenarios.py --source git:<pushed rpcn-skills commit>`, when it finishes, then it is `PASS 3/3`, and each run's saved `skills-lock.json` has that commit as `ref`.
- Given `uv run tests/test_run_scenarios.py`, then every test passes.

## Implementation Notes

- The scratchpad prototype `check_skill.py` no longer existed; the stream-json handling was written fresh in `run_scenarios.py` (`StreamState`).
- Each run folder is `git init`-ed so it is its own project root and nothing from `rpcn-test-skills` (for example the user's root `.claude/skills/`) is picked up. The smoke run's init event listed only `rpcn-test` plus built-in skills, and 0 MCP servers.
- For `git:<commit>`, install fails unless every installed skill's lock entry has `ref` equal to the commit.
- A run also fails when Claude's result is not `success` (for example `error_max_turns`) or no result event arrives; checks still run and are recorded.
- `[[report]]`/`[[lint]]` use the first `install` skill's `rpcn_check.py`; an optional per-entry `skill` key picks another installed skill.
- The rpcn-test-skills root had no `.gitignore` before, so `.claude/skills/` was not actually ignored yet; the new `.gitignore` covers it.
- Verified: 57 unit tests pass; one `--runs 1` local smoke run passed every check (15 turns, $0.29, 46 s), exit 0. Local commit `f402499` in rpcn-test-skills, no remote.
- **Verification (orchestrator, 2026-10-29),** with live progress shown in the conversation:
  - **Local source:** `uv run run_scenarios.py` gave `PASS 3/3` (16.3 turns, $0.29 and 46 s on average), in `runs/20261029-102543`.
  - **Git source:** `--source git:651b7bf4f3fb5f30d4bc2e9777025e537784b5b1` gave `PASS 3/3` (15.3 turns, $0.30 and 50 s), in `runs/20261029-102811`. All three `run-<i>.skills-lock.json` files record `ref` as that commit.
  - **Unit tests:** 57 pass.
  - **Observed:** every run spends 1–3 turns on compound shell commands (`S=…;`, `cd … &&`, `cat`, heredocs) that `Bash(uv run *)` refuses before Claude falls back to plain calls. That's a skill wording issue for rpcn-test, not a runner defect.
- **After the review fixes:** rpcn-test-skills commit `a7bdecd`, 63 unit tests pass, and a `--runs 1` smoke run gives `PASS 1/1` (16 turns, $0.28, 43 s, `runs/20261029-103449`).

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 8 → patch, 3 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | `[status]` nested keys and types aren't validated | medium | patch | `STATUS_KEYS` checks only the first level, against the matrix row "Bad expect.toml → exit 2". |
| 2 | The `[[report]]` guard counts keys, so a check can pass with nothing to check | medium | patch | `{file, skill}` gets past it, and `evaluate_report` then passes on any JSON. |
| 3 | `git` isn't in the preflight check, and `git init`'s return code is ignored | low | patch | It gives a traceback mid-run, or a run without isolation. |
| 4 | Unexpected exceptions exit 1, the code for a failed check | low | patch | A crash can't be told apart from a failed check. The fix is a top-level catch with exit 2. |
| 5 | Results folders started in the same second collide | low | patch | `exist_ok=False` on a timestamp that changes only every second. |
| 6 | The timeout waits for stdout to close, not for the process | low | reject | It needs a background child holding stdout open. `allowed_tools` blocks background shells. The fix would add branches. |
| 7 | `timeout_s = inf` or `nan` passes validation | low | reject | It needs a deliberately odd `expect.toml`. Guarding against it adds a check. |
| 8 | `run_rpcn_check` loses the timeout and the stderr reason | low | patch | A direct correction that keeps the reason. |
| 9 | The README gives the wrong stderr file name | low | patch | The file on disk is `run-<i>.stream.stderr.txt`. |
| 10 | The unknown-scenario test depends on the machine | low | patch | It can pass through the missing-source path. The fix passes an explicit temporary source. |
| 11 | Fence parsing: an unclosed fence, or a json fence nested in a markdown sample | low | reject | The status block's shape is fixed by AD-8 and the skill. Neither case appears in real runs, and handling them adds parser branches. |

## Verification

**Who runs what:** the implementer runs only the unit tests, plus at most one `--runs 1` smoke run to confirm the runner starts. The orchestrator runs the full 3-run local and git-source checks, so the user can watch the live progress.

**Commands** (run from `rpcn-test-skills`):
- `uv run tests/test_run_scenarios.py` -- expected: all pass
- `uv run run_scenarios.py` -- expected: live progress, `PASS 3/3`, exit 0
- `uv run run_scenarios.py --source git:651b7bf4f3fb5f30d4bc2e9777025e537784b5b1` (the latest pushed rpcn-skills commit) -- expected: `PASS 3/3`, `ref` recorded
