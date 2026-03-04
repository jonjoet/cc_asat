process SAMTOOLS_FAIDX {
    tag "${reference.simpleName}"
    label 'process_low'

    conda 'bioconda::samtools=1.20'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/samtools:1.20--h50ea8bc_0' :
        'quay.io/biocontainers/samtools:1.20--h50ea8bc_0' }"

    input:
    path reference

    output:
    path "${reference}.fai", emit: fai

    script:
    """
    samtools faidx ${reference}
    """
}
