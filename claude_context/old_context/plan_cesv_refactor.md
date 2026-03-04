# CESV Pipeline Refactor Plan
_Generated: 2026-02-22_

## Overview

Two coordinated changes:
1. Deprecate and then remove the NucDiff + difference-summary steps (moving them to a separate pipeline)
2. Add an AGAT GFF-fixing step as an early, skippable pre-processing stage in both workflow entry points

---

## Part 1: NucDiff / ASSEMBLY_COMPARISON — Deprecate then Remove

### Files that constitute the "NucDiff package"

Before removing anything from the main repo, copy these files into the target repo (or use repomix with `--include` to pack them as a standalone reference):

| File | Role |
|------|------|
| `modules/local/nucdiff/main.nf` | NUCDIFF process |
| `modules/local/generate_summary/main.nf` | GENERATE_SUMMARY process |
| `subworkflows/local/assembly_comparison.nf` | Subworkflow wrapping both |
| `bin/generate_summary.py` | Python summariser script |
| `docker/nucdiff/Dockerfile` | Custom NucDiff container |

To extract: `cp -r` those paths into a new repo, or run:
```
repomix --include "modules/local/nucdiff/**,modules/local/generate_summary/**,subworkflows/local/assembly_comparison.nf,bin/generate_summary.py,docker/nucdiff/**"
```
The originals stay untouched in the main repo until the full removal phase.

---

### Deprecation phase

Goal: keep existing runs working while signalling the step is leaving.

1. Add `skip_assembly_comparison = false` to `nextflow.config` params block.
2. In `workflows/euk_scaffold_validation.nf`, wrap both `ASSEMBLY_COMPARISON(...)` call sites:
   ```groovy
   if (!params.skip_assembly_comparison) {
       log.warn "ASSEMBLY_COMPARISON (NucDiff) is deprecated and will be removed in a future release. Use --skip_assembly_comparison to suppress this warning."
       ASSEMBLY_COMPARISON(ch_reference, ch_final_for_comparison)
   }
   ```
3. Update README to note the deprecation and point to the future separate pipeline.

---

### Removal phase (after NucDiff pipeline is established elsewhere)

Files to delete:
- `modules/local/nucdiff/main.nf`
- `modules/local/generate_summary/main.nf`
- `subworkflows/local/assembly_comparison.nf`
- `bin/generate_summary.py`
- `docker/nucdiff/`

Edits:
- `workflows/euk_scaffold_validation.nf`:
  - Remove both `ASSEMBLY_COMPARISON(...)` call sites and the `include` line
  - Re-examine the `.combine(ANNOTATION_TRANSFER.out.lifted_gff).map { it[0] }` channel-dependency pattern used on `ch_final_for_comparison` — this was added *solely* to sequence NucDiff after annotation transfer. Once ASSEMBLY_COMPARISON is gone, check whether QUAST still needs that same sequencing constraint independently or whether it can run in parallel.
- `nextflow.config`: remove `nucdiff_prefix` and `skip_assembly_comparison` params
- `README.md`: remove nucdiff from params table and output directory tree

---

## Part 2: AGAT GFF Fixing

### Design principles

- One module, one GFF in / one GFF out — maximally composable
- Fixing happens upstream of all consumers; no downstream module knows about AGAT
- Both workflow entry points (`EUK_SCAFFOLD_VALIDATION` and `ANNOTATION_TRANSFER_ONLY`) default to fixing; each GFF has its own skip flag
- Skip flags are per-GFF so you can fix reference but not vendor (or vice versa)

### New params (add to `nextflow.config`)

```groovy
fix_reference_gff = true   // run AGAT fix on reference_gff before use
fix_vendor_gff    = true   // run AGAT fix on vendor_gff before use
```

### New module: `modules/local/agat/fix_gff/main.nf`

```groovy
process AGAT_FIX_GFF {
    tag "${gff.baseName}"
    label 'process_low'

    conda 'bioconda::agat=1.4.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/agat:1.4.0--pl5321hdfd78af_0' :
        'quay.io/biocontainers/agat:1.4.0--pl5321hdfd78af_0' }"

    input:
    path gff

    output:
    path "${gff.baseName}_fixed.gff3", emit: fixed_gff

    script:
    """
    agat_convert_sp_gxf2gxf.pl \\
        --gxf ${gff} \\
        --output ${gff.baseName}_fixed.gff3
    """
}
```

### Wiring pattern (same for both workflow files)

After input channel declarations, before any process that consumes the GFF:

```groovy
include { AGAT_FIX_GFF } from '../modules/local/agat/fix_gff/main'

// Reference GFF
ch_reference_gff_fixed = (params.reference_gff && params.fix_reference_gff)
    ? AGAT_FIX_GFF(ch_reference_gff).fixed_gff
    : ch_reference_gff

// Vendor GFF (only meaningful if vendor_gff is supplied)
ch_vendor_gff_fixed = (params.vendor_gff && params.fix_vendor_gff)
    ? AGAT_FIX_GFF(ch_vendor_gff).fixed_gff
    : ch_vendor_gff
```

Then substitute `ch_reference_gff_fixed` / `ch_vendor_gff_fixed` everywhere
`ch_reference_gff` / `ch_vendor_gff` are passed downstream (ANNOTATION_TRANSFER, QUAST).

### Files to create / edit

| Action | File |
|--------|------|
| **Create** | `modules/local/agat/fix_gff/main.nf` |
| Edit | `workflows/euk_scaffold_validation.nf` — add include + wiring |
| Edit | `workflows/annotation_transfer_only.nf` — add include + wiring (same pattern, same defaults) |
| Edit | `nextflow.config` — add `fix_reference_gff`, `fix_vendor_gff` |
| Edit | `README.md` — document new params |

### Note on `annotation_transfer_only.nf`

This entry point should mirror the main workflow: both GFF fix flags default `true`, both skippable independently via `--fix_reference_gff false` / `--fix_vendor_gff false`. The wiring is identical to the main workflow — no special-casing needed.

---

## Sequencing

1. Package / document NucDiff file set for extraction (no deletion yet)
2. Add AGAT module and wire into both workflow entry points
3. Deprecate ASSEMBLY_COMPARISON with skip flag + log warning
4. Once NucDiff pipeline is live in separate repo: full removal pass
