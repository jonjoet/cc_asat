# Plan: Make reference_gff and vendor_gff fully optional

## Context

The pipeline currently requires `reference_gff` to run any annotation transfer. A stale branch (`claude/handle-missing-reference-gff-d0NJg`) attempted to fix this but is 9 commits behind main and had gaps (didn't update `annotation_transfer_only.nf`, dropped `run_vendor_liftoff`, and made an unnecessary QUAST change). Instead of rebasing, we'll reimplement the feature cleanly on main.

**Goal:** Support all 4 GFF input configurations in both entry points:

| Config | reference_gff | vendor_gff | Behavior |
|--------|--------------|------------|----------|
| Both | provided | provided | Full pipeline (current) |
| Ref only | provided | null | Reference liftoff only (current) |
| Vendor only | null | provided | Vendor liftoff only, no merge |
| Neither | null | null | No annotation transfer |

## Changes (4 files)

### 1. `subworkflows/local/annotation_transfer.nf` — core change

- Move `ch_ref_lifted`, `ch_ref_unmapped` initialization to `Channel.empty()` at top of `main:`, alongside the existing empty-channel initializations for copies/merge/vendor
- Wrap the entire reference block (megagene filter → primary liftoff → name fix → copies liftoff → copy report) in `if (reference_gff) { ... }`
- Inside that guard, assign `ch_ref_unmapped = LIFTOFF_REFERENCE.out.unmapped`
- Add `&& reference_gff` to the merge guard (line 86): `if (!params.skip_merge && reference_gff)` — prevents merge in vendor-only mode
- Change emits: `lifted_gff = ch_ref_lifted` and `unmapped = ch_ref_unmapped` (channel variables, not direct process outputs)

### 2. `workflows/euk_scaffold_validation.nf`

- Line 72: Broaden condition to `(params.reference_gff || params.vendor_gff) && !params.skip_annotation_transfer`
- Pass `null` (not `NO_GFF` sentinel) as `reference_gff` to ANNOTATION_TRANSFER when absent: `ch_reference_gff_for_transfer = params.reference_gff ? ch_reference_gff : null`
- Keep `ch_reference_gff` with `NO_GFF` sentinel for QUAST (already works)
- Fix QUAST sync: use `.mix().first()` across `lifted_gff` and `vendor_lifted_gff` so QUAST waits for whichever output exists

### 3. `workflows/annotation_transfer_only.nf`

- Make `ch_reference_gff_raw` conditional (NO_GFF sentinel when absent), same pattern as euk_scaffold_validation
- Guard AGAT fix on `params.reference_gff && params.fix_reference_gff`
- Pass null for reference_gff to ANNOTATION_TRANSFER when absent
- Same `.mix().first()` QUAST sync pattern

### 4. `main.nf`

- Lines 56-58: Change ANNOTATION_TRANSFER_ONLY validation from requiring `--reference_gff` to requiring at least one of `--reference_gff` or `--vendor_gff`

## Key design decisions

- **null vs NO_GFF sentinel**: ANNOTATION_TRANSFER receives `null` for absent reference_gff (triggers Nextflow `if (reference_gff)` guards). QUAST receives `NO_GFF` sentinel path (it needs a path-type input and checks the filename).
- **QUAST sync via `.mix().first()`**: When only vendor runs, `lifted_gff` is `Channel.empty()`. Mixing with `vendor_lifted_gff` and taking `.first()` gives a sync barrier regardless of which config is active.
- **No QUAST module changes**: The existing `stageAs: 'reference.gff'` and `NO_GFF` check work correctly for all configs.
- **Preserves `run_vendor_liftoff`**: The old branch dropped this; we keep it for the annotation_transfer_only case where assembly is unchanged.

## Verification

- `nextflow run main.nf -preview -profile docker` with each of the 4 GFF configs (both entry points = 8 cases)
- Confirm QUAST, LIFTOFF, MERGE processes appear/absent as expected in each preview
- Full run on small test data for at least the vendor-only config (the novel case)
