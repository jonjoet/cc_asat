#!/usr/bin/env python3
"""
merge_annotations.py

Symmetric identity-based merge of two GFF3 annotation sets (reference and
vendor), both already lifted onto the same coordinate space.

Matching logic (requires BOTH for a full match):
  1. Reciprocal CDS overlap >= threshold
  2. At least one shared identifier (case-insensitive)

Classification:
  - Full match:     CDS overlap + identifier match → merged into one feature
  - Partial (pos):  CDS overlap met, no identifier match → both kept, tagged
  - Partial (id):   Identifier match, CDS overlap not met → both kept, tagged
  - Unmatched:      Neither condition → kept as-is

Requires gffutils.
"""

import argparse
import re
import sys
from collections import defaultdict

import gffutils

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

# Default fields for exact matching (structured identifiers)
DEFAULT_EXACT_FIELDS = ('ID', 'Name', 'gene', 'locus_tag')

# Default fields for word-level matching (free-text annotations)
DEFAULT_WORD_FIELDS = ('product', 'description')

# Kept for GENERIC_VALUES / GENERIC_PATTERN filtering (used by both modes)
IDENTIFIER_KEYS = DEFAULT_EXACT_FIELDS + DEFAULT_WORD_FIELDS

GENERIC_VALUES = {
    'hypothetical protein', 'conserved protein of unknown function',
    'protein of unknown function', 'unnamed protein product',
    'unknown protein', 'uncharacterized protein',
}
GENERIC_PATTERN = re.compile(r'^(gene|cds|mrna|rna|exon)-?\d+$', re.IGNORECASE)

# Descriptive attribute keys used for description preference merging
DESCRIPTION_KEYS = ('Name', 'product', 'description')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_generic(value):
    """Check if a value is generic/uninformative."""
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
    return vals[0] if vals else None


def get_description_str(feature):
    """Return best human-readable label for a feature."""
    for key in ('product', 'description', 'Name', 'ID'):
        val = get_attr_first(feature, key)
        if val and not is_generic(val):
            return val
    return 'unknown'


# ---------------------------------------------------------------------------
# Database loading
# ---------------------------------------------------------------------------

def load_db(gff_path, label):
    """Load a GFF3 file into an in-memory gffutils database."""
    print(f"Loading {label} GFF: {gff_path}", file=sys.stderr)
    db = gffutils.create_db(
        gff_path,
        ':memory:',
        merge_strategy='create_unique',
        sort_attribute_values=True,
        force=True,
    )
    return db


# ---------------------------------------------------------------------------
# Identifier collection
# ---------------------------------------------------------------------------

def _tokenize(value, min_length):
    """Split a free-text value into lowercase word tokens of at least min_length."""
    return {w.lower() for w in re.findall(r'[A-Za-z0-9]+', value)
            if len(w) >= min_length}


def collect_identifiers(gene, db, exact_fields, word_fields, word_min_length):
    """Collect non-generic identifiers from a gene and all its descendants.

    Exact fields are matched as whole lowercase strings.
    Word fields are tokenized into individual words (>= word_min_length chars).

    Returns a set of lowercase tokens suitable for intersection testing.
    """
    ids = set()

    def _harvest(feature):
        for key in exact_fields:
            for val in feature.attributes.get(key, []):
                if val and not is_generic(val):
                    ids.add(val.lower())
        for key in word_fields:
            for val in feature.attributes.get(key, []):
                if val and not is_generic(val):
                    ids.update(_tokenize(val, word_min_length))

    _harvest(gene)
    try:
        for child in db.children(gene.id, level=None):
            _harvest(child)
    except Exception:
        pass

    return ids


# ---------------------------------------------------------------------------
# CDS footprint computation
# ---------------------------------------------------------------------------

def cds_footprint(gene, db):
    """Compute the union of CDS intervals under a gene.

    Returns a set of 1-based positions (covered bases). If no CDS children
    exist, falls back to the gene span itself.
    """
    positions = set()
    try:
        cds_features = list(db.children(gene, featuretype='CDS', level=None))
    except gffutils.FeatureNotFoundError:
        cds_features = []

    if cds_features:
        for cds in cds_features:
            positions.update(range(cds.start, cds.end + 1))
    else:
        # Fallback: use gene span (for non-coding genes, tRNAs, etc.)
        positions.update(range(gene.start, gene.end + 1))

    return positions


def reciprocal_cds_overlap(fp_a, fp_b):
    """Compute reciprocal CDS overlap fraction.

    Returns overlap_bases / min(len(fp_a), len(fp_b)), or 0.0 if either is empty.
    """
    if not fp_a or not fp_b:
        return 0.0
    overlap = len(fp_a & fp_b)
    denominator = min(len(fp_a), len(fp_b))
    return overlap / denominator if denominator > 0 else 0.0


# ---------------------------------------------------------------------------
# Gene collection and spatial indexing
# ---------------------------------------------------------------------------

def collect_genes(db):
    """Collect all gene-level features from a database."""
    return list(db.features_of_type('gene'))


def build_spatial_index(genes):
    """Build a per-seqid dict of gene lists for spatial lookup."""
    by_seqid = defaultdict(list)
    for gene in genes:
        by_seqid[gene.seqid].append(gene)
    # Sort by start position within each seqid
    for seqid in by_seqid:
        by_seqid[seqid].sort(key=lambda g: g.start)
    return by_seqid


def find_overlapping_genes(gene, genes_by_seqid):
    """Find genes on the same seqid whose span overlaps the given gene."""
    candidates = genes_by_seqid.get(gene.seqid, [])
    result = []
    for g in candidates:
        if g.start > gene.end:
            break
        if g.end >= gene.start:
            result.append(g)
    return result


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def find_all_candidates(ref_genes, vendor_genes, ref_db, vendor_db,
                        vendor_by_seqid, overlap_threshold,
                        exact_fields, word_fields, word_min_length):
    """Find all candidate match pairs between reference and vendor genes.

    Returns three lists:
      full_matches:    [(ref_gene, vendor_gene, overlap_frac, matched_ids)]
      partial_pos:     [(ref_gene, vendor_gene, overlap_frac)]
      partial_id:      [(ref_gene, vendor_gene, matched_ids)]
    """
    full_matches = []
    partial_pos = []
    partial_id = []

    # Pre-compute ref footprints and identifiers
    ref_fps = {}
    ref_ids = {}
    for rg in ref_genes:
        ref_fps[rg.id] = cds_footprint(rg, ref_db)
        ref_ids[rg.id] = collect_identifiers(rg, ref_db,
                                              exact_fields, word_fields, word_min_length)

    # Pre-compute vendor footprints and identifiers
    vendor_fps = {}
    vendor_ids = {}
    for vg in vendor_genes:
        vendor_fps[vg.id] = cds_footprint(vg, vendor_db)
        vendor_ids[vg.id] = collect_identifiers(vg, vendor_db,
                                                 exact_fields, word_fields, word_min_length)

    for rg in ref_genes:
        r_fp = ref_fps[rg.id]
        r_ids = ref_ids[rg.id]

        overlapping_vendors = find_overlapping_genes(rg, vendor_by_seqid)

        for vg in overlapping_vendors:
            v_fp = vendor_fps[vg.id]
            v_ids = vendor_ids[vg.id]

            overlap_frac = reciprocal_cds_overlap(r_fp, v_fp)
            has_overlap = overlap_frac >= overlap_threshold
            matched_ids = r_ids & v_ids

            if has_overlap and matched_ids:
                full_matches.append((rg, vg, overlap_frac, matched_ids))
            elif has_overlap:
                partial_pos.append((rg, vg, overlap_frac))
            elif matched_ids:
                partial_id.append((rg, vg, matched_ids))

    return full_matches, partial_pos, partial_id


def resolve_full_matches(full_matches):
    """Greedy best-first resolution of full matches.

    Each gene participates in at most one match. Sorts by overlap fraction
    descending and assigns greedily.

    Returns list of resolved (ref_gene, vendor_gene, overlap_frac, matched_ids).
    """
    full_matches.sort(key=lambda x: x[2], reverse=True)

    used_ref = set()
    used_vendor = set()
    resolved = []

    for rg, vg, frac, ids in full_matches:
        if rg.id in used_ref or vg.id in used_vendor:
            continue
        resolved.append((rg, vg, frac, ids))
        used_ref.add(rg.id)
        used_vendor.add(vg.id)

    return resolved


def resolve_partials(partial_list, matched_ref_ids, matched_vendor_ids, is_pos=True):
    """Filter partial matches to only include unmatched genes.

    Returns list of tuples with only genes not already in a full match.
    """
    resolved = []
    for entry in partial_list:
        rg = entry[0]
        vg = entry[1]
        if rg.id in matched_ref_ids or vg.id in matched_vendor_ids:
            continue
        resolved.append(entry)
    return resolved


# ---------------------------------------------------------------------------
# Output GFF construction
# ---------------------------------------------------------------------------

def merge_matched_gene(ref_gene, vendor_gene, ref_db, vendor_db,
                       coord_pref, desc_pref, overlap_frac, matched_ids):
    """Merge a matched gene pair into output GFF lines.

    Returns list of GFF3 line strings.
    """
    # Choose coordinate source
    if coord_pref == 'vendor':
        coord_gene, other_gene = vendor_gene, ref_gene
        coord_db, other_db = vendor_db, ref_db
    else:
        coord_gene, other_gene = ref_gene, vendor_gene
        coord_db, other_db = ref_db, vendor_db

    # Choose description source
    if desc_pref == 'vendor':
        desc_gene, fallback_gene = vendor_gene, ref_gene
        desc_db, fallback_db = vendor_db, ref_db
    else:
        desc_gene, fallback_gene = ref_gene, vendor_gene
        desc_db, fallback_db = ref_db, vendor_db

    lines = []

    # Build merged gene feature from coord source
    merged = _clone_feature(coord_gene)

    # Apply description preference
    for key in DESCRIPTION_KEYS:
        pref_val = get_attr_first(desc_gene, key)
        fallback_val = get_attr_first(fallback_gene, key)
        if pref_val and not is_generic(pref_val):
            merged.attributes[key] = [pref_val]
        elif fallback_val and not is_generic(fallback_val):
            merged.attributes[key] = [fallback_val]

    # Merge unique attributes from the other source
    for key, vals in other_gene.attributes.items():
        if key in merged.attributes:
            existing = merged.attributes[key]
            if existing != vals and key not in ('ID', 'Parent'):
                # Store conflicting values with prefix
                if coord_pref == 'vendor':
                    merged.attributes[f'ref_{key}'] = vals
                else:
                    merged.attributes[f'vendor_{key}'] = vals
        else:
            merged.attributes[key] = vals

    # Add merge metadata
    merged.attributes['annotation_source'] = ['merged']
    merged.attributes['ref_id'] = [ref_gene.id]
    merged.attributes['vendor_id'] = [vendor_gene.id]

    lines.append(str(merged))

    # Merge children: use coord source's children as base
    try:
        coord_children = list(coord_db.children(coord_gene, level=1,
                                                 order_by='start'))
    except gffutils.FeatureNotFoundError:
        coord_children = []

    for child in coord_children:
        merged_child = _clone_feature(child)
        merged_child.attributes['annotation_source'] = ['merged']
        lines.append(str(merged_child))

        # Recurse into grandchildren
        try:
            grandchildren = list(coord_db.children(child, level=1,
                                                    order_by='start'))
        except gffutils.FeatureNotFoundError:
            grandchildren = []
        for gc in grandchildren:
            merged_gc = _clone_feature(gc)
            merged_gc.attributes['annotation_source'] = ['merged']
            lines.append(str(merged_gc))

    return lines


def _clone_feature(feature):
    """Create a shallow copy of a gffutils Feature for modification."""
    # gffutils features can be recreated from string representation
    return gffutils.feature.feature_from_line(str(feature))


def emit_gene_with_children(gene, db, source_tag, extra_note=None):
    """Emit a gene and all its descendants as GFF3 lines.

    Returns list of GFF3 line strings.
    """
    lines = []

    cloned = _clone_feature(gene)
    cloned.attributes['annotation_source'] = [source_tag]
    if extra_note:
        existing_notes = cloned.attributes.get('Note', [])
        existing_notes.append(extra_note)
        cloned.attributes['Note'] = existing_notes
    lines.append(str(cloned))

    try:
        for child in db.children(gene, level=None, order_by='start'):
            cc = _clone_feature(child)
            cc.attributes['annotation_source'] = [source_tag]
            lines.append(str(cc))
    except gffutils.FeatureNotFoundError:
        pass

    return lines


def build_output_lines(resolved_full, partial_pos, partial_id,
                       unmatched_ref, unmatched_vendor,
                       ref_db, vendor_db,
                       coord_pref, desc_pref,
                       always_keep_types):
    """Build all output GFF3 lines from classification results.

    Returns list of (seqid, start, line_str) for sorting.
    """
    entries = []  # (seqid, start, line_str)

    # Full matches → merged features
    for rg, vg, frac, ids in resolved_full:
        merged_lines = merge_matched_gene(rg, vg, ref_db, vendor_db,
                                          coord_pref, desc_pref, frac, ids)
        coord_gene = vg if coord_pref == 'vendor' else rg
        for line in merged_lines:
            entries.append((coord_gene.seqid, coord_gene.start, line))

    # Partial matches (position only) → both kept independently
    for rg, vg, frac in partial_pos:
        note = f'partial_match:position_only;overlap_frac={frac:.2f};with={vg.id}'
        for line in emit_gene_with_children(rg, ref_db, 'reference', note):
            entries.append((rg.seqid, rg.start, line))

        note = f'partial_match:position_only;overlap_frac={frac:.2f};with={rg.id}'
        for line in emit_gene_with_children(vg, vendor_db, 'vendor', note):
            entries.append((vg.seqid, vg.start, line))

    # Partial matches (identifier only) → both kept independently
    for rg, vg, ids in partial_id:
        ids_str = ','.join(sorted(ids))
        note = f'partial_match:identifier_only;matched_ids={ids_str};with={vg.id}'
        for line in emit_gene_with_children(rg, ref_db, 'reference', note):
            entries.append((rg.seqid, rg.start, line))

        note = f'partial_match:identifier_only;matched_ids={ids_str};with={rg.id}'
        for line in emit_gene_with_children(vg, vendor_db, 'vendor', note):
            entries.append((vg.seqid, vg.start, line))

    # Unmatched reference
    for rg in unmatched_ref:
        for line in emit_gene_with_children(rg, ref_db, 'reference'):
            entries.append((rg.seqid, rg.start, line))

    # Unmatched vendor
    for vg in unmatched_vendor:
        for line in emit_gene_with_children(vg, vendor_db, 'vendor'):
            entries.append((vg.seqid, vg.start, line))

    return entries


def write_gff(output_path, entries):
    """Write sorted GFF3 output."""
    entries.sort(key=lambda x: (x[0], x[1]))
    with open(output_path, 'w') as out:
        out.write('##gff-version 3\n')
        for _, _, line in entries:
            out.write(line + '\n')
    print(f"Wrote {len(entries)} feature lines to {output_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _fmt_gene(gene, db):
    """Format a gene for summary display."""
    name = get_attr_first(gene, 'Name') or get_attr_first(gene, 'ID') or 'unknown'
    desc = get_description_str(gene)
    return f"{gene.seqid}:{gene.start}-{gene.end} {name} [{desc}]"


def write_summary(summary_path, ref_genes, vendor_genes,
                  resolved_full, partial_pos, partial_id,
                  unmatched_ref, unmatched_vendor,
                  ref_db, vendor_db, coord_pref, desc_pref):
    """Write human-readable merge summary."""
    lines = []
    lines.append('=' * 60)
    lines.append('ANNOTATION MERGE SUMMARY')
    lines.append('=' * 60)
    lines.append(f'Reference genes:    {len(ref_genes)}')
    lines.append(f'Vendor genes:       {len(vendor_genes)}')
    lines.append('')
    lines.append('Classification:')
    lines.append(f'  Full matches (merged):             {len(resolved_full)}')
    lines.append(f'  Partial matches (position only):   {len(partial_pos)}')
    lines.append(f'  Partial matches (identifier only): {len(partial_id)}')
    lines.append(f'  Unmatched reference:               {len(unmatched_ref)}')
    lines.append(f'  Unmatched vendor:                  {len(unmatched_vendor)}')

    if resolved_full:
        lines.append('')
        lines.append(f'--- FULL MATCHES ({len(resolved_full)}) ---')
        for rg, vg, frac, ids in resolved_full:
            lines.append(f'  ref: {_fmt_gene(rg, ref_db)}')
            lines.append(f'  vnd: {_fmt_gene(vg, vendor_db)}')
            ids_str = ', '.join(sorted(ids))
            lines.append(f'  basis: overlap={frac:.2f}, matched_ids: {ids_str}')
            lines.append(f'  coords_from: {coord_pref}, description_from: {desc_pref}')
            lines.append('')

    if partial_pos:
        lines.append(f'--- PARTIAL MATCHES: POSITION ONLY ({len(partial_pos)}) ---')
        for rg, vg, frac in partial_pos:
            lines.append(f'  ref: {_fmt_gene(rg, ref_db)}')
            lines.append(f'  vnd: {_fmt_gene(vg, vendor_db)}')
            lines.append(f'  basis: overlap={frac:.2f}, no identifier match')
            lines.append('')

    if partial_id:
        lines.append(f'--- PARTIAL MATCHES: IDENTIFIER ONLY ({len(partial_id)}) ---')
        for rg, vg, ids in partial_id:
            lines.append(f'  ref: {_fmt_gene(rg, ref_db)}')
            lines.append(f'  vnd: {_fmt_gene(vg, vendor_db)}')
            ids_str = ', '.join(sorted(ids))
            lines.append(f'  basis: no CDS overlap, matched_ids: {ids_str}')
            lines.append('')

    if unmatched_ref:
        lines.append(f'--- UNMATCHED REFERENCE ({len(unmatched_ref)}) ---')
        for rg in unmatched_ref:
            lines.append(f'  {_fmt_gene(rg, ref_db)}')
        lines.append('')

    if unmatched_vendor:
        lines.append(f'--- UNMATCHED VENDOR ({len(unmatched_vendor)}) ---')
        for vg in unmatched_vendor:
            lines.append(f'  {_fmt_gene(vg, vendor_db)}')
        lines.append('')

    lines.append('=' * 60)

    text = '\n'.join(lines)
    print(text, file=sys.stderr)

    with open(summary_path, 'w') as f:
        f.write(text + '\n')
    print(f"Summary written to {summary_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description='Symmetric identity-based merge of two GFF3 annotation sets.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--reference', required=True,
                   help='Reference GFF3 (lifted onto final assembly)')
    p.add_argument('--vendor', required=True,
                   help='Vendor GFF3 (lifted onto final assembly)')
    p.add_argument('--output', required=True,
                   help='Output merged GFF3')
    p.add_argument('--summary', required=True,
                   help='Output merge summary report')
    p.add_argument('--overlap-threshold', type=float, default=0.50,
                   help='Reciprocal CDS overlap fraction for positional match (default: 0.50)')
    p.add_argument('--coord-preference', default='reference',
                   choices=['reference', 'vendor'],
                   help='Source of coordinates for merged features (default: reference)')
    p.add_argument('--description-preference', default='vendor',
                   choices=['reference', 'vendor'],
                   help='Source of Name/product/description for merged features (default: vendor)')
    p.add_argument('--always-keep-types', default=None,
                   help='Space-separated feature types that are never dropped')
    p.add_argument('--exact-fields',
                   default=' '.join(DEFAULT_EXACT_FIELDS),
                   help='Space-separated GFF attribute keys matched exactly '
                        '(default: "%(default)s")')
    p.add_argument('--word-fields',
                   default=' '.join(DEFAULT_WORD_FIELDS),
                   help='Space-separated GFF attribute keys matched word-by-word '
                        '(default: "%(default)s")')
    p.add_argument('--word-min-length', type=int, default=4,
                   help='Minimum word length for word-field matching (default: 4)')
    p.add_argument('--reference-label', default='Reference',
                   help='Label for reference in summary (default: Reference)')
    p.add_argument('--vendor-label', default='Vendor',
                   help='Label for vendor in summary (default: Vendor)')
    return p.parse_args()


def main():
    args = parse_args()

    always_keep_types = set()
    if args.always_keep_types:
        always_keep_types = set(args.always_keep_types.split())

    exact_fields = tuple(args.exact_fields.split()) if args.exact_fields.lower() != 'none' else ()
    word_fields = tuple(args.word_fields.split()) if args.word_fields.lower() != 'none' else ()

    print(f"Identifier matching — exact fields: {exact_fields}", file=sys.stderr)
    print(f"Identifier matching — word fields:  {word_fields} "
          f"(min word length: {args.word_min_length})", file=sys.stderr)

    # Load databases
    ref_db = load_db(args.reference, args.reference_label)
    vendor_db = load_db(args.vendor, args.vendor_label)

    # Collect genes
    ref_genes = collect_genes(ref_db)
    vendor_genes = collect_genes(vendor_db)
    print(f"Reference genes: {len(ref_genes)}, Vendor genes: {len(vendor_genes)}",
          file=sys.stderr)

    # Build spatial index for vendor genes
    vendor_by_seqid = build_spatial_index(vendor_genes)

    # Find all candidate matches
    print("Finding candidate matches...", file=sys.stderr)
    full_matches, partial_pos, partial_id = find_all_candidates(
        ref_genes, vendor_genes, ref_db, vendor_db,
        vendor_by_seqid, args.overlap_threshold,
        exact_fields, word_fields, args.word_min_length,
    )
    print(f"  Full match candidates: {len(full_matches)}", file=sys.stderr)
    print(f"  Partial (position): {len(partial_pos)}", file=sys.stderr)
    print(f"  Partial (identifier): {len(partial_id)}", file=sys.stderr)

    # Resolve full matches (greedy best-first)
    resolved_full = resolve_full_matches(full_matches)
    print(f"  Resolved full matches: {len(resolved_full)}", file=sys.stderr)

    # Track which genes are in full matches
    matched_ref_ids = {rg.id for rg, _, _, _ in resolved_full}
    matched_vendor_ids = {vg.id for _, vg, _, _ in resolved_full}

    # Filter partial matches to exclude already-matched genes
    partial_pos = resolve_partials(partial_pos, matched_ref_ids, matched_vendor_ids)
    partial_id = resolve_partials(partial_id, matched_ref_ids, matched_vendor_ids,
                                  is_pos=False)

    # Also exclude genes in partial matches from unmatched
    partial_ref_ids = set()
    partial_vendor_ids = set()
    for entry in partial_pos:
        partial_ref_ids.add(entry[0].id)
        partial_vendor_ids.add(entry[1].id)
    for entry in partial_id:
        partial_ref_ids.add(entry[0].id)
        partial_vendor_ids.add(entry[1].id)

    all_matched_ref = matched_ref_ids | partial_ref_ids
    all_matched_vendor = matched_vendor_ids | partial_vendor_ids

    unmatched_ref = [g for g in ref_genes if g.id not in all_matched_ref]
    unmatched_vendor = [g for g in vendor_genes if g.id not in all_matched_vendor]

    # Build output
    print("Building merged GFF3...", file=sys.stderr)
    entries = build_output_lines(
        resolved_full, partial_pos, partial_id,
        unmatched_ref, unmatched_vendor,
        ref_db, vendor_db,
        args.coord_preference, args.description_preference,
        always_keep_types,
    )
    write_gff(args.output, entries)

    # Summary
    write_summary(
        args.summary, ref_genes, vendor_genes,
        resolved_full, partial_pos, partial_id,
        unmatched_ref, unmatched_vendor,
        ref_db, vendor_db,
        args.coord_preference, args.description_preference,
    )

    print("Done.", file=sys.stderr)


if __name__ == '__main__':
    main()
