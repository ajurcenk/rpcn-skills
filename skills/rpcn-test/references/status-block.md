# Status block

Fill the headless status block this way:

- `status`: `blocked` (with `reason` the first error) only after an exit 2
  in Steps 1–4 or a report that stays not ready; otherwise `complete`, even
  when lint fails.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `checks.tests`: `skipped`.
- `artifacts`: the report path, or `[]`.
- Questions go in `open_questions`.
