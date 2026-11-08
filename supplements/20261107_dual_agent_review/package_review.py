"""Package only completed, validated review records and verify local copies."""
from pathlib import Path
import hashlib, json, shutil, zipfile

HERE = Path(__file__).resolve().parent
TASK = Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业')
BACKUP = TASK / '服务器备份/supplements/20261107_dual_agent_review'
DELIVER = TASK / '数据质量评测/双智能体审查_20261107'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    metrics = json.loads((HERE / 'review_metrics.json').read_text(encoding='utf-8'))
    sample = json.loads((HERE / 'sampling_manifest.json').read_text(encoding='utf-8'))
    assert metrics['human_review'] is False
    assert [metrics['counts'][k]['n'] for k in ['retained', 'excluded', 'repair', 'quarantine']] == [300, 100, 33, 16]
    assert sha(HERE / 'review_packet.jsonl') == sample['packet_sha256']
    assert sha(HERE / 'review_protocol.md') == sample['protocol_sha256']
    names = ['review_protocol.md', 'review_packet.jsonl', 'sampling_manifest.json', 'private_sampling_map.json',
             'prepare_review.py', 'aggregate_review.py', 'build_review_report.py', 'package_review.py',
             'reviewer_a.jsonl', 'reviewer_b.jsonl', 'reviewer_a_notes.md', 'reviewer_b_notes.md',
             'reviewer_a_supplement.jsonl', 'reviewer_b_supplement.jsonl',
             'reviewer_a_supplement_notes.md', 'reviewer_b_supplement_notes.md',
             'supplementary_dd_evidence.json', 'supplementary_agreement.json', 'coordinator_metadata_check.json',
             'initial_agreement.json', 'adjudication_queue.json', 'adjudication.jsonl', 'coordinator_spotcheck_ids.json',
             'final_labels.jsonl', 'review_metrics.json', 'review_labels.csv', 'retained_review_flags.json',
             '数据清洗双智能体审查结果.md']
    for name in sample['witness_hashes_verified']:
        source = HERE.parent / 'witnesses' / name
        assert sha(source) == sample['witness_hashes_verified'][name]
        target = HERE / 'witnesses' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(source, target)
        names.append('witnesses/' + name)
    for name in ['fetch_witnesses.py', 'build_repair_proposals.py']:
        target = HERE / 'method_evidence' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(HERE.parent / name, target)
        names.append('method_evidence/' + name)
    html_name = 'ernvyingxiongzhuan_039.html'
    source_html = HERE.parent / 'witnesses' / html_name
    dd = json.loads((HERE / 'supplementary_dd_evidence.json').read_text(encoding='utf-8'))
    assert sha(source_html) == dd['html_sha256']
    shutil.copyfile(source_html, HERE / 'witnesses' / html_name)
    names.append('witnesses/' + html_name)
    rows = []
    for name in names:
        p = HERE / name
        rows.append({'name': name, 'local_path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    previous = json.loads((HERE.parent / 'nature_revision_20261107/final_manifest.json').read_text(encoding='utf-8'))
    figures = []
    for row in previous['files']:
        if row['name'].endswith('.png'):
            assert sha(Path(row['local_path'])) == row['sha256']
            figures.append({'name': row['name'], 'sha256': row['sha256']})
    assert len(figures) == 2
    manifest = {'files': rows, 'preserved_figures': figures,
                'review_type': 'AI-assisted, not human gold', 'units': 449,
                'packet_sha256': sample['packet_sha256'], 'protocol_sha256': sample['protocol_sha256']}
    mp = HERE / 'artifact_manifest.json'
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    archive = HERE / '数据清洗双智能体审查_20261107.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name in names + ['artifact_manifest.json']:
            z.write(HERE / name, arcname=name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for row in rows:
            assert hashlib.sha256(z.read(row['name'])).hexdigest() == row['sha256']
    BACKUP.mkdir(parents=True, exist_ok=True)
    for name in names + ['artifact_manifest.json', archive.name]:
        target = BACKUP / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE / name, target)
        assert sha(target) == sha(HERE / name)
    DELIVER.mkdir(parents=True, exist_ok=True)
    for name in ['数据清洗双智能体审查结果.md', 'review_labels.csv', 'review_metrics.json', archive.name]:
        shutil.copyfile(HERE / name, DELIVER / name)
        assert sha(DELIVER / name) == sha(HERE / name)
    print(json.dumps({'artifact_files_verified': len(rows), 'zip_sha256': sha(archive),
                      'preserved_figures': len(figures), 'backup': str(BACKUP),
                      'delivery': str(DELIVER)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
