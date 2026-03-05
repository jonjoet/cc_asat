process DIFF_LIFTOFF_COPIES {
    tag "${params.sample_name}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/copy_analysis", mode: 'copy'
    publishDir "${params.outdir}/final_outputs", mode: 'copy'

    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path primary_gff, stageAs: 'primary_liftoff.gff3'
    path copies_gff, stageAs: 'copies_liftoff.gff3'

    output:
    path "${params.sample_name}_copy_report.txt", emit: copy_report

    script:
    """
    diff_liftoff_copies.py \\
        --primary primary_liftoff.gff3 \\
        --copies copies_liftoff.gff3 \\
        --output ${params.sample_name}_copy_report.txt
    """
}
