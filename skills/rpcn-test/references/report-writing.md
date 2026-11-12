# Writing the test report

Follow `test-report-format.md` and `handoff-header.md` (both in this folder).

**Header:**
- `format: test-report@2`
- `status: ready`
- `produced_by: rpcn-test@<data.plugin_version>`
- `rpcn_version` from `binary.version`
- `inputs` from Step 2, in that order. Record each `file` relative to the
  report's folder, not as `hash` printed it:
  - the pipeline as `<pipeline>` alone, never `pipes/<pipeline>`
  - the design note as `<name>.design.md`, last, only when the Design
    check ran (it wrote rows; not with any `Not run` line,
    `design-check.md` section 1)
  - any other input as its path from the pipeline's folder. For example, with
    the pipeline in `pipes/`:
    - hashed as `resources.yaml` from the project root: record
      `../resources.yaml`
    - hashed as `pipes/orders.resources.yaml`: record `orders.resources.yaml`
    - hashed as `pipes/orders.enrich.blobl`: record `orders.enrich.blobl`

**Sections:**
- Summary: `**Verdict:** pass` only with 0 lint errors, no `fail`
  sample row, a Dry run that did not fail, no failed unit test case and no
  Design check `mismatch`, else `fail`.
- Lint: `0 errors.` or the error table.
- Bloblang samples: as `samples.md` says.
- Dry run: as `dry-run.md` says.
- Unit tests: as `unit-tests.md` says.
- Design check: as `design-check.md` says.
- Proposed changes: one numbered item and `diff` block per fix (lint fixes
  against the pipeline, sample fixes against the `.blobl`, dry-run and
  unit-test fixes against the file that holds the failing processor,
  design fixes against the pipeline, or `<res>` when the component is
  there, with the `<res>` copy linted as `design-check.md` section 4 says),
  or `None.`
  End an unverified fix's item title with `(unverified)`.

**Not ready:** when Step 5's `hash --check` does not report
`data.ready: true`, fix only the report's header or format once and
recheck; never re-hash an input or change a `sha256`. Still not ready: set
`status: draft`, say why, and in headless mode report `blocked`.
