/*
 * Annotation Transfer Only Workflow
 *
 * Transfers annotations from a reference genome to a target assembly using Liftoff.
 * Optionally merges vendor annotations if provided.
 */

include { ANNOTATION_TRANSFER } from '../subworkflows/local/annotation_transfer'
include { DNAAPLER             } from '../modules/local/dnaapler/main'
include { QUAST                } from '../modules/local/quast/main'
include { AGAT_FIX_GFF as AGAT_FIX_REFERENCE_GFF } from '../modules/local/agat/fix_gff/main'
include { AGAT_FIX_GFF as AGAT_FIX_VENDOR_GFF    } from '../modules/local/agat/fix_gff/main'

workflow ANNOTATION_TRANSFER_ONLY {

    // ---- Input channels ----
    ch_assembly  = Channel.value(file(params.assembly, checkIfExists: true))
    ch_reference = Channel.value(file(params.reference, checkIfExists: true))
    ch_reference_gff_raw = Channel.value(file(params.reference_gff, checkIfExists: true))

    // ---- AGAT GFF fixing ----
    if (params.fix_reference_gff) {
        AGAT_FIX_REFERENCE_GFF(ch_reference_gff_raw, 'reference')
        ch_reference_gff = AGAT_FIX_REFERENCE_GFF.out.fixed_gff
    } else {
        ch_reference_gff = ch_reference_gff_raw
    }

    // For vendor annotation merging (optional)
    ch_original_assembly = params.original_assembly
        ? Channel.value(file(params.original_assembly, checkIfExists: true))
        : ch_assembly

    ch_vendor_gff_raw = params.vendor_gff
        ? Channel.value(file(params.vendor_gff, checkIfExists: true))
        : null

    if (params.vendor_gff && params.fix_vendor_gff) {
        AGAT_FIX_VENDOR_GFF(ch_vendor_gff_raw, 'vendor')
        ch_vendor_gff = AGAT_FIX_VENDOR_GFF.out.fixed_gff
    } else {
        ch_vendor_gff = ch_vendor_gff_raw
    }

    // ---- Optional reorientation (on by default for bacterial) ----
    def do_reorient = params.reorient_assembly != null ? params.reorient_assembly : (params.organism_type == 'bacterial')
    if (do_reorient) {
        DNAAPLER(ch_assembly)
        ch_assembly = DNAAPLER.out.reoriented
    }

    // ---- Run annotation transfer ----
    ANNOTATION_TRANSFER(
        ch_assembly,
        ch_reference,
        ch_reference_gff,
        ch_original_assembly,
        ch_vendor_gff
    )

    // ---- QUAST (runs after annotation transfer completes) ----
    ch_assembly_for_quast = ch_assembly
        .combine(ANNOTATION_TRANSFER.out.lifted_gff)
        .map { it[0] }
    QUAST(ch_assembly_for_quast, ch_reference, ch_reference_gff)

    emit:
    lifted_gff        = ANNOTATION_TRANSFER.out.lifted_gff
    unmapped          = ANNOTATION_TRANSFER.out.unmapped
    vendor_lifted_gff = ANNOTATION_TRANSFER.out.vendor_lifted_gff
    merged_gff        = ANNOTATION_TRANSFER.out.merged_gff
    merge_summary     = ANNOTATION_TRANSFER.out.merge_summary
}
