process LIFTOFF {
    tag "${params.sample_name}"
    label 'process_medium'
    conda 'bioconda::liftoff=1.6.3'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/liftoff:1.6.3--pyhdfd78af_0' :
        'quay.io/biocontainers/liftoff:1.6.3--pyhdfd78af_0' }"

    input:
    path target_assembly
    path source_assembly
    path source_gff, stageAs: 'input_source.gff3'
    val prefix
    val use_copies

    output:
    path "${params.sample_name}_${prefix}_liftoff.gff3",   emit: lifted_gff
    path "${params.sample_name}_${prefix}_unmapped.txt",    emit: unmapped

    script:
    def copies_arg = use_copies ? "-copies -sc ${params.liftoff_sc}" : ''
    def feature_types_arg = params.liftoff_feature_types ? "-f feature_types.txt" : ''
    """
    cp -L ${source_gff} local_source.gff3
    cp -L ${source_assembly} local_source.fasta

    # Write additional feature types file (one type per line) for Liftoff -f
    printf '%s\\n' ${params.liftoff_feature_types} > feature_types.txt

    liftoff \
        -g local_source.gff3 \
        -o ${params.sample_name}_${prefix}_liftoff.gff3 \
        -u ${params.sample_name}_${prefix}_unmapped.txt \
        -s ${params.liftoff_s} \
        ${copies_arg} \
        ${feature_types_arg} \
        -p ${task.cpus} \
        ${target_assembly} \
        local_source.fasta
    """
}
