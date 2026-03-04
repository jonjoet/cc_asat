include { RAGTAG_CORRECT  } from '../../modules/local/ragtag/correct/main'
include { RAGTAG_SCAFFOLD } from '../../modules/local/ragtag/scaffold/main'

workflow SCAFFOLDING {
    take:
    assembly
    reference
    reads         // file or null sentinel
    run_correct   // boolean value channel

    main:
    if (run_correct) {
        RAGTAG_CORRECT(assembly, reference, reads)
        ch_corrected = RAGTAG_CORRECT.out.corrected
    } else {
        ch_corrected = assembly
    }

    RAGTAG_SCAFFOLD(ch_corrected, reference)

    emit:
    scaffold  = RAGTAG_SCAFFOLD.out.scaffold
    agp       = RAGTAG_SCAFFOLD.out.agp
    stats     = RAGTAG_SCAFFOLD.out.stats
}
