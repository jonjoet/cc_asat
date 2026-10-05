include { RAGTAG_CORRECT           } from '../../modules/local/ragtag/correct/main'
include { RAGTAG_SCAFFOLD          } from '../../modules/local/ragtag/scaffold/main'
include { RENAME_RAGTAG_SCAFFOLDS  } from '../../modules/local/rename_ragtag_scaffolds/main'
include { CLASSIFY_UNPLACED        } from '../../modules/local/classify_unplaced/main'

workflow SCAFFOLDING {
    take:
    assembly
    reference
    reads           // file or null sentinel
    run_correct     // boolean value channel

    main:
    if (run_correct) {
        RAGTAG_CORRECT(assembly, reference, reads)
        ch_corrected = RAGTAG_CORRECT.out.corrected
    } else {
        ch_corrected = assembly
    }

    RAGTAG_SCAFFOLD(ch_corrected, reference)

    CLASSIFY_UNPLACED(RAGTAG_SCAFFOLD.out.agp, RAGTAG_SCAFFOLD.out.confidence)

    RENAME_RAGTAG_SCAFFOLDS(RAGTAG_SCAFFOLD.out.scaffold)

    emit:
    scaffold      = RENAME_RAGTAG_SCAFFOLDS.out.scaffold
    agp           = RAGTAG_SCAFFOLD.out.agp
    stats         = RAGTAG_SCAFFOLD.out.stats
    unplaced_list = CLASSIFY_UNPLACED.out.unplaced_list   // published via conf/modules.config (scaffold/, final_outputs/)
}
