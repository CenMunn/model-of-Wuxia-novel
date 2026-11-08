"""Recompute descriptive corpus QC metrics without modifying the frozen corpus."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,re,argparse

HERE=Path(__file__).resolve().parent
SNAPSHOT=Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业/服务器备份/snapshots/20261107_preprocess_v1')
PROJECT=SNAPSHOT/'nlp'
VERSION=PROJECT/'shared/data/versions/corpus_v1_20261107'
OUT=Path("C:/Users/g'g/Documents/Codex/2026-11-06/lst-x4d-x20-x47-r-x55/outputs")
HAN=re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]')
def han(s):return len(HAN.findall(s))
def pua(c):
    n=ord(c);return 0xe000<=n<=0xf8ff or 0xf0000<=n<=0xffffd or 0x100000<=n<=0x10fffd
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):
    with p.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():yield json.loads(line)
def main():
    global SNAPSHOT,PROJECT,VERSION,OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--snapshot-root',default=str(SNAPSHOT))
    parser.add_argument('--manifest')
    parser.add_argument('--out',default=str(OUT))
    args=parser.parse_args()
    SNAPSHOT=Path(args.snapshot_root);PROJECT=SNAPSHOT/'nlp';VERSION=PROJECT/'shared/data/versions/corpus_v1_20261107';OUT=Path(args.out)
    OUT.mkdir(parents=True,exist_ok=True)
    index=json.loads(Path(args.manifest or SNAPSHOT/'snapshot_manifest.json').read_text(encoding='utf-8'))
    expected={r['relative_path']:r['sha256'] for r in index['files']}
    used=[]
    def check(path):
        key=path.relative_to(SNAPSHOT).as_posix();observed=digest(path)
        assert observed==expected[key],key
        used.append(dict(path=str(path),archive_relative_path=key,sha256=observed))
    for name in ['raw_manifest.json','statistics.json','verification.json','config.json',
        'clean/paragraphs.jsonl','records/line_classification.jsonl','records/repairs.jsonl','records/quarantine.jsonl',
        'vocab/char_all_training.json']:
        check(VERSION/name)
    raw_manifest=json.loads((VERSION/'raw_manifest.json').read_text(encoding='utf-8'))
    stat=json.loads((VERSION/'statistics.json').read_text(encoding='utf-8'))
    verification=json.loads((VERSION/'verification.json').read_text(encoding='utf-8'))
    raw_lines={};raw_han={};raw_pua=0
    for b in raw_manifest['books']:
        path=PROJECT/b['relative_path'];check(path);assert digest(path)==b['sha256']
        text=path.read_bytes().decode(b['encoding'],errors='strict')
        raw_lines[b['book_id']]=text.splitlines();raw_han[b['book_id']]=han(text)
        raw_pua+=sum(map(pua,text))
    archive=PROJECT/raw_manifest['archive']['relative_path'];check(archive)
    assert digest(archive)==raw_manifest['archive']['sha256']
    ps=list(rows(VERSION/'clean/paragraphs.jsonl'))
    clean_han=Counter();clean_chars=Counter();split_chars=Counter();unknown=0;unknown_den=0;clean_pua=0;replacement=0
    vocab=json.loads((VERSION/'vocab/char_all_training.json').read_text(encoding='utf-8'))
    vocab_chars=set(vocab['tokens'][4:])
    for p in ps:
        text=p['text'];clean_han[p['book_id']]+=han(text);clean_chars[p['book_id']]+=len(text);split_chars[p['split']]+=len(text)
        clean_pua+=sum(map(pua,text));replacement+=text.count('\ufffd')
        if p['split']=='validation':unknown+=sum(c not in vocab_chars for c in text);unknown_den+=len(text)
    assert sum(clean_han.values())==stat['story_han_characters']
    assert clean_chars.total()==stat['story_characters']
    assert unknown==verification['validation_unknown_char_occurrences']
    assert unknown/unknown_den==verification['validation_unknown_char_fraction']
    assert clean_pua==replacement==0
    repaired=list(rows(VERSION/'records/repairs.jsonl'));isolated=list(rows(VERSION/'records/quarantine.jsonl'))
    restored=sum(r['original_pua_occurrences'] for r in repaired);quarantined=sum(r['original_pua_occurrences'] for r in isolated)
    assert raw_pua==restored+quarantined==196
    classes=Counter()
    for r in rows(VERSION/'records/line_classification.jsonl'):
        classes[r['category']]+=han('\n'.join(raw_lines[r['book_id']][r['start_line']-1:r['end_line']]))
    assert classes.total()==sum(raw_han.values())
    books=[]
    for b in stat['books']:
        bid=b['book_id'];before=raw_han[bid];after=clean_han[bid]
        books.append(dict(book_id=bid,title=b['title'],source_group=b['source_group'],raw_han=before,
            clean_han=after,net_han_change=after-before,after_before_ratio=after/before,
            chapters=b['chapters'],validation_chapters=b['validation_chapters'],
            story_characters=b['characters'],validation_characters=b['validation_characters'],
            validation_character_fraction=b['validation_fraction']))
    before=sum(raw_han.values());after=sum(clean_han.values());total_samples=sum(stat['sample_counts'].values())
    separated=sum(n for k,n in classes.items() if k not in ['story','repaired_story','quarantine'])
    repaired_after=after-classes['story'];repair_delta=repaired_after-classes['repaired_story']
    assert before-separated-classes['quarantine']+repair_delta==after
    result=dict(version_id=stat['version_id'],date='2026-11-07',logical_books=17,raw_han=before,clean_han=after,
        net_han_change=after-before,after_before_han_ratio=after/before,raw_pua_occurrences=raw_pua,
        evidence_restored_pua=restored,quarantined_pua=quarantined,clean_pua_occurrences=clean_pua,
        clean_replacement_characters=replacement,known_pua_disposition_coverage=(restored+quarantined)/raw_pua,
        known_pua_evidence_restoration_fraction=restored/raw_pua,known_pua_quarantine_fraction=quarantined/raw_pua,
        quarantined_paragraphs=len(isolated),repair_records=len(repaired),repair_records_replayed=verification['repair_records_replayed_against_cached_source'],
        total_samples=total_samples,samples_verified=verification['samples_verified'],
        structural_sample_pass_fraction=verification['samples_verified']/total_samples,
        train_samples=stat['sample_counts']['train'],validation_samples=stat['sample_counts']['validation'],
        samples_by_source=stat['sample_counts_by_source'],chapters=stat['chapters'],paragraphs=stat['paragraphs'],
        train_chapters=stat['chapter_split_counts']['train'],validation_chapters=stat['chapter_split_counts']['validation'],
        split_story_characters=dict(split_chars),validation_character_fraction=split_chars['validation']/split_chars.total(),
        vocabulary_size=len(vocab['tokens']),validation_unknown_characters=unknown,validation_character_denominator=unknown_den,
        validation_vocabulary_coverage=1-unknown/unknown_den,
        cross_chapter_samples=verification['cross_chapter_samples'],cross_gap_samples=verification['cross_gap_samples'],
        cross_split_exact_substrings_at_least_128=verification['cross_split_exact_substrings_at_least_128_nonwhitespace_characters'],
        scene_boundaries=stat['scene_breaks_preserved'],raw_han_by_classification=dict(classes),
        separated_nonstory_and_heading_han=separated,quarantined_original_han=classes['quarantine'],
        repaired_block_han_before=classes['repaired_story'],repaired_block_han_after=repaired_after,repair_net_han_change=repair_delta,
        books=books,source_files_rehashed=used,corpus_modified=False,training_started=False,
        limitations=['没有全文逐字金标准，不能计算总体清洗准确率/错字纠正准确率/F1',
            '规模变化含非正文分离和有据补入，不等于逐字保留率或准确率',
            '重复检查限于记录的算法和阈值，不是穷尽语义去重',
            '验证词表覆盖率是字符可表示性，不是模型准确率',
            '样本结构通过率仅覆盖已实现的结构/来源/连续性检查'])
    (HERE/'figure_data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'预处理量化指标_20261107.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'预处理各书统计_20261107.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(books[0]));w.writeheader();w.writerows(books)
    print(json.dumps({k:result[k] for k in ['raw_han','clean_han','net_han_change','after_before_han_ratio',
        'raw_pua_occurrences','evidence_restored_pua','quarantined_pua','total_samples',
        'validation_character_denominator','validation_vocabulary_coverage']},ensure_ascii=False))
    print('CLASSIFICATION',json.dumps(classes,ensure_ascii=False))
    print('BOOKS',json.dumps(books,ensure_ascii=False))

if __name__=='__main__':main()
