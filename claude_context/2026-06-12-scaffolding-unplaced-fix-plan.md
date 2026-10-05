# Scaffolding / Unplaced-Contig Handling Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix how `cc_asat` handles RagTag-unplaced contigs (the path plasmids take): replace the dead unplaced-output plumbing with a real read-only QC artifact, and stop the header renamer from mangling contig identity.

**Architecture:** Two coordinated fixes in the scaffolding subworkflow. (A) A new stdlib Python script reads `ragtag.scaffold.agp` (read-only — never writes it) and emits a TSV listing every unplaced contig, classified by AGP structure with an optional `.fai` cross-check; the dead `emit: unplaced` / `NO_FILE` sentinel path is removed. (B) `rename_ragtag_scaffolds.py` switches from a destructive "strip first underscore" rule to non-destructive prefix-if-missing by default, with an optional `--chr-pattern` regex for strain substitution on placed scaffolds (e.g. `LEXst001_ChrI → S_ChrI`). Unplaced contigs stay in the single main FASTA (confirmed design decision) and remain visible via the new artifact.

**Tech Stack:** Nextflow DSL2, Python 3 (stdlib only, `python:3.12` container), RagTag 2.1.0 (`-u`, no `-C`). No test framework — verification uses inline `--self-test` assertions run in Docker, plus a Nextflow `-resume` run.

**Confirmed design decisions (do not re-litigate):**
- Unplaced contigs are **kept** in the single `<sample>_scaffolds.fasta` (option (a) from the brief). The new artifact is purely informational. Splitting them out would route plasmids around DNAAPLER / gap-closing / annotation transfer.
- Classifier uses **both** signals: AGP structure is authoritative; the reference `.fai` is a cross-check that only emits a stderr warning on disagreement. The AGP is read **only**.
- Renamer **default** is prefix-if-missing (never deletes a token). Strain substitution is **opt-in** via `--chr-pattern` and discriminates by the pattern alone (no classifier gating) — the no-match fallback is non-destructive.

**Ground truth (RagTag v2.1.0, invocation `ragtag.py scaffold <ref> <asm> -o ragtag_out -u -t N`):**
- Placed scaffolds are AGP objects named `<reference_seq>_RagTag`.
- An unplaced contig is its own AGP object: exactly **one `W` component line, no gap (`N`/`U`) lines**, and component-id (col 6) **equals** the object name (col 1) with a trailing `_RagTag` removed.
- A single-contig **placed** chromosome also has one `W` line and no gaps, but its object name is the *reference* name, so col-6 ≠ object-basename. That inequality is the placed-vs-unplaced discriminator.

---

## File Structure

**Create:**
- `bin/classify_unplaced_contigs.py` — stdlib AGP classifier → unplaced TSV; `--self-test`.
- `modules/local/classify_unplaced/main.nf` — `CLASSIFY_UNPLACED` process (AGP + reference `.fai` → TSV).

**Modify:**
- `bin/rename_ragtag_scaffolds.py` — rewrite `rename_header`; add `--chr-pattern`, `--self-test`.
- `modules/local/rename_ragtag_scaffolds/main.nf` — drop `unplaced` input + dead branch + optional output; add `--chr-pattern` passthrough.
- `modules/local/ragtag/scaffold/main.nf` — remove the false `emit: unplaced` line.
- `subworkflows/local/scaffolding.nf` — drop `ch_unplaced` sentinel plumbing; add `reference_fai` to `take:`; call `CLASSIFY_UNPLACED`; emit `unplaced_list`.
- `workflows/euk_scaffold_validation.nf` — pass `SAMTOOLS_FAIDX.out.fai` into both `SCAFFOLDING(...)` calls.
- `nextflow.config` — add `scaffold_rename_pattern = null` param.
- `conf/modules.config` — add `CLASSIFY_UNPLACED` publishDir.
- `README.md` — document the new param, pipeline step, and output file.

---

## Task 1: Fix the header renamer (`rename_ragtag_scaffolds.py`)

**Files:**
- Modify: `bin/rename_ragtag_scaffolds.py`

The new `_self_test()` asserts the previously-broken cases (`contig_3 → S_contig_3`, not the old `S_3`), so it is both the failing test and the regression guard. We write the complete new script, then run `--self-test` in Docker to confirm.

- [ ] **Step 1: Replace the script with the non-destructive renamer + self-test**

Overwrite `bin/rename_ragtag_scaffolds.py` with:

```python
#!/usr/bin/env python3
"""Rename sequence headers after ragtag scaffold.

Default: prefix each header with the sample id exactly once, preserving the
original contig name verbatim (non-destructive, idempotent on re-runs).

Optional --chr-pattern <regex>: a regex with one capture group. On match, the
header becomes "<sample_id>_<captured>" (used to swap a reference strain prefix
for the new strain id while keeping the chromosome label, e.g. LEXst001_ChrI ->
S_ChrI). On no match, falls back to the non-destructive prefix behaviour, so
unplaced contigs / plasmids keep their full names.
"""

import argparse
import re
import sys

RAGTAG_SUFFIX = "_RagTag"


def rename_header(name, sample_id, pattern=None):
    name = name.removeprefix(">").split()[0]
    if name.endswith(RAGTAG_SUFFIX):
        name = name[: -len(RAGTAG_SUFFIX)]
    if pattern:
        m = re.search(pattern, name)
        if m:
            return f">{sample_id}_{m.group(1)}"
    prefix = f"{sample_id}_"
    if not name.startswith(prefix):
        name = prefix + name
    return f">{name}"


def rename_fasta(input_path, output_path, sample_id, pattern=None):
    with open(input_path) as fh_in, open(output_path, "w") as fh_out:
        for line in fh_in:
            if line.startswith(">"):
                fh_out.write(rename_header(line.rstrip(), sample_id, pattern) + "\n")
            else:
                fh_out.write(line)


def _self_test():
    # default mode (no pattern): preserve names, prefix once, idempotent
    assert rename_header(">contig_3", "S") == ">S_contig_3"
    assert rename_header(">2micron_plasmid", "S") == ">S_2micron_plasmid"
    assert rename_header(">contig_3_RagTag", "S") == ">S_contig_3"
    assert rename_header(">S_contig_3", "S") == ">S_contig_3"            # idempotent
    assert rename_header(">LEXst001_ChrI", "S") == ">S_LEXst001_ChrI"    # preserved
    # pattern mode: swap strain prefix, keep chromosome label
    pat = r"_(Chr[IVXLCDM]+)$"
    assert rename_header(">LEXst001_ChrI", "S", pat) == ">S_ChrI"
    assert rename_header(">LEXst001_ChrI_RagTag", "S", pat) == ">S_ChrI"
    assert rename_header(">S_ChrI", "S", pat) == ">S_ChrI"              # idempotent
    assert rename_header(">2micron_plasmid", "S", pat) == ">S_2micron_plasmid"  # no match -> fallback


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--sample-id")
    parser.add_argument(
        "--chr-pattern",
        default=None,
        help="Regex with one capture group; on match header becomes "
        "<sample_id>_<captured>. On no match, non-destructive prefix fallback.",
    )
    parser.add_argument("--self-test", action="store_true",
                        help="Run inline unit assertions and exit")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        print("rename_ragtag_scaffolds self-test passed", file=sys.stderr)
        return

    if not (args.input and args.output and args.sample_id):
        parser.error("--input, --output and --sample-id are required unless --self-test is given")

    rename_fasta(args.input, args.output, args.sample_id, args.chr_pattern)
    print(f"Renamed sequences written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the self-test in Docker to verify it passes**

Run:
```bash
docker run --rm -v /mnt/internal_hdd/claude_code/cc_asat/bin:/scripts \
  python:3.12 python3 /scripts/rename_ragtag_scaffolds.py --self-test
```
Expected: exit 0, stderr `rename_ragtag_scaffolds self-test passed`.

- [ ] **Step 3: Commit**

```bash
git add bin/rename_ragtag_scaffolds.py
git commit -m "fix(scaffolding): non-destructive header rename with optional chr-pattern substitution

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Wire `--chr-pattern` through the rename module

**Files:**
- Modify: `modules/local/rename_ragtag_scaffolds/main.nf`
- Modify: `nextflow.config`

- [ ] **Step 1: Add the `scaffold_rename_pattern` param**

In `nextflow.config`, immediately after the `reorient_assembly = ...` line (currently line 77), insert a new block:

```groovy
    // ---- Scaffold renaming ----
    scaffold_rename_pattern = null   // optional regex w/ one capture group to substitute strain prefix on placed scaffolds (e.g. '_(Chr[IVXLCDM]+)$'); null = prefix sample_name verbatim
```

- [ ] **Step 2: Drop the dead unplaced path and add the pattern passthrough**

Replace the entire contents of `modules/local/rename_ragtag_scaffolds/main.nf` with:

```groovy
process RENAME_RAGTAG_SCAFFOLDS {
    tag "${params.sample_name}"
    label 'process_single'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path scaffold

    output:
    path "${params.sample_name}_scaffolds.fasta", emit: scaffold

    script:
    def pattern_arg = params.scaffold_rename_pattern ? "--chr-pattern '${params.scaffold_rename_pattern}'" : ""
    """
    rename_ragtag_scaffolds.py \\
        --input ${scaffold} \\
        --output ${params.sample_name}_scaffolds.fasta \\
        --sample-id ${params.sample_name} \\
        ${pattern_arg}
    """
}
```

- [ ] **Step 3: Confirm Nextflow still parses the config**

Run:
```bash
/mnt/internal_hdd/claude_code/nextflow config /mnt/internal_hdd/claude_code/cc_asat -profile docker > /dev/null && echo CONFIG_OK
```
Expected: `CONFIG_OK` (no Groovy parse error).

- [ ] **Step 4: Commit**

```bash
git add modules/local/rename_ragtag_scaffolds/main.nf nextflow.config
git commit -m "feat(scaffolding): add scaffold_rename_pattern param; drop dead unplaced rename path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: AGP unplaced classifier script (`classify_unplaced_contigs.py`)

**Files:**
- Create: `bin/classify_unplaced_contigs.py`

- [ ] **Step 1: Write the classifier with inline self-test**

Create `bin/classify_unplaced_contigs.py`:

```python
#!/usr/bin/env python3
"""Classify RagTag scaffold AGP objects as placed or unplaced.

Read-only consumer of `ragtag.scaffold.agp` (never modifies it). Emits a TSV
listing every contig RagTag left unplaced, so plasmids / extra-chromosomal
contigs that failed to anchor are recorded instead of silently riding along
unlabelled inside the main scaffolds FASTA.

Classification (ground truth from RagTag v2.1.0 with `-u`, no `-C`):
an AGP object is UNPLACED iff
  * it has exactly one `W` component line,
  * it has no gap lines (`N`/`U`), and
  * the component id (col 6) equals the object name (col 1) with a trailing
    `_RagTag` removed.
Everything else is placed. Optional cross-check against the reference `.fai`:
an unplaced object's basename should NOT be a reference sequence name; a
disagreement is reported to stderr but the AGP structure stays authoritative.
"""

import argparse
import sys

RAGTAG_SUFFIX = "_RagTag"


def strip_suffix(name):
    return name[: -len(RAGTAG_SUFFIX)] if name.endswith(RAGTAG_SUFFIX) else name


def parse_agp(lines):
    """Group AGP rows by object name (col 1), preserving order."""
    objects = {}
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.rstrip("\n").split("\t")
        objects.setdefault(fields[0], []).append(fields)
    return objects


def classify(objects):
    """Return list of (contig_id, object_name, length_bp) for unplaced objects."""
    unplaced = []
    for obj, rows in objects.items():
        w_rows = [r for r in rows if len(r) > 4 and r[4] == "W"]
        gap_rows = [r for r in rows if len(r) > 4 and r[4] in ("N", "U")]
        if len(w_rows) == 1 and not gap_rows:
            comp_id = w_rows[0][5]
            if comp_id == strip_suffix(obj):
                length = int(w_rows[0][2]) - int(w_rows[0][1]) + 1
                unplaced.append((comp_id, obj, length))
    return unplaced


def load_reference_names(fai_path):
    names = set()
    with open(fai_path) as fh:
        for line in fh:
            if line.strip():
                names.add(line.split("\t")[0])
    return names


def _self_test():
    placed_multi = [  # multi-contig placed scaffold: has a gap -> placed
        ["chrI_RagTag", "1", "1000", "1", "W", "ctgA", "1", "1000", "+"],
        ["chrI_RagTag", "1001", "1100", "2", "N", "100", "scaffold", "yes", "align_genus"],
        ["chrI_RagTag", "1101", "2000", "3", "W", "ctgB", "1", "900", "+"],
    ]
    placed_single = [  # single-contig placed chromosome: object=ref name != component id
        ["chrM_RagTag", "1", "500", "1", "W", "ctgMito", "1", "500", "+"],
    ]
    unplaced_ctg = [  # unplaced contig: one W, no gap, basename == component id
        ["2micron_plasmid_RagTag", "1", "6300", "1", "W", "2micron_plasmid", "1", "6300", "+"],
    ]
    objects = {}
    for rows in (placed_multi, placed_single, unplaced_ctg):
        for r in rows:
            objects.setdefault(r[0], []).append(r)
    result = classify(objects)
    assert {r[0] for r in result} == {"2micron_plasmid"}, result
    assert result[0] == ("2micron_plasmid", "2micron_plasmid_RagTag", 6300), result[0]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--agp")
    parser.add_argument("--fai", default=None,
                        help="Reference .fai for an optional placed-vs-unplaced cross-check")
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true",
                        help="Run inline unit assertions and exit")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        print("classify_unplaced_contigs self-test passed", file=sys.stderr)
        return

    if not (args.agp and args.output):
        parser.error("--agp and --output are required unless --self-test is given")

    with open(args.agp) as fh:
        objects = parse_agp(fh)
    unplaced = classify(objects)

    if args.fai:
        ref_names = load_reference_names(args.fai)
        for _, obj, _ in unplaced:
            if strip_suffix(obj) in ref_names:
                print(f"WARNING: object {obj} classified unplaced by AGP structure but its "
                      f"basename matches a reference sequence in {args.fai}", file=sys.stderr)

    with open(args.output, "w") as out:
        out.write("contig_id\tobject_name\tlength_bp\n")
        for contig_id, obj, length in unplaced:
            out.write(f"{contig_id}\t{obj}\t{length}\n")

    print(f"{len(unplaced)} unplaced contig(s) written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the self-test in Docker to verify the classifier**

Run:
```bash
docker run --rm -v /mnt/internal_hdd/claude_code/cc_asat/bin:/scripts \
  python:3.12 python3 /scripts/classify_unplaced_contigs.py --self-test
```
Expected: exit 0, stderr `classify_unplaced_contigs self-test passed`.

- [ ] **Step 3: Sanity-check against a hand-written AGP**

```bash
mkdir -p /mnt/internal_hdd/claude_code/tmp/agp_test
printf 'chrI_RagTag\t1\t1000\t1\tW\tctgA\t1\t1000\t+\n' >  /mnt/internal_hdd/claude_code/tmp/agp_test/t.agp
printf 'chrI_RagTag\t1001\t1100\t2\tN\t100\tscaffold\tyes\talign_genus\n' >> /mnt/internal_hdd/claude_code/tmp/agp_test/t.agp
printf 'chrI_RagTag\t1101\t2000\t3\tW\tctgB\t1\t900\t+\n' >> /mnt/internal_hdd/claude_code/tmp/agp_test/t.agp
printf 'chrM_RagTag\t1\t500\t1\tW\tctgMito\t1\t500\t+\n' >> /mnt/internal_hdd/claude_code/tmp/agp_test/t.agp
printf '2micron_plasmid_RagTag\t1\t6300\t1\tW\t2micron_plasmid\t1\t6300\t+\n' >> /mnt/internal_hdd/claude_code/tmp/agp_test/t.agp
docker run --rm -v /mnt/internal_hdd/claude_code/cc_asat/bin:/scripts \
  -v /mnt/internal_hdd/claude_code/tmp/agp_test:/data python:3.12 \
  python3 /scripts/classify_unplaced_contigs.py --agp /data/t.agp --output /data/out.tsv
cat /mnt/internal_hdd/claude_code/tmp/agp_test/out.tsv
```
Expected stdout: a TSV header plus exactly one data row — `2micron_plasmid	2micron_plasmid_RagTag	6300`.

- [ ] **Step 4: Commit**

```bash
git add bin/classify_unplaced_contigs.py
git commit -m "feat(scaffolding): add read-only AGP classifier for unplaced contigs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `CLASSIFY_UNPLACED` Nextflow process

**Files:**
- Create: `modules/local/classify_unplaced/main.nf`
- Modify: `conf/modules.config`

- [ ] **Step 1: Create the process module**

Create `modules/local/classify_unplaced/main.nf`:

```groovy
process CLASSIFY_UNPLACED {
    tag "${params.sample_name}"
    label 'process_single'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path agp
    path fai

    output:
    path "${params.sample_name}_unplaced_contigs.tsv", emit: unplaced_list

    script:
    """
    classify_unplaced_contigs.py \\
        --agp ${agp} \\
        --fai ${fai} \\
        --output ${params.sample_name}_unplaced_contigs.tsv
    """
}
```

- [ ] **Step 2: Add publishDir routing**

In `conf/modules.config`, immediately after the `RENAME_RAGTAG_SCAFFOLDS` block (currently ends line 31), insert:

```groovy
    withName: 'CLASSIFY_UNPLACED' {
        publishDir = [
            [
                path: { "${params.outdir}/scaffold" },
                mode: 'copy'
            ],
            [
                path: { "${params.outdir}/final_outputs" },
                mode: 'copy'
            ]
        ]
    }
```

- [ ] **Step 3: Commit**

```bash
git add modules/local/classify_unplaced/main.nf conf/modules.config
git commit -m "feat(scaffolding): add CLASSIFY_UNPLACED process and publishDir

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Remove the false `emit: unplaced` from RAGTAG_SCAFFOLD

**Files:**
- Modify: `modules/local/ragtag/scaffold/main.nf`

- [ ] **Step 1: Delete the dead output line**

In `modules/local/ragtag/scaffold/main.nf`, delete this line from the `output:` block (currently line 17):

```groovy
    path "ragtag_out/ragtag.scaffold.unplaced.fasta",   emit: unplaced, optional: true
```

The `output:` block now ends with the `.stats` emit. No other line changes.

- [ ] **Step 2: Commit**

```bash
git add modules/local/ragtag/scaffold/main.nf
git commit -m "fix(scaffolding): drop emit for ragtag.scaffold.unplaced.fasta (RagTag never writes it)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Rewire the scaffolding subworkflow

**Files:**
- Modify: `subworkflows/local/scaffolding.nf`
- Modify: `workflows/euk_scaffold_validation.nf`

- [ ] **Step 1: Update the subworkflow**

Replace the entire contents of `subworkflows/local/scaffolding.nf` with:

```groovy
include { RAGTAG_CORRECT           } from '../../modules/local/ragtag/correct/main'
include { RAGTAG_SCAFFOLD          } from '../../modules/local/ragtag/scaffold/main'
include { RENAME_RAGTAG_SCAFFOLDS  } from '../../modules/local/rename_ragtag_scaffolds/main'
include { CLASSIFY_UNPLACED        } from '../../modules/local/classify_unplaced/main'

workflow SCAFFOLDING {
    take:
    assembly
    reference
    reference_fai   // reference .fai from SAMTOOLS_FAIDX (unplaced cross-check)
    reads           // file or null sentinel
    run_correct     // boolean value channel

    main:
    if (run_correct) {
        RAGTAG_CORRECT(assembly, reference, reads)
        ch_corrected = RAGTAG_CORRECT.out.corrected
    } else {
        ch_corrected = assembly
    }

    RAGTAG_SCAFFOLD(ch_corrected, reference)

    CLASSIFY_UNPLACED(RAGTAG_SCAFFOLD.out.agp, reference_fai)

    RENAME_RAGTAG_SCAFFOLDS(RAGTAG_SCAFFOLD.out.scaffold)

    emit:
    scaffold      = RENAME_RAGTAG_SCAFFOLDS.out.scaffold
    agp           = RAGTAG_SCAFFOLD.out.agp
    stats         = RAGTAG_SCAFFOLD.out.stats
    unplaced_list = CLASSIFY_UNPLACED.out.unplaced_list
}
```

- [ ] **Step 2: Pass the `.fai` into both SCAFFOLDING call sites**

In `workflows/euk_scaffold_validation.nf`, update the two calls (currently lines 37 and 39) to add `SAMTOOLS_FAIDX.out.fai` as the third argument:

Change:
```groovy
        SCAFFOLDING(ch_assembly, ch_reference, ch_reads_scaffold, true)
```
to:
```groovy
        SCAFFOLDING(ch_assembly, ch_reference, SAMTOOLS_FAIDX.out.fai, ch_reads_scaffold, true)
```

And change:
```groovy
        SCAFFOLDING(ch_assembly, ch_reference, Channel.value(file('NO_READS')), false)
```
to:
```groovy
        SCAFFOLDING(ch_assembly, ch_reference, SAMTOOLS_FAIDX.out.fai, Channel.value(file('NO_READS')), false)
```

(`SAMTOOLS_FAIDX(ch_reference)` already runs at line 32, before these calls.)

- [ ] **Step 3: Confirm the DSL2 graph still resolves (dry parse)**

Run:
```bash
/mnt/internal_hdd/claude_code/nextflow config /mnt/internal_hdd/claude_code/cc_asat -profile docker > /dev/null && echo CONFIG_OK
```
Expected: `CONFIG_OK`. (Full graph validation happens in Task 8's pipeline run.)

- [ ] **Step 4: Commit**

```bash
git add subworkflows/local/scaffolding.nf workflows/euk_scaffold_validation.nf
git commit -m "refactor(scaffolding): classify unplaced contigs; drop NO_FILE sentinel plumbing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the pipeline step note**

In `README.md`, under **### Assembly processing**, change the RagTag Scaffold bullet (currently line 77) to:

```markdown
2. **RagTag Scaffold** — Orders and orients contigs against the reference. Contigs RagTag cannot anchor (e.g. plasmids absent from the reference) are kept in the main FASTA and listed in `scaffold/{sample}_unplaced_contigs.tsv`.
```

- [ ] **Step 2: Document the new parameter**

In the **### Scaffolding Controls** table, add a row after the `--reorient_assembly` row (currently line 129):

```markdown
| `--scaffold_rename_pattern` | `null` | Optional regex with one capture group to substitute a reference strain prefix on placed scaffolds, keeping the chromosome label (e.g. `'_(Chr[IVXLCDM]+)$'` turns `LEXst001_ChrI` into `{sample}_ChrI`). Unmatched names (plasmids/unplaced contigs) keep their full name with the sample prefix. |
```

- [ ] **Step 3: Document the new output file**

In the **## Output** tree, under the `scaffold/` entry (currently line 206), add:

```markdown
  scaffold/
    {sample}_unplaced_contigs.tsv        # Contigs RagTag left unplaced (also in final_outputs/)
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document scaffold_rename_pattern and unplaced-contig artifact

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Re-run both self-tests together**

```bash
docker run --rm -v /mnt/internal_hdd/claude_code/cc_asat/bin:/scripts python:3.12 \
  sh -c 'python3 /scripts/rename_ragtag_scaffolds.py --self-test && python3 /scripts/classify_unplaced_contigs.py --self-test'
```
Expected: both `... self-test passed` lines, exit 0.

- [ ] **Step 2: Run the pipeline on a bacterial test case with a plasmid absent from the reference**

Use an existing small test dataset (assembly with a plasmid contig that is NOT in the reference). From the repo root:
```bash
/mnt/internal_hdd/claude_code/nextflow run main.nf -profile docker \
  --assembly <asm.fasta> --reference <ref.fasta> \
  --organism_type bacterial --sample_name testbac \
  --outdir /mnt/internal_hdd/claude_code/tmp/asat_verify -resume
```
Expected: pipeline completes; no error referencing `ragtag.scaffold.unplaced.fasta`.

> **Note (CLAUDE.md):** Docker-dependent Nextflow runs must happen on the main thread, not in a sandboxed subagent. If no ready-made plasmid-bearing test case exists, ask the human to point at one before running this step.

- [ ] **Step 3: Confirm the three acceptance checks on the run outputs**

```bash
OUT=/mnt/internal_hdd/claude_code/tmp/asat_verify
# (i) plasmid is listed as unplaced
cat $OUT/scaffold/testbac_unplaced_contigs.tsv
# (ii) plasmid is still present in the final FASTA, correctly named (not mangled)
grep '>' $OUT/scaffold/testbac_scaffolds.fasta
# (iii) contig count + total length conserved vs RagTag output
grep -c '>' $OUT/scaffold/ragtag.scaffold.fasta $OUT/scaffold/testbac_scaffolds.fasta
```
Expected: (i) the plasmid contig appears as a row; (ii) its header is `testbac_<original_name>` with no lost tokens; (iii) both FASTAs have the same sequence count.

- [ ] **Step 4: Confirm DNAAPLER processed the plasmid**

```bash
ls /mnt/internal_hdd/claude_code/tmp/asat_verify/dnaapler/
```
Expected: dnaapler output exists (default-on for `bacterial`), i.e. the unplaced plasmid was not routed around reorientation.

- [ ] **Step 5: Final cleanup commit (if any docs/comments adjusted during verification)**

Only if verification surfaced a needed tweak; otherwise skip. Do not `git push` (per project policy — the human pushes manually).

---

## Self-Review Notes

- **Spec coverage:** Issue A (dead emit removed — Task 5; sentinel plumbing removed — Task 6; read-only AGP artifact — Tasks 3/4). Issue B (non-destructive rename + pattern — Tasks 1/2). Out-of-scope items (no `-C`, no version-pin change, plasmid-in-reference) are untouched. Acceptance criteria map to Task 8.
- **No `optional: true` masking:** `CLASSIFY_UNPLACED` always emits the TSV (header-only if there are no unplaced contigs), so the new output is never optional. The only removed `optional` was the structurally-absent `unplaced` emit.
- **Type/signature consistency:** `SCAFFOLDING.take` gains `reference_fai` (3rd position); both call sites updated to match. `RENAME_RAGTAG_SCAFFOLDS` drops its 2nd input; its sole caller (scaffolding.nf) updated. `rename_header(name, sample_id, pattern=None)` and `classify(objects)` signatures are used consistently across script and self-tests.
```
