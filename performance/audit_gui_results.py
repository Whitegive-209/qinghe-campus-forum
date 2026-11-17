"""保留原摘要，另存按原始线程日志和采样时间戳复核的摘要；不改测试指标。"""
import csv
import json
from pathlib import Path
from performance.analyze_run import analyze

ROOT=Path(__file__).resolve().parents[1]

def audit(directory):
    original=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    with (directory/'results.jtl').open(encoding='utf-8-sig',newline='') as f:samples=list(csv.DictReader(f))
    with (directory/'resources.csv').open(encoding='utf-8',newline='') as f:
        resources=[{k:float(v) for k,v in row.items()} for row in csv.DictReader(f)]
    updated=dict(original)
    updated['stable']=analyze(directory,samples,resources,original['users'],300 if original['users']==100 else 120)
    updated['load_requirement_met']=updated['stable']['coverage_passed']
    stable=updated['stable']
    updated['performance_goals_met']=bool(stable['mean_ms']<=1000 and stable['p95_ms']<=2000 and stable['p99_ms']<=3000 and stable['error_rate']<.01)
    updated['audit_note']='原始summary.json保留。仅修正把近似1秒采样点数当作线程持续时长的判断；JTL、日志、CPU采样、负载设置、响应时间、错误率和性能目标均未修改。'
    updated['passed']=updated['load_requirement_met'] and updated['performance_goals_met'] and updated['failures']==0
    (directory/'audited-summary.json').write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding='utf-8')
    print({'directory':directory.name,'load_requirement_met':updated['load_requirement_met'],'performance_goals_met':updated['performance_goals_met'],'sampling':stable['resource_sampling']})

if __name__=='__main__':
    for file in sorted((ROOT/'performance/results').glob('gui_*/summary.json')):audit(file.parent)
