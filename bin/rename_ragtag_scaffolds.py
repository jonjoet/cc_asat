#!/usr/bin/env python3
"""Rename sequence headers after ragtag scaffold.

Strips _RagTag suffix, strips any existing sample-id prefix (anything before
the first underscore), then prepends the given sample id.
"""

import argparse
import sys


def rename_header(name: str, sample_id: str) -> str:
    name = name.removeprefix(">").split()[0]
    # Strip ragtag suffix
    if name.endswith("_RagTag"):
        name = name[: -len("_RagTag")]
    # Strip stale sample-id prefix (everything up to and including first underscore)
    if "_" in name:
        name = name[name.index("_") + 1 :]
    return f">{sample_id}_{name}"


def rename_fasta(input_path: str, output_path: str, sample_id: str) -> None:
    with open(input_path) as fh_in, open(output_path, "w") as fh_out:
        for line in fh_in:
            if line.startswith(">"):
                fh_out.write(rename_header(line.rstrip(), sample_id) + "\n")
            else:
                fh_out.write(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample-id", required=True)
    args = parser.parse_args()

    rename_fasta(args.input, args.output, args.sample_id)
    print(f"Renamed sequences written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
