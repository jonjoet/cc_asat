# cc_asat — Scaffolding / Unplaced-Contig Handling Fix Brief

**Status:** issues verified against source; ready to implement in Claude Code.
**Audience:** Claude Code session working in the `cc_asat` repo.
**Scope:** Fix how the scaffolding subworkflow handles contigs that RagTag leaves
unplaced (this is the path plasmids and other extra-chromosomal/unanchored contigs
take). Two confirmed defects plus one naming-safety fix. Do **not** expand scope
beyond what is listed in §3–§5.

---

## 1. Why this brief exists

The scaffolding step is pure RagTag 2.1.0 (`ragtag.py scaffold ... -u`, no `-C`).
The pipeline currently contains a code path intended to separate unplaced contigs
into their own file, but that path is **dead** — it keys on an output file RagTag
never produces — so it silently does nothing. Separately, the header-renaming script
mangles contig names in a way that destroys plasmid/contig identity. Neither is
caught by any test because nothing errors; the outputs are just wrong/misleading.

These were found by reading the pinned RagTag source (tag `v2.1.0`), not from docs.
The facts in §2 are verified there and should be treated as ground truth — please do
not "fix" the code back toward the incorrect assumptions.

## 2. Ground truth: what RagTag 2.1.0 actually does here

With the exact invocation in `modules/local/ragtag/scaffold/main.nf`
(`ragtag.py scaffold <reference> <assembly> -o ragtag_out -u -t <cpus>`):

- RagTag writes **`ragtag.scaffold.fasta`**, `.agp`, `.stats`, `.confidence.txt`
  (plus `.asm.*`/`.debug.*` intermediates). It does **not** write any
  `ragtag.scaffold.unplaced.fasta`. No such filename exists anywhere in RagTag.
- The output FASTA is generated **from the AGP**, so every query contig appears in
  it exactly once. Nothing is dropped.
- **Placed** contigs are grouped into scaffold objects named `<reference_seq>_RagTag`.
- **Unplaced** contigs (no alignment good enough to anchor — e.g. a plasmid whose
  homolog is absent from the reference) are written **individually** into that same
  FASTA. Because `-u` is set, each gets its original name plus a `_RagTag` suffix.
  They are *not* concatenated into a `Chr0` pseudomolecule — that only happens with
  `-C`, which this pipeline does not pass (and should not: `-C` would fuse all
  plasmids/unplaced contigs into one sequence).
- In the AGP, an unplaced contig is its own object: exactly one `W` component line,
  no gap (`N`/`U`) lines, and the component id (column 6) equals the object name with
  the trailing `_RagTag` stripped. A placed single-contig chromosome also has one `W`
  line and no gaps, but its object name is the *reference* name, so the component id
  does **not** equal the object basename. That difference is the reliable
  placed-vs-unplaced discriminator (see §3).

## 3. Issue A — dead unplaced output, plus no real unplaced artifact

**Locations**
- `modules/local/ragtag/scaffold/main.nf` — declares
  `path "ragtag_out/ragtag.scaffold.unplaced.fasta", emit: unplaced, optional: true`.
  RagTag never creates this file, so the channel is always empty. `optional: true`
  hides the problem.
- `subworkflows/local/scaffolding.nf` —
  `ch_unplaced = RAGTAG_SCAFFOLD.out.unplaced.ifEmpty(file('NO_FILE'))`. Because the
  upstream channel is always empty, `ch_unplaced` is always the `NO_FILE` sentinel.
- `modules/local/rename_ragtag_scaffolds/main.nf` — its `handle_unplaced` branch is
  gated on `unplaced.name != 'NO_FILE'`, which is therefore never true. The whole
  `<sample>_unplaced.fasta` emit path never fires.

**Net effect:** unplaced contigs (including plasmids when the plasmid is absent from
the reference) are silently carried inside the main `<sample>_scaffolds.fasta` with no
separation, no label, and no record of which contigs failed to anchor. The pipeline
*appears* to separate them but does not.

**Desired behavior**
1. Remove the false `emit: unplaced` from the scaffold module (it can never fire) and
   the dead `NO_FILE`-sentinel plumbing that depends on it, so the code stops implying
   a separation that doesn't happen.
2. Add a **non-destructive** QC artifact derived from `ragtag.scaffold.agp` that lists
   (and optionally extracts to FASTA) the contigs RagTag left unplaced. Publish it to
   the results directory. Classification rule, from §2: an AGP object is *unplaced* iff
   it has exactly one `W` component, no gap lines, and component-id (col 6) ==
   object-name with a trailing `_RagTag` removed. Everything else is placed. (Optional
   belt-and-suspenders: cross-check object basenames against the reference `.fai`,
   which `SAMTOOLS_FAIDX` already produces in `euk_scaffold_validation.nf`.)

**Design decision to confirm with the human before coding — do not guess**
Should unplaced contigs be (a) **kept** in the single main FASTA (recommended) with the
new artifact being purely informational, or (b) **removed** from the main FASTA into a
separate file?

> Recommendation: **(a), keep them in the main FASTA.** Downstream steps —
> `TGS_GAPCLOSER`, optional `RAGTAG_PATCH`, `DNAAPLER`, `QUAST`, and annotation
> transfer — all consume the single scaffold channel. `DNAAPLER` (default-on for
> bacterial) is the step that actually reorients circular plasmids to a canonical
> start, and annotation transfer should be able to annotate plasmid genes. Splitting
> unplaced contigs *out* of the main channel would route plasmids around exactly the
> steps that are supposed to process them. So the fix should make unplaced contigs
> **visible** (and correctly named — see Issue B), not exile them.

**Acceptance criteria**
- Pipeline runs with no reference to a non-existent `ragtag.scaffold.unplaced.fasta`.
- A results file lists every contig RagTag left unplaced for a test input; for an input
  with a plasmid not present in the reference, that plasmid contig appears in the list.
- The main `<sample>_scaffolds.fasta` still contains every input contig (placed +
  unplaced); contig count and total length are conserved vs the RagTag output.
- No `optional: true` is masking a structurally-absent file in the changed code.

## 4. Issue B — header rename destroys contig identity

**Location:** `bin/rename_ragtag_scaffolds.py`, function `rename_header`.

The current logic, after stripping a `_RagTag` suffix, does:

```python
if "_" in name:
    name = name[name.index("_") + 1:]   # "strip stale sample-id prefix"
return f">{sample_id}_{name}"
```

This unconditionally deletes everything up to and including the **first underscore**,
on the assumption that it's a stale sample-id prefix. For real contig names that is
destructive and lossy:

- `contig_3` (Flye) → `3` → `sample_3`
- `2micron_plasmid` → `plasmid` → `sample_2micron` becomes `sample_plasmid`
- any descriptive header with an underscore loses its first token, and distinct
  contigs can collide to the same final name.

This hits unplaced contigs hardest — i.e. exactly the plasmids from Issue A — so the
one class of sequence a user most wants to identify becomes the least identifiable.

**Desired behavior:** stop eating arbitrary leading tokens. Only strip a leading prefix
when it is genuinely a previously-applied sample-id (idempotency for re-runs), i.e.
strip `"<sample_id>_"` only when the name actually starts with it; otherwise preserve
the original contig name verbatim. Do not split on "first underscore."

**Acceptance criteria**
- `contig_3`, with `--sample-id S` → `S_contig_3` (name preserved).
- `2micron_plasmid` → `S_2micron_plasmid`.
- Idempotent on re-run: a header already named `S_contig_3` does not become
  `S_S_contig_3` and does not lose `contig_3`.
- No two distinct input contigs map to the same output header on a realistic assembly.
- Add a couple of unit assertions covering these cases (the script is pure stdlib;
  small inline tests are fine — do not add a new test framework).

## 5. Out of scope / known limitations — leave alone

These are inherent RagTag behavior, **not** bugs in this repo. Do not try to fix them
here; just don't regress them:

- **Plasmid present in the reference.** RagTag treats the reference plasmid as a
  "chromosome" and will order/orient the assembly plasmid against it. For a clean
  single circular contig this is near-benign (mostly orientation); RagTag is linear
  scaffolding over a circular molecule, so origin/rotation follows the alignment, and
  small or repeat-sharing plasmids may fall below `-f 1000` / `-q 10` and stay
  unplaced. Canonical plasmid reorientation is `DNAAPLER`'s job, not scaffolding's.
- Do **not** add `-C` to the RagTag invocation to "collect" unplaced contigs — it
  would concatenate all of them into a single `Chr0` pseudomolecule.
- Do not change RagTag's version pin (`bioconda::ragtag=2.1.0`) as part of this work.

## 6. Verification

- A unit-level check of the AGP classifier in §3 against a small hand-written AGP that
  contains: a multi-contig placed scaffold, a single-contig placed chromosome, and an
  unplaced contig — assert only the last is classified unplaced.
- An end-to-end `-resume` run on an existing test case with `--organism_type bacterial`
  and an assembly that includes a plasmid absent from the reference: confirm the
  plasmid is (i) listed in the new unplaced artifact, (ii) still present and correctly
  named in the final FASTA, (iii) processed by `DNAAPLER`.
- Confirm `nextflow run` no longer references the non-existent unplaced filename and
  that removing the dead path didn't break the `RENAME_RAGTAG_SCAFFOLDS` signature
  used by `scaffolding.nf`.
