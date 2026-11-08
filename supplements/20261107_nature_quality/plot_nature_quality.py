"""Plot exact corpus measurements with a restrained scientific composition."""
from pathlib import Path
import sys,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager
from matplotlib.transforms import ScaledTranslation
from matplotlib.patches import Patch
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=Path("C:/Users/g'g/Documents/Codex/2026-11-06/lst-x4d-x20-x47-r-x55/outputs")
SKILL=Path.home()/'.codex/skills/nature-figure/scripts'
sys.path.insert(0,str(SKILL))
from audit_panel_alignment import require_matplotlib_panel_alignment

FONT=Path('C:/Windows/Fonts/msyh.ttc')
BOLD=Path('C:/Windows/Fonts/msyhbd.ttc')
fontManager.addfont(str(FONT));fontManager.addfont(str(BOLD))
FAMILY=FontProperties(fname=str(FONT)).get_name()
REG=FontProperties(fname=str(FONT));FB=FontProperties(fname=str(BOLD),weight='bold')
TEAL='#2A7F83';CORAL='#CC8B78';GRAY='#8793A1';INK='#28323D';LIGHT='#E1E5E9';PALE='#DCE9E9'
STEMS=['数据质量评测_Nature版_20261107','各书语料变化_Nature版_20261107']

def panel(ax,letter,title):
    ax.set_label(letter)
    offset=ScaledTranslation(-28/72,14/72,ax.figure.dpi_scale_trans)
    ax.text(0,1,letter,transform=ax.transAxes+offset,fontsize=11,fontweight='bold',fontproperties=FB,va='baseline',ha='left')
    ax.set_title(title,loc='left',pad=14,fontsize=10.5,fontproperties=FB,color=INK)

def style(ax,grid='x'):
    ax.spines[['top','right']].set_visible(False)
    ax.spines['left'].set_color(INK);ax.spines['bottom'].set_color(INK)
    ax.spines['left'].set_linewidth(.65);ax.spines['bottom'].set_linewidth(.65)
    ax.tick_params(axis='both',labelsize=8,length=2.4,width=.6,color=INK,labelcolor=INK,pad=4)
    if grid:ax.grid(axis=grid,color=LIGHT,lw=.45,zorder=0)
    ax.set_axisbelow(True)

def export(fig,stem):
    fig.canvas.draw()
    report=require_matplotlib_panel_alignment(fig,json_out=HERE/(stem+'.alignment.json'),
        overlay_svg=HERE/(stem+'.alignment.svg'),require_panel_labels=True,
        tolerance_pt=1.5,gutter_tolerance_pt=1.5,strict=True)
    assert report['verdict']=='PASS',report
    fig.savefig(OUT/(stem+'.png'),dpi=600,facecolor='white',transparent=False,bbox_inches=None,
        metadata={'Title':stem,'Description':'Measured structural data-quality metrics and descriptive corpus statistics.'})
    fig.savefig(HERE/(stem+'.pdf'),facecolor='white',bbox_inches=None,
        metadata={'Title':stem,'Subject':'Source-backed corpus quality measurements; semantic accuracy not human-labelled.'})
    fig.savefig(HERE/(stem+'.svg'),facecolor='white',bbox_inches=None,
        metadata={'Title':stem,'Date':'2026-11-07'})
    fig.savefig(HERE/(stem+'.tiff'),dpi=600,facecolor='white',transparent=False,bbox_inches=None,
        pil_kwargs={'compression':'tiff_lzw'})
    plt.close(fig)

def quality_figure(q):
    d=q['base_metrics']
    fig,axs=plt.subplots(2,2,figsize=(9,6.4))
    fig.subplots_adjust(left=.17,right=.95,top=.86,bottom=.115,wspace=.70,hspace=.83)
    fig.suptitle('武侠语料数据质量',x=.070,y=.968,ha='left',fontsize=16,fontproperties=FB,color=INK)
    a,b,c,e=axs.flat

    panel(a,'a','样本质量指标');a.set_axis_off()
    metrics=[('字段完整率',q['sample_field_completeness']),('类型一致率',q['field_type_consistency']),
        ('文本对唯一率',q['exact_text_pair_uniqueness']),('验证词表覆盖率',d['validation_vocabulary_coverage']),('文本语义准确率',None)]
    for i,(label,value) in enumerate(metrics):
        y=.89-i*.20
        a.text(0,y,label,transform=a.transAxes,fontsize=9.3,color=INK,va='center',fontproperties=REG)
        display='待人工标注' if value is None else (f'{value:.4%}' if i==3 else f'{value:.2%}')
        a.text(1,y,display,transform=a.transAxes,ha='right',va='center',fontsize=9.4,
            color=GRAY if value is None else TEAL,fontproperties=REG if value is None else FB)
        if i<4:a.plot([0,1],[y-.10,y-.10],transform=a.transAxes,color=LIGHT,lw=.6)

    panel(b,'b','已知字符异常处置');style(b,grid=None)
    b.spines['left'].set_visible(False);b.tick_params(axis='y',length=0)
    b.barh(2,196,height=.43,color='#F0F2F4',edgecolor=GRAY,lw=.7,zorder=3)
    b.barh(1,170,height=.43,color=TEAL,edgecolor=TEAL,lw=.7,zorder=3)
    b.barh(1,26,left=170,height=.43,color=CORAL,edgecolor=CORAL,lw=.7,zorder=3)
    b.scatter([0],[0],s=16,facecolor='white',edgecolor=INK,lw=.7,clip_on=False,zorder=4)
    b.text(201,2,'196',fontsize=8.5,color=INK,va='center')
    b.text(6,0,'0',fontsize=8.5,color=INK,va='center')
    b.set_yticks([2,1,0],['原始PUA','修复与隔离','正文剩余'])
    b.set_xlim(0,220);b.set_xticks([0,50,100,150,200]);b.set_ylim(-.60,3.05)
    b.set_xlabel('出现次数 / 次',fontsize=8.5)
    b.legend(handles=[Patch(facecolor=TEAL,label='有据恢复 170'),Patch(facecolor=CORAL,edgecolor=CORAL,label='隔离 26')],
        loc='upper right',bbox_to_anchor=(.99,1.0),ncols=2,frameon=False,fontsize=7.2,
        handlelength=1.15,columnspacing=1.1,handletextpad=.45,borderpad=0)

    panel(c,'c','样本来源与划分');style(c)
    c.spines['left'].set_visible(False);c.tick_params(axis='y',length=0)
    values=[65035,3469,3962,224];ys=[3,2,1,0]
    for i,(y,value) in enumerate(zip(ys,values)):
        c.barh(y,value,height=.49,color=TEAL if i%2==0 else PALE,edgecolor=TEAL,
            linewidth=.6,zorder=3)
        c.text(value+700,y,f'{value:,}',va='center',fontsize=8.1,color=INK)
    c.set_yticks(ys,['金庸·训练','金庸·验证','补充·训练','补充·验证'])
    c.set_ylim(-.65,3.65);c.set_xlim(0,80000);c.set_xticks([0,20000,40000,60000])
    c.set_xticklabels(['0','20,000','40,000','60,000']);c.set_xlabel('样本数 / 条',fontsize=8.5)

    panel(e,'d','后文长度分布');style(e,grid='y')
    keys=['train_jinyong','validation_jinyong','train_supplementary','validation_supplementary']
    arrays=[np.asarray(q['distributions'][key]['target']) for key in keys]
    positions=[1,2,4,5]
    vp=e.violinplot(arrays,positions=positions,widths=.72,points=100,showextrema=False,showmedians=False)
    for i,body in enumerate(vp['bodies']):
        color=TEAL if i<2 else CORAL;body.set_facecolor(color);body.set_edgecolor(color);body.set_alpha(.30);body.set_linewidth(.65)
    for x,values in zip(positions,arrays):
        low,q25,median,q75,high=np.quantile(values,[0,.25,.5,.75,1])
        e.vlines(x,low,high,color=INK,lw=.65,zorder=4)
        e.vlines(x,q25,q75,color=INK,lw=2.1,zorder=5)
        e.scatter([x],[median],s=11,facecolor='white',edgecolor=INK,lw=.65,zorder=6)
    e.set_xlim(.35,5.65);e.set_ylim(0,800);e.set_yticks([0,200,400,600,800]);e.set_ylabel('后文长度 / 字符',fontsize=8.5)
    e.set_xticks(positions,['训练','验证','训练','验证'])
    e.text(1.5,-.25,'金庸',transform=e.get_xaxis_transform(),ha='center',va='top',fontsize=8.5,color=INK,fontproperties=FB)
    e.text(4.5,-.25,'补充语料',transform=e.get_xaxis_transform(),ha='center',va='top',fontsize=8.5,color=INK,fontproperties=FB)
    export(fig,STEMS[0])

def paired_figure(q):
    books=sorted(q['base_metrics']['books'],key=lambda b:b['raw_han'],reverse=True)
    fig,(a,b)=plt.subplots(1,2,figsize=(9,7.2))
    fig.subplots_adjust(left=.17,right=.95,top=.85,bottom=.10,wspace=.70)
    fig.suptitle('各书语料处理前后',x=.070,y=.967,ha='left',fontsize=16,fontproperties=FB,color=INK)
    panel(a,'a','汉字量对比');panel(b,'b','汉字量净变化')
    for ax in [a,b]:style(ax);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
    b.grid(False)
    ys=np.arange(len(books));raw=np.array([x['raw_han']/10000 for x in books]);clean=np.array([x['clean_han']/10000 for x in books])
    a.hlines(ys,clean,raw,color=GRAY,lw=.8,zorder=2)
    a.scatter(raw,ys,marker='o',s=19,facecolors='white',edgecolors=GRAY,lw=.9,zorder=3,label='原始文件')
    a.scatter(clean,ys,marker='D',s=16,color=TEAL,lw=.5,zorder=4,label='故事正文')
    names=[x['title']+('（补充）' if x['source_group']=='supplementary' else '') for x in books]
    a.set_yticks(ys,names);a.set_xlim(0,110);a.set_xticks([0,25,50,75,100]);a.set_xlabel('汉字量 / 万字',fontsize=8.5)
    a.legend(loc='upper right',bbox_to_anchor=(1.04,1.085),ncols=2,frameon=False,fontsize=7.4,
        columnspacing=.9,handletextpad=.3,borderpad=0)
    change=100*(clean/raw-1)
    b.barh(ys,change,height=.48,color=TEAL,edgecolor=TEAL,lw=.4,zorder=3)
    b.axvline(0,color=INK,lw=.65)
    for i in np.argsort(change)[:2]:
        b.text(change[i]-2.2,ys[i],f'{change[i]:.2f}%',ha='right',va='center',fontsize=8.4,color=INK)
    b.set_xlim(-102,2);b.set_xticks([-100,-75,-50,-25,0]);b.set_yticks(ys,[])
    b.set_xlabel('（正文−原始）/ 原始（%）',fontsize=8.5)
    for ax in [a,b]:ax.set_ylim(len(books)-.5,-.75)
    export(fig,STEMS[1])

def main():
    q=json.loads((HERE/'quality_profile.json').read_text(encoding='utf-8'));OUT.mkdir(parents=True,exist_ok=True)
    params={'font.family':'sans-serif','font.sans-serif':[FAMILY,'Arial','DejaVu Sans'],'font.size':8.5,
        'axes.unicode_minus':False,'axes.labelcolor':INK,'text.color':INK,'svg.fonttype':'none','pdf.fonttype':42,
        'ps.fonttype':42,'figure.facecolor':'white','savefig.facecolor':'white','legend.frameon':False,
        'axes.spines.top':False,'axes.spines.right':False,'hatch.linewidth':.35}
    with plt.rc_context(params):quality_figure(q);paired_figure(q)
    records=[]
    for stem in STEMS:
        for root,suffix in [(OUT,'.png'),(HERE,'.pdf'),(HERE,'.svg')]:
            p=root/(stem+suffix);records.append(dict(file=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (HERE/'exports.json').write_text(json.dumps(dict(backend='python',matplotlib=matplotlib.__version__,files=records,
        input_modified=False,visible_prose_annotations=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'rendered':[str(OUT/(s+'.png')) for s in STEMS]},ensure_ascii=False))
if __name__=='__main__':main()
