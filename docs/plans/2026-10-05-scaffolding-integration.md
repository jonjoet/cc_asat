# Integrate scaffolding fixes into PR #4

Date: 2026-10-05. Status: proposed; independent Opus/high plan review, authorized
plan commit and user summary approval precede a fresh implementation session.
Planning changes only this document; no merge, product edits, commit or push.
Requested planner/implementer: gpt-6-astra / high. Actual native model/effort:
**unknown**; dispatch metadata is not native execution evidence. No substitution,
extra-usage fallback, nested agents or agmsg. Work is serial under qbk-polly.
Revision 1 addresses `plan-review-1/REVIEW.md` against plan SHA256
`09ecf5d6d02dacfa749caf918f05bd8ab98f4305d1795de4787f92f2be6060d9`;
the revised plan still requires the retained reviewer's recheck and user approval.
Revision 2 addresses B3/N9–N11 in `plan-review-2/REVIEW.md` against SHA256
`98034d60909c8956bcea1670502217d32beea3643a73ad974055b4727d209c43`.

## Authority and boundaries

Worktree: `/home/qbk/qbk-code/cc_asat/.worktrees/qbk-polly/parser-v2/feature`.
Branch: `claude/ecstatic-thompson-w5cfoh`; existing PR:
<https://github.com/jonjoet/cc_asat/pull/4>.

| Role | Examined immutable SHA |
|---|---|
| Current PR4/base | `3d56a4513734d9dd41ddc80b31d7055e5232dbef` |
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
- Requirement record:
  `/home/qbk/qbk-code/tmp/cc_asat/scaffolding-integration-20261005T173525Z/REQUIREMENTS.txt`.
  This plan restates the requirements; no prior transcript is needed.

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
| Source `bin/rename_ragtag_scaffolds.py:23–46`: pattern runs before idempotent-prefix guard; only tests `lastindex` after a match; output opens immediately; no duplicate-ID check. Valid Python regexes can have zero/multiple groups, unmatched optional groups, unstable second-pass results or colliding outputs. | Validate one capture group before output, nonempty captured ID on each match, stable results and unique final IDs. Fail clearly without truncating input or publishing partial output. |
| Source rename module `:15–16` escapes apostrophes, but truthiness silently treats false/zero/empty like absence; separate-token forwarding fails for leading-hyphen patterns. | Accept null or a nonempty string; put this type/empty check in `RENAME_RAGTAG_SCAFFOLDS`'s `script:` block, before constructing the command. Forward one shell-quoted `--chr-pattern=<pattern>` token; helper validates Python regex semantics. No Java regex validator, entry/preflight edits or annotation-only behavior change. |
| Source classifier `:29–56` silently ignores truncated W rows; the `.fai` disagreement only warns (`:118–123`). | Skip blank/comment lines; reject any remaining row with fewer than five fields as malformed. Once the type is available, validate only W/N/U rows/coordinates and ignore other component types. Preserve the source structural rule and warning-only reference cross-check, including the name-collision limitation below. No general AGP validator or classifier-semantic repair. |
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
`S288C_ChrI`. Require proposed output IDs to be fixed points of this same operation
so canonical output stays unchanged on rerun. Reject reserved-suffix/custom-pattern cases that cannot
meet that rule, with a useful diagnostic; do not silently invent replacement IDs.
Reject duplicate input IDs and convergent output IDs (including `x` versus `S_x`,
or distinct strain names both mapping to `S_ChrI`), identifying the conflicting
original and proposed IDs. Validate before replacing output; reject input/output
aliasing, preserving the input and any pre-existing output on failure. Keep this
direct-CLI-only protection minimal: a path/same-file check and validate-before-write;
no new general filesystem safety framework. Keep
sequences, order, count and per-record length unchanged. Stdlib only.

Classifier contract: on well-formed RagTag 2.1.0 `-u`, no `-C` AGP, unplaced means
exactly one W component, no N/U gap, component ID equals object ID after stripping
one terminal `_RagTag`. Everything else is placed. TSV header is exactly
`contig_id\tobject_name\tlength_bp`; rows use **original query ID and raw RagTag
object ID**, in AGP order, with inclusive object-span length. AGP/reference inputs
are read-only. Empty/comment-only AGP or all-placed input yields a mandatory
header-only TSV.

**Real-world limitation requiring explicit user approval:** when a query contig
and reference sequence share a name, a genuinely placed single-contig chromosome
can satisfy the source rule and be listed as unplaced. With `chr1` on both sides,
`chr1_RagTag … W chr1 …` produces `chr1\tchr1_RagTag\t30000` for the 30 kb fixture.
The FAI cross-check only warns in the classifier task's `.command.err`; a successful
pipeline run does not expose that warning on the console. Preserve this source
behavior; do not imply scientific correctness or acceptance by making the merge.
The user summary and README must prominently disclose it and the warning location;
changing the classifier decision requires a separate ruling.

The approval summary and README must also enumerate the proposed hard failures:
invalid pattern syntax/group count or capture, duplicate/convergent IDs, non-fixed-
point names (including unplaced original IDs ending `_RagTag`), and YAML pattern
`false`/`0`/`''`/`{}`. Use null to disable the pattern; false is no longer “off.”
Pattern errors surface at the rename task, after RagTag/correction may have run,
not entry preflight. After correcting inputs/parameters, users may use `-resume`
with the retained work directory. Also document W/N/U malformed-row failures and
the helper's direct-CLI input/output-alias rejection; none is implied user approval.

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
plans immediately before edits. The only additions beyond base should initially
be the reviewed plan commit. Stop for an unexplained product delta/source movement.
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
branches, resource closures and selector; pass `SAMTOOLS_FAIDX.out.fai` directly
in both correction branches. It is already a value channel; remove source's
redundant `.first()` to avoid its warning. Review staged
**and unstaged** changes against both parents. A second compatibility commit is
acceptable if parent directs it; no cherry-pick/squash/rebase replaces the merge.

Future build file set (not current planning write permission):

| Files | Implementation |
|---|---|
| `bin/rename_ragtag_scaffolds.py` | Merge source; bounded validation, idempotence, collision and safe-output fixes above; extend inline self-test. |
| `bin/classify_unplaced_contigs.py` | Merge source behavior, including name-collision ambiguity; reject short noncomment rows, otherwise validate W/N/U only and ignore other types; self-tests for empty and edge outcomes. |
| `modules/local/rename_ragtag_scaffolds/main.nf` | One FASTA input/output; type/empty check in `script:` and shell-quoted equals-form pattern forwarding. Keep `process_single`. |
| `modules/local/classify_unplaced/main.nf` | AGP + FAI inputs, mandatory TSV output, `process_single`, source Python image. |
| `modules/local/ragtag/scaffold/main.nf` | Remove nonexistent unplaced emit only; preserve `-u`, no `-C`, pinned tool and `-t ${task.cpus}`. |
| `subworkflows/local/scaffolding.nf` | Add third FAI argument, classify alongside rename, emit `unplaced_list`, remove dead sentinel/input/output. |
| `workflows/euk_scaffold_validation.nf` | Pass FAI in both calls; retain options map and single downstream FASTA, annotation routing and reorientation. |
| `nextflow.config`, `conf/modules.config` | Add null pattern default and two TSV publish routes only; preserve all resource/engine/profile policy. |
| `README.md`, `assets/params.example.yaml`, `tests/README.md` | Combined interface, default naming change, opt-in examples/quoting, raw TSV schema/stage/publication, prominent name-collision warning and `.command.err` location, hard failures listed above, no separate unplaced FASTA, annotation-only unaffected, parser/cap promises and exact bounded gates. YAML includes null plus commented Roman/bacterial patterns. |
| Three source `claude_context/` documents | Bring in intact through merge; historical context, not active execution instructions. Link from current docs; no modernization/backlog cleanup. |
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
No retry loop or auto-expanding test matrix; only the single conditional OOM
fallback specified below is permitted. Record actual case/assertion/task
counts separately: these stdlib drivers have no pytest-collected test functions.

| Gate / implemented mode | Exact bounded coverage and pass criteria |
|---|---|
| `helpers.py` | Run both script self-tests and CLI assertions: default underscores/plasmid/accession, RagTag suffix, already-prefixed and repeated-run byte identity; Roman/bacterial/custom pattern, source-order `S288C_R64_ChrI → S288C_ChrI`, no-match, quoted apostrophe/backslash and leading-hyphen `-(Chr[IVX]+)$` via equals-form argv; invalid syntax, zero/multiple groups (even no-match), unmatched/empty capture, duplicate/convergent IDs, unstable/reserved-suffix names, aliased input/output. Failures nonzero with specific diagnostics and unchanged input/pre-existing output. Compare sequence/order/length exactly; no partial output. AGP: multi-W+N, multi-W+U, placed single, unplaced, multiple unplaced/order, all-placed, empty/comments, optional FAI and known equal-name misclassification/warning, malformed W/N/U rows/coordinates; exact TSV bytes and unchanged AGP/FAI hashes. Fixtures and expected literals saved, not derived using production rename/classify functions. |
| `static` | `nextflow lint <repo>` under strict v2, no formatting, zero errors; preserve warnings. Explicit inventory of 18 production modules, both helper modules single-labelled; scan active code/tests for obsolete unplaced emits/input/NO_FILE (historical docs excluded). Source audit preserves resource closures/floor/options and no new thread overrides. |
| `integration-resources` v2/v1 | Two config dumps (`docker`, `test,docker`); reuse existing canonical driver methods for R02 through CLI, R03 through YAML and L02 aliased-limit override, not the whole contract mode. Five tiers for each resource case, exact fixture triples; alias oversized requests clamp correctly. This is three resource startups per parser, plus configs/version, with no biological tasks. Preserve shared vector hash `32a1105d46420837bb1fbe148c9b4e5d095213f5d2a2856c43ba09448d83a8ab`. |
| `scaffolding-preview` v2/v1/unset | Five actual-entry previews: full default/no correction, full with reads+run_correct=true, full bacterial auto-reorientation, annotation-only without organism, invalid selector. Valid route inputs; require expected process membership, both full branches resolve FAI/rename/classifier, annotation has none of those scaffolding processes, invalid selector rejects before submission. All zero tasks. Assert absence of the engine warning containing "The operator `first` is useless when applied to a value channel" in output/logs of full-route previews and both smoke runs (also any permitted fallback). Supply custom pattern via YAML in one full case and CLI in another; explicit CLI `--reorient_assembly false` excludes DNAAPLER in the default full case. Retain exact selector error checks. Previews do not evaluate module script blocks or prove task pattern transport. |
| `scaffolding-modules` | Four v2 cases using real modules: mixed AGP/FASTA at R02 (`1/512 MB/30min`), mixed with a quoted leading-hyphen pattern via **YAML** at R03 (`8/7 GB/12h`), all-placed/header-only TSV at R02, and real `SCAFFOLDING` with correction enabled at `1/4 GB/1h` plus actual SAMTOOLS_FAIDX. v1 repeats only the first case. First three call real rename/classify together; each must execute once, inherit single resources, publish exact TSV to both destinations and retain all FASTA records. R03 single expected `[1,2147483648,3600000]`; R02 `[1,536870912,1800000]`. Correction case uses the renamed query below, expects an exact header-only TSV in both publications, verifies staged FAI/command observables below, and checks real correct/scaffold/rename/classifier completion with `-t 1`; no gap closing. |
| Pattern transport negatives, in `scaffolding-modules` v2 only | Four additional rename-only cases supply YAML `false`, `0`, `''` and `{}` at R02. Require nonzero exit with a named scaffold_rename_pattern type/empty diagnostic and no renamed/published FASTA. These are expected rejections, separate from successful task/resource counts. |
| `docker-rename` v2 | Execute the repaired existing one-task harness and exact combined-FASTA assertions, including bin bind/PATH, absence of a separate unplaced FASTA and R02 trace/wrapper requests. |
| `scaffolding-smoke` v2 | Two actual full runs, named FULL-DEFAULT (fungal/default rename/reorientation false) and FULL-PATTERN (bacterial/Roman regex/auto reorientation true), recipe below. No stubs. Require scaffold/classifier/rename, final wrapping, reference and vendor annotation, iterative merge and QUAST completion; second also DNAAPLER. Exactly one unplaced TSV row in each publication, retained plasmid sequence and expected final IDs, gene features on chromosome and plasmid whose seqids all exist in final FASTA. No nonexistent output/sentinel, duplicate ID or lost contig. |
| `annotation-smoke`, `legacy-entry` | Existing real annotation-only v2 gate and its five filter/merge command cases, plus existing six v1 legacy previews unchanged. Assert no scaffolding/classifier or unplaced TSV in annotation-only output; input identifiers remain unchanged when reorientation is false. |

Generate deterministic smoke inputs under the evidence case, using the existing
30 kb parser fixture chromosome sequence and gene. Rename its reference header/GFF
seqid to `strain_ChrI` and query header to `contig_3`. Add an unrelated 6 kb
`2micron_plasmid` query sequence using the documented LCG/codon recipe in tests
README with seed 20261006; insert its own distinct 897 bp coding sequence at
offset 1000 and vendor gene/mRNA/exon/CDS at 1001–1897. Reference contains no
plasmid. Save generator inputs, exact FASTA/GFF and hashes; ensure the placed
chromosome/query IDs differ to avoid the known AGP ambiguity. For correction's
module case, copy existing reference/assembly/reads to evidence; retain reference
`chr1` and rename only the assembly header to `contig_3` (same 30 kb sequence).
Expect exactly `contig_id\tobject_name\tlength_bp\n` in both published TSVs.
Require the classifier's staged FAI to match SAMTOOLS_FAIDX's emitted file by hash
and contain `chr1`/`30000` as its first two fields; `.command.sh` must pass that
staged filename to `--fai` and the scaffold AGP to `--agp`. These are wiring
observables, not a claim of biological correction quality. In existing module
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

One test-only fallback is proposed for user approval: if FULL-PATTERN's DNAAPLER
task has confirmed Docker OOM evidence tied to that task (not exit 137 alone),
preserve the failed run and allow exactly one fresh
FULL-PATTERN-M8 run. Change only CLI `--max_memory '4 GB'` to `'8 GB'`; keep
1 CPU, 1h, the same inputs/scientific options, no resume, and the 1,200-second
bound and launcher `--memory 4g`. Expected low/DNAAPLER resources become
`[1,2147483648,3600000]`, medium `[1,4294967296,3600000]`, single
`[1,2147483648,3600000]`. No high/unlabelled tasks run in this no-reads smoke;
their 8 GB requests would not be admitted by the 4 GiB launcher. Verify the
listed exact traces and unchanged biological assertions. No product/config-default
edits, admission overrides, new matrix, larger fixture or further retries; keep
the combined 10 GiB disk budget and 20 GiB free-space floor. Missing memory
headroom or a second failure blocks the gate, including DNAAPLER failing again at
2 GiB. Report the 4 GB failure and any 8 GB success distinctly; never claim the
4 GB smoke passed.

For OOM evidence, record UTC `smoke_start`/`smoke_end` around the bounded original
run, then immediately query the existing daemon with
`timeout 30s docker events --since "$smoke_start" --until "$smoke_end" --filter type=container --filter event=oom --format '{{json .}}'`.
Retain the exact command, timestamps, JSON stdout, stderr and exit code under that
case's evidence. Correlate the event's container ID/name with the DNAAPLER task's
container name in its preserved `.command.run`; an event for another task does
not qualify. No privileged kernel/dmesg access. Missing, expired, uncorrelated or
failed event capture does **not** justify a retry; the gate remains blocked.

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

Future gate handoff must list absolute paths to `$evidence/RUN.txt`, source diff,
untracked archive, image/JAR metadata, `helpers/{command.txt,output.log,exit-code.txt}`,
every `<mode>-26.04.6-<parser>/{RUN.txt,command.txt,output.log,exit-code.txt,
case-inventory.tsv,results.tsv}`, per-case trace/work/outputs, and `ARTIFACTS.txt`.
Record disk consumption and before/after source equality. Preserve unsuccessful
attempts. Missing/inaccessible evidence blocks review; expected cases cannot vanish
from inventory. After the eventual merge commit, prove both base and source SHAs
are ancestors with `git merge-base --is-ancestor`, retain `git show --format=raw`
for its two parents, and bind tested snapshot to the committed tree.

Reviewer prompt: “Read this full plan and REQUIREMENTS.txt. Check all nine source
commits' intended behavior, merge ancestry, parser/resource/selector preservation,
helper failure semantics, raw-versus-final naming, bounded Docker gates and disk
rules. Review the exact plan hash, then the exact final integration SHA/snapshot;
report blockers, non-blockers and suggestions separately with file:line evidence.
Do not infer semantic validity from a conflict-free merge or prior approvals.”

Open procedural decisions: independent Opus/high review, authorized reviewed-plan
commit and user summary approval. Keeping unplaced sequences in the main FASTA
is settled; acceptance of the disclosed classifier limitation and new hard
failures is **not** implied and must be explicit in that summary approval.
Implementation feasibility risks are regex/suffix
ambiguities, AGP reference/query name collisions, source shell interpolation,
channel starvation, actual DNAAPLER output, and immutable-cache availability.
Report unexpected substantial scope before expanding. No permission to fix unrelated
scientific behavior is implied by “all intended features.”

After green gates and final independent review, the designated feature owner may
update **existing PR4** with combined behavior, evidence and limitations under the
build/publication dispatch. No task PR. Commit messages state established actual
model/effort honestly (unknown if unavailable) and end with a blank line followed
by `Co-authored-by: omnigent <noreply@omnigent.ai>`. Later user real-world tests decide
whether to merge; no main merge is authorized here. Stop this phase with the
uncommitted plan, plan SHA256, exact refs/status/evidence paths and limitations.
