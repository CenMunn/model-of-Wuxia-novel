"""Write a transparent record of completed AI labels, not a human evaluation."""
from pathlib import Path
from collections import Counter
import hashlib, json, zipfile

HERE = Path(__file__).resolve().parent
TITLES = {'retained': '保留正文', 'excluded': '排除内容', 'repair': '修复记录', 'quarantine': '隔离记录'}

def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]

def percent(value):
    return f'{value * 100:.2f}%'

def main():
    metrics = json.loads((HERE / 'review_metrics.json').read_text(encoding='utf-8'))
    sampling = json.loads((HERE / 'sampling_manifest.json').read_text(encoding='utf-8'))
    packet = {r['id']: r for r in rows(HERE / 'review_packet.jsonl')}
    labels = rows(HERE / 'final_labels.jsonl')
    a = {r['id']: r for r in rows(HERE / 'reviewer_a.jsonl')}
    b = {r['id']: r for r in rows(HERE / 'reviewer_b.jsonl')}
    flagged = [r for r in labels if r['kind'] == 'retained' and r['flags']]
    flagged_rows = []
    for r in flagged:
        p = packet[r['id']]
        flagged_rows.append({'id': r['id'], 'book': r['book'], 'raw_line': r['raw_line'],
                             'text': p['text'], 'flags': r['flags'],
                             'reviewer_a_reason': a[r['id']]['reason'], 'reviewer_b_reason': b[r['id']]['reason'],
                             'confirmed_error': False, 'note': 'AI复查提示；尚未对权威出版物逐字校勘。'})
    (HERE / 'retained_review_flags.json').write_text(json.dumps(flagged_rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    metrics['retained_flagged_units'] = len(flagged)
    metrics['retained_flagged_fraction'] = len(flagged) / 300
    metrics['retained_flags_are_not_verified_error_rate'] = True
    recoveries = metrics['recoverable_quarantine_ids']
    metrics['recovery_candidate_raw_characters_excluding_outer_whitespace'] = sum(len(packet[i]['text'].strip()) for i in recoveries)
    (HERE / 'review_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    text = ['# 数据清洗双智能体辅助审查记录', '',
            '日期：2026-11-07（北京时间）；数据版本：corpus_v1_20261107。', '',
            '本记录由两名分别使用独立上下文的AI审查代理逐项判断，再由主助手对分歧、疑似缺陷、不确定、低置信项目及全部高风险隔离项复核。'
            '这不是两名真人的人工评测，也没有人工金标准；独立上下文不保证模型判断误差统计独立。', '',
            '抽样规程在判读前固定，未按标签重抽样。保留正文采用简单随机无放回抽样，种子2026110701；'
            '排除内容采用简单随机无放回抽样，种子2026110702。', '',
            '| 评测项目 | 已复核分母 | AI仲裁后结果 | 未确定项 |',
            '| --- | ---: | --- | ---: |']
    metric_names = {'retained': '保留样本中应整段排除的噪声比例',
                    'excluded': '排除样本中误排主故事段落的比例',
                    'repair': '相对于缓存同章参考文本的修复支持率',
                    'quarantine': '仍有必要隔离的记录比例（隔离必要性审查）'}
    for kind, stat in metrics['counts'].items():
        text.append(f"| {metric_names[kind]} | {stat['n']} | {stat['reported_numerator']}/{stat['n']}（{percent(stat['observed_ai_label_rate'])}） | {stat['uncertain']} |")
    text += ['', f'保留正文总体为{sampling["retained_population"]:,}个清洁段落，抽样覆盖17本书。'
             f'排除内容总体为排除记录内{sampling["excluded_nonempty_line_population"]:,}条非空原始物理行；该总体不含单列章回结构标记、空行和乱码隔离段。'
             '段落比例不能解释为字符比例，也不合并为总体Accuracy或F1。', '',
             f'隔离16项的最终分类为：3项继续隔离、{len(recoveries)}项有据回收候选、2项待定。'
             f'候选原段共{metrics["recovery_candidate_raw_characters_excluding_outer_whitespace"]:,}字符（去段首尾空白）。'
             '这些项全部来自补充语料《儿女英雄传》，不直接影响仅金庸训练样本。回收候选尚未回写；原有16处断点仍保留。', '',
             f'另有{len(flagged)}/300段保留样本被至少一位AI标记为有待复查的字词、标点或其他局部问题（{percent(len(flagged)/300)}）。'
             '这些标记不是已经权威校勘确认的错误，也不自动意味着整段应被删除。详见retained_review_flags.json。', '',
             '| 初始独立判读 | 一致项/总项 | 原始一致率 | Cohen κ |', '| --- | ---: | ---: | --- |']
    for kind, stat in metrics['initial_agreement']['by_kind'].items():
        kappa = '不可定义（标签退化为单类）' if stat['cohen_kappa'] is None else f"{stat['cohen_kappa']:.4f}"
        text.append(f"| {TITLES[kind]} | {stat['agree']}/{stat['n']} | {percent(stat['raw_agreement'])} | {kappa} |")
    text += ['', f"全部449项初始原始一致率为{percent(metrics['initial_agreement']['overall_raw_agreement'])}。"
             '一致率衡量两位AI是否做出相同判定，不衡量其判定是否真实正确；κ受标签分布影响，不当作模型质量分数。', '',
             '初轮完成后，协调复查发现历史缓存HTML中的5段叶dd未被原只取p的参考抽取器收录。'
             '补充相同HTML证据后，两位审查者对Q009、Q011、Q012、Q013均认可为可回收候选，Q010仍有分歧。'
             '补充阶段一致4/5（80%），独立初轮的449项标签、一致率和分歧记录保持原样。', '',
             'Q016的共同“漏记”疑点经源码与逐位置重放核实后撤销：unresolved_positions只记录尚未定位的位置，'
             '不是总PUA位置；总4处已被统计，其中1处可定位但因全段隔离未应用。本项可回收建议仍成立。', '',
             '分歧项：' + ('、'.join(metrics['initial_agreement']['disagreement_ids']) or '无') + '。',
             '进入主助手复核的项目：' + ('、'.join(metrics['initial_agreement']['adjudication_required_ids']) or '无') + '。',
             '最终仍不确定：' + ('、'.join(metrics['unresolved_ids']) or '无') + '。',
             '最终建议有据回收的隔离项：' + ('、'.join(metrics['recoverable_quarantine_ids']) or '无') + '。', '']
    if (HERE / 'adjudication.jsonl').exists():
        decisions = rows(HERE / 'adjudication.jsonl')
        for d in decisions:
            item = packet[d['id']]
            text.append(f"- {d['id']}，{item['book']}，原始第{item['raw_line']}行：{d['final_label']}。{d['reason']}")
        text.append('')
    text += ['解读边界：', '',
             '- 样本内未发现不等于全语料错误率为零；不确定项没有从分母剔除。',
             '- 修复支持率不等于与三联版或其他出版物逐字一致的准确率；本轮未核验影印本。',
             '- 隔离合理性依赖当前可用参考和既定规则，不宣称不存在任何可恢复版本。',
             '- 本轮没有修改冻结语料、更新两张既有图或开始训练。训练效益仍需验证损失、困惑度和生成对照实验。', '',
             '审查过程可追溯文件：review_protocol.md、sampling_manifest.json、review_packet.jsonl、'
             'reviewer_a.jsonl、reviewer_b.jsonl、initial_agreement.json、adjudication.jsonl、final_labels.jsonl。', '',
             f"材料SHA-256：{sampling['packet_sha256']}",
             f"规程SHA-256：{sampling['protocol_sha256']}", '']
    (HERE / '数据清洗双智能体审查结果.md').write_text('\n'.join(text), encoding='utf-8')
    print(json.dumps({'report': str(HERE / '数据清洗双智能体审查结果.md'),
                      'retained_flagged_units': len(flagged), 'metrics': metrics['counts']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
