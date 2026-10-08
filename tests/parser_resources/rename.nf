include { RENAME_RAGTAG_SCAFFOLDS } from '../../modules/local/rename_ragtag_scaffolds/main'
include { FILTER_MEGAGENES } from '../../modules/local/filter_megagenes/main'
include { MERGE_ANNOTATIONS } from '../../modules/local/merge_annotations/main'
include { normalizeBoolean } from '../../utils/params'

workflow {
    if (params.test_kind == 'rename') {
        RENAME_RAGTAG_SCAFFOLDS(file(params.fixture + '/ragtag_scaffold.fasta')
                                )
    } else {
        FILTER_MEGAGENES(file(params.fixture + '/reference.gff3'), 'reference')
        MERGE_ANNOTATIONS(file(params.fixture + '/reference.gff3'), file(params.fixture + '/vendor.gff3'),
                          'iterative', normalizeBoolean('merge_novel_only', params.merge_novel_only))
    }
}
