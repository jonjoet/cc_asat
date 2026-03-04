#!/usr/bin/env nextflow

/*
 * Microbial Scaffold Validation Pipeline
 *
 * Scaffold -> Gap-close -> Annotate -> Compare workflow for validating
 * de novo assemblies against a reference genome.
 */

nextflow.enable.dsl = 2

include { EUK_SCAFFOLD_VALIDATION } from './workflows/euk_scaffold_validation'
include { ANNOTATION_TRANSFER_ONLY as ANNOTATION_TRANSFER_WORKFLOW } from './workflows/annotation_transfer_only'

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

def validateInputs() {
    if (!params.assembly) {
        error "ERROR: --assembly is required (pre-built de novo assembly FASTA)"
    }
    if (!params.reference) {
        error "ERROR: --reference is required (reference genome FASTA)"
    }
    if (!params.organism_type || !(params.organism_type in ['fungal', 'bacterial'])) {
        error "ERROR: --organism_type is required and must be 'fungal' or 'bacterial'"
    }
    if (params.run_correct && !params.reads) {
        error "ERROR: --run_correct requires --reads to be provided"
    }
}

// ---------------------------------------------------------------------------
// Main workflow
// ---------------------------------------------------------------------------

workflow {
    validateInputs()
    EUK_SCAFFOLD_VALIDATION()
}

// ---------------------------------------------------------------------------
// Alternative entry: Annotation Transfer Only
// Usage: nextflow run main.nf -entry ANNOTATION_TRANSFER_ONLY --assembly ... --reference ... --reference_gff ...
// ---------------------------------------------------------------------------

workflow ANNOTATION_TRANSFER_ONLY {
    // Simplified validation for annotation transfer only
    if (!params.assembly) {
        error "ERROR: --assembly is required"
    }
    if (!params.reference) {
        error "ERROR: --reference is required"
    }
    if (!params.reference_gff) {
        error "ERROR: --reference_gff is required for annotation transfer"
    }

    ANNOTATION_TRANSFER_WORKFLOW()
}

// ---------------------------------------------------------------------------
// Workflow completion
// ---------------------------------------------------------------------------

workflow.onComplete {
    log.info ""
    log.info "Pipeline completed!"
    log.info "Results: ${params.outdir}"
    log.info ""
}
