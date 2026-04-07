process RAGTAG_CORRECT {
    tag "${params.sample_name}"
    label 'process_medium'
    conda 'bioconda::ragtag=2.1.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/ragtag:2.1.0--pyhb7b1952_0' :
        'quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0' }"

    input:
    path assembly
    path reference
    path reads

    output:
    path "ragtag_correct_out/ragtag.correct.fasta", emit: corrected

    script:
    """
    ragtag.py correct \
        ${reference} \
        ${assembly} \
        -R ${reads} \
        -T ${params.read_type} \
        -u \
        -o ragtag_correct_out \
        -t ${task.cpus}
    """
}
