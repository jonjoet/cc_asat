# Liftoff Iterative Annotation Pipeline: Handling Copies

## Problem

Running Liftoff iteratively (genome A → B → C) for genome scaffolding and annotation creates layers of duplicate features. The copy name suffixes (e.g., `_0`, `_1`) stack across rounds, producing IDs like `gene1_0_0`, which conflict with gffutils and break downstream processing.

## Solution: Two Parallel Runs per Round

The simplest and most robust approach is to run Liftoff twice at each step — once with `-copies` for analysis, and once without for the next transfer:

### Workflow

1. Run Liftoff **with** `-copies` from genome A → B — keep this output for copy-number analysis
2. Run Liftoff **without** `-copies` from genome A → B — use this clean output as the reference annotation for the next round (B → C)
3. Repeat

This avoids suffix stacking entirely and eliminates the need for a postprocessing script to strip copies from the GFF. Both outputs are produced natively by Liftoff, so there's no risk of a filtering bug silently mangling parent-child relationships.

### Tradeoff: Runtime

The run without `-copies` should be noticeably faster than the one with, since the copy-finding step (which iteratively repeats the alignment process until no more copies are found) is the expensive part. Whether the doubled runtime matters depends on genome size and the number of pipeline rounds.

### Verification

Confirm that primary annotations are identical between the two runs. They should be, since copy-finding occurs after the initial liftover and shouldn't affect primary placements. Verify by diffing the two outputs (filtering out `extra_copy_number` lines from the copies version). If they match on the first round, the two-run approach can be trusted going forward.

### Alternative: Single Run + Postprocessing

If runtime is a concern, an alternative is to run once with `-copies` and strip copies in postprocessing. A simple filter drops any GFF line containing the `extra_copy_number` attribute:

```python
def strip_copies(input_gff, output_gff):
    with open(input_gff) as fin, open(output_gff, 'w') as fout:
        for line in fin:
            if line.startswith('#'):
                fout.write(line)
                continue
            if 'extra_copy_number' in line:
                continue
            fout.write(line)
```

For correctness, a more robust version should also remove child features whose `Parent` points to a copy. Collect all copy feature IDs first, then filter out any feature whose ID or Parent matches a copy. The two-run approach is preferred because it avoids this complexity.

## Determinism of Copy Detection

Liftoff's copy detection is deterministic given the same inputs (reference genome, target genome, reference annotation, and parameters). Copies are identified via minimap2 alignment, so identical inputs will produce identical copy calls.

**Caveat:** If the target assembly changes between scaffolding rounds (contigs joined, gaps filled, bases corrected), copy locations can shift or disappear. This is expected.

## The `-sc` Parameter

The `-sc` flag sets the minimum exon/CDS sequence identity threshold for a hit to be classified as a copy. Key details:

- **Default:** 1.0 (100% identity required)
- **Must be greater than `-s`** (the general alignment identity threshold, default 0.5)
- The default of 1.0 is very strict and brittle across iterative rounds — a single base change in an exon can cause a copy to drop below threshold and silently disappear

### How `-sc` Is Applied

The `-sc` threshold is an **absolute threshold** applied independently to each secondary alignment hit. It is *not* a measure of similarity to the best hit. Liftoff computes the exon/CDS sequence identity for each alignment location against the reference gene sequence, and any secondary hit meeting or exceeding `-sc` is called as a copy.

After the initial liftover, Liftoff repeats the alignment process for all genes. An extra copy is annotated at a locus if it does not overlap any previously annotated feature and meets the `-sc` threshold. This process repeats until all valid mappings are found.

### Interaction Between `-s` and `-sc`

The primary (best) hit is the alignment that maximizes sequence identity — no secondary hit can exceed it. This means:

- `-s` gates the initial primary liftover (default 0.5)
- `-sc` gates copy detection afterward (default 1.0)
- Since copies can never have higher identity than the primary, the default `-sc 1.0` effectively requires the primary hit itself to be at or near 100% identity for any copies to be found at all
- With defaults, if the primary hit lands at 95% identity, *no copies can ever be called*, regardless of how many good secondary hits exist — because none can reach 100%

This makes the default `-copies` behavior extremely conservative. It really only catches exact duplications in highly conserved regions. For anything with meaningful divergence, `-copies` with default `-sc` is effectively a no-op.

### Recommended Settings

| Project | `-sc` Value | Source |
|---------|-------------|--------|
| T2T CHM13 annotation (JHU) | 0.95 | Liftoff v1.6.3, RefSeq r110 |
| UW Genome Browser T2T track | 0.85 | GenCode r35 liftover |

**Recommendation for iterative pipelines:** Set `-sc` explicitly (e.g., 0.95) and keep it consistent across all rounds. Choose `-sc` based on the identity range your primary hits typically land at — if primaries are around 95%, then `-sc 0.90` gives reasonable headroom to catch slightly more divergent copies.

## Additional Notes

- The primary (best-hit) feature retains the original ID; only extra copies get suffixed IDs and the `extra_copy_number` attribute.
- If gffutils still chokes on primary features, try `merge_strategy="merge"` in `gffutils.create_db()` or pre-sanitize the GFF with `genometools` (`gt gff3`).
- Consider LiftOn as an alternative for cross-species transfers — it combines DNA and protein alignments for improved accuracy on divergent genomes.
