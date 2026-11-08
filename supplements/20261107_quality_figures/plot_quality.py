"""Create source-backed, descriptive corpus-QC figures for reports and slides."""
from pathlib import Path
import json,hashlib,platform,csv,zipfile,shutil,argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
from matplotlib.patches import FancyBboxPatch,Patch
from matplotlib.transforms import blended_transform_factory
from PIL import Image

HERE=Path(__file__).resolve().parent
OUT=Path("C:/Users/g'g/Documents/Codex/2026-11-06/lst-x4d-x20-x47-r-x55/outputs")
FONT=Path('C:/Windows/Fonts/msyh.ttc');BOLD=Path('C:/Windows/Fonts/msyhbd.ttc')
FAMILY=REG=BOLDPROP=None
BLUE='#2166AC';GREEN='#177C66';ORANGE='#A55516';INK='#172B4D';MUTED='#526277';GRAY='#718096';GRID='#DDE5ED';PALE='#F3F6FA'
STEMS=['数据预处理量化总览_20261107','各书处理前后汉字量_20261107']

def text(fig,x,y,s,size=12,color=INK,bold=False,**kw):
    return fig.text(x,y,s,fontsize=size,color=color,fontproperties=BOLDPROP if bold else REG,**kw)
def axis_style(ax):
    ax.set_facecolor('white')
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color(GRID)
    ax.tick_params(axis='both',length=0,labelsize=10,colors=MUTED,pad=7)
    ax.grid(axis='x',color=GRID,linewidth=.65,zorder=0)
    ax.set_axisbelow(True)
def export(fig,stem):
    fig.savefig(OUT/(stem+'.png'),dpi=220,facecolor='white',transparent=False,
        metadata={'Title':stem,'Description':'Descriptive corpus preparation metrics; no model evaluation or text-correction accuracy asserted.'})
    fig.savefig(OUT/(stem+'.svg'),facecolor='white',transparent=False,
        metadata={'Title':stem,'Date':'2026-11-07','Description':'Source data and metric definitions accompany the figure.'})
    plt.close(fig)

def overview(d):
    fig=plt.figure(figsize=(16.5,11.5),facecolor='white')
    text(fig,.055,.952,'语料预处理 · 量化结果',30,bold=True)
    text(fig,.055,.914,'固定版本 corpus_v1_20261107  |  金庸15本＋补充2本  |  统计日期 2026-11-07',12,color=MUTED)
    cards=[('正文汉字量',f"{d['clean_han']:,}",'17本 · 527个正文单元'),
           ('可用续写样本',f"{d['total_samples']:,}",'68,997训练＋3,693验证'),
           ('已知PUA已处置',f"{d['raw_pua_occurrences']} / {d['raw_pua_occurrences']}",'170次恢复；26次隔离'),
           ('验证词表覆盖',f"{d['validation_vocabulary_coverage']:.4%}",f"未知 {d['validation_unknown_characters']} / {d['validation_character_denominator']:,} 个字符")]
    for i,(label,value,note) in enumerate(cards):
        x=.055+i*.232;w=.212
        fig.add_artist(FancyBboxPatch((x,.778),w,.108,boxstyle='round,pad=0.008,rounding_size=0.009',
            transform=fig.transFigure,facecolor=PALE,edgecolor=GRID,linewidth=.7,zorder=-2))
        text(fig,x+.012,.860,label,11.5,color=MUTED)
        text(fig,x+.012,.816,value,24,bold=True,color=BLUE if i<2 else GREEN)
        text(fig,x+.012,.788,note,9.8,color=MUTED)

    text(fig,.055,.714,'A  原始与处理后的汉字量',16,bold=True)
    ax=fig.add_axes([.140,.535,.325,.140]);axis_style(ax)
    values=[d['raw_han']/10000,d['clean_han']/10000]
    ax.barh([1,0],values,height=.45,color=['#E4E9EF',BLUE],edgecolor=[GRAY,BLUE],linewidth=.9,zorder=3)
    ax.set_yticks([1,0],['原始文件','处理后正文']);ax.set_ylim(-.6,1.6);ax.set_xlim(0,1000)
    ax.set_xticks([0,200,400,600,800,1000]);ax.set_xlabel('汉字量 / 万字',fontsize=10,color=MUTED,labelpad=5)
    for y,value in zip([1,0],values):ax.text(value+13,y,f'{value:.2f}万',va='center',fontsize=11,color=INK)
    text(fig,.055,.473,f"量比 {d['after_before_han_ratio']:.2%}；净减少 {-d['net_han_change']/10000:.2f}万汉字",12,bold=True)
    text(fig,.055,.449,'原始量含序跋、目录等；处理后含有据补入内容。',10.5,color=MUTED)

    text(fig,.565,.714,'B  196次私用区字符异常的去向',16,bold=True)
    ax=fig.add_axes([.580,.546,.355,.110]);axis_style(ax)
    ax.barh([0],[d['evidence_restored_pua']],height=.46,color=GREEN,edgecolor=GREEN,zorder=3)
    ax.barh([0],[d['quarantined_pua']],left=[d['evidence_restored_pua']],height=.46,
        color=ORANGE,edgecolor='white',hatch='///',linewidth=.7,zorder=3)
    ax.set_ylim(-.55,.55);ax.set_xlim(0,196);ax.set_yticks([]);ax.set_xticks([0,50,100,150,196])
    ax.set_xlabel('原始出现次数 / 次',fontsize=10,color=MUTED,labelpad=5)
    ax.text(85,0,'有据恢复 170次\n86.73%',ha='center',va='center',color='white',fontsize=12,fontproperties=BOLDPROP,linespacing=1.5)
    ax.text(183,0,'26次\n13.27%',ha='center',va='center',color='white',fontsize=10,fontproperties=BOLDPROP,linespacing=1.4,
        bbox={'facecolor':ORANGE,'edgecolor':'none','pad':.5})
    ax.legend(handles=[Patch(facecolor=GREEN,label='有据恢复'),Patch(facecolor=ORANGE,edgecolor='white',hatch='///',label='原段隔离')],
        loc='lower left',bbox_to_anchor=(0,1.12),frameon=False,ncols=2,fontsize=10,handlelength=1.4,columnspacing=2)
    text(fig,.565,.473,'进入正文的PUA：0次；仍隔离16个原段落。',12,bold=True)
    text(fig,.565,.449,'处置完成率100% ≠ 原文全部修复正确。',10.5,color=MUTED)

    text(fig,.055,.392,'C  训练与验证样本分布',16,bold=True)
    ax=fig.add_axes([.140,.166,.325,.190]);axis_style(ax)
    counts=[d['samples_by_source'][k] for k in ['train_jinyong','validation_jinyong','train_supplementary','validation_supplementary']]
    labels=['金庸 · 训练','金庸 · 验证','补充 · 训练','补充 · 验证'];ys=[3,2,1,0]
    for i,(y,n) in enumerate(zip(ys,counts)):
        color=BLUE if i%2==0 else GREEN
        ax.barh(y,n,height=.53,color=color,edgecolor=color,hatch='///' if i%2 else None,linewidth=.7,zorder=3)
        ax.text(n+850,y,f'{n:,}',ha='left',va='center',fontsize=11,color=INK)
    ax.set_yticks(ys,labels);ax.set_ylim(-.65,3.65);ax.set_xlim(0,78000);ax.set_xticks([0,20000,40000,60000])
    ax.set_xticklabels(['0','20,000','40,000','60,000']);ax.set_xlabel('续写样本数 / 条',fontsize=10,color=MUTED,labelpad=5)

    text(fig,.565,.392,'D  可复核的规则验收',16,bold=True)
    ax=fig.add_axes([.565,.160,.370,.205]);ax.set_axis_off()
    checks=[('样本跨回／跨隔离断点','0 条'),('修复记录证据重放','33 / 33'),
        ('跨集长重复（≥128非空白字符）','未检出'),('验证正文占比（按字符）',f"{d['validation_character_fraction']:.3%}"),
        ('原始文件指纹','17本TXT＋RAR一致')]
    for i,(label,value) in enumerate(checks):
        y=.94-i*.20
        ax.text(0,y,label,fontsize=11.5,color=MUTED,va='center',transform=ax.transAxes)
        ax.text(1,y,value,fontsize=12,color=INK,ha='right',va='center',transform=ax.transAxes,fontproperties=BOLDPROP)
        if i<4:ax.plot([0,1],[y-.092,y-.092],color=GRID,lw=.65,transform=ax.transAxes)

    fig.lines.append(plt.Line2D([.055,.945],[.103,.103],transform=fig.transFigure,color=GRID,lw=.8))
    text(fig,.055,.074,'口径：汉字量不含标点和空白；样本、修复及指纹为固定版本的全量规则检查，不是人工正确率。',10.5,color=MUTED)
    text(fig,.055,.048,'范围：未做全文逐字校勘；近重复检查有算法与阈值范围；尚未训练模型，也没有生成质量分数。',10.5,color=MUTED)
    export(fig,STEMS[0])

def by_book(d):
    fig=plt.figure(figsize=(16.5,11.8),facecolor='white')
    text(fig,.055,.952,'各书处理前后 · 汉字量对比',28,bold=True)
    text(fig,.055,.914,'原始文件包含序跋、目录、附录等；处理后为故事正文。按原始汉字量排序，所有条形从0开始。',12,color=MUTED)
    ax=fig.add_axes([.135,.159,.540,.680]);axis_style(ax)
    bs=sorted(d['books'],key=lambda b:b['raw_han'],reverse=True)
    ys=list(range(len(bs)))
    ax.barh([y-.16 for y in ys],[b['raw_han']/10000 for b in bs],height=.26,color='#E4E9EF',edgecolor=GRAY,linewidth=.9,label='原始文件',zorder=3)
    ax.barh([y+.16 for y in ys],[b['clean_han']/10000 for b in bs],height=.26,color=BLUE,edgecolor=BLUE,linewidth=.7,label='处理后正文',zorder=3)
    ax.set_yticks(ys,[b['title']+(' *' if b['source_group']=='supplementary' else '') for b in bs])
    ax.set_ylim(len(bs)-.5,-.75);ax.set_xlim(0,110);ax.set_xticks([0,20,40,60,80,100]);ax.tick_params(axis='y',labelsize=11.5,pad=12)
    ax.set_xlabel('汉字量 / 万字',fontsize=12,color=MUTED,labelpad=10)
    ax.legend(frameon=False,ncols=2,fontsize=11,loc='lower left',bbox_to_anchor=(0,1.035),columnspacing=2)
    blend=blended_transform_factory(fig.transFigure,ax.transData)
    for x,label in [(.745,'原始 / 万字'),(.840,'正文 / 万字'),(.930,'后／前量比')]:
        text(fig,x,.858,label,11.5,bold=True,ha='center')
    for y,b in zip(ys,bs):
        for x,value in [(.745,f"{b['raw_han']/10000:.2f}"),(.840,f"{b['clean_han']/10000:.2f}"),(.930,f"{b['after_before_ratio']:.2%}")]:
            fig.text(x,y,value,transform=blend,ha='center',va='center',fontsize=11.5,color=INK,fontproperties=REG)
    fig.lines.append(plt.Line2D([.705,.705],[.159,.842],transform=fig.transFigure,color=GRID,lw=.8))
    fig.lines.append(plt.Line2D([.055,.945],[.104,.104],transform=fig.transFigure,color=GRID,lw=.8))
    text(fig,.055,.077,'* 补充语料。量比表示规模变化，不是清洗准确率；处理后文本包含有据恢复和补齐的内容。',10.5,color=MUTED)
    text(fig,.055,.050,'《越女剑》量比约20.32%，主要因为将原文件所附《三十三剑客图》分离；不是仅凭篇幅删去故事。',10.5,color=MUTED)
    export(fig,STEMS[1])

def docs(d):
    records=[
        dict(metric='known_pua_disposition_coverage',label='已知PUA处置完成率',numerator=196,denominator=196,value=1,unit='ratio',scope='所有已定位PUA均有恢复或隔离状态，不是全部错字修复率'),
        dict(metric='known_pua_evidence_restoration_fraction',label='已知PUA有据恢复占比',numerator=170,denominator=196,value=170/196,unit='ratio',scope='按原始PUA出现次数计'),
        dict(metric='known_pua_quarantine_fraction',label='已知PUA隔离占比',numerator=26,denominator=196,value=26/196,unit='ratio',scope='随16段原文隔离；不是伪造修复'),
        dict(metric='structural_sample_pass_fraction',label='样本结构核验通过率',numerator=72690,denominator=72690,value=1,unit='ratio',scope='仅限实现的来源、连续性、划分和长度等结构规则'),
        dict(metric='repair_replay_fraction',label='修复记录证据重放通过率',numerator=33,denominator=33,value=1,unit='ratio',scope='验证可按来源和偏移重建，不等于权威底本全文校勘'),
        dict(metric='validation_vocabulary_coverage',label='验证文本词表覆盖率',numerator=d['validation_character_denominator']-49,denominator=d['validation_character_denominator'],value=d['validation_vocabulary_coverage'],unit='ratio',scope='统一训练词表；只统计验证正文字符，不是模型准确率'),
        dict(metric='after_before_han_ratio',label='处理后/原始汉字量比',numerator=d['clean_han'],denominator=d['raw_han'],value=d['after_before_han_ratio'],unit='ratio',scope='规模比，含非正文分离及有据补入，不是逐字保留率'),
        dict(metric='cross_gap_sample_rate',label='跨隔离断点样本率',numerator=0,denominator=72690,value=0,unit='ratio',scope='依照已记录断点核验'),
        dict(metric='validation_character_fraction',label='验证正文字符占比',numerator=d['split_story_characters']['validation'],denominator=sum(d['split_story_characters'].values()),value=d['validation_character_fraction'],unit='ratio',scope='含标点；按整回划分，非独立原文测试集')]
    with (OUT/'预处理量化指标_20261107.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    description=['# 数据预处理量化图表说明','',
        '对象：corpus_v1_20261107；用于课程报告、PPT和小组复核。图表使用真实归档统计及对原件、正文的只读重算，未训练任何模型。','',
        '## 图表','',
        '1. 数据预处理量化总览：正文规模、PUA异常去向、训练/验证样本数量、词表覆盖和规则验收。',
        '2. 各书处理前后汉字量：同一零起点尺度显示17本书的原始/正文汉字量，右侧提供精确量比。SVG保留可编辑文字，依赖微软雅黑或兼容中文字体；PNG不依赖字体安装。','',
        '## 主要数值与解释','',
        '|指标|数值|含义|','|---|---:|---|',
        f"|原始汉字量|{d['raw_han']:,}|17本原文件，包含非正文|",
        f"|处理后正文汉字量|{d['clean_han']:,}|含有据恢复及补齐内容，排除隔离段落|",
        f"|处理后／原始规模比|{d['after_before_han_ratio']:.4%}|不是逐字保留率，也不是清洗准确率|",
        '|已知PUA处置完成率|196/196＝100%|170次恢复＋26次隔离|',
        '|有据恢复占比|170/196＝86.7347%|按原始异常码位出现次数计|',
        '|样本结构检查通过率|72,690/72,690＝100%|限于已实现的结构规则|',
        '|修复证据重放通过率|33/33＝100%|可按来源与偏移重建修复|',
        f"|验证文本词表覆盖率|{d['validation_vocabulary_coverage']:.6%}|未知49/{d['validation_character_denominator']:,}；不是预测准确率|",
        '|跨回／跨隔离断点样本|0条|依照已记录的章节与断点检查|',
        f"|验证正文字符占比|{d['validation_character_fraction']:.4%}|按整回分配；与样本行数占比不同|",'',
        '## 汉字量变化可追溯','',
        f"原始{d['raw_han']:,} − 分离的序跋/目录/附录/注释/标题等{d['separated_nonstory_and_heading_han']:,} − 隔离原段{d['quarantined_original_han']:,} ＋ 修复及补齐的净变化{d['repair_net_han_change']:,} ＝ 正文{d['clean_han']:,}。",
        '“分离”表示这些内容仍保留在原件、元数据和分类记录中。标题是结构信息，分离到元数据不等于它是错误内容。1639字符的缺文章尾补齐含标点及换行，与此处“汉字量净变化”不是同一单位或范围。','',
        '## 不能从这些数字推出的结论','',
        '不能把规则通过率称为“全文清洗准确率100%”。尚无逐字金标准或独立人工抽检标注，因此当前不能报告总体纠错准确率、误删率、过滤Precision/Recall/F1。',
        '后续如需上述指标，应先对原文块标注“应保留/应剔除”，对修复处标注正确字符，再统计误删、漏剔除和错误修复；要保留抽样方式、样本量与评审分歧。',
        '未检出长重复限于至少128个非空白字符的完全重复及记录的近重复候选方法；不代表所有语义改写与短语均被穷尽。验证集用于选模，没有另设独立原文测试集。','',
        '## 复现与审计','',
        'source-data JSON记录输入文件SHA256、各书数值、原始汉字分类与分母；CSV可直接导入Excel。量化数值为固定版本的描述性全量统计，不展示没有依据的误差条或显著性。',
        '图表代码与源数据副本随图表包保存；原始语料和固定数据版本不改动。数值按项目同一汉字范围重算；标点、空白及PUA不计为汉字。',
        '仅重绘图表可运行：python plot_quality.py --data 预处理量化指标_20261107.json --out <输出目录>。Linux需用--font和--bold-font指定已安装的中文字体。',
        '重新统计可使用collect_figure_data.py的--snapshot-root、--manifest和--out参数，分别指定包含nlp目录的归档根目录、服务端导出的归档清单、输出目录。绘图仅需Python、Matplotlib和Pillow；源数据为JSON/CSV。','']
    (OUT/'量化图表说明_20261107.md').write_text('\n'.join(description),encoding='utf-8')
    for name in ['collect_figure_data.py','plot_quality.py']:
        source=HERE/name;target=OUT/name
        if source.resolve()!=target.resolve():shutil.copyfile(source,target)
    files=[OUT/(stem+ext) for stem in STEMS for ext in ['.png','.svg']]
    files += [OUT/n for n in ['预处理量化指标_20261107.json','预处理各书统计_20261107.csv','预处理量化指标_20261107.csv',
        '量化图表说明_20261107.md','collect_figure_data.py','plot_quality.py']]
    manifest=dict(date='2026-11-07',version=d['version_id'],python=platform.python_version(),matplotlib=matplotlib.__version__,
        font_family=FAMILY,svg_text_editable=True,assessed_scope='descriptive corpus preparation metrics; no overall accuracy or model scores',
        corpus_modified=False,files=[])
    for p in files:
        row=dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        if p.suffix=='.png':
            with Image.open(p) as im:row.update(width=im.width,height=im.height,mode=im.mode,dpi=im.info.get('dpi'))
        manifest['files'].append(row)
    manifest_path=OUT/'量化图表导出核验_20261107.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files.append(manifest_path)
    bundle=OUT/'数据预处理量化图表包_20261107.zip'
    with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,arcname=p.name)
    print(json.dumps(dict(figures=[str(p) for p in files if p.suffix in ['.png','.svg']],bundle=str(bundle),
        files=len(files),png_dimensions=[(r['width'],r['height']) for r in manifest['files'] if 'width' in r]),ensure_ascii=False))

def main():
    global OUT,FONT,BOLD,FAMILY,REG,BOLDPROP
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',default=str(HERE/'figure_data.json' if (HERE/'figure_data.json').exists() else HERE/'预处理量化指标_20261107.json'))
    parser.add_argument('--out',default=str(OUT))
    parser.add_argument('--font',default=str(FONT))
    parser.add_argument('--bold-font',default=str(BOLD))
    args=parser.parse_args();OUT=Path(args.out);FONT=Path(args.font);BOLD=Path(args.bold_font)
    assert FONT.is_file(),'Pass --font with an installed Chinese font file'
    if not BOLD.is_file():BOLD=FONT
    fontManager.addfont(str(FONT));fontManager.addfont(str(BOLD))
    FAMILY=FontProperties(fname=str(FONT)).get_name();REG=FontProperties(fname=str(FONT));BOLDPROP=FontProperties(fname=str(BOLD))
    d=json.loads(Path(args.data).read_text(encoding='utf-8'));OUT.mkdir(parents=True,exist_ok=True)
    if Path(args.data).resolve()!=(OUT/'预处理量化指标_20261107.json').resolve():
        shutil.copyfile(args.data,OUT/'预处理量化指标_20261107.json')
    style={'font.family':FAMILY,'font.size':11,'axes.unicode_minus':False,'svg.fonttype':'none',
        'axes.titleweight':'bold','figure.facecolor':'white','savefig.facecolor':'white','hatch.linewidth':.7}
    with plt.rc_context(style):overview(d);by_book(d)
    docs(d)
if __name__=='__main__':main()
