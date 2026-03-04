#!/usr/bin/env python3
"""
Replace generic Name attributes in a GFF3 file with informative alternatives.

Post-Liftoff, many features retain generic names like "gene-1" or
"hypothetical protein" that are unhelpful in genome browsers. This script
searches each feature's own attributes and its children's attributes for
a more informative value (product, description, locus_tag, gene) and
promotes the best one to the Name field.

Requires gffutils.
"""

import argparse
import re
import sys

import gffutils

# ---------------------------------------------------------------------------
# Shared constants (also used by merge_annotations.py)
# ---------------------------------------------------------------------------

GENERIC_VALUES = {
    'hypothetical protein',
    'conserved protein of unknown function',
    'protein of unknown function',
    'unnamed protein product',
    'unknown protein',
    'uncharacterized protein',
}

GENERIC_PATTERN = re.compile(r'^(gene|cds|mrna|rna|exon)-?\d+$', re.IGNORECASE)

# Priority order for replacement candidates
REPLACEMENT_KEYS = ('product', 'description', 'locus_tag', 'gene')


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--input', required=True, help='Input GFF3 file')
    p.add_argument('--output', required=True, help='Output GFF3 file with fixed names')
    p.add_argument('--summary', default=None,
                   help='Optional summary report of name changes')
    return p.parse_args()


def is_generic(value):
    """Check if a Name value is generic/uninformative."""
    if not value:
        return True
    v = value.strip()
    if not v or v == '.':
        return True
    if v.lower() in {g.lower() for g in GENERIC_VALUES}:
        return True
    if GENERIC_PATTERN.match(v):
        return True
    return False


def get_attr_first(feature, key):
    """Get the first value of a GFF attribute, or None."""
    vals = feature.attributes.get(key, [])
    if vals:
        return vals[0]
    return None


def find_replacement(feature, db):
    """Find a non-generic replacement for a feature's Name.

    Checks the feature itself first, then its children (mRNA, CDS).
    Returns (replacement_value, source_key) or (None, None).
    """
    # Check own attributes
    for key in REPLACEMENT_KEYS:
        val = get_attr_first(feature, key)
        if val and not is_generic(val):
            return val, key

    # Check children's attributes
    try:
        children = list(db.children(feature, level=1))
    except gffutils.FeatureNotFoundError:
        children = []

    for child in children:
        for key in REPLACEMENT_KEYS:
            val = get_attr_first(child, key)
            if val and not is_generic(val):
                return val, f"child({child.featuretype}).{key}"

    return None, None


def build_db(gff_path):
    """Build an in-memory gffutils database from a GFF3 file."""
    print(f"Loading {gff_path} into gffutils database...", file=sys.stderr)
    db = gffutils.create_db(
        gff_path,
        ':memory:',
        merge_strategy='merge',
        sort_attribute_values=True,
        force=True,
    )
    return db


def fix_names(db):
    """Collect rename decisions for all features with generic Names.

    Returns:
      changes:  list of (feature_id, featuretype, old_name, new_name, source_key)
      renames:  dict of {feature_id: (new_name, old_name)}
    """
    changes = []
    renames = {}

    for feature in db.all_features():
        name = get_attr_first(feature, 'Name')
        if name is None:
            continue
        if not is_generic(name):
            continue

        replacement, source_key = find_replacement(feature, db)
        if replacement is None:
            continue

        renames[feature.id] = (replacement, name)
        changes.append((
            feature.id,
            feature.featuretype,
            name,
            replacement,
            source_key,
        ))

    return changes, renames


def write_output(db, output_path, renames):
    """Write all features to GFF3, applying renames during output."""
    count = 0
    with open(output_path, 'w') as out:
        out.write('##gff-version 3\n')
        for feature in db.all_features(order_by=('seqid', 'start')):
            if feature.id in renames:
                new_name, old_name = renames[feature.id]
                feature.attributes['Name'] = [new_name]
                feature.attributes['original_name'] = [old_name]
            out.write(str(feature) + '\n')
            count += 1
    print(f"Wrote {count} features", file=sys.stderr)


def write_summary(summary_path, changes):
    """Write a human-readable summary of name changes."""
    with open(summary_path, 'w') as out:
        out.write('=' * 60 + '\n')
        out.write('GFF NAME FIX SUMMARY\n')
        out.write('=' * 60 + '\n')
        out.write(f'Features renamed: {len(changes)}\n\n')

        if not changes:
            out.write('No generic names found to replace.\n')
        else:
            for feat_id, ftype, old, new, source in changes:
                out.write(f"  {feat_id} ({ftype}): "
                          f'"{old}" -> "{new}" [from {source}]\n')

        out.write('=' * 60 + '\n')


def main():
    args = parse_args()

    db = build_db(args.input)
    changes, renames = fix_names(db)

    print(f"Renamed {len(changes)} features", file=sys.stderr)

    write_output(db, args.output, renames)

    if args.summary:
        write_summary(args.summary, changes)

    print("Done.", file=sys.stderr)


if __name__ == '__main__':
    main()
