include { SEQTK_FQ2FA   } from '../../modules/local/seqtk/fq2fa/main'
include { TGS_GAPCLOSER } from '../../modules/local/tgsgapcloser/main'

workflow GAP_CLOSING {
    take:
    scaffold
    reads

    main:
    SEQTK_FQ2FA(reads)
    TGS_GAPCLOSER(scaffold, SEQTK_FQ2FA.out.reads_fa)

    emit:
    gapclosed = TGS_GAPCLOSER.out.gapclosed
    details   = TGS_GAPCLOSER.out.details
}
