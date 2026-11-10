# Status block

Fill the headless status block this way:

- `status`: `blocked` (with `reason`) only after:
  - an exit 2, except from Step 2's design-note check (not ready, below)
  - an existing file on a write request
  - a component the binary doesn't list (`reason` names it)
  - lint still failing after 3 revisions
  - a report that is not ready (`reason` says why: draft, or an input
    changed or missing since it was hashed)

  Otherwise `complete`. A proposed change that can't be applied doesn't
  block: the run ends `complete`, with that item in `open_questions`.
  Neither does a design note that is missing or not ready (AD-8): with a
  not-ready note the run ends `complete`, `reason` stays `null`, and
  `open_questions` holds one line saying the note is not ready and why.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `checks.tests`: `skipped`.
- `artifacts`: every file written or edited, as paths from the project root,
  or `[]`. Never the test report: rpcn-author doesn't edit it. A design note
  is listed only when Deviations rows were added to it.
- Questions go in `open_questions`.
