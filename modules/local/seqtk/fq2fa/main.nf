process SEQTK_FQ2FA {
    tag "${params.sample_name}"
    label 'process_low'

    conda 'bioconda::seqtk=1.4'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/seqtk:1.4--he4a0461_2' :
        'quay.io/biocontainers/seqtk:1.4--he4a0461_2' }"

    input:
    path reads_fq

    output:
    path "reads.fasta", emit: reads_fa

    script:
    """
    seqtk seq -A ${reads_fq} > reads.fasta
    """
}
