"""Read-only sample profiling for an evidence-backed plotting revision."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
import numpy as np

HERE=Path(__file__).resolve().parent
SNAP=Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业/服务器备份/snapshots/20261107_preprocess_v1')
DATA=SNAP/'nlp/shared/data/versions/corpus_v1_20261107'
BASE=HERE.parent/'figures_20261107/figure_data.json'

def main():
    data=json.loads(BASE.read_text(encoding='utf-8'))
    manifest=json.loads((SNAP/'snapshot_manifest.json').read_text(encoding='utf-8'))
    expected={r['relative_path']:r['sha256'] for r in manifest['files']}
    required=['sample_id','book_id','chapter_id','segment_id','scene_id','split','source_group',
        'source_paragraph_ids','target_paragraph_ids','source','target']
    n=complete=consistent=0;ids=set();pairs=Counter();pair_splits=defaultdict(set);source_hashes=[];distributions={}
    for split in ['train','validation']:
        path=DATA/f'samples/{split}.jsonl'
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==expected[path.relative_to(SNAP).as_posix()]
        source_hashes.append(dict(relative_path=path.relative_to(SNAP).as_posix(),sha256=digest))
        with path.open(encoding='utf-8') as f:
            for line in f:
                s=json.loads(line);n+=1
                complete+=all(k in s and s[k] is not None and (len(s[k])>0 if isinstance(s[k],(str,list)) else True) for k in required)
                lists=['source_paragraph_ids','target_paragraph_ids']
                types=all(isinstance(s.get(k),str) for k in required if k not in lists)
                types &= all(isinstance(s.get(k),list) and all(isinstance(x,str) for x in s[k]) for k in lists)
                types &= s.get('split')==split and s.get('source_group') in ['jinyong','supplementary']
                consistent+=types;ids.add(s['sample_id'])
                key=hashlib.sha256(s['source'].encode()+b'\x00'+s['target'].encode()).hexdigest()
                pairs[key]+=1;pair_splits[key].add(split)
                group=split+'_'+s['source_group']
                d=distributions.setdefault(group,dict(source=[],target=[]))
                d['source'].append(len(s['source']));d['target'].append(len(s['target']))
    assert n==data['total_samples']==72690
    profile={}
    for group,v in distributions.items():
        profile[group]={}
        for side,values in v.items():
            a=np.asarray(values,dtype=np.int64);q=np.quantile(a,[0,.25,.5,.75,1])
            iqr=q[3]-q[1];flags=int(np.sum((a<q[1]-1.5*iqr)|(a>q[3]+1.5*iqr)))
            profile[group][side]=dict(n=len(a),minimum=int(a.min()),q25=float(q[1]),median=float(q[2]),q75=float(q[3]),
                maximum=int(a.max()),mean=float(a.mean()),population_std=float(a.std()),iqr_flag_count=flags)
    result=dict(base_metrics=data,samples=n,required_fields=required,required_field_count=len(required),
        complete_samples=int(complete),sample_field_completeness=complete/n,
        consistent_type_samples=int(consistent),field_type_consistency=consistent/n,
        unique_sample_ids=len(ids),sample_id_uniqueness=len(ids)/n,unique_text_pairs=len(pairs),exact_text_pair_uniqueness=len(pairs)/n,
        repeated_pair_occurrences=sum(c-1 for c in pairs.values()),cross_split_exact_text_pairs=sum(len(v)>1 for v in pair_splits.values()),
        semantic_text_accuracy=None,semantic_accuracy_status='not_human_labelled',
        distributions=distributions,profile=profile,extra_source_hashes=source_hashes,
        input_data_modified=False,model_training_started=False,
        references=[
            {'url':'https://blog.csdn.net/universsky2015/article/details/137296952','use':'context-dependent quality dimensions; no unsupported accuracy/F1'},
            {'url':'https://blog.csdn.net/ayiya_Oese/article/details/147810050','use':'missingness, exact duplication, type consistency and descriptive length profiling'},
            {'url':'https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework','use':'primary-source check of operational completeness, consistency, uniqueness, validity and accuracy distinctions'}],
        adaptations=['Do not impute missing novel text using numeric means, modes, or a model.',
            'IQR flags are descriptive length flags, never proof of corrupt prose and never automatic exclusions.',
            'Overlapping continuation windows are dependent; no KS p-values or inferential confidence intervals.',
            'No timeliness score is imposed on a fixed classical-literature corpus.',
            'No composite score or semantic accuracy is inferred from structural rule passes.'])
    (HERE/'quality_profile.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['samples','complete_samples','consistent_type_samples','unique_sample_ids','unique_text_pairs',
        'repeated_pair_occurrences','cross_split_exact_text_pairs','semantic_text_accuracy']},ensure_ascii=False))
    print(json.dumps(profile,ensure_ascii=False))

if __name__=='__main__':main()
