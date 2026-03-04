# Fix Blank GFF Column 9 Attributes (before AGAT)

## Problem

AUGUSTUS outputs GFF with two patterns of blank attributes:

**Pattern A** — gene line blank, transcripts have real attributes:
```
contig_24  AUGUSTUS  gene        3031   5440   0.54  -  .
contig_24  AUGUSTUS  transcript  3031   5440   0.54  -  .  ID=g1846.t1;Parent=g1846;Name=YL067_YEAST
contig_24  AUGUSTUS  stop_codon  3031   3033   .     -  0
contig_24  AUGUSTUS  CDS         3034   4575   0.94  -  0
```

**Pattern B** — gene AND transcript both blank:
```
contig_24  AUGUSTUS  gene        270130  270360  0.73  +  .
contig_24  AUGUSTUS  transcript  270130  270360  0.73  +  .
contig_24  AUGUSTUS  CDS         270130  270357  0.73  +  0
contig_24  AUGUSTUS  stop_codon  270358  270360  .     +  0
```

AGAT's `agat_convert_sp_gxf2gxf.pl` uses a 3-tier parsing strategy:
1. **Parent/child** — uses `ID`/`Parent`
2. **Common tag** — groups by shared attribute value
3. **Sequential** — fallback: attaches features to last parent

Pattern A works OK — AGAT uses the transcript's real attributes. Pattern B causes mega-genes because AGAT can't find gene boundaries.

## Why AGAT can't solve this

The `agat_config.yaml` only lets you change *which attribute name* to key on — useless when column 9 is entirely empty.

## Solution

`bin/fix_blank_gff_attributes.py` with `--mode fix`:

**Only fixes blank gene + blank transcript pairs.** When a blank-attribute L1 (gene) line is immediately followed by a blank-attribute L2 (transcript) line, assigns synthetic `ID=`/`Parent=` to both. All other lines pass through unchanged.

This is minimal and targeted:
- Pattern A genes: untouched (transcript has real attrs, AGAT handles it)
- Pattern B genes: get synthetic IDs on gene + transcript, AGAT uses sequential grouping for L3 features within each gene
- Real annotations: completely untouched
- No redundant synthetic features overlapping real ones

### Earlier approaches that failed
1. **Full hierarchy fix** (assign synthetic IDs to all blank lines) — created redundant synthetic features overlapping real ones when a blank gene had real-attribute transcripts
2. **Strip mode** — removed blank genes AND blank L3 features, leaving orphaned transcripts

## Files

| File | Action |
|------|--------|
| `bin/fix_blank_gff_attributes.py` | **Created** — core Python script (fix/strip/none modes) |
| `modules/local/gff_fix_blank_attrs/main.nf` | **Created** — Nextflow process module |
| `nextflow.config` | **Edited** — `blank_gff_attributes = 'fix'` param |
| `workflows/annotation_transfer_only.nf` | **Edited** — includes + pre-processing blocks |
| `workflows/euk_scaffold_validation.nf` | **Edited** — includes + pre-processing blocks |
| `README.md` | **Edited** — documented new step and param |

## Integration pattern

```
ch_*_gff_raw  →  [GFF_FIX_BLANK_ATTRS]  →  ch_*_gff_preproc  →  [AGAT_FIX_GFF]  →  ch_*_gff
```

Gated by `params.blank_gff_attributes in ['fix', 'strip']`. Mode is passed to the script.

## Param

```
blank_gff_attributes = 'fix'   // 'fix', 'strip', or 'none'
```

- `fix` (default) — assign synthetic IDs to blank gene+transcript pairs only
- `strip` — remove all blank-attribute lines entirely
- `none` — skip this step
