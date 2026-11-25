# Describing an existing pipeline

Read this from Step 2 when no note exists yet (the not-found exit), the
request names a pipeline `<dir>/<name>.yaml` (or `.yml`) that exists, and
it asks for that pipeline's design: "describe my pipeline `orders.yaml`",
"write a design note for `pipes/orders.yaml`", "document this pipeline's
design". The note describes what the config does today, not what it should
do.

Not describe mode, so the plain path as today:

- the named pipeline doesn't exist (Read finds no file): design from the
  request alone;
- no pipeline is named ("write a design note for my pipeline");
- a note exists: Step 2's rule (headless `blocked`; interactive asks
  whether to update it).

## What it reads

With Read only, and nothing else:

- the pipeline `<dir>/<name>.yaml`, with any resources it defines inline
  (`cache_resources`, `rate_limit_resources`, `processor_resources`,
  `input_resources`, `output_resources`);
- its resources file `<dir>/<name>.resources.yaml` (`.resources.yml` for
  `.yml`), when it exists, and any other resources file in the project
  that defines a label a `resource:` (or a `cache:` or `rate_limit:` field)
  in the pipeline points to and the pipeline doesn't define;
- each `.blobl` file a `from "<path>"` (or `import "<path>"`) names, in
  those files or in another `.blobl` file read this way (the path is from
  the project root).

Write nothing but `<note>`: never edit, rewrite or format the pipeline, its
resources, `.blobl` or `.env.example` files. They stay byte-identical. No
YAML is written.

## Steps 3 and 4: the components

Take each component the config uses, in config order: the input (a
`broker` input, then each of its children) and the input's own
`processors`, then any buffer, then each pipeline processor, then the
output (a `fallback`, `broker` or `switch`, then each output inside it)
and each output's own `processors`, then any metrics or tracer, then the
resources (inline ones, then the resources files'). Nested processors
count too, such as a `branch`'s, a `switch` output case's or a `batching`
block's `processors`, each where it sits. Run `list <category>` and `fields
<category> <component>` for each one, as Steps 3 and 4 say, and keep the
`fields` description of every field the note names.

A component the binary doesn't list (`fields` exit 1): never swap in a
close match, since the config uses what it uses. Leave it out of
Components, and write `[blocking] <the config's component> (<kind>, in
<file>) is not listed by Redpanda Connect <binary.version>.` in Open
decisions. The note is `draft`.

Pick no new component: `patterns.md` is read only for its Notes and Basis,
never to add a part the config lacks. Wherever `note-writing.md` or
`patterns.md` keys a rule to the request ("from the request and the Step 3
and 4 results only", "no `retry` without a retry asked for", "none were
asked for"), read "the config" for "the request" in describe mode.

## Step 5: the note

Write `<note>` as `note-writing.md` says (header, title, the eleven
sections), with these differences:

- **`inputs: []`.** The pipeline and its files are never hashed, so a
  later change by rpcn-author doesn't make the note stale.
- **Purpose:** what the pipeline does, in two or three sentences, naming
  the file it describes (`pipes/orders.yaml`).
- **Inputs and Outputs:** what the config reads and writes, by system and
  topic, endpoint or path. An address or secret is the `${ENV_VAR}` the
  config uses, never a value. A rate the config doesn't show is left out.
- **Components:** one row per component that passed Step 4, in config
  order; the role says what the config does with it (`DLQ topic
  orders.dlq`).
- **Error handling, Delivery and ordering, Idempotency, Batching:** what
  the config does, and nothing more. Each behaviour claim has a basis: a
  `patterns.md` entry's Basis for its component (pattern 1 for a
  `fallback`, 2 for a `switch` on `errored()`, 3 for a `retry`, 4 for
  `batching.count`, 5 for a `dedupe`), or a field value with the
  description `fields` printed for it. Name a field only with the value
  the config gives it, or its `fields` default. A behaviour neither backs
  is not written.
- **Throughput expectations:** `None.` unless the config states an
  expected rate. A `rate_limit` is a cap, not an expected rate: it goes in
  Components, its role naming the cap.
- **Deviations:** the header row and separator only.

## The four asks, from the config

The config answers an ask (`questions.md`, "The four asks") this way:

1. **The failure target:** a `fallback` whose later output takes a failed
   write, or a `switch` case on `errored()` to an output, answers it for
   that path. Error handling names that output's destination. The config
   has no answer when no `fallback` or `switch` sends a failure anywhere:
   a `[blocking]` failure target as "A choice left open" says (headless,
   no Suggested destination), and the note is `draft`. A path the config
   doesn't route (processing failures with no `switch`) is written as
   that: the config routes them nowhere else.
2. **The delivery guarantee:** never a claim; the config gives it as a
   pick. A DLQ or a `retry` gives at-least-once, as `questions.md` infers
   it, written in Open decisions as `[non-blocking] Which delivery
   guarantee holds? Picked: at-least-once — failed writes are kept in
   <the DLQ>.` (`orders.dlq`, by name). A failure path to a `drop` output
   gives `Picked: at-most-once — failed writes are dropped.` Delivery and
   ordering states the pick as a pick ("at-least-once, picked: see Open
   decisions"), and Error handling keeps pattern 1's fact: a failed write
   goes to the DLQ, by name. Neither is asked. With no DLQ, `retry` or
   `drop`, delivery is open, as for the failure target.
3. **Ordering:** the config shows settings, not intent. The settings are
   the input's ordering field (such as `unordered_processing.enabled` or
   `checkpoint_limit` on a `redpanda` input) and each output's
   `max_in_flight`, read from `fields`. Write in Delivery and ordering
   what each set value does, in its `fields` description's words, and
   claim no order beyond that description. The ask is `[non-blocking]`,
   the config's behaviour as the pick, naming the setting: `[non-blocking]
   Must order hold, per key or overall? Picked: no ordering
   (unordered_processing.enabled: true on the input).`
4. **The idempotency key:** a `dedupe` answers it: Idempotency names its
   key and cache (pattern 5). With none, Idempotency says only that the
   config has no `dedupe`, with no claim about redelivery, and the ask is
   `[non-blocking]`:
   `[non-blocking] Can messages repeat, and which field identifies one?
   Picked: no dedupe (the config has none).`

Every other choice the config makes (a retry count, a batch size) is
written as the config's value, not as an open decision.

## Asking

Interactive: ask, as `questions.md` says (Rounds, through the question
tool when the host offers it), only the asks the config leaves open, each
with the config's behaviour as `My pick`. An ask the config answers is
never asked. An answer that differs from the config is recorded as intent
beside what the config does, in its section ("the config does X;
intended: Y"), and adds no component the pipeline lacks; the note still
describes the config. Headless: never ask; write each open ask as "A choice left
open" and the list above say.

`status` follows the Ready rule, and Step 6 checks the note as for any
note. Headless, the status block's `artifacts` lists the note.
