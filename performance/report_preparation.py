"""读取已执行JMeter小流量记录，生成准备阶段报告与交付包。"""
import csv
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import zipfile

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'performance'
LABELS = {'home': '首页', 'browse': '帖子浏览', 'login': '登录', 'write': '发帖评论', 'like': '点赞'}


def main():
    candidates = sorted((P / 'results').glob('smoke_*/summary.json'))
    if not candidates:
        raise RuntimeError('没有实际小流量结果，不能生成报告。')
    smoke_path = candidates[-1]
    values = json.loads(smoke_path.read_text(encoding='utf-8'))
    if {r['scene'] for r in values} != set(LABELS) or not all(r['passed'] for r in values):
        raise RuntimeError('最近的调试未完整通过五类场景，请先检查。')
    now = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    lines = ['# 第四阶段：JMeter环境准备与小流量调试报告', '', f'整理时间：{now}', '',
             '## 本阶段结论', '',
             '已准备5份真实JMeter测试计划、200个独立合成账号CSV、独立MySQL性能库、结果保存和资源监控工具。五类场景各2用户1循环的调试均通过。仅确认脚本可执行，不代表100并发性能通过。', '',
             '环境：Windows / Python 3.14 / Django 5.2.19 / MySQL 8.0.41 / Apache JMeter 5.6.3 / Java 17.0.12。JMeter及网站和数据库在同一电脑，存在资源竞争。', '',
             '目标：http://127.0.0.1:8001；仅本机，独立数据库qinghe_forum_perf。演示网站8000端口及qinghe_forum库不参与本次调试。', '',
             '准备的初始数据：200账号、5分类、1000帖子、5000评论、999基础点赞。本次发帖场景新增2篇帖子、2条评论，按运行编号保留，未清库。', '',
             '## 五类场景实际结果（2用户、1循环、无阅读停顿）', '',
             '| 场景 | HTTP请求 | 成功 | 失败 | 平均ms | P90 | P95 | P99 | RPS | 错误率 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in values:
        lines.append(f"| {LABELS[r['scene']]} | {r['requests']} | {r['success']} | {r['failures']} | {r['mean_ms']} | {r['p90_ms']} | {r['p95_ms']} | {r['p99_ms']} | {r['rps']} | {r['error_rate']:.2%} |")
    lines += ['', f"合计{sum(r['requests'] for r in values)}个HTTP请求，失败{sum(r['failures'] for r in values)}个。各场景计入登录、CSRF准备等真实请求；不计虚构的业务事务样本。小样本分位数仅描述本次请求，不能据此判断稳定性或承载上限。", '',
              '结果口径：RPS按各场景第一条请求开始至最后一条完成统计；分位数按最近秩法。CPU/内存采样范围包括JMeter启动及HTML报告生成，不能直接当作稳定负载资源消耗。', '',
              '## 业务与数据校验', '',
              '登录对比返回的用户名与用户ID，每线程固定账号、独立Cookie。保留CSRF安全机制，使用动态Cookie令牌。', '',
              '发帖评论实际数据库核对：', '', '```json', json.dumps(next(r for r in values if r['scene']=='write')['data_checks'], ensure_ascii=False, indent=2), '```', '',
              '点赞实际数据库核对：', '', '```json', json.dumps(next(r for r in values if r['scene']=='like')['data_checks'], ensure_ascii=False, indent=2), '```', '',
              '## 定时与监控调试', '']
    for path in sorted((P / 'results').glob('load_*/home/summary.json')):
        run = json.loads((path.parent / 'run.json').read_text(encoding='utf-8'))
        if run['virtual_users'] != 2 or run['steady_seconds'] != 5:
            continue
        stats = json.loads(path.read_text(encoding='utf-8'))
        with (path.parent / 'resources.csv').open(encoding='utf-8') as f:
            resources = list(csv.DictReader(f))
        lines.append(f"- {path.parent.parent.name}：2用户、1秒Ramp-up+5秒稳定配置，{stats['requests']}请求、{stats['failures']}失败，定时正常结束。整机CPU峰值{stats['max_total_cpu_percent']}%，最低可用内存{stats['min_available_memory_mb']}MB（含启动与报告生成）。")
        if resources and 'db_Threads_connected' in resources[0]:
            lines.append('  已记录MySQL连接数、运行线程、慢查询计数和锁等待计数。')
    lines += ['', '发现并修复的监控问题：Windows虚拟环境启动器会创建真正的Python服务子进程。最初五场景的site进程CPU/RSS仅包含启动器，数据不完整，禁止用于网站进程占用分析。执行器已修正为合计网站进程树，并用额外2用户定时检查复核，原始记录未删除。此修正属于测量工具修正，不是网站性能优化。', '',
              '共享MySQL全局计数及进程资源可能受到其他项目影响。正式性能测试应对齐JTL时间戳、单独统计稳定区间，结合连接/锁等待差值判断；不能将全局计数直接归因于本论坛。', '',
              '## 文件与复现', '',
              '- [运行说明与术语](../performance/README.md)',
              '- [首页JMX](../performance/plans/home.jmx)',
              '- [浏览JMX](../performance/plans/browse.jmx)',
              '- [登录JMX](../performance/plans/login.jmx)',
              '- [发帖评论JMX](../performance/plans/write.jmx)',
              '- [点赞JMX](../performance/plans/like.jmx)',
              '- [合成测试账号CSV](../performance/data/accounts.csv)',
              '- [初始数据清单](../performance/data/manifest.json)', '']
    for r in values:
        rel = (smoke_path.parent / r['scene']).relative_to(ROOT).as_posix()
        lines.append(f"- {LABELS[r['scene']]}：[原始JTL](../{rel}/results.jtl)、[HTML报告](../{rel}/html/index.html)、[资源CSV](../{rel}/resources.csv)、[真实摘要](../{rel}/summary.json)。")
    lines += ['', '执行器默认smoke模式；所有JMX默认1用户1循环。独立CSV不含真实用户或数据库管理员密码，勿把它当作生产账号。运行参数、计划SHA256、CSV SHA256保存在每轮run.json中；新版本还记录运行前的数据表行数。', '',
              '## 后续状态', '',
              '| 项目 | 状态 |', '| --- | --- |',
              '| 环境、JMX、CSV、数据及少量用户调试 | 已完成 |',
              '| 10/25/50/75/100用户正式梯度 | 未测试 |',
              '| 100用户稳定5分钟 | 未测试 |',
              '| 超过100用户压力测试 | 未测试，必须另行确认具体参数 |',
              '| 根据性能瓶颈优化和同条件复测 | 未执行 |', '',
              '下一阶段按已确认的10/25/50/75/100梯度分别执行五种场景，100用户稳定时间5分钟。此前应单独预热，固定数据规模与参数，检查资源余量。超过100用户前，另行展示地址、线程数、Ramp-up、时长、场景及停止条件并等待确认。', '']
    report = ROOT / 'docs/JMeter准备与调试报告.md'
    report.write_text('\n'.join(lines), encoding='utf-8')
    archive = ROOT / 'deliverables' / ('JMeter准备与调试_' + datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S') + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for folder in ['performance', 'forum', 'campus', 'scripts', 'templates', 'static', 'docs', 'test-results']:
            for file in (ROOT / folder).rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts:
                    z.write(file, file.relative_to(ROOT).as_posix())
        for name in ['manage.py','README.md','requirements.txt','requirements-dev.txt','start.ps1','启动论坛.cmd','.gitignore']:
            z.write(ROOT / name, name)
    print(json.dumps({'报告': str(report), '交付包': str(archive), '调试请求': sum(r['requests'] for r in values)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
