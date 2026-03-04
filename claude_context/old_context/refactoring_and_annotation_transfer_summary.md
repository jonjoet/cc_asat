# Refactoring + Annotation Transfer: Design Summary

## What Was Done

The pipeline was refactored from a monolithic `main.nf` + multi-process module files into nf-core-style modularity, and annotation transfer via Liftoff was added as a new optional feature.

---

## Design Intent

### 1. Structural Refactoring

**Goal**: Adopt nf-core conventions for maintainability — one process per file, subworkflows grouping related steps, a thin `main.nf` entry point, and a `workflows/` orchestration layer.

**Scope**: Structural only. No logic changes to existing processes. No meta maps, no `versions.yml` (not needed for this project).

**Target layout:**
```
main.nf                                  # validate inputs, call workflow
workflows/euk_scaffold_validation.nf     # orchestration
subworkflows/local/
  scaffolding.nf
  gap_closing.nf
  annotation_transfer.nf
  assembly_comparison.nf
modules/local/<tool>/main.nf             # one process per file
bin/
  generate_summary.py                    # pre-existing
  merge_annotations.py                   # new
```

### 2. Annotation Transfer

**Goal**: Transfer gene annotations from a reference genome (and optionally a vendor annotation) onto the final assembly, using Liftoff for coordinate remapping via alignment.

**Why Liftoff instead of AGP remapping**: Gap closing (TGS-Gapcloser) changes scaffold lengths (e.g., replacing 100 Ns with 5 bp of real sequence). This invalidates RagTag's AGP coordinate tables for the final assembly. Liftoff re-aligns source features against the target assembly directly, so it works correctly regardless of any gap-filling that occurred.

**Why Liftoff twice**: The same Liftoff process (with aliases `LIFTOFF_REFERENCE` and `LIFTOFF_VENDOR`) is used for both transfers:
- `LIFTOFF_REFERENCE`: reference genome → final assembly (always runs when `--reference_gff` provided)
- `LIFTOFF_VENDOR`: original de novo assembly → final assembly (runs only when `--vendor_gff` provided)

Both outputs end up in final-assembly coordinates. This makes the merge step trivial — no AGP parsing needed.

---

## Key Design Decisions

### NUCDIFF runs after annotation transfer (not in parallel)

**Rationale**: The plan calls for GENERATE_SUMMARY to eventually incorporate annotation info (e.g., newly added genes from vendor annotations). To set this up correctly from the start, NUCDIFF is placed downstream of annotation transfer via a channel dependency.

**Implementation**: When annotation transfer runs, `ch_final` is combined with the `ANNOTATION_TRANSFER.out.lifted_gff` channel before being passed to `ASSEMBLY_COMPARISON`. This forces Nextflow to wait for annotation transfer to complete before dispatching NUCDIFF.

```groovy
ch_final_for_comparison = ch_final
    .combine(ANNOTATION_TRANSFER.out.lifted_gff)
    .map { it[0] }
ASSEMBLY_COMPARISON(ch_reference, ch_final_for_comparison)
```

When annotation transfer is skipped, `ch_final` passes directly to `ASSEMBLY_COMPARISON` with no delay.

### QUAST runs in parallel

QUAST is not part of the annotation transfer or comparison chain. It receives `ch_final` directly and runs in parallel with everything downstream.

### Annotation transfer is opt-in, merge is opt-in-within-opt-in

- Annotation transfer activates when `--reference_gff` is provided AND `--skip_annotation_transfer` is not set.
- Vendor merge additionally requires `--vendor_gff`.
- This gives three operating modes:
  1. No annotation transfer (no `--reference_gff`, or `--skip_annotation_transfer`)
  2. Reference-only Liftoff (`--reference_gff`)
  3. Full merge (`--reference_gff --vendor_gff`)

### merge_annotations.py: AGP code removed

The source script (`claude_context/novel_annotation_transfer.py`) included AGP parsing and coordinate remapping logic. This was stripped out entirely in `bin/merge_annotations.py` because both input GFFs are already in the same coordinate space (the final assembly) when they arrive from Liftoff.

**Kept from original**:
- `IntervalIndex` class
- `GFFFeature` dataclass
- `parse_gff()`, `build_interval_index()`, `collect_gene_groups()`, `_collect_descendants()`
- `filter_novel_features()` with `always_keep_types` override (critical for transposable elements)
- `write_merged_gff()`, `print_summary()`
- All overlap detection logic (`compute_overlap_fraction`, `classify_vendor_feature`)

**Removed**:
- `AGPEntry` dataclass
- `parse_agp()`
- `remap_vendor_gff()`, `remap_coordinate()`, `remap_feature()`
- `--agp` CLI argument
- `--unplaced-prefix` CLI argument and unplaced contig handling (irrelevant when Liftoff handles placement)

### Liftoff container choice

`quay.io/biocontainers/liftoff:1.6.3--pyhdfd78af_0` — this image includes minimap2 and samtools, which Liftoff requires internally.

---

## Files Changed

| Action  | File |
|---------|------|
| Replace | `main.nf` |
| Edit    | `nextflow.config` (added `vendor_gff`, `skip_annotation_transfer` params) |
| Create  | `workflows/euk_scaffold_validation.nf` |
| Create  | `subworkflows/local/scaffolding.nf` |
| Create  | `subworkflows/local/gap_closing.nf` |
| Create  | `subworkflows/local/annotation_transfer.nf` |
| Create  | `subworkflows/local/assembly_comparison.nf` |
| Create  | `modules/local/samtools/faidx/main.nf` |
| Create  | `modules/local/quast/main.nf` |
| Create  | `modules/local/ragtag/correct/main.nf` |
| Create  | `modules/local/ragtag/scaffold/main.nf` |
| Create  | `modules/local/ragtag/patch/main.nf` |
| Create  | `modules/local/seqtk/fq2fa/main.nf` |
| Create  | `modules/local/tgsgapcloser/main.nf` |
| Create  | `modules/local/nucdiff/main.nf` |
| Create  | `modules/local/generate_summary/main.nf` |
| Create  | `modules/local/liftoff/main.nf` |
| Create  | `modules/local/merge_annotations/main.nf` |
| Create  | `bin/merge_annotations.py` |
| Delete  | `modules/qc.nf` |
| Delete  | `modules/scaffold.nf` |
| Delete  | `modules/gapcloser.nf` |
| Delete  | `modules/compare.nf` |
| Delete  | `modules/reports.nf` |

---

## Verification Checklist

1. **Syntax check**: `nextflow run main.nf -preview` — validates DAG without executing
2. **Regression test**: Run with existing params (assembly + reference + reads, no `--reference_gff`) — outputs should match previous run
3. **Liftoff-only test**: `--reference_gff ref.gff3` — verify `results/annotation_transfer/liftoff/liftoff_output.gff3`
4. **Full annotation transfer test**: `--reference_gff ref.gff3 --vendor_gff vendor.gff` — verify both Liftoff runs and `results/annotation_transfer/merged/merged_annotations.gff3`
5. **Skip flag test**: `--reference_gff ref.gff3 --skip_annotation_transfer` — QUAST gets the GFF but Liftoff does NOT run
6. **Ordering check**: Confirm in trace/timeline that NUCDIFF starts only after annotation transfer completes
