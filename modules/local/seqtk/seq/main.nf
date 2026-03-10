process SEQTK_SEQ {
    tag "${params.sample_name}"
    label 'process_low'

    conda 'bioconda::seqtk=1.4'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/seqtk:1.4--he4a0461_2' :
        'quay.io/biocontainers/seqtk:1.4--he4a0461_2' }"

    input:
    path assembly

    output:
    path "${params.sample_name}_final.fasta", emit: final_fasta

    script:
    """
    seqtk seq -l 80 ${assembly} > ${params.sample_name}_final.fasta
    """
}
