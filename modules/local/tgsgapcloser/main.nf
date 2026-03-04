process TGS_GAPCLOSER {
    tag "${params.sample_name}"
    label 'process_high'
    publishDir "${params.outdir}/gapclosed", mode: 'copy'

    conda 'bioconda::tgsgapcloser=1.2.1'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/tgsgapcloser:1.0.3--h8b12597_0' :
        'quay.io/biocontainers/tgsgapcloser:1.0.3--h8b12597_0' }"

    input:
    path scaffold
    path reads_fa

    output:
    path "gapclosed.scaff_seqs",      emit: gapclosed
    path "gapclosed.gap_fill_detail", emit: details

    script:
    """
    tgsgapcloser \
        --scaff ${scaffold} \
        --reads ${reads_fa} \
        --output gapclosed \
        --thread ${task.cpus} \
        --ne
    """
}
