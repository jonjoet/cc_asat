# Novel-Only Merge Mode

## Motivation

The pipeline was designed for single-pass use: take a reference and vendor annotation, merge them onto a new assembly. But a natural use case is **iterative refinement** — feeding the pipeline's own merged GFF and final FASTA back as the reference for a subsequent run with a new vendor annotation.

The full symmetric merge is not safe for this because it was not designed to be idempotent. Specifically:

### Problems with full merge on re-entry

1. **Stale `vendor_*`/`ref_*` prefixed attributes**: When attributes conflict during merge, the script creates prefixed copies (e.g. `vendor_Name`, `ref_product`). On a second run, the merged gene (now the "reference") carries these from Run 1. If the new vendor happens to agree on an attribute value, the old prefixed attribute persists — now referring to a gene from a previous run.

2. **`Note` accumulation**: Partial match Notes are appended (`existing_notes.append(extra_note)`), so genes that are partial matches in multiple rounds accumulate stacked Notes from each round.

3. **Duplicate features from partial matches**: Partial matches keep both the reference and vendor copy at the same locus. When this merged GFF is used as a new reference, both copies are lifted, creating progressively more duplicates with each round.

4. **ID mangling**: gffutils `merge_strategy='create_unique'` appends `_0`, `_1` suffixes to duplicate IDs. Partial-match duplicates from previous rounds collide, producing IDs like `gene-ABC_liftoff_0_0_0` after several rounds.

5. **AGAT megagene risk**: AGAT's sequential fallback parser can create encompassing parent genes from the duplicated/overlapping features that came out of a previous merge.

6. **`original_name` persistence**: `fix_gff_names.py` stores the old name in `original_name`. This persists across rounds but doesn't cause functional problems.

## Solution: `--novel-only` flag

The `--novel-only` flag (`--merge_novel_only` in Nextflow params) changes the merge output strategy:

- **Reference features**: All pass through unchanged with `annotation_source=reference`. No merging, no metadata injection, no Notes.
- **Matched vendor features** (full match, partial-position, partial-identifier): Dropped — the reference already covers them.
- **Unmatched vendor features**: Added with `annotation_source=vendor` — these are genuinely novel.

The matching/classification logic still runs identically so the summary reports what matched and what didn't. This is valuable for understanding what the vendor annotation covers relative to the reference, even though the matched vendor features are not emitted.

### What it does NOT change

- `--coord-preference` and `--description-preference` are accepted but ignored (no merging occurs).
- The vendor liftoff still runs upstream (it is independent of the merge step), so the lifted vendor GFF is still available as a separate output for inspection.
- `--skip-merge` remains orthogonal: it skips the merge process entirely, while `--novel-only` runs the merge process in a restricted output mode.

## Companion flag: `--fix_generic_names false`

For iterative runs, `--fix_generic_names false` should also be set. The `fix_gff_names.py` script uses gffutils to load the Liftoff output, but gffutils' `create_unique` merge strategy has a single-retry bug: when a duplicate ID is encountered, it tries one suffixed alternative (`_1`), and if that also exists, it crashes with `UNIQUE constraint failed`. This happens when Liftoff's `-copies` flag produces child features with duplicate IDs across gene copies. Since names were already fixed in the previous run, re-fixing is unnecessary anyway.

## Implementation

Three files changed:

- `bin/merge_annotations.py`: Added `--novel-only` argparse flag. `build_output_lines()` has a `novel_only` branch that emits reference features as-is and only appends unmatched vendor features. `write_summary()` notes the mode in its header.
- `nextflow.config`: Added `merge_novel_only = false` param.
- `modules/local/merge_annotations/main.nf`: Passes `--novel-only` when param is set.
