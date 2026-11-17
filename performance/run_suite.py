"""执行已确认的25轮梯度；遇失败立即停止，不执行超过100用户的测试。"""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def main():
    suite = ROOT/'performance/results'/('suite_'+datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S'))
    suite.mkdir(parents=True, exist_ok=False)
    rounds = []
    config = [(10,10,120),(25,25,120),(50,50,120),(75,75,120),(100,60,300)]
    # 预热独立保存，不合并正式统计。
    print('单独预热：2用户，五类场景各1循环。', flush=True)
    result = subprocess.run([sys.executable,'performance/run_jmeter.py','--mode','smoke','--scene','all','--users','2','--ramp','1'], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    for users,ramp,steady in config:
        for scene in ['home','browse','login','write','like']:
            before = set((ROOT/'performance/results').glob('load_*'))
            entry = {'users':users,'ramp':ramp,'steady':steady,'scene':scene,'status':'running'}
            rounds.append(entry)
            (suite/'progress.json').write_text(json.dumps(rounds,ensure_ascii=False,indent=2),encoding='utf-8')
            print(f'正式梯度 {users} 用户 / {scene}，稳定 {steady} 秒',flush=True)
            result = subprocess.run([sys.executable,'performance/run_jmeter.py','--mode','load','--scene',scene,'--users',str(users),'--ramp',str(ramp),'--steady',str(steady)],cwd=ROOT)
            created = set((ROOT/'performance/results').glob('load_*'))-before
            entry.update(status='complete' if result.returncode==0 else 'failed',result_dirs=[str(p.relative_to(ROOT)) for p in created])
            (suite/'progress.json').write_text(json.dumps(rounds,ensure_ascii=False,indent=2),encoding='utf-8')
            if result.returncode:
                print('本轮未通过，已停止后续梯度。保留原始现场：'+str(suite),flush=True)
                raise SystemExit(result.returncode)
            time.sleep(5)
    print('25轮正式测试执行完成：'+str(suite),flush=True)


if __name__ == '__main__':
    main()
