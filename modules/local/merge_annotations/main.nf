process MERGE_ANNOTATIONS {
    tag "${params.sample_name}"
    label 'process_low'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/gffutils:0.13--pyh7cba7a3_0' :
        'quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0' }"

    input:
    path ref_gff, stageAs: 'ref_liftoff_output.gff3'
    path vendor_gff, stageAs: 'vendor_liftoff_output.gff3'
    val merge_label

    output:
    path "${params.sample_name}_merged${merge_label ? '_' + merge_label : ''}.gff3",       emit: merged_gff
    path "${params.sample_name}_merge${merge_label ? '_' + merge_label : ''}_summary.txt", emit: merge_summary

    script:
    def label_suffix = merge_label ? "_${merge_label}" : ''
    def skip_types_arg = params.merge_skip_types ? "--skip-types '${params.merge_skip_types}'" : ''
    def novel_only_arg = params.merge_novel_only ? '--novel-only' : ''
    """
    merge_annotations.py \\
        --reference ref_liftoff_output.gff3 \\
        --vendor vendor_liftoff_output.gff3 \\
        --output ${params.sample_name}_merged${label_suffix}.gff3 \\
        --summary ${params.sample_name}_merge${label_suffix}_summary.txt \\
        --overlap-threshold ${params.merge_overlap_threshold} \\
        --coord-preference ${params.coord_preference} \\
        --description-preference ${params.description_preference} \\
        --exact-fields '${params.merge_exact_fields}' \\
        --word-fields '${params.merge_word_fields}' \\
        --word-min-length ${params.merge_word_min_length} \\
        ${skip_types_arg} \\
        ${novel_only_arg}
    """
}
