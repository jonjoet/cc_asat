#!/usr/bin/env python3
"""
novel_annotation_transfer.py

Transfer novel annotations from a vendor GFF to a scaffolded assembly,
filling gaps in a Liftoff-transferred reference annotation.

Workflow:
  1. Parse RagTag AGP to build contig→scaffold coordinate mapping
  2. Remap vendor GFF from contig-space to scaffold-space
  3. Load Liftoff GFF (reference-transferred, has priority)
  4. Filter vendor features: keep only those filling gaps in Liftoff annotation
  5. Output merged GFF with provenance tracking

Overlap handling:
  - Vendor features with >MAX_OVERLAP_FRAC of their length overlapping a
    Liftoff feature are dropped (reference takes priority)
  - Vendor features with partial overlap (between MIN and MAX thresholds)
    are kept but flagged with Note=partial_overlap_with_reference
  - Vendor features with <MIN_OVERLAP_FRAC overlap are kept cleanly

Usage:
  python novel_annotation_transfer.py \
    --agp ragtag.scaffold.agp \
    --liftoff liftoff_output.gff3 \
    --vendor vendor_annotation.gff \
    --output merged_annotations.gff3 \
    [--max-overlap 0.50] \
    [--min-overlap 0.10] \
    [--feature-types gene mRNA CDS] \
    [--unplaced-prefix "unplaced_"]
"""

import argparse
import sys
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

# ── Simple interval index (no external dependency) ───────────────────────────

class IntervalIndex:
    """
    Simple interval container using sorted lists + binary search.
    Sufficient for yeast-scale genomes (~6,000 genes).
    """
    def __init__(self):
        self._intervals = []  # list of (start, end, data)
        self._sorted = False

    def add(self, start, end, data=None):
        self._intervals.append((start, end, data))
        self._sorted = False

    def _ensure_sorted(self):
        if not self._sorted:
            self._intervals.sort(key=lambda x: (x[0], x[1]))
            self._sorted = True

    def overlap(self, qstart, qend):
        """Return all intervals overlapping [qstart, qend]."""
        self._ensure_sorted()
        results = []
        for start, end, data in self._intervals:
            if start > qend:
                break  # past query range
            if end >= qstart:
                results.append((start, end, data))
        return results


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class AGPEntry:
    """One component (W) line from an AGP file."""
    scaffold: str
    scaffold_start: int  # 1-based
    scaffold_end: int    # 1-based
    component: str       # contig name
    comp_start: int      # 1-based
    comp_end: int        # 1-based
    orientation: str     # + or -


@dataclass
class GFFFeature:
    """One line of a GFF3 file."""
    seqid: str
    source: str
    ftype: str
    start: int   # 1-based
    end: int     # 1-based
    score: str
    strand: str
    phase: str
    attributes: str
    raw_line: str = ""
    children: list = field(default_factory=list)

    @property
    def length(self):
        return self.end - self.start + 1

    def get_attr(self, key):
        """Extract a value from GFF3 attributes column."""
        match = re.search(rf'{key}=([^;]+)', self.attributes)
        return match.group(1) if match else None

    def set_attr(self, key, value):
        """Add or update an attribute."""
        if re.search(rf'{key}=', self.attributes):
            self.attributes = re.sub(rf'{key}=[^;]+', f'{key}={value}', self.attributes)
        else:
            self.attributes = self.attributes.rstrip(';') + f';{key}={value}'

    def to_gff_line(self):
        return '\t'.join([
            self.seqid, self.source, self.ftype,
            str(self.start), str(self.end),
            self.score, self.strand, self.phase,
            self.attributes
        ])


# ── AGP parsing and coordinate remapping ─────────────────────────────────────

def parse_agp(agp_path):
    """
    Parse RagTag AGP file. Returns dict: contig_name -> list[AGPEntry]
    (a contig should appear only once, but list handles edge cases)
    """
    contig_to_placement = {}
    with open(agp_path) as f:
        for line in f:
            if line.startswith('#') or line.strip() == '':
                continue
            parts = line.strip().split('\t')
            # AGP columns: obj, obj_start, obj_end, part_num, comp_type, ...
            # For W (sequence component) lines:
            #   col5=comp_type, col6=comp_name, col7=comp_start, col8=comp_end, col9=orientation
            # For N/U (gap) lines: skip
            if parts[4] in ('N', 'U'):
                continue
            entry = AGPEntry(
                scaffold=parts[0],
                scaffold_start=int(parts[1]),
                scaffold_end=int(parts[2]),
                component=parts[5],
                comp_start=int(parts[6]),
                comp_end=int(parts[7]),
                orientation=parts[8]
            )
            contig_to_placement[entry.component] = entry
    return contig_to_placement


def remap_coordinate(pos, agp: AGPEntry):
    """
    Remap a single 1-based coordinate from contig-space to scaffold-space.
    Handles reverse-complement orientation.
    """
    if agp.orientation == '+':
        return agp.scaffold_start + (pos - agp.comp_start)
    else:  # reverse complement
        return agp.scaffold_end - (pos - agp.comp_start)


def remap_feature(feature: GFFFeature, agp: AGPEntry) -> GFFFeature:
    """
    Remap a GFF feature from contig coordinates to scaffold coordinates.
    Handles strand flip for reverse-complemented contigs.
    """
    if agp.orientation == '+':
        new_start = agp.scaffold_start + (feature.start - agp.comp_start)
        new_end = agp.scaffold_start + (feature.end - agp.comp_start)
        new_strand = feature.strand
    else:
        # Reverse complement: coordinates flip, strand flips
        new_start = agp.scaffold_end - (feature.end - agp.comp_start)
        new_end = agp.scaffold_end - (feature.start - agp.comp_start)
        if feature.strand == '+':
            new_strand = '-'
        elif feature.strand == '-':
            new_strand = '+'
        else:
            new_strand = feature.strand  # '.', keep as-is

    remapped = GFFFeature(
        seqid=agp.scaffold,
        source=feature.source,
        ftype=feature.ftype,
        start=new_start,
        end=new_end,
        score=feature.score,
        strand=new_strand,
        phase=feature.phase,
        attributes=feature.attributes
    )
    return remapped


# ── GFF parsing ──────────────────────────────────────────────────────────────

def parse_gff(gff_path, feature_types=None):
    """
    Parse GFF3 file. Returns list of GFFFeature.
    If feature_types is set, only return those types.
    Skips comment/directive lines (except collects ##sequence-region).
    """
    features = []
    with open(gff_path) as f:
        for line in f:
            if line.startswith('#') or line.strip() == '':
                continue
            parts = line.strip().split('\t')
            if len(parts) != 9:
                continue
            feat = GFFFeature(
                seqid=parts[0],
                source=parts[1],
                ftype=parts[2],
                start=int(parts[3]),
                end=int(parts[4]),
                score=parts[5],
                strand=parts[6],
                phase=parts[7],
                attributes=parts[8],
                raw_line=line.strip()
            )
            if feature_types is None or feat.ftype in feature_types:
                features.append(feat)
    return features


def build_parent_child_index(features):
    """
    Build a dict mapping Parent ID -> list of child features.
    Also returns dict of ID -> feature for top-level lookup.
    """
    id_to_feature = {}
    parent_to_children = defaultdict(list)

    for f in features:
        fid = f.get_attr('ID')
        if fid:
            id_to_feature[fid] = f
        parent = f.get_attr('Parent')
        if parent:
            # GFF3 allows comma-separated parents
            for p in parent.split(','):
                parent_to_children[p].append(f)

    return id_to_feature, parent_to_children


# ── Overlap detection and filtering ──────────────────────────────────────────

def build_interval_index(features):
    """
    Build per-seqid IntervalIndex from a list of GFF features.
    """
    indexes = defaultdict(IntervalIndex)
    for f in features:
        indexes[f.seqid].add(f.start, f.end, f)
    return indexes


def compute_overlap_fraction(feature: GFFFeature, index: IntervalIndex) -> float:
    """
    Compute fraction of feature's length that overlaps any interval in index.
    Handles multiple overlapping reference features by merging covered bases.
    """
    overlaps = index.overlap(feature.start, feature.end)
    if not overlaps:
        return 0.0

    # Merge overlapping reference intervals to get total covered bases
    covered = set()
    for start, end, _ in overlaps:
        ov_start = max(feature.start, start)
        ov_end = min(feature.end, end)
        covered.update(range(ov_start, ov_end + 1))

    return len(covered) / feature.length


def classify_vendor_feature(feature, liftoff_indexes, max_overlap, min_overlap):
    """
    Classify a vendor feature based on overlap with Liftoff annotations.
    
    Returns:
        'drop'    - too much overlap, reference annotation covers this
        'flag'    - partial overlap, keep but mark
        'keep'    - novel, no significant overlap
    """
    index = liftoff_indexes.get(feature.seqid)
    if index is None:
        return 'keep'  # different scaffold, no reference annotation at all

    frac = compute_overlap_fraction(feature, index)

    if frac >= max_overlap:
        return 'drop'
    elif frac >= min_overlap:
        return 'flag'
    else:
        return 'keep'


# ── Main pipeline ────────────────────────────────────────────────────────────

def remap_vendor_gff(vendor_features, contig_to_placement, unplaced_prefix):
    """
    Remap all vendor features from contig-space to scaffold-space.
    Features on unplaced contigs get prefixed but keep original coordinates.
    """
    remapped = []
    stats = {'placed': 0, 'unplaced': 0, 'skipped': 0}

    for feat in vendor_features:
        if feat.seqid in contig_to_placement:
            agp = contig_to_placement[feat.seqid]
            new_feat = remap_feature(feat, agp)
            # Track provenance
            new_feat.set_attr('original_contig', feat.seqid)
            new_feat.set_attr('original_coords', f'{feat.start}-{feat.end}')
            remapped.append(new_feat)
            stats['placed'] += 1
        else:
            # Unplaced contig — keep with prefix
            new_feat = GFFFeature(
                seqid=f"{unplaced_prefix}{feat.seqid}",
                source=feat.source,
                ftype=feat.ftype,
                start=feat.start,
                end=feat.end,
                score=feat.score,
                strand=feat.strand,
                phase=feat.phase,
                attributes=feat.attributes
            )
            new_feat.set_attr('original_contig', feat.seqid)
            new_feat.set_attr('unplaced', 'true')
            remapped.append(new_feat)
            stats['unplaced'] += 1

    return remapped, stats


def collect_gene_groups(features):
    """
    Group features into gene-level groups (gene + its children).
    Returns list of (top_level_feature, [child_features]).
    Features without Parent that aren't 'gene' type are treated as standalone.
    """
    id_to_feat, parent_to_children = build_parent_child_index(features)

    # Find top-level features (no Parent attribute)
    top_level = [f for f in features if f.get_attr('Parent') is None]

    groups = []
    seen_ids = set()
    for f in top_level:
        fid = f.get_attr('ID')
        children = []
        if fid:
            children = _collect_descendants(fid, parent_to_children, seen_ids)
            seen_ids.add(fid)
        groups.append((f, children))

    # Catch any orphans (features with Parent not found in file)
    orphans = [f for f in features
                if f.get_attr('Parent') is not None
                and f.get_attr('ID') not in seen_ids
                and f not in [c for _, cs in groups for c in cs]]
    for f in orphans:
        groups.append((f, []))

    return groups


def _collect_descendants(parent_id, parent_to_children, seen):
    """Recursively collect all descendants of a parent feature."""
    children = parent_to_children.get(parent_id, [])
    all_desc = []
    for c in children:
        all_desc.append(c)
        cid = c.get_attr('ID')
        if cid and cid not in seen:
            seen.add(cid)
            all_desc.extend(_collect_descendants(cid, parent_to_children, seen))
    return all_desc


def filter_novel_features(vendor_groups, liftoff_indexes, max_overlap, min_overlap,
                          always_keep_types=None):
    """
    Filter vendor gene groups. Classify based on top-level feature overlap.
    Keep/flag/drop entire gene groups together.
    
    Features with ftype in always_keep_types are never dropped — they're
    either 'keep' or 'flag'. This is critical for detecting transposon
    insertions within reference genes.
    """
    if always_keep_types is None:
        always_keep_types = set()
    else:
        always_keep_types = set(always_keep_types)

    novel = []
    flagged = []
    dropped = []

    for top_feat, children in vendor_groups:
        classification = classify_vendor_feature(
            top_feat, liftoff_indexes, max_overlap, min_overlap
        )

        # Override: always-keep types get promoted from 'drop' to 'flag'
        if classification == 'drop' and top_feat.ftype in always_keep_types:
            classification = 'flag'

        if classification == 'keep':
            top_feat.set_attr('annotation_source', 'vendor_novel')
            for c in children:
                c.set_attr('annotation_source', 'vendor_novel')
            novel.append((top_feat, children))

        elif classification == 'flag':
            top_feat.set_attr('annotation_source', 'vendor_novel')
            top_feat.set_attr('Note', 'partial_overlap_with_reference_annotation')
            for c in children:
                c.set_attr('annotation_source', 'vendor_novel')
            flagged.append((top_feat, children))

        else:
            dropped.append((top_feat, children))

    return novel, flagged, dropped


def write_merged_gff(output_path, liftoff_features, novel_groups, flagged_groups,
                     unplaced_groups=None):
    """
    Write merged GFF3 with Liftoff features first (reference priority),
    then novel vendor features, grouped by seqid and sorted by position.
    """
    # Tag all Liftoff features with source
    for f in liftoff_features:
        if not f.get_attr('annotation_source'):
            f.set_attr('annotation_source', 'liftoff_reference')

    # Flatten groups
    all_novel = []
    for top, children in novel_groups + flagged_groups:
        all_novel.append(top)
        all_novel.extend(children)

    all_unplaced = []
    if unplaced_groups:
        for top, children in unplaced_groups:
            top.set_attr('annotation_source', 'vendor_unplaced')
            for c in children:
                c.set_attr('annotation_source', 'vendor_unplaced')
            all_unplaced.append(top)
            all_unplaced.extend(children)

    # Combine and sort by seqid then start position
    all_features = liftoff_features + all_novel + all_unplaced
    all_features.sort(key=lambda f: (f.seqid, f.start, -f.length))

    with open(output_path, 'w') as out:
        out.write('##gff-version 3\n')
        out.write(f'# Merged annotation: Liftoff reference + vendor novel features\n')
        out.write(f'# Liftoff features: {len(liftoff_features)}\n')
        out.write(f'# Novel vendor features: {len(all_novel)}\n')
        out.write(f'# Unplaced vendor features: {len(all_unplaced)}\n')
        out.write('#\n')

        for f in all_features:
            out.write(f.to_gff_line() + '\n')


def print_summary(remap_stats, novel, flagged, dropped, liftoff_count):
    """Print a human-readable summary of the merge."""
    print("\n" + "=" * 60)
    print("ANNOTATION MERGE SUMMARY")
    print("=" * 60)
    print(f"\nLiftoff (reference) features:    {liftoff_count}")
    print(f"\nVendor feature remapping:")
    print(f"  Placed on scaffolds:           {remap_stats['placed']}")
    print(f"  On unplaced contigs:           {remap_stats['unplaced']}")
    print(f"\nVendor feature classification (gene-level groups):")
    print(f"  Novel (no significant overlap):{len(novel):>5}")
    print(f"  Flagged (partial overlap):     {len(flagged):>5}")
    print(f"  Dropped (covered by ref):      {len(dropped):>5}")
    print()

    if flagged:
        print("Flagged features (review these):")
        for top, _ in flagged:
            fid = top.get_attr('ID') or top.get_attr('Name') or 'unknown'
            print(f"  {top.seqid}:{top.start}-{top.end} ({top.strand}) {top.ftype} {fid}")
        print()

    if novel:
        # Summarize by type
        type_counts = defaultdict(int)
        for top, _ in novel:
            type_counts[top.ftype] += 1
        print("Novel feature types:")
        for ftype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {ftype}: {count}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Transfer novel vendor annotations to scaffolded assembly, '
                    'filling gaps in Liftoff reference annotation.'
    )
    parser.add_argument('--agp', required=True,
                        help='RagTag scaffold AGP file (maps contigs to scaffolds)')
    parser.add_argument('--liftoff', required=True,
                        help='Liftoff output GFF3 (reference annotations on scaffolded assembly)')
    parser.add_argument('--vendor', required=True,
                        help='Vendor GFF (annotation of raw assembly, contig coordinates)')
    parser.add_argument('--output', required=True,
                        help='Output merged GFF3')
    parser.add_argument('--max-overlap', type=float, default=0.50,
                        help='Max overlap fraction to keep vendor feature (default: 0.50). '
                             'Features with overlap >= this are dropped.')
    parser.add_argument('--min-overlap', type=float, default=0.10,
                        help='Min overlap to flag (default: 0.10). Features with overlap '
                             'between min and max are kept but flagged.')
    parser.add_argument('--feature-types', nargs='*', default=None,
                        help='Only consider these GFF feature types from vendor '
                             '(default: all types). E.g., --feature-types gene mRNA CDS')
    parser.add_argument('--unplaced-prefix', default='unplaced_',
                        help='Prefix for unplaced contig seqids (default: unplaced_)')
    parser.add_argument('--always-keep-types', nargs='*',
                        default=['transposable_element', 'repeat_region',
                                 'LTR_retrotransposon', 'long_terminal_repeat',
                                 'transposon_fragment'],
                        help='Feature types that bypass overlap filter and are always '
                             'kept (flagged if overlapping). Important for detecting '
                             'transposon insertions within reference genes. '
                             '(default: transposable_element repeat_region '
                             'LTR_retrotransposon long_terminal_repeat transposon_fragment)')
    parser.add_argument('--summary', default=None,
                        help='Write summary report to file (default: stdout)')

    args = parser.parse_args()

    # ── Step 1: Parse AGP ──
    print("Parsing AGP file...", file=sys.stderr)
    contig_to_placement = parse_agp(args.agp)
    print(f"  {len(contig_to_placement)} contigs placed in scaffolds", file=sys.stderr)

    # ── Step 2: Parse and remap vendor GFF ──
    print("Parsing vendor GFF...", file=sys.stderr)
    vendor_features = parse_gff(args.vendor, args.feature_types)
    print(f"  {len(vendor_features)} features loaded", file=sys.stderr)

    print("Remapping to scaffold coordinates...", file=sys.stderr)
    remapped_vendor, remap_stats = remap_vendor_gff(
        vendor_features, contig_to_placement, args.unplaced_prefix
    )

    # ── Step 3: Parse Liftoff GFF ──
    print("Parsing Liftoff GFF...", file=sys.stderr)
    liftoff_features = parse_gff(args.liftoff)
    print(f"  {len(liftoff_features)} features loaded", file=sys.stderr)

    # ── Step 4: Build interval trees from Liftoff top-level features ──
    # Use all feature types for overlap detection
    liftoff_indexes = build_interval_index(liftoff_features)

    # ── Step 5: Group vendor features by gene and filter ──
    print("Grouping vendor features and filtering...", file=sys.stderr)
    vendor_groups = collect_gene_groups(remapped_vendor)

    # Separate placed vs unplaced groups
    placed_groups = [(t, c) for t, c in vendor_groups
                     if not t.seqid.startswith(args.unplaced_prefix)]
    unplaced_groups = [(t, c) for t, c in vendor_groups
                       if t.seqid.startswith(args.unplaced_prefix)]

    novel, flagged, dropped = filter_novel_features(
        placed_groups, liftoff_indexes, args.max_overlap, args.min_overlap,
        always_keep_types=args.always_keep_types
    )

    # ── Step 6: Write merged output ──
    print("Writing merged GFF3...", file=sys.stderr)
    write_merged_gff(args.output, liftoff_features, novel, flagged, unplaced_groups)

    # ── Summary ──
    print_summary(remap_stats, novel, flagged, dropped, len(liftoff_features))

    if args.summary:
        import io
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        print_summary(remap_stats, novel, flagged, dropped, len(liftoff_features))
        sys.stdout = old_stdout
        with open(args.summary, 'w') as f:
            f.write(buf.getvalue())
        print(f"Summary written to {args.summary}", file=sys.stderr)

    print(f"\nDone! Merged GFF written to {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
