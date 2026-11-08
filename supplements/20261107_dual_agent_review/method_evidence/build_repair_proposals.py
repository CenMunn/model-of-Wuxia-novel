from pathlib import Path
import re,json,difflib,hashlib
HERE=Path(__file__).resolve().parent
RAW=Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业/数据导入/补充语料')
SERVER=Path('/home/xh/ww/nlp/shared/data/raw/supplementary/lfglib_20261106')
SAN_PATH=SERVER/'sanxiawuyi/original.txt' if SERVER.exists() else next(RAW.glob('三侠*.txt'))
ERN_PATH=SERVER/'ernvyingxiongzhuan/original.txt' if SERVER.exists() else next(RAW.glob('儿女*.txt'))
manifest=json.loads((HERE/'witnesses/manifest.json').read_text(encoding='utf-8'))
norm_table=str.maketrans({'著':'着','裡':'里','裏':'里','「':'“','」':'”','『':'‘','』':'’'})
def norm(s):return s.translate(norm_table)
def pua(c):return 0xe000<=ord(c)<=0xf8ff or 0xf0000<=ord(c)<=0xffffd or 0x100000<=ord(c)<=0x10fffd
repairs=[]; unresolved=[]
san=SAN_PATH.read_text(encoding='utf-8').splitlines()
for line,n in [(208,3),(305,6),(323,7),(386,10)]:
    raw=san[line-1];text=raw.strip();pars=(HERE/f'witnesses/sanxiawuyi_{n:03d}.txt').read_text(encoding='utf-8').split('\n\n')
    scored=sorted([(difflib.SequenceMatcher(None,norm(text),norm(p),autojunk=False).ratio(),p) for p in pars],reverse=True)
    witness=scored[0][1];m=difflib.SequenceMatcher(None,norm(text),norm(witness),autojunk=False)
    first=next(i for i,c in enumerate(text) if pua(c))
    anchors=[b for b in m.get_matching_blocks() if b.size>=20 and b.a+b.size<=first]
    anchor=max(anchors,key=lambda b:b.a+b.size); a=anchor.a+anchor.size;b=anchor.b+anchor.size
    assert first-a<12 and anchor.size>=25 and scored[0][0]-scored[1][0]>.15
    changed=text[:a]+witness[b:]
    assert not any(pua(c) for c in changed)
    source=next(x for x in manifest if x['book_id']=='sanxiawuyi' and x['chapter']==n)
    repairs.append({'book_id':'sanxiawuyi','line':line,'operation':'replace_corrupted_suffix_from_matched_chapter_paragraph',
        'before':raw,'after':changed,'local_suffix_start':a,'witness_suffix_start':b,'matching_anchor':text[anchor.a:a],
        'original_pua_occurrences':sum(map(pua,raw)),'source':source,'witness_paragraph':witness,
        'reason':'同回相同叙事段落，受损起点前有长锚点；保留可读前缀，仅从对照文本恢复严重乱码后缀。'})
# Only fill the explicitly marked missing tail; keep every existing readable character.
raw=san[1043];mark='（以下缺失）';assert raw.endswith(mark)
prefix=raw[:-len(mark)];anchor=prefix[-40:];w=(HERE/'witnesses/sanxiawuyi_045.txt').read_text(encoding='utf-8')
hits=[m.start() for m in re.finditer(re.escape(norm(anchor)),norm(w))];assert len(hits)==1
end=hits[0]+len(anchor);suffix=w[end:]
assert suffix.startswith('是个堆书籍之所') and suffix.rstrip().endswith('且听下回分解。')
repairs.append({'book_id':'sanxiawuyi','line':1044,'operation':'complete_explicitly_missing_chapter_tail',
 'before':raw,'after':prefix.strip()+suffix,'matching_anchor':anchor,'witness_suffix_start':end,
 'source':next(x for x in manifest if x['book_id']=='sanxiawuyi' and x['chapter']==45),
 'original_pua_occurrences':0,'inserted_characters':len(suffix),'reason':'缺文标记前40字符与同回对照文本唯一对应；补入该锚点之后至本回末的文本。'})
ern=ERN_PATH.read_text(encoding='utf-8').splitlines();chapter=0
for line,raw in enumerate(ern,1):
    match=re.match(r'^第([一二三四五六七八九十]+)回',raw.strip())
    if match and line>=90:
        d={'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9};v=match[1]
        chapter=(10 if v=='十' else d.get(v[0],1)*10+d.get(v[-1],0) if '十' in v else d[v])
    if not any(map(pua,raw)):continue
    witness=(HERE/f'witnesses/ernvyingxiongzhuan_{chapter:03d}.txt').read_text(encoding='utf-8')
    replacements=[]
    for pos,c in enumerate(raw):
        if not pua(c):continue
        candidates=[]
        for k in [20,16,12,8]:
            left=raw[max(0,pos-k):pos];right=raw[pos+1:pos+1+k]
            if len(left)<8 or len(right)<8 or any(pua(c) for c in left+right):continue
            pat=re.escape(norm(left))+r'([^\n]{1,4}?)'+re.escape(norm(right))
            matches=list(re.finditer(pat,norm(witness)))
            if len(matches)==1:
                a,b=matches[0].span(1);replacement=witness[a:b]
                if not any(map(pua,replacement)):candidates.append((k,replacement,left,right,a,b));break
        if candidates:replacements.append((pos,c,candidates[0]))
    positions={p for p,_,_ in replacements};allpos={i for i,c in enumerate(raw) if pua(c)}
    if positions!=allpos:
        unresolved.append({'book_id':'ernvyingxiongzhuan','line':line,'chapter':chapter,'unresolved_positions':sorted(allpos-positions),
                           'original_pua_occurrences':len(allpos),'text':raw,'action':'quarantine_entire_original_paragraph_without_joining_across_gap'})
        continue
    changed=raw
    for pos,c,cand in reversed(replacements):changed=changed[:pos]+cand[1]+changed[pos+1:]
    repairs.append({'book_id':'ernvyingxiongzhuan','line':line,'operation':'replace_pua_from_unique_bilateral_context_in_same_chapter',
        'before':raw,'after':changed.strip(),'original_pua_occurrences':len(allpos),
        'replacements':[{'offset':p,'before':c,'after':cand[1],'left_anchor':cand[2],'right_anchor':cand[3],
                         'witness_start':cand[4],'witness_end':cand[5]} for p,c,cand in replacements],
        'source':next(x for x in manifest if x['book_id']=='ernvyingxiongzhuan' and x['chapter']==chapter),
        'reason':'同回对照文本中左右各至少8字符唯一吻合，仅替换有据私用区字符，不全局应用映射。'})
result={'repairs':repairs,'quarantines':unresolved,'comparison_only_normalization':{'著':'着','裡':'里','裏':'里','「':'“','」':'”','『':'‘','』':'’'},
        'comparison_normalization_applied_to_training_text':False}
(HERE/'repairs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'repair_lines':len(repairs),'pua_restored':sum(x['original_pua_occurrences'] for x in repairs),
                  'quarantine_lines':len(unresolved),'pua_quarantined':sum(x['original_pua_occurrences'] for x in unresolved),
                  'missing_tail_characters':repairs[4]['inserted_characters'],
                  'unresolved_lines':[x['line'] for x in unresolved]},ensure_ascii=False))
