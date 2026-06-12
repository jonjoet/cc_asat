process RAGTAG_SCAFFOLD {
    tag "${params.sample_name}"
    label 'process_medium'
    conda 'bioconda::ragtag=2.1.0'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/ragtag:2.1.0--pyhb7b1952_0' :
        'quay.io/biocontainers/ragtag:2.1.0--pyhb7b1952_0' }"

    input:
    path assembly
    path reference

    output:
    path "ragtag_out/ragtag.scaffold.fasta",            emit: scaffold
    path "ragtag_out/ragtag.scaffold.agp",              emit: agp
    path "ragtag_out/ragtag.scaffold.stats",            emit: stats

    script:
    """
    ragtag.py scaffold \
        ${reference} \
        ${assembly} \
        -o ragtag_out \
        -u \
        -t ${task.cpus}
    """
}
