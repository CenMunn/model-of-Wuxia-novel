"""Validate actual reviewer records and aggregate AI-assisted, unit-specific labels."""
from pathlib import Path, PureWindowsPath
from collections import Counter
import argparse, csv, hashlib, json, os

HERE = Path(__file__).resolve().parent
DEFAULT_WITNESSES = HERE.parent / 'witnesses'
if not DEFAULT_WITNESSES.exists():
    DEFAULT_WITNESSES = HERE / 'witnesses'
WITNESS_ROOT = Path(os.environ.get('NLP_REVIEW_WITNESSES', str(DEFAULT_WITNESSES)))
LABELS = {
    'retained': {'KEEP', 'REMOVE', 'UNCERTAIN'},
    'excluded': {'EXCLUDE', 'RESTORE', 'UNCERTAIN'},
    'repair': {'SUPPORTED', 'UNSUPPORTED', 'UNCERTAIN'},
    'quarantine': {'JUSTIFIED', 'OVERCONSERVATIVE', 'UNCERTAIN'},
}
POSITIVE = {'retained': 'KEEP', 'excluded': 'EXCLUDE', 'repair': 'SUPPORTED', 'quarantine': 'JUSTIFIED'}
BAD = {'retained': 'REMOVE', 'excluded': 'RESTORE', 'repair': 'UNSUPPORTED', 'quarantine': 'OVERCONSERVATIVE'}

def rows(path):
    with path.open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]

def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from strings(value)

def content_strings(record):
    keys = ['text', 'before', 'after', 'evidence', 'context_before', 'context_after', 'source_section_opening', 'supplementary_reference']
    for key in keys:
        yield from strings(record.get(key))
    if record.get('reference_file'):
        reference = Path(record['reference_file'])
        if not reference.exists():
            reference = WITNESS_ROOT / PureWindowsPath(record['reference_file']).name
        yield reference.read_text(encoding='utf-8')

def load_review(path, packet, complete=True):
    records = rows(path)
    ids = [r['id'] for r in records]
    assert len(ids) == len(set(ids)), f'Duplicate IDs in {path.name}'
    assert set(ids) <= packet.keys(), f'Unknown IDs in {path.name}'
    if complete:
        assert set(ids) == packet.keys(), f'Missing IDs in {path.name}: {sorted(packet.keys() - set(ids))}'
    for r in records:
        item = packet[r['id']]
        assert r['kind'] == item['kind'], r['id']
        assert r['label'] in LABELS[r['kind']], r['id']
        assert r['confidence'] in ['high', 'medium', 'low'], r['id']
        quote = r['evidence_quote']
        assert len(quote) >= 1 and any(quote in s for s in content_strings(item)), f'Non-verbatim quote {path.name}: {r["id"]}: {quote}'
        assert sum('\u4e00' <= c <= '\u9fff' for c in r['reason']) >= 12, f'Short reason {path.name}: {r["id"]}'
        assert isinstance(r['flags'], list), r['id']
    return {r['id']: r for r in records}

def agreement(a, b):
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[label] * cb[label] for label in ca.keys() | cb.keys()) / n ** 2
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    return {'n': n, 'agree': sum(x == y for x, y in zip(a, b)), 'raw_agreement': observed,
            'cohen_kappa': kappa, 'kappa_note': 'undefined when expected agreement is one' if kappa is None else '',
            'reviewer_a_labels': dict(ca), 'reviewer_b_labels': dict(cb),
            'confusion': [{'a': x, 'b': y, 'n': count} for (x, y), count in Counter(zip(a, b)).items()]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--progress', action='store_true')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--final', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'sampling_manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((HERE / 'review_packet.jsonl').read_bytes()).hexdigest() == manifest['packet_sha256']
    assert hashlib.sha256((HERE / 'review_protocol.md').read_bytes()).hexdigest() == manifest['protocol_sha256']
    packet_rows = rows(HERE / 'review_packet.jsonl')
    packet = {r['id']: r for r in packet_rows}
    assert len(packet) == len(packet_rows) == 449
    if args.progress:
        out = {}
        for name in ['a', 'b']:
            p = HERE / f'reviewer_{name}.jsonl'
            if p.exists():
                rs = rows(p)
                out[name] = {'written': len(rs), 'unique_ids': len({r['id'] for r in rs}), 'kinds': dict(Counter(r['kind'] for r in rs))}
            else:
                out[name] = {'written': 0}
        print(json.dumps(out, ensure_ascii=False))
        return
    a = load_review(HERE / 'reviewer_a.jsonl', packet)
    b = load_review(HERE / 'reviewer_b.jsonl', packet)
    supplement = None
    supplement_path = HERE / 'supplementary_dd_evidence.json'
    if supplement_path.exists():
        new_evidence = json.loads(supplement_path.read_text(encoding='utf-8'))
        html_path = Path(new_evidence['html_file'])
        if not html_path.exists():
            html_path = WITNESS_ROOT / PureWindowsPath(new_evidence['html_file']).name
        assert hashlib.sha256(html_path.read_bytes()).hexdigest() == new_evidence['html_sha256']
        extended = {r['id']: {**packet[r['id']], 'supplementary_reference': r['reference_dd_text']} for r in new_evidence['items']}
        sa = load_review(HERE / 'reviewer_a_supplement.jsonl', extended)
        sb = load_review(HERE / 'reviewer_b_supplement.jsonl', extended)
        ids = list(extended)
        supplement = {'stage': 'additional evidence after initial 449 labels were completed',
                      'n': len(ids), 'ids': ids,
                      'agreement': agreement([sa[i]['label'] for i in ids], [sb[i]['label'] for i in ids]),
                      'disagreement_ids': [i for i in ids if sa[i]['label'] != sb[i]['label']],
                      'html_sha256': new_evidence['html_sha256'],
                      'initial_labels_preserved': True}
        (HERE / 'supplementary_agreement.json').write_text(json.dumps(supplement, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    agree = {}
    required = []
    extra_path = HERE / 'coordinator_spotcheck_ids.json'
    extra_checks = json.loads(extra_path.read_text(encoding='utf-8')) if extra_path.exists() else []
    extra = {r['id']: r['reason'] for r in extra_checks}
    assert len(extra) == len(extra_checks) and set(extra) <= packet.keys()
    for kind in LABELS:
        ids = [r['id'] for r in packet_rows if r['kind'] == kind]
        agree[kind] = agreement([a[i]['label'] for i in ids], [b[i]['label'] for i in ids])
    for item in packet_rows:
        i = item['id']; reasons = []
        if a[i]['label'] != b[i]['label']:
            reasons.append('reviewer_disagreement')
        if 'UNCERTAIN' in [a[i]['label'], b[i]['label']]:
            reasons.append('uncertain_label')
        if BAD[item['kind']] in [a[i]['label'], b[i]['label']]:
            reasons.append('potential_defect')
        if 'low' in [a[i]['confidence'], b[i]['confidence']]:
            reasons.append('low_confidence')
        if i in extra:
            reasons.append('coordinator_high_risk_check: ' + extra[i])
        if reasons:
            required.append({'id': i, 'triggers': reasons, 'reviewer_a': a[i], 'reviewer_b': b[i], 'material': item})
    (HERE / 'adjudication_queue.json').write_text(json.dumps(required, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    initial = {'review_type': 'two separately prompted AI reviewers', 'human_gold': False,
               'by_kind': agree, 'overall_raw_agreement': sum(a[i]['label'] == b[i]['label'] for i in packet) / len(packet),
               'disagreement_ids': [i for i in packet if a[i]['label'] != b[i]['label']],
               'coordinator_high_risk_ids': list(extra),
               'adjudication_required_ids': [r['id'] for r in required],
               'packet_sha256': manifest['packet_sha256']}
    (HERE / 'initial_agreement.json').write_text(json.dumps(initial, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not args.final:
        print(json.dumps(initial, ensure_ascii=False))
        return
    adjudicated = rows(HERE / 'adjudication.jsonl')
    ad = {r['id']: r for r in adjudicated}
    assert len(ad) == len(adjudicated)
    assert set(ad) == {r['id'] for r in required}, 'Missing or extra adjudication IDs'
    final = []
    for item in packet_rows:
        i = item['id']; kind = item['kind']
        if i in ad:
            decision = ad[i]
            assert decision['final_label'] in LABELS[kind]
            assert len(decision['reason']) >= 12
            label, reason = decision['final_label'], decision['reason']
            origin = 'coordinator_adjudication'
        else:
            label, reason = a[i]['label'], '两位审查者同标签，保留各自逐项依据；一致并不构成人工真值。'
            origin = 'reviewer_agreement'
        reviewer_flags = sorted(set(a[i]['flags']) | set(b[i]['flags']))
        dismissed = ad.get(i, {}).get('dismissed_flags', [])
        added = ad.get(i, {}).get('added_flags', [])
        assert set(dismissed) <= set(reviewer_flags), i
        final.append({'id': i, 'kind': kind, 'book': item['book'], 'raw_line': item.get('raw_line'),
                      'reviewer_a_label': a[i]['label'], 'reviewer_b_label': b[i]['label'],
                      'final_label': label, 'decision_origin': origin, 'reason': reason,
                      'reviewer_flags': reviewer_flags, 'dismissed_flags': dismissed, 'added_flags': added,
                      'flags': sorted((set(reviewer_flags) - set(dismissed)) | set(added))})
    summary = {}
    for kind in LABELS:
        rs = [r for r in final if r['kind'] == kind]
        counts = Counter(r['final_label'] for r in rs)
        n = len(rs); uncertain = counts['UNCERTAIN']; bad = counts[BAD[kind]]; good = counts[POSITIVE[kind]]
        numerator = bad if kind in ['retained', 'excluded'] else good
        summary[kind] = {'n': n, 'labels': dict(counts), 'reported_numerator': numerator,
                         'observed_ai_label_rate': numerator / n, 'uncertain': uncertain,
                         'uncertainty_count_range': [numerator / n, (numerator + uncertain) / n],
                         'range_is_not_confidence_interval': True}
    metrics = {'review_type': 'AI-assisted dual review plus coordinator adjudication',
               'version': manifest['version'], 'human_review': False, 'human_gold_accuracy_available': False,
               'counts': summary, 'initial_agreement': initial,
               'supplementary_review': supplement,
               'unresolved_ids': [r['id'] for r in final if r['final_label'] == 'UNCERTAIN'],
               'potential_defect_ids': [r['id'] for r in final if r['final_label'] == BAD[r['kind']]],
               'recoverable_quarantine_ids': [r['id'] for r in final if r['kind'] == 'quarantine' and r['final_label'] == 'OVERCONSERVATIVE'],
               'flag_counts': dict(Counter(flag for r in final for flag in r['flags'])),
               'packet_sha256': manifest['packet_sha256'], 'protocol_sha256': manifest['protocol_sha256'],
               'no_corpus_edits': True, 'no_training': True,
               'limits': ['AI label rates do not measure externally verified human-gold accuracy.',
                          'Separate contexts from the same model can retain correlated systematic errors.',
                          'Excluded sampling covers 2244 nonempty source lines within exclusion records, not all removed characters.',
                          'Retained, excluded, repair and quarantine use different units; no pooled accuracy or F1 is reported.',
                          'Cached witness support does not establish agreement with the printed edition.']}
    (HERE / 'review_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (HERE / 'final_labels.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in final), encoding='utf-8')
    with (HERE / 'review_labels.csv').open('w', encoding='utf-8-sig', newline='') as f:
        fields = list(final[0])
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in final:
            writer.writerow({**row, **{k: ';'.join(row[k]) for k in ['flags', 'reviewer_flags', 'dismissed_flags', 'added_flags']}})
    print(json.dumps(metrics, ensure_ascii=False))

if __name__ == '__main__':
    main()
