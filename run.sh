#!/usr/bin/env bash
# Thin convenience wrapper around `nextflow run main.nf` for cc_asat.
# Usage: ./run.sh [-profile <profiles> | -p <profiles>] <params.yaml> [extra Nextflow args...]
# Workflow selection stays in the YAML (full or annotation_transfer_only).
# NEXTFLOW may name a launcher executable; otherwise use nextflow on PATH.
set -euo pipefail

fail() {
    echo "ERROR: $*" >&2
    echo 'Usage: ./run.sh [-profile <profiles> | -p <profiles>] <params.yaml> [extra Nextflow args...]' >&2
    exit 1
}

PROFILE="docker"
if [[ "${1:-}" == "-profile" || "${1:-}" == "-p" ]]; then
    [[ -n "${2:-}" && "${2:-}" != -* ]] || fail "$1 needs a profile value"
    PROFILE="$2"
    shift 2
fi

[[ -n "${1:-}" ]] || fail 'a params YAML file is required'
PARAMS="$1"
shift
[[ -f "$PARAMS" && -r "$PARAMS" ]] || fail "params file not found/readable: $PARAMS"

# Resolve the pipeline without changing the caller's working directory: relative
# YAML/input paths and Nextflow work/results directories retain their meaning.
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CMD=("${NEXTFLOW:-nextflow}" run "$HERE/main.nf"
     -profile "$PROFILE" -params-file "$PARAMS" "$@")
exec "${CMD[@]}"
