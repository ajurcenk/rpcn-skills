---
title: 'Eval speed-up: parallel trigger runs and scenario runs'
type: 'chore'
ticket: ''
created: '2026-11-11'
status: 'done'
baseline_revision: 'adf5e59b9606601c5940c89a9b5b440d1c9b91ec'
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

**Problem:** a full `uv run tools/run_evals.py` takes about 58 minutes, because everything runs one session at a time. Story 2.8's eval spent 954 s on the trigger gate (90 sessions) and 2,522 s on the scenarios (69 runs). Every remaining story adds to it, and a run lost to a setup glitch repeats it in full.

**Approach:** run sessions in parallel at the same cost and the same 3-run bar, aiming for about 16–18 minutes and certainly under 30:
- `run_evals.py` passes `--concurrency` to `claude plugin eval`;
- `run_scenarios.py` gains `--jobs`, which runs scenario runs in parallel workers;
- `run_evals.py` passes both, defaulting to 4.

## Boundaries & Constraints

**Always:**
- **Same outputs:** `results.json` and the eval record keep their shape and contents. Scenarios and runs stay in a fixed order (scenario order, then run index) whatever order they finish in. `--jobs 1` behaves exactly as today.
- **Readable progress:** every progress line keeps its `[<scenario> run i/n +Ns]` prefix, and lines never interleave mid-line. The final summary table stays in scenario order.
- **No skills change:** no file under `skills/` changes, so no new eval record is needed. `claude plugin eval` keeps `--no-publish`.

**Never:**
- Run comparison (`[compare]`) scenarios in parallel. They stay sequential, after the pool.
- Overlap the trigger gate with the scenario stage. The stages stay in today's order.
- Change any check, pass rule or eval-record rule.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | `run_scenarios.py` with no `--jobs` | Sequential, as today | — |
| Parallel | `--jobs 4` | Up to 4 runs at once. `results.json` holds the same entries, in scenario and run order | — |
| One run fails or crashes | `--jobs 4`, one run raises | That run is recorded as failed, as today, and the others go on | — |
| Bad value | `--jobs 0` or `--jobs 9` (allowed: 1–8) | Usage error, exit 2 | — |
| Compare scenario | `--with-compare` | The compare scenario runs sequentially after the pool | — |
| Evals | `run_evals.py` defaults | `claude plugin eval … --concurrency 4` and `run_scenarios.py … --jobs 4` | `--concurrency` and `--jobs` flags override them (1–8) |
| Ctrl-C | an interrupt during a `--jobs 4` run | Queued runs are cancelled, running Claude sessions are killed, the finished runs are saved, and the exit code is 130. `run_evals.py` stops its child the same way | — |

**Decisions (2026-11-11, user, at review):**
- **Crash rule:** `--jobs 1` stays exactly as today, so a crash aborts with exit 2. With `--jobs` above 1, a crashed run is recorded as failed and the pool goes on.
- **Status check:** fix the runner's status check in this change, which overrides the "Never: change any check" line for this one check only.
  - **The rule:** the status block is the **last** fenced `json` block in the final reply that parses as an object with the status keys. Earlier `json` blocks, such as the Dry run messages story 2.8 makes rpcn-test show, are ignored.
  - **Why:** the smoke run failed `dry_run_pass` with "expected exactly one status block, found 3".
  - **Still a failure:** no matching block at all.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, local only, with baseline `ddf9c4df78a2e4c4891a84526267b6d9590b65ae`.

- **`T/run_scenarios.py`:**
  - `parse_args` (around 1706) gains `--jobs` (int, 1–8, default 1).
  - In `main` (around 1868), the loop runs `run_once(sc, i, …)` per scenario and run.
    - Build a list of (scenario, i) tasks for the non-compare scenarios.
    - Run them in a `concurrent.futures.ThreadPoolExecutor(max_workers=jobs)`.
    - Collect each result into its scenario entry by index, and recompute `pass_count` and `passed` as today.
    - `save()` is called under a lock after each finished run.
    - Compare scenarios run afterwards, as today.
  - Make every progress print go through one module-level lock: `run_once.say` (around 1455), the setup failure print (1467) and the judge prints. Keep `flush=True`.
  - Stagger each worker's first run by about 2 s × worker slot, so parallel `npx skills add` calls don't start together.
  - Each run already uses its own `out_dir/<scenario>/run-<i>` folder.
- **`T/tests/test_run_scenarios.py`:**
  - `--jobs` validation;
  - parallel results in fixed order, using a patched `run_once` with varied sleeps;
  - one raising run doesn't stop the others;
  - `--jobs 1` matches today's sequence.
- **`T/README.md`:** document `--jobs` and the rate-limit note (sessions share one account limit).
- **`R/tools/run_evals.py`:**
  - `run_trigger` (around 134) adds `--concurrency <n>`;
  - `run_scenarios` (around 211) adds `--jobs <n>`;
  - `parse_args` gains `--concurrency` and `--jobs` (1–8, default 4).
- **`R/tools/tests/test_eval_record.py`:** its fake-`claude` and fake-`uv` tests assert the new arguments.
- **`R/evals/README.md`:** state the run time and the two flags.

## Tasks & Acceptance

**Execution:**
- [x] `T/run_scenarios.py`, `T/tests/test_run_scenarios.py`, `T/README.md`: `--jobs`.
- [x] `R/tools/run_evals.py`, `R/tools/tests/test_eval_record.py`, `R/evals/README.md`: `--concurrency` and `--jobs`.

**Acceptance Criteria:**
- **Given** both repos, **when** all `tools/` suites and T's tests run, **then** all pass.
- **Given** both binaries, **when** `run_scenarios.py --jobs 4 --runs 1 --no-judge` runs every non-compare scenario, **then** all pass, `results.json` is in scenario order, and the wall time is well under the sum of the run times. Report both numbers.

## Implementation Notes

- `--jobs 1` keeps today's loop untouched, including a raising `run_once` aborting with exit 2. With `--jobs` above 1, a raising run is recorded as a failed run (`errors: ["crashed: <Type>: <msg>"]`, `passed: false`) and the pool goes on.
- With `--jobs` above 1, every scenario entry is created up front in scenario order (compare ones too), so a partial `results.json` lists every scenario with its finished runs so far, in run order.
- Stagger: the first `jobs` tasks sleep `STAGGER_S` (2 s) x their index; tests patch it to 0.
- `run_evals.py` passes `--concurrency <c>` after `--trust-plugin` and `--jobs <j>` after `--runs`.
- Smoke run (`--jobs 4 --runs 1 --no-judge`, 23 non-compare scenarios, both binaries): wall time 233 s, against 851 s summed run time; $6.67. 22/23 passed. `rpcn-test__dry_run_pass` failed `status` once because the reply showed sample data in ```json fences (3 blocks found), which is model output and not related to parallelism. A rerun passed 1/1. `results.json` was in scenario order.
- Review fixes:
  - **Ctrl-C in `run_scenarios.py`:** `run_pool` cancels the queued futures (`shutdown(cancel_futures=True)`). `run_claude` registers each live `Popen` in a locked set, and `stop_sessions()` kills their process groups and blocks new sessions. `main` ignores a second SIGINT while it saves, then exits 130 with `error: "interrupted"`. That handler is in `main`, so it also covers `--jobs 1`.
  - **Ctrl-C in `run_evals.py`:** it sends SIGINT to its child (`uv` passes it on), waits 15 s, then terminates it, and exits 130 without a record.
  - **Crash and error paths:** the crash handler's print is guarded, and any collection-loop exception cancels the queued futures before re-raising.
  - **Status check:** the last status-shaped json block wins (an object with a `status` key and only AD-8 keys). Earlier blocks are ignored, and no matching block is still a failure.
  - **Prints:** `rejudge` prints go through `say_line`.
  - **Second smoke run** (`--jobs 4 --runs 1 --no-judge`, 23 non-compare scenarios, both binaries): 23/23 passed. Wall time 221 s, against 812 s summed run time. Cost $6.48.
- **Pushed:** `adf5e59..134af75`. CI run 43075713210 was green.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 2 medium, 4 low, 0 false, 0 maybe-false. Two points went to the user: the crash rule (kept as built) and the status check (fixed here).

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| Ctrl-C drains every queued run, and paid sessions run on unsaved | medium | patch | `shutdown(cancel_futures=True)`, live sessions' process groups killed, finished runs saved, exit 130. `run_evals.py` stops its child. A real-SIGINT test covers it. |
| The crash handler's print can raise, and a collection-loop error drains the queue unrecorded | low | patch | The print is guarded, and the queued futures are cancelled before re-raising. |
| AC 2 (all pass in one run) not met: `dry_run_pass` failed "exactly one status block" | medium | patch (user decision) | The status block is the last fenced `json` block with the status keys. The second smoke run passed 23/23. |
| A run that crashes late loses its cost and turns in the record | low | reject | Only a runner bug in a check function can cause it, and that is rare. The fix would mean restructuring `run_once`. |
| `rejudge` prints bypass the shared lock | low | patch | They use `say_line`. |
| A README sentence reads as an instruction | low | patch | Reworded. |

## Verification

**Commands:**
- `uv run tools/tests/test_eval_record.py` and the other `tools/tests` suites: pass.
- In `T`: `uv run tests/test_run_scenarios.py`: pass. Then the parallel smoke run in the AC (about $7). The implementation agent may run it.
