include { DNAAPLER             } from '../modules/local/dnaapler/main'
include { SAMTOOLS_FAIDX       } from '../modules/local/samtools/faidx/main'
include { RAGTAG_PATCH              } from '../modules/local/ragtag/patch/main'
include { RESTORE_PATCH_SEQNAMES   } from '../modules/local/restore_patch_seqnames/main'
include { QUAST                } from '../modules/local/quast/main'
include { SEQTK_SEQ            } from '../modules/local/seqtk/seq/main'
include { AGAT_FIX_GFF as AGAT_FIX_REFERENCE_GFF } from '../modules/local/agat/fix_gff/main'
include { AGAT_FIX_GFF as AGAT_FIX_VENDOR_GFF    } from '../modules/local/agat/fix_gff/main'
include { SCAFFOLDING          } from '../subworkflows/local/scaffolding'
include { GAP_CLOSING          } from '../subworkflows/local/gap_closing'
include { ANNOTATION_TRANSFER  } from '../subworkflows/local/annotation_transfer'

workflow EUK_SCAFFOLD_VALIDATION {

    // ---- Input channels ----
    ch_assembly  = Channel.value(file(params.assembly, checkIfExists: true))
    ch_reference = Channel.value(file(params.reference, checkIfExists: true))

    ch_reference_gff_raw = params.reference_gff
        ? Channel.value(file(params.reference_gff, checkIfExists: true))
        : Channel.value(file('NO_GFF'))

    // ---- AGAT GFF fixing ----
    if (params.reference_gff && params.fix_reference_gff) {
        AGAT_FIX_REFERENCE_GFF(ch_reference_gff_raw, 'reference')
        ch_reference_gff = AGAT_FIX_REFERENCE_GFF.out.fixed_gff
    } else {
        ch_reference_gff = ch_reference_gff_raw
    }

    // ---- Index reference ----
    SAMTOOLS_FAIDX(ch_reference)

    // ---- Scaffolding ----
    if (params.run_correct && params.reads) {
        ch_reads_scaffold = Channel.value(file(params.reads, checkIfExists: true))
        SCAFFOLDING(ch_assembly, ch_reference, SAMTOOLS_FAIDX.out.fai.first(), ch_reads_scaffold, true)
    } else {
        SCAFFOLDING(ch_assembly, ch_reference, SAMTOOLS_FAIDX.out.fai.first(), Channel.value(file('NO_READS')), false)
    }
    ch_scaffolded = SCAFFOLDING.out.scaffold

    // ---- Gap closing ----
    if (params.reads) {
        ch_reads_gc = Channel.value(file(params.reads, checkIfExists: true))
        GAP_CLOSING(ch_scaffolded, ch_reads_gc)
        ch_gapclosed = GAP_CLOSING.out.gapclosed
    } else {
        ch_gapclosed = ch_scaffolded
    }

    // ---- Optional patch from reference ----
    if (params.fill_gaps_from_ref) {
        RAGTAG_PATCH(ch_gapclosed, ch_reference)
        RESTORE_PATCH_SEQNAMES(ch_gapclosed, RAGTAG_PATCH.out.patched, RAGTAG_PATCH.out.agp, RAGTAG_PATCH.out.rename_agp)
        ch_final = RESTORE_PATCH_SEQNAMES.out.renamed
    } else {
        ch_final = ch_gapclosed
    }

    // ---- Optional reorientation (on by default for bacterial) ----
    def do_reorient = params.reorient_assembly != null ? params.reorient_assembly : (params.organism_type == 'bacterial')
    if (do_reorient) {
        DNAAPLER(ch_final)
        ch_final = DNAAPLER.out.reoriented
    }

    // ---- Wrap final FASTA to 80 cols for broad tool compatibility ----
    SEQTK_SEQ(ch_final)

    // ---- Annotation transfer (conditional) ----
    def run_annotation_transfer = params.reference_gff && !params.skip_annotation_transfer

    if (run_annotation_transfer) {
        ch_vendor_gff_raw = params.vendor_gff
            ? Channel.value(file(params.vendor_gff, checkIfExists: true))
            : null

        // Fix vendor GFF if provided and fixing enabled
        if (params.vendor_gff && params.fix_vendor_gff) {
            AGAT_FIX_VENDOR_GFF(ch_vendor_gff_raw, 'vendor')
            ch_vendor_gff = AGAT_FIX_VENDOR_GFF.out.fixed_gff
        } else {
            ch_vendor_gff = ch_vendor_gff_raw
        }

        ANNOTATION_TRANSFER(
            ch_final,
            ch_reference,
            ch_reference_gff,
            ch_assembly,
            ch_vendor_gff,
            true
        )

        // QUAST runs after annotation transfer completes
        ch_final_for_quast = ch_final
            .combine(ANNOTATION_TRANSFER.out.lifted_gff)
            .map { it[0] }
        QUAST(ch_final_for_quast, ch_reference, ch_reference_gff)
    } else {
        // No annotation transfer — QUAST runs immediately
        QUAST(ch_final, ch_reference, ch_reference_gff)
    }
}
