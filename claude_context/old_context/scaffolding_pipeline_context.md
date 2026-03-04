# Context Document: Yeast Genome Scaffolding Pipeline
## For use with Claude Code — refactoring to nf-core style + annotation transfer module

---

## 1. Project Background

This pipeline processes **yeast (eukaryotic)** genome assemblies derived from **Oxford Nanopore Technology (ONT)** long reads. The core goal is to scaffold draft contigs against a complete reference genome, close gaps, and assess assembly quality. An annotation transfer step is now being added.

The pipeline is written in **Nextflow** (DSL2 assumed) and is being refactored toward **nf-core modular style**.

---

## 2. Known Biology and Analysis Context

### Yeast genome characteristics relevant to the pipeline:
- Small genome (~12 Mb), 16 chromosomes
- ONT reads are long, so assemblers (e.g., Flye) often produce **contigs larger than individual chromosomes**, causing chimeric contigs that span chromosome boundaries
- **Structural rearrangements are common between yeast strains**: translocations, reciprocal translocations, segmental duplications, and subtelomeric repeats are frequently real, not assembly errors
- When QUAST reports "translocations" after scaffolding, this is often **real structural variation**, not pipeline error — this should be documented in QC output

### Key pipeline logic nuances:
- `ragtag correct` should ideally be run **before** `ragtag scaffold` to break chimeric contigs at likely misassembly breakpoints; this is especially important for yeast
- QUAST uses MUMmer (nucmer) internally for alignment; running QUAST pre- and post-scaffolding should yield similar results unless RagTag introduced errors (which it generally doesn't — it preserves contigs faithfully)
- TGSgapcloser uses minimap2 internally for the gap-filling step and can be **killed by the OOM killer** on large ONT read sets — memory allocation for this process needs to be generous (64GB+ depending on dataset)

---

## 3. Current Pipeline Steps (reconstructed from conversation history)

The pipeline currently performs these steps, roughly in order:

1. **RagTag correct** (`ragtag correct`) — optional; breaks chimeric contigs before scaffolding
2. **RagTag scaffold** (`ragtag scaffold`) — scaffolds contigs against reference using alignment; joins with Ns; does NOT split contigs
3. **TGS-GapCloser** (`tgsgapcloser --ne`) — fills N-gaps in scaffolds using ONT reads; `--ne` skips error correction; uses minimap2 internally with `-x ava-ont`
4. **QUAST** (`quast`) — assembly quality assessment against reference; produces Icarus plots and summary statistics

**Inferred from errors and troubleshooting:**
- TGS-GapCloser is run as `TGS_GAPCLOSER` process in Nextflow
- Uses container `quay.io/biocontainers/tgsgapcloser:1.0.3--h8b12597_0`
- Input to TGS-GapCloser: `ragtag.scaffold.fasta` and `reads.fasta`
- Output prefix: `gapclosed`
- Parameters: `--thread 6 --ne`

---

## 4. Nextflow / Infrastructure Context

### Environment:
- Running Nextflow with **container support** (Docker/Singularity via biocontainers)
- Using a local HPC/workstation with a storage path like `/storage/jon/Data_folders_JT/...`
- Work directory cleanup is a concern; user uses `rm -rf work/ .nextflow/ .nextflow.log*` for full cleanup (or `cleanup = true` in config for automatic cleanup on success, though this disables `-resume`)

### Container requirements for Nextflow compatibility:
- Containers need `procps` installed (for `ps` monitoring)
- Entrypoint must be `[]` (cleared), CMD should be `/bin/bash`
- Should run as root with `HOME=/root` to avoid permissions issues
- Do NOT use named conda environments inside containers — install directly into base

### Known container issue:
- There is a **version mismatch** in the TGS-GapCloser container: the image tag is `1.0.3` but the binary reports version `1.1.1`. This is likely benign but worth noting.

### Debugging tips used:
- `tail -f .nextflow.log` in a second terminal for real-time logging
- `tail -f work/<hash>/.command.log` to watch process-level output
- `-ansi-log false` for verbose terminal output
- `-with-trace` for post-run resource tracking

---

## 5. nf-core Modularization Principles (to apply during refactor)

The refactor should align with [nf-core DSL2 module conventions](https://nf-co.re/docs/contributing/modules):

### Directory structure target:
```
pipeline/
├── main.nf                        # Entry point, orchestrates subworkflows
├── nextflow.config
├── nextflow_schema.json
├── workflows/
│   └── scaffolding.nf             # Top-level workflow
├── subworkflows/
│   └── local/
│       ├── scaffolding.nf         # Groups ragtag_correct + ragtag_scaffold
│       ├── gap_closing.nf         # TGS-GapCloser
│       └── annotation_transfer.nf # NEW: Liftoff-based annotation transfer
└── modules/
    └── local/
        ├── ragtag/
        │   ├── correct/main.nf
        │   └── scaffold/main.nf
        ├── tgsgapcloser/
        │   └── main.nf
        ├── quast/
        │   └── main.nf
        └── liftoff/               # NEW
            └── main.nf
```

### nf-core process conventions to follow:
- Each process in its own `modules/local/<tool>/main.nf`
- Process names in `UPPERCASE` (e.g., `RAGTAG_SCAFFOLD`, `TGS_GAPCLOSER`, `LIFTOFF`)
- Input/output use **named tuples** with `meta` map as first element: `tuple val(meta), path(fasta)`
- `meta` map carries sample ID and other metadata through the pipeline
- Use `tag "$meta.id"` in each process
- `publishDir` with `mode: 'copy'` (not symlinks — symlinks can confuse downstream tools and Galaxy integrations)
- Resource directives (`cpus`, `memory`, `time`) defined in `nextflow.config` using `withName` selectors, not hardcoded in process definitions
- Containers specified per-process using `container` directive pointing to biocontainers images

### Example nf-core-style process template:
```groovy
process RAGTAG_SCAFFOLD {
    tag "$meta.id"
    label 'process_medium'

    container "quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0"

    input:
    tuple val(meta), path(assembly)
    tuple val(meta_ref), path(reference)

    output:
    tuple val(meta), path("ragtag_output/ragtag.scaffold.fasta"), emit: scaffolded_fasta
    tuple val(meta), path("ragtag_output/ragtag.scaffold.stats"),  emit: stats
    path "versions.yml",                                           emit: versions

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    ragtag.py scaffold \\
        $args \\
        -o ragtag_output \\
        -t $task.cpus \\
        ${reference} \\
        ${assembly}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        ragtag: \$(ragtag.py --version 2>&1 | head -1)
    END_VERSIONS
    """
}
```

### Key nf-core requirements:
- Every process must emit a `versions.yml` file
- Use `task.ext.args` pattern for passing extra arguments from config
- Use `task.ext.prefix` for output file naming
- Process labels (`process_low`, `process_medium`, `process_high`) map to resource tiers in config

---

## 6. Annotation Transfer Module (NEW)

### Tool decision: **Liftoff** (preferred over RATT)
- Liftoff is more modern, actively maintained, handles structural variation better
- RATT is unmaintained and has known unfixed bugs
- Liftoff uses minimap2 internally for alignment

### GFF/GFF3 input requirements for Liftoff:
- Liftoff expects a **3-level hierarchy**: `gene → mRNA/transcript → CDS/exon`
- Yeast reference annotations (e.g., from SGD) should already conform to this
- If the source annotation lacks `gene` features (e.g., was generated by Bakta for bacterial genomes, or is CDS-only), use **AGAT** to add parent gene features:
  ```bash
  agat_sp_add_parentfeatures.pl --gff input.gff3 --output fixed.gff3
  ```
- Alternatively, a Python script or awk can duplicate CDS lines as gene features

### Liftoff dependencies:
- Python package; requires minimap2 as external dependency
- Install via conda: `conda install -c bioconda liftoff`
- Biocontainer available: `quay.io/biocontainers/liftoff`

### Liftoff usage pattern:
```bash
liftoff \
    -g reference_annotation.gff3 \
    -o output_annotation.gff3 \
    -u unmapped_features.txt \
    -copies \
    target_genome.fasta \
    reference_genome.fasta
```

### Module design notes:
- Input: `(meta, target_fasta)` + reference fasta + reference GFF3 (can be passed as value channel or path)
- Output: lifted-over GFF3, unmapped features file, versions.yml
- The reference genome + annotation can be shared across samples as a single value channel (not per-sample)
- Consider whether to run annotation QC (e.g., count transferred features) as part of this module or a separate QC step

### Post-liftoff considerations:
- Check unmapped features file — features that fail to transfer may indicate real structural differences
- For yeast, subtelomeric genes often fail to lift over cleanly due to repeat complexity
- Liftoff handles inversions and rearrangements better than RATT, but very divergent regions will still have transfer failures

---

## 7. Resource Allocation Recommendations

Based on OOM errors observed with TGS-GapCloser:

```groovy
process {
    withName: 'TGS_GAPCLOSER' {
        memory = '64 GB'   // minimap2 inside tgsgapcloser is memory-hungry
        cpus   = 8
        time   = '12h'
    }
    withName: 'RAGTAG_SCAFFOLD' {
        memory = '16 GB'
        cpus   = 8
        time   = '4h'
    }
    withName: 'RAGTAG_CORRECT' {
        memory = '16 GB'
        cpus   = 8
        time   = '4h'
    }
    withName: 'LIFTOFF' {
        memory = '16 GB'
        cpus   = 4
        time   = '4h'
    }
    withName: 'QUAST' {
        memory = '8 GB'
        cpus   = 4
        time   = '2h'
    }
}
```

---

## 8. Suggested Refactoring Approach for Claude Code

1. **Start with the module definitions** — extract each existing process into its own `modules/local/<tool>/main.nf` file following the nf-core template above, adding `versions.yml` emission and `task.ext.args` support
2. **Create subworkflows** that group logically related steps:
   - `SCAFFOLD_GENOME` subworkflow: ragtag_correct → ragtag_scaffold
   - `CLOSE_GAPS` subworkflow: tgsgapcloser
   - `ASSESS_ASSEMBLY` subworkflow: quast (pre and post scaffolding)
   - `TRANSFER_ANNOTATIONS` subworkflow (NEW): liftoff
3. **Standardize channel structure** — ensure `meta` map flows through all processes
4. **Move resource definitions** out of process blocks and into `nextflow.config` using `withName` selectors
5. **Add the Liftoff module** as a new `modules/local/liftoff/main.nf` and wire it into a new subworkflow
6. **Test incrementally** using `-resume` between runs to avoid re-running completed steps

---

## 9. Files / Paths Claude Code Should Look For

When starting, ask the user to share or point to:
- The current `main.nf` or primary workflow `.nf` file
- The current `nextflow.config`
- Any existing module files if partially modularized
- The reference genome FASTA and annotation GFF3 to be used for Liftoff

---

*Generated from conversation history — covers RagTag scaffolding troubleshooting, TGS-GapCloser OOM debugging, Nextflow container standardization, Liftoff vs RATT annotation transfer decisions, nf-core module conventions, and yeast genome biology context.*
