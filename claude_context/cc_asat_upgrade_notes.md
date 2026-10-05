# cc_asat upgrade notes

`cc_gcev` adopts full nf-core conventions. Several of them are places where the
sibling pipeline `cc_asat` (v0.8.0) currently falls short. This doc records each
divergence so it can be backported into `cc_asat`.

| # | nf-core convention | cc_asat today | cc_gcev does | Backport action for cc_asat |
|---|---|---|---|---|
| 1 | **meta maps** (`tuple val(meta), path(...)`) | tags with `params.sample_name`, bare `path` inputs | meta maps carry `id`, `role`, `target_id`; `tag "${meta.id}"` | Refactor modules to `tuple val(meta), path(...)`; build a `meta` in the workflow. Enables future multi-sample. |
| 2 | **`versions.yml`** emitted per process + collected | no process emits versions | every process emits `versions.yml`; `DUMP_SOFTWARE_VERSIONS` collects | Add a `versions.yml` stanza to each `script:` and a collector process. |
| 3 | **`task.ext.args` / `task.ext.prefix`** | tool flags hard-wired from `params.*` in script blocks | tunable flags routed via `ext.args` in `conf/modules.config`; output names from `ext.prefix ?: meta.id` | Move tool flags to `ext.args`; derive prefixes from `ext.prefix`. |
| 4 | **`tag` uses meta**, not a global param | `tag "${params.sample_name}"` everywhere (identical under fan-out) | `tag "${meta.id}"` | Switch tags to `${meta.id}` once meta maps land (#1). |
| 5 | optional inputs as empty/optional tuples | sentinel files (`file('NO_GFF')`) | optional meta tuples / `[]`; sentinels only where they truly simplify | Prefer optional channels over `NO_FILE` sentinels. |
| 6 | `nextflow_schema.json` + `nf-schema` param validation | hand-rolled `validateInputs()` | hand-rolled `validateInputs()` (phase 1), params structured for a future schema | Add `nextflow_schema.json` + `validateParameters()`. |

Items #1–#4 are the substantive ones; #5–#6 are lower priority.
