# Status block

Fill the headless status block this way:

- `status`: `blocked` (with `reason` the first error) only after an exit 2
  in Steps 1–4 (but `blobl`, which `samples.md` handles) or a report that
  stays not ready; otherwise `complete`, even when lint or a sample fails.
- `checks.lint`: `pass`, `fail`, or `skipped` when lint did not run.
- `checks.tests`: from the Bloblang samples (`samples.md`), else `skipped`.
- `artifacts`: the report path and, when written in this run, the samples
  file; or `[]`.
- Questions go in `open_questions`.
