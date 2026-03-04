# Plan: Annotation Merge Pipeline Refactor

## Context

The current annotation merge pipeline has two problems:

1. **Megagene artifacts**: AGAT's GFF3 fixing sometimes creates spurious mega-genes (gene features spanning hundreds of kb). The current merge logic uses `covered_bases / feature.length` as its overlap metric — but for a 500kb megagene spanning 50 real 1kb genes, the fraction is only ~10%, so the megagene passes through as "novel." The metric is fundamentally wrong for this case.

2. **Priority model loses information**: The merge forces one source as "priority" (kept unconditionally) and filters the other. This can't represent "both sources annotate the same gene but the vendor has a better product name" — you either keep the reference's annotation or the vendor's, never the best of both.

**Goal**: Replace the priority-based merge with a symmetric identity-based merge that matches genes across sources, and add a pre-Liftoff megagene filter. Use gffutils (SQLite-backed GFF3 library) for both steps.

---

## Current Pipeline Architecture

This is a Nextflow DSL2 pipeline for microbial scaffold validation. The annotation transfer portion currently works as follows:

```
raw GFF → [fix_blank_attrs] → [AGAT_FIX_GFF]      (in workflow files)
    ↓
[LIFTOFF_REFERENCE] + [LIFTOFF_VENDOR] → [MERGE_ANNOTATIONS] → merged GFF
    (in annotation_transfer subworkflow)
```

### Key existing files:
- `bin/merge_annotations.py` — 667-line Python script, priority-based merge with custom IntervalIndex
- `bin/fix_blank_gff_attributes.py` — fixes AUGUSTUS GFF blank attributes before AGAT
- `modules/local/merge_annotations/main.nf` — runs merge twice (swapped inputs for ref-priority + vendor-priority)
- `modules/local/agat/fix_gff/main.nf` — AGAT GFF3 format fixing
- `modules/local/liftoff/main.nf` — Liftoff annotation transfer
- `subworkflows/local/annotation_transfer.nf` — wires LIFTOFF + MERGE
- `workflows/euk_scaffold_validation.nf` — main pipeline workflow
- `workflows/annotation_transfer_only.nf` — standalone annotation transfer workflow
- `nextflow.config` — all parameters

### Current merge logic (what's being replaced):
- One source is "priority" (kept unconditionally), other is "secondary"
- Secondary features classified by overlap fraction: `covered_bases / feature.length`
- >= 50% overlap → dropped; 10-50% → flagged; <10% → kept as novel
- Module runs script twice with swapped inputs for both priority directions
- Uses `python:3.12` container (stdlib only)
- Has `always_keep_types` for transposable elements (never dropped)
- Identifier matching only used for categorizing WHY something was dropped (redundant/replaced/different_type)

### Conventions:
- Nextflow DSL2: one process per `modules/local/<tool>/main.nf`
- Process names UPPER_SNAKE_CASE, aliased with `include { X as X_VARIANT }`
- Params in `nextflow.config` under `params {}`, underscore naming
- `bin/` scripts auto-added to PATH, Python 3
- Each process has both Docker and Singularity container URIs
- Target scale: yeast (~12 Mb, ~6000 genes) and bacteria (~1-10 Mb)

---

## New Pipeline Flow

```
raw GFF → [fix_blank_attrs] → [AGAT_FIX_GFF]      (in workflows, unchanged)
    ↓
[FILTER_MEGAGENES] → [LIFTOFF] → [FIX_GFF_NAMES] → [MERGE_ANNOTATIONS]
    (in annotation_transfer subworkflow)                    ↓
                                                     single merged GFF
```

Both reference and vendor GFFs go through FILTER_MEGAGENES and FIX_GFF_NAMES independently.

---

## Files to Create

### 1. `bin/filter_megagenes.py`

Removes artifactual mega-genes from a single GFF3 file using gffutils.

**Detection criteria** (both configurable, either triggers removal):
- **Containment count**: A gene whose span overlaps > `--gene-threshold` other gene-level features in the same file. This is the primary signal — real genes overlap 0-2 neighbors; a megagene overlaps dozens. Use `db.region(seqid, start, end, featuretype='gene')` and exclude self.
- **Absolute length**: A gene longer than `--max-length-bp` (optional, disabled when 0).

**Algorithm**:
1. `gffutils.create_db(input, ':memory:', merge_strategy='create_unique')` — in-memory, handles duplicate IDs
2. For each gene: count overlapping genes via `db.region()`, check length
3. Collect megagene IDs; also collect all descendant IDs (via `db.children()`) for removal
4. Write output GFF3, skipping megagenes and their children
5. Write summary: each removed gene's ID, coordinates, length, overlap count

**CLI**:
```
filter_megagenes.py \
    --input input.gff3 \
    --output filtered.gff3 \
    --summary filter_report.txt \
    --gene-threshold 5 \
    [--max-length-bp 0]
```

### 2. `modules/local/filter_megagenes/main.nf`

```groovy
process FILTER_MEGAGENES {
    tag "${gff.baseName}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/megagene_filter_${prefix}", mode: 'copy'

    container  // gffutils BioContainers image (see Container section)

    input:
    path gff
    val prefix  // 'reference' or 'vendor'

    output:
    path "${gff.baseName}_megafiltered.gff3", emit: filtered_gff
    path "${gff.baseName}_megagene_summary.txt", emit: summary

    script:
    def max_len_arg = params.max_gene_length_bp ? "--max-length-bp ${params.max_gene_length_bp}" : ''
    """
    filter_megagenes.py \\
        --input ${gff} \\
        --output ${gff.baseName}_megafiltered.gff3 \\
        --summary ${gff.baseName}_megagene_summary.txt \\
        --gene-threshold ${params.megagene_gene_threshold} \\
        ${max_len_arg}
    """
}
```

### 3. `bin/fix_gff_names.py`

Replaces generic Name attributes with informative alternatives from other fields. Runs post-Liftoff so IGV displays useful labels.

**Algorithm**:
1. Load GFF3 into gffutils DB
2. For each feature with a Name attribute:
   - Check if Name is generic (matches `GENERIC_PATTERN` like `gene-123` or is in `GENERIC_VALUES` like "hypothetical protein")
   - If generic: search for a non-generic value in priority order: `product`, `description`, `locus_tag`, `gene`
   - Also check children: if a gene's Name is generic but a child mRNA/CDS has a non-generic `product`, propagate up
   - If replacement found: set `Name=<replacement>`, store old value in `original_name=<old>`
3. Write output GFF3 and summary (count of renames, before/after for each)

**Shared constants** (duplicated in each script or extracted to a shared module):
```python
IDENTIFIER_KEYS = ('ID', 'Name', 'gene', 'locus_tag', 'product', 'description')

GENERIC_VALUES = {
    'hypothetical protein', 'conserved protein of unknown function',
    'protein of unknown function', 'unnamed protein product',
    'unknown protein', 'uncharacterized protein',
}
GENERIC_PATTERN = re.compile(r'^(gene|cds|mrna|rna|exon)-?\d+$', re.IGNORECASE)
```

**CLI**:
```
fix_gff_names.py \
    --input lifted.gff3 \
    --output names_fixed.gff3 \
    [--summary name_fix_report.txt]
```

### 4. `modules/local/fix_gff_names/main.nf`

```groovy
process FIX_GFF_NAMES {
    tag "${gff.baseName}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/fix_names_${prefix}", mode: 'copy'

    container  // gffutils BioContainers image

    input:
    path gff
    val prefix

    output:
    path "${gff.baseName}_names_fixed.gff3", emit: fixed_gff
    path "${gff.baseName}_name_fix_summary.txt", emit: summary

    script:
    """
    fix_gff_names.py \\
        --input ${gff} \\
        --output ${gff.baseName}_names_fixed.gff3 \\
        --summary ${gff.baseName}_name_fix_summary.txt
    """
}
```

### 5. `bin/merge_annotations.py` (complete rewrite)

Replaces the existing priority-based script with a symmetric identity-based merge.

**Matching logic** (match requires BOTH conditions):
- **Full match**: Reciprocal CDS overlap >= threshold AND at least one identifier cross-match (case-insensitive, any field from one feature matches any field from the other)
- **Partial match (position only)**: CDS overlap met, no identifier match
- **Partial match (identifier only)**: Identifier match found, CDS overlap not met
- **Unmatched**: Neither condition met

**CDS overlap computation** (fixes the megagene problem):
- For each gene, compute its CDS footprint: union of all CDS intervals via `db.children(gene, featuretype='CDS')`
- Reciprocal overlap = `overlap_bases / min(ref_cds_length, vendor_cds_length)`
- This uses actual coding sequence, not gene span — immune to inflated gene boundaries

**Identifier matching**:
- Reuse `IDENTIFIER_KEYS`: ID, Name, gene, locus_tag, product, description
- Reuse `GENERIC_VALUES` and `GENERIC_PATTERN` to exclude generic identifiers
- Collect identifiers from the gene AND all its children (mRNA, CDS may carry product annotations)
- Match is case-insensitive intersection of the two identifier sets
- Record WHICH identifiers matched (for the summary)

**Match resolution** (greedy best-first):
- Sort all full-match candidate pairs by CDS overlap fraction (descending)
- Assign greedily: each gene participates in at most one match
- Remaining genes become unmatched or participate in partial matches

**Output GFF construction**:
- **Matched pairs**: Coordinates from `--coord-preference` source (default: reference). Name/product/description from `--description-preference` source (default: vendor), falling back to the other source if preferred source is generic. All unique attributes from both sources retained. Conflicting attribute values prefixed with `ref_`/`vendor_`. Tagged `annotation_source=merged;ref_id=X;vendor_id=Y`.
- **Partial matches**: Both features kept independently. Tagged with `annotation_source=<source>` and `Note=partial_match:<basis>;overlap_frac=0.XX;matched_ids=<list>;with=<other_id>`.
- **Unmatched**: Kept as-is, tagged `annotation_source=<source>`.
- **always_keep_types**: Features with these types are never dropped. If matched, merged normally. If unmatched, kept.
- Sort all output features by seqid, start position.

**Summary output**:
```
============================================================
ANNOTATION MERGE SUMMARY
============================================================
Reference genes:    N
Vendor genes:       N

Classification:
  Full matches (merged):             N
  Partial matches (position only):   N
  Partial matches (identifier only): N
  Unmatched reference:               N
  Unmatched vendor:                  N

--- FULL MATCHES (N) ---
  ref: chrI:1000-2000 YAL001C [TFC3]
  vnd: chrI:1005-1998 gene-42 [TFC3]
  basis: overlap=0.95, matched_ids: tfc3
  coords_from: reference, description_from: vendor

--- PARTIAL MATCHES: POSITION ONLY (N) ---
  ref: chrII:5000-6000 YBL050W [SEC17]
  vnd: chrII:5010-5990 gene-99 [hypothetical protein]
  basis: overlap=0.92, no identifier match

--- PARTIAL MATCHES: IDENTIFIER ONLY (N) ---
  ...

--- UNMATCHED REFERENCE (N) ---
  chrIII:1000-2000 gene YCL001W [unknown]

--- UNMATCHED VENDOR (N) ---
  chrIV:3000-4000 gene gene-150 [novel transporter]
============================================================
```

**CLI**:
```
merge_annotations.py \
    --reference ref_lifted.gff3 \
    --vendor vendor_lifted.gff3 \
    --output merged.gff3 \
    --summary merge_summary.txt \
    --overlap-threshold 0.50 \
    --coord-preference reference \
    --description-preference vendor \
    [--always-keep-types "transposable_element repeat_region ..."] \
    [--reference-label Reference] \
    [--vendor-label Vendor]
```

---

## Files to Modify

### 6. `modules/local/merge_annotations/main.nf`

Rewrite to single-pass merge with new CLI args and gffutils container.

Key changes:
- Single invocation (no more swapped-input double run)
- New container (gffutils instead of python:3.12)
- New params: `--overlap-threshold`, `--coord-preference`, `--description-preference`
- One merged GFF + one summary (instead of two of each)
- `publishDir` to `final_outputs/` simplified: always publishes the single merged GFF

### 7. `subworkflows/local/annotation_transfer.nf`

Rewrite to wire in new steps:

```
FILTER_MEGAGENES_REFERENCE → LIFTOFF_REFERENCE → [FIX_GFF_NAMES_REFERENCE] ─┐
                                                                              ├→ MERGE_ANNOTATIONS
FILTER_MEGAGENES_VENDOR    → LIFTOFF_VENDOR    → [FIX_GFF_NAMES_VENDOR]    ─┘
```

New includes:
- `FILTER_MEGAGENES as FILTER_MEGAGENES_REFERENCE` / `_VENDOR`
- `FIX_GFF_NAMES as FIX_GFF_NAMES_REFERENCE` / `_VENDOR`

FIX_GFF_NAMES gated by `params.fix_generic_names`.

Updated emits (simplified):
- `lifted_gff`, `unmapped`, `vendor_lifted_gff` — unchanged
- `merged_gff` — single merged GFF (replaces ref_priority_gff / vendor_priority_gff)
- `merge_summary` — single summary (replaces ref/vendor_priority_summary pair)
- Remove: `ref_priority_gff`, `vendor_priority_gff`, `ref_priority_summary`, `vendor_priority_summary`

### 8. `workflows/annotation_transfer_only.nf`

Update emits to match new subworkflow outputs:
- Remove references to `ref_priority_gff`, `vendor_priority_gff`, `ref_priority_summary`, `vendor_priority_summary`
- Replace with `merged_gff`, `merge_summary`

### 9. `workflows/euk_scaffold_validation.nf`

No emit changes needed (doesn't have an emit block), but verify nothing downstream references old priority-based channel names. Currently only references `ANNOTATION_TRANSFER.out.lifted_gff` for QUAST/ASSEMBLY_COMPARISON sequencing barriers.

### 10. `nextflow.config`

**Add** (in the annotation section, around line 48):
```groovy
// ---- Megagene filtering ----
megagene_gene_threshold  = 5      // max overlapping genes before flagging as megagene
max_gene_length_bp       = null   // absolute max gene length in bp (null = disabled)

// ---- Merge settings (identity-based) ----
merge_overlap_threshold  = 0.50   // reciprocal CDS overlap fraction for positional match
coord_preference         = 'reference'  // which source's coordinates for matched pairs
description_preference   = 'vendor'     // which source's description for matched pairs

// ---- Name cleanup ----
fix_generic_names        = true   // replace generic Name attrs with informative alternatives post-Liftoff
```

**Remove**: `merge_priority = 'reference'`

**Keep unchanged**: `always_keep_types`, `skip_merge`, `blank_gff_attributes`, `fix_reference_gff`, `fix_vendor_gff`

---

## Container

All three gffutils-based processes (FILTER_MEGAGENES, FIX_GFF_NAMES, MERGE_ANNOTATIONS) use the same container:

```groovy
container "${ workflow.containerEngine == 'singularity' ?
    'https://depot.galaxyproject.org/singularity/gffutils:0.13--pyh7cba7a3_0' :
    'quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0' }"
```

Verify availability before implementation. Fallback: custom Dockerfile with `pip install gffutils` on `python:3.12`.

---

## Implementation Order

1. `nextflow.config` — add new params (keep `merge_priority` temporarily)
2. `bin/filter_megagenes.py` + `modules/local/filter_megagenes/main.nf` — new, no dependencies broken
3. `bin/fix_gff_names.py` + `modules/local/fix_gff_names/main.nf` — new, independent
4. `bin/merge_annotations.py` — complete rewrite (riskiest change)
5. `modules/local/merge_annotations/main.nf` — update to match new script
6. `subworkflows/local/annotation_transfer.nf` — wire everything together
7. `workflows/annotation_transfer_only.nf` — update emits
8. `workflows/euk_scaffold_validation.nf` — verify, no changes likely needed
9. `nextflow.config` — remove `merge_priority`

---

## Verification

1. **Container check**: `docker pull quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0` — confirm it exists and has gffutils importable
2. **filter_megagenes.py unit test**: Create a synthetic GFF3 with one normal gene and one megagene spanning 10 others. Run the script, verify the megagene is removed and the normal gene is kept.
3. **fix_gff_names.py unit test**: Create a GFF3 with `Name=gene-1;product=TFC3`. Run the script, verify Name becomes TFC3.
4. **merge_annotations.py unit test**: Create two GFF3s:
   - One gene present in both with same locus_tag but different coordinates → should be a full match
   - One gene in ref only → should be unmatched reference
   - One gene in vendor only → should be unmatched vendor
   - Two genes overlapping positionally but with different identifiers → should be a partial match (position only)
5. **Nextflow dry run**: `nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY -preview` — verify DAG shows the new steps in correct order
6. **Full integration**: Run on yeast-scale data with both reference and vendor GFFs. Check:
   - Megagene filter summary shows any removed artifacts
   - Name fix summary shows renamed features
   - Merge summary categorizes all genes correctly
   - Output GFF3 is valid (load in IGV or validate with `gt gff3validator`)
