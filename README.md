# cc_asat — Annotation-aware Scaffold Assembly Tool

Nextflow DSL2 pipeline for validating and improving microbial de novo assemblies against a reference genome. Supports both fungal (eukaryotic) and bacterial (prokaryotic) genomes. Scaffolds the assembly, closes gaps, transfers annotations from both reference and vendor sources, merges them using identity-based matching, and produces QC reports.

## Pipeline Steps

The default workflow (`EUK_SCAFFOLD_VALIDATION`) runs:

1. **AGAT GFF fixing** (optional, on by default) — Standardises input GFF files using `agat_convert_sp_gxf2gxf.pl`. Controlled by `--fix_reference_gff` and `--fix_vendor_gff`.

2. **RagTag Correct** (optional, off by default) — Error-corrects the assembly using long reads. Enable with `--run_correct` (requires `--reads`).

3. **RagTag Scaffold** — Orders and orients contigs against the reference.

4. **TGS-GapCloser** (conditional) — Closes gaps using long reads. Runs when `--reads` is provided.

5. **RagTag Patch** (optional, off by default) — Fills remaining gaps from reference sequence. Enable with `--fill_gaps_from_ref`.

6. **dnaapler** (conditional) — Reorients circular contigs so dnaA is at position 1. On by default for bacterial genomes, off for fungal. Override with `--reorient_assembly true/false`.

7. **Annotation Transfer** (conditional, requires `--reference_gff`) — For each GFF source (reference and optionally vendor):
   - **Megagene Filter** — Removes artifactual mega-genes that span many real genes (common AGAT artifact). Configurable via `--megagene_gene_threshold` and `--max_gene_length_bp`.
   - **Liftoff** — Lifts annotations onto the final assembly.
   - **Name Fix** (on by default) — Replaces generic feature names (e.g. `gene-1`) with informative alternatives from product/description fields. Controlled by `--fix_generic_names`.
   - **Annotation Merge** — Symmetric identity-based merge of reference and vendor annotations. Matches genes by reciprocal CDS overlap AND shared identifiers. Produces a single merged GFF with full/partial/unmatched classification.

8. **QUAST** — Assembly quality metrics.

An alternative entry point, `ANNOTATION_TRANSFER_ONLY`, runs steps 1, 6 (optional), 7, and 8 on a pre-existing assembly.

## Quick Start

Minimal run (scaffolding + gap closing, no annotations):
```bash
nextflow run main.nf \
    --assembly      assembly.fasta \
    --reference     ref.fasta \
    --organism_type fungal \
    --reads         reads.fastq.gz \
    -profile        docker
```

Full run with annotation transfer and vendor merge:
```bash
nextflow run main.nf \
    --assembly       assembly.fasta \
    --reference      ref.fasta \
    --organism_type  fungal \
    --reads          reads.fastq.gz \
    --reference_gff  ref.gff3 \
    --vendor_gff     vendor.gff \
    -profile         docker
```

Bacterial genome (reorientation enabled by default):
```bash
nextflow run main.nf \
    --assembly       assembly.fasta \
    --reference      ref.fasta \
    --organism_type  bacterial \
    --reads          reads.fastq.gz \
    --reference_gff  ref.gff3 \
    -profile         docker
```

Annotation transfer only (no scaffolding):
```bash
nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY \
    --assembly      target.fasta \
    --reference     ref.fasta \
    --reference_gff ref.gff3 \
    --vendor_gff    vendor.gff \
    --organism_type fungal \
    -profile        docker
```

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

### Annotation Transfer Controls

| Parameter | Default | Description |
|---|---|---|
| `--skip_annotation_transfer` | `false` | Skip annotation transfer even when `--reference_gff` provided |
| `--skip_merge` | `false` | Run liftoff but skip merging (debug mode) |
| `--fix_reference_gff` | `true` | Run AGAT on reference GFF before use |
| `--fix_vendor_gff` | `true` | Run AGAT on vendor GFF before use |
| `--fix_generic_names` | `true` | Replace generic Name attributes post-Liftoff |
| `--megagene_gene_threshold` | `5` | Gene overlapping more than this many others is removed |
| `--max_gene_length_bp` | — | Absolute max gene length in bp (disabled by default) |

### Merge Controls

| Parameter | Default | Description |
|---|---|---|
| `--merge_overlap_threshold` | `0.50` | Reciprocal CDS overlap fraction required for positional match |
| `--coord_preference` | `reference` | Source of coordinates for merged features |
| `--description_preference` | `vendor` | Source of Name/product/description for merged features |
| `--always_keep_types` | `transposable_element repeat_region LTR_retrotransposon long_terminal_repeat transposon_fragment` | Space-separated feature types never dropped |

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
├── correct/                              # RagTag correction (if --run_correct)
├── scaffold/                             # RagTag scaffolding
├── gapclosed/                            # TGS-GapCloser (if --reads)
├── dnaapler/                             # dnaapler reorientation (if enabled)
├── patch/                                # RagTag patch (if --fill_gaps_from_ref)
├── annotation_transfer/                  # (if --reference_gff)
│   ├── megagene_filter_reference/        # megagene filter results
│   ├── megagene_filter_vendor/           # (if --vendor_gff)
│   ├── liftoff_reference/               # Liftoff output + AGAT-cleaned GFF
│   ├── liftoff_vendor/                  # (if --vendor_gff)
│   ├── fix_names_reference/             # name fix results (if --fix_generic_names)
│   ├── fix_names_vendor/                # (if --vendor_gff + --fix_generic_names)
│   └── merged/                          # (if --vendor_gff and not --skip_merge)
│       ├── {sample}_merged.gff3
│       └── {sample}_merge_summary.txt
├── qc/
│   └── {sample}_quast_results/
├── final_outputs/                        # Key results
│   ├── {sample}_final.fasta
│   ├── {sample}_reference_liftoff.gff3
│   ├── {sample}_vendor_liftoff.gff3     # if --vendor_gff
│   └── {sample}_merged.gff3            # if vendor merge ran
└── pipeline_info/
    ├── timeline.html
    ├── report.html
    ├── trace.txt
    └── dag.html
```

### Merge Summary

The merge summary (`{sample}_merge_summary.txt`) reports:
- **Full matches**: Genes matched by both CDS overlap and identifier — merged into single features
- **Partial matches (position only)**: CDS overlap but no shared identifier — both kept, tagged
- **Partial matches (identifier only)**: Shared identifier but no CDS overlap — both kept, tagged
- **Unmatched**: Present in only one source — kept as-is with source tag

Each merged feature is tagged with `annotation_source=merged`, `ref_id=`, and `vendor_id=` attributes. Unmatched and partial features are tagged with `annotation_source=reference` or `annotation_source=vendor`.

## Profiles

| Profile | Description |
|---|---|
| `standard` | Docker + Conda fallback (recommended) |
| `docker` | Docker only |
| `singularity` | Singularity only |
| `singularity_conda` | Singularity + Conda fallback (HPC) |
| `conda` | Conda only |
| `test` | Test defaults (`sample_name=test_sample`, `outdir=test_results`) |

## Requirements

- Nextflow >= 23.04.0
- Docker, Singularity, or Conda for process execution
- Target scale: yeast (~12 Mb, ~6000 genes) and bacterial (~1-10 Mb) genomes
