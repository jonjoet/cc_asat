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
            if not m.lastindex:
                sys.exit(f"--chr-pattern '{pattern}' matched '{name}' but has no capture group")
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
    # a zero-capture-group pattern has no lastindex (guard relies on this)
    assert re.search(r"Chr[IVXLCDM]+", ">S_ChrI".removeprefix(">")).lastindex is None


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
