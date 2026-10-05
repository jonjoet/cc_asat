#!/usr/bin/env python3
"""Rename sequence headers after ragtag scaffold.

Default: prefix each header with the sample id exactly once, preserving the
original contig name after removing one scaffold-added terminal _RagTag suffix.

Optional --chr-pattern <regex>: a regex with one capture group. On match, the
header becomes "<sample_id>_<captured>" (used to swap a reference strain prefix
for the new strain id while keeping the chromosome label, e.g. LEXst001_ChrI ->
S_ChrI). On no match, falls back to the non-destructive prefix behaviour, so
unplaced contigs / plasmids keep their full names.
"""

import argparse
import os
import re
import sys

RAGTAG_SUFFIX = "_RagTag"


def compile_pattern(pattern):
    if pattern is None:
        return None
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("--chr-pattern must be a nonempty string")
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"invalid --chr-pattern syntax: {error}") from error
    if compiled.groups != 1:
        raise ValueError("--chr-pattern must have exactly one capture group")
    return compiled


def rename_header(name, sample_id, pattern=None):
    name = name.removeprefix(">").split()[0]
    if name.endswith(RAGTAG_SUFFIX):
        name = name[: -len(RAGTAG_SUFFIX)]
    compiled = compile_pattern(pattern)
    if compiled is not None:
        m = compiled.search(name)
        if m:
            if not m.group(1):
                raise ValueError(f"--chr-pattern matched '{name}' with an empty or unmatched capture")
            return f">{sample_id}_{m.group(1)}"
    prefix = f"{sample_id}_"
    if not name.startswith(prefix):
        name = prefix + name
    return f">{name}"


def rename_fasta(input_path, output_path, sample_id, pattern=None):
    if os.path.realpath(input_path) == os.path.realpath(output_path) or (
        os.path.exists(output_path) and os.path.samefile(input_path, output_path)
    ):
        raise ValueError("input/output alias: paths must identify different files")
    compile_pattern(pattern)
    lines = []
    inputs, outputs = set(), {}
    with open(input_path) as fh_in:
        for line in fh_in:
            if line.startswith(">"):
                original = line[1:].split()[0]
                proposed = rename_header(line.rstrip(), sample_id, pattern)[1:]
                if original in inputs:
                    raise ValueError(f"duplicate input ID '{original}' proposing '{proposed}'")
                if proposed in outputs:
                    raise ValueError(f"convergent final ID '{proposed}' from '{outputs[proposed]}' and '{original}'")
                inputs.add(original)
                outputs[proposed] = original
                lines.append(">" + proposed + "\n")
            else:
                lines.append(line)
    with open(output_path, "w") as fh_out:
        fh_out.writelines(lines)


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
    assert rename_header(">contig_7_RagTag_RagTag", "S") == ">S_contig_7_RagTag"
    assert rename_header(">S288C_R64_ChrI", "S288C", pat) == ">S288C_ChrI"


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

    try:
        rename_fasta(args.input, args.output, args.sample_id, args.chr_pattern)
    except (ValueError, OSError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(f"Renamed sequences written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
