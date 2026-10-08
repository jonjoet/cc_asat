#!/usr/bin/env python3
"""List raw AGP W query IDs absent from same-task RagTag scaffold confidence.

RagTag 2.1.0 with -u and no -C emits confidence rows for final placed queries.
Neither object names nor reference names determine placement. Inputs are read-only.
"""
import argparse
import math
import sys

CONFIDENCE_HEADER = 'query\tgrouping_confidence\tlocation_confidence\torientation_confidence'
TSV_HEADER = 'contig_id\tobject_name\tlength_bp\n'


def parse_agp(lines):
    """Validate relevant W/N/U rows; retain W rows in file order."""
    components = []
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        fields = line.rstrip('\r\n').split('\t')
        if len(fields) < 5:
            raise ValueError(f'malformed AGP row {number}: fewer than five fields')
        if fields[4] not in ('W', 'N', 'U'):
            continue
        try:
            if len(fields) != 9 or not fields[0]:
                raise ValueError('expected nine fields and nonempty object ID')
            start, end, part = map(int, fields[1:4])
            if start < 1 or end < start or part < 1:
                raise ValueError('invalid object coordinates or part number')
            if fields[4] == 'W':
                cs, ce = map(int, fields[6:8])
                if not fields[5] or cs < 1 or ce < cs or ce - cs != end - start:
                    raise ValueError('invalid component ID or coordinates')
                if fields[8] not in ('+', '-', '?', '0', 'na'):
                    raise ValueError('invalid W orientation')
                components.append((fields[5], fields[0], end - start + 1))
            else:
                if int(fields[5]) != end - start + 1 or not fields[6] or fields[7] not in ('yes', 'no') or not fields[8]:
                    raise ValueError('invalid gap length/type/linkage/evidence')
        except ValueError as error:
            raise ValueError(f'malformed AGP row {number}: {error}') from error
    return components


def parse_confidence(lines, components):
    iterator = iter(lines)
    if next(iterator, '').rstrip('\r\n') != CONFIDENCE_HEADER:
        raise ValueError('malformed confidence: missing or incorrect header')
    queries = set()
    available = {row[0] for row in components}
    for number, line in enumerate(iterator, 2):
        if not line.strip():
            continue
        fields = line.rstrip('\r\n').split('\t')
        if len(fields) != 4:
            raise ValueError(f'malformed confidence row {number}: expected four fields')
        query = fields[0]
        if not query or query in queries:
            raise ValueError(f'malformed confidence row {number}: empty or duplicate query ID {query!r}')
        try:
            if not all(math.isfinite(float(score)) for score in fields[1:]):
                raise ValueError('nonfinite score')
        except ValueError as error:
            raise ValueError(f'malformed confidence row {number}: nonnumeric or nonfinite score') from error
        if query not in available:
            raise ValueError(f'inconsistent confidence query {query!r}: absent from AGP W components')
        queries.add(query)
    return queries


def classify(components, placed):
    return [row for row in components if row[0] not in placed]


def _self_test():
    same = parse_agp(['chr1_RagTag\t1\t10\t1\tW\tchr1\t1\t10\t+\n'])
    assert classify(same, {'chr1'}) == []
    assert classify(same, set()) == [('chr1', 'chr1_RagTag', 10)]
    assert classify([], parse_confidence([CONFIDENCE_HEADER + '\n'], [])) == []
    assert classify(same, parse_confidence([CONFIDENCE_HEADER + '\n'], same)) == same


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agp')
    parser.add_argument('--confidence', help='Mandatory confidence from the same successful scaffold task')
    parser.add_argument('--output')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        print('classify_unplaced_contigs self-test passed', file=sys.stderr)
        return
    if not (args.agp and args.confidence and args.output):
        parser.error('--agp, --confidence and --output are required unless --self-test is given')
    try:
        with open(args.agp) as handle:
            components = parse_agp(handle)
        try:
            with open(args.confidence) as handle:
                placed = parse_confidence(handle, components)
        except OSError as error:
            raise ValueError(f'missing/unreadable confidence: {error}') from error
        unplaced = classify(components, placed)
        with open(args.output, 'w') as handle:
            handle.write(TSV_HEADER)
            for query, obj, length in unplaced:
                handle.write(f'{query}\t{obj}\t{length}\n')
    except (ValueError, OSError) as error:
        parser.exit(1, f'ERROR: {error}\n')
    print(f'{len(unplaced)} unplaced contig(s) written to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
