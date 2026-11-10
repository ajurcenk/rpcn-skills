# Writing the test report

Follow `test-report-format.md` and `handoff-header.md` (both in this folder).

**Header:**
- `status: ready`
- `produced_by: rpcn-test@<data.plugin_version>`
- `rpcn_version` from `binary.version`
- `inputs` from Step 2, in that order. Record each `file` relative to the
  report's folder, not as `hash` printed it:
  - the pipeline as `<pipeline>` alone, never `pipes/<pipeline>`
  - any other input as its path from the pipeline's folder. For example, with
    the pipeline in `pipes/`:
    - hashed as `resources.yaml` from the project root: record
      `../resources.yaml`
    - hashed as `pipes/orders.resources.yaml`: record `orders.resources.yaml`
    - hashed as `pipes/orders.enrich.blobl`: record `orders.enrich.blobl`

**Sections:**
- Summary: `**Verdict:** pass` only with 0 lint errors and no `fail`
  sample row, else `fail`.
- Lint: `0 errors.` or the error table.
- Bloblang samples: as `samples.md` says.
- Unit tests, Design check: `Not run: not in this version of rpcn-test.`
- Proposed changes: one numbered item and `diff` block per fix (lint fixes
  against the pipeline, sample fixes against the `.blobl`), or `None.`
  End an unverified fix's item title with `(unverified)`.
