process AGAT_FIX_GFF {
    tag "${gff.baseName}"
    label 'process_low'
    conda 'bioconda::agat=1.4.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/agat:1.4.0--pl5321hdfd78af_0' :
        'quay.io/biocontainers/agat:1.4.0--pl5321hdfd78af_0' }"

    input:
    path gff
    val prefix

    output:
    path "${gff.baseName}_fixed.gff3", emit: fixed_gff

    script:
    """
    agat_convert_sp_gxf2gxf.pl \\
        --gxf ${gff} \\
        --output ${gff.baseName}_fixed.gff3
    """
}
