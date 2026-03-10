process DNAAPLER {
    tag "${params.sample_name}"
    label 'process_low'
    conda 'bioconda::dnaapler=1.1.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/dnaapler:1.1.0--pyhdfd78af_0' :
        'quay.io/biocontainers/dnaapler:1.1.0--pyhdfd78af_0' }"

    input:
    path assembly

    output:
    path "${params.sample_name}_reoriented.fasta", emit: reoriented

    script:
    """
    dnaapler all \
        -i ${assembly} \
        -o dnaapler_output \
        -p ${params.sample_name} \
        -t ${task.cpus}

    cp dnaapler_output/${params.sample_name}_reoriented.fasta ${params.sample_name}_reoriented.fasta
    """
}
