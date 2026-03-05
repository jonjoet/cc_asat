#!/usr/bin/env python3
"""
Compare primary (no -copies) and copies Liftoff outputs to identify extra copies.

Parses both GFF3 files and reports features present in the copies output but
absent from the primary output. These are gene copies detected by Liftoff's
-copies mode.

Uses only stdlib — runs in python:3.12 container.
"""

import argparse
import sys
from collections import defaultdict


def parse_gff_features(path):
    """Parse GFF3 file, return dict of feature_id -> feature info."""
    features = {}
    with open(path) as f:
        for line in f:
            if line.startswith('#'):
                continue
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) != 9:
                continue
            seqid, source, ftype, start, end, score, strand, phase, attrs_str = parts
            attrs = {}
            for item in attrs_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, val = item.split('=', 1)
                    attrs[key] = val
            fid = attrs.get('ID', '')
            if fid:
                features[fid] = {
                    'seqid': seqid,
                    'start': int(start),
                    'end': int(end),
                    'strand': strand,
                    'type': ftype,
                    'attrs': attrs,
                }
    return features


def find_parent_gene(feature, all_features):
    """Walk Parent chain to find the top-level gene ID."""
    visited = set()
    current = feature
    while current:
        fid = current['attrs'].get('ID', '')
        if fid in visited:
            break
        visited.add(fid)
        if current['type'] == 'gene':
            return fid
        parent_id = current['attrs'].get('Parent', '')
        if parent_id and parent_id in all_features:
            current = all_features[parent_id]
        else:
            break
    return ''


def get_extra_copy_number(attrs):
    """Extract extra_copy_number from attributes, return as string or empty."""
    return attrs.get('extra_copy_number', '')


def main():
    parser = argparse.ArgumentParser(
        description='Diff primary vs copies Liftoff output to identify extra copies')
    parser.add_argument('--primary', required=True, help='Primary Liftoff GFF3 (no -copies)')
    parser.add_argument('--copies', required=True, help='Copies Liftoff GFF3 (with -copies)')
    parser.add_argument('--output', required=True, help='Output copy report (TSV)')
    args = parser.parse_args()

    primary_features = parse_gff_features(args.primary)
    copies_features = parse_gff_features(args.copies)

    primary_ids = set(primary_features.keys())
    copies_only_ids = set(copies_features.keys()) - primary_ids

    # Collect gene-level extra copies
    extra_genes = []
    extra_other = []
    for fid in sorted(copies_only_ids):
        feat = copies_features[fid]
        ecn = get_extra_copy_number(feat['attrs'])
        parent_gene = find_parent_gene(feat, copies_features)
        entry = {
            'seqid': feat['seqid'],
            'start': feat['start'],
            'end': feat['end'],
            'strand': feat['strand'],
            'type': feat['type'],
            'id': fid,
            'parent_gene': parent_gene,
            'extra_copy_number': ecn,
            'name': feat['attrs'].get('Name', ''),
        }
        if feat['type'] == 'gene':
            extra_genes.append(entry)
        else:
            extra_other.append(entry)

    # Write report
    with open(args.output, 'w') as out:
        out.write('# Liftoff Copy Analysis Report\n')
        out.write(f'# Primary features: {len(primary_features)}\n')
        out.write(f'# Copies features: {len(copies_features)}\n')
        out.write(f'# Extra copy features: {len(copies_only_ids)}\n')
        out.write(f'# Extra copy genes: {len(extra_genes)}\n')
        out.write('#\n')
        out.write('seqid\tstart\tend\tstrand\ttype\tfeature_id\tparent_gene\textra_copy_number\tname\n')
        for entry in extra_genes + extra_other:
            out.write('{seqid}\t{start}\t{end}\t{strand}\t{type}\t{id}\t{parent_gene}\t{extra_copy_number}\t{name}\n'.format(**entry))

    # Summary to stderr
    print(f'Primary features: {len(primary_features)}', file=sys.stderr)
    print(f'Copies features: {len(copies_features)}', file=sys.stderr)
    print(f'Extra copy features: {len(copies_only_ids)}', file=sys.stderr)
    print(f'Extra copy genes: {len(extra_genes)}', file=sys.stderr)


if __name__ == '__main__':
    main()
