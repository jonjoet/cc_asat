include { RENAME_RAGTAG_SCAFFOLDS } from '../../modules/local/rename_ragtag_scaffolds/main'
include { CLASSIFY_UNPLACED } from '../../modules/local/classify_unplaced/main'
include { SCAFFOLDING } from '../../subworkflows/local/scaffolding'

workflow {
    if (params.test_kind == 'correct') {
        SCAFFOLDING(file(params.assembly), file(params.reference), file(params.reads), true)
    } else if (params.test_kind == 'rename') {
        RENAME_RAGTAG_SCAFFOLDS(file(params.assembly))
    } else {
        RENAME_RAGTAG_SCAFFOLDS(file(params.assembly))
        CLASSIFY_UNPLACED(file(params.agp), file(params.confidence))
    }
}
