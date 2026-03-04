include { LIFTOFF as LIFTOFF_REFERENCE } from '../../modules/local/liftoff/main'
include { LIFTOFF as LIFTOFF_VENDOR    } from '../../modules/local/liftoff/main'
include { FILTER_MEGAGENES as FILTER_MEGAGENES_REFERENCE } from '../../modules/local/filter_megagenes/main'
include { FILTER_MEGAGENES as FILTER_MEGAGENES_VENDOR    } from '../../modules/local/filter_megagenes/main'
include { FIX_GFF_NAMES as FIX_GFF_NAMES_REFERENCE } from '../../modules/local/fix_gff_names/main'
include { FIX_GFF_NAMES as FIX_GFF_NAMES_VENDOR    } from '../../modules/local/fix_gff_names/main'
include { MERGE_ANNOTATIONS            } from '../../modules/local/merge_annotations/main'

workflow ANNOTATION_TRANSFER {
    take:
    final_assembly     // final assembly FASTA
    reference          // reference genome FASTA
    reference_gff      // reference GFF3
    original_assembly  // original de novo assembly FASTA (source for vendor annotations)
    vendor_gff         // vendor GFF3 or null sentinel

    main:
    // --- Megagene filtering (reference) ---
    FILTER_MEGAGENES_REFERENCE(reference_gff, 'reference')
    ch_ref_gff_filtered = FILTER_MEGAGENES_REFERENCE.out.filtered_gff

    // --- Liftoff reference annotations onto final assembly ---
    LIFTOFF_REFERENCE(final_assembly, reference, ch_ref_gff_filtered, 'reference')

    // --- Optional name fix (reference) ---
    if (params.fix_generic_names) {
        FIX_GFF_NAMES_REFERENCE(LIFTOFF_REFERENCE.out.lifted_gff, 'reference')
        ch_ref_lifted = FIX_GFF_NAMES_REFERENCE.out.fixed_gff
    } else {
        ch_ref_lifted = LIFTOFF_REFERENCE.out.lifted_gff
    }

    // --- Conditionally: lift vendor annotations and merge ---
    ch_merged_gff     = Channel.empty()
    ch_merge_summary  = Channel.empty()
    ch_vendor_lifted  = Channel.empty()

    if (vendor_gff) {
        // Megagene filtering (vendor)
        FILTER_MEGAGENES_VENDOR(vendor_gff, 'vendor')
        ch_vendor_gff_filtered = FILTER_MEGAGENES_VENDOR.out.filtered_gff

        LIFTOFF_VENDOR(final_assembly, original_assembly, ch_vendor_gff_filtered, 'vendor')

        // Optional name fix (vendor)
        if (params.fix_generic_names) {
            FIX_GFF_NAMES_VENDOR(LIFTOFF_VENDOR.out.lifted_gff, 'vendor')
            ch_vendor_lifted_final = FIX_GFF_NAMES_VENDOR.out.fixed_gff
        } else {
            ch_vendor_lifted_final = LIFTOFF_VENDOR.out.lifted_gff
        }
        ch_vendor_lifted = ch_vendor_lifted_final

        if (!params.skip_merge) {
            MERGE_ANNOTATIONS(ch_ref_lifted, ch_vendor_lifted_final)
            ch_merged_gff    = MERGE_ANNOTATIONS.out.merged_gff
            ch_merge_summary = MERGE_ANNOTATIONS.out.merge_summary
        }
    }

    emit:
    lifted_gff        = LIFTOFF_REFERENCE.out.lifted_gff
    unmapped          = LIFTOFF_REFERENCE.out.unmapped
    vendor_lifted_gff = ch_vendor_lifted
    merged_gff        = ch_merged_gff
    merge_summary     = ch_merge_summary
}
