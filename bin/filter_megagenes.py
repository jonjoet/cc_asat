#!/usr/bin/env python3
"""
Filter artifactual mega-genes from a GFF3 file.

Mega-genes are spurious gene features (often created by AGAT's GFF3 fixing)
that span large genomic regions encompassing many real genes. Detection uses
two configurable criteria (either triggers removal):

  1. Containment count: gene overlaps more than --gene-threshold other genes
  2. Absolute length: gene longer than --max-length-bp (disabled when 0)

Requires gffutils.
"""

import argparse
import sys
from collections import defaultdict

import gffutils


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', required=True, help='Input GFF3 file')
    p.add_argument('--output', required=True, help='Output filtered GFF3 file')
    p.add_argument('--summary', required=True, help='Summary report of removed genes')
    p.add_argument('--gene-threshold', type=int, default=5,
                   help='Max overlapping genes before flagging as megagene (default: 5)')
    p.add_argument('--max-length-bp', type=int, default=0,
                   help='Max gene length in bp; 0 = disabled (default: 0)')
    return p.parse_args()


def build_db(gff_path):
    """Build an in-memory gffutils database from a GFF3 file."""
    print(f"Loading {gff_path} into gffutils database...", file=sys.stderr)
    db = gffutils.create_db(
        gff_path,
        ':memory:',
        merge_strategy='create_unique',
        sort_attribute_values=True,
        force=True,
    )
    return db


def find_megagenes(db, gene_threshold, max_length_bp):
    """Identify megagene IDs and their reasons for removal.

    Returns dict of {gene_id: {seqid, start, end, length, overlap_count, reason}}.
    """
    megagenes = {}
    genes = list(db.features_of_type('gene'))
    print(f"Scanning {len(genes)} genes for megagene artifacts...", file=sys.stderr)

    for gene in genes:
        length = gene.end - gene.start + 1

        # Count overlapping genes (exclude self)
        overlapping = list(db.region(
            seqid=gene.seqid,
            start=gene.start,
            end=gene.end,
            featuretype='gene',
        ))
        overlap_count = sum(1 for g in overlapping if g.id != gene.id)

        reasons = []
        if overlap_count > gene_threshold:
            reasons.append(f"overlaps {overlap_count} genes (threshold: {gene_threshold})")
        if max_length_bp > 0 and length > max_length_bp:
            reasons.append(f"length {length} bp exceeds {max_length_bp} bp")

        if reasons:
            megagenes[gene.id] = {
                'seqid': gene.seqid,
                'start': gene.start,
                'end': gene.end,
                'length': length,
                'overlap_count': overlap_count,
                'reason': '; '.join(reasons),
            }

    return megagenes


def collect_descendants(db, gene_ids):
    """Collect all descendant feature IDs for a set of gene IDs."""
    to_remove = set(gene_ids)
    for gene_id in gene_ids:
        try:
            for child in db.children(gene_id, level=None):
                to_remove.add(child.id)
        except gffutils.FeatureNotFoundError:
            pass
    return to_remove


def write_filtered_gff(db, output_path, ids_to_remove):
    """Write GFF3, skipping features whose IDs are in ids_to_remove."""
    removed_count = 0
    kept_count = 0
    with open(output_path, 'w') as out:
        out.write('##gff-version 3\n')
        for feature in db.all_features(order_by=('seqid', 'start')):
            if feature.id in ids_to_remove:
                removed_count += 1
            else:
                out.write(str(feature) + '\n')
                kept_count += 1
    print(f"Wrote {kept_count} features ({removed_count} removed)", file=sys.stderr)


def write_summary(summary_path, megagenes):
    """Write a human-readable summary of removed megagenes."""
    with open(summary_path, 'w') as out:
        out.write('=' * 60 + '\n')
        out.write('MEGAGENE FILTER SUMMARY\n')
        out.write('=' * 60 + '\n')
        out.write(f'Megagenes removed: {len(megagenes)}\n\n')

        if not megagenes:
            out.write('No megagenes detected.\n')
        else:
            for gene_id, info in sorted(megagenes.items(),
                                         key=lambda x: (x[1]['seqid'], x[1]['start'])):
                out.write(f"  {info['seqid']}:{info['start']}-{info['end']}  "
                          f"{gene_id}  length={info['length']}  "
                          f"overlapping_genes={info['overlap_count']}  "
                          f"reason: {info['reason']}\n")

        out.write('=' * 60 + '\n')


def main():
    args = parse_args()

    db = build_db(args.input)
    megagenes = find_megagenes(db, args.gene_threshold, args.max_length_bp)

    if megagenes:
        print(f"Found {len(megagenes)} megagene(s) to remove", file=sys.stderr)
        ids_to_remove = collect_descendants(db, megagenes.keys())
    else:
        print("No megagenes detected", file=sys.stderr)
        ids_to_remove = set()

    write_filtered_gff(db, args.output, ids_to_remove)
    write_summary(args.summary, megagenes)

    print("Done.", file=sys.stderr)


if __name__ == '__main__':
    main()
