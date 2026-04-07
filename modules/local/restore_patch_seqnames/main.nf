process RESTORE_PATCH_SEQNAMES {
    tag "${params.sample_name}"
    label 'process_low'
    input:
    path original_fasta
    path patched_fasta
    path patch_agp
    path rename_agp

    output:
    path "${params.sample_name}_patched.fasta", emit: renamed

    script:
    """
    restore_patch_seqnames.py \
        --original ${original_fasta} \
        --patched ${patched_fasta} \
        --patch-agp ${patch_agp} \
        --rename-agp ${rename_agp} \
        --output ${params.sample_name}_patched.fasta
    """
}
