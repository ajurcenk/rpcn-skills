# Writing the design note

The note is the contract rpcn-author builds to and rpcn-test checks
against (AD-7). Its format is `design-format.md` (in this folder): exactly
eleven `##` sections, with those headings, in that order. Write it in one
Write call, from the request and the Step 3 and 4 results only. State no
component, field or behaviour that the request, `list` or `fields` did not
give you.

## Header and title

```markdown
---
artifact: design
format: design@1
pipeline: <name>
status: <ready|draft>
produced_by: rpcn-design@<data.plugin_version from Step 1>
rpcn_version: <binary.version from Step 1>
inputs: []
updated: <today, YYYY-MM-DD>
---

# <name>: design
```

`inputs` stays `[]` for a plain request. When the request names a file in
the project that the design is made from (a requirements file, a sample
message), hash it from the note's folder and copy each pair into `inputs`,
as `handoff-header.md` says ("Writing the hashes"):

```bash
uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py hash <file>
```

## Sections

1. **Purpose:** what the pipeline is for, in two or three sentences.
2. **Inputs:** each source: system, topic or endpoint, message shape,
   expected rate. Addresses and secrets are named as `${ENV_VAR}`, never
   given a value.
3. **Outputs:** each sink: system, topic or endpoint, message shape. The
   DLQ is an output too.
4. **Components:** a table with columns `kind`, `component`, `role`, one
   row per component, each one Step 4 checked. `kind` is the singular of
   the Step 3 category (`input`, `output`, `processor`, `cache`,
   `rate_limit`, `buffer`, `metrics`, `tracer`). Every component that
   Inputs, Outputs or Error handling names has a row. A role is one short
   phrase, with no `|`.
5. **Error handling:** the minimal pattern below.
6. **Delivery and ordering:** what the request says about the delivery
   guarantee and ordering, else `None.`
7. **Idempotency:** what the request says about duplicates and dedupe
   keys, else `None.`
8. **Batching:** what the request says about batching, else `None.`
9. **Throughput expectations:** the rates, message sizes and latency the
   request gives, else `None.`
10. **Open decisions:** one bullet per gap, as below, else `None.`
11. **Deviations:** the header row and separator only, so rpcn-author can
    append to it:

    ```markdown
    | section | what | why | date | resolved |
    |---|---|---|---|---|
    ```

## Error handling: the minimal pattern

Say, in plain sentences, what happens to a message that fails:

- **The DLQ destination**, by name: the system and the topic, table or
  path, such as "the Redpanda topic `orders.dlq`". Use the one the
  request names. If it names none, pick a topic on the input's system
  when it has topics (`<input topic>.dlq`), else a file
  `<name>.dlq.jsonl`, and write that pick as an open decision.
- **The retries:** how many times the sink that can fail is retried
  before the message goes to the DLQ. Use the request's count, else pick
  3 and write the pick as an open decision. Name the retry field only
  when Step 4's `fields` output for that component lists it (such as
  `max_retries` or `retries`).
- **Where each kind of failure goes,** as intent, in the request's
  words: such as "orders that fail processing or can't be delivered go
  to `orders.dlq`". Name a component only when Components lists it (such
  as a wrapper output that `list outputs` lists and `fields` passed, as
  in `design-format.md`'s Example). Say nothing about how Redpanda
  Connect routes the message: building that is rpcn-author's job.
- **A drop:** only when the request asks for one. Then the DLQ is
  `None.` for that path, and the section says the message is dropped.

When the request says failures go nowhere (log and drop), write that, and
no DLQ.

## Open decisions

Never ask. For every choice the request leaves open that changes the
design, pick the answer and write it in:

- `[non-blocking] <the question>? Picked: <the pick>.` Use a pick in its
  section as if the request had said it. Each pick also goes in the
  status block's `open_questions` as `Assumed: <pick> (<question>)`.
- `[blocking] <the question>.` only for a part of the flow that no listed
  component fits (Step 4). The note is then `draft`.

A detail the request leaves out that changes nothing in the pipeline (a
rate, a message size) is not an open decision: leave it out of its
section, or write `None.`

## Before Step 6

Check the note against `design-format.md`'s Readiness list, then run the
`hash --check`.
