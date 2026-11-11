# Status block

Fill the headless status block this way:

- `status`: `blocked` (with `reason` the first error) only after an exit 2
  in Steps 1–4 (but `blobl`, `run` and `test`, which `samples.md`,
  `dry-run.md` and `unit-tests.md` handle) or a report that stays not
  ready; otherwise `complete`, even when lint, a sample, the dry run or a
  unit test fails.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `checks.tests`: the Bloblang samples (`samples.md`), the dry run
  (`dry-run.md`) and the unit tests (`unit-tests.md`) together: `fail`
  when any sample row is `fail`, the dry run failed or any unit test case
  failed; `pass` when at least one of them ran and none failed; `skipped`
  when none ran (a `Not run` section did not run).
- `artifacts`: the report path and, when written in this run, the samples
  file and `<dir>/<name>_benthos_test.yaml`; or `[]`.
- Questions go in `open_questions`.
