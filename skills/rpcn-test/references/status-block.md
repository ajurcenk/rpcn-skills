# Status block

Fill the headless status block this way:

- `status`: `blocked` (with `reason` the first error) only after an exit 2
  in Steps 1–4 (but `blobl` and `run`, which `samples.md` and `dry-run.md`
  handle) or a report that stays not ready; otherwise `complete`, even when
  lint, a sample or the dry run fails.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `checks.tests`: the Bloblang samples (`samples.md`) and the dry run
  (`dry-run.md`) together: `fail` when any sample row is `fail` or the dry
  run failed; `pass` when at least one of them ran and none failed;
  `skipped` when neither ran (a `Not run` dry run did not run).
- `artifacts`: the report path and, when written in this run, the samples
  file; or `[]`.
- Questions go in `open_questions`.
