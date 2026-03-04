process MERGE_ANNOTATIONS {
    tag "${params.sample_name}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/merged", mode: 'copy'
    publishDir "${params.outdir}/final_outputs", mode: 'copy', saveAs: { filename ->
        filename.endsWith('_merged.gff3') ? filename : null
    }

    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/gffutils:0.13--pyh7cba7a3_0' :
        'quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0' }"

    input:
    path ref_gff, stageAs: 'ref_liftoff_output.gff3'
    path vendor_gff, stageAs: 'vendor_liftoff_output.gff3'

    output:
    path "${params.sample_name}_merged.gff3",          emit: merged_gff
    path "${params.sample_name}_merge_summary.txt",    emit: merge_summary

    script:
    def always_keep_arg = params.always_keep_types ? "--always-keep-types '${params.always_keep_types}'" : ''
    """
    merge_annotations.py \\
        --reference ref_liftoff_output.gff3 \\
        --vendor vendor_liftoff_output.gff3 \\
        --output ${params.sample_name}_merged.gff3 \\
        --summary ${params.sample_name}_merge_summary.txt \\
        --overlap-threshold ${params.merge_overlap_threshold} \\
        --coord-preference ${params.coord_preference} \\
        --description-preference ${params.description_preference} \\
        ${always_keep_arg}
    """
}
