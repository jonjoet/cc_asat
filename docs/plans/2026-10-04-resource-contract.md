# Shared parser and resource contract — revision 2

Contract ID: `cc-resource-v1`. Status: proposed, awaiting independent re-review and user
summary approval. This is a planning artifact, not implementation or test execution evidence.
Authoring selection: gpt-6-astra / high per dispatch; no separate native attestation available.

Authority: 2026-10-04 plan-fix dispatch and REQUIREMENTS.txt SHA-256
`e6c47c724a34d8bd68ffb79700fcf33ca4a12c25f0bacde74ab0bc5277e738f0`.
This document resolves review-1 B2/B3 using the parent's R1/R3/R4 reconciliation. It is the
single normative policy/schema/vector source for both repository plans. Parent copies it
**byte-for-byte** to `docs/plans/2026-10-04-resource-contract.md` in cc_asat; both plans record
its SHA-256. No sibling copy has been performed by this author. Changes require a new hash,
matching copies and re-review. No common installed library or cross-repository runtime import.

The sole future fixture path in **both** repositories is
`tests/integration/resource_vectors.json`. It does not exist as an implementation deliverable
of this planning task. **Parent assigns the fresh gcev implementer as the sole fixture author.**
That implementer materializes the approved contract once, saves the completed fixture and its
SHA-256 in immutable evidence, and returns both to parent. Only after parent supplies that
completed artifact does the asat implementer copy it byte-for-byte and verify its hash. Asat
may build independent plumbing beforehand, but must not read an in-progress gcev file or
independently recreate its case IDs/expectations. No fixture is authored during planning.
No separate normative table remains in either implementation plan.

## Engine/parser and workflow selection

Set `manifest.nextflowVersion = '!>=26.04.6'`. Pin 26.04.6 for reproducible acceptance.
Explicit v2 and genuinely unset `NXF_SYNTAX_PARSER` are supported primary paths. V1 on
26.04.6 is a focused fallback: configuration/resource/parameter gates, not another full
scientific/browser acceptance matrix. Reject 26.04.5 under both parsers before tasks, checking
native version-mismatch wording and the required version; do not require a custom upgrade
message. Later engines are permitted by the floor but need the focused gates on upgrade.
No 25.04.0 support, typed params block, or other v2-only syntax while retaining this fallback.

The patch-level floor is deliberate: the reviewed strict closure mechanisms work on this
exact engine. Raising compatibility beyond resourceLimits alone avoids an older-engine config
rewrite and mixed CLI conversion semantics. It does not imply lower engines cannot work.

cc_asat annotation-only selection is **PENDING USER**, outside this resource reconciliation.
Recommended public interface is `--workflow full|annotation_transfer_only` on a single entry
workflow; the alternative is a separate root script. Strict v2 rejects `-entry`, including
previews; it cannot be a successful v2 gate. Parent must obtain the ruling, amend the sibling
plan's exact commands and documentation, and review it. Do not represent either alternative
as approved or change gcev's public entrypoint. Shared parameter/resource cases apply to both
asat execution paths once selected; one v1 legacy `-entry` check may be retained by that plan.

## Effective maxima, defaults and validation

Use effective Nextflow params after normal config/profile/YAML/CLI resolution; never reparse
the user's command or YAML. CLI wins over params-file, which wins over merged config params.
Config sources retain Nextflow order: NXF_HOME, project, launch, then ordered `-c` files and
their selected profiles. The P-series below deliberately constructs one controlled ladder;
it is not a claim that profile values universally outrank every external config assignment.
Do not support `-C` replacement of the whole project config as retaining the project contract.

Omitted CPU default: `max(1, Runtime.runtime.availableProcessors() - 2)`.
Omitted memory default: `max(1, floor(MemTotal_kB/1048576) - 2)` GiB from `/proc/meminfo`;
if reading/parsing fails, use `floor(Runtime.runtime.maxMemory()/1073741824)` before the same
reservation/floor. Omitted time default: 168h. Detection is a launch-host heuristic, not
cgroup/Slurm/worker-node allocation. It supplies defaults only. Explicit maxima above or below
detection win. Explicit null is invalid for caps. Log effective maxima, without top-level
config printing. No production detector knobs, detector redesign or retry policy.

CPU accepts integral numbers or trimmed ASCII digit strings in 1..2147483647, including leading
zeros. Reject Boolean, fractional/decimal/exponent forms, null, collections, nonnumeric and
out-of-range values before narrowing. Memory accepts MemoryUnit or trimmed unit-bearing string;
time accepts Duration or trimmed unit-bearing string. Require finite positive quantities
representable as at least one byte / one millisecond and at most signed-long maximum; reject
overflow rather than saturate. Bare numeric memory/time values are invalid. Preserve native
Nextflow units: KB/MB/GB mean 1024/1048576/1073741824 bytes. Fractional unit quantities remain
valid if representable; preserve native parsing of compound durations. No CPU bound applies
to gcev's arbitrary-sized sequence_end_window. No new scientific-threshold hardening is implied.

Validate all effective caps and public Boolean inputs in entry preflight **before any task**.
Late resource-limit closures also perform safe cap conversion, not fallback-on-error.
Diagnostics use these exact templates (engine prefix/timestamp outside the text is immaterial):

```text
E_CPU: ERROR: --max_cpus must be an integer >= 1 (maximum 2147483647); received '<value>'.
E_MEM: ERROR: --max_memory must be a positive memory quantity with units, e.g. '512 MB' or '8 GB'; received '<value>'.
E_TIME: ERROR: --max_time must be a positive duration with units, e.g. '30min' or '12h'; received '<value>'.
E_BOOL: ERROR: --<name> must be a boolean (true or false); received '<value>'.
E_AUTO: ERROR: --reorient_assembly must be a boolean (true or false) or YAML null for auto; received '<value>'.
```

Render `<value>` deterministically: strings retain supplied spelling with backslash, single
quote, CR, LF and tab escaped; other types use compact JSON (`null`, `true`, `[]`, `{}`, numbers).
Templates identify the parameter even when native unit parsing threw an exception. For the
stable typed YAML cases below, assert the complete template and exact rendered received value.
For CLI, assert the complete parameter-specific template with only the received-value slot
variable: exact prefix through `received '`, escaped value, exact final `'.`. Preserve actual
rendering/type and raw argv, but do not require identical rendering across parsers (v1 can
convert a large digit string to Double). Neither nonzero exit nor parameter-name-only matching
is sufficient. No re-reading CLI tokens to undo the engine's own conversion. Send every
dash-leading CLI value as one `--name=value` argv element, e.g. `--max_time=-1h`; using this
equals form for all CLI cases is permitted. Shell quoting must preserve spaces as one value.

## Scaling and ceilings

Let C, M, T be the validated integer CPU cap, byte cap and millisecond cap. For d=4 (low)
or d=2 (medium), use integer `ceilDiv(x,d) = (x div d) + (x mod d == 0 ? 0 : 1)`;
avoid `(x+d-1)` overflow and floating-point arithmetic. MiB truncation below intentionally
matches current gcev `MemoryUnit.toMega()` behavior.

```text
cpu(d,F)  = min(C, max(F, ceilDiv(C,d)))
mem(d,F)  = min(M, max(F, max(1,ceilDiv(M div 1048576,d))*1048576))
time(d,F) = min(T, max(F, max(1,ceilDiv(T,d))))
```

| Tier key / label | CPU | Memory bytes | Time milliseconds |
|---|---|---|---|
| single / process_single | 1 | min(M,2147483648) | min(T,3600000) |
| low / process_low | cpu(4,1) | mem(4,1073741824) | time(4,3600000) |
| medium / process_medium | cpu(2,2) | mem(2,2147483648) | time(2,14400000) |
| high / process_high | C | M | T |
| unlabelled / no label | C | M | T |

Use explicit final tier clamps **plus** global closure-valued `process.resourceLimits` deriving
all three dimensions from effective params at task evaluation time. A plain eagerly evaluated
map is insufficient: review-1 reproduced stale caps after `-c` overrides. Native limits protect
withName/alias/attempt-based requests; explicit tier clamps protect their own calculations.
Return MemoryUnit/Duration values. No label uses detected capacities after overrides. Keep
existing module labels. Site configs may lower requests; replacing resourceLimits or injecting
resource-changing `task.ext.args` thread flags is unsupported customization. Do not add
speculative thread-override guards as this migration. No arbitrary-config security claim.

One CPU is supported in every tier. A floor is not a tool requirement. Extra threads and pipes
may time-share that allocation. Docker CPU shares are not a hard CPU quota; no total runnable-
thread, instantaneous CPU, aggregate memory or pipeline-concurrency guarantee is introduced.
Tiny allocations can fail normal work; never enlarge them or retry above them. If a pinned
enabled tool truly requires N>1 CPUs, require actionable preflight **before any pipeline task**:
`ERROR: <process/tool version> requires at least <N> CPUs, but --max_cpus is <C>.`
Follow with raise-cap or an existing optional-feature disable remedy (raise-cap only for required
work). Preserve tool evidence and obtain parent reconciliation; do not invent a global minimum.

## Boolean and nullable auto contract

Accept actual Boolean or trimmed **case-insensitive** `true`/`false` strings. Canonicalize to
Boolean in workflow options and lower-case text for tool arguments. Missing values retain their
existing defaults. Reject numeric values/surrogates, yes/no, blank, arbitrary strings and
collections. Null is allowed only for nullable `reorient_assembly`: missing/YAML null selects
bacterial=true, fungal=false, and false when organism_type is absent on asat's currently
permitted annotation-only path. Explicit false always wins; CLI strings `null` and `auto` are
invalid. The pending public selector does not change that scientific behavior.

Workflow options maps are not config variables. Config closures that interpolate the Boolean
must use the effective raw param's `toString().trim().toLowerCase(java.util.Locale.ROOT)` after
entry preflight has validated it. In gcev these are the sequence_end_filter argument builders
for JBROWSE_BUNDLE and BUILD_REPORT in conf/modules.config. Do not capture a map before config
merging or mutate global params after includes.

## Fixture schema and stable vector IDs

UTF-8 JSON; `schema_version: 1`, `contract_id: "cc-resource-v1"`,
`contract_sha256: "<hash of this file>"`, `resource_cases`, `precedence_cases`,
`negative_cases`, `boolean_cases`, `mechanism_cases`. IDs are unique strings from the tables
below; do not recycle them. Each resource row has:

```json
{
  "id": "R01",
  "input": {"max_cpus": 1, "max_memory": "128 MB", "max_time": "30min"},
  "effective": {"cpus": 1, "memory_bytes": 134217728, "time_ms": 1800000},
  "expected": {"single": [1,134217728,1800000], "low": [1,134217728,1800000],
    "medium": [1,134217728,1800000], "high": [1,134217728,1800000],
    "unlabelled": [1,134217728,1800000]},
  "mode": "execute", "transports": ["cli","yaml"]
}
```

Every triple is `[integer CPUs, integer bytes, integer milliseconds]`, never MB or hours.
All five expected keys are required. Table H/U abbreviates two identical values only here;
JSON contains both. Integers must be parsed losslessly. All R rows run on 26.04.6 v1/v2 with
both transports; unset-parser focused confirmation uses R02/R03. Values are specifications
derived from the reviewed arithmetic, not results from this revision's product testing.

| ID | Input C / memory / time | Effective = H/U | Single | Low | Medium | Mode |
|---|---|---|---|---|---|---|
| R01 | 1 / 128 MB / 30min | [1,134217728,1800000] | [1,134217728,1800000] | [1,134217728,1800000] | [1,134217728,1800000] | execute |
| R02 | 1 / 512 MB / 30min | [1,536870912,1800000] | [1,536870912,1800000] | [1,536870912,1800000] | [1,536870912,1800000] | execute |
| R03 | 8 / 7 GB / 12h | [8,7516192768,43200000] | [1,2147483648,3600000] | [2,1879048192,10800000] | [4,3758096384,21600000] | execute |
| R04 | 3 / 3 GB / 3h | [3,3221225472,10800000] | [1,2147483648,3600000] | [1,1073741824,3600000] | [2,2147483648,10800000] | execute |
| R05 | 2 / 3 GB / 5h | [2,3221225472,18000000] | [1,2147483648,3600000] | [1,1073741824,4500000] | [2,2147483648,14400000] | execute |
| R06 | 5 / 10 GB / 10h | [5,10737418240,36000000] | [1,2147483648,3600000] | [2,2684354560,9000000] | [3,5368709120,18000000] | execute |
| R07 | 7 / 7169 MB / 13h | [7,7517241344,46800000] | [1,2147483648,3600000] | [2,1880096768,11700000] | [4,3759144960,23400000] | execute |
| R08 | 8 / 4097 MB / 28800001ms | [8,4296015872,28800001] | [1,2147483648,3600000] | [2,1074790400,7200001] | [4,2148532224,14400001] | execute |
| R09 | 1 / 1536 KB / 1500ms | [1,1572864,1500] | [1,1572864,1500] | [1,1572864,1500] | [1,1572864,1500] | execute |
| R10 | 1 / 1 MB / 1ms | [1,1048576,1] | [1,1048576,1] | [1,1048576,1] | [1,1048576,1] | resolution_only |
| R11 | 1 / 1 B / 1ms | [1,1,1] | [1,1,1] | [1,1,1] | [1,1,1] | resolution_only |
| R12 | " 0003 " / 1.5 GB / 1h 30min | [3,1610612736,5400000] | [1,1610612736,3600000] | [1,1073741824,3600000] | [2,1610612736,5400000] | execute |
| R13 | 8 / 4096.5 MB / 8h | [8,4295491584,28800000] | [1,2147483648,3600000] | [2,1073741824,7200000] | [4,2147483648,14400000] | execute |

R01–R11 are the review R3 union plus explicit one-byte boundary. R12 tests units/leading zeros;
R13 distinguishes toMega truncation before proportional scaling. R10/R11 resolution-only rows
use five `exec:` processes (single/low/medium/high/unlabelled), recording their resolved task
directives from the exec bodies; normal terminate-on-error behavior, all five records and exit
0 are mandatory. No shell task, tolerated timeout or expected internal engine crash. This
proves directive resolution, not OS enforcement of one byte or one millisecond. No biological
tool runs. Execute rows are tiny echo tasks inside the no-socket outer container and
must all finish, including R09; no actual per-task Docker memory enforcement in this harness.

## Controlled precedence and partial overrides

Define a fixture-only ladder, each stage added to the previous invocation: project defaults
16/16GB/24h; c1 root assignments 6/6GB/6h; c2 root assignments 3/3GB/3h; selected `contract_profile`
defined in c2 sets 5/10GB/10h; YAML 4/4GB/4h; CLI 1/512MB/30min. No launch or user config in this
isolated harness. The real repository `nextflow.config` is loaded first, retaining the actual
resource closures under test. The stage called `project` is a separate appended fixture file
`project.config`, not a replacement repository config. In `c2.config`, put all three root
assignments **before** the `profiles { contract_profile { ... } }` block; no root assignments
follow that block. This ordering is required for v1/v2 parity, not a cosmetic convention.

Run from a fresh evidence directory with isolated NXF_HOME and no launch config. Base command
is `nextflow -c "$SOURCE/nextflow.config" -c "$FIXTURE/project.config"`; append `-c` files in
the P-table order, then `run "$SOURCE/tests/integration/resource_probe.nf"`. P01 adds no files;
P02 adds c1; P03–P09 add c1 then c2; P10 adds c2 then c1. P04–P09 alone add
`-profile contract_profile`. P05/P06 add the full YAML via `-params-file`, P07–P09 the memory-only
YAML. P06 supplies all three CLI caps, P08 only CPU, P09 CPU and time. P10 has no profile,
params-file or CLI cap. Append the test safety/trace overlay after these files in every case;
it must not assign maxima or tier requests. Profile selections do not replace the fixture
stage ordering. Preserve expanded argv and every file; let the engine merge, not the harness.

Each precedence JSON object has `id`, `stages` (ordered strings: project,c1,c2,profile,yaml,cli),
`overrides` (stage-to-parameter-map; omitted keys truly absent), and `expected_effective`
with integer cpus/memory_bytes/time_ms. Tasks for all five tiers must match formulas from that
expected effective cap, independently of the production helpers. Preserve exact input files.

| ID | Invocation stages / variation | Expected effective [C,bytes,ms] |
|---|---|---|
| P01 | project | [16,17179869184,86400000] |
| P02 | project,c1 | [6,6442450944,21600000] |
| P03 | project,c1,c2 | [3,3221225472,10800000] |
| P04 | project,c1,c2,profile | [5,10737418240,36000000] |
| P05 | project,c1,c2,profile,yaml | [4,4294967296,14400000] |
| P06 | project,c1,c2,profile,yaml,cli | [1,536870912,1800000] |
| P07 | through profile; YAML contains only max_memory='512 MB' | [5,536870912,36000000] |
| P08 | P07 plus CLI contains only max_cpus=1 | [1,536870912,36000000] |
| P09 | P08 plus CLI max_time='30min' | [1,536870912,1800000] |
| P10 | project,c2,c1; no profile/YAML/CLI | [6,6442450944,21600000] |

Run P01–P10 under v1/v2, plus P06 unset. One dimension at a time can inherit or override;
neither null nor false means omission. Negative YAML/null cases prove that distinction.

## Negative inputs and Boolean case IDs

Negative fixture objects: `id`, `parameter`, `input` (typed JSON), `transports`,
`diagnostic` (template key), `expected_tasks:0`, and `assertions` keyed by transport:
`yaml: {mode:"exact", received:"<independently rendered input>"}` and, when CLI is required,
`cli: {mode:"template"}`. `received` contains the literal expected escaped value, not a matcher
or a value copied from the result. The fixture author fills it from the typed input using the
rendering rule above. The checker substitutes it into the named template for exact YAML checks;
CLI uses the single-variable-slot rule above. E_BOOL/E_AUTO objects use the same assertions.
Other params use valid R03 caps and valid
pipeline inputs. Each ordered table entry below expands to its own ID using two-digit ordinal
in listed order, e.g. `NC-01`, `NM-01`, `NT-01`. This expansion is part of schema version 1;
do not combine failures or let one bad dimension mask another. YAML is mandatory for every
entry. CLI additionally tests every nonempty scalar string/numeric entry; booleans additionally
use CLI true/false. Null/list/map/empty cases need only typed YAML. Capture effective rendering.
These are full helper-level grammar cases; real-entry sampling is explicitly bounded below.

| Prefix / parameter / diagnostic | Ordered typed JSON inputs |
|---|---|
| NC / max_cpus / E_CPU | `0`, `-1`, `1.5`, `"1.0"`, `"1e3"`, `true`, `false`, `null`, `""`, `" "`, `[]`, `{}`, `"bogus"`, `2147483648`, `"999999999999999999999"` |
| NM / max_memory / E_MEM | `"0 B"`, `"-1 MB"`, `"bogus"`, `"1 XB"`, `null`, `true`, `false`, `""`, `" "`, `[]`, `{}`, `1024`, `"1024"`, `"NaN GB"`, `"Infinity GB"`, `"9223372036854775808 B"`, `"0.0001 B"` |
| NT / max_time / E_TIME | `"0ms"`, `"-1h"`, `"bogus"`, `"1 fortnightz"`, `null`, `true`, `false`, `""`, `" "`, `[]`, `{}`, `1000`, `"1000"`, `"NaN h"`, `"Infinity h"`, `"9223372036854775808ms"`, `"0.0001ms"` |

Boolean objects: `id`, `input` (or `omitted:true`), `nullable`, `expected` (Boolean/null or
`"existing_default"`), `diagnostic` on failures, `transports`. Test these cases across every
public Boolean name in the repository's plan; append `/<name>` to result IDs. No scientific
default changes. Expected values are explicit per ID:

| ID | Typed input | Expected Boolean |
|---|---|---|
| B01 | `true` | true |
| B02 | `false` | false |
| B03 | `"true"` | true |
| B04 | `"false"` | false |
| B05 | `" TrUe "` | true |
| B06 | `" FaLsE "` | false |
| B07 | `"FALSE"` | false |
| B08 | `"False"` | false |
| B09 | omitted | existing default (nullable auto resolved by A cases) |

All supplied values use YAML and CLI spelling. B09 omits the key entirely in both batches.
BN01–BN09 inputs: `1`, `0`, `"yes"`, `"no"`, `""`, `" "`, `[]`, `{}`, `null`; E_BOOL
for nonnullable flags. Add BN10/BN11 strings `"null"`/`"auto"`. Null for nullable reorientation
is instead A01; A02 is omission. A01/A02 × bacterial/fungal/absent organism expect true/false/false
after auto resolution; A03 explicit false stays false for all three. Invalid nullable flags use
E_AUTO. BN transports follow the negative scalar/shape rule above. Test helper conversion and
the real-entry subset below; preview does not prove output gating. A01 uses typed YAML only;
A02 omits the key in both transport batches; A03 supplies false via YAML and CLI. No CLI null
is substituted for the YAML-null auto case.

## Common parameter batching and coverage map

Use this same rule in both repos. The fixture adds `parameter_batches` with H-YAML/H-CLI and
`entry_cases` with EV/EN/EC/EA IDs below. These are expansion recipes, not repository-specific
copies of the normative cases. The runner supplies its flag inventory, defaults and routes.
Each batch object has `id`, `transport`, `case_refs` and `expand_flags` (Boolean); nullable
contexts expand from the A cases. Flag expansion applies only to Boolean cases; resource cases
run once per transport/parser, not once per flag. Each entry recipe has `id`, `expand` (`once`, `flags`,
`dimensions` or `nullable_routes`), `layers` (config/YAML/CLI maps or the explicit all-flags
assignments below), `case_refs`, `expected_exit` (`zero` or `nonzero`), `expected_tasks:0`,
and negative `diagnostic`/`assertions` references. Expand IDs with `/route` and `/flag` or
`/dimension` as needed; append parser only in the result key. Save resolved input maps and
expected diagnostic assertions in the pre-run coverage inventory so no recipe relies on
guessing from logs. Repo-specific inventories live in the runner, not a divergent fixture.

**Helper layer:** H-YAML and H-CLI each run once per parser (26.04.6 v1/v2: four startups per
repo). Include every NC/NM/NT case on its required transports and every B/BN case for each
public Boolean; for nullable reorientation substitute A01 for BN09 and include all A01/A02/A03
organism contexts. Include resource validation of R01–R13 as well. Inputs use unique keys such
as `case_NC_02`, through a real params-file or real `--case_NC_02=-1` argv; the harness passes
the resulting effective value and intended public name to the **production normalization
helper**, not a reimplementation. Omission cases have no key. This batches engine transport
conversion without losing per-case type information. Pure validation must expose catchable
failures to the harness; the production entry adapter still terminates on the first invalid
input. Catch each expected helper rejection independently, recording exact diagnostics and
normalized type/value for every ID/flag/context. Exit 0 only when the whole batch matches;
no processes or submissions. Do not concatenate invalid inputs into one production validation
call, where the first failure would hide the rest. Only the harness catches expected failures.

**Real-entry layer:** run each following row on v1 and v2 for each supported public route
(one gcev route; two asat routes after the deferred interface ruling). Use valid route fixture
inputs and R03 caps; all unrelated options valid. Every invocation uses preview and requires
zero tasks; success exit 0, rejection nonzero with the specified diagnostic assertion. No
special production test parameter or bypass is added. Observe scientific consumers separately.

| IDs / expansion | Inputs and required result |
|---|---|
| EV01 | All public Booleans CLI `FALSE`, overriding YAML `"yes"` and appended config `"no"` for those flags. Accept; proves CLI precedence and explicit false acceptance for every flag. |
| EV02 | All public Booleans YAML `" TrUe "`, overriding appended config `"yes"`; no Boolean CLI. Accept; proves YAML precedence and true acceptance for every flag. |
| EV03 | No Boolean overrides in appended test config, YAML or CLI; retain existing repository/profile route defaults. Accept. |
| EV04 | Config sets all flags true, YAML sets all false, CLI sets only the lexicographically first public flag true. Accept; partial Boolean override. Exact helper values and resource P-series remain separate oracles. |
| EN-CLI/<flag> | One flag invalid via CLI `yes` (BN03); all others omitted/default. Reject E_BOOL or E_AUTO naming that flag. |
| EN-YAML/<flag> | One nonnullable flag YAML null (BN09); nullable reorientation instead YAML [] (BN07). Reject exact E_BOOL/E_AUTO. |
| EC-CLI/<dimension> | One cap CLI NC-02 (`-1`), NM-02 (`-1 MB`) or NT-02 (`-1h`), using equals syntax. Reject its complete parameter-specific template. |
| EC-YAML/<dimension> | One cap YAML null: NC-08, NM-05 or NT-05. Reject exact diagnostic. |
| EA01 / EA02 (asat only) | Reorientation YAML null / omitted. On full route use bacterial / fungal respectively; on annotation-only route use absent organism / bacterial respectively. Accept; helper layer verifies the exact auto result. Explicit false is covered by EV01 and all three A03 contexts at helper level. |

Both actual asat routes validate every public flag, even if a consumer is unused on that route.
Use route-valid fixtures in the local plan; full route never omits a required organism. The
selector remains USER DEFERRED; do not run interface-dependent cases through rejected `-entry`
on v2. Existing scientific constraints remain in force and are not bypassed to make previews
pass. If a valid Boolean combination exposes an existing independent input constraint, adjust
only the fixture inputs and record the constraint, not the case's Boolean assignments.

For F flags and R routes, real-entry count per parser is R × (4 + 2F + 6), plus 2R for a repo
with nullable reorientation. Thus gcev (F=9,R=1) has **56 real-entry invocations + 4 helper
batches = 60**; asat (F=10,R=2) has **128 + 4 = 132** across the two parsers. These counts
exclude existing scientific/numeric negatives, selector-specific cases, R/P/L/D resource gates
and actual task acceptance. Do not multiply helper batches by route or by flag. H-CLI/H-YAML
contain many assertion rows, not many startups; preserve row counts separately.

Write `parameter-coverage.tsv` before running: case ID, flag/dimension, organism context,
parser, transport, layer (helper/entry/consumer), invocation ID, expected outcome and artifact.
Every grammar row maps to a helper batch; every public flag/route maps to EV01–04 and both EN
cases; every resource dimension/route maps to both EC cases; nullable paths map to EA/helper A.
Append actual outcome without dropping rows. Consumer rows cite the existing local scientific
acceptance/one-CPU gates, not preview output. Missing mapped rows or unexpected tasks fail.
This deliberately does not execute every spelling through every real consumer: grammar is
exhaustive at the helper boundary, entry wiring has representative success/failure/precedence,
and downstream scientific gating retains each plan's existing bounded acceptance matrix.

## Mechanism cases, default oracle and pass conditions

Mechanism JSON objects have `id`, `kind`, `spec` (the inputs named here), and `assertions`
(the exact required checks here); engine/parser/result evidence lives outside the fixture.

- L01: R02 with withName asking 99 CPUs/99GB/999h. L02: the same through a fully qualified
  aliased process. Observe all dimensions clamped to R02, with actual task completion.
- L03: R02 synthetic process requests cap × task.attempt, fails intentionally at attempt 1,
  succeeds at attempt 2 with maxRetries=1. Both attempts' directives <= caps; exactly two
  attempts. Run in both repos under v1/v2; unset confirmation L01 only. Production retries unchanged.
- D01: omit all maxima, use the 26.04.6 image with `NXF_OPTS='-Xmx768m -XX:ActiveProcessorCount=4'`.
  A separate minimal no-config Nextflow script in the **same container and JVM flags** prints
  raw Runtime.availableProcessors and Runtime.maxMemory; also preserve that container's raw
  `/proc/meminfo`. The script contains no production detector/scaling functions. Require raw
  CPU=4 (otherwise environment gate fails), so expected CPU default=2. Independently parse
  MemTotal with the Python checker, floor whole GiB and reserve two; expected time=604800000ms.
  Then run the production config with omitted maxima and compare all tiers. Docker --cpus is
  not the oracle for JVM processors and --memory is not the oracle for /proc MemTotal.
- D02: repeat with ActiveProcessorCount=1; require observed raw CPU=1 and default CPU=1.
- D03: fallback component test. Extract the real default-memory closure byte-for-byte into
  a run-directory config; change only its `/proc/meminfo` literal to a nonexistent run-local
  file, preserving source excerpt/hash and exact one-literal patch. Evaluate under both parsers
  with `NXF_OPTS='-Xms64m -Xmx5g -XX:ActiveProcessorCount=4'` for D03 only, and an independent
  raw maxMemory observation under those same flags. Require observed maxMemory >=5 GiB or fail
  environment setup; expected
  max(1,floor(maxMemory/1073741824)-2)*1073741824 bytes. This tests the real closure's fallback,
  not a separate copied algorithm: an observed exact 5 GiB must yield 3 GiB, distinguishing
  reservation arithmetic from the 1 GiB floor. Keep the small initial heap, no AlwaysPreTouch
  or heap-filling workload; the 5 GiB maximum reserves address space, not a demand to allocate
  the whole heap. The outer container remains bounded, with no host or daemon alteration.
  Label it component-only, not full-pipeline execution.
- D04: explicit R03 with ActiveProcessorCount=4; CPU cap must remain 8 although detection would
  choose 2. D01–D04 v1/v2; D01 also unset. No production detector parameter or cgroup rewrite.

For every invocation preserve RUN.txt first, exact inputs/command/parser/version/image digest,
stdout/stderr/exit, raw directive records, trace and command wrappers when applicable. Results
are `results.tsv` rows keyed by contract/case/engine/parser/transport/tier/attempt with actual
CPUs/bytes/ms, expectation and status. Distinguish resolution-only/component cases from
completed task executions. Require every expected case exactly once per specified cell, exact
values and independent <= cap invariants. Missing rows, unexpected tasks, invalid real-entry
exit 0, unrecorded helper rejection, wrong diagnostics or unlabelled skips fail. Helper batches
exit 0 only after asserting every expected success/rejection. Count invocations/tasks separately
from test functions.

For task-executing resource and scientific gates, generate the test-only per-case overlay
`$CASE/trace-resources.config` and append it with `-c` (including in existing acceptance runners):

```groovy
trace.enabled = true
trace.file = '/absolute/case/path/trace.tsv'  // substitute the actual CASE path
trace.raw = true
trace.fields = 'task_id,hash,name,status,exit,cpus,memory,time'
```

These eight columns are required by resource validators. With raw enabled, memory and time
are bytes and milliseconds; compare requested `time`, never duration/realtime. Fail if any
required column/value is missing, malformed or above its cap. Preserve separate directive
records with tier, attempt and transport, joining to trace task_id/hash/name; retry attempt
identity does not depend on an assumed default trace column. This overlay changes tracing
only, never production config or resource requests. No trace file is required for zero-task
entry/helper checks; their no-submission audit is mandatory. Exec-only R10/R11 use the five
resolved directive records as the primary oracle; they make no shell/OS enforcement claim.

## Common launcher boundary

User instructions prohibit host tests; containerized Nextflow is a deliberate test-infrastructure
addition compared with gcev's current tests/README host-orchestrator convention. Parent discloses
this choice in the approval summary. No socket for lint/config/previews, floor negatives,
parameter checks, default probes, or echo/resource tests. Use an isolated, short-lived Docker
orchestration container with the existing host socket only for gates executing actual Docker
tasks. The socket is privileged access, not a security sandbox; do not change daemon settings,
shared host config, user groups or permissions. Per-container socket group access is sufficient.
Source is read-only; cache/work/output and uid/gid belong to a fresh external run directory;
use identical absolute paths inside/outside for host-daemon task mounts.

The small test launcher and existing NEXTFLOW_BIN seams are the only runner infrastructure
needed, plus parser selection, absolute paths and provenance. Keep the temporary Nextflow+CLI
image recipe in evidence; no production container or CI refactor. Mandatory external run-base
export in every shell; harness/launcher must reject unset, relative, or product-checkout-contained
bases. No fallback under .worktrees. Existing valid same-snapshot gates can be reused with exact
artifact references. Heavy gates run serially across repos. Scientific validators and full gate
commands remain in each implementation plan, not in the shared resource fixture.
