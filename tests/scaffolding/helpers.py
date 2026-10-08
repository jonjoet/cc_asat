#!/usr/bin/env python3
"""Independent stdlib CLI regressions and deterministic gate fixture generation."""
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

HEADER = 'contig_id\tobject_name\tlength_bp\n'
CONF = 'query\tgrouping_confidence\tlocation_confidence\torientation_confidence\n'


def records(path):
    result = []
    for line in Path(path).read_text().splitlines():
        if line.startswith('>'):
            result.append([line[1:].split()[0], ''])
        else:
            result[-1][1] += line.strip()
    assert len({r[0] for r in result}) == len(result), path
    return result


def fasta(path, rows):
    path.write_text(''.join('>' + name + '\n' + '\n'.join(seq[i:i+80] for i in range(0, len(seq), 80)) + '\n' for name, seq in rows))


def generated(seed, length=6000):
    state = seed
    def step():
        nonlocal state
        state = (1664525 * state + 1013904223) % 2**32
        return state
    seq = ''.join('ACGT'[step() >> 30] for _ in range(length))
    codons = sorted(''.join(c) for c in itertools.product('ACGT', repeat=3) if ''.join(c) not in ('TAA', 'TAG', 'TGA'))
    gene = 'ATG' + ''.join(codons[(step() >> 16) % 61] for _ in range(297)) + 'TAA'
    return seq[:1000] + gene + seq[1897:]


def generate(repo, directory, kind):
    """Inputs are literal or independently generated; no production-helper oracle."""
    directory.mkdir()
    fixture = repo / 'tests/fixtures/parser_resources'
    if kind.startswith('FULL-'):
        pattern = kind == 'FULL-PATTERN'
        chromosome = records(fixture / 'assembly.fasta')[0][1]
        query = 'contig_3' if pattern else 'strain_ChrI'
        plasmid = generated(20261006)
        fasta(directory / 'assembly.fasta', [(query, chromosome), ('2micron_plasmid', plasmid)])
        refs = [('strain_ChrI', chromosome)]
        if pattern:
            refs.append(('2micron_plasmid', generated(20261007)))
        fasta(directory / 'reference.fasta', refs)
        (directory / 'reference.gff3').write_text((fixture / 'reference.gff3').read_text().replace('chr1\t', 'strain_ChrI\t'))
        vendor = (fixture / 'vendor.gff3').read_text().replace('chr1\t', query + '\t')
        plasmid_gene = ''.join(line.replace('chr1\t', '2micron_plasmid\t').replace('gene1', 'plasmid_gene1').replace('transcript1', 'plasmid_transcript1').replace('exon1', 'plasmid_exon1').replace('cds1', 'plasmid_cds1').replace('fixture_gene', 'plasmid_gene') + '\n'
            for line in (fixture / 'vendor.gff3').read_text().splitlines() if line and not line.startswith('#'))
        (directory / 'vendor.gff3').write_text(vendor + plasmid_gene)
        expected = HEADER + '2micron_plasmid\t2micron_plasmid_RagTag\t6000\n'
        recipe = dict(kind=kind, query=query, plasmid_seed=20261006, reference_plasmid_seed=20261007 if pattern else None,
                      length=6000, gene_offset=1000, gene_length=897)
    elif kind == 'CORRECTION':
        for name in ('reference.fasta', 'reads.fastq'):
            (directory / name).write_bytes((fixture / name).read_bytes())
        fasta(directory / 'assembly.fasta', [('contig_3', records(fixture / 'assembly.fasta')[0][1])])
        expected, recipe = HEADER, dict(kind=kind, confidence_query='contig_3_1_30000_+')
    else:
        quote = kind == 'MODULE-QUOTED'
        placed = kind == 'MODULE-PLACED'
        name = "strain-ChrI'_RagTag" if quote else 'strain_ChrI_RagTag'
        fasta(directory / 'assembly.fasta', [(name, 'ACGTNNACGT'), ('2micron_plasmid_RagTag', 'GGGAAACCC')])
        # Both N and U gap fixtures. Query IDs need not equal FASTA object IDs.
        agp = ('strain_ChrI_RagTag\t1\t4\t1\tW\tctgA\t1\t4\t+\n'
               'strain_ChrI_RagTag\t5\t6\t2\tN\t2\tscaffold\tyes\talign_genus\n'
               'strain_ChrI_RagTag\t7\t10\t3\tW\tctgB\t1\t4\t+\n'
               'other\t1\t4\t1\tW\tctgC\t1\t4\t+\n'
               'other\t5\t6\t2\tU\t2\tscaffold\tyes\talign_genus\n'
               'other\t7\t10\t3\tW\tctgD\t1\t4\t+\n'
               '2micron_plasmid_RagTag\t1\t9\t1\tW\t2micron_plasmid\t1\t9\t+\n')
        (directory / 'scaffold.agp').write_text(agp)
        queries = ['ctgA', 'ctgB', 'ctgC', 'ctgD'] + (['2micron_plasmid'] if placed else [])
        (directory / 'confidence.txt').write_text(CONF + ''.join(q + '\t1\t1\t1\n' for q in queries))
        expected = HEADER + ('' if placed else '2micron_plasmid\t2micron_plasmid_RagTag\t9\n')
        recipe = dict(kind=kind)
    (directory / 'expected.tsv').write_text(expected)
    (directory / 'recipe.json').write_text(json.dumps(recipe, indent=2) + '\n')
    (directory / 'hashes.tsv').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '\t' + str(p) + '\n'
                                               for p in sorted(directory.iterdir()) if p.is_file()))


def checks(repo, evidence):
    cases = []
    def rename(case, text, expected=None, pattern=None, error=None, alias=None):
        cases.append(dict(id=case, helper='rename', text=text, expected=expected, pattern=pattern, error=error, alias=alias))
    sequence = 'ACGT\nNNAC\n'
    names = ['contig_3', '2micron_plasmid', 'LEXst001_ChrI', 'NZ_CP012345.1', 'contig_7_RagTag_RagTag', 'S_already']
    rename('DEFAULT', ''.join('>' + n + ' description\n' + sequence for n in names),
           ['S_contig_3', 'S_2micron_plasmid', 'S_LEXst001_ChrI', 'S_NZ_CP012345.1', 'S_contig_7_RagTag', 'S_already'])
    rename('ROMAN', '>strain_ChrI_RagTag\nACGT\n>S_ChrII\nTGCA\n>plasmid\nAAAA\n', ['S_ChrI','S_ChrII','S_plasmid'], r'_(Chr[IVXLCDM]+)$')
    rename('BACTERIAL', '>strain_Chr\nACGT\n>strain_Chr2\nTGCA\n', ['S_Chr','S_Chr2'], r'_(Chr[0-9IVXLCDM]*)$')
    rename('SOURCE-ORDER', '>S288C_R64_ChrI\nACGT\n', ['S288C_ChrI'], r'_(Chr[IVXLCDM]+)$')
    rename('LEADING-HYPHEN', '>strain-ChrI_RagTag\nACGT\n', ['S_ChrI'], r'-(Chr[IVX]+)$')
    rename('QUOTE-BACKSLASH', ">strain-ChrI'\\_RagTag\nACGT\n", ['S_ChrI'], r"-(Chr[IVX]+)'\\$")
    for case, pattern, text, error in (
        ('REGEX-SYNTAX','(', '>x\nACGT\n','syntax'), ('ZERO-GROUP','never', '>x\nACGT\n','exactly one'),
        ('MULTIPLE-GROUP','(never)(match)', '>x\nACGT\n','exactly one'),
        ('UNMATCHED-GROUP','(y)?x', '>x\nACGT\n','empty or unmatched'),
        ('EMPTY-GROUP','(x*)', '>z\nACGT\n','empty or unmatched'),
        ('DUPLICATE',None, '>x\nACGT\n>x desc\nTGCA\n','duplicate input'),
        ('CONVERGENT-PREFIX',None, '>x\nACGT\n>S_x\nTGCA\n','convergent final'),
        ('CONVERGENT-PATTERN',r'_(ChrI)$', '>a_ChrI\nACGT\n>b_ChrI\nTGCA\n','convergent final')):
        rename(case, text, pattern=pattern, error=error)
    for alias in ('same', 'symlink', 'hardlink'):
        rename('ALIAS-' + alias, '>x\nACGT\n', error='input/output alias', alias=alias)
    def classify(case, agp, confidence=CONF, expected=HEADER, error=None):
        cases.append(dict(id=case, helper='classify', agp=agp, confidence=confidence, expected=expected, error=error))
    w = 'chr1_RagTag\t1\t4\t1\tW\tchr1\t1\t4\t+\n'
    classify('SAME-NAME-PLACED', w, CONF+'chr1\t1\t1\t1\n')
    classify('SAME-NAME-UNPLACED', w, expected=HEADER+'chr1\tchr1_RagTag\t4\n')
    classify('RAW-SUFFIX', w.replace('chr1\t1\t4\t+', 'chr1_RagTag\t1\t4\t+'), expected=HEADER+'chr1_RagTag\tchr1_RagTag\t4\n')
    classify('EMPTY', '')
    classify('COMMENTS', '\n# empty\n')
    classify('IGNORED-TYPE', 'x\tbogus\tx\ty\tF\n')
    for gap in ('N', 'U'):
        multi = ('ref\t1\t4\t1\tW\ta\t1\t4\t+\nref\t5\t6\t2\t'+gap+'\t2\tscaffold\tyes\talign_genus\nref\t7\t10\t3\tW\tb\t1\t4\t+\n')
        classify('MULTI-'+gap, multi, CONF+'a\t1\t1\t1\nb\t1\t1\t1\n')
        classify('ALL-UNPLACED-'+gap, multi, expected=HEADER+'a\tref\t4\nb\tref\t4\n')
    classify('MULTIPLE-ORDER', w + 'z_RagTag\t1\t3\t1\tW\tz\t1\t3\t+\n', expected=HEADER+'chr1\tchr1_RagTag\t4\nz\tz_RagTag\t3\n')
    for case, text in (
        ('AGP-SHORT', 'x\t1\t4\t1\n'), ('AGP-W-SHORT', 'x\t1\t4\t1\tW\tx\n'),
        ('AGP-START', w.replace('\t1\t4\t1', '\t0\t4\t1')),
        ('AGP-END', w.replace('\t1\t4\t1', '\t4\t1\t1')),
        ('AGP-NUMERIC', w.replace('\t1\t4\t1', '\tx\t4\t1')),
        ('AGP-COMPONENT', w.replace('chr1\t1\t4\t+', 'chr1\t1\t3\t+')),
        ('AGP-ORIENTATION', w.replace('\t+\n', '\tbad\n')),
        ('AGP-N', 'x\t1\t4\t1\tN\t3\tscaffold\tyes\talign_genus\n'),
        ('AGP-U', 'x\t1\t4\t1\tU\t4\tscaffold\tbad\talign_genus\n')):
        classify(case, text, error='malformed AGP')
    for case, text, error in (
        ('CONF-MISSING',None,'missing/unreadable confidence'), ('CONF-ZERO','','header'), ('CONF-HEADER','wrong\n','header'),
        ('CONF-FIELDS',CONF+'chr1\t1\t1\n','four fields'), ('CONF-EMPTY',CONF+'\t1\t1\t1\n','empty or duplicate'),
        ('CONF-DUPLICATE',CONF+'chr1\t1\t1\t1\nchr1\t1\t1\t1\n','empty or duplicate'),
        ('CONF-NONNUMERIC',CONF+'chr1\tx\t1\t1\n','nonnumeric'), ('CONF-NAN',CONF+'chr1\tnan\t1\t1\n','nonfinite'),
        ('CONF-INF',CONF+'chr1\t1\tinf\t1\n','nonfinite'), ('CONF-INCONSISTENT',CONF+'other\t1\t1\t1\n','inconsistent confidence')):
        classify(case, w, text, error=error)
    cases = [dict(id='SELF-'+script, helper='self', script=script) for script in ('rename_ragtag_scaffolds','classify_unplaced_contigs')] + cases
    (evidence / 'case-inventory.json').write_text(json.dumps(cases, indent=2)+'\n')
    results = []
    for case in cases:
        path = evidence / case['id']
        path.mkdir()
        (path / 'RUN.txt').write_text((evidence / 'RUN.txt').read_text())
        output = path / 'output.txt'
        output.write_text('PREEXISTING\n')
        before = {}
        if case['helper'] == 'self':
            cmd = [sys.executable, str(repo / ('bin/'+case['script']+'.py')), '--self-test']
        elif case['helper'] == 'rename':
            source = path / 'input.fasta'
            source.write_text(case['text'])
            before[source] = source.read_bytes()
            if case['alias']:
                output.unlink()
                if case['alias'] == 'same':
                    output = source
                elif case['alias'] == 'symlink':
                    output.symlink_to(source)
                else:
                    os.link(source, output)
            sample = 'S288C' if case['id'] == 'SOURCE-ORDER' else 'S'
            cmd = [sys.executable, str(repo / 'bin/rename_ragtag_scaffolds.py'), '--input', str(source), '--output', str(output), '--sample-id', sample]
            if case['pattern'] is not None:
                cmd += ['--chr-pattern='+case['pattern']]
        else:
            source, confidence = path / 'input.agp', path / 'confidence.txt'
            source.write_text(case['agp'])
            before[source] = source.read_bytes()
            if case['confidence'] is not None:
                confidence.write_text(case['confidence'])
                before[confidence] = confidence.read_bytes()
            cmd = [sys.executable, str(repo / 'bin/classify_unplaced_contigs.py'), '--agp', str(source), '--confidence', str(confidence), '--output', str(output)]
        original_output = output.read_bytes()
        (path / 'command.txt').write_text(shlex.join(cmd)+'\n')
        run = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
        (path / 'output.log').write_text(run.stdout)
        (path / 'exit-code.txt').write_text(str(run.returncode)+'\n')
        error = case.get('error')
        assert (run.returncode != 0) == bool(error), (case, run.stdout)
        for p, data in before.items():
            assert p.read_bytes() == data, p
        if error:
            assert error in run.stdout, (case, run.stdout)
            assert output.read_bytes() == original_output, case
        elif case['helper'] == 'rename':
            observed = records(output)
            assert [r[0] for r in observed] == case['expected'], (case, observed)
            assert [r[1] for r in observed] == [r[1] for r in records(source)], case
            (path / 'expected-ids.json').write_text(json.dumps(case['expected'])+'\n')
        elif case['helper'] == 'classify':
            assert output.read_text() == case['expected'], (case, output.read_text())
            (path / 'expected.tsv').write_text(case['expected'])
        (path / 'input-hashes.tsv').write_text(''.join(hashlib.sha256(v).hexdigest()+'\t'+str(p)+'\n' for p,v in before.items()))
        results.append(dict(case=case['id'], expected='rejection' if error else 'success', outcome='PASS'))
        (evidence / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(f'PASS: {len(cases)} helper CLI cases ({sum(bool(c.get("error")) for c in cases)} expected rejections); no collected test functions.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    checks(args.repo, args.evidence)

if __name__ == '__main__':
    main()
