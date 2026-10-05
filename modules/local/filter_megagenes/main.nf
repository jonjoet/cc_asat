process FILTER_MEGAGENES {
    tag "${gff.baseName}"
    label 'process_low'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/gffutils:0.13--pyh7cba7a3_0' :
        'quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0' }"

    input:
    path gff
    val prefix

    output:
    path "${gff.baseName}_megafiltered.gff3", emit: filtered_gff
    path "${gff.baseName}_megagene_summary.txt", emit: summary

    script:
    def max_len_arg = (params.max_gene_length_bp && !(params.max_gene_length_bp.toString().trim() ==~ /[+-]?0+(?:\.0+)?/)) ? "--max-length-bp ${params.max_gene_length_bp}" : ''
    """
    filter_megagenes.py \\
        --input ${gff} \\
        --output ${gff.baseName}_megafiltered.gff3 \\
        --summary ${gff.baseName}_megagene_summary.txt \\
        --gene-threshold ${params.megagene_gene_threshold} \\
        ${max_len_arg}
    """
}
