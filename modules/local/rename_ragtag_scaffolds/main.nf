process RENAME_RAGTAG_SCAFFOLDS {
    tag "${params.sample_name}"
    label 'process_single'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path scaffold
    path unplaced

    output:
    path "${params.sample_name}_scaffolds.fasta",          emit: scaffold
    path "${params.sample_name}_unplaced.fasta",           emit: unplaced, optional: true

    script:
    def handle_unplaced = unplaced.name != 'NO_FILE' ? """
    rename_ragtag_scaffolds.py \\
        --input ${unplaced} \\
        --output ${params.sample_name}_unplaced.fasta \\
        --sample-id ${params.sample_name}
    """ : ""
    """
    rename_ragtag_scaffolds.py \\
        --input ${scaffold} \\
        --output ${params.sample_name}_scaffolds.fasta \\
        --sample-id ${params.sample_name}
    ${handle_unplaced}
    """
}
