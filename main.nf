#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { EUK_SCAFFOLD_VALIDATION } from './workflows/euk_scaffold_validation'
include { ANNOTATION_TRANSFER_ONLY as ANNOTATION_TRANSFER_WORKFLOW } from './workflows/annotation_transfer_only'
include { preflight } from './utils/params'

workflow {
    def options = preflight(params)
    workflow.onComplete = {
        log.info ""
        log.info "Pipeline completed!"
        log.info "Results: ${params.outdir}"
        log.info ""
    }
    if (params.workflow == 'annotation_transfer_only') {
        ANNOTATION_TRANSFER_WORKFLOW(options)
    } else {
        EUK_SCAFFOLD_VALIDATION(options)
    }
}

// Compatibility route for NXF_SYNTAX_PARSER=v1 only; the selector is still validated.
workflow ANNOTATION_TRANSFER_ONLY {
    def options = preflight(params, true)
    log.info "INFO: Legacy -entry ANNOTATION_TRANSFER_ONLY selects annotation_transfer_only; --workflow does not select the route."
    workflow.onComplete = {
        log.info ""
        log.info "Pipeline completed!"
        log.info "Results: ${params.outdir}"
        log.info ""
    }
    ANNOTATION_TRANSFER_WORKFLOW(options)
}
