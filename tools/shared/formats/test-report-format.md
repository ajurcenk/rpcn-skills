# Test report format, `test-report@1`

The test report `<name>.test-report.md` is what rpcn-test writes after it
checks `<name>.yaml` (AD-6). It sits beside the pipeline in the developer's
project, and rpcn-test is its only writer. Its header follows
`handoff-header.md`, with:

```yaml
artifact: test-report
format: test-report@1
```

A breaking change to this format (a section renamed, removed or reordered, a
table column or result value changed) bumps the major to `test-report@2`.
Readers reject a major they do not know, through `rpcn_check.py hash --check`.

## Header

- `inputs`: every file the checks read, hashed before the checks ran:
  - the pipeline YAML, `<name>.yaml`, always first
  - each resources file passed to lint or the tests (`<name>.resources.yaml`)
  - the design note `<name>.design.md`, when the Design check used it

  The `.env` or `.env.example` file, the test cases file and the samples file
  are not inputs: rpcn-test writes the last two itself.
- `rpcn_version`: the binary the checks ran on.

When any input changes, `hash --check` reports the report as not ready, so a
report can never vouch for a pipeline it did not test.

## Status

- `draft` while the checks run, or when a check could not run to the end.
- `ready` once every section below is filled in, from one run against the
  inputs as hashed. A `ready` report can still have the verdict `fail`.
- `superseded` is not used by rpcn-test: it rewrites the report on each run.

## Sections

The body has exactly these six `##` sections, with these headings, in this
order. A section whose check did not run holds `Not run.` and one line saying
why (for example `Not run: no design note.`).

1. **Summary**: the line `**Verdict:** pass` or `**Verdict:** fail`, then one
   line per check with its result. The verdict is `pass` only when Lint has 0
   errors, no Bloblang sample or unit test failed, and Design check has no
   `mismatch`. A check that did not run does not fail the verdict.
2. **Lint**: the `rpcn_check.py lint` result. A line `0 errors.`, or a table
   of its `errors` in the order the script gives them, with columns `file`,
   `line`, `column`, `message` (an empty cell for `null`).
3. **Bloblang samples**: one row per sample run with `rpcn_check.py blobl`:
   `mapping` (the processor label, its config path such as
   `pipeline.processors.0`, or the `.blobl` file), `sample`, `expected`,
   `actual`, `result` (`pass` or `fail`).
4. **Unit tests**: the test cases file run with `rpk connect test`, through
   `rpcn_check.py test`: the file, the count passed and failed, and one row per
   failed case with its name and message.
5. **Design check**: the pipeline against the design note's Error handling,
   Delivery and ordering, and Idempotency (AD-7). One row per section:
   `section`, `finding`, `result`. `result` is one of:
   - `ok`: the pipeline does what the section says
   - `mismatch`: it does not, and no unresolved Deviations row covers it
   - `deviation-recorded`: it does not, and an unresolved Deviations row
     covers it (the row's `what` goes in `finding`)
6. **Proposed changes**: rpcn-test never edits the pipeline (AD-6). Each
   change it proposes is a numbered item: one line on why, then a fenced
   `diff` block in unified format against the input file, for rpcn-author to
   apply. Write `None.` when there are none.

## Readiness list

After `rpcn_check.py hash --check <name>.test-report.md` reports
`ready: true`, every reader checks:

- [ ] The six sections are present, with the headings above, in order.
- [ ] Summary has a `**Verdict:**` line of `pass` or `fail`.
- [ ] Every section that did not run says `Not run` and why.
- [ ] `inputs` lists `<name>.yaml`, and the design note when Design check ran.

A reader that needs the pipeline itself to be ready (AD-6: rpcn-scale,
rpcn-deploy) uses it only when the same `hash --check` reports
`pipeline_ready: true`: the report is ready, its `<name>.yaml` input hash
matches, and its verdict is `pass` (`data.verdict`). It also checks:

- [ ] Lint ran.

rpcn-author reads a `ready` report with either verdict, to apply its
Proposed changes. If any item a reader needs fails, it treats the report, and
so the pipeline, as not ready.

## Example

The pipeline the example report tested:

<!-- example-file: orders.yaml -->
```yaml
input:
  redpanda:
    seed_brokers: [ "${REDPANDA_BROKERS}" ]
    topics: [ orders ]
    consumer_group: orders-to-http

pipeline:
  processors:
    - mapping: |
        root = this
        root.total_cents = (this.total * 100).round()

output:
  fallback:
    - http_client:
        url: "${ORDERS_API_URL}"
        verb: POST
        max_in_flight: 8
        retries: 3
    - redpanda:
        seed_brokers: [ "${REDPANDA_BROKERS}" ]
        topic: orders.dlq
```

Its design note is the example in `design-format.md`. The report:

<!-- The two sha256 values are the real hashes of the example orders.yaml above and of the
     example orders.design.md in design-format.md; the rpcn_check tests check them. -->
<!-- example-file: orders.test-report.md -->
````markdown
---
artifact: test-report
format: test-report@1
pipeline: orders
status: ready
produced_by: rpcn-test@0.1.0
rpcn_version: 4.115.0
inputs:
  - file: orders.yaml
    sha256: 77c752d3d897336753043dd647d081da3caae2669b3c6bc7169fa80b44729e56
  - file: orders.design.md
    sha256: 7be7ffdd17c1b56532c029f0298782c1ff43eb3be2ea32b5d9348d7279a1fa3b
updated: 2026-10-23
---

# orders: test report

## Summary

**Verdict:** pass

- Lint: 0 errors
- Bloblang samples: 2 passed, 0 failed
- Unit tests: 3 passed, 0 failed
- Design check: 2 ok, 1 deviation-recorded, 0 mismatch
- Proposed changes: 1

## Lint

0 errors.

## Bloblang samples

| mapping | sample | expected | actual | result |
|---|---|---|---|---|
| pipeline.processors.0 | `{"id":"o1","total":12.5}` | `{"id":"o1","total":12.5,"total_cents":1250}` | `{"id":"o1","total":12.5,"total_cents":1250}` | pass |
| pipeline.processors.0 | `{"id":"o2","total":0.1}` | `{"id":"o2","total":0.1,"total_cents":10}` | `{"id":"o2","total":0.1,"total_cents":10}` | pass |

## Unit tests

`orders_benthos_test.yaml`: 3 passed, 0 failed.

## Design check

| section | finding | result |
|---|---|---|
| Error handling | Retries 3 times, then `fallback` to `orders.dlq` | ok |
| Delivery and ordering | The HTTP output uses `max_in_flight: 8`, so posts can arrive out of order | deviation-recorded |
| Idempotency | Every message keeps `id`, which the API deduplicates on | ok |

## Proposed changes

1. Key DLQ messages by `customer_id`, so a replay from `orders.dlq` keeps
   each customer's orders on one partition, in order (Delivery and ordering).

```diff
--- a/orders.yaml
+++ b/orders.yaml
@@ -20,3 +20,4 @@
     - redpanda:
         seed_brokers: [ "${REDPANDA_BROKERS}" ]
         topic: orders.dlq
+        key: ${! json("customer_id") }
```
````
