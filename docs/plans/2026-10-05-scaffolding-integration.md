# Integrate scaffolding fixes into PR #4

Date: 2026-10-05. Status: proposed; independent Opus/high plan review, authorized
plan commit and user summary approval precede a fresh implementation session.
Planning changes only this document; no merge, product edits, commit or push.
Requested planner/implementer: gpt-6-astra / high. Actual native model/effort:
**unknown**; dispatch metadata is not native execution evidence. No substitution,
extra-usage fallback, nested agents or agmsg. Work is serial under qbk-polly.
This user-directed placement/naming revision starts from reviewed plan commit
`d5a4cf77cdf4894ce788fe052ff57422826e29d6` (plan SHA256
`e6cc7268b711df354544212639131a9de7ae5944f0da1c3c470af42cae518d1e`).
Earlier reviews cover those earlier bytes only; hold this revision uncommitted
for retained Opus review and revised user summary approval.

## Authority and boundaries

Worktree: `/home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature`.
Branch: `claude/ecstatic-thompson-w5cfoh`; existing PR:
<https://github.com/jonjoet/cc_asat/pull/4>.

| Role | Examined immutable SHA |
|---|---|
| Current worktree HEAD / prior plan commit | `d5a4cf77cdf4894ce788fe052ff57422826e29d6` |
| PR4 product base | `3d56a4513734d9dd41ddc80b31d7055e5232dbef` |
| Source, `origin/scaffolding-unplaced-fix` | `8f454f9abb667204f8360f09a0a4f4e8774ebd1b` |
| Common ancestor/main | `5db41dcf4e0416602af8188ef1d8686bf88200e1` |

Read these with this plan in a fresh session:

- `CLAUDE.md`, `/home/qbk/qbk-code/CLAUDE.md`, and the dispatch's host rules.
- `docs/plans/2026-10-04-parser-v2-resources.md` and
  `docs/plans/2026-10-04-resource-contract.md` (contract SHA256
  `2a00165b10f57ba9812aac12debb47abb35c2c716b10d48858ad4b3c194ff398`).
- At the source SHA, `claude_context/2026-06-12-scaffolding-unplaced-fix-plan.md`
  and `claude_context/cc_asat-scaffolding-unplaced-fix-brief.md`, read in full
  during this investigation. Source implementation supersedes its older code
  snippets. This dispatch supersedes its obsolete host paths, subagent, commit
  and resume instructions. The prior parser plan's deferral of this integration
  is lifted by the present authorization; its resource/scientific contracts stand.
- Original integration requirement record:
  `/home/qbk/qbk-code/tmp/cc_asat/scaffolding-integration-20261005T173525Z/REQUIREMENTS.txt`.
- **Superseding user decisions**, read in full:
  `/home/qbk/qbk-code/tmp/cc_asat/scaffolding-integration-20261005T173525Z/placement-plan-revision/REQUIREMENTS.txt`
  (SHA256 `eaec4664a3af7aa8739fa5055659d6f2efd3712ac901351eeedd18dfd2633832`).
  These replace the old name-based placement rule and repeat-renaming/fixed-point
  requirement, including conflicting source plans and prior approval summaries.
- Pinned source investigation and provenance:
  `/home/qbk/qbk-code/tmp/cc_gcev/ragtag-placement-investigation-20261005T193050Z/{REPORT.md,RUN.txt}`.
  The report and saved sources are source evidence, not runtime acceptance.
  The contracts below are self-contained; no prior transcript is needed.

Deliver **all intended features of all nine source commits**, preserving ancestry
through an ordinary merge. Keep Nextflow `!>=26.04.6`, v2 explicit/unset primary,
focused v1 compatibility, `--workflow full` (default),
`--workflow annotation_transfer_only`, and v1 legacy annotation `-entry` precedence.
Preserve normalized Boolean options and capped 25/50/100% tiers, including single,
unlabelled and one-CPU behavior. Do not change shared contract/vector bytes.

Non-goals: GCEV edits, deferred quantity grammar (jonjoet/cc_gcev #16), shared
skills (cx_helpers #1), optional-GFF implementation, annotation algorithms,
new RagTag options/version, `-C`, splitting unplaced FASTA, meta-map/nf-core
conversion, tool upgrades, broad input validation, CI changes, whole-repo audit.
The existing patch-restoration module's missing container remains a disclosed
limitation; this plan does not authorize its repair or claim patch-arm runtime
acceptance. No main merge/push, PR closure, branch deletion or history rewriting.

## Investigation findings and selected behavior

The nine source commits are `56c09ca`, `77512e4`, `57ef03d`, `30fcd89`,
`5c5381d`, `6bdcb79`, `527c8fc`, `6ccf4b4`, `8f454f9`. Their 13-file diff adds
the renamer/pattern, AGP classifier/module/publication, removes dead outputs,
rewires scaffolding, and supplies docs including both chromosome-pattern examples.
Parent's legacy merge-tree preview found no markers and overlap in README,
nextflow.config and the full workflow. This is **not semantic validation**.

Bounded static findings (line references belong to the indicated SHA):

| Finding | Required disposition |
|---|---|
| Source `bin/rename_ragtag_scaffolds.py:23–46`: pattern runs before prefix-if-missing; only tests `lastindex` after a match; output opens immediately; no duplicate-ID check. Regexes can have zero/multiple groups, unmatched optional groups or colliding outputs. | Preserve source naming order. Validate one capture group before output, nonempty captured ID on each match and unique final IDs. Fail clearly without truncating input or publishing partial output. No second-pass validation. |
| Source rename module `:15–16` escapes apostrophes, but truthiness silently treats false/zero/empty like absence; separate-token forwarding fails for leading-hyphen patterns. | Accept null or a nonempty string; put this type/empty check in `RENAME_RAGTAG_SCAFFOLDS`'s `script:` block, before constructing the command. Forward one shell-quoted `--chr-pattern=<pattern>` token; helper validates Python regex semantics. No Java regex validator, entry/preflight edits or annotation-only behavior change. |
| Source classifier `:29–56` infers placement from object/component names, misclassifying same-name placed singletons; its FAI warning (`:118–123`) cannot disambiguate same-name unplaced queries. | Replace that decision with mandatory same-task confidence query-ID membership. Remove FAI input/cross-check and all name-based fallbacks. Retain narrow malformed-AGP rejection: skip blank/comments, reject fewer than five fields, validate W/N/U rows/coordinates, ignore other component types. |
| Source design says pattern matching alone selects renames. Its README says “placed scaffolds,” which can imply an absent classifier gate. | Document that any matching header, including an unplaced one, can change. Default and unmatched IDs preserve original tokens. No new classifier-to-renamer coupling. |
| Base `tests/parser_resources/rename.nf:9–10` and `assert_results.py:741–763` supply/expect the removed separate unplaced FASTA. Static audit at `:279` expects 17 modules; trace tier assignment at `:732` omits classifier/RagTag. | Repair these tests, expect 18 modules with explicit new membership, and classify actual process tiers correctly. Do not loosen assertions to make integration pass. |
| Base `tests/parser_resources/run.sh:39–45` extracts a JAR per phase and restricts evidence to the GCEV tmp root (`:17`). | Narrow runner maintenance: reuse immutable distribution read-only, support ASAT evidence root, isolate writable state. No shared engine edits. |

Naming contract: first whitespace-delimited FASTA sequence ID remains the identity
(description stripping is existing behavior). Remove the one RagTag-added terminal
`_RagTag`, preserve internal underscores, prefix `<sample>_` once. Default examples:
`contig_3 → S_contig_3`, `2micron_plasmid → S_2micron_plasmid`,
`LEXst001_ChrI → S_LEXst001_ChrI`. Optional Python search regex with exactly one
group produces `<sample>_<group1>`; examples `_(Chr[IVXLCDM]+)$` and
`_(Chr[0-9IVXLCDM]*)$` retain the source's Roman/bacterial behavior. Preserve source
order: suffix removal, pattern substitution on match, otherwise prefix-if-missing.
Thus sample `S288C`, reference `S288C_R64_ChrI` and the Roman pattern still produce
`S288C_ChrI`. This is a single rename of RagTag output, not a promise about applying
the helper again. For original `contig_7_RagTag`, RagTag emits
`contig_7_RagTag_RagTag`; sample `S` must produce `S_contig_7_RagTag` successfully
when unique. Strip exactly the added suffix, preserving the original suffix;
never reject a valid result because of a hypothetical second pass.
Reject duplicate input IDs and convergent output IDs (including `x` versus `S_x`,
or distinct strain names both mapping to `S_ChrI`), identifying the conflicting
original and proposed IDs. Validate before replacing output; reject input/output
aliasing, preserving the input and any pre-existing output on failure. Keep this
direct-CLI-only protection minimal: a path/same-file check and validate-before-write;
no new general filesystem safety framework. Keep
sequences, order, count and per-record length unchanged. Stdlib only.

Classifier contract: use the unchanged AGP and mandatory
`ragtag.scaffold.confidence.txt` from the **same successful RagTag 2.1.0 scaffold
task**, with `-u`, no `-C`. Upstream commit
`e993fb2787346345662c240967a3ec80bb2aac64` is pinned by the investigation.
Its `ragtag_scaffold.py:78–115,194–219` emits confidence rows only for final placed
queries; `ragtag_stats.py:57–78` consumes that membership as placement authority.
For each AGP **W** row in file order, its raw column-6 query ID is unplaced iff
absent from the confidence `query` column. Do not strip suffixes from query IDs,
compare object/reference/renamed IDs, reapply score thresholds or run extra alignments.
N/U gap rows never emit a TSV row. Keep TSV header exactly
`contig_id\tobject_name\tlength_bp`; output raw AGP column 6, raw column 1 and
column 3 minus column 2 plus 1, in AGP W-row order. Inputs remain read-only.

README and approval summary must explain that with `--run_correct`, these raw
query IDs are correction-output IDs, not necessarily the user's input IDs.
Existing `RAGTAG_CORRECT -u` can add coordinate/orientation suffixes: an unplaced
`contig_7_1_48000_+` remains that TSV ID and, with default naming/sample `S`, becomes
`S_contig_7_1_48000_+` in FASTA. Remove only the scaffold-added terminal `_RagTag`;
do not strip correction suffixes or add a mapping policy. The selected naming rule
and required `contig_7_RagTag_RagTag → S_contig_7_RagTag` example remain unchanged.

Confidence has exact header
`query\tgrouping_confidence\tlocation_confidence\torientation_confidence`.
Use the investigation's minimal integrity checks: four fields per nonblank data
row, unique nonempty query IDs, parseable finite scores and confidence IDs present
among AGP W components. Missing/malformed/inconsistent confidence fails clearly
before writing output; never substitute a naming rule. No score cutoff/range
policy or general AGP validator is introduced. Empty/comment-only AGP with a
valid header-only confidence file and all-placed inputs yield a mandatory
header-only TSV. Header-only confidence is different from a missing/zero-byte file.
Synthetic empty/all-unplaced helper fixtures are not evidence that RagTag completes
an all-failed-placement run: the pinned CLI can fail before emitting these files.

Both same-name cases must work: `chr1_RagTag … W chr1 …` is placed when confidence
contains `chr1`, and genuinely unplaced when it does not, even when reference
contains `chr1`. The latter successful-run fixture also places another query on
another reference; no reference-name warning or override remains. The old false-
unplaced limitation is superseded. Remaining limits: membership records RagTag's
decision, not biological correctness or an unplaced reason. A truncated but
well-formed confidence file can remove a row undetectably; matching filenames alone
do not prove provenance. Wire both mandatory outputs directly from the same task,
never accept an external/stale file. Distinct queries causing duplicate RagTag
object names can still fail upstream; this classifier does not repair failed runs.

The approval summary and README must also enumerate the proposed hard failures:
invalid pattern syntax/group count or capture, duplicate/convergent IDs, and YAML pattern
`false`/`0`/`''`/`{}`. Use null to disable the pattern; false is no longer “off.”
Pattern errors surface at the rename task, after RagTag/correction may have run,
not entry preflight. After correcting inputs/parameters, users may use `-resume`
with the retained work directory. Also document malformed relevant AGP rows,
missing/malformed/inconsistent mandatory confidence, and the helper's direct-CLI
input/output-alias rejection. Preserve all these validations and validate-before-
write; remove only repeat-renaming/fixed-point checks. Document the successful
original-suffix example above. Implementation still awaits revised summary approval.

Publish `{sample}_unplaced_contigs.tsv` to both `scaffold/` and `final_outputs/`.
It describes the scaffolding stage, before gap filling/reorientation; it is not a
final-coordinate map. Keep every unplaced sequence in the main scaffold channel
for gap closing, patching, DNAAPLER, wrapping, QUAST and annotation. Compare
renamed FASTA record count/length/sequences to **RagTag output**, not input contig
count (placed contigs can join and gain gaps). Document how raw TSV object IDs map
through the selected rename rule to FASTA IDs; GFF seqids must match final FASTA.
Remove only the obsolete `NO_FILE`/unplaced-output plumbing; do not delete unrelated
`NO_READS`/`NO_GFF` sentinels or old user results on disk.

## Integration sequence and concrete file changes

After independent plan review, authorized plan commit, user summary approval and
fresh build dispatch: check branch, status, recent history and reread applicable
plans immediately before edits. Beyond current HEAD, only authorized plan-revision
commits should initially exist. Stop for unexplained product delta/source movement.
In the assigned feature worktree, use the pinned source SHA:

```bash
cd /home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature
git status --short
git log --oneline -6
git merge-base HEAD 8f454f9abb667204f8360f09a0a4f4e8774ebd1b
git merge --no-ff --no-commit 8f454f9abb667204f8360f09a0a4f4e8774ebd1b
git diff --cached --stat
git diff --check
```

Keep merge pending while reconciling/testing; commit only the green authorized
snapshot with both parents intact. Resolve any textual overlap from combined
contracts, never wholesale “ours/theirs.” Preserve PR4's normalized `options`
branches, resource closures and selector. Expose mandatory confidence alongside
AGP from `RAGTAG_SCAFFOLD`; call `CLASSIFY_UNPLACED` with those two outputs from
that invocation. Pairing relies on the current single scaffold task per run with
value-channel inputs. Future multi-sample fan-out would require paired output
tuples; do not implement that future work here.
Remove the source branch's newly added `reference_fai` take/input
and FAI arguments at both SCAFFOLDING call sites (including `.first()`). Keep the
existing reference-index step otherwise unchanged; no FAI placement authority.
Review staged
**and unstaged** changes against both parents. A second compatibility commit is
acceptable if parent directs it; no cherry-pick/squash/rebase replaces the merge.

Future build file set (not current planning write permission):

| Files | Implementation |
|---|---|
| `bin/rename_ragtag_scaffolds.py` | Merge source naming order; retain regex, duplicate-ID, alias and validate-before-write safeguards. Single-pass suffix preservation; remove only second-pass/fixed-point checks. Keep both source assertions labelled "idempotent": they test already-prefixed IDs and retained prefix-if-missing behavior. |
| `bin/classify_unplaced_contigs.py` | Replace name/FAI heuristic with AGP W versus confidence query membership; require `--confidence`, remove `--fai`; retain narrow AGP validation and add the minimal confidence checks above. Self-tests cover both same-name statuses and empty outcomes. |
| `modules/local/rename_ragtag_scaffolds/main.nf` | One FASTA input/output; type/empty check in `script:` and shell-quoted equals-form pattern forwarding. Keep `process_single`. |
| `modules/local/classify_unplaced/main.nf` | AGP + mandatory confidence inputs, pass `--agp`/`--confidence`, mandatory TSV output, `process_single`, source Python image. |
| `modules/local/ragtag/scaffold/main.nf` | Remove nonexistent unplaced emit; add nonoptional `path "ragtag_out/ragtag.scaffold.confidence.txt", emit: confidence`. Preserve `-u`, no `-C`, pinned tool and `-t ${task.cpus}`. |
| `subworkflows/local/scaffolding.nf` | Route same RAGTAG_SCAFFOLD invocation's AGP/confidence to classifier; no FAI argument. Classify alongside rename, emit `unplaced_list`, remove dead sentinel/input/output. |
| `workflows/euk_scaffold_validation.nf` | Retain original four-argument SCAFFOLDING calls in both correction branches; remove source's FAI-only additions. Keep index step, options map, single downstream FASTA, annotation routing and reorientation. |
| `nextflow.config`, `conf/modules.config` | Add null pattern default and two TSV publish routes; existing RagTag scaffold publish rule also publishes newly emitted confidence under scaffold/. No additional final_outputs confidence copy. Preserve resource/engine/profile policy. |
| `README.md`, `assets/params.example.yaml`, `tests/README.md` | Combined interface; single-pass naming and original-suffix example, opt-in patterns/quoting; mandatory same-task confidence authority, both same-name outcomes, raw TSV schema/stage/publication, correction-output IDs/suffixes and remaining limits/hard failures above. Remove old name-heuristic warning and repeat-renaming guarantees. No separate unplaced FASTA; annotation-only unaffected; parser/cap promises and exact bounded gates. YAML includes null plus commented Roman/bacterial patterns. |
| Three source `claude_context/` documents | Bring in intact through merge; historical context, not active execution instructions. Where README links them, add one line: "The placement rule in these historical documents is superseded by mandatory same-task confidence query-ID membership." No historical-document rewrite, modernization or backlog cleanup. |
| `tests/parser_resources/rename.nf`, `tests/fixtures/parser_resources/ragtag_scaffold.fasta`, `tests/fixtures/parser_resources/ragtag_unplaced.fasta` | One combined rename fixture with unplaced record; remove obsolete separate fixture and its assertions. Keep unrelated fixtures unchanged. |
| `tests/parser_resources/run.sh`, `tests/parser_resources/assert_results.py` | Shared-JAR read-only mount, ASAT evidence root, focused modes below, exact module count/tier checks and new naming/publication assertions. Preserve existing modes and full matrices as optional regression tools. |
| New `tests/scaffolding/helpers.py`, `tests/scaffolding/modules.nf` | Stdlib assertions/fixture generator and small real-module/subworkflow harness. Reuse existing driver/trace machinery; no new framework. Generate inputs in evidence, never checkout. |

`main.nf`, `utils/params.nf`, shared vectors/contract and unrelated production
modules require no edits. If an actual downstream defect demands extending this
set, report exact evidence and scope to parent before expanding.

Serial tasks: (1) merge/reconcile; (2) helpers and fixtures; (3) module wiring,
harness compatibility and docs; (4) gates; (5) independent final Opus/high review
and publication handoff. Parallel split: none dispatched. Helper assertions and
documentation are conceptually independent after behavior is fixed, but one worker
owns all writes; all Docker gates run serially. Keep the new independent reviewer
through final integration review; no implementation self-signoff.

## Executable acceptance gates

Commands below are the **future implemented runner interface**, not tests already
run. Extend the listed test files to implement it. Host shell/Git/Docker orchestration
only; every Nextflow/Python/product invocation runs in Docker. No host installs.

### Evidence, runtime and disk setup

82 GiB free was observed during planning. Budget at most **10 GiB additional** for
this bounded gate set; check `df`/`du` before each phase, stop for review if below
20 GiB free or above budget. Do not prune images/evidence. Relevant pinned tool
images and Python/Nextflow images were present; re-inspect before use. No large
downloads or full biological/resource/Boolean matrix to resolve fixture failures.

Use the existing 42,337,859-byte 26.04.6 JAR, SHA256
`2ca0251ae2d749317d9fbe5fe191a1616b5f44b608224268924c71b32f5ed9e2`.
Its provenance is the adjacent `RUN.txt` and `jar.sha256` below; this is tooling
reuse, not reuse of an old product test result. It has 1,591 hard links: **never
chmod, overwrite or extract into it**. Bind its distribution read-only; do not
copy it per phase/invocation. If missing/hash mismatch, stop and obtain a verified
immutable cache location from parent. Do not silently download another engine.

```bash
set -euo pipefail
repo=/home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature
evidence=/home/qbk/qbk-code/tmp/cc_asat/scaffolding-build-$(date -u +%Y%m%dT%H%M%SZ)
export CC_GCEV_RUN_BASE="$evidence"  # retain runner variable; allow ASAT root too
export CC_ASAT_NXF_DIST=/home/qbk/qbk-code/tmp/cc_gcev/parser-v2-build-20261005T013953Z/review-asat-3d56a45/static-26.04.6-v2/framework
test ! -e "$evidence"
mkdir -p "$evidence"
printf 'commit: %s   dirty: %s\nstarted: %s\npurpose: scaffolding integration acceptance\n' \
  "$(git -C "$repo" rev-parse HEAD)" \
  "$(test -z "$(git -C "$repo" status --porcelain)" && echo no || echo yes)" \
  "$(date -u +%FT%TZ)" > "$evidence/RUN.txt"
git -C "$repo" status --porcelain=v1 > "$evidence/status.txt"
git -C "$repo" diff --binary HEAD > "$evidence/source.diff"
git -C "$repo" ls-files --others --exclude-standard -z > "$evidence/untracked.list"
tar -C "$repo" --null -T "$evidence/untracked.list" -cf "$evidence/newfiles.tar"
sha256sum "$evidence/source.diff" "$evidence/newfiles.tar" >> "$evidence/RUN.txt"
git -C "$repo" rev-parse -q --verify MERGE_HEAD >> "$evidence/RUN.txt" \
  || printf 'MERGE_HEAD: none (committed-tree rerun)\n' >> "$evidence/RUN.txt"
df -h "$evidence" > "$evidence/disk-before.txt"
sha256sum "$CC_ASAT_NXF_DIST/26.04.6/nextflow-26.04.6-one.jar" > "$evidence/jar.sha256"
docker image inspect nextflow/nextflow:26.04.6 python:3.12 > "$evidence/images.json"
```

Runner must verify JAR hash and Nextflow image ID
`sha256:83bbf3dd9e84ecd4d53a86620d08fe0259bca00a8f59f6f31664eb90033f460f`,
mount `-v "$CC_ASAT_NXF_DIST:$CC_ASAT_NXF_DIST:ro"`, set
`NXF_DIST=$CC_ASAT_NXF_DIST`, `NXF_VER=26.04.6`, `NXF_OFFLINE=true`,
`NXF_DISABLE_CHECK_LATEST=true`,
and record actual `nextflow -version`. Record each tool's immutable image ID.
Keep HOME/NXF_HOME/NXF_CACHE_DIR/NXF_TEMP/TMPDIR/cwd/work/output per case under
evidence, source read-only and bytecode disabled. Unset parser means absent env
variable. Existing launcher shape remains Docker `--user uid:gid --cpus 4
--memory 4g`, `NXF_OPTS=-Xmx768m`. No socket for lint/config/previews/resource
echoes; socket plus its group and identical absolute mounts only for real task
modes. Tasks use normal module images, uid/gid, explicit bin bind/PATH, queueSize
and maxForks 1. No source writes, anonymous unrecorded caches or host-tool fallback.

### Commands and required observations

First, helpers (120-second bound, Python image resolved by immutable ID):

```bash
mkdir "$evidence/helpers"
cp "$evidence/RUN.txt" "$evidence/helpers/RUN.txt"
py_image=$(docker image inspect --format '{{.Id}}' python:3.12)
cmd=(docker run --rm --network none --cpus 1 --memory 512m
  --user "$(id -u):$(id -g)" -e PYTHONDONTWRITEBYTECODE=1
  -e HOME="$evidence/helpers" -e TMPDIR="$evidence/helpers"
  -v "$repo:$repo:ro" -v "$evidence:$evidence" -w "$evidence/helpers"
  "$py_image" python3 "$repo/tests/scaffolding/helpers.py"
  --repo "$repo" --evidence "$evidence/helpers")
printf '%q ' "${cmd[@]}" > "$evidence/helpers/command.txt"
set +e
timeout 120 "${cmd[@]}" > "$evidence/helpers/output.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$evidence/helpers/exit-code.txt"
test "$code" = 0

for mode in static integration-resources scaffolding-preview scaffolding-modules docker-rename scaffolding-smoke; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" \
    --mode "$mode" --engine 26.04.6 --parser v2 --interface selector
done
for mode in integration-resources scaffolding-preview scaffolding-modules legacy-entry; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" \
    --mode "$mode" --engine 26.04.6 --parser v1 --interface selector
done
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" \
  --mode scaffolding-preview --engine 26.04.6 --parser unset --interface selector
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" \
  --mode annotation-smoke --engine 26.04.6 --parser v2 --interface selector
git -C "$repo" diff --check
```

Each mode records a case inventory **before** execution. Bound each Nextflow
invocation to 600 seconds (full smoke at most 1,200 seconds per run); terminate
and record timed-out launcher/task containers without deleting work/output.
No retry loop, OOM fallback or auto-expanding test matrix. Record actual case/assertion/task
counts separately: these stdlib drivers have no pytest-collected test functions.

| Gate / implemented mode | Exact bounded coverage and pass criteria |
|---|---|
| `helpers.py` | Run both script self-tests and CLI assertions: default underscores/plasmid/accession, RagTag suffix, already-prefixed ID and successful `contig_7_RagTag_RagTag → S_contig_7_RagTag`; Roman/bacterial/custom pattern, source-order `S288C_R64_ChrI → S288C_ChrI`, no-match, quoted apostrophe/backslash and leading-hyphen `-(Chr[IVX]+)$` via equals-form argv; invalid syntax, zero/multiple groups (even no-match), unmatched/empty capture, duplicate/convergent IDs and aliased input/output. Failures nonzero with specific diagnostics and unchanged input/pre-existing output. Compare sequence/order/length exactly; no partial output or second-pass checks. AGP: multi-W+N, multi-W+U, placed single, multiple unplaced/order, all-placed, empty/comments, all-unplaced with header-only confidence, and both same-name placed/unplaced cases. Assert raw query-ID membership even for IDs ending `_RagTag`; malformed W/N/U/coordinates and fewer-than-five-field noncomment rows fail; other types ignored. Confidence: missing/zero-byte, wrong header/field count, duplicate/empty query, nonnumeric/nonfinite scores and query absent from W components fail before writing. Exact TSV bytes and unchanged AGP/confidence hashes. Fixtures and expected literals saved, not derived using production functions. |
| `static` | `nextflow lint <repo>` under strict v2, no formatting, zero errors; preserve warnings. Explicit inventory of 18 production modules, both helper modules single-labelled; scan active code/tests for obsolete unplaced emits/input/NO_FILE (historical docs excluded). Source audit preserves resource closures/floor/options and no new thread overrides. |
| `integration-resources` v2/v1 | Two config dumps (`docker`, `test,docker`); reuse existing canonical driver methods for R02 through CLI, R03 through YAML and L02 aliased-limit override, not the whole contract mode. Five tiers for each resource case, exact fixture triples; alias oversized requests clamp correctly. This is three resource startups per parser, plus configs/version, with no biological tasks. Preserve shared vector hash `32a1105d46420837bb1fbe148c9b4e5d095213f5d2a2856c43ba09448d83a8ab`. |
| `scaffolding-preview` v2/v1/unset | Five actual-entry previews: full default/no correction, full with reads+run_correct=true, full bacterial auto-reorientation, annotation-only without organism, invalid selector. Valid route inputs; require expected process membership, both full branches wire scaffold AGP/confidence to classifier alongside rename, annotation has none of those scaffolding processes, invalid selector rejects before submission. All zero tasks. Assert absence of the engine warning containing "The operator `first` is useless when applied to a value channel" in output/logs of full-route previews and both smoke runs. Supply custom pattern via YAML in one full case and CLI in another; explicit CLI `--reorient_assembly false` excludes DNAAPLER in the default full case. Retain exact selector error checks. Previews do not evaluate module script blocks or prove task pattern transport/provenance. |
| `scaffolding-modules` | Four v2 cases using real modules: mixed AGP/confidence/FASTA at R02 (`1/512 MB/30min`), mixed with a quoted leading-hyphen pattern via **YAML** at R03 (`8/7 GB/12h`), all-placed/header-only TSV at R02, and real `SCAFFOLDING` with correction enabled at `1/4 GB/1h`. v1 repeats only the first case. First three call real rename/classify together; each must execute once, inherit single resources, publish exact TSV to both destinations and retain all FASTA records. R03 single expected `[1,2147483648,3600000]`; R02 `[1,536870912,1800000]`. Correction case uses the renamed query below, expects an exact header-only TSV in both publications, verifies mandatory same-task AGP/confidence and command observables below, and checks real correct/scaffold/rename/classifier completion with `-t 1`; no gap closing or FAI classifier argument. |
| Pattern transport negatives, in `scaffolding-modules` v2 only | Four additional rename-only cases supply YAML `false`, `0`, `''` and `{}` at R02. Require nonzero exit with a named scaffold_rename_pattern type/empty diagnostic and no renamed/published FASTA. These are expected rejections, separate from successful task/resource counts. |
| `docker-rename` v2 | Execute the repaired existing one-task harness and exact combined-FASTA assertions, including bin bind/PATH, absence of a separate unplaced FASTA and R02 trace/wrapper requests. |
| `scaffolding-smoke` v2 | Two actual full runs, named FULL-DEFAULT (fungal/default rename/reorientation false; same-name placed query) and FULL-PATTERN (bacterial/Roman regex/auto reorientation true; same-name unplaced query), recipe below. No stubs. Require scaffold/classifier/rename, final wrapping, reference and vendor annotation, iterative merge and QUAST completion; second also DNAAPLER. Assert confidence membership and same-task provenance; exactly one unplaced TSV row in each publication, retained plasmid sequence and expected final IDs, gene features on chromosome and plasmid whose seqids all exist in final FASTA. No nonexistent output/sentinel, duplicate ID or lost contig. |
| `annotation-smoke`, `legacy-entry` | Existing real annotation-only v2 gate and its five filter/merge command cases, plus existing six v1 legacy previews unchanged. Assert no scaffolding/classifier or unplaced TSV in annotation-only output; input identifiers remain unchanged when reorientation is false. |

Generate deterministic smoke inputs under the evidence case, using the existing
30 kb parser fixture chromosome sequence and gene. Rename its reference header/GFF
seqid to `strain_ChrI`. FULL-DEFAULT also uses query header `strain_ChrI`: assert
this same-name placed query is in confidence and absent from the TSV.
FULL-PATTERN uses query header `contig_3`. Add an unrelated 6 kb
`2micron_plasmid` query sequence using the documented LCG/codon recipe in tests
README with seed 20261006; insert its own distinct 897 bp coding sequence at
offset 1000 and vendor gene/mRNA/exon/CDS at 1001–1897. FULL-DEFAULT reference has
no plasmid. FULL-PATTERN reference additionally contains a different unrelated
6 kb sequence named `2micron_plasmid` (same LCG recipe, seed 20261007): assert the
query plasmid remains genuinely unplaced despite its reference-matching name,
absent from confidence and present in the TSV; `contig_3` is placed. This adds no
run or alignment job. Both expect the single literal TSV row
`2micron_plasmid\t2micron_plasmid_RagTag\t6000` after the header. Save generator
inputs, exact FASTA/GFF and hashes. For correction's
module case, copy existing reference/assembly/reads to evidence; retain reference
`chr1` and rename only the assembly header to `contig_3` (same 30 kb sequence).
Expect exactly `contig_id\tobject_name\tlength_bp\n` in both published TSVs.
Require confidence to contain exactly `contig_3_1_30000_+`, the ID RagTag correct
assigns under `-u`. In this case and both full smokes,
match the classifier's staged AGP/confidence hashes to the mandatory files from
the same completed RAGTAG_SCAFFOLD task and preserve its task ID/work path.
For the planned default Docker staging, also record `readlink -f` of both staged
symlinks and require resolution to the corresponding emitted files inside that
recorded scaffold task work directory; matching hashes alone are insufficient.
Inspect
`.command.sh` for those staged filenames passed to `--agp` and `--confidence`,
with no `--fai`. Verify scaffold/ also publishes that confidence file unchanged.
These are wiring observables, not a claim of biological correction quality.
In existing module
case 2, use pattern `-(Chr[IVX]+)'$` via YAML and header `strain-ChrI'_RagTag`:
expect `fixture_ChrI`, proving leading-hyphen/apostrophe transport in the same task.
Handwritten module fixtures also cover N/U gaps; no extra transport matrix.

The driver's full-run argv, with absolute case fixture paths substituted, is:

```bash
nextflow -c "$CASE/docker.config" -c "$CASE/trace-resources.config" \
  run "$repo/main.nf" -profile docker -cache false -work-dir "$CASE/work" \
  --workflow full --assembly "$CASE/inputs/assembly.fasta" \
  --reference "$CASE/inputs/reference.fasta" \
  --reference_gff "$CASE/inputs/reference.gff3" \
  --vendor_gff "$CASE/inputs/vendor.gff3" --sample_name fixture \
  --organism_type fungal --reorient_assembly false \
  --run_correct false --fill_gaps_from_ref false --liftoff_copies false \
  --fix_reference_gff false --fix_vendor_gff false --fix_generic_names false \
  --merge_novel_only true --max_cpus 1 --max_memory '4 GB' --max_time 1h \
  --outdir "$CASE/results"
```

FULL-PATTERN changes organism to bacterial, **omits** reorient_assembly to exercise
auto, and supplies `--scaffold_rename_pattern='_(Chr[IVXLCDM]+)$'` via **CLI**
to the actual task (module case 2 supplies YAML). No reads: gap closing
is intentionally not run. Expected default chromosome/plasmid IDs are
`fixture_strain_ChrI`/`fixture_2micron_plasmid`; pattern chromosome is `fixture_ChrI`.
Check per-record sequence identity against RagTag before renaming, then final
identity allowing only DNAAPLER rotation/reverse-complement where enabled.
Inspect actual staged DNAAPLER input for the plasmid and actual output, not merely
directory existence. A miniature marker/no-output failure is a **blocked bacterial
gate**, not a pass; investigate within the bound, then ask parent before larger
fixtures or product changes. Do not silently disable this accepted source gate.

**N12: the earlier optional OOM retry is unavailable** because its task-container
correlation condition cannot be satisfied in practice. On OOM or suspected OOM,
stop and report the blocked gate with preserved logs/trace/task commands; exit 137
alone is not proof of OOM. No speculative retry, higher-cap run, resume, admission
override or product edit. Retain the original 1,200-second bound, 4 GB requested
cap, launcher `--memory 4g`, combined 10 GiB disk budget and 20 GiB free-space floor.
Do not add correlation probes or privileged kernel access to repair this fallback.

All successful actual task cases save raw trace with
`task_id,hash,name,status,exit,cpus,memory,time`; require COMPLETED/exit 0, exact
tier values and every dimension <= effective cap. Save `.command.sh`/`.command.run`
and verify Docker memory/CPU-share flags and applicable worker arguments. CPU
shares are not a hard CPU quota. Small resource echo probes stay inside the
no-socket launcher; do not apply metadata admission overrides to real tools.

No old runtime artifact is claimed as acceptance of this new snapshot. Bounded
coverage is justified by keeping `utils/params.nf`, dispatcher, resource closures,
contract and vector bytes unchanged (audit the base-to-final diff); this is not
permission to call previous-tree gates “passed” on the merge. If those mechanisms
change unexpectedly, reconcile scope and select the affected prior-plan gates.
Only exact-snapshot evidence with matching RUN/diff/untracked hashes may be reused;
doc-only commit binding requires comparing the tested product tree explicitly.
PR text must distinguish the prior selector/Boolean matrices verified for
`3d56a45` from the bounded gates actually executed on the merged snapshot, citing
their respective evidence. Reviewer's source-helper/engine probes and older dirty
tool runs are investigation only, not merged-tree acceptance or planner execution.

## Review, publication and handoff

Planning evidence directory:
`/home/qbk/qbk-code/tmp/cc_asat/scaffolding-integration-20261005T173525Z/planner/`.
It contains RUN.txt first, history/source investigation, disk/JAR observations,
authority hashes, plan snapshot/hash, document checks and final status. Planning
ran only source/document/static inspection; no Docker product tests or merge.
Revision evidence is in sibling `planner-revision-1/` (RUN.txt first, before/after
plan snapshots, targeted diff, hashes, dispositions and document-only checks).
The narrow second revision uses sibling `planner-revision-2/` with the same records.
This superseding user-directed revision uses
`/home/qbk/qbk-code/tmp/cc_asat/scaffolding-integration-20261005T173525Z/placement-plan-revision/planner/`
with RUN.txt, before/after plan snapshots, exact diff/hash, reference/status and
document checks. Its pinned RagTag source investigation is not runtime validation.
The focused B4/N13–N17 fix is recorded in sibling `planner-fix-b4/`. It inspected
`review/REVIEW.md` and `review/reviewer-probe-ragtag-placement/{RUN.txt,output.log,command.txt}`;
the reviewer's pinned-container probe establishes the correction-ID expectation,
not merged-product acceptance or planner runtime execution.

Future gate handoff must list absolute paths to `$evidence/RUN.txt`, source diff,
untracked archive, image/JAR metadata, `helpers/{command.txt,output.log,exit-code.txt}`,
every `<mode>-26.04.6-<parser>/{RUN.txt,command.txt,output.log,exit-code.txt,
case-inventory.tsv,results.tsv}`, per-case trace/work/outputs, and `ARTIFACTS.txt`.
Record disk consumption and before/after source equality. Preserve unsuccessful
attempts. Missing/inaccessible evidence blocks review; expected cases cannot vanish
from inventory. After the eventual merge commit, prove both base and source SHAs
are ancestors with `git merge-base --is-ancestor`, retain `git show --format=raw`
for its two parents, and bind tested snapshot to the committed tree.

Reviewer prompt: “Read this full plan and both requirement records, giving the
placement-plan-revision user decisions precedence. Check all nine source
commits' intended behavior, merge ancestry, parser/resource/selector preservation,
mandatory same-task confidence membership of raw query IDs, both same-name
regressions, single-pass original-suffix preservation and retained helper failure
semantics. Check raw-versus-final naming, bounded Docker gates, N12 stop/report
and disk rules. Review the exact plan hash, then the exact final integration SHA/snapshot;
report blockers, non-blockers and suggestions separately with file:line evidence.
Do not infer semantic validity from a conflict-free merge or prior approvals.”

Open procedural decisions: independent Opus/high review, authorized reviewed-plan
commit and revised user summary approval. Confidence membership, single-pass naming
and keeping unplaced sequences in the main FASTA are settled user decisions.
The summary must disclose correction-output IDs/suffixes under `--run_correct`,
the remaining provenance/upstream-failure limitations, new hard failures and
unavailable OOM retry; do not carry forward the superseded
equal-name classifier limitation or fixed-point rejection. Implementation risks
are confidence provenance/integrity, upstream duplicate object names, shell
interpolation, channel starvation, actual DNAAPLER output and immutable-cache
availability. Runtime feasibility of the bounded fixtures remains to be tested.
Report unexpected substantial scope before expanding. No permission to fix unrelated
scientific behavior is implied by “all intended features.”

After green gates and final independent review, the designated feature owner may
update **existing PR4** with combined behavior, evidence and limitations under the
build/publication dispatch. No task PR. Commit messages state established actual
model/effort honestly (unknown if unavailable) and end with a blank line followed
by `Co-authored-by: omnigent <noreply@omnigent.ai>`. Later user real-world tests decide
whether to merge; no main merge is authorized here. Stop this phase with the
uncommitted plan, plan SHA256, exact refs/status/evidence paths and limitations.
