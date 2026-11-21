---
title: 'Roll the newest tested pin from 4.115.0 to 4.117.0'
type: 'chore'
ticket: ''
created: '2026-11-20'
status: 'in-progress'
baseline_revision: '7c5f780bdc5e8791df50ed5546c691d54429b0db'
route: 'oneshot'
route_source: 'auto'
risk: 'medium'
review: ''
review_source: ''
lenses_ran: []
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** the tested binaries are 4.100.0 and the newest release (initiative Constraints). The newest pin is still 4.115.0, and epic 3's Constraints say the roll to 4.117.0 lands before its first build. Every AD-15 fact must be proved on the newest pin.

**Approach:**
- **Change the pin:** in `tools/rpcn_versions.txt`, replace `4.115.0` with `4.117.0`, keeping the `4.100.0` floor. `tools/fetch_rpcn.py` fetches the new binary, and the CI cache key follows the file.
- **Re-prove the facts:** run `rpcn_check`'s real-binary tests on 4.100.0 and 4.117.0. For each SOURCES.md row that cites 4.115.0, change it to 4.117.0 only when its proof passes there. A fact that changes is reported, not papered over.
- **Update the version wording:** `tools/shared/rpcn_check/SCHEMA.md` and `skills/rpcn-author/references/questions.md`, which name 4.115.0 as a tested pin.
- **Leave examples alone:** a header example's `rpcn_version`, and the test fixtures that pin their own versions.
- **Eval record:** the skills change by one line, so a passing record is needed (AD-14): `run_evals.py`, without the comparisons.

</frozen-after-approval>

## Implementation Notes

- **Pin:** `tools/rpcn_versions.txt` now pins `4.117.0`, with the `4.100.0` floor kept. `fetch_rpcn.py` fetched it, and its `--version` is 4.117.0. It embeds benthos `v4.84.0`, the same as 4.115.0.
- **Facts re-proved:** all 187 `rpcn_check` tests pass on 4.100.0 and 4.117.0, the real-binary ones included. No fact changed. The six SOURCES.md rows proved by those tests now cite connect `v4.117.0` (benthos `v4.84.0`). The same wording changed in `tools/shared/rpcn_check/SCHEMA.md` (3 places) and in `skills/rpcn-author/references/questions.md` (1 line, the only skills change).
- **Not re-proved, kept as written:** the `lint-errors.md` row (adapted from `redpanda-data/skills`) says it was "checked by hand against `rpcn_check lint` output on 4.100.0 and 4.115.0. No CI test yet". This roll did not redo that hand check, so the row still says 4.115.0.
- **Kept as examples:** `rpcn_version: 4.115.0` in the header examples of the shared formats, and the fixture pins in `tools/tests/test_eval_record.py` and `test_rpcn_check.py`. These are sample values, not tested pins.
- **CI:** the binary cache key hashes `tools/rpcn_versions.txt`, so it follows the change with no edit.
- **Checks:** R's suites (146), the validator, `sync_shared --check`, and T's tests with 4.100.0 and 4.117.0 (343) pass.

## Review Triage Log

## Verification

- `uv run tools/fetch_rpcn.py` — prints the 4.100.0 and 4.117.0 binary paths
- `RPCN_TEST_BINARIES=<abs 4.100.0>:<abs 4.117.0> uv run --with pytest pytest -q tools/shared/rpcn_check/tests` — pass
- `uv run --with pytest pytest -q tools/tests skills`, `uv run tools/validate_skills.py`, `uv run tools/sync_shared.py --check` — pass
- T's tests with the new binaries — pass
- `run_evals.py` — a passing `dirty: false` record
