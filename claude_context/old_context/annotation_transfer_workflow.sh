#!/bin/bash
# annotation_transfer_workflow.sh
#
# Complete workflow for transferring annotations to a scaffolded yeast assembly.
# Combines Liftoff (reference annotations) with vendor novel annotations.
#
# Prerequisites:
#   pip install liftoff intervaltree
#   conda install -c bioconda minimap2 samtools  # liftoff dep
#
# Usage:
#   bash annotation_transfer_workflow.sh \
#     scaffolded_assembly.fasta \
#     reference.fasta \
#     reference_annotation.gff3 \
#     vendor_annotation.gff \
#     ragtag.scaffold.agp \
#     output_dir

set -euo pipefail

SCAFFOLDED=$1       # RagTag scaffolded assembly FASTA
REFERENCE=$2        # Reference genome FASTA (e.g., S288C)
REF_GFF=$3          # Reference annotation GFF3 (e.g., from SGD)
VENDOR_GFF=$4       # Vendor annotation GFF (Plasmidsaurus, contig coordinates)
AGP=$5              # RagTag scaffold AGP file
OUTDIR=$6

mkdir -p ${OUTDIR}

echo "============================================"
echo "ANNOTATION TRANSFER PIPELINE"
echo "============================================"

# ── Step 1: Liftoff — transfer reference annotations ──────────────────────
# Liftoff uses minimap2 to align reference genes to the new assembly
# and transfers annotations with proper handling of structural changes.
echo ""
echo "Step 1: Running Liftoff (reference → scaffolded assembly)..."

liftoff \
  -g ${REF_GFF} \
  -o ${OUTDIR}/liftoff_output.gff3 \
  -u ${OUTDIR}/liftoff_unmapped.txt \
  -dir ${OUTDIR}/liftoff_intermediate \
  -p 8 \
  -copies \
  ${SCAFFOLDED} \
  ${REFERENCE}

# -copies: also look for extra gene copies (useful for detecting
#          duplication events in engineered strains)
# -u: report unmapped features (reference genes missing from assembly)

echo "  Liftoff complete."
echo "  Mapped features: $(grep -c -v '^#' ${OUTDIR}/liftoff_output.gff3 || true)"
echo "  Unmapped features: $(wc -l < ${OUTDIR}/liftoff_unmapped.txt || echo 0)"

# ── Step 2: Merge novel vendor annotations ────────────────────────────────
echo ""
echo "Step 2: Identifying and merging novel vendor annotations..."

python novel_annotation_transfer.py \
  --agp ${AGP} \
  --liftoff ${OUTDIR}/liftoff_output.gff3 \
  --vendor ${VENDOR_GFF} \
  --output ${OUTDIR}/merged_annotations.gff3 \
  --max-overlap 0.50 \
  --min-overlap 0.10 \
  --summary ${OUTDIR}/merge_summary.txt

# ── Step 3: Quick sanity checks ──────────────────────────────────────────
echo ""
echo "Step 3: Sanity checks..."

# Count features by source
echo "Features by annotation source:"
grep -v '^#' ${OUTDIR}/merged_annotations.gff3 | \
  grep -oP 'annotation_source=[^;]+' | \
  sort | uniq -c | sort -rn

# Check for any novel features that look like transposable elements
echo ""
echo "Potential transposable elements in novel features:"
grep 'annotation_source=vendor_novel' ${OUTDIR}/merged_annotations.gff3 | \
  grep -iE 'transpos|LTR|Ty[0-9]|retro|repeat' || echo "  (none found)"

# List unplaced features (could be plasmids, mito, contamination)
echo ""
echo "Unplaced contig features:"
grep 'annotation_source=vendor_unplaced' ${OUTDIR}/merged_annotations.gff3 | \
  awk -F'\t' '{print $1, $3, $4"-"$5}' | head -20 || echo "  (none)"

echo ""
echo "============================================"
echo "DONE"
echo "============================================"
echo "Outputs:"
echo "  Merged GFF:       ${OUTDIR}/merged_annotations.gff3"
echo "  Liftoff output:   ${OUTDIR}/liftoff_output.gff3"
echo "  Unmapped genes:   ${OUTDIR}/liftoff_unmapped.txt"
echo "  Merge summary:    ${OUTDIR}/merge_summary.txt"
echo ""
echo "Review recommendations:"
echo "  1. Check liftoff_unmapped.txt for missing reference genes"
echo "  2. Review 'flagged' features in merge_summary.txt"
echo "  3. BLAST any novel features you don't recognize"
echo "  4. Load merged_annotations.gff3 in IGV with the scaffolded assembly"
