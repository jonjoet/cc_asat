# Plan: Batch / Multi-Sample Runs

## Problem

The pipeline currently takes a single assembly + reference pair via scalar params
(`--assembly`, `--reference`, etc.) and produces one set of results. Running
multiple pairs requires separate `nextflow run` invocations.

## Options Considered

### Option A — nf-core samplesheet + meta map (full refactor)

The idiomatic nf-core approach: accept a `--input` CSV samplesheet, parse it into
a channel of `[meta, files...]` tuples, and thread `meta` through every process.

- **Effort:** Touch every module and subworkflow to add `val(meta)` to
  input/output tuples. Add `${meta.id}/` to every `publishDir`. ~1-2 days of
  mechanical refactoring plus testing.
- **Benefit:** Automatic parallelism across samples within a single Nextflow run,
  shared executor/resource scheduling, single `-resume` cache.
- **When it's worth it:** 10+ samples run routinely, or if we want to publish the
  pipeline as an nf-core community module.

### Option B — Bash wrapper with config files (chosen approach)

Keep the pipeline single-sample. Add a lightweight launcher script that reads two
TSV config files and loops `nextflow run` for each pair.

- **Effort:** One new script + two template TSVs. No pipeline changes.
- **Benefit:** Zero refactoring risk, works today, each run gets independent
  `-resume` caching.
- **Downside:** Runs are sequential by default (can be parallelised with `&` or
  `xargs -P` but then you manage multiple Nextflow instances manually).

## Chosen Design: Two Config Files + Launcher Script

### `batch/samples.tsv` — genome definitions

One row per genome file (assemblies and references in the same table).

| Column  | Required | Description                            |
|---------|----------|----------------------------------------|
| id      | yes      | Unique identifier (used in runs.tsv)   |
| fasta   | yes      | Path to FASTA                          |
| gff     | no       | Path to GFF (use `-` or empty for none)|

The GFF is context-dependent: for a reference row it becomes `--reference_gff`,
for an assembly row it becomes `--vendor_gff`.

Example:
```
id	fasta	gff
ref_yeast	/data/ref/S288C.fa	/data/ref/S288C.gff
asm_strainA	/data/asm/strainA.fa	/data/vendor/strainA.gff
asm_strainB	/data/asm/strainB.fa	-
```

### `batch/runs.tsv` — pair definitions

One row per pipeline invocation.

| Column        | Required | Description                                      |
|---------------|----------|--------------------------------------------------|
| run_name      | yes      | Used as `--sample_name` and `--outdir` subdirectory |
| assembly_id   | yes      | Must match an `id` in samples.tsv                |
| reference_id  | yes      | Must match an `id` in samples.tsv                |
| organism_type | yes      | `fungal` or `bacterial`                           |
| reads         | no       | Path to reads FASTQ (use `-` for none)           |
| extra_args    | no       | Additional Nextflow params (e.g. `--run_correct`)|

Example:
```
run_name	assembly_id	reference_id	organism_type	reads	extra_args
strainA_vs_S288C	asm_strainA	ref_yeast	fungal	-	--fill_gaps_from_ref
strainB_vs_S288C	asm_strainB	ref_yeast	fungal	/data/reads/strainB.fq.gz	--run_correct --read_type ont
```

### `batch/run_batch.sh` — launcher script

Bash script that:

1. Reads `samples.tsv` into an associative array keyed by id (storing fasta + gff).
2. Iterates over `runs.tsv`, looks up assembly and reference by id.
3. Builds the `nextflow run main.nf` command with:
   - `--sample_name "$run_name"`
   - `--outdir "results/$run_name"`
   - `--assembly` / `--reference` from the sample lookup
   - `--reference_gff` from the reference sample's GFF (if present)
   - `--vendor_gff` from the assembly sample's GFF (if present)
   - `--organism_type`
   - `--reads` (if provided)
   - Any `extra_args` appended verbatim
   - `-resume` always included
4. Runs each command sequentially, logging start/end times and exit codes.
5. Prints a summary table at the end (run_name, status, duration).

Optional flags for the launcher:
- `--dry-run` — print commands without executing
- `--parallel N` — run up to N pipelines concurrently (via `xargs -P`)
- `--samples-file` / `--runs-file` — override default file paths

## Future: Upgrading to Option A

If batch usage becomes frequent enough to justify the refactor, the migration path
is:

1. Add `val(meta)` to every process input/output tuple.
2. Replace `Channel.value(file(params.X))` with samplesheet-parsed channels.
3. Add `${meta.id}/` to `publishDir` paths.
4. The `batch/` configs could be repurposed as the samplesheet format or replaced
   with a single nf-core-style CSV.
