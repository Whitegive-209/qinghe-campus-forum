"""从已结束的GUI原始JTL生成HTML；不启动网站或JMeter负载。"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
JAVA = Path(r'C:\Program Files\Java\jdk-17\bin\java.exe')
JMETER = Path(r'F:\JMeter\apache-jmeter-5.6.3\bin\ApacheJMeter.jar')


def render(directory):
    directory = directory.resolve()
    results = (ROOT / 'performance/results').resolve()
    if directory.parent != results or not directory.name.startswith('gui_'):
        raise RuntimeError('只处理本项目GUI测试目录。')
    if not (directory / 'summary.json').exists() or (directory / 'INVALID_RUN.json').exists():
        raise RuntimeError('缺少完成摘要或本轮已标记无效，不能生成有效成绩报告。')
    destination = directory / 'html'
    if destination.exists():
        print(json.dumps({'directory': directory.name, 'skipped': True,
                          '原因': '已有HTML目录，保留原文件不覆盖。'}, ensure_ascii=False), flush=True)
        return
    jtl = directory / 'results.jtl'
    before = hashlib.sha256(jtl.read_bytes()).hexdigest()
    suffix = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S_%f')
    generation_log = directory / f'html-generation-{suffix}.log'
    command = [str(JAVA), '-Xmx512m', '-jar', str(JMETER), '-g', str(jtl),
               '-o', str(destination), '-j', str(generation_log)]
    with (directory / f'html-generation-console-{suffix}.log').open('x', encoding='utf-8') as output:
        subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                       timeout=120, check=True)
    if not (destination / 'index.html').exists():
        raise RuntimeError('JMeter没有生成HTML入口。')
    if hashlib.sha256(jtl.read_bytes()).hexdigest() != before:
        raise RuntimeError('原始JTL发生变化，停止。')
    evidence = {'created_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                'source_jtl_sha256': before, 'source_unchanged': True,
                'execution': 'JMeter -g: offline report only; no load',
                'generation_log': str(generation_log),
                'html': str(destination / 'index.html')}
    for filename in ('gui-plan.jmx', 'plan.jmx'):
        plan = directory / filename
        if plan.exists():
            evidence[filename + '_sha256'] = hashlib.sha256(plan.read_bytes()).hexdigest()
    (directory / 'html-evidence.json').write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'directory': directory.name, 'html_created': True}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directories', nargs='*', type=Path)
    args = parser.parse_args()
    targets = args.directories or sorted(p.parent for p in (ROOT/'performance/results').glob('gui_*/summary.json'))
    for target in targets:
        render(target)
