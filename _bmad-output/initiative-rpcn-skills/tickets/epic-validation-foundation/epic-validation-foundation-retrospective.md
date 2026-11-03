---
epic: epic-validation-foundation
date: 2026-11-03
verdict: accepted-with-open-items
criteria: declared
headless: false
---

# Retrospective: Validation foundation (epic 1)

## Epic summary

- **Epic:** `epic-validation-foundation`, with 12 stories. All are `done`. None was left at `built`, and none was unfinished (`pending_tickets` is empty).
- **Criteria:** declared. The epic file has Requirements R1 to R11 and a Done when list. R1 was re-rendered on 2026-11-03, when the marketplace install channel was dropped.
- **Going-in concerns:** none raised by the user.
- **History:** linear, with no merges. Each range below runs from one plan's baseline to the next plan's baseline, in the order the builds started.

| Story | Range | Commits | Files | Notes |
|---|---|---|---|---|
| 1.1 | `363e3f34..fbe04fe2` | 4 | 13 | |
| 1.2 | `fbe04fe2..9cb2ad17` | 1 | 15 | |
| 1.3 | `9cb2ad17..bb8ee06a` | 2 | 7 | |
| 1.4 | `bb8ee06a..650bf257` | 2 | 14 | |
| 1.5 | `650bf257..651b7bf4` | 2 | 4 | |
| 1.6 | `651b7bf4..6c027ecb` | 3 | 2 | Code is in `rpcn-test-skills` (`f402499`, `a7bdecd`) |
| 1.10 | `6c027ecb..6290d06b` | 3 | 1 | Code is in `rpcn-test-skills` (`c637dc6`, `fb88bbf`, `ec9bcbe`, `91f8497`) |
| 1.7 | `6290d06b..5160bf02` | 3 | 36 | |
| 1.11 | `5160bf02..050ba1c1` | 3 | 8 | |
| 1.8 | `050ba1c1..570732bb` | 2 | 13 | |
| 1.9 | `570732bb..03e66fd7` | 2 | 6 | |
| 1.12 | `03e66fd7..35a8bb5` | 5 | 35 | Inferred end. It includes the 2026-11-03 replan commits `c62ed12`, `40cf866` and `35a8bb5`, which belong to this epic's R1. |

### Evidence inventory

- **Available:**
  - The epic file and its memlog.
  - All 12 plans. Their Review Triage Logs, Implementation Notes and Plan Change Logs are present where a review ran.
  - The per-range `git_evidence` JSON, in the session scratchpad.
  - The architecture companion `architecture-rpcn-skills/architecture-rpcn-skills.md`, with its reviews.
  - `deferred-work.md`.
  - Eval records in `evals/results/*.json`.
  - The local repo `rpcn-test-skills`, which has 6 commits and no remote.
- **Story files:** none. All 12 stories were built from their `tickets.toml` entries.
- **Run folders in the epic folder:** none.
- **Previous retrospective:** none, because this is the first epic.
- **Session logs:** one long session transcript for stories 1.1 to 1.12, `~/.claude/projects/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f.jsonl`. It was compacted several times, so the earlier turns survive only as summaries.
- **Narrowed:** `rpcn-test-skills` has no remote, so its code is never seen by this repo's CI or its review history. It is reviewed here only through its local commits.

## Findings

Phase 2 ran three ways:
- **Aggregate views:** one subagent.
- **Diff review:** `bmad-review` with the adversarial, edge-case and verification-gap lenses, over the epic diff and the whole `rpcn-test-skills` repo.
- **Behavior check:** run by me.

The diff review's baseline: all unit suites pass, with rpcn_check 134, sync_shared 25, eval_gate 20, eval_record 34, validate_skills 49 and run_scenarios 116 tests. I re-checked F1 and F7 at their sources. The rest are subagent reports, each citing its source. **[X]** marks a finding that crosses a story boundary.

### Seams between stories (diff review)

| # | Finding | Source | Disposition |
|---|---|---|---|
| F1 [X] 1.4/1.5 | A pipeline in a subfolder never gets a ready report. The skill hashes `pipes/orders.yaml` from the project root, because it can't `cd`. `hash --check` then resolves inputs against the report's own folder and looks for `pipes/pipes/orders.yaml`. **Re-checked.** | `rpcn_check.py:550-555` (`os.path.join(folder, item["file"])`), `SKILL.md:52` | fix now (A1) |
| F2 [X] 1.2/1.5 | Two SKILL.md rules clash. The general "exit 2 from any call → write no report" rule fights Step 5's "fix it once, then draft". A malformed header, or a re-lint timeout, aborts a run whose lint has already finished. | `SKILL.md` Step 1 vs Step 5, `rpcn_check.py:531-560` | fix now (A1) |
| F3 1.5 | Step 5's `hash --check` is the only call not written as a fenced `uv run ${CLAUDE_SKILL_DIR}/…` command. | `SKILL.md:83` | fix now (A1) |
| F4 1.5 | Step 4's "revise until clean" loop has no limit. A fix it can't make loops the agent until `max_turns`, with no report. | `SKILL.md` Step 4 | fix now (A1) |
| F5 (behavior) | The skill checks its fix at a fixed shared path, `/tmp/rpcn-test-fixcheck/`, so concurrent runs collide. | run log `runs/20261103-143101` (+17s) | fix now (A1) |
| F6 [X] 1.2/1.5 | `cmd_lint` turns every non-empty output line into an error. An `rpk` notice on a clean pipeline then reads as a lint failure. CI never tests through a real `rpk connect`. | `rpcn_check.py:356-363` | defer (D1) |
| F7 [X] 1.4/1.5 | `pipeline_ready` compares inputs only with `<pipeline>.yaml`, so a `.yml` pipeline is never ready. A shared `resources.yaml` is neither linted nor hashed. | `rpcn_check.py:583`, `SKILL.md:52` | defer (D1) |
| F8 1.4 | A test report with `inputs: []` comes back `ready: true`, which bypasses the staleness check. | `_check_handoff` | defer (D1) |
| F9 [X] 1.6/1.11 | The contract between `run_scenarios` and `run_evals` (the `results:` line and the result keys) is tested only against a fake runner. | `test_eval_record.py:262-294` | fix now (A3) |
| F10 1.6 | The runner's `run_checks` call site and its `[[report]]`/`[[lint]]` loops never run in a test. | `run_scenarios.py:1216-1229` | fix now (A3) |
| F11 [X] | `rpcn-test-skills` has no CI and no remote. Its 116 tests run only by hand, and `run_evals` depends on it at `../rpcn-test-skills`. | no `.github/`, `tools/run_evals.py:237,252` | open question (Q1) |
| F12 1.6 | `lint_broken`'s `[[lint]] ok=false` check repeats the `unchanged` check. Nothing compares the report's error table with the runner's own lint. | `scenarios/rpcn-test__lint_broken/expect.toml` | defer (D2) |
| F13 1.7 | `eval_gate` doesn't check the cases it receives against the `evals/` folders, so a dropped case silently shrinks the suite. The prefixes are also hardcoded to `rpcn-test__`. | `eval_gate.py:43-44,130-131` | defer (D2, epic 2) |
| F14 [X] 1.3/1.9 | `sync_shared --check` misses an orphaned copy after its mapping is removed. The validator's warnings (size about 1280 > 1200, and an unused `design-format.md`) don't show in CI. | `sync_shared.py`, `validate_skills.py` output | defer (D2) |
| F15 [X] 1.11 | The skills hash includes untracked files under `skills/`. That fails safe, because CI rejects the record, but it wastes a paid run. The current record is `dirty: true`. | `eval_record.py:73` | accept |
| F16 | Minor: `eval_gate --min-runs 0` with no runs raises ZeroDivisionError, and there is no test for `normpath` in `pipeline_ready`. | `eval_gate.py:157` | accept |

### Aggregate views

- **Architecture delta (the spine against the code):**
  - AD-14 says CI installs binaries with `rpk connect install`. CI actually uses `tools/fetch_rpcn.py`, and the spine still carries its `[ASSUMPTION]` tag (`ci.yml:38-46`).
  - AD-13 names `case.yaml`, which no eval case has (`evals/*/`).
  - AD-3 says `>=3.10` and the standard library only. But `validate_skills.py` needs `>=3.11` and `pyyaml`, and the `rpcn-test-skills` scripts need `>=3.11`. This is also why `run_evals.py:77-93` carries a regex fallback for Python 3.10.
  - Disposition: fix now (A2).
- **Duplication:**
  - There are three git subprocess helpers, each with different failure behaviour (`eval_record.py:51`, `run_evals.py:104`, `run_scenarios.py:662`).
  - Comparison-scenario detection is written twice (`run_evals.py:77-93` vs `run_scenarios.py:178`).
  - The stray-file exclusion is written twice (`eval_record.py:46` vs `validate_skills.py:73-75`).
  - Disposition: defer (D2), except the regex fallback, which A2 removes.
- **Size growth:**
  - `rpcn_check.py` is 1,296 lines, built over stories 1.1, 1.2, 1.4 and 1.8. Accept: AD-2 copies a single file. Watch it in epic 2.
  - `test_rpcn_check.py` is 1,928 lines and `run_scenarios.py` is 1,559. Defer (D2): split them by subcommand, and by judge/arms.
- **Pattern divergence:**
  - Only `sync_shared`, `validate_skills` and `eval_record_check` take `--root`. `run_evals`, `fetch_rpcn` and `eval_gate` hardwire the root, under three different constant names.
  - Two test files call `sys.executable` instead of `uv run`.
  - Defer (D2).
  - The tools' JSON shapes differ from rpcn_check's schema-1 envelope. Accept: AD-4 binds only rpcn_check.
- **Reconciliation:** see Acceptance verdict.

## Behavior verification

These checks ran on 2026-11-03, on the real binary `rpk connect` 4.112.0 (`~/.local/bin/rpk`), using the shipped copy `skills/rpcn-test/scripts/rpcn_check.py`.

- **`binary`:** ok, and it found `rpk` 4.112.0.
- **`lint`:**
  - On `multi_error.yaml` it reports 4 errors and exits 1.
  - On `valid.yaml` it reports ok.
- **`blobl`, `fields inputs kafka_franz`, `list inputs` and `hash`:** all report `ok: true`. `fields` reports `kafka_franz` as `deprecated`.
- **End-to-end run:** `run_scenarios.py --source local:../rpcn-skills --scenario rpcn-test__lint_broken --runs 1 --no-judge` gave **PASS 1/1** in 15 turns, for $0.28 and 40 s. The results are in `rpcn-test-skills/runs/20261103-143101/results.json`, and every check passed:
  - The skill triggered.
  - The status was `complete`, with `checks.lint` set to `fail`.
  - The report was ready, with verdict `fail` and `pipeline_ready` false.
  - The pipeline still lints with 4 errors, and it was not edited.
- **Observed:** to check its proposed fix, the skill wrote the pipeline to a fixed path outside the project, `/tmp/rpcn-test-fixcheck/multi_error.yaml`. That is in the run log, step "+17s". Two concurrent runs would share that path.
- **Not exercised:**
  - the 4.100.0 floor binary (CI covers it in the unit tests)
  - the `npx skills` install from GitHub (the user checked it on a clean machine on 2026-11-03)
  - the trigger evals (record `evals/results/2026-10-30-83f54a3fa504.json`)
  - the benchmark arms (story 1.10's results)

## Previous-retro follow-through

None. This is the first epic.

## Action items

All of these are proposed. None has been applied.

| # | Action | Owner | Kind |
|---|---|---|---|
| A1 | **A bug ticket for the `rpcn-test` hand-off fixes (F1–F5).** It covers four changes. Because it changes `skills/`, it needs `run_evals.py` (about $4.20) and a new record. | Sofia writes the bug, and `bmad-build` builds it | remediation |
| A2 | **Reconcile the spine with as-built (the architecture delta).** It covers three corrections. | `bmad-architecture` | spec reconciliation |
| A3 | **Test the runner contract in `rpcn-test-skills` (F9, F10).** It covers two tests. | `bmad-build`, in `rpcn-test-skills` | remediation |
| A4 | **Before epic 2 adds a sibling, tighten R7's negatives** (`evals/rpcn-test__miss_*`) to assert that no `rpcn-` skill fired. Make `eval_gate` take the expected case list (F13). | Sofia, in epic 2's sibling-edit rule (AD-9) | spec reconciliation |
| L1 | **Process lesson:** F1, F2, F6 and F7 all sit where skill instructions meet script behaviour (the cwd, exit codes, file names). Each story was reviewed alone. In the future, a skill story's scenarios should include at least one pipeline outside the project root, and one non-default name (`.yml`, a shared resources file). | Sofia, in epic 2's story template | process |
| L2 | **Process lesson:** the record's `dirty: true` and F15 show that evals were run with uncommitted work. `run_evals` should warn when `skills/` has uncommitted or untracked files. | `bmad-build` | process |

What A1 covers:
- record hashed inputs relative to the report's folder, and add a subfolder scenario
- limit the exit-2 rule to Steps 1–3
- show `hash --check` as a fenced command
- cap the fix loop at 2 revisions and use a per-run temp folder

What A2 covers:
- AD-14 installs binaries with `fetch_rpcn.py`; drop its `[ASSUMPTION]`
- AD-13 drops `case.yaml`
- AD-3 sets developer tools at `>=3.11`, with the shipped `rpcn_check` staying `>=3.10`; then remove `run_evals`' 3.10 regex fallback

What A3 covers:
- a contract test, using a `schema` field or a real-runner fixture, for the `results:` line and the keys `run_evals` reads
- a `run_once` test that drives `run_checks` with a stub `rpcn_check.py`

**Deferred, with context kept in the findings:**
- **D1:** rpcn_check hand-off hardening (F6, F7, F8), before epic 2's readers depend on `pipeline_ready`.
- **D2:** test-suite and tooling hygiene: F12, F13, F14, duplication, the file splits, `--root` and `uv run` in the tests.

**Accepted:**
- F15 and F16.
- The tools' JSON shapes.
- The two copies of `rpcn_check`.
- `enforce_admins: false` on `main`, by user decision (option a).
- R9's winner was decided by the judge after a tie on errors found.

## Decision records

There are no `adr-*.md` files in the repo. The spine's AD-1 to AD-14 already record the architecture decisions, so they aren't proposed again. Two plan-level decisions pass the test: each is hard to reverse, surprising without context, and the result of a real trade-off.

| Proposed record | Plan / commit | Approved | File |
|---|---|---|---|
| `docs/decisions/adr-scenario-runner-in-a-separate-local-repo.md`. The scenario runner and benchmark live in a sibling repo, `rpcn-test-skills`, that has no remote, so skill source never sits beside installed copies. | `story-rpcn-test-skills-scenario-runner-plan.md`, `rpcn-test-skills` `f402499` | not answered, not written | — |
| `docs/decisions/adr-rpcn-check-written-not-copied-from-connect-plugin.md`. The `blobl`, `list`, `fields`, `run` and `test` helpers were written from scratch, even though copying was allowed, because the Connect plugin's helper scripts carry no licence header (Apache-2.0 vs RCL can't be told apart). | `story-rpcn-check-blobl-list-fields-run-and-test-plan.md`, `aabc482` | not answered, not written | — |

## Acceptance verdict

**Machine verdict: accepted-with-open-items.** The criteria were declared in the epic file. Every story is done, and `pending_tickets` is empty.

| Item | Status | Evidence |
|---|---|---|
| R1 npx install offers only rpcn-test | met | the user's clean-machine check, 2026-11-03 (`35a8bb5`), and `npx skills add . --list` |
| R2 rpcn_check subcommands, envelope, exits | met | 134 tests on 4.100.0 and 4.115.0, CI run 41702664999, and the behavior check |
| R3 sync and drift fail in CI | met | `ci.yml`, `test_sync_shared.py` |
| R4 formats; a stale hash means not ready | met | `test_rpcn_check.py` `test_stale_report` |
| R5 lint-only rpcn-test, report, Next, status block | met | record `2026-10-30-83f54a3fa504.json`, and the behavior run PASS 1/1. F1–F4 limit it to pipelines in the project root (A1). |
| R6 each validator rule rejects | met | 49 tests |
| R7 triggers ≥90%, negatives silent, ≥3 runs | met, with a caveat | 42/42 and accuracy 1.0 (`2026-10-30-f7572be95821.json`). The negatives check only that `rpcn-test` stayed silent, which is the same as "no skill fired" while it is the only skill. A4 closes this before a sibling exists. |
| R8 runner | met | `rpcn-test-skills` `f402499`/`a7bdecd`, lint_broken 3/3 |
| R9 four arms, a winner | met | `runs/20261029-111007/results.json`, winner `ours` (decided by the judge) |
| R10 local record; CI rejects a missing one | met | `ci.yml`, `test_eval_record.py`, and the blocked throwaway PR #1 |
| R11 PR checks block merges | met by design | protection requires `check`, and admins bypass by user decision (option a) |
| Done when 1–5 | met | as above |

**Open items:** A1–A4, D1 and D2. A1 is a user-facing defect in the shipped skill: it doesn't break a requirement as written, but it limits R5 to pipelines in the project root.

**Human decision (2026-11-03):** the user confirmed **accepted-with-open-items**.

## Open questions

- **Q1:** should `rpcn-test-skills` get a remote and its own CI (F11)? Today it is local-only by your choice. So evals can only run on this machine, and its 116 tests never run automatically.
- **Q2:** should A1 be fixed now, as a bug before epic 2, or as epic 2's first story? Epic 2 rewrites `rpcn-test` anyway.

Q1, Q2 and both decision records were not answered at sign-off. They stay open, and no record was written.
