process QUAST {
    tag "${params.sample_name}"
    label 'process_low'
    conda 'bioconda::quast=5.2.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/quast:5.2.0--py39pl5321h4e691d4_3' :
        'quay.io/biocontainers/quast:5.2.0--py39pl5321h4e691d4_3' }"

    input:
    path assembly
    path reference
    path reference_gff, stageAs: 'reference.gff'

    output:
    path "${params.sample_name}_quast_results", emit: report

    script:
    def fungus_arg = params.organism_type == 'fungal' ? '--fungus' : ''
    def gff_cmd = ''
    def gff_arg = ''
    if (reference_gff.name != 'NO_GFF') {
        gff_cmd = "cp -L ${reference_gff} local_reference.gff"
        gff_arg = "--features local_reference.gff"
    }
    """
    ${gff_cmd}

    quast ${assembly} \
        -r ${reference} \
        -o ${params.sample_name}_quast_results \
        --threads ${task.cpus} \
        --split-scaffolds \
        --labels ${params.sample_name} \
        ${gff_arg} \
        ${fungus_arg}
    """
}
