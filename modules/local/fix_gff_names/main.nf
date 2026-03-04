process FIX_GFF_NAMES {
    tag "${gff.baseName}"
    label 'process_low'
    publishDir "${params.outdir}/annotation_transfer/fix_names_${prefix}", mode: 'copy'

    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/gffutils:0.13--pyh7cba7a3_0' :
        'quay.io/biocontainers/gffutils:0.13--pyh7cba7a3_0' }"

    input:
    path gff
    val prefix

    output:
    path "${gff.baseName}_names_fixed.gff3", emit: fixed_gff
    path "${gff.baseName}_name_fix_summary.txt", emit: summary

    script:
    """
    fix_gff_names.py \\
        --input ${gff} \\
        --output ${gff.baseName}_names_fixed.gff3 \\
        --summary ${gff.baseName}_name_fix_summary.txt
    """
}
