"""从真实GUI测试摘要生成进度表，未执行的场景明确列为未测试。"""
import csv
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
names={'home':'首页','browse':'帖子浏览','login':'登录','write':'发帖评论','like':'点赞'}
rows=[]
for path in sorted((ROOT/'performance/results').glob('gui_*/summary.json')):
    value=json.loads(path.read_text(encoding='utf-8'))
    if (path.parent/'audited-summary.json').exists():
        value=json.loads((path.parent/'audited-summary.json').read_text(encoding='utf-8'))
    if value.get('execution_mode')!='GUI':continue
    stable=value.get('stable',{})
    goals=bool(stable.get('mean_ms') is not None and stable['mean_ms']<=1000 and
               stable['p95_ms']<=2000 and stable['p99_ms']<=3000 and stable['error_rate']<.01)
    rows.append({'scene':value.get('scene','home'),'users':value['users'],
                 'requests':value['requests'],'success':value['success'],'failures':value['failures'],
                 'mean_ms':value['mean_ms'],'p90_ms':value['p90_ms'],'p95_ms':value['p95_ms'],'p99_ms':value['p99_ms'],
                 'rps':value['rps'],'error_rate':value['error_rate'],
                 'stable_requests':stable.get('requests'),'stable_mean_ms':stable.get('mean_ms'),
                 'stable_p95_ms':stable.get('p95_ms'),'stable_p99_ms':stable.get('p99_ms'),'stable_rps':stable.get('rps'),
                 'all_threads_alive_seconds':stable.get('all_threads_alive_seconds'),
                 'coverage_passed':stable.get('coverage_passed'),
                 'performance_goals_met':goals,
                 'data_checks_passed':value.get('data_checks',{}).get('passed'),
                 'html_created':(path.parent/'html/index.html').exists(),
                 'cpu_total_mean_percent':stable.get('cpu_total_percent_mean'),
                 'cpu_total_max_percent':stable.get('cpu_total_percent_max'),
                 'site_rss_mb_max':stable.get('site_rss_mb_max'),
                 'jmeter_rss_mb_max':stable.get('jmeter_rss_mb_max'),
                 'memory_available_mb_min':stable.get('memory_available_mb_min'),
                 'path':str(path.parent.relative_to(ROOT)).replace('\\','/')})
directory=ROOT/'docs'
with (directory/'GUI测试已执行指标.csv').open('w',encoding='utf-8-sig',newline='') as f:
    if rows:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
lines=['# JMeter可视化测试执行进度','',f'更新时间：{datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()}','',
       '按用户要求在真实JMeter中文图形界面配置并点击开始，聚合报告实时显示。GUI结果与此前命令行测试分别保存，不合并为同一次测试。只将已结束且有原始记录的结果列入下表。','',
       '| 场景 | 虚拟用户 | 请求数 | 失败 | 平均ms | P90 | P95 | P99 | RPS | 错误率 | 全部线程共同保持秒 |',
       '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
pause_state=json.loads((ROOT/'.runtime/gui-latest.json').read_text(encoding='utf-8'))
if pause_state.get('paused_by_user'):
    lines[4:4]=['当前已按用户要求暂停测试。浏览75用户出现连接被拒绝，本轮无效，未计入下表；见[JMeter测试异常分析](JMeter测试异常分析_20261116.md)。','']
for r in rows:
    lines.append(f"| {names[r['scene']]} | {r['users']} | {r['requests']} | {r['failures']} | {r['mean_ms']} | {r['p90_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['rps']} | {r['error_rate']:.2%} | {r['all_threads_alive_seconds']} |")
lines+=['','上表为含Ramp-up的全程请求统计。稳定区间指标、CPU和内存见同目录GUI测试已执行指标.csv及每轮summary.json；原始JTL、线程日志与资源CSV都在对应performance/results/gui_*目录。','',
        '## 计划覆盖情况','','| 场景 | 10 | 25 | 50 | 75 | 100 |','| --- | --- | --- | --- | --- | --- |']
for scene,label in names.items():
    states=[]
    for users in (10,25,50,75,100):
        selected=[r for r in rows if r['scene']==scene and r['users']==users]
        states.append('已执行' if selected else '未完成')
    lines.append('| '+label+' | '+' | '.join(states)+' |')
unmet=[r for r in rows if not r['performance_goals_met']]
if unmet:
    lines+=['','## 未达到性能目标的已执行轮次','',
            '目标按稳定阶段判断：平均响应≤1000ms、P95≤2000ms、P99≤3000ms、错误率<1%。请求成功与性能达标分别记录。','']
    for r in unmet:
        lines.append(f"- {names[r['scene']]} {r['users']}用户：稳定阶段平均{r['stable_mean_ms']}ms、P95 {r['stable_p95_ms']}ms、P99 {r['stable_p99_ms']}ms；不标记为全面通过。")
lines+=['','100用户必须全部线程至少共同保持300秒，不能将爬升时间计作稳定时间。超过100用户的压力测试尚未执行，仍需展示具体参数并另行确认。','',
        '界面显示整理：25用户运行时聚合报告曾保留上轮内存显示；结束后清空显示，再加载本轮独立JTL，确认2177请求与原始结果一致。没有删除或改写原始JTL。后续每轮启动前验证显示从0开始。','']
(directory/'JMeter可视化测试进度.md').write_text('\n'.join(lines),encoding='utf-8')
print({'completed_GUI_rounds':len(rows),'report':str(directory/'JMeter可视化测试进度.md')})
