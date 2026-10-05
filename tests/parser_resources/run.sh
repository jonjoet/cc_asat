#!/usr/bin/env bash
# Host orchestration only: all Nextflow and assertions execute in Docker.
set -euo pipefail
repo= evidence= mode= engine= parser= interface=selector
while (($#)); do
    case "$1" in
        --repo) repo=$2;; --evidence) evidence=$2;; --mode) mode=$2;;
        --engine) engine=$2;; --parser) parser=$2;; --interface) interface=$2;;
        *) echo "Unknown argument: $1" >&2; exit 2;;
    esac
    shift 2
done
: "${CC_GCEV_RUN_BASE:?export an absolute CC_GCEV_RUN_BASE}"
[[ "$repo" = /* && "$evidence" = /* && "$evidence" = "$CC_GCEV_RUN_BASE" ]] || exit 2
repo=$(realpath "$repo")
evidence=$(realpath -m "$evidence")
[[ "$evidence" = "$CC_GCEV_RUN_BASE" && ( "$evidence" = /home/qbk/qbk-code/tmp/cc_gcev/* || "$evidence" = /home/qbk/qbk-code/tmp/cc_asat/* ) ]] || exit 2
case "$evidence/" in "$repo/"*) echo 'Evidence must be outside the checkout' >&2; exit 2;; esac
[[ "$interface" = selector && "$parser" =~ ^(v1|v2|unset)$ && "$engine" =~ ^26.04.[56]$ ]] || exit 2
[[ "$mode" =~ ^(static|contract|fractions|unsupported|entry-parameters|previews|legacy-entry|tools|docker-rename|annotation-smoke|integration-resources|scaffolding-preview|scaffolding-modules|scaffolding-smoke)$ ]] || exit 2
[[ -f "$evidence/RUN.txt" ]] || { echo 'Create evidence RUN.txt before invoking runner' >&2; exit 2; }
phase="$evidence/$mode-$engine-$parser"
[[ ! -e "$phase" ]] || { echo "Refusing to overwrite $phase" >&2; exit 2; }
mkdir "$phase"
cp "$evidence/RUN.txt" "$phase/RUN.txt"
printf 'started_phase: %s\npurpose_phase: %s/%s/%s\n' "$(date -u +%FT%TZ)" "$mode" "$engine" "$parser" >> "$phase/RUN.txt"
git -C "$repo" rev-parse -q --verify MERGE_HEAD >> "$phase/RUN.txt" || printf 'MERGE_HEAD: none\n' >> "$phase/RUN.txt"
df -B1 "$evidence" > "$phase/disk-before.txt"
du -sb "$CC_GCEV_RUN_BASE" > "$phase/size-before.txt"
[[ $(df -B1 --output=avail "$evidence" | tail -1) -ge 21474836480 ]] || exit 2
git -C "$repo" status --porcelain=v1 > "$phase/status.txt"
git -C "$repo" diff --binary HEAD > "$phase/source.diff"
git -C "$repo" ls-files --others --exclude-standard -z > "$phase/untracked.list"
tar -C "$repo" --null -T "$phase/untracked.list" -cf "$phase/newfiles.tar"
sha256sum "$phase/source.diff" "$phase/newfiles.tar" "$repo/docs/plans/2026-10-04-resource-contract.md" "$repo/tests/integration/resource_vectors.json" >> "$phase/RUN.txt"
if [[ "$mode" = static ]]; then
    for file in main.nf utils/params.nf docs/plans/2026-10-04-resource-contract.md tests/integration/resource_vectors.json nextflow.config; do
        mkdir -p "$phase/base-preserved/$(dirname "$file")"
        git -C "$repo" show "3d56a4513734d9dd41ddc80b31d7055e5232dbef:$file" > "$phase/base-preserved/$file"
    done
fi
image="nextflow/nextflow:$engine"
# No implicit pulls: the scheduler grants heavyweight image setup separately.
docker image inspect "$image" > "$phase/image.json"
image_id=$(docker image inspect --format '{{.Id}}' "$image")
if [[ "$engine" = 26.04.6 ]]; then
    [[ "$image_id" = sha256:83bbf3dd9e84ecd4d53a86620d08fe0259bca00a8f59f6f31664eb90033f460f ]] || exit 2
fi
: "${CC_ASAT_NXF_DIST:?export verified immutable CC_ASAT_NXF_DIST}"
[[ "$CC_ASAT_NXF_DIST" = /* ]] || exit 2
jar="$CC_ASAT_NXF_DIST/$engine/nextflow-$engine-one.jar"
[[ -r "$jar" ]] || exit 2
if [[ "$engine" = 26.04.6 ]]; then
    [[ $(sha256sum "$jar" | cut -d ' ' -f1) = 2ca0251ae2d749317d9fbe5fe191a1616b5f44b608224268924c71b32f5ed9e2 ]] || exit 2
fi
sha256sum "$jar" > "$phase/jar.sha256"

# Tool mode uses separate direct tool containers, never a socket in the metadata launcher.
# Every command is bounded; a failed runtime remains recorded for the explicit source-only review.
if [[ "$mode" = tools ]]; then
    fixture="$repo/tests/fixtures/parser_resources"
    printf 'case\texpected\toutcome\n' > "$phase/tool-inventory.tsv"
    for case in T-RAGTAG-CORRECT T-RAGTAG-SCAFFOLD T-RAGTAG-PATCH T-LIFTOFF T-QUAST T-DNAAPLER T-TGS; do
        printf '%s\truntime output and one-worker source validation\tPENDING\n' "$case" >> "$phase/tool-inventory.tsv"
    done
    run_tool() {
        local name=$1 image=$2 command=$3 help=$4
        local case_dir="$phase/$name"
        mkdir "$case_dir"
        cp "$phase/RUN.txt" "$case_dir/RUN.txt"
        printf 'purpose_case: pinned one-worker tool command %s\n' "$name" >> "$case_dir/RUN.txt"
        # Index-building tools need writable input neighbours; never index the checkout.
        mkdir "$case_dir/inputs"
        cp "$fixture/"* "$case_dir/inputs/"
        command=${command//"$fixture"/"$case_dir/inputs"}
        if ! docker image inspect "$image" > "$case_dir/image.json" 2> "$case_dir/image-inspect.log"; then
            docker pull "$image" > "$case_dir/pull.log" 2>&1
            docker image inspect "$image" > "$case_dir/image.json"
        fi
        local image_id
        image_id=$(docker image inspect --format '{{.Id}}' "$image")
        cat > "$case_dir/source.py" <<'PY'
import glob, os, sys
from pathlib import Path
terms = ("ragtag", "liftoff", "quast", "dnaapler", "tgsgapcloser")
paths = set()
for base in sys.path + ["/usr/local/bin", "/usr/bin", "/opt/conda/bin"]:
    p = Path(base)
    if not p.is_dir():
        continue
    for term in terms:
        for item in p.glob("*" + term + "*"):
            if item.is_dir():
                paths.update(item.rglob("*.py"))
                paths.update(item.rglob("*.sh"))
            elif item.is_file():
                paths.add(item)
for path in sorted(paths):
    try:
        text = path.read_text()
    except (UnicodeError, OSError):
        continue
    print("\nSOURCE " + str(path))
    for number, line in enumerate(text.splitlines(), 1):
        print("%d: %s" % (number, line))
PY
        local source_cmd=(docker run --rm --cpus 2 --memory 2g --user "$(id -u):$(id -g)"
            --entrypoint /bin/bash -e PYTHONDONTWRITEBYTECODE=1 -e HOME="$case_dir"
            -v "$repo:$repo:ro" -v "$case_dir:$case_dir" -w "$case_dir" "$image_id"
            -c "$help; if command -v python3 >/dev/null; then python3 '$case_dir/source.py'; else tool=\$(command -v tgsgapcloser); printf '\\nSOURCE %s\\n' \"\$tool\"; cat \"\$tool\"; fi")
        printf '%q ' "${source_cmd[@]}" > "$case_dir/source-command.txt"
        set +e
        timeout 600 "${source_cmd[@]}" > "$case_dir/source.log" 2>&1
        printf '%s\n' "$?" > "$case_dir/source-exit.txt"
        set -e
        local tool_cmd=(docker run --rm --cpus 2 --memory 4g --user "$(id -u):$(id -g)"
            --entrypoint /bin/bash -e PYTHONDONTWRITEBYTECODE=1 -e HOME="$case_dir"
            -v "$repo:$repo:ro" -v "$case_dir:$case_dir" -w "$case_dir" "$image_id" -c "$command")
        printf '%q ' "${tool_cmd[@]}" > "$case_dir/command.txt"
        set +e
        timeout 600 "${tool_cmd[@]}" > "$case_dir/output.log" 2>&1
        printf '%s\n' "$?" > "$case_dir/exit-code.txt"
        set -e
    }
    ragtag=quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0
    run_tool T-RAGTAG-CORRECT "$ragtag" "ragtag.py correct '$fixture/reference.fasta' '$fixture/assembly.fasta' -R '$fixture/reads.fastq' -T ont -u -o result -t 1" 'ragtag.py correct --help'
    run_tool T-RAGTAG-SCAFFOLD "$ragtag" "ragtag.py scaffold '$fixture/reference.fasta' '$fixture/assembly.fasta' -u -o result -t 1" 'ragtag.py scaffold --help'
    run_tool T-RAGTAG-PATCH "$ragtag" "ragtag.py patch '$fixture/assembly.fasta' '$fixture/reference.fasta' --fill-only -o result -t 1" 'ragtag.py patch --help'
    run_tool T-LIFTOFF quay.io/biocontainers/liftoff:1.6.3--pyhdfd78af_0 "cp '$fixture/reference.gff3' source.gff3; cp '$fixture/reference.fasta' source.fasta; liftoff -g source.gff3 -o lifted.gff3 -u unmapped.txt -s 0.5 -p 1 '$fixture/assembly.fasta' source.fasta" 'liftoff --help'
    run_tool T-QUAST quay.io/biocontainers/quast:5.2.0--py39pl5321h4e691d4_3 "quast '$fixture/assembly.fasta' -r '$fixture/reference.fasta' -o result --threads 1 --split-scaffolds --labels fixture --features '$fixture/reference.gff3' --fungus" 'quast --help'
    run_tool T-DNAAPLER quay.io/biocontainers/dnaapler:1.1.0--pyhdfd78af_0 "dnaapler all -i '$fixture/assembly.fasta' -o result -p fixture -t 1" 'dnaapler all --help'
    run_tool T-TGS quay.io/biocontainers/tgsgapcloser:1.0.3--h8b12597_0 "tgsgapcloser --scaff '$fixture/assembly.fasta' --reads '$fixture/reference.fasta' --output gapclosed --thread 1 --ne" 'tgsgapcloser --help'
fi
args=(docker run --rm --cpus 4 --memory 4g --user "$(id -u):$(id -g)"
    --entrypoint /usr/bin/python3
    -e PYTHONDONTWRITEBYTECODE=1 -e NXF_OFFLINE=true -e NXF_DISABLE_CHECK_LATEST=true
    -e NXF_DIST="$CC_ASAT_NXF_DIST" -e NXF_VER="$engine" -e NXF_OPTS=-Xmx768m
    -e CC_GCEV_RUN_BASE="$evidence"
    -v "$CC_ASAT_NXF_DIST:$CC_ASAT_NXF_DIST:ro"
    -v "$repo:$repo:ro" -v "$evidence:$evidence" -w "$phase")
[[ "$parser" = unset ]] || args+=(-e NXF_SYNTAX_PARSER="$parser")
if [[ "$mode" = docker-rename || "$mode" = annotation-smoke || "$mode" = scaffolding-modules || "$mode" = scaffolding-smoke ]]; then
    args+=(--group-add "$(stat -c %g /var/run/docker.sock)" -v /var/run/docker.sock:/var/run/docker.sock)
fi
# Record the immutable identities of all actual task images before execution.
if [[ "$mode" = docker-rename || "$mode" = annotation-smoke || "$mode" = scaffolding-modules || "$mode" = scaffolding-smoke ]]; then
    for tool_image in python:3.12 quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0 quay.io/biocontainers/samtools:1.20--h50ea8bc_0 quay.io/biocontainers/seqtk:1.4--he4a0461_2 quay.io/biocontainers/liftoff:1.6.3--pyhdfd78af_0 quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0 quay.io/biocontainers/quast:5.2.0--py39pl5321h4e691d4_3 quay.io/biocontainers/dnaapler:1.1.0--pyhdfd78af_0; do
        docker image inspect "$tool_image" >> "$phase/tool-images.json" || exit 2
    done
fi
args+=("$image_id" "$repo/tests/parser_resources/assert_results.py"
    --repo "$repo" --phase "$phase" --mode "$mode" --engine "$engine" --parser "$parser")
printf '%q ' "${args[@]}" > "$phase/command.txt"
printf '\n' >> "$phase/command.txt"
set +e
"${args[@]}" > "$phase/output.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$phase/exit-code.txt"
cat "$phase/output.log"
git -C "$repo" status --porcelain=v1 > "$phase/status-after.txt"
cmp "$phase/status.txt" "$phase/status-after.txt"
git -C "$repo" diff --binary HEAD > "$phase/source-after.diff"
cmp "$phase/source.diff" "$phase/source-after.diff"
tar -C "$repo" --null -T "$phase/untracked.list" -cf "$phase/newfiles-after.tar"
cmp "$phase/newfiles.tar" "$phase/newfiles-after.tar"
df -B1 "$evidence" > "$phase/disk-after.txt"
du -sb "$CC_GCEV_RUN_BASE" > "$phase/size-after.txt"
printf '%s\n' "$phase/RUN.txt" "$phase/command.txt" "$phase/output.log" "$phase/exit-code.txt" "$phase/results.tsv" "$phase/case-inventory.tsv" >> "$evidence/ARTIFACTS.txt"
exit "$code"
