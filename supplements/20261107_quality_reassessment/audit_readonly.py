"""Read-only checks of the frozen, backed-up continuation corpus.

Produces audit records outside the corpus; does not train or alter figures.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re
import argparse
import numpy as np

HERE = Path(__file__).resolve().parent
SNAP = Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业/服务器备份/snapshots/20261107_preprocess_v1')
DATA = SNAP / 'nlp/shared/data/versions/corpus_v1_20261107'

def rows(path):
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def han(text):
    return sum('\u4e00' <= c <= '\u9fff' for c in text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, default=SNAP / 'nlp')
    parser.add_argument('--manifest', type=Path, default=SNAP / 'snapshot_manifest.json')
    parser.add_argument('--output', type=Path, default=HERE)
    args = parser.parse_args()
    project = args.project_root
    DATA = project / 'shared/data/versions/corpus_v1_20261107'
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    expected = {r['relative_path']: r['sha256'] for r in manifest['files']}
    names = ['config.json', 'statistics.json', 'verification.json', 'raw_manifest.json',
             'clean/paragraphs.jsonl', 'clean/chapters.jsonl', 'clean/segments.jsonl',
             'records/excluded_blocks.jsonl', 'records/repairs.jsonl', 'records/quarantine.jsonl',
             'records/boundaries.jsonl', 'vocab/char_all_training.json', 'vocab/char_jinyong_training.json',
             'samples/train.jsonl', 'samples/validation.jsonl', 'samples/train_jinyong.jsonl',
             'samples/validation_jinyong.jsonl']
    checked = []
    for name in names:
        p = DATA / name
        digest = sha(p)
        relative = 'nlp/' + p.relative_to(project).as_posix()
        assert digest == expected[relative], name
        checked.append({'relative_path': relative, 'sha256': digest})
    config = json.loads((DATA / 'config.json').read_text(encoding='utf-8'))
    ps = rows(DATA / 'clean/paragraphs.jsonl')
    cs = rows(DATA / 'clean/chapters.jsonl')
    pm = {p['paragraph_id']: p for p in ps}
    cm = {c['chapter_id']: c for c in cs}
    raw = {}
    book_specs = {b['book_id']: b for b in config['books']}
    for b in config['books']:
        p = project / b['relative_path']
        assert sha(p) == b['sha256'], str(p)
        checked.append({'relative_path': 'nlp/' + p.relative_to(project).as_posix(), 'sha256': b['sha256']})
        raw[b['book_id']] = p.read_bytes().decode(b['encoding'], errors='strict').splitlines()
    repairs = rows(DATA / 'records/repairs.jsonl')
    rm = {r['repair_id']: r for r in repairs}
    original_match = repaired_match = 0
    for p in ps:
        if p['text_origin'] == 'original':
            text = raw[p['book_id']][p['original_line_start'] - 1]
            assert text[p['original_char_start']:p['original_char_end']] == p['text']
            original_match += 1
        else:
            assert p['text'] in [t.strip(' \t\u3000\r\n') for t in rm[p['repair_id']]['after'].split('\n\n')]
            repaired_match += 1
    vocabs = {}
    for name in ['all', 'jinyong']:
        v = json.loads((DATA / f'vocab/char_{name}_training.json').read_text(encoding='utf-8'))
        vocabs[name] = set(v['tokens'][4:])
        chars = {c for p in ps if p['split'] == 'train' and (name == 'all' or p['source_group'] == 'jinyong') for c in p['text']} | {'\n'}
        assert chars == vocabs[name]
    failures = Counter()
    sample_stats = {}
    used, targets = defaultdict(set), defaultdict(set)
    clean_chars = defaultdict(Counter)
    target_chars = defaultdict(Counter)
    normalized = defaultdict(Counter)
    sample_previews = {}
    required = ['sample_id', 'book_id', 'chapter_id', 'segment_id', 'scene_id', 'split', 'source_group',
                'source_paragraph_ids', 'target_paragraph_ids', 'source', 'target']
    total = complete = 0
    for p in ps:
        clean_chars[p['source_group'], p['split']].update(p['text'])
    for split in ['train', 'validation']:
        ss = rows(DATA / f'samples/{split}.jsonl')
        groups = defaultdict(list)
        for s in ss:
            total += 1
            complete += all(k in s and s[k] is not None and (len(s[k]) > 0 if isinstance(s[k], (str, list)) else True) for k in required)
            pars = [pm[i] for i in s['source_paragraph_ids'] + s['target_paragraph_ids']]
            for field in ['book_id', 'chapter_id', 'segment_id', 'scene_id']:
                failures['cross_' + field] += len({p[field] for p in pars}) != 1 or {p[field] for p in pars} != {s[field]}
            failures['split_mismatch'] += {p['split'] for p in pars} != {split}
            orders = [p['order'] for p in pars]
            failures['discontinuity'] += orders != list(range(orders[0], orders[-1] + 1))
            for side in ['source', 'target']:
                failures[side + '_reconstruction'] += s[side] != '\n\n'.join(pm[i]['text'] for i in s[side + '_paragraph_ids'])
                failures[side + '_length'] += not config['samples']['min_' + side + '_chars'] <= len(s[side]) <= config['samples']['max_' + side + '_chars']
            key = (s['source_group'], split)
            used[key].update(p['paragraph_id'] for p in pars)
            targets[key].update(s['target_paragraph_ids'])
            target_chars[key].update(s['target'])
            groups[s['source_group']].append(s)
            normalized[split][hashlib.sha256((re.sub(r'\s+', '', s['source']) + '\x00' + re.sub(r'\s+', '', s['target'])).encode()).hexdigest()] += 1
            rank = hashlib.sha256(('reassessment-20261107:' + s['sample_id']).encode()).hexdigest()
            if split == 'train' and (s['book_id'] not in sample_previews or rank < sample_previews[s['book_id']][0]):
                sample_previews[s['book_id']] = (rank, s)
        for group, values in groups.items():
            sample_stats[group + '_' + split] = {'n': len(values)}
            for side in ['source', 'target']:
                a = np.asarray([len(s[side]) for s in values])
                q1, med, q3 = np.quantile(a, [.25, .5, .75])
                sample_stats[group + '_' + split][side] = {'min': int(a.min()), 'q25': float(q1), 'median': float(med), 'q75': float(q3), 'max': int(a.max())}
    coverage = {}
    unknowns = {}
    for group, split in sorted(clean_chars):
        key = (group, split)
        pop = [p for p in ps if (p['source_group'], p['split']) == key]
        denominator = sum(len(p['text']) for p in pop)
        coverage[group + '_' + split] = {
            'paragraphs': len(pop), 'body_characters': denominator,
            'used_paragraphs': len(used[key]), 'used_characters': sum(len(pm[i]['text']) for i in used[key]),
            'used_character_fraction': sum(len(pm[i]['text']) for i in used[key]) / denominator,
            'target_character_fraction': sum(len(pm[i]['text']) for i in targets[key]) / denominator}
        if split == 'validation':
            unknowns[group] = {}
            for name, vocab in vocabs.items():
                unknowns[group][name] = {}
                for unit, counts in [('unique_body', clean_chars[key]), ('sample_target', target_chars[key])]:
                    missing = sum(n for c, n in counts.items() if c not in vocab)
                    n = sum(counts.values())
                    unknowns[group][name][unit] = {'unknown_occurrences': missing, 'characters': n, 'coverage': 1 - missing / n}
    exclusions = rows(DATA / 'records/excluded_blocks.jsonl')
    major = {}
    for bid in ['jy_yuenv', 'jy_bixue']:
        b = book_specs[bid]
        body = [p for p in ps if p['book_id'] == bid]
        erows = []
        for ex in exclusions:
            if ex['book_id'] != bid:
                continue
            text = ex['original_text']
            assert text == '\n'.join(raw[bid][ex['original_line_start'] - 1:ex['original_line_end']])
            erows.append({'category': ex['category'], 'start_line': ex['original_line_start'], 'end_line': ex['original_line_end'],
                          'han': han(text), 'start_excerpt': text.strip()[:90], 'end_excerpt': text.strip()[-90:]})
        major[bid] = {'title': b['title'], 'raw_han_bmp': han('\n'.join(raw[bid])), 'clean_han_bmp': sum(han(p['text']) for p in body),
                      'body_start_line': b['body_start'], 'body_end_line': b['body_end'],
                      'raw_after_body': raw[bid][b['body_end']:b['body_end'] + 7], 'exclusions': erows}
    preview = []
    for bid, (_, s) in sorted(sample_previews.items()):
        preview.append({'book_id': bid, 'sample_id': s['sample_id'], 'source_end': s['source'][-140:], 'target_start': s['target'][:180]})
    result = {
        'version_id': config['version_id'], 'basis': 'read-only inspection of hash-matched server snapshot',
        'source_files_rehashed': checked, 'samples': total, 'complete_samples': complete,
        'sample_failures': dict(failures), 'paragraphs_replayed_from_original': original_match,
        'paragraphs_replayed_from_recorded_repairs': repaired_match,
        'whitespace_normalized_repeated_pairs': sum(sum(n - 1 for n in counts.values()) for counts in normalized.values()),
        'whitespace_normalized_pairs_cross_split': len(normalized['train'].keys() & normalized['validation'].keys()),
        'sample_length_profiles': sample_stats, 'sample_body_coverage': coverage, 'validation_vocabulary_coverage': unknowns,
        'major_reduction_audit': major,
        'validation_chapters_by_book': {b['title']: sum(c['split'] == 'validation' for c in cs if c['book_id'] == b['book_id']) for b in config['books']},
        'human_labelled_gold_available': False, 'semantic_cleaning_accuracy': None,
        'model_training_performed': False, 'original_figures_modified': False,
        'references': ['https://blog.csdn.net/universsky2015/article/details/137296952',
                       'https://blog.csdn.net/ayiya_Oese/article/details/147810050',
                       'https://aclanthology.org/2022.acl-long.577/',
                       'https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework']}
    (output / 'audit_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'sample_boundary_spotchecks.json').write_text(json.dumps(preview, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    assert total == complete == 72690
    assert not any(failures.values())
    print(json.dumps({k: v for k, v in result.items() if k not in ['source_files_rehashed', 'references', 'major_reduction_audit']}, ensure_ascii=False))
    print('EXCLUSIONS ' + json.dumps(major, ensure_ascii=False))

if __name__ == '__main__':
    main()
