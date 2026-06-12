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
        # AGP component_type is column 5 (index 4): 'W' = WGS contig component,
        # 'N'/'U' = gap. A valid W line has 9 columns (object_id 1, object_start 2,
        # object_end 3, part_number 4, 'W' 5, component_id 6, comp_start 7,
        # comp_end 8, orientation 9), so require the full width before indexing 5/2/1.
        w_rows = [r for r in rows if len(r) >= 9 and r[4] == "W"]
        gap_rows = [r for r in rows if len(r) > 4 and r[4] in ("N", "U")]
        if len(w_rows) == 1 and not gap_rows:
            comp_id = w_rows[0][5]                                   # AGP col 6: component (contig) id
            if comp_id == strip_suffix(obj):
                length = int(w_rows[0][2]) - int(w_rows[0][1]) + 1   # col 3 - col 2 + 1 (1-based inclusive)
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
    placed_u_gap = [  # placed scaffold with a 'U' (unknown-size) gap -> placed
        ["chrII_RagTag", "1", "800", "1", "W", "ctgC", "1", "800", "+"],
        ["chrII_RagTag", "801", "900", "2", "U", "100", "scaffold", "yes", "align_genus"],
        ["chrII_RagTag", "901", "1600", "3", "W", "ctgD", "1", "700", "+"],
    ]
    placed_single = [  # single-contig placed chromosome: object=ref name != component id
        ["chrM_RagTag", "1", "500", "1", "W", "ctgMito", "1", "500", "+"],
    ]
    unplaced_ctg = [  # unplaced contig: one W, no gap, basename == component id
        ["2micron_plasmid_RagTag", "1", "6300", "1", "W", "2micron_plasmid", "1", "6300", "+"],
    ]
    objects = {}
    for rows in (placed_multi, placed_u_gap, placed_single, unplaced_ctg):
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
