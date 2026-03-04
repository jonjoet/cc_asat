# Plan: Merge Annotation Enhancements (4 Issues)

## Context

The pipeline merges reference and vendor (Plasmidsaurus) GFF3 annotations onto a scaffolded assembly. Currently, the merge always gives reference priority, produces minimal summary info, and doesn't publish AGAT-cleaned intermediate GFFs. Four enhancements are needed:

1. Produce **both** merge directions (ref-priority + vendor-priority), with a param to select the "primary"
2. **Publish AGAT-cleaned GFFs** alongside their downstream Liftoff outputs
3. **Richer merge summary** with gene names, functions, locations, overlap partners, and categorized dropped annotations
4. **Gene function info in partial-overlap notes** in the GFF attributes

## User requirements / refinements

- **stageAs safety**: Use stageAs when needed to avoid collisions between input and output names when running the merge step twice. The current stageAs directives (`ref_liftoff_output.gff3`, `vendor_liftoff_output.gff3`) are safe since output names are different.
- **Redundancy matching**: Don't rely only on Name. Collect ALL possible identifiers from both overlapping features (ID, Name, gene, locus_tag, product, description) and call them redundant if ANY value from one set matches ANY from the other (case-insensitive). Filter out generic values like "hypothetical protein" and auto-generated patterns like "gene-1".

---

## Phase 1: Enrich `merge_annotations.py` (Issues 3 + 4)

**File:** `bin/merge_annotations.py`

### 1a. Add identifier/description helpers to `GFFFeature`

Add constants at module level:

```python
IDENTIFIER_KEYS = ('ID', 'Name', 'gene', 'locus_tag', 'product', 'description')

GENERIC_VALUES = {
    'hypothetical protein', 'conserved protein of unknown function',
    'protein of unknown function', 'unnamed protein product',
    'unknown protein', 'uncharacterized protein',
}
GENERIC_PATTERN = re.compile(r'^(gene|cds|mrna|rna|exon)-?\d+$', re.IGNORECASE)
```

Add two methods to `GFFFeature`:

- `get_identifiers(self) -> set[str]`: Collect values from all `IDENTIFIER_KEYS`, lowercase, exclude generics and auto-generated IDs matching `GENERIC_PATTERN`. Returns a set for intersection checks.
- `get_description(self) -> str`: Return best human-readable label — tries `product`, `description`, `Name`, `ID` in order, returns first non-None non-generic value or `'unknown'`.

### 1b. Add `OverlapResult` dataclass and enrich `classify_vendor_feature`

```python
@dataclass
class OverlapResult:
    classification: str          # 'drop', 'flag', 'keep'
    overlap_fraction: float      # 0.0-1.0
    overlapping_features: list   # list of GFFFeature from reference
```

Update `classify_vendor_feature` to return `OverlapResult` instead of a bare string. The overlapping features come from the `IntervalIndex.overlap()` call — the `data` field already stores the feature.

### 1c. Update `filter_novel_features` to carry overlap details

Change the return lists from `(top_feat, children)` tuples to `(top_feat, children, overlap_result)` triples.

**Issue 4 implementation:** When `classification == 'flag'`, build a richer Note:
```
Note=partial_overlap_with_reference:REF_NAME(ref_product);overlap_frac=0.35
```
Where `REF_NAME` and `ref_product` come from the overlapping reference features. If multiple overlapping features, comma-separate them.

### 1d. Add redundancy categorization for dropped features

Add a function:
```python
def categorize_dropped(vendor_feat, overlap_result) -> str:
```

Logic:
- Collect identifiers from vendor feature AND from ALL overlapping reference features
- If **any identifier cross-matches** (case-insensitive intersection is non-empty) → `'redundant'`
- Else if vendor feature type == overlapping reference feature type → `'replaced'` (same type, different gene)
- Else → `'different_type'` (e.g., vendor transposon overlapping reference gene)

### 1e. Rewrite `print_summary`

New structure:

```
============================================================
ANNOTATION MERGE SUMMARY
============================================================

Liftoff (reference) features:    N
Vendor features processed:       N gene groups

Vendor classification:
  Novel (no significant overlap):    N
  Flagged (partial overlap):         N
  Dropped (covered by reference):    N
    - Redundant (identifier match):  N
    - Replaced (same type, diff ID): N
    - Different type:                N

--- DROPPED: REDUNDANT (N) ---
  seqid:start-end(strand)  type  vendor_ID  [product]
    overlaps: ref_ID [ref_product] at seqid:start-end  (overlap: NN%)

--- DROPPED: REPLACED (N) ---
  (same format)

--- DROPPED: DIFFERENT TYPE (N) ---
  (same format)

--- FLAGGED (N) ---
  seqid:start-end(strand)  type  vendor_ID  [product]
    overlaps: ref_ID [ref_product]  (overlap: NN%)

--- NOVEL (N) ---
  seqid:start-end(strand)  type  vendor_ID  [product]

Novel feature types:
  gene: N
  transposable_element: N
  ...
============================================================
```

Each feature entry shows: `seqid:start-end(strand) ftype Name/ID [product/description]`.
For dropped/flagged: also shows what reference feature(s) it overlapped and the overlap fraction.

### 1f. Update `write_merged_gff` and `main()`

Update `write_merged_gff` to handle the new tuple shape (ignore the overlap_result when writing).
Wire the enriched data through `main()`. No new CLI arguments needed for issues 3/4.

---

## Phase 2: Both merge directions (Issue 1)

### 2a. `nextflow.config`

Add parameter:
```groovy
merge_priority = 'reference'  // 'reference' or 'vendor' — which merged GFF goes to final_outputs/
```

### 2b. `modules/local/merge_annotations/main.nf`

Rewrite the script block to call `merge_annotations.py` twice:

```bash
# Reference-priority merge (current behavior)
merge_annotations.py \
    --liftoff ref_liftoff_output.gff3 \
    --vendor vendor_liftoff_output.gff3 \
    --output ${params.sample_name}_ref_priority_merged.gff3 \
    --summary ${params.sample_name}_ref_priority_merge_summary.txt \
    ${always_keep_arg}

# Vendor-priority merge (swapped inputs)
merge_annotations.py \
    --liftoff vendor_liftoff_output.gff3 \
    --vendor ref_liftoff_output.gff3 \
    --output ${params.sample_name}_vendor_priority_merged.gff3 \
    --summary ${params.sample_name}_vendor_priority_merge_summary.txt \
    ${always_keep_arg}
```

**Staging is safe** — inputs have fixed staged names (`ref_liftoff_output.gff3`, `vendor_liftoff_output.gff3`), outputs have distinct names.

Update outputs to emit all 4 files:
```groovy
output:
path "${params.sample_name}_ref_priority_merged.gff3",          emit: ref_priority_gff
path "${params.sample_name}_vendor_priority_merged.gff3",       emit: vendor_priority_gff
path "${params.sample_name}_ref_priority_merge_summary.txt",    emit: ref_priority_summary
path "${params.sample_name}_vendor_priority_merge_summary.txt", emit: vendor_priority_summary
```

Update publishDir:
- Both GFFs + summaries always go to `annotation_transfer/merged/`
- The "primary" GFF (based on `merge_priority` param) also goes to `final_outputs/` via `saveAs`:

```groovy
publishDir "${params.outdir}/annotation_transfer/merged", mode: 'copy'
publishDir "${params.outdir}/final_outputs", mode: 'copy', saveAs: { filename ->
    if (params.merge_priority == 'reference' && filename.contains('ref_priority_merged.gff3')) return filename
    if (params.merge_priority == 'vendor' && filename.contains('vendor_priority_merged.gff3')) return filename
    return null
}
```

### 2c. `subworkflows/local/annotation_transfer.nf`

Update emit channels to expose both GFFs. Add a `merged_gff` convenience channel that selects the primary based on `params.merge_priority`:
```groovy
ch_merged_gff = params.merge_priority == 'vendor'
    ? MERGE_ANNOTATIONS.out.vendor_priority_gff
    : MERGE_ANNOTATIONS.out.ref_priority_gff
```

---

## Phase 3: Publish AGAT-cleaned GFFs (Issue 2)

### 3a. `modules/local/agat/fix_gff/main.nf`

Add `val prefix` input and publishDir:

```groovy
process AGAT_FIX_GFF {
    tag "${gff.baseName}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/liftoff_${prefix}", mode: 'copy'

    input:
    path gff
    val prefix

    output:
    path "${gff.baseName}_fixed.gff3", emit: fixed_gff
    ...
}
```

### 3b. `workflows/euk_scaffold_validation.nf`

Update AGAT calls to pass prefix:
```groovy
AGAT_FIX_REFERENCE_GFF(ch_reference_gff_raw, 'reference')
AGAT_FIX_VENDOR_GFF(ch_vendor_gff_raw, 'vendor')
```

### 3c. `workflows/annotation_transfer_only.nf`

Same change:
```groovy
AGAT_FIX_REFERENCE_GFF(ch_reference_gff_raw, 'reference')
AGAT_FIX_VENDOR_GFF(ch_vendor_gff_raw, 'vendor')
```

---

## Files Modified (Summary)

| File | Issues | Phase |
|------|--------|-------|
| `bin/merge_annotations.py` | 3, 4 | 1 |
| `modules/local/merge_annotations/main.nf` | 1 | 2 |
| `modules/local/agat/fix_gff/main.nf` | 2 | 3 |
| `subworkflows/local/annotation_transfer.nf` | 1 | 2 |
| `workflows/euk_scaffold_validation.nf` | 2 | 3 |
| `workflows/annotation_transfer_only.nf` | 2 | 3 |
| `nextflow.config` | 1 | 2 |

## Implementation order

Phase 1 → Phase 2 → Phase 3 (Phase 3 is independent but cleanest last)

---

## Status: ALL PHASES COMPLETE

### Phase 1: COMPLETE
All changes implemented in `bin/merge_annotations.py`:
- Added `IDENTIFIER_KEYS`, `GENERIC_VALUES`, `GENERIC_PATTERN` constants
- Added `GFFFeature.get_identifiers()` and `GFFFeature.get_description()` methods
- Added `OverlapResult` dataclass
- `classify_vendor_feature` now returns `OverlapResult` (single `index.overlap()` call, no separate `compute_overlap_fraction`)
- `filter_novel_features` returns `(top_feat, children, overlap_result)` triples; flagged features get enriched Notes with ref names and overlap fractions
- Added `categorize_dropped()` — classifies as redundant/replaced/different_type
- Rewrote `print_summary()` with detailed per-feature sections and subcategories
- Updated `write_merged_gff` and `main()` to handle new triple format
- Smoke-tested with synthetic GFF data — produces valid GFF3 and enriched summary
- No new CLI arguments; fully backward compatible

### Phase 2: COMPLETE
- Added `merge_priority = 'reference'` param to `nextflow.config`
- Rewrote `modules/local/merge_annotations/main.nf`: calls merge script twice (ref-priority + vendor-priority), emits 4 outputs, publishDir uses saveAs to select primary GFF for `final_outputs/`
- Updated `subworkflows/local/annotation_transfer.nf`: exposes both priority GFFs + summaries, adds `merged_gff` convenience channel selected by `params.merge_priority`
- Updated `workflows/annotation_transfer_only.nf` emit block to expose new channels

### Phase 3: COMPLETE
- Added `val prefix` input and `publishDir` to `modules/local/agat/fix_gff/main.nf` — publishes to `annotation_transfer/liftoff_${prefix}/`
- Updated AGAT calls in `workflows/euk_scaffold_validation.nf` to pass `'reference'` / `'vendor'` prefix
- Updated AGAT calls in `workflows/annotation_transfer_only.nf` to pass `'reference'` / `'vendor'` prefix
