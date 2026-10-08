process RENAME_RAGTAG_SCAFFOLDS {
    tag "${params.sample_name}"
    label 'process_single'
    container "${ workflow.containerEngine == 'singularity' ?
        'https://depot.galaxyproject.org/singularity/python:3.12' :
        'python:3.12' }"

    input:
    path scaffold

    output:
    path "${params.sample_name}_scaffolds.fasta", emit: scaffold

    script:
    def pattern = params.scaffold_rename_pattern
    if (pattern != null && (!(pattern instanceof String) || pattern.isEmpty())) {
        error "ERROR: --scaffold_rename_pattern must be null or a nonempty string."
    }
    def safe_pattern = pattern?.replace("'", "'\\''")
    def pattern_arg = pattern != null ? "'--chr-pattern=${safe_pattern}'" : ""
    """
    rename_ragtag_scaffolds.py \\
        --input ${scaffold} \\
        --output ${params.sample_name}_scaffolds.fasta \\
        --sample-id ${params.sample_name} \\
        ${pattern_arg}
    """
}
