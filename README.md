# cc_asat — Assembly Scaffolding and Annotation Transfer

Nextflow DSL2 pipeline for validating and improving microbial de novo assemblies against a reference genome. Supports fungal and bacterial genomes. Scaffolds the assembly, closes gaps, transfers annotations with identity-based merging, and runs QC.

## Quick Start

### 1. Annotation transfer only (no scaffolding)

Transfer annotations from a reference to your assembly, optionally merging vendor annotations:

```bash
nextflow run main.nf --workflow annotation_transfer_only \
    --assembly      my_assembly.fasta \
    --reference     ref.fasta \
    --reference_gff ref.gff3 \
    --organism_type fungal \
    --sample_name   my_strain \
    -profile        docker
```

To merge vendor annotations alongside the reference lift:

```bash
nextflow run main.nf --workflow annotation_transfer_only \
    --assembly      my_assembly.fasta \
    --reference     ref.fasta \
    --reference_gff ref.gff3 \
    --vendor_gff    vendor.gff \
    --organism_type fungal \
    --sample_name   my_strain \
    -profile        docker
```

### 2. Full workflow with vendor merge

Scaffold, gap-close, and merge reference + vendor annotations:

```bash
nextflow run main.nf \
    --assembly       assembly.fasta \
    --reference      ref.fasta \
    --reference_gff  ref.gff3 \
    --vendor_gff     vendor.gff \
    --organism_type  fungal \
    --reads          reads.fastq.gz \
    --sample_name    my_strain \
    -profile         docker
```

### 3. Iterative run (using previous output as reference)

Feed the iterative-safe merged GFF from a previous run back as reference input:

```bash
nextflow run main.nf \
    --assembly       new_assembly.fasta \
    --reference      prev_run_final.fasta \
    --reference_gff  prev_run_merged_iterative.gff3 \
    --vendor_gff     new_vendor.gff \
    --organism_type  fungal \
    --reads          reads.fastq.gz \
    --liftoff_copies false \
    --merge_novel_only true \
    --sample_name    my_strain_v2 \
    -profile         docker
```

`--liftoff_copies false` skips the copies Liftoff run (copy suffixes from a prior run would compound). `--merge_novel_only true` passes reference features through unchanged, only adding unmatched vendor features.

## Pipeline Steps

The default `--workflow full` route (`EUK_SCAFFOLD_VALIDATION`) has two logical tracks — assembly processing and annotation transfer — plus a QC step.

### Assembly processing

1. **RagTag Correct** (optional) — Error-corrects the assembly using long reads.
2. **RagTag Scaffold** — Orders and orients contigs against the reference.
3. **TGS-GapCloser** (conditional on `--reads`) — Closes gaps using long reads.
4. **RagTag Patch** (optional) — Fills remaining gaps from reference sequence.
5. **dnaapler** (conditional) — Reorients circular contigs to a canonical start (dnaA for bacterial chromosomes, other markers via mode selection).
6. **seqtk seq** — Wraps the final FASTA to 80 columns for broad tool compatibility.

Once the final assembly is produced, **annotation transfer** runs if `--reference_gff` was provided (see the next subsection for details), and **QUAST** runs at the end to report assembly metrics (plus gene-structure metrics when a reference GFF is available).

`--workflow annotation_transfer_only` skips scaffolding and gap closing, optionally applies dnaapler, then runs annotation transfer and QUAST on a pre-existing assembly. This route requires `--reference_gff`; `--organism_type` may be omitted.

### Annotation Transfer

For each input GFF (reference, and optionally vendor):

1. **AGAT GFF fix** (optional, per input) — Standardises the GFF so downstream tools behave predictably. Controlled by `--fix_reference_gff` and `--fix_vendor_gff` (both default `true`).
2. **Megagene Filter** — Removes artifactual mega-genes (common AGAT artifact).
3. **Liftoff** — Lifts annotations onto the final assembly, including genes and non-gene features (LTRs, transposable elements, repeats, etc. — see `--liftoff_feature_types`). The reference is lifted twice by default: once without `-copies` (primary, iterative-safe) and once with `-copies` (copy detection). Vendor is lifted once.
4. **Name Fix** (optional) — Replaces generic feature names with informative alternatives.

If `--vendor_gff` is provided, the reference and vendor lifted GFFs are merged by identity (see below).

The dual Liftoff approach produces two merged GFFs when vendor annotations are provided:
- **Full merge** (`*_merged.gff3`) — Uses the copies Liftoff output. Contains detected duplications. Best for analysis of the current genome.
- **Iterative merge** (`*_merged_iterative.gff3`) — Uses the primary (no copies) Liftoff output. Clean IDs, safe as reference input for subsequent pipeline runs.

A **copy report** (`*_copy_report.txt`) lists features detected as extra copies.

## Parameters

### Required

| Parameter | Description |
|---|---|
| `--assembly` | De novo assembly FASTA |
| `--reference` | Reference genome FASTA |
| `--organism_type` | `fungal` or `bacterial`; required for `--workflow full` |

### Optional Inputs

| Parameter | Default | Description |
|---|---|---|
| `--reads` | — | Long reads FASTQ(.gz) for gap closing and correction |
| `--read_type` | `ont` | Read type: `sr`, `ont`, or `corr` |
| `--reference_gff` | — | Reference GFF3 for annotation transfer and QUAST |
| `--vendor_gff` | — | Vendor annotation GFF3 on the original assembly |

### Scaffolding Controls

| Parameter | Default | Description |
|---|---|---|
| `--run_correct` | `false` | Run RagTag Correct before scaffolding (requires `--reads`) |
| `--fill_gaps_from_ref` | `false` | Fill remaining gaps from reference after gap closing |
| `--reorient_assembly` | auto | Run dnaapler; defaults to `true` for bacterial, `false` for fungal |

### Annotation Transfer Controls

| Parameter | Default | Description |
|---|---|---|
| `--skip_annotation_transfer` | `false` | Skip annotation transfer even when `--reference_gff` provided |
| `--skip_merge` | `false` | Run Liftoff but skip merging (debug mode) |
| `--fix_reference_gff` | `true` | Run AGAT on reference GFF before use |
| `--fix_vendor_gff` | `true` | Run AGAT on vendor GFF before use |
| `--fix_generic_names` | `true` | Replace generic Name attributes post-Liftoff |
| `--megagene_gene_threshold` | `5` | Gene overlapping more than this many others is removed |
| `--max_gene_length_bp` | — | Absolute max gene length in bp (null or zero disables the limit) |

### Liftoff Controls

| Parameter | Default | Description |
|---|---|---|
| `--liftoff_copies` | `true` | Run dual Liftoff (with and without `-copies`) for copy analysis |
| `--liftoff_s` | `0.5` | Primary alignment identity threshold (Liftoff default) |
| `--liftoff_sc` | `0.95` | Copy sequence identity threshold for `-copies` mode |
| `--liftoff_feature_types` | *(see below)* | Space-separated list of additional parent feature types for Liftoff to lift (beyond `gene`, which is always included) |

By default, Liftoff only lifts `gene` features and their children. The `--liftoff_feature_types` parameter specifies additional top-level feature types to lift. Types not present in the source GFF are silently ignored, so the default list is safe for both fungal and bacterial genomes.

Default `liftoff_feature_types`: `pseudogene LTR_retrotransposon transposable_element repeat_region long_terminal_repeat transposon_fragment insertion_sequence mobile_element mobile_genetic_element prophage CRISPR centromere telomere origin_of_replication regulatory_region`.

Feature types follow the [Sequence Ontology](http://www.sequenceontology.org/browser/obob.cgi) (SO) vocabulary used by GFF3. Consult the SO browser to find additional types relevant to your annotation.

### Merge Controls

| Parameter | Default | Description |
|---|---|---|
| `--merge_novel_only` | `false` | Novel-only mode: reference features pass through unchanged, only unmatched vendor features are added |
| `--merge_overlap_threshold` | `0.95` | Reciprocal CDS overlap fraction required for positional match |
| `--coord_preference` | `reference` | Source of coordinates for merged features |
| `--description_preference` | `vendor` | Source of Name/product/description for merged features |
| `--merge_exact_fields` | `ID Name gene locus_tag` | GFF attributes matched as whole strings |
| `--merge_word_fields` | `product description` | GFF attributes matched word-by-word (set to `none` to disable) |
| `--merge_word_min_length` | `4` | Minimum word length for word-field matching |
| `--merge_skip_types` | `region chromosome source` | Space-separated feature types to exclude from merging (metadata types that span entire sequences) |

### General

| Parameter | Default | Description |
|---|---|---|
| `--sample_name` | `sample` | Prefix for output files |
| `--outdir` | `results` | Output directory |
| `--workflow` | `full` | Exact selector: `full` or `annotation_transfer_only` |
| `--max_cpus` | auto | CPU limit (auto-detected minus 2) |
| `--max_memory` | auto | Memory limit (auto-detected minus 2 GB) |
| `--max_time` | `168h` | Wall time limit |

## Output

```
results/
  annotation_transfer/
    agat/                                # AGAT-fixed GFFs
    megagene_filter/
      reference/
      vendor/                            # if --vendor_gff
    liftoff/
      reference/                         # Primary Liftoff (no copies)
      reference_copies/                  # Copies Liftoff (if --liftoff_copies)
      vendor/                            # if --vendor_gff
    copy_analysis/                       # if --liftoff_copies
      {sample}_copy_report.txt
    fix_names/                           # if --fix_generic_names
      reference/
      reference_copies/
      vendor/
    merged/                              # if --vendor_gff and not --skip_merge
      {sample}_merged.gff3              # Full merge (from copies Liftoff)
      {sample}_merged_iterative.gff3    # Iterative merge (from primary Liftoff)
      {sample}_merge_summary.txt
      {sample}_merge_iterative_summary.txt
  correct/                               # if --run_correct
  scaffold/
  gapclosed/                             # if --reads
  dnaapler/                              # if reorientation enabled
  patch/                                 # if --fill_gaps_from_ref
  qc/
    {sample}_quast_results/
  final_outputs/
    {sample}_final.fasta
    {sample}_reference_liftoff.gff3      # Primary ref Liftoff (no copies)
    {sample}_merged.gff3                 # Full merge
    {sample}_merged_iterative.gff3       # Iterative merge (safe for reuse)
    {sample}_copy_report.txt             # Copy analysis
  pipeline_info/
```

### Merge Summary

The merge summary reports:
- **Full matches**: Genes matched by both CDS overlap and identifier — merged into single features
- **Partial matches (position only)**: CDS overlap but no shared identifier — both kept
- **Partial matches (identifier only)**: Shared identifier but no CDS overlap — both kept
- **Unmatched**: Present in only one source — kept as-is

Features are tagged with `annotation_source=merged|reference|vendor` and, for merged features, `ref_id=` and `vendor_id=` attributes.

## Profiles

| Profile | Description |
|---|---|
| `standard` | Docker + Conda fallback (recommended) |
| `docker` | Docker only |
| `singularity` | Singularity only |
| `singularity_conda` | Singularity + Conda fallback (HPC) |
| `conda` | Conda only |
| `test` | Test defaults |

## Requirements

- Nextflow >= 26.04.6 (enforced)
- Docker, Singularity, or Conda
- Target scale: yeast (~12 Mb, ~6000 genes) and bacterial (~1-10 Mb) genomes

## Parser migration and parameter files

Nextflow 26.04.6 with parser v2 is the primary supported path, either with
`NXF_SYNTAX_PARSER=v2` or with that variable unset. V1 is a focused compatibility
fallback; later Nextflow releases should be checked with the parser/resource gates
before deployment. Version 26.04.5 is below the enforced floor on both parsers.

Replace old `-entry ANNOTATION_TRANSFER_ONLY` commands with
`--workflow annotation_transfer_only`. Values are exact and case-sensitive;
empty, null, and unknown selectors fail before tasks. The default is `full`.
For older command wrappers, the legacy route remains available on v1:

```bash
NXF_SYNTAX_PARSER=v1 nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY \
    -params-file annotation.yaml -profile docker
```

Legacy `-entry` always selects annotation-only, including when `--workflow full`
is present. The selector must still be valid, and the same caps and Booleans are
validated. It logs: `INFO: Legacy -entry ANNOTATION_TRANSFER_ONLY selects annotation_transfer_only; --workflow does not select the route.`

Start with [assets/params.example.yaml](assets/params.example.yaml), replace its
path placeholders, and run `nextflow run main.nf -params-file params.yaml -profile docker`.
CLI parameters override YAML, which overrides config/profile parameters.
Booleans accept actual YAML Booleans or trimmed, case-insensitive `true`/`false`
strings. Values such as `yes`, `0`, or `auto` are rejected before tasks.

```yaml
workflow: annotation_transfer_only
assembly: my_assembly.fasta
reference: reference.fasta
reference_gff: reference.gff3
liftoff_copies: false
merge_novel_only: false
reorient_assembly: null
```

`reorient_assembly: null` (or omission) selects auto: true for bacterial, false
for fungal, and false when annotation-only omits `organism_type`. Explicit
`--reorient_assembly false` stays false even for bacterial input. CLI text `null`
is not YAML null. Other public Booleans do not accept null.

## Resource requests

Use `--max_cpus`, `--max_memory`, and `--max_time` as the resource interface.
Every explicit cap governs every task, including caps below nominal tier floors
and one CPU. CPU accepts integers or digit strings in 1..2147483647; memory and
time require positive unit-bearing quantities (for example `512 MB`, `1.5 GB`,
`30min`, or `1h 30min`). Null and invalid caps fail before any task.
Clock-format durations such as `01:30:00` are rejected; use `1h 30min` or `90min`.
Fractional quantities retain Nextflow's native rounding to bytes/milliseconds;
compound durations round each component before addition.

| Process tier | CPU request | Memory request | Time request |
|---|---|---|---|
| single | 1 | 2 GiB | 1h |
| low | 25%, rounded up; floor 1 | 25%, rounded up in MiB; floor 1 GiB | 25%, rounded up in ms; floor 1h |
| medium | 50%, rounded up; floor 2 | 50%, rounded up in MiB; floor 2 GiB | 50%, rounded up in ms; floor 4h |
| high / unlabelled | maximum | maximum | maximum |

All requests, including floors, are clamped to the effective maxima. Memory is
truncated to whole MiB before proportional division, matching the shared policy;
Nextflow GB/MB units are binary. For caps 8 CPUs / 7 GB / 12h, low requests
2 CPUs / 1792 MB / 3h and medium requests 4 CPUs / 3584 MB / 6h.
This replaces cc_asat's older fixed low/medium requests and fixed high walltime.

Omitted CPU and memory maxima use launcher detection minus two CPUs/two whole
GiB, with a minimum of one CPU/one GiB. Memory uses Linux MemTotal, falling back
to JVM maximum memory; time defaults to 168h. These are launcher heuristics,
not cgroup or scheduler allocation detection. Explicit caps replace detection.

Limits are per-task requests, not an aggregate pipeline budget. Docker CPU
shares permit time-sharing and are not a hard CPU quota; tool worker flags use
the allocated CPUs. Very small positive memory/time caps can cause real task
failures. Native resource limits also clamp larger `withName` requests; replacing
`resourceLimits`, replacing the entire project config with `-C`, or overriding
tool thread flags through `task.ext.args` is outside this supported interface.

See [tests/README.md](tests/README.md) for Docker-only reproduction, parser matrices,
preserved evidence, and the distinction between previews and actual tool runs.
