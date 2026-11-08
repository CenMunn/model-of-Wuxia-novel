"""Render the incremental, measured content-review evidence as one figure."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.patches import Rectangle
from matplotlib.transforms import ScaledTranslation
from matplotlib.colors import to_rgb
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'dual_agent_review_20261107'
STEM = '双智能体复核新增指标_Nature版_20261107'
SCRIPTS = Path.home() / '.codex/skills/nature-figure/scripts'
sys.path.insert(0, str(SCRIPTS))
from audit_panel_alignment import require_matplotlib_panel_alignment

TEAL = '#2A7F83'
CORAL = '#CC8B78'
AMBER = '#C9A15C'
GRAY = '#AAB5C2'
INK = '#28323D'
LIGHT = '#E2E7EB'
PALE = '#E9EEF1'
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BOLD = Path('C:/Windows/Fonts/msyhbd.ttc')
fontManager.addfont(str(FONT))
fontManager.addfont(str(BOLD))
FAMILY = FontProperties(fname=str(FONT)).get_name()
REG = FontProperties(fname=str(FONT))
FB = FontProperties(fname=str(BOLD), weight='bold')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]

def extract():
    manifest = json.loads((SOURCE / 'artifact_manifest.json').read_text(encoding='utf-8'))
    expected = {r['name']: r['sha256'] for r in manifest['files']}
    inputs = ['review_metrics.json', 'final_labels.jsonl', 'reviewer_a.jsonl', 'reviewer_b.jsonl', 'review_packet.jsonl']
    verified = []
    for name in inputs:
        assert sha(SOURCE / name) == expected[name], name
        verified.append({'name': name, 'sha256': expected[name]})
    metrics = json.loads((SOURCE / 'review_metrics.json').read_text(encoding='utf-8'))
    final = rows(SOURCE / 'final_labels.jsonl')
    packet = {r['id']: r for r in rows(SOURCE / 'review_packet.jsonl')}
    a = {r['id']: r for r in rows(SOURCE / 'reviewer_a.jsonl')}
    b = {r['id']: r for r in rows(SOURCE / 'reviewer_b.jsonl')}
    assert len(final) == len(packet) == len(a) == len(b) == 449
    counts = {kind: Counter(r['final_label'] for r in final if r['kind'] == kind)
              for kind in ['retained', 'excluded', 'repair', 'quarantine']}
    assert counts['retained'] == Counter(KEEP=300)
    assert counts['excluded'] == Counter(EXCLUDE=100)
    assert counts['repair'] == Counter(SUPPORTED=33)
    assert counts['quarantine'] == Counter(JUSTIFIED=3, OVERCONSERVATIVE=11, UNCERTAIN=2)
    flagged = [r['id'] for r in final if r['kind'] == 'retained' and r['flags']]
    assert len(flagged) == metrics['retained_flagged_units'] == 14
    categories = ['JUSTIFIED', 'OVERCONSERVATIVE', 'UNCERTAIN']
    matrix = np.zeros((3, 3), dtype=int)
    qids = [r['id'] for r in final if r['kind'] == 'quarantine']
    for key in qids:
        matrix[categories.index(a[key]['label']), categories.index(b[key]['label'])] += 1
    assert matrix.tolist() == [[5, 0, 3], [0, 7, 0], [0, 0, 1]]
    agreement = np.trace(matrix) / matrix.sum()
    chance = np.dot(matrix.sum(axis=0), matrix.sum(axis=1)) / matrix.sum() ** 2
    kappa = (agreement - chance) / (1 - chance)
    assert abs(kappa - metrics['initial_agreement']['by_kind']['quarantine']['cohen_kappa']) < 1e-12
    recovered_ids = [r['id'] for r in final if r['kind'] == 'quarantine' and r['final_label'] == 'OVERCONSERVATIVE']
    chars = sum(len(packet[key]['text'].strip()) for key in recovered_ids)
    assert chars == metrics['recovery_candidate_raw_characters_excluding_outer_whitespace'] == 2808
    result = {'ai_assisted_review': True, 'human_gold_accuracy': None, 'review_units': 449,
              'paragraph_noise': {'numerator': counts['retained']['REMOVE'], 'denominator': 300, 'unit': 'paragraph'},
              'main_story_false_exclusion': {'numerator': counts['excluded']['RESTORE'], 'denominator': 100, 'unit': 'nonempty_source_line'},
              'repair_support': {'numerator': counts['repair']['SUPPORTED'], 'denominator': 33, 'unit': 'repair_record'},
              'local_review_flags': {'numerator': len(flagged), 'denominator': 300, 'fraction': len(flagged)/300},
              'final_quarantine': {'JUSTIFIED': 3, 'OVERCONSERVATIVE': 11, 'UNCERTAIN': 2},
              'recovery_candidate_characters': chars, 'initial_quarantine_matrix': matrix.tolist(),
              'initial_quarantine_categories': categories, 'initial_quarantine_agreement': float(agreement),
              'initial_quarantine_kappa': float(kappa), 'source_hashes_verified': verified,
              'frozen_corpus_modified': False, 'previous_figures_modified': False}
    (HERE / 'source_data.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    csv_rows = [
        ['a', 'paragraph_noise', 0, 300, 'paragraph', 'final_review'],
        ['a', 'main_story_false_exclusion', 0, 100, 'source_line', 'final_review'],
        ['a', 'repair_support', 33, 33, 'record', 'final_review'],
        ['b', 'local_review_flags', 14, 300, 'paragraph', 'final_review'],
        ['c', 'continued_quarantine', 3, 16, 'record', 'after_additional_evidence'],
        ['c', 'recovery_candidate', 11, 16, 'record', 'after_additional_evidence'],
        ['c', 'unresolved', 2, 16, 'record', 'after_additional_evidence'],
        ['d', 'quarantine_reviewer_agreement', int(np.trace(matrix)), 16, 'record', 'initial_independent_review']]
    with (HERE / 'source_data.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['panel', 'metric', 'numerator', 'denominator', 'unit', 'stage'])
        writer.writerows(csv_rows)
    return result

def panel(ax, letter, title):
    ax.set_label(letter)
    transform = ax.transAxes + ScaledTranslation(-28/72, 14/72, ax.figure.dpi_scale_trans)
    ax.text(0, 1, letter, transform=transform, fontsize=11, fontproperties=FB, va='baseline', ha='left')
    ax.set_title(title, loc='left', pad=14, fontsize=10.5, fontproperties=FB, color=INK)

def blend(color, strength):
    rgb = np.asarray(to_rgb(color))
    return tuple(1 - strength * (1-rgb))

def render(d):
    fig, axs = plt.subplots(2, 2, figsize=(9, 6.5))
    fig.subplots_adjust(left=.13, right=.95, top=.84, bottom=.14, wspace=.47, hspace=.70)
    fig.suptitle('数据清洗 · 双智能体辅助复核', x=.070, y=.966, ha='left', fontsize=16, fontproperties=FB, color=INK)
    a, b, c, e = axs.flat

    panel(a, 'a', '内容抽查与修复证据')
    a.set_axis_off()
    values = [('整段噪声', '0 / 300 段'), ('误排主故事', '0 / 100 段'), ('修复有据', '33 / 33 条')]
    for i, (label, value) in enumerate(values):
        y = .81 - i * .30
        a.text(0, y, label, transform=a.transAxes, va='center', fontsize=9.4, fontproperties=REG, color=INK)
        a.text(1, y, value, transform=a.transAxes, ha='right', va='center', fontsize=10.2, fontproperties=FB, color=TEAL)
        if i < 2:
            a.plot([0, 1], [y-.15, y-.15], transform=a.transAxes, color=LIGHT, lw=.65)

    panel(b, 'b', '局部文字复查提示')
    b.set_axis_off()
    b.set_xlim(0, 30); b.set_ylim(-.5, 16.5)
    b.text(0, 14.45, f"{d['local_review_flags']['fraction']:.2%}", fontsize=17, fontproperties=FB, color=CORAL, va='center')
    b.text(30, 14.45, '14 / 300 段', ha='right', va='center', fontsize=8.7, color=INK)
    b.text(30, 11.1, '每格 1 段', ha='right', va='center', fontsize=7.2, color='#647281')
    for i in range(300):
        x = i % 30; y = 9 - i // 30
        b.add_patch(Rectangle((x+.06, y+.06), .88, .88, facecolor=CORAL if i < 14 else PALE, edgecolor='none'))

    panel(c, 'c', '隔离处置建议 · 补充复核后')
    c.spines[['top', 'right', 'left']].set_visible(False)
    c.spines['bottom'].set_color(INK); c.spines['bottom'].set_linewidth(.65)
    c.set_xlim(0, 16); c.set_ylim(0, 1.6); c.set_yticks([])
    c.set_xticks([0, 4, 8, 12, 16]); c.tick_params(axis='x', labelsize=8, length=2.4, width=.6, color=INK, pad=4)
    c.set_xlabel('隔离记录 / 条', fontsize=8.4)
    c.text(0, 1.39, f"候选原段 {d['recovery_candidate_characters']:,} 字符", fontsize=9.2, color=INK, va='center')
    start = 0
    for n, label, color, fg in [(3, '继续隔离', TEAL, 'white'), (11, '回收候选', AMBER, INK), (2, '待核', GRAY, INK)]:
        c.barh(.70, n, left=start, height=.70, color=color, edgecolor='white', linewidth=.7, zorder=2)
        x = start + n/2
        c.text(x, .83, str(n), ha='center', va='center', fontsize=12, fontproperties=FB, color=fg)
        c.text(x, .53, label, ha='center', va='center', fontsize=7.2, color=fg)
        start += n
    assert start == 16

    panel(e, 'd', '隔离项初轮判读一致性')
    e.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
    e.set_xlim(0, 3); e.set_ylim(3.02, -.83)
    e.set_xticks([.5, 1.5, 2.5], ['合理', '偏保守', '待定'])
    e.set_yticks([.5, 1.5, 2.5], ['合理', '偏保守', '待定'])
    e.tick_params(axis='both', length=0, labelsize=7.7, pad=4)
    e.set_xlabel('审查者 B', fontsize=8.4, labelpad=6)
    e.set_ylabel('审查者 A', fontsize=8.4, labelpad=8)
    e.text(0, -.45, f"一致率 {d['initial_quarantine_agreement']:.2%}   ·   κ = {d['initial_quarantine_kappa']:.3f}",
           va='center', fontsize=7.9, color=INK)
    matrix = np.asarray(d['initial_quarantine_matrix'])
    for row in range(3):
        for col in range(3):
            n = int(matrix[row, col])
            strength = .88*n/matrix.max()
            color = blend(TEAL if row == col else CORAL, strength) if n else '#F5F7F8'
            e.add_patch(Rectangle((col, row), 1, 1, facecolor=color, edgecolor='white', linewidth=1))
            e.text(col+.5, row+.5, str(n), va='center', ha='center', fontsize=11 if n else 8.5,
                   fontproperties=FB if n else REG, color='white' if row == col and n >= 5 else INK if n else '#8A96A3')

    fig.canvas.draw()
    audit = require_matplotlib_panel_alignment(fig, json_out=HERE/(STEM+'.alignment.json'),
        overlay_svg=HERE/(STEM+'.alignment.svg'), require_panel_labels=True,
        tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True)
    assert audit['verdict'] == 'PASS'
    fig.savefig(HERE/(STEM+'.png'), dpi=600, facecolor='white', transparent=False, bbox_inches=None,
                metadata={'Title': STEM, 'Description': 'Measured AI-assisted review labels, not human-gold accuracy.'})
    fig.savefig(HERE/(STEM+'.pdf'), facecolor='white', bbox_inches=None,
                metadata={'Title': STEM, 'Subject': 'Independent initial labels and final source-backed review recommendations.'})
    fig.savefig(HERE/(STEM+'.svg'), facecolor='white', bbox_inches=None, metadata={'Title': STEM, 'Date': '2026-11-07'})
    fig.savefig(HERE/(STEM+'.tiff'), dpi=600, facecolor='white', bbox_inches=None, pil_kwargs={'compression': 'tiff_lzw'})
    plt.close(fig)

def main():
    data = extract()
    params = {'font.family': 'sans-serif', 'font.sans-serif': [FAMILY, 'Arial', 'DejaVu Sans'],
              'font.size': 8.5, 'axes.unicode_minus': False, 'axes.labelcolor': INK, 'text.color': INK,
              'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
              'figure.facecolor': 'white', 'savefig.facecolor': 'white', 'legend.frameon': False}
    with plt.rc_context(params):
        render(data)
    outputs = []
    for suffix in ['.png', '.pdf', '.svg', '.tiff']:
        p = HERE/(STEM+suffix)
        outputs.append({'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)})
    (HERE/'exports.json').write_text(json.dumps({'backend': 'python', 'matplotlib': matplotlib.__version__,
        'files': outputs, 'data_modified': False, 'visible_explanatory_footnotes': False}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'figure': str(HERE/(STEM+'.png')), 'panels': 4}, ensure_ascii=False))

if __name__ == '__main__':
    main()
