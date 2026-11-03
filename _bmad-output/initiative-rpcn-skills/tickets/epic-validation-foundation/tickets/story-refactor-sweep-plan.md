---
title: 'Refactor sweep'
type: 'chore'
ticket: '12'
created: '2026-11-03'
status: done
baseline_revision: '03e66fd7925e07ba8e5d1244156afe175a09e0bc'
route: 'oneshot'
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

**Problem:** Epic 1 left two loose ends that code can close:
- **A deferred `rpk` question.** `deferred-work.md` asks whether `rpk connect --version` auto-downloads Redpanda Connect when the plugin is missing. The unit tests only model a missing plugin as "exit 1", but real `rpk` behaves differently.
- **A CI warning.** Every CI run warns that `setup-uv`'s cache glob matches no file, so the uv cache never invalidates.

**Approach:**
- **Settle the `rpk` question by experiment.** With `rpk` v26.2.2 and no Connect plugin on `PATH`, `rpk connect --version` prints rpk's help text and exits 0, with no download and no files written. `rpcn_check binary` then exits 2 with the `rpk connect install` hint. Pin that behaviour with a unit test using a fake `rpk` that prints help text and exits 0.
- **Fix the CI warning.** Point `setup-uv`'s `cache-dependency-glob` at the PEP 723 scripts that declare dependencies.

Nothing under `skills/` changes.

Out of this story:
- **The spine rename** (`ARCHITECTURE-SPINE.md` to `architecture-rpcn-skills.md`). It edits the initiative and the epic ticket files, which `bmad-build` may not write, so it goes to the product owner.
- **The marketplace-install check.** It's hands-on, for the user.
- **The "Kafka Connect" exemption.** That's epic 4.

</frozen-after-approval>

## Implementation Notes

- **The experiment:** I copied `rpk` into an empty scratch folder and ran it with `env -i HOME=<scratch> PATH=<scratch>/bin:/usr/bin`.
  - `rpk connect --version` printed the `rpk connect` usage text and exited 0 in 0.03 s. No file appeared under the scratch home.
  - `rpcn_check.py binary` under the same environment exited 2: "`rpk connect --version` failed (printed no `Version:` line); run `rpk connect install` …".
  - Without the `PATH` isolation, rpk found its managed plugin at `~/.local/bin/.rpk.managed-connect` (4.112.0), even with a temporary `HOME`.

## Review Triage Log

Pass 1 (quick): 0 high, 1 medium, 2 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| The new test's assertions match `test_missing`. `INSTALL_HINT` always says "rpk connect install", so the test doesn't pin the exit-0, no-`Version:` path | medium | patch | Confirmed. The test now also asserts "`rpk connect --version` failed (printed no `Version:` line)". |
| `tools/**/*.py` resets the uv cache on any tool edit, not only on dependency changes, and the comment overstated it | low | patch (comment) / reject (glob) | The cost is a cold cache after a tool edit. Narrowing the glob to the two scripts with dependencies would miss future scripts. Only the comment was corrected. |
| `deferred-work.md` still shows the `rpk` question as open | low | reject | The build workflow forbids editing old entries there. The answer is recorded above, and the user is told so that the product owner can close the entry. |

## Verification

**Commands:**
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py`: all pass, including the new test.
- `uv run tools/validate_skills.py && uv run tools/sync_shared.py --check && uv run tools/eval_record_check.py`: still green.
