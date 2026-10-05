# Parser v2 and shared resource policy — cc_asat implementation plan

Date: 2026-10-04; revised 2026-10-05, round 3 after review 2. Phase: tier-2 plan-fix only.
Revisions and byte-identical canonical contract adoption are proposed for re-review.
The user-deferred public command-interface choice remains open; independent
planning work is otherwise complete. No implementation is
authorized by this document. Final plan review and user summary approval precede
a fresh implementation session.

## 1. Authority, snapshots, and handoff boundary

Work only in `/home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature`,
branch `claude/ecstatic-thompson-w5cfoh`, starting at
`5e8e2447eb4401967a84c8255f5d04afbbc2fdb8`. The expanded docs-only dispatch permits
this plan and a byte-for-byte copy of the canonical resource contract named below.
No commits, merges, rebases, cherry-picks, publication, or
root/sibling checkout edits during planning. Retain existing PR #4 and its
published history: https://github.com/jonjoet/cc_asat/pull/4 .

Read-only source authorities inspected:

- cc_asat main `5db41dcf4e0416602af8188ef1d8686bf88200e1`, preserved at
  `/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-review-20261004T224225Z/cc_asat/main/checkout`.
  Candidate immediately follows this main; its only change is nextflow.config.
- cc_gcev main `002b0aa33199058f212de172afe1ae3855ae1049`, preserved at
  `/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-review-20261004T224225Z/cc_gcev/main/checkout`.
  Use this main, not old candidate `9fbe1475191658c265b95f6e4d46e2d36d97b440`,
  as the common resource-policy authority.
- Required investigation reports:
  `/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-review-20261004T224225Z/cc_asat/report.md`
  and `/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-review-20261004T224225Z/cc_gcev/report.md`.
  Their source-specific RUN.txt files establish provenance. Their failures describe
  those snapshots, not this unimplemented plan or a future implementation.
- Applicable workspace/repo instructions, cc_asat README and
  `claude_context/optional_gff_plan.md`; cc_asat has no ROADMAP or test suite at
  these SHAs. The optional-GFF plan is explicitly deferred here. cc_gcev
  `docs/ROADMAP.md` identifies its current scientific/reporting contract.

**Requirement authority, now read in full:**
`/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-plans-20261004T231148Z/REQUIREMENTS.txt`
has SHA256 `e6c47c724a34d8bd68ffb79700fcf33ca4a12c25f0bacde74ab0bc5277e738f0`.
The previous missing-authority statement is resolved. The record covers all-tier
caps below floors, shared proportional scaling, command/thread auditing, early
tool-minimum failure, one-CPU semantics, precedence/validation/detection,
Boolean/nullable behavior, parser matrix and scope/history boundaries. Those
requirements are addressed by the sections below and the pinned canonical
contract. The deferred selector ruling remains an explicit approval dependency.

Review 1 was read in full at
`/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-plans-20261004T231148Z/review-1/review.md`
(SHA256 `3f961c817bf52195d18f81a580157230a73d19af13410821d49e2b936c06888f`).
Its synthetic probes are feasibility evidence inspected through that report,
not tests run by this planner or acceptance of future product changes.
Review 2 was also read in full at
`/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-plans-20261004T231148Z/review-2/review.md`.
This revision addresses C1–C3 and N1–N7 through the completed canonical revision
and matching local gate corrections. Its runtime probes were not rerun here.

Authorship: dispatch requests `gpt-6-astra / high`. The native session identifies
Codex/GPT-6 but exposes no independent precise model/effort attestation; no extra
identity probe was made. Do not present dispatch metadata as native proof.
Future plan commit requires separate instruction after independent review; its
model body must truthfully reflect established execution metadata, and its final
trailer must be `Co-authored-by: omnigent <noreply@omnigent.ai>`.

## 2. Acceptance contract and selected compatibility policy

The implementation must achieve all of these together:

1. Both logical cc_asat modes and their modules compile and run with parser v2;
   replacing check_max alone is insufficient.
2. CPU, memory, and time caps from effective parameters govern low, medium,
   high, single, and unlabelled tasks, including caps below every nominal floor.
3. Both repositories consume the canonical contract referenced in section 3.
4. CLI and YAML false remain false; nullable auto remains distinct from false;
   invalid resource/boolean values fail before scheduling any biological task.
5. Existing assembly/annotation results, required inputs, filenames, publication
   routes, Liftoff copy/merge branches, and completion messages are preserved.
   Gcev frame, donor-alignment, complete/internal evidence, IGV/JBrowse and variant
   schema contracts remain frozen in its separately owned implementation.

**Reconciled engine decision: `manifest.nextflowVersion = '!>=26.04.6'`.**
26.04.6/v2, both explicit and unset, is the supported path; 26.04.6/v1 is a
focused fallback checked for config/resources/parameters. 26.04.5 under both v1
and v2 must reject the floor before any task. Older positive cells are removed.
The patch-level floor intentionally excludes older engines rather than importing
25.04 config-expression workarounds and different CLI-typing paths. Review 1
established those costs and showed the chosen mechanisms working synthetically
on 26.04.6; actual repository gates remain necessary. Keep legacy params with
explicit conversion and entry-local `workflow.onComplete = { ... }` handlers.
Run strict lint on 26.04.6 without formatting. Do not claim later engines tested.

### Public mode selection — decision deferred by the user

Review B1 demonstrates that strict parsing rejects `-entry`, including previews.
The existing annotation-only Quick Start therefore needs a public-interface
change. The user has explicitly deferred this choice until the other planning
work is ready. The following is a recommendation, **not a selected or approved
interface**. No question or wait for this choice is part of this revision.

Recommended future interface: one anonymous entry workflow in `main.nf`, using
`--workflow full` (default) or `--workflow annotation_transfer_only`. If selected,
declare default `full` in nextflow.config; validate exactly those string values
before dispatch (reject null/empty/unknown values); normalize resources/Booleans
once, perform the selected mode's existing input validation, then call its named
subworkflow with the options map. Full requires organism_type as today;
annotation-only continues to allow its omission. Unknown selectors fail before
any task. Register completion handling on the actual entry workflow. If this
interface is chosen, finalize its parameter-specific diagnostic in that ruling;
the shared resource contract does not define an E_WORKFLOW template.

Alternative, also unapproved: keep `main.nf` as full mode and add root-level
`annotation_transfer_only.nf` with an anonymous entry invoking the existing
annotation subworkflow. Both roots use the same normalization/preflight helper
and completion handling. Do not introduce --workflow under this alternative.

If the user also chooses to retain the named v1 legacy route, keep
`-entry ANNOTATION_TRANSFER_ONLY` only for 26.04.6/v1, with the same annotation
preflight, and add one bounded v1 compatibility preview. Do not retain or test
this route implicitly. If both selector and legacy retention are selected, the
later ruling must specify their interaction and diagnostic: effective default
`full` cannot distinguish omission from explicit `--workflow full`. Do not invent
CLI reparsing or claim the former nondefault-conflict rule resolves that ambiguity.
Under either choice, update README Quick Starts, params examples, migration
notes, conditional allowlist and every mode gate. No v2/unset gate uses -entry.
Section 8 gives the exact conditional command forms; the later ruling selects
one set before implementation dispatch.

Official references, read during planning:
[parser migration](https://docs.seqera.io/nextflow/strict-syntax),
[resourceLimits](https://docs.seqera.io/nextflow/reference/process/directives/resource-limits),
[manifest](https://docs.seqera.io/nextflow/reference/config/manifest), and
[config precedence/selectors](https://docs.seqera.io/nextflow/config).
They establish parser availability, closure-contained config logic, CLI conversion
changes, task clamping and configuration ordering. Runtime gates remain required.

## 3. Pinned canonical shared contract and local implementation

The normative [shared contract](2026-10-04-resource-contract.md), ID
`cc-resource-v1`, has SHA256
`2a00165b10f57ba9812aac12debb47abb35c2c716b10d48858ad4b3c194ff398`.
It was read in full and copied byte-for-byte, after verifying and preserving the
prior reviewed local hash `c1c2f5f76b964b9d43ee062fc41df74e6b7a553e46d6a157d68ccf9006020284`,
from the parent-supplied immutable artifact:
`/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-plans-20261004T231148Z/fix-3/cc_gcev-final/resource-contract.md`.
The local durable copy is `docs/plans/2026-10-04-resource-contract.md`; its hash
and byte comparison match that source. No in-progress sibling artifact was read.

Cross-repo reconciliation also read the immutable sibling plan
`/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-plans-20261004T231148Z/fix-3/cc_gcev-final/plan.md`
(SHA256 `00d2a36129477390ee3eb9e7f8595784c187d25074f394bc03984fa65131d35f`)
and its adjacent report.md. No vector JSON was authored in planning. The sole
future fixture path in both repos is `tests/integration/resource_vectors.json`;
the parent-assigned **fresh gcev implementer** authors it once from the approved
contract and returns a completed immutable artifact/hash to parent. The fresh
asat implementer copies only that parent-supplied completed artifact byte-for-byte
and verifies its hash. Independent asat plumbing can proceed beforehand; do not
read an in-progress sibling file or independently recreate the fixture.
Document-byte identity is verified; implementation/vector-result parity has not
been run and is not claimed.

That artifact is the sole normative definition of formulas, floors, unit
representation, accepted types, error text, fixture schema/case IDs/expected
bytes and milliseconds, precedence ladder and negative sets. The former asat
normative tables and independent precedence values have been removed. Do not
recreate another table here or derive expected vectors from implementation code.
The fresh implementer must receive this plan and the checked-in contract copy
together. Changes to the contract require new matching copies/hashes and re-review;
this asat planner did not independently edit it.

Reconciliation checklist from this dispatch (summary, not a competing contract):
retain gcev proportional policy, rounding behavior and practical floors; use
integer quotient/remainder ceilings instead of floating point; explicitly clamp
each tier closure and also retain closure-valued native resourceLimits evaluated
from effective params after overrides. CPU integer/digit grammar accepts leading
zeros and is bounded by the gcev range 1..2147483647. Use the canonical gcev-style
`ERROR: --max_cpus must be an integer >= 1 (maximum 2147483647); received '<value>'.`
diagnostic and the canonical memory/time diagnostics. Boolean strings are
trimmed and case-insensitive true/false. Use the canonical precedence, detection,
negative and synthetic retry cases without local substitutions. These decisions
have been reconciled against the delivered document; future gates still must
prove them in actual product code.

Local config mechanism: move detection declarations/try/catch into immediately
invoked default-expression closures. Preserve launcher CPU and Linux MemTotal
detection, JVM fallback, reservations and omitted-parameter defaults as specified
by the contract. Log effective maxima from preflight. Keep config-only output
parseable; no top-level config functions/statements, closure-valued custom params,
runtime params mutation or plugin dependency. A supplied explicit cap replaces
detection rather than receiving a second reservation or detected ceiling. Native
limits must be a late-bound closure, not an early plain map. Every tier closure
returns an explicitly capped request as well, protecting it if site configuration
replaces native limits. Neither mechanism alone proves parser compatibility.

Late closures safely convert effective caps and preserve canonical errors too.
Validate effective caps before any task for either logical mode. No invalid
value silently falls back to detection. User withName requests remain subject to
native caps; repository selectors may not disable them. Arbitrary external
replacement config is not a security boundary; -C replacement of the project
config does not retain this contract. Document --max_* as the supported
resource interface and thread overrides through task.ext.args as unsupported
advanced configuration; add no speculative thread-option guards. Mixed mutually
exclusive engine profiles remain unsupported; engine+test order is covered.

One CPU remains valid, including medium/high. A nominal tier floor is not a
tool hard minimum. Current Docker CPU settings provide **shares, not a hard
quota**; piped programs/OS threads may time-share, and idle host capacity may be
used. Check requested CPUs and tool worker flags without claiming a thread-count
ceiling or hard runtime CPU enforcement. If a pinned tool truly requires a larger
allocation, preflight the selected enabled path **before any task is submitted**,
naming tool/process, minimum, supplied cap and remedy (raise cap or disable that
optional arm). Never wait until the affected task starts or silently inflate
resources. Record and review any demonstrated new limitation.

Tiny positive memory/time caps may cause real OOM/timeouts; metadata-only cases
prove arithmetic at sub-executable sizes. Limits are per-task requests, not an
aggregate budget. Detection still describes the launcher, not a scheduler or
cgroup guarantee; no detector rewrite or production retries are introduced.

## 4. Current-main command and selector audit

These observations concern unmodified current-main source, not the old candidates.
All 17 cc_asat process definitions are labelled: one single, eleven low, four
medium, one high. conf/modules.config only routes publication; it has no CPU
selector overrides or thread flags. Keep labels unchanged.

| cc_asat current-main source | CPU behavior and implementation disposition |
|---|---|
| modules/local/ragtag/{correct,scaffold,patch}/main.nf:26,26,25 | All medium; `-t ${task.cpus}`; no hard-coded minimum. Verify pinned RagTag 2.1.0 one-CPU path and subordinate aligner settings. |
| modules/local/liftoff/main.nf:37 | Medium; `-p ${task.cpus}`. Verify 1.6.3 handles one worker; primary/copies/vendor aliases share policy. |
| modules/local/tgsgapcloser/main.nf:23 | High; `--thread ${task.cpus}`. Docker pins 1.0.3 while Conda says 1.2.1; inspect/test Docker 1.0.3, record discrepancy without upgrading either. |
| modules/local/dnaapler/main.nf:21 | Low; `-t ${task.cpus}`; verify pinned 1.1.0 accepts 1. |
| modules/local/quast/main.nf:31 | Low; `--threads ${task.cpus}`; verify 5.2.0 and subordinate programs, not just CLI help. |
| modules/local/{agat/fix_gff,samtools/faidx,seqtk/fq2fa,seqtk/seq}/main.nf | Low; no explicit multiworker flag. Inspect pinned tools for implicit default pools; keep serial/default behavior unless an actual cap violation is demonstrated. |
| modules/local/{diff_liftoff_copies,filter_megagenes,fix_gff_names,merge_annotations,restore_patch_seqnames}/main.nf | Low; Python helper commands, no threading options. No resource-driven algorithm change. |
| modules/local/rename_ragtag_scaffolds/main.nf:3,17–28 | Single; Python rename commands run sequentially. Use this real module for a tiny one-CPU Docker smoke. Main previously had no single-label selector, so its requests were global maxima. |

The sibling source inspection finds additional assumptions that its owner must
cover. `modules/local/minimap2/align_reads/main.nf:26–35,62–64` explicitly supports
budgets below three while piping minimap2 into samtools sort. With C=1 or 2,
minimap2 gets `-t 1`, sort gets `-@ 0`, index gets `-@ (C-1)`. This is shared CPU
time, not proof that a minimum of three allocated CPUs is required. At C=8,
current arithmetic gives mapper 4, sort extra workers 2, index extra workers 7.
`modules/local/donor_align/main.nf:43–57` pipes minimap2 to calmd and then sorts
sequentially: C=1 yields mapper 1/sort 0/index 0; C=2 gives 1/1/1.
`modules/local/donor_focus_bam/main.nf:19–27` pipes view/filter/view, with index
extra workers max(0,C-1). Do not change canonical donor SAM, tags, alignment
options, record retention or sorting semantics to fix a resource preference.

Gcev `conf/modules.config:182–184` gives the donor-read alias frozen additional
alignment flags without a thread override; donor_align rejects reserved `-t`
arguments. The generic read mapper has task.ext.args after its thread option:
document thread overrides through ext.args as unsupported advanced configuration;
do not add a new guard or change scientific flags in this migration. Preserve
existing donor-policy guards. NucDiff's medium label does not imply two required CPUs:
`modules/local/nucdiff/main.nf:35` has no task CPU flag and configured args only
set nucmer minmatch. IGV high is a resource tier, not a tool CPU minimum. The
other gcev selectors inspected set routes/arguments rather than resource minima.
No IGV relabelling or acceleration is authorized.

Inspect pinned tool help/source and run bounded Docker commands during build to
confirm implicit thread defaults. A help page alone is not runtime proof. Extra
OS threads may time-share the one-CPU request; flags demanding worker counts
above task.cpus are not. Asat checks all seven thread-bearing paths at one CPU;
the sibling's scheduled actual read-mapper cases cover C=1/2/3/5/8 as described
in section 8. Do not imply that every donor wrapper runs at all five counts.
No substantive tool probe was run in this plan-only phase.

## 5. Boolean boundary and migration-only numeric handling

Add `utils/params.nf` with ordinary includable DSL2 functions, not top-level
statements. Pure validation exposes catchable failures for the batched helper
harness; only that harness catches expected failures. The production entry
adapter terminates on the first invalid effective value, before any task.
Implement the canonical strict Boolean grammar from section 3,
including trimmed case-insensitive strings and nullable modes. No permissive
`.toBoolean()` without a membership check. Return an immutable
normalized options map from preflight; pass it through workflow `take:` inputs
and pass the normalized novel-only Boolean into its consuming process. Do not assign
normalized values back into params after includes have captured them.

Normalize these cc_asat booleans for **both logical modes**, regardless of the
eventual public selector choice:
`run_correct`, `fill_gaps_from_ref`, `skip_annotation_transfer`, `skip_merge`,
`liftoff_copies`, `fix_generic_names`, `fix_reference_gff`, `fix_vendor_gff`,
`merge_novel_only`, and nullable `reorient_assembly`.
Null/omitted reorient remains auto: true for bacterial, false for fungal, and
**false when organism_type is omitted on annotation-only**, matching the existing
comparison to 'bacterial'. Full still requires fungal/bacterial. Explicit false
wins even for bacterial; explicit true enables reorientation even on annotation
mode without organism_type. Cover all three auto contexts plus explicit overrides.
YAML null remains auto, not false during normalization. Preserve the existing
annotation-only guards; skip_annotation_transfer must not bypass reference_gff.

Do not add numeric-range hardening for megagene_gene_threshold, liftoff_s,
liftoff_sc, merge_overlap_threshold, merge_word_min_length or max_gene_length_bp.
These values already interpolate into tool commands; retain existing strings,
defaults and downstream tool validation. Only max_gene_length_bp's truthiness
requires migration handling: null and numeric/string zero keep the length limit
disabled, while nonzero values retain the existing argument interpolation.
Preserve the existing omitted-argument behavior for zero; no new range/type
rejections are implied. Test CLI/YAML zero and a representative positive value.
The other module change is merge_novel_only: its normalized false must not emit
--novel-only. No options input or source edit is needed in LIFTOFF. Do not
interpret paths or feature-list strings as booleans.

Sibling parity includes strict boolean parsing, not identical flag inventories:
its owner must handle sequence_end_filter, igv_include_unfiltered_tracks,
donor_igv_reports, igv_reports, igv_whole_genome, igv_structural_report,
igv_target_frame, igv_include_bam and jbrowse_bundle without coupling independent
report gates. Preserve its existing integer/domain checks and null contracts.

## 6. Concrete implementation write set

This is the proposed **future** cc_asat build allowlist, subject to approved
implementation dispatch. It is not permission to edit these files during planning.

| File | Required change |
|---|---|
| nextflow.config | Closure-contained detection defaults; explicit tier clamps plus late native-cap closure per canonical contract; no top-level scripting/check_max; enforced floor; preserve profiles/report routing. Add workflow default only if selector chosen. |
| utils/params.nf (new) | Pure catchable resource/Boolean validation plus terminating entry adapter, options map and shared mode-specific preflight; conditional selector validation. No threshold hardening or scientific logic. |
| main.nf | Shared preflight before any task; normalized run_correct validation; pass options and entry-local completion. If recommended selector is chosen, anonymous dispatcher plus --workflow validation; conditional v1 legacy entry only if approved. |
| annotation_transfer_only.nf (new, conditional only) | Add only if the separate-root-script alternative is selected; root-level anonymous entry, shared annotation preflight and completion. Otherwise this file is outside the future allowlist. |
| workflows/annotation_transfer_only.nf | Add take: options and main: before existing statements; replace direct boolean uses with options; preserve outputs and vendor lift semantics. |
| workflows/euk_scaffold_validation.nf | Take/pass options; preserve existing channels, sentinels and annotation gating; use normalized reorientation and correction flags. |
| subworkflows/local/annotation_transfer.nf | Take/pass options; use normalized copies, name-fix and merge flags; preserve primary versus copies outputs and aliases. |
| modules/local/filter_megagenes/main.nf | Migration-only null/zero length-limit handling; keep existing inputs and numeric text interpolation. |
| modules/local/merge_annotations/main.nf | Add val novel_only fed from normalized options by both aliases; retain numeric interpolation and merge algorithm unchanged. |
| README.md | Selected future public mode route, migration from -entry, conditional v1 legacy note; reconciled engine/parser policy, canonical resource policy, false/null examples including absent annotation organism, detector caveat and gate commands. |
| assets/params.example.yaml (new) | Required-path placeholders, caps, YAML false/null examples; add workflow only if the selector recommendation is approved. |
| tests/README.md (new) | Reproduction, Docker setup, evidence schema, modes/counts, runtime versus metadata scope. |
| tests/parser_resources/run.sh (new) | Docker-only orchestrator with modes below; uid/gid, immutable images, RUN-first, parser/version flags, exit capture and no source writes. |
| tests/parser_resources/{probe.config,assert_results.py,parameters.nf,rename.nf,detect.nf} (new) | Resource safety/trace overlays, canonical-vector consumer, batched real-helper checks, explicit-bin-path rename harness and independent raw detection probe. No local normative cases.json. |
| tests/integration/resource_probe.nf (new) | Five-label observable resource harness at the canonical command path; exec-only R10/R11 plus echo and test-only retry cases. This replaces the earlier proposed resources.nf path, not an additional harness. |
| tests/integration/resource_vectors.json (new, future build only) | Copy the completed parent-supplied artifact authored once by the fresh gcev implementer; verify its exact hash. No planning JSON exists; no independent local cases.json. |
| This plan and docs/plans/2026-10-04-resource-contract.md | Docs-only handoff; the contract is a byte-identical adopted copy. Future contract changes require matching hashes and re-review. |
| tests/fixtures/parser_resources/{assembly.fasta,reference.fasta,reference.gff3,vendor.gff3,reads.fastq,ragtag_scaffold.fasta,ragtag_unplaced.fasta} (new) | Tiny deterministic valid input set for both previews, safe tool microchecks and rename output assertions; fixture generation recipe in tests README. |

No bin/ algorithm edits, conf/modules.config publication changes or container
version upgrades are planned. If a pinned module actually needs a thread flag
repair, return file/line evidence and request an allowlist extension before
editing that module. Cascading lint errors must be re-evaluated after the direct
repairs; unrelated lint-warning cleanup or broad framework refactoring is out.
Small channel/explicit-closure warnings may be fixed only in already touched files.

## 7. Canonical vectors and asat-specific acceptance coverage

Consume the pinned contract's vectors, schema, negative cases, diagnostics
and precedence ladder without maintaining an asat normative table. Contract-byte
identity is verified; parent must compare the future JSON fixture and results
when implemented. This revision does not claim runtime parity passed.
Every executable cap vector covers
single/low/medium/high/unlabelled, comparing task.cpus, task.memory.toBytes() and
task.time.toMillis() to the supplied expected bytes/milliseconds. Sub-executable
memory/time cases R10/R11 use five `exec:` processes to record resolved directives,
normal terminate-on-error behavior and mandatory exit 0 with all five records.
No shell tasks, tolerated timeouts or internal engine crashes pass these rows.
This is directive-resolution evidence, not OS enforcement of one byte/one ms.
R09 is an executable echo case in the no-socket local harness, not a per-task
1.5-MB Docker container. Record the distinction, not a false
tool-runtime pass. Independent assertions consume the canonical expected values;
they must not call the production scaling implementation as their oracle.

Run contract R01–R13, P01–P10, L01–L03 and D01–D04 on 26.04.6/v1 and v2 with
their specified transports/modes; unset focused resource confirmation is only
R02/R03, P06, L01 and D01. L02 includes the fully qualified alias; L03 must have
exactly two attempts, first intentionally fails, second succeeds, both capped.
Do not introduce production retry directives.

P01–P10 load the real repository nextflow.config first so its actual resource
closures remain under test. Run from fresh evidence with isolated NXF_HOME and
no user/launch config. The fixture stage named project is an appended
`project.config`, never replacement repository config. In c2.config all root
assignments precede the profiles block, with none following it. Use the exact
ordered -c/profile/YAML/CLI ladder in the canonical contract, including reversed
c2,c1 for P10 and partial overrides for P07–P09. Append the safety/trace overlay
last; it must not assign caps or tier requests. For example, inside the no-socket
launcher P04 is:

```bash
nextflow -c "$SOURCE/nextflow.config" -c "$FIXTURE/project.config" \
  -c "$FIXTURE/c1.config" -c "$FIXTURE/c2.config" \
  -c "$SOURCE/tests/parser_resources/probe.config" \
  -c "$CASE/trace-resources.config" \
  run "$SOURCE/tests/integration/resource_probe.nf" -profile contract_profile \
  -cache false -work-dir "$CASE/work" --outdir "$CASE/results"
```

Use the canonical **H/EV/EN/EC/EA batching and coverage rule**, not an exhaustive
real-entry cross-product. H-YAML and H-CLI each run once per v1/v2 parser: four
helper startups total. Pass every required NC/NM/NT transport, every B/BN case
for all ten flags, nullable A contexts and R01–R13 validation through actual
engine params transport and the production helper. Unique case keys preserve
types; omitted inputs have no key. Catch and record each expected rejection
independently; batch exit 0 requires every row to match and zero processes.
The entry adapter must still terminate normally on invalid input; no test bypass.

Through **both actual selected routes** under v1/v2, run the canonical EV01–04,
EN-CLI/EN-YAML for every flag, EC-CLI/EC-YAML for every cap dimension, and EA01/02
recipes. Use previews and valid biological inputs, even for negatives; validate
all ten flags on either route even if a consumer is unused. This is 128 entry
startups plus four helper batches = **132 shared parameter startups** for asat;
gcev's nine flags/one route produce 56+4=60. These totals exclude R/P/L/D gates,
selector-specific cases, migration-only numeric checks and task acceptance.
Do not multiply helper batches by route or count their assertion rows as startups.

All dash-leading CLI values must be a single `--name=value` argument, including
`--max_cpus=-1`, `--max_memory=-1 MB` and `--max_time=-1h`; preserve shell quoting
and raw argv. Assert complete canonical templates: typed YAML includes the exact
independently rendered received value; CLI allows only that received-value slot
to vary with engine conversion, retaining actual type/rendering. Parameter-only
or nonzero-only assertions fail. No reparsing CLI tokens to reverse conversion.

Before execution write `parameter-coverage.tsv` using the contract's columns,
mapping every grammar ID/flag/context to its helper batch, every flag/route to
EV and EN, every dimension/route to EC, and nullable paths to EA/helper A.
Use the contract's explicit **per-ID B01–B09 expectations**, not alternating
true/false assumptions (B07/B08 both false). A01 is YAML null only, A02 omits
the key and A03 tests explicit false through both transports. Record consumer
rows against the bounded scientific/command gates below; preview is not runtime
output evidence. Append outcomes without dropping expected rows. Missing rows,
wrong diagnostics or unexpected submissions fail; no unrecorded helper errors.

Default oracle follows canonical D01–D04, including the fallback component test.
Use detect.nf as the independent no-config script, with the same engine/JVM flags:
NXF_OPTS='-Xmx768m -XX:ActiveProcessorCount=4' for D01 (raw CPU must be 4),
ActiveProcessorCount=1 for D02 (raw CPU must be 1). Preserve raw maxMemory and
/proc/meminfo; the container Python checker independently derives defaults.
D03 extracts the real memory-default closure byte-for-byte into evidence and
changes only its /proc/meminfo literal to a nonexistent run-local path; retain
source excerpt/hash and one-literal diff. D03 alone uses
`NXF_OPTS='-Xms64m -Xmx5g -XX:ActiveProcessorCount=4'` for both the closure and
independent raw maxMemory observation. Require observed maxMemory >=5 GiB; an
exact 5 GiB yields 3 GiB after reservation, exposing errors hidden by a 768-MiB
heap's floor. Retain the bounded outer container, small initial heap, no
AlwaysPreTouch or heap-filling workload. Label D03 component-only, not a
pipeline run. D04 proves explicit overrides above detection. The contract defines
all expected values. Do not adjust expectations when a JVM flag is ineffective,
mutate host /proc, add detector knobs, or call Docker quotas a detection oracle.

Asat Boolean cases apply the canonical grammar to every flag listed in section
5 using the helper/entry split above, including mixed case/whitespace, negatives
and the canonical Boolean precedence recipes. Nullable reorient covers fungal,
bacterial and annotation-only with organism_type absent, each with omission,
YAML null, false and true. Preserve required organism validation in full mode.
For EV/EN/EC use assembly/reference, reference and vendor GFFs plus reads so
run_correct=true remains valid. Full always supplies a valid organism. EA01/02
use exactly the canonical route/organism assignments: full bacterial/fungal;
annotation absent/bacterial. Keep reference_gff required on annotation-only.
Previews verify branch membership; helper output verifies normalized types.
Real generated commands must omit --novel-only for false, omit the length-limit
argument for null/zero, and preserve representative nonzero numeric interpolation.
Do not introduce a negative numeric-threshold suite. Selected-interface tests
are conditional as specified in sections 2 and 8, never v2 -entry tests.

## 8. Docker gates and exact reproduction interface

Implement the following runner interface as part of the allowlist. These are
future commands, not tests executed during planning. Host shell orchestrates
Docker only; Nextflow, Python assertions and tool commands run in containers.
No host package installation. Heavy gates in the two repos run serially under
parent scheduling. Preserve all outputs, including unsuccessful setup attempts.
The common evidence root `/home/qbk/qbk-code/tmp/cc_gcev` is intentional for both
repositories. In every later shell, export an absolute CC_GCEV_RUN_BASE under
that root; the runner must require the export, require --evidence to name that
same base, and refuse unset/relative/product-worktree-contained destinations.

```bash
repo=/home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature
evidence=/home/qbk/qbk-code/tmp/cc_gcev/cc_asat-parser-v2-build-$(date -u +%Y%m%dT%H%M%SZ)
export CC_GCEV_RUN_BASE="$evidence"
test ! -e "$evidence"
mkdir "$evidence"
printf 'commit: %s   dirty: %s\nstarted: %s\npurpose: parser/resource implementation acceptance\n' \
  "$(git -C "$repo" rev-parse HEAD)" \
  "$(test -z "$(git -C "$repo" status --porcelain)" && echo no || echo yes)" \
  "$(date -u +%FT%TZ)" > "$evidence/RUN.txt"
git -C "$repo" diff --binary HEAD > "$evidence/source.diff"
git -C "$repo" status --porcelain=v1 > "$evidence/status.txt"
# If dirty, also preserve every untracked source file and its hash in a source
# snapshot; record the snapshot and diff hashes in RUN.txt before any gate.
git -C "$repo" diff --check
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode static --engine 26.04.6 --parser v2
for parser in v2 unset v1; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode contract --engine 26.04.6 --parser "$parser"
done
for parser in v1 v2; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode unsupported --engine 26.04.5 --parser "$parser"
done
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode tools --engine 26.04.6 --parser v2
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode docker-rename --engine 26.04.6 --parser v2
# Run this dependent block only after the user selects the public interface.
# CC_ASAT_INTERFACE must then be selector OR scripts, never an inferred default.
: "${CC_ASAT_INTERFACE:?Set to the approved selector or scripts interface}"
for parser in v1 v2; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode entry-parameters --engine 26.04.6 --parser "$parser" --interface "$CC_ASAT_INTERFACE"
done
for parser in v2 unset; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode previews --engine 26.04.6 --parser "$parser" --interface "$CC_ASAT_INTERFACE"
done
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode annotation-smoke --engine 26.04.6 --parser v2 --interface "$CC_ASAT_INTERFACE"
# Only if retaining the legacy route was separately selected:
# bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode legacy-entry --engine 26.04.6 --parser v1
```

Runner implementation must print/preserve the fully expanded Docker/Nextflow
commands, not just its own invocation. Mode definitions:

`--parser unset` must remove NXF_SYNTAX_PARSER from the container environment,
not set it to the literal string 'unset'. Interface-independent modes do not need
a selector decision. Mode-dependent tests are finalized after that decision.

- static: `nextflow lint <repo>` without formatting; zero errors, warnings recorded.
  Also source audit for all boolean consumers, labels, thread flags and selectors.
- contract: `nextflow config <repo> -profile <profile> -flat` for standard, docker,
  conda, singularity, singularity_conda, test, test,docker and docker,test;
  R/P/L/D resource cells exactly as section 7, plus H-YAML/H-CLI batches
  under v1/v2 (four helper startups across the two parsers). Unset uses the
  bounded resource cells and config matrix, not a full parameter cross-product.
  Success requires every expected assertion row, canonical transport-aware
  diagnostics/types/values and no cap violations. Complete v1 fallback also needs
  entry-parameters, but no v1 biological matrix.
- entry-parameters (conditional interface): run exactly the canonical EV/EN/EC/EA
  real-entry recipes through both selected routes: 64 previews per parser,
  128 across v1/v2. Every invocation, valid or invalid, uses -preview and valid
  fixture inputs; assert the specified exit/diagnostic and zero tasks. All ten
  flags are checked on both routes. Retain the section 7 coverage map and exact
  YAML/full-template CLI assertions. Do not repeat the helper grammar cross-product
  through entries. EA absent-organism cases exercise annotation mode only;
  full-mode absent organism keeps its existing required-input error. No socket.
- previews (conditional interface): both logical modes with -preview -cache false,
  valid fixture inputs, unique outdir/work, and bounded section 7 branch/auto/zero
  comparisons. Reuse same-snapshot v2 entry cases where they supply these checks;
  do not repeat the entire grammar matrix. Require successful compilation and
  expected process membership; retain selector-specific negatives plus focused
  unset-parser cap/Boolean negatives, all before tasks.
  Exact route forms after selection are in the table below. Explicit/unset v2
  must agree; previews do not count as tool execution.
- unsupported: 26.04.5/v1 and /v2 run main.nf with valid full-mode inputs and its
  default route. Require nonzero exit, the actual engine version-mismatch text
  identifying 26.04.5 and required >=26.04.6, and zero submitted/executed tasks
  from logs/trace/work inspection; use -preview so even accidental floor bypass
  cannot launch biological tasks. Do not demand invented upgrade advice. A
  syntax error or missing input/image is not a passing floor-rejection case.
- tools: inspect and exercise the pinned command paths in section 4 using the
  criteria immediately below. Record each command's result separately, including
  a clearly named source-only outcome where the bounded fixture fallback applies.
- docker-rename: run the real RENAME_RAGTAG_SCAFFOLDS module using its Python image,
  real scaffold/unplaced fixture inputs, caps 1 CPU/512MB/30min; assert output
  sequence IDs/sequences, resolved resources and `.command.run` memory/CPU-share
  settings. The nested rename.nf script does not inherit repository bin/. Its
  test-only config must append a read-only Docker bind of the absolute repo/bin
  path at that same absolute path, and set the rename process beforeScript to
  `export PATH="<absolute-repo>/bin:$PATH"`. Preserve uid/gid runOptions. Verify
  the bind/export in wrappers and successful resolution of
  rename_ragtag_scaffolds.py; do not edit the production rename module or place
  a script in the repository root. All generated config stays in evidence.
- annotation-smoke (conditional interface): real annotation-only mode on identical synthetic reference
  and assembly with valid reference/vendor GFFs; `--organism_type fungal
  --reorient_assembly false --fix_reference_gff false --fix_vendor_gff false
  --liftoff_copies false --merge_novel_only true --max_cpus 1 --max_memory '4 GB'
  --max_time 1h`; compare expected iterative outputs, no copies/full merge,
  and confirm QUAST completion. This is a tiny integration gate, not a genome
  benchmark. Use at least 1 GB requests for real low-tier tools as the policy gives.
- legacy-entry (conditional retention): one valid-input 26.04.6/v1 annotation
  preview using -entry ANNOTATION_TRANSFER_ONLY and shared preflight; no strict
  parser variant. If retention is not approved this mode must not run.

Conditional public route commands; append fixture --assembly/--reference and
--reference_gff, appropriate organism flag, -profile test,docker, --outdir and
-work-dir in the runner. Previews also append -preview -cache false. In actual
smoke mode append the flags above and omit -preview.

| User choice (not yet made) | Full route | Annotation-only route |
|---|---|---|
| Recommended selector | `nextflow run <repo>/main.nf --workflow full` (also test omission) | `nextflow run <repo>/main.nf --workflow annotation_transfer_only` |
| Alternative separate root | `nextflow run <repo>/main.nf` | `nextflow run <repo>/annotation_transfer_only.nf` |

If the selector is chosen, add invalid/null/empty --workflow cases with zero
tasks and test both default and explicit full. If scripts are chosen, lint and
preview both root scripts, verify their manifest/config resolution, and omit
selector-validation cases. Both alternatives run the same normalization tests,
annotation-without-organism auto tests, Boolean negatives and scientific output
assertions. Neither treats v2 -entry as a supported route.

Tools-mode pass criteria and bounded fallback:

- Cover seven command paths: RagTag correct/scaffold/patch, Liftoff, QUAST,
  dnaapler all and TGS-GapCloser. Supply worker argument 1, preserve scientific
  options, inspect pinned-version help/source for implicit pools, and save the
  actual invocation plus image digest. Execute one command at a time with a
  10-minute timeout; no large genome download/benchmark to satisfy this gate.
- Runtime pass requires exit 0, the documented expected nonempty outputs, and
  a command/source check that configured workers do not demand >1 CPU. Validate
  RagTag FASTA/AGP structure, Liftoff lifted GFF sequence IDs and feature presence,
  QUAST report identifying the fixture, dnaapler output sequence preservation
  up to allowed rotation/orientation, and TGS-GapCloser expected FASTA/details.
  Use a deterministic valid miniature fixture for the relevant operation; a
  biologically valid unchanged output may pass when that is the tool's documented
  no-op behavior. A timeout or input error never proves a CPU minimum.
- If a miniature valid fixture for a tool (notably dnaapler marker search or
  TGS gap filling) is impractical within this bound, do not inflate the fixture
  into new scientific work. Record `SOURCE_ONLY_RUNTIME_NOT_VERIFIED`, the
  failed/skipped runtime case and reason, and exact pinned tool source/help
  evidence showing acceptance/propagation of 1 worker and any implicit threads.
  This is an explicit limited substitute for that micro-runtime gate, to be
  assessed in independent review and disclosed in the handoff; it is not a
  runtime pass or proof of end-to-end one-CPU success. Missing pinned-source
  evidence leaves the gate unresolved. A demonstrated true tool minimum instead
  requires the preflight behavior in section 3 before any product task.
- Gcev's finalized plan schedules `T-READS-C1/C2/C3/C5/C8` for the real read-mapper
  command: reuse its same-snapshot O-READS/v2 for C1, then four tiny module runs
  for C2/C3/C5/C8, checking actual mapper/sort/index flags, trace, BAM and index.
  Its O-DONORS cases retain donor/alias scientific one-CPU checks. Its plan owns
  the exact thread expectations and command; do not duplicate that table here
  or imply every donor wrapper runs at every count. No cross-repo tool execution
  or source edits are delegated from this asat task.

Use Nextflow images pinned by recorded immutable digest, including
`nextflow/nextflow:26.04.6@sha256:83bbf3dd9e84ecd4d53a86620d08fe0259bca00a8f59f6f31664eb90033f460f`.
Resolve and record the official 26.04.5 image digest during build; no invented
digests or mutable latest. The existing investigation records a root-only JAR
permission issue. Preserve its workaround: stream the image's packaged JAR to
the run directory, make that evidence-owned copy readable, and mount it in the
expected NXF_HOME framework path for uid/gid runs. Record JAR hash and actual
`nextflow -version` per engine; do not reuse another engine's JAR or silently run
the host pixi binary. Existing recipes under the investigation runtime directory
are reference recipes, not current-SHA acceptance results.

Static/echo containers: `--user $(id -u):$(id -g) --cpus 4 --memory 4g`,
NXF_OPTS=-Xmx768m except D03's explicit -Xms64m/-Xmx5g override (D cases also
use their canonical ActiveProcessorCount), writable
HOME/NXF_HOME/NXF_CACHE_DIR/NXF_TEMP/TMPDIR/work under each case's evidence
folder, source read-only, PYTHONDONTWRITEBYTECODE=1, cache false, no resume and
one queued task. Test-only local executor admission may exceed outer capacity
for zero-work metadata probes; record that explicitly and never apply it to
biological tasks. In echo/resource probes explicitly disable Docker/Conda/
Singularity and use the local executor inside the outer container. No Docker
socket for static/config/echo/parameter/detection,
preview or floor cases. Direct pinned-tool microcommands likewise need no socket
inside the tool container; the host shell only launches that container.

Actual Nextflow Docker-task gates (rename and annotation smoke) alone use a
Docker-capable launcher container with explicitly scoped daemon-socket access.
All Nextflow invocations remain containerized because project rules prohibit
host tests. This is a deliberate narrow test-harness addition to be disclosed by
the parent in the user summary, not a host-Nextflow fallback. Socket access grants
daemon control; launcher isolation is operational scope, not a security sandbox.
Use only the assigned source/evidence mounts, serial task execution and recorded
commands. Do not change shared daemon configuration, permissions or group setup;
do not run privileged containers or add broad CI/container infrastructure.
Provide docker CLI in an ephemeral test-only image if the Nextflow image lacks
it, with its recipe/digest under evidence; no host installs or production image edits.
Use invoking uid/gid plus the socket's group ID. Bind source and evidence at
**identical absolute host paths** inside the launcher so sibling task mounts
resolve on the daemon host. Source stays read-only. Give child tasks their normal
module images and preserve profile runOptions uid/gid. Record daemon/image
versions and `.command.run` CPU-share/memory flags; outer launcher quotas do not cap
sibling containers. Never mount other users' directories. Set timeouts for tools.

Every task-executing resource/rename/annotation gate writes the canonical
`$CASE/trace-resources.config` overlay and appends it with `-c`. It enables raw
trace at that case's absolute trace.tsv path and explicitly sets
`trace.fields = 'task_id,hash,name,status,exit,cpus,memory,time'`.
These eight columns and numeric requested resources are mandatory; default
trace columns are insufficient. Compare memory bytes and requested time ms,
never duration/realtime, and fail missing/malformed/over-cap values. Preserve
separate tier/attempt/transport directive records, joined by task_id/hash/name;
do not assume a default attempt column. The overlay changes tracing only, not
requests. R10/R11 use five exec-body directive records as primary evidence.
Zero-task helper/entry cases need no trace file but require no-submission audits.

Each case directory begins with RUN.txt and retains command.txt, output.log,
exit-code.txt, normalized effective parameters, expected/observed TSV or JSON,
trace, `.nextflow.log`, work task scripts/wrappers, relevant outputs and hashes.
Record request walltime via task.time.toMillis(), not trace elapsed runtime.
Do not infer actual task memory/time from a config dump alone. State test case
counts separately from test functions; currently cc_asat has no collected suite.
Emit the contract's results.tsv schema and case-inventory.tsv with expected
cells before each phase, plus parameter-coverage.tsv before parameter checks;
include source, contract and future fixture hashes in
every RUN. Also create an absolute-path ARTIFACTS.txt. Missing images/tooling or
inaccessible artifacts are blocked gates, not successes.

## 9. Behavior changes, exclusions, integration and task order

Explicit cc_asat behavior changes requiring approval:

- Low changes from fixed 2 CPU/4GB/1h to 25% with 1 CPU/1GB/1h floors;
  medium changes from detected min(8 CPU,16GB)/4h to 50% with 2 CPU/2GB/4h floors;
  high changes from detected CPUs/memory and 12h to effective maxima including
  max_time (default 168h). E.g. 8 CPU/7GB/12h gives 2/1792MB/3h low and
  4/3584MB/6h medium. This is requested consistency work, not preservation of
  asat's historical requests.
- Unlabelled returns to maxima (candidate changed it to 1 CPU/4GB/1h);
  process_single becomes capped 1 CPU/2GB/1h (main had no selector).
- Explicit CPU/memory caps regain authority; invalid caps/flags now reject early.
  Version floor rises to 26.04.6; v2 CLI false becomes stable. Longer proportional time
  requests may change scheduling even when actual runtime is unchanged.
- Annotation-only needs a v2-compatible public route because -entry is rejected.
  The --workflow recommendation and separate-root alternative remain deferred,
  unapproved user choices. Preserve scientific behavior under whichever is chosen;
  retain the v1 legacy route only conditionally as described in section 2.
- Containerized Nextflow with socket access only for actual Docker-task gates is
  a narrow test-harness addition; parent must disclose this in the plan summary.
  No shared-daemon changes or host tests are authorized.

Non-goals: scientific/annotation/scaffolding redesign, optional-GFF support,
separate scaffolding-unplaced-fix integration, missing sentinel repairs, container
version harmonization, unrelated numeric-range hardening, retries/escalation in production, HPC/cgroup detection,
Slurm execution, IGV acceleration, new CI uploads/cache infrastructure, broad
unit-test framework or script algorithm tests. Preserve RESTORE_PATCH_SEQNAMES's
known container limitation as out of scope; do not claim a patch-arm Docker gate
passed when only annotation and rename were run.

Branch strategy after approval: cc_asat is main+one candidate commit; recheck
refs/status, but no integration merge is needed at the recorded SHAs. Keep its
branch and PR. Gcev is independently owned, 70 commits behind and conflicting;
its implementation must incorporate current main by a non-rewriting merge and
resolve from current-main proportional/scientific contracts, then reapply native
caps. Never accept the obsolete candidate config wholesale. No merge now. New
upstream changes require re-reading intersecting files and reviewing the new
base; branch protection and parent publication permissions still apply.

Serial within this repo:

1. Canonical document adoption is complete at the hash in section 3; vector JSON
   remains future build work. Resolve the user-deferred selector
   when the user elects to decide, finalize conditional allowlist/commands, then
   obtain independent full-plan review and user summary approval. No new question
   or wait for that choice is part of this plan-fix task.
2. Fresh implementer checks base/status/history and current plans; implements
   config, preflight and syntax first; tests 26.04.6 config/selected-route preview
   before expanding edits. Failure of the selected syntax at the selected floor
   is a blocking implementation issue, not license to silently change the matrix.
3. Wire Boolean options through workflows/modules; consume canonical fixtures;
   run bounded parser/resource gates and document results. Update README/examples.
4. Parent schedules Docker tool/integration gates serially across repositories.
   Gcev additionally needs its current unit/negative/read/Session-3 and relevant
   sequence-end/IGV gates with internally forced v1 removed or parameterized;
   that work and file set belong to its sibling plan, not this checkout.
5. Review exact final implementation SHA/snapshot independently. Only green,
   authorized feature commits; no push or PR mutation inferred from plan approval.
   Parent/designated owner updates existing PR description with scope/evidence.
   No task PR to main, merging to main, branch deletion or force-push.

Parallel split: sibling plans and independent reviews can proceed concurrently.
During approved implementation, independent asat plumbing can proceed while the
fresh gcev implementer authors the shared JSON once. Fixture adoption is serial:
parent supplies the completed immutable artifact/hash before asat copies it.
No independent fixture reconstruction or in-progress sibling read. This dispatch
starts no subagents and sends no cross-planner messages.
Config/options wiring shares files and stays serial. Heavy Docker gates stay
serial to avoid shared-host contention.

## 10. Risks and remaining decisions

- Requirement authority and canonical document adoption are resolved and hashed
  in sections 1/3. Only the finalized artifact was read/copied, without edits.
  Future JSON/test-result parity remains an implementation gate; the fresh
  implementer must receive this plan and the pinned contract together.
- Public selector choice is explicitly deferred by the user. Recommendation,
  alternative and conditional gates are concrete, but neither is approved.
  Independent planning revisions proceed without asking or waiting for a ruling.
- Early strict-parser limitations, dynamic resourceLimits evaluation, image/JAR
  availability and pinned-tool one-CPU behavior require the stated gates; none
  was tested during planning. Do not turn an environmental setup failure into a
  compatibility verdict.
- Read-only source audit finds no true mandatory multi-CPU tool; implicit tool
  pools still need bounded Docker confirmation. A demonstrated mandatory minimum
  needs actionable selected-path preflight before any task and parent review,
  never silent cap inflation. Source-only tool fallback is reported as unverified
  runtime coverage, not a pass.
- Practical floors cannot guarantee task success under arbitrarily tiny caps.
  Preserve honest scheduler/request versus runtime enforcement distinctions.
- Fresh implementation must preserve current asat input and scientific behavior;
  in particular, passing normalized options must not inadvertently implement the
  deferred optional-GFF plan or modify copies/iterative merge identity rules.

Review prompt for the parent: review the entire saved plan, both independent
reviews and round-three dispositions, dispatch and hashed requirements. Examine
the pinned byte-identical canonical
artifact and resolve only the public choice actually
approved by the user. Independently check current-main contracts, override timing,
command assumptions, floor, conditional allowlist and Docker/socket boundaries.
Report blockers, non-blockers and suggestions separately with line references.
Do not approve from this planner's summary or treat reviewer prototypes as
acceptance of future product code. Do not infer selector approval from this plan.
