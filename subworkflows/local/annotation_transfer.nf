include { LIFTOFF as LIFTOFF_REFERENCE        } from '../../modules/local/liftoff/main'
include { LIFTOFF as LIFTOFF_REFERENCE_COPIES } from '../../modules/local/liftoff/main'
include { LIFTOFF as LIFTOFF_VENDOR           } from '../../modules/local/liftoff/main'
include { FILTER_MEGAGENES as FILTER_MEGAGENES_REFERENCE } from '../../modules/local/filter_megagenes/main'
include { FILTER_MEGAGENES as FILTER_MEGAGENES_VENDOR    } from '../../modules/local/filter_megagenes/main'
include { FIX_GFF_NAMES as FIX_GFF_NAMES_REFERENCE        } from '../../modules/local/fix_gff_names/main'
include { FIX_GFF_NAMES as FIX_GFF_NAMES_REFERENCE_COPIES } from '../../modules/local/fix_gff_names/main'
include { FIX_GFF_NAMES as FIX_GFF_NAMES_VENDOR           } from '../../modules/local/fix_gff_names/main'
include { MERGE_ANNOTATIONS as MERGE_FULL      } from '../../modules/local/merge_annotations/main'
include { MERGE_ANNOTATIONS as MERGE_ITERATIVE } from '../../modules/local/merge_annotations/main'
include { DIFF_LIFTOFF_COPIES                  } from '../../modules/local/diff_liftoff_copies/main'

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

    // --- Primary reference liftoff (no copies — iterative-safe) ---
    LIFTOFF_REFERENCE(final_assembly, reference, ch_ref_gff_filtered, 'reference', false)

    // --- Optional name fix (reference primary) ---
    if (params.fix_generic_names) {
        FIX_GFF_NAMES_REFERENCE(LIFTOFF_REFERENCE.out.lifted_gff, 'reference')
        ch_ref_lifted = FIX_GFF_NAMES_REFERENCE.out.fixed_gff
    } else {
        ch_ref_lifted = LIFTOFF_REFERENCE.out.lifted_gff
    }

    // --- Copies reference liftoff (with -copies — for copy analysis) ---
    ch_ref_lifted_copies = Channel.empty()
    ch_copy_report       = Channel.empty()

    if (params.liftoff_copies) {
        LIFTOFF_REFERENCE_COPIES(final_assembly, reference, ch_ref_gff_filtered, 'reference_copies', true)

        // Name fix (reference copies)
        if (params.fix_generic_names) {
            FIX_GFF_NAMES_REFERENCE_COPIES(LIFTOFF_REFERENCE_COPIES.out.lifted_gff, 'reference_copies')
            ch_ref_lifted_copies = FIX_GFF_NAMES_REFERENCE_COPIES.out.fixed_gff
        } else {
            ch_ref_lifted_copies = LIFTOFF_REFERENCE_COPIES.out.lifted_gff
        }

        // Copy report (diff primary vs copies)
        DIFF_LIFTOFF_COPIES(LIFTOFF_REFERENCE.out.lifted_gff, LIFTOFF_REFERENCE_COPIES.out.lifted_gff)
        ch_copy_report = DIFF_LIFTOFF_COPIES.out.copy_report
    }

    // --- Conditionally: lift vendor annotations and merge ---
    ch_merged_gff              = Channel.empty()
    ch_merge_summary           = Channel.empty()
    ch_merged_iterative_gff    = Channel.empty()
    ch_merge_iterative_summary = Channel.empty()
    ch_vendor_lifted           = Channel.empty()

    if (vendor_gff) {
        // Megagene filtering (vendor)
        FILTER_MEGAGENES_VENDOR(vendor_gff, 'vendor')
        ch_vendor_gff_filtered = FILTER_MEGAGENES_VENDOR.out.filtered_gff

        LIFTOFF_VENDOR(final_assembly, original_assembly, ch_vendor_gff_filtered, 'vendor', false)

        // Optional name fix (vendor)
        if (params.fix_generic_names) {
            FIX_GFF_NAMES_VENDOR(LIFTOFF_VENDOR.out.lifted_gff, 'vendor')
            ch_vendor_lifted_final = FIX_GFF_NAMES_VENDOR.out.fixed_gff
        } else {
            ch_vendor_lifted_final = LIFTOFF_VENDOR.out.lifted_gff
        }
        ch_vendor_lifted = ch_vendor_lifted_final

        if (!params.skip_merge) {
            // Iterative merge: primary ref (no copies) + vendor — always produced
            MERGE_ITERATIVE(ch_ref_lifted, ch_vendor_lifted_final, 'iterative')
            ch_merged_iterative_gff    = MERGE_ITERATIVE.out.merged_gff
            ch_merge_iterative_summary = MERGE_ITERATIVE.out.merge_summary

            // Full merge: copies ref + vendor — only if copies enabled
            if (params.liftoff_copies) {
                MERGE_FULL(ch_ref_lifted_copies, ch_vendor_lifted_final, '')
                ch_merged_gff    = MERGE_FULL.out.merged_gff
                ch_merge_summary = MERGE_FULL.out.merge_summary
            }
        }
    }

    emit:
    lifted_gff              = LIFTOFF_REFERENCE.out.lifted_gff          // primary ref liftoff (no copies)
    unmapped                = LIFTOFF_REFERENCE.out.unmapped
    vendor_lifted_gff       = ch_vendor_lifted
    merged_gff              = ch_merged_gff                              // full merge (with copies ref)
    merge_summary           = ch_merge_summary
    merged_iterative_gff    = ch_merged_iterative_gff                    // iterative merge (no copies ref)
    merge_iterative_summary = ch_merge_iterative_summary
    copy_report             = ch_copy_report
}
