# Project: cc_asat (Annotation-aware Scaffold Assembly Tool)

Nextflow DSL2 pipeline for microbial scaffold validation. Supports both fungal and bacterial genomes. Scaffolds a de novo assembly against a reference, gap-closes, optionally reorients circular contigs (dnaapler), transfers annotations with identity-based merging, and runs QC.

## Repository Layout

```
main.nf                          # Entry points: EUK_SCAFFOLD_VALIDATION, ANNOTATION_TRANSFER_ONLY
nextflow.config                  # All params, resource config, profiles
workflows/                       # Top-level workflow files
subworkflows/local/              # Reusable subworkflows (scaffolding, gap_closing, annotation_transfer)
modules/local/<tool>/main.nf     # One process per module (DSL2 convention)
bin/                             # Python helper scripts (auto-added to PATH by Nextflow)
claude_context/                  # Implementation plans and design context (not used by the pipeline)
```

## Conventions

- **Nextflow DSL2**: Each process is in its own `modules/local/<tool>/main.nf`. Subworkflows compose processes. Workflows compose subworkflows.
- **Process naming**: Process names are UPPER_SNAKE_CASE. When aliasing the same process (e.g. AGAT for reference vs vendor), use `include { X as X_VARIANT }`.
- **Params**: All parameters are defined in `nextflow.config` under `params {}`. Use underscore naming (`sample_name`, not `sampleName`). Params that accept space-separated lists (like `merge_skip_types`) are passed as strings.
- **bin/ scripts**: Python 3 scripts in `bin/` are automatically on PATH inside Nextflow processes. The gffutils-based scripts (`filter_megagenes.py`, `fix_gff_names.py`, `merge_annotations.py`) run in the gffutils BioContainers image. They write progress to stderr and data to stdout/files.
- **publishDir**: Intermediate results go to descriptive subdirectories under `${params.outdir}/`. Key results are also copied to `final_outputs/` using `saveAs` filters.
- **Containers**: Each process specifies both Docker and Singularity container URIs. Bioinformatics tools use BioContainers. The three gffutils-based annotation processes share `quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0`.

## Annotation Transfer Architecture

The annotation transfer subworkflow runs this pipeline for both reference and vendor GFF inputs independently:

```
GFF → FILTER_MEGAGENES → LIFTOFF → [FIX_GFF_NAMES] → MERGE_ANNOTATIONS
```

### Megagene Filtering (`bin/filter_megagenes.py`)
Pre-Liftoff step that removes artifactual mega-genes (e.g. from AGAT's sequential fallback parser). Detection criteria: gene overlapping more than `--gene-threshold` other genes, or exceeding `--max-length-bp`. Uses gffutils `db.region()`.

### Name Fixing (`bin/fix_gff_names.py`)
Post-Liftoff step (gated by `params.fix_generic_names`) that replaces generic Name attributes (e.g. `gene-1`, `hypothetical protein`) with informative alternatives found in `product`, `description`, `locus_tag`, or `gene` fields. Checks both the feature and its children.

### Annotation Merge (`bin/merge_annotations.py`)
Symmetric identity-based merge of reference and vendor lifted GFFs. This is the most complex custom script:

- **Matching requires both**: reciprocal CDS overlap >= threshold AND shared identifier (case-insensitive)
- **CDS footprint overlap**: Uses union of CDS intervals (not gene span), immune to inflated gene boundaries
- **Identifier matching**: Collects from gene + all descendants, excludes generic values
- **Greedy resolution**: Full match candidates sorted by overlap fraction, assigned best-first
- **Classification**: Full match (merged), partial match (position or identifier only, both kept), unmatched (kept as-is)
- **Merged features**: Coordinates from `--coord-preference` source, descriptions from `--description-preference` source with fallback
- Single merged GFF + detailed summary (replaces the old dual ref-priority/vendor-priority approach)

### Shared Constants
`GENERIC_VALUES`, `GENERIC_PATTERN`, and `IDENTIFIER_KEYS` are defined independently in both `fix_gff_names.py` and `merge_annotations.py`.

## Testing

The production environment is Docker-only, so tests should run inside Docker where possible. Use `quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0` for the three gffutils-based scripts and `python:3.12` for any stdlib-only scripts.

Test pattern for Python scripts:
```bash
docker run --rm \
  -v /path/to/test/data:/data \
  -v /path/to/repo/bin:/scripts \
  quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0 \
  python3 /scripts/my_script.py --input /data/test.gff3 ...
```

For Nextflow changes: use `-profile docker` with `-preview` for a dry run, or run the full pipeline on small synthetic data with `-profile docker`.

The pipeline targets yeast-scale genomes (~12 Mb, ~6000 genes) and bacterial genomes (~1-10 Mb).
