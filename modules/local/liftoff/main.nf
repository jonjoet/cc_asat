process LIFTOFF {
    tag "${params.sample_name}"
    label 'process_medium'
    publishDir "${params.outdir}/annotation_transfer/liftoff_${prefix}", mode: 'copy'
    publishDir "${params.outdir}/final_outputs", mode: 'copy', saveAs: { filename ->
        filename.endsWith('_liftoff.gff3') ? filename : null
    }

    conda 'bioconda::liftoff=1.6.3'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/liftoff:1.6.3--pyhdfd78af_0' :
        'quay.io/biocontainers/liftoff:1.6.3--pyhdfd78af_0' }"

    input:
    path target_assembly
    path source_assembly
    path source_gff, stageAs: 'input_source.gff3'
    val prefix

    output:
    path "${params.sample_name}_${prefix}_liftoff.gff3",   emit: lifted_gff
    path "${params.sample_name}_${prefix}_unmapped.txt",    emit: unmapped

    script:
    """
    cp -L ${source_gff} local_source.gff3
    cp -L ${source_assembly} local_source.fasta

    liftoff \
        -g local_source.gff3 \
        -o ${params.sample_name}_${prefix}_liftoff.gff3 \
        -u ${params.sample_name}_${prefix}_unmapped.txt \
        -copies \
        -p ${task.cpus} \
        ${target_assembly} \
        local_source.fasta
    """
}
