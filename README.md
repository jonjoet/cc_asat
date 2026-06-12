# cc_asat — Assembly Scaffolding and Annotation Transfer

Nextflow DSL2 pipeline for validating and improving microbial de novo assemblies against a reference genome. Supports fungal and bacterial genomes. Scaffolds the assembly, closes gaps, transfers annotations with identity-based merging, and runs QC.

## Quick Start

### 1. Annotation transfer only (no scaffolding)

Transfer annotations from a reference to your assembly, optionally merging vendor annotations:

```bash
nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY \
    --assembly      my_assembly.fasta \
    --reference     ref.fasta \
    --reference_gff ref.gff3 \
    --organism_type fungal \
    --sample_name   my_strain \
    -profile        docker
```

To merge vendor annotations alongside the reference lift:

```bash
nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY \
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

The default workflow (`EUK_SCAFFOLD_VALIDATION`) has two logical tracks — assembly processing and annotation transfer — plus a QC step.

### Assembly processing

1. **RagTag Correct** (optional) — Error-corrects the assembly using long reads.
2. **RagTag Scaffold** — Orders and orients contigs against the reference. Contigs RagTag cannot anchor (e.g. plasmids absent from the reference) are kept in the main FASTA and listed in `scaffold/{sample}_unplaced_contigs.tsv`.
3. **TGS-GapCloser** (conditional on `--reads`) — Closes gaps using long reads.
4. **RagTag Patch** (optional) — Fills remaining gaps from reference sequence.
5. **dnaapler** (conditional) — Reorients circular contigs to a canonical start (dnaA for bacterial chromosomes, other markers via mode selection).
6. **seqtk seq** — Wraps the final FASTA to 80 columns for broad tool compatibility.

Once the final assembly is produced, **annotation transfer** runs if `--reference_gff` was provided (see the next subsection for details), and **QUAST** runs at the end to report assembly metrics (plus gene-structure metrics when a reference GFF is available).

`ANNOTATION_TRANSFER_ONLY` skips assembly processing entirely, optionally applies dnaapler, then runs annotation transfer and QUAST on a pre-existing assembly.

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
| `--organism_type` | `fungal` or `bacterial` |

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
| `--scaffold_rename_pattern` | `null` | Optional regex with one capture group to substitute a reference strain prefix on placed scaffolds, keeping the chromosome label. Eukaryotic/yeast (roman numerals): `'_(Chr[IVXLCDM]+)$'` turns `LEXst001_ChrI` into `{sample}_ChrI`. Bacterial (single or numbered chromosome; arabic numerals optional): `'_(Chr[0-9IVXLCDM]*)$'` turns `strain_Chr` into `{sample}_Chr` and also matches `Chr1`/`Chr2`. The pattern keys off your reference's sequence names, so unmatched names (plasmids, unplaced contigs, or accession-named references like `NZ_CP012345.1`) keep their full name with the sample prefix. |

### Annotation Transfer Controls

| Parameter | Default | Description |
|---|---|---|
| `--skip_annotation_transfer` | `false` | Skip annotation transfer even when `--reference_gff` provided |
| `--skip_merge` | `false` | Run Liftoff but skip merging (debug mode) |
| `--fix_reference_gff` | `true` | Run AGAT on reference GFF before use |
| `--fix_vendor_gff` | `true` | Run AGAT on vendor GFF before use |
| `--fix_generic_names` | `true` | Replace generic Name attributes post-Liftoff |
| `--megagene_gene_threshold` | `5` | Gene overlapping more than this many others is removed |
| `--max_gene_length_bp` | — | Absolute max gene length in bp (disabled by default) |

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
    {sample}_unplaced_contigs.tsv        # Contigs RagTag left unplaced (also in final_outputs/)
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

- Nextflow >= 23.04.0
- Docker, Singularity, or Conda
- Target scale: yeast (~12 Mb, ~6000 genes) and bacterial (~1-10 Mb) genomes
