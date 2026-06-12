process CLASSIFY_UNPLACED {
    tag "${params.sample_name}"
    label 'process_single'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path agp
    path fai

    output:
    path "${params.sample_name}_unplaced_contigs.tsv", emit: unplaced_list

    script:
    """
    classify_unplaced_contigs.py \\
        --agp ${agp} \\
        --fai ${fai} \\
        --output ${params.sample_name}_unplaced_contigs.tsv
    """
}
