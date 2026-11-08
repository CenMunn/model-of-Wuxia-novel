"""Verify the final chart and retain reproducible local copies."""
from pathlib import Path
from PIL import Image
import hashlib, json, shutil, zipfile

HERE = Path(__file__).resolve().parent
STEM = '双智能体复核新增指标_Nature版_20261107'
TASK = Path('D:/大三上课程/自然语言处理/作业/武侠小说生成作业')
DELIVER = TASK/'数据质量评测/双智能体审查_20261107'
BACKUP = TASK/'服务器备份/supplements/20261107_dual_review_figure'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    alignment = json.loads((HERE/(STEM+'.alignment.json')).read_text(encoding='utf-8'))
    assert alignment['verdict'] == 'PASS'
    collision = json.loads((HERE/'collision_audit.json').read_text(encoding='utf-8'))
    assert collision['verdict'] == 'PASS'
    font = json.loads((HERE/'pdf_text_audit.json').read_text(encoding='utf-8'))
    assert font['minimum_found_pt'] >= 5 and font['below_minimum_count'] == 0
    with Image.open(HERE/(STEM+'.png')) as im:
        assert im.size == (5400,3900)
        assert min(im.info['dpi']) >= 599
    old = json.loads((HERE.parent/'nature_revision_20261107/final_manifest.json').read_text(encoding='utf-8'))
    preserved = []
    for row in old['files']:
        if row['name'].endswith('.png'):
            assert sha(Path(row['local_path'])) == row['sha256']
            preserved.append({'name':row['name'], 'sha256':row['sha256']})
    assert len(preserved) == 2
    names = ['figure_contract.md','academic_visual_prompt.md','plot_review_metrics.py','package_figure.py',
             'source_data.json','source_data.csv','exports.json','collision_audit.json','pdf_text_audit.json','qa_review.json']
    names += [STEM+suffix for suffix in ['.png','.pdf','.svg','.tiff','.alignment.json','.alignment.svg']]
    records = []
    for name in names:
        p=HERE/name
        records.append({'name':name,'local_path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
    manifest = {'files':records,'previous_figures_preserved':preserved,'backend':'python','review_units':449,
                'original_data_modified':False,'user_facing_figures':1}
    (HERE/'artifact_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    archive = HERE/'双智能体复核新增指标_20261107.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in names+['artifact_manifest.json']:
            z.write(HERE/name,arcname=name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for row in records:
            assert hashlib.sha256(z.read(row['name'])).hexdigest()==row['sha256']
    BACKUP.mkdir(parents=True,exist_ok=True)
    for name in names+['artifact_manifest.json',archive.name]:
        shutil.copyfile(HERE/name,BACKUP/name)
        assert sha(HERE/name)==sha(BACKUP/name)
    DELIVER.mkdir(parents=True,exist_ok=True)
    for name in [STEM+'.png',STEM+'.pdf',STEM+'.svg',archive.name]:
        shutil.copyfile(HERE/name,DELIVER/name)
        assert sha(HERE/name)==sha(DELIVER/name)
    print(json.dumps({'figure':str(DELIVER/(STEM+'.png')),'verified_artifacts':len(records),
                      'zip_sha256':sha(archive),'preserved_figures':len(preserved)},ensure_ascii=False))

if __name__=='__main__':
    main()
