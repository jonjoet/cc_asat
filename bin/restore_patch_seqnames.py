#!/usr/bin/env python3
"""
restore_patch_seqnames.py

Restore original sequence names to a ragtag-patched FASTA.

ragtag.py patch --fill-only renames sequences to generic IDs (seq0000001, etc.).
This script restores the original accessions using two independent methods:

  1. Parallel header comparison: since --fill-only preserves count and order,
     the Nth sequence in the patched FASTA corresponds to the Nth in the original.

  2. AGP-based mapping: ragtag.patch.rename.agp and ragtag.patch.agp together
     define old_name -> generic_name -> patched_name mappings.

Both methods must agree; the script errors out if they disagree.

Usage:
  restore_patch_seqnames.py \
    --original original.fasta \
    --patched patched.fasta \
    --patch-agp ragtag.patch.agp \
    --rename-agp ragtag.patch.rename.agp \
    --output restored.fasta
"""

import argparse
import sys


def parse_fasta_headers(path):
    """Return ordered list of sequence IDs from a FASTA file."""
    headers = []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                seq_id = line[1:].split()[0]
                headers.append(seq_id)
    return headers


def parse_rename_agp(path):
    """Parse ragtag.patch.rename.agp to get original_name -> renamed_name mapping.

    The rename AGP maps original sequence names to ragtag's internal renamed
    sequences (e.g., chr1 -> seq0000001_RagTag). Each sequence appears as a
    single W-line spanning the full length.
    """
    mapping = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) < 6 or fields[4] != "W":
                continue
            renamed = fields[0]     # target: the renamed seq (e.g. seq0000001_RagTag)
            original = fields[5]    # component: the original seq name
            mapping[renamed] = original
    return mapping


def parse_patch_agp(path):
    """Parse ragtag.patch.agp to get renamed_name -> patched_name mapping.

    The patch AGP maps ragtag's renamed sequences to the final patched output
    sequence names. With --fill-only, each renamed seq maps to exactly one
    patched seq.
    """
    mapping = {}
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            fields = line.strip().split("\t")
            if len(fields) < 6 or fields[4] != "W":
                continue
            patched = fields[0]     # target: patched output seq name
            renamed = fields[5]     # component: the renamed seq
            # A patched seq may have multiple components (original + gap fills).
            # We want the component that came from the rename step (has _RagTag suffix
            # or matches a key from the rename AGP). Store first W-line per patched seq.
            if patched not in mapping:
                mapping[patched] = renamed
    return mapping


def build_agp_mapping(rename_agp_path, patch_agp_path):
    """Build patched_name -> original_name mapping from the two AGP files."""
    # renamed_name -> original_name
    rename_map = parse_rename_agp(rename_agp_path)
    # patched_name -> renamed_name (first component)
    patch_map = parse_patch_agp(patch_agp_path)

    # Chain: patched_name -> renamed_name -> original_name
    agp_mapping = {}
    for patched_name, renamed_name in patch_map.items():
        if renamed_name in rename_map:
            agp_mapping[patched_name] = rename_map[renamed_name]
        else:
            # The component might be a gap-fill fragment, not from the original.
            # Skip these — we only care about the primary sequence mapping.
            pass

    return agp_mapping


def restore_fasta(original_path, patched_path, output_path, agp_mapping):
    """Rewrite patched FASTA with original sequence names restored."""
    original_headers = parse_fasta_headers(original_path)
    patched_headers = parse_fasta_headers(patched_path)

    if len(original_headers) != len(patched_headers):
        print(
            f"ERROR: Sequence count mismatch: original has {len(original_headers)}, "
            f"patched has {len(patched_headers)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Method 1: positional mapping (parallel headers)
    positional_mapping = {}
    for patched_id, original_id in zip(patched_headers, original_headers):
        positional_mapping[patched_id] = original_id

    # Method 2: AGP-based mapping (already computed)
    # Validate that both methods agree
    for patched_id in patched_headers:
        pos_original = positional_mapping.get(patched_id)
        agp_original = agp_mapping.get(patched_id)

        if agp_original is None:
            print(
                f"WARNING: Patched sequence '{patched_id}' not found in AGP mapping, "
                f"using positional mapping: '{pos_original}'",
                file=sys.stderr,
            )
            continue

        if pos_original != agp_original:
            print(
                f"ERROR: Mapping disagreement for '{patched_id}': "
                f"positional='{pos_original}', AGP='{agp_original}'",
                file=sys.stderr,
            )
            sys.exit(1)

    # Use positional mapping (validated against AGP) to rewrite
    header_idx = 0
    with open(patched_path) as fin, open(output_path, "w") as fout:
        for line in fin:
            if line.startswith(">"):
                original_name = original_headers[header_idx]
                # Preserve any description after the ID in the original header?
                # No — just use the clean original ID.
                fout.write(f">{original_name}\n")
                header_idx += 1
            else:
                fout.write(line)

    print(f"Restored {header_idx} sequence names in {output_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Restore original sequence names to a ragtag-patched FASTA"
    )
    parser.add_argument(
        "--original", required=True, help="Original (pre-patch) FASTA"
    )
    parser.add_argument(
        "--patched", required=True, help="Patched FASTA from ragtag"
    )
    parser.add_argument(
        "--patch-agp", required=True, help="ragtag.patch.agp file"
    )
    parser.add_argument(
        "--rename-agp", required=True, help="ragtag.patch.rename.agp file"
    )
    parser.add_argument(
        "--output", required=True, help="Output FASTA with restored names"
    )
    args = parser.parse_args()

    agp_mapping = build_agp_mapping(args.rename_agp, args.patch_agp)
    restore_fasta(args.original, args.patched, args.output, agp_mapping)


if __name__ == "__main__":
    main()
