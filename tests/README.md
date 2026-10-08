# Parser and resource acceptance

Run all checks inside Docker. The host runner only records provenance and launches
containers; it never runs Nextflow, Python assertions, or scientific tools on the
host. No package installation is needed on the host.

## Images and scheduling

Cache the official Nextflow 26.04.6 and 26.04.5 images before running gates.
The runner verifies the approved 26.04.6 image ID
`83bbf3dd9e84ecd4d53a86620d08fe0259bca00a8f59f6f31664eb90033f460f`
and records full image metadata for both engines. Every invocation uses the
recorded immutable image ID. Set `CC_ASAT_NXF_DIST` to an existing verified
distribution; it is mounted read-only with independent writable state per case.
The 26.04.6 JAR SHA256 must be
`2ca0251ae2d749317d9fbe5fe191a1616b5f44b608224268924c71b32f5ed9e2`.
Never chmod/write/extract into the shared hardlinked binary or copy it per phase.
The hash and actual `nextflow -version` output are retained. No host fallback.

Light modes use at most four outer CPUs/4 GiB and have no Docker socket.
`tools` runs pinned tool images directly, one command at a time, with a
10-minute timeout per invocation. `docker-rename`, `annotation-smoke`,
`scaffolding-modules` and `scaffolding-smoke` mount the daemon socket into the
Nextflow launcher, using the invoking
uid/gid and socket group, identical absolute source/evidence mounts, and serial
task execution. The cached Nextflow image provides the Docker CLI. This access
is daemon control, not a security sandbox. Do not change daemon configuration
or account groups. Coordinate heavyweight image pulls and tool gates with other
active repository workers before invoking those modes.

## Reproduction

Choose a fresh absolute evidence path under `~/qbk-code/tmp/cc_gcev` or
`~/qbk-code/tmp/cc_asat`. Preserve
all attempts. The runner refuses existing phase paths and requires the exported
run base to match `--evidence` exactly.

```bash
repo=$(git rev-parse --show-toplevel)
evidence="$HOME/qbk-code/tmp/cc_gcev/cc_asat-parser-$(date -u +%Y%m%dT%H%M%SZ)"
export CC_GCEV_RUN_BASE="$evidence"
export CC_ASAT_NXF_DIST=/absolute/path/to/verified/framework
mkdir "$evidence"
printf 'commit: %s   dirty: %s\nstarted: %s\npurpose: parser/resource acceptance\n' \
  "$(git -C "$repo" rev-parse HEAD)" \
  "$(test -z "$(git -C "$repo" status --porcelain)" && echo no || echo yes)" \
  "$(date -u +%FT%TZ)" > "$evidence/RUN.txt"
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode static --engine 26.04.6 --parser v2
for parser in v2 unset v1; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode contract --engine 26.04.6 --parser "$parser"
done
for parser in v1 v2 unset; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode fractions --engine 26.04.6 --parser "$parser"
done
for parser in v1 v2; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode unsupported --engine 26.04.5 --parser "$parser"
done
export CC_ASAT_INTERFACE=selector
for parser in v1 v2; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode entry-parameters --engine 26.04.6 --parser "$parser" --interface "$CC_ASAT_INTERFACE"
done
for parser in v1 v2 unset; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode previews --engine 26.04.6 --parser "$parser" --interface "$CC_ASAT_INTERFACE"
done
bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode legacy-entry --engine 26.04.6 --parser v1 --interface "$CC_ASAT_INTERFACE"
# Run these only when the heavyweight slot is available:
for mode in tools docker-rename annotation-smoke; do
  bash "$repo/tests/parser_resources/run.sh" --repo "$repo" --evidence "$evidence" --mode "$mode" --engine 26.04.6 --parser v2 --interface "$CC_ASAT_INTERFACE"
done
git -C "$repo" diff --check
```

## Coverage and interpretation

The shared fixture is `tests/integration/resource_vectors.json`, copied
byte-for-byte from the independently validated cc_gcev artifact. SHA256:
`32a1105d46420837bb1fbe148c9b4e5d095213f5d2a2856c43ba09448d83a8ab`.
It is the oracle; no tests generate expected R triples from the product helpers.
Python's JSON integers are lossless. Fixture layer recipe keys are expanded by
the harness, never sent as public pipeline parameters.

- `static`: strict lint without formatting and a source audit of all 18 modules,
  labels, worker arguments and normalized Boolean consumers.
- `contract`: eight config/profile combinations; R01–R13 through CLI/YAML;
  P01–P10; L01–L03; D01–D04; two helper batches on each of v1/v2.
  The genuinely unset parser has only R02/R03, P06, L01 and D01 plus configs.
  D03 is explicitly a memory-default fallback component test, using only the
  documented one-literal replacement and a separate raw JVM observation.
- H-YAML/H-CLI exercise the actual production helper through engine parameter
  transport. At the current fixture, these contain 296/242 assertion rows per
  parser, not separate Nextflow startups or collected test functions.
- `entry-parameters`: 64 actual-entry previews per parser, covering both
  approved selector routes, ten flags, three caps, precedence, and nullable
  contexts. Together with four helper startups this gives **132 shared
  parameter startups** across v1/v2.
- `fractions`: repository-local inexact decimal memory/duration regressions,
  independent of the shared fixture. CLI/YAML helper batches, config-only exec
  resolution, and real-entry previews check native rounding, compound durations,
  unchanged native object identity, overflow/sub-unit rejection and clock-format
  rejection. Full v1/v2 each use 76 startups; focused unset uses 28, including
  version calls. These do not alter the 132 shared parameter startup count.
- `previews`: selector success/invalid/empty/null cases and exact YAML
  whitespace rejection; reorientation auto/false/true contexts and numeric
  migration previews. CLI trailing whitespace is not an oracle because engine
  transport can trim it. Preview membership comes from actual process creation
  log records, never the list of all parsed process definitions.
- `legacy-entry`: six v1-only previews prove legacy annotation precedence,
  selector validation, cap validation and Boolean validation.
- `unsupported`: 26.04.5/v1 and /v2 must reject the enforced floor before tasks.
- `tools`: seven pinned one-worker command paths. Runtime success requires
  expected biological outputs; source-only substitutes are explicitly labelled
  `SOURCE_ONLY_RUNTIME_NOT_VERIFIED` and require independent source review.
  An input error or timeout is never proof of a tool CPU minimum.
- `docker-rename`: the real rename module, its bin bind/PATH resolution, exact
  renamed sequences, resource trace and Docker CPU-share/memory arguments.
- `annotation-smoke`: real one-CPU annotation-only iterative outputs, false
  copies/reorientation/AGAT gates and QUAST; five additional real filter/merge
  command checks cover false novel-only and null/CLI/YAML zero/positive length
  limits. This does not exercise the full scaffolding or reference patch arm.

R10/R11 use five exec bodies with normal termination, proving directive
resolution at sub-executable sizes. Other R cases are completed echo tasks in
the outer container, with local admission deliberately larger than that
container's physical allocation. This exemption never applies to biological
tasks. These checks do not prove OS enforcement of 1 byte or 1 ms. Docker CPU
shares also do not impose a hard runtime CPU quota.

## Evidence

Every phase and case starts with `RUN.txt`. Phase evidence retains source diff,
untracked-file archive and hashes, pinned contract/fixture hashes, image/JAR
metadata, expanded Docker command, exit and status before/after. Cases retain
expanded Nextflow argv, effective input layers, stdout/stderr, exit, work/cache,
`.nextflow.log` and expected/observed records.

`case-inventory.tsv` retains expected outcomes and final status.
`parameter-coverage.tsv` maps grammar rows, flags/dimensions, organism,
transport and entry route to invocation IDs. `results.tsv` identifies
contract/case/engine/parser/transport/tier/attempt and actual CPU/bytes/ms.
Resource records join raw trace via work hash; trace supplies task ID and name.
`ARTIFACTS.txt` contains absolute evidence paths. Missing rows, wrong diagnostics,
unexpected tasks and missing images fail gates; they are not silent skips.
The source-only tool status is not a runtime pass.

## Deterministic fixtures

The 30,000-base reference and assembly are identical. To reproduce their sequence,
start a 32-bit unsigned LCG with seed 20261005 and repeat
`state = (1664525 * state + 1013904223) mod 2**32`; choose from `ACGT` using
`state >> 30`. Continue that generator for 297 codons, selecting each with
`(state >> 16) mod 61` from the lexicographically sorted A/C/G/T codons excluding
TAA, TAG and TGA. Replace sequence at zero-based offset 1000 with
`ATG + those 297 codons + TAA`, preserving total length, and wrap at 80 columns.
This nonrepetitive coding sequence supplies unique seeds for default Liftoff mapping.
The GFFs describe that single gene/mRNA/exon/CDS. Four FASTQ reads are 3000-base
windows starting at 0, 1500, 3000 and 4500, with `I` quality. The rename input
is one combined tiny literal FASTA. These fixtures are miniature transport and
command checks, not representative scientific datasets.

## Bounded scaffolding integration gates

The approved [integration plan](../docs/plans/2026-10-05-scaffolding-integration.md)
fixes the gate matrix. Helpers run in Python Docker with a 120-second bound.
On 26.04.6 v2 run `static`, `integration-resources`, `scaffolding-preview`,
`scaffolding-modules`, `docker-rename`, `scaffolding-smoke` and `annotation-smoke`.
On v1 run `integration-resources`, `scaffolding-preview`, `scaffolding-modules`
and `legacy-entry`; unset runs only `scaffolding-preview`.

```bash
# First create RUN.txt and retain the full binary diff/untracked snapshot as above.
# Use fresh evidence, including after any source change; do not overwrite attempts.
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
```

Inventory is written before execution. Counts exclude each mode's version call:
`integration-resources` has two configs and R02 CLI/R03 YAML/L02 alias (11 actual
resource tasks); previews have five zero-task entries; modules have four v2
successful cases (10 actual tasks) and four separately counted expected YAML
rejections, while v1 repeats just the mixed case (two tasks). Rename has one task.
Two full smokes have 11/12 real tasks, including DNAAPLER in FULL-PATTERN;
annotation retains its one smoke plus five two-task command cases. There are no
pytest-collected test functions. Exact counts/resources are retained in inventories,
raw traces and `results.tsv`; a failed task or incomplete case cannot count as pass.

`tests/scaffolding/helpers.py` independently asserts CLI diagnostics, unchanged
inputs/pre-existing outputs on validation failure, exact TSV bytes, single-pass
original-suffix preservation and sequence/order/length preservation. It generates
module fixtures containing N/U gaps, quoted leading-hyphen pattern transport,
and header-only all-placed publications. Correction uses the 30 kb fixture renamed
to `contig_3`, requiring confidence ID exactly `contig_3_1_30000_+` and header-only
TSV. Correction suffixes remain raw evidence IDs and may remain in final FASTA IDs.

FULL-DEFAULT uses same-name placed query/reference `strain_ChrI`, fungal/default
rename and explicit reorientation false. FULL-PATTERN uses query `contig_3`,
bacterial auto reorientation and Roman regex via CLI. Both add unrelated 6 kb
query `2micron_plasmid` using the LCG/codon recipe above with seed 20261006 and
its own gene at 1001–1897. FULL-PATTERN additionally has an unrelated reference
sequence named `2micron_plasmid`, seed 20261007, exercising genuine unplaced status
despite a reference-matching name. Vendor plasmid feature IDs and Name are distinct.
Both TSVs must contain exactly `2micron_plasmid`, `2micron_plasmid_RagTag`, `6000`
after the unchanged header. Generator recipe, literal inputs and hashes are saved.
Raw TSV query membership, same-task AGP/confidence hashes and staged symlink
resolution to the completed scaffold work directory are mandatory. Final chromosome
and plasmid genes must have seqids in the final FASTA. Compare sequences to RagTag
before rename, then allow only rotation/reverse-complement when DNAAPLER is enabled.

The launcher stays at 4 CPUs/4 GiB; full tasks use a 1 CPU/4 GB/1h cap. Each
full invocation is bounded at 1200 seconds, others at 600 seconds. OOM/suspected
OOM stops the run for reporting, with no retry, cap escalation or resume. A failed
DNAAPLER miniature fixture blocks the bacterial gate. Disk budget is 10 GiB added
across all attempts, with a 20 GiB free-space floor; inspect df/du before each phase
and retain failures/work directories. The patch-restoration missing container
remains outside these gates and is not repaired or claimed verified.
