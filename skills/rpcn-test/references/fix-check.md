# Fix check

After writing the fully fixed pipeline to the temp path Step 4 names:

1. Lint it with the same `--resources` and `--env-file` as Step 3.
2. Revise at most twice, then mark any fix that still fails as unverified.
3. If this lint exits 2, mark the fixes unverified and, when a report is
   written, write it as `draft` with that reason.
