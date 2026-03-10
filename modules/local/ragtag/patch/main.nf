process RAGTAG_PATCH {
    tag "${params.sample_name}"
    label 'process_medium'
    conda 'bioconda::ragtag=2.1.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/ragtag:2.1.0--pyhb7b1952_0' :
        'quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0' }"

    input:
    path scaffold
    path reference

    output:
    path "ragtag_patch_out/ragtag.patch.fasta",      emit: patched
    path "ragtag_patch_out/ragtag.patch.agp",         emit: agp
    path "ragtag_patch_out/ragtag.patch.rename.agp",  emit: rename_agp

    script:
    """
    ragtag.py patch \
        ${scaffold} \
        ${reference} \
        --fill-only \
        -o ragtag_patch_out \
        -t ${task.cpus}
    """
}
