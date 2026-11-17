"""本机JMeter执行器。默认小流量调试；最多100用户，不包含压力测试许可。"""
import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from zoneinfo import ZoneInfo

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
JAVA = Path(r'C:\Program Files\Java\jdk-17\bin\java.exe')
JMETER = Path(r'F:\JMeter\apache-jmeter-5.6.3\bin\ApacheJMeter.jar')
SCENES = ['home', 'browse', 'login', 'write', 'like']


def percentile(values, q):
    values = sorted(values)
    return values[max(0, math.ceil(q * len(values)) - 1)] if values else None


def summary(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise RuntimeError('JTL无样本，测试不成立。')
    times = [int(r['elapsed']) for r in rows]
    start = min(int(r['timeStamp']) for r in rows)
    end = max(int(r['timeStamp']) + int(r['elapsed']) for r in rows)
    failures = [r for r in rows if r['success'] != 'true']
    return rows, {'requests': len(rows), 'success': len(rows)-len(failures), 'failures': len(failures),
                  'mean_ms': round(sum(times)/len(times), 2), 'p90_ms': percentile(times, .90),
                  'p95_ms': percentile(times, .95), 'p99_ms': percentile(times, .99),
                  'rps': round(len(rows)/max((end-start)/1000, .001), 3),
                  'error_rate': len(failures)/len(rows), 'sample_start_ms': start, 'sample_end_ms': end,
                  'peak_active_threads': max(int(r['grpThreads']) for r in rows),
                  'labels': dict(Counter(r['label'] for r in rows)),
                  'failure_details': [{k: r.get(k) for k in ['label','responseCode','responseMessage','failureMessage']} for r in failures[:20]]}


def verify_data(scene, run_id, rows):
    os.environ['FORUM_DATABASE'] = 'qinghe_forum_perf'
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus.settings')
    import django
    django.setup()
    from django.db.models import Count
    from forum.models import Post, Comment, PostLike
    checks = {}
    if scene == 'write':
        expected_posts = sum(r['label'] == '发帖-提交' and r['success'] == 'true' for r in rows)
        expected_comments = sum(r['label'] == '评论-提交' and r['success'] == 'true' for r in rows)
        prefix = 'JM-' + run_id + '-'
        posts = Post.objects.filter(title__startswith=prefix)
        comments = Comment.objects.filter(body__startswith=prefix)
        duplicates = posts.values('title').annotate(n=Count('id')).filter(n__gt=1).count()
        bad_authors = sum(not p.title.startswith(prefix + str(int(p.author.username.split('_')[-1])-1) + '-') for p in posts.select_related('author'))
        bad_comments = sum(c.body != c.post.title + ' 评论' or c.author_id != c.post.author_id for c in comments.select_related('post'))
        checks = {'expected_posts': expected_posts, 'stored_posts': posts.count(), 'expected_comments': expected_comments,
                  'stored_comments': comments.count(), 'duplicate_titles': duplicates, 'wrong_authors': bad_authors,
                  'wrong_comment_relations': bad_comments}
        checks['passed'] = expected_posts > 0 and expected_posts == checks['stored_posts'] and expected_comments == checks['stored_comments'] and not (duplicates or bad_authors or bad_comments)
    elif scene == 'like':
        manifest = json.loads((ROOT / 'performance/data/manifest.json').read_text(encoding='utf-8'))
        with (ROOT / 'performance/data/accounts.csv').open(encoding='utf-8', newline='') as f:
            accounts = list(csv.DictReader(f))
        expected = set()
        touched = set()
        for row in rows:
            if row['success'] == 'true' and row['label'] in ('点赞', '重复点赞', '取消点赞'):
                user_id = int(accounts[int(row['threadName'].rsplit('-', 1)[1])-1]['user_id'])
                touched.add(user_id)
                if row['label'] == '取消点赞':
                    expected.discard(user_id)
                else:
                    expected.add(user_id)
        actual = set(PostLike.objects.filter(post_id=manifest['target_post']).values_list('user_id', flat=True))
        duplicates = PostLike.objects.values('post_id','user_id').annotate(n=Count('id')).filter(n__gt=1).count()
        checks = {'expected_target_likes': len(expected), 'stored_target_likes': len(actual),
                  'mismatched_user_ids': sorted(expected.symmetric_difference(actual)),
                  'duplicate_user_post_pairs': duplicates, 'passed': expected == actual and duplicates == 0,
                  '说明': '定时结束可能停在点赞后、取消前，按各用户最后成功的操作核对数据库，不将尚未发出的取消请求误报为失败。'}
    else:
        checks = {'passed': True, '说明': '页面与身份断言见JTL；本场景无业务数据写入核对。'}
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', choices=SCENES+['all'], default='all')
    parser.add_argument('--mode', choices=['smoke', 'load'], default='smoke')
    parser.add_argument('--users', type=int, default=2)
    parser.add_argument('--ramp', type=int, default=1)
    parser.add_argument('--steady', type=int, default=120)
    args = parser.parse_args()
    if not (1 <= args.users <= 100) or args.ramp < 1 or args.steady < 1:
        parser.error('仅允许1至100用户，Ramp-up和稳定时间需为正数。超过100用户必须另行确认。')
    for name in ['functional-results.json', 'browser-results.json']:
        if not json.loads((ROOT / 'test-results' / name).read_text(encoding='utf-8'))['成功']:
            raise RuntimeError('功能测试尚未通过，禁止进入JMeter测试。')
    accounts = ROOT / 'performance/data/accounts.csv'
    if not accounts.exists():
        raise RuntimeError('缺少测试数据，请先运行seed_perf。')
    run_root = ROOT / 'performance/results' / (args.mode + '_' + datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S'))
    run_root.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env['FORUM_DATABASE'] = 'qinghe_forum_perf'
    env['PYTHONUTF8'] = '1'
    # 不复用未知服务；绑定冲突时退出，不会结束其他进程。
    with socket.socket() as s:
        s.bind(('127.0.0.1', 8001))
    server_out = (run_root / 'site.log').open('w', encoding='utf-8')
    server = subprocess.Popen([sys.executable, str(ROOT / 'scripts/serve.py'), '--port', '8001'], cwd=ROOT, env=env, stdout=server_out, stderr=subprocess.STDOUT)
    results = []
    process = None
    import MySQLdb
    config = json.loads((ROOT / '.runtime/mysql-config.json').read_text(encoding='utf-8'))
    db = None
    try:
        db = MySQLdb.connect(host='127.0.0.1', port=config['db_port'], user=config['db_user'], passwd=config['db_password'],
                             db='qinghe_forum_perf', charset='utf8mb4', connect_timeout=5)
        db.autocommit(True)
        for attempt in range(30):
            if server.poll() is not None:
                raise RuntimeError('性能网站未启动，请查看site.log。')
            try:
                with urlopen('http://127.0.0.1:8001/health/', timeout=1) as r:
                    if json.load(r)['status'] == 'ok':
                        break
            except OSError:
                time.sleep(.5)
        else:
            raise RuntimeError('性能网站未就绪。')
        for scene in (SCENES if args.scene == 'all' else [args.scene]):
            directory = run_root / scene
            directory.mkdir()
            run_id = run_root.name + '_' + scene
            plan = ROOT / 'performance/plans' / (scene + '.jmx')
            params = {'users': args.users, 'ramp': args.ramp, 'port': 8001, 'accounts': accounts,
                      'run_id': run_id, 'think': 0 if args.mode == 'smoke' else 1000,
                      'jitter': 0 if args.mode == 'smoke' else 1000,
                      'loops': 1 if args.mode == 'smoke' else -1,
                      'scheduled': 'false' if args.mode == 'smoke' else 'true',
                      'duration': args.ramp + args.steady + (3 if args.mode == 'load' else 0),
                      'CookieManager.save.cookies': 'true', 'jmeter.save.saveservice.output_format': 'csv',
                      'jmeter.save.saveservice.thread_counts': 'true',
                      'jmeter.save.saveservice.assertion_results_failure_message': 'true',
                      'jmeterengine.nongui.port': 55445, 'jmeterengine.nongui.maxport': 55445}
            command = [str(JAVA), '-Xms256m', '-Xmx768m', '-jar', str(JMETER), '-n', '-t', str(plan),
                       '-l', str(directory / 'results.jtl'), '-j', str(directory / 'jmeter.log'), '-e', '-o', str(directory / 'html')]
            command += [f'-J{k}={v}' for k, v in params.items()]
            meta = {'scene': scene, 'mode': args.mode, 'virtual_users': args.users, 'ramp_seconds': args.ramp,
                    'steady_seconds': args.steady if args.mode == 'load' else None, 'url': 'http://127.0.0.1:8001',
                    'database': 'qinghe_forum_perf', 'parameters': {k: str(v) for k,v in params.items()},
                    'plan_sha256': hashlib.sha256(plan.read_bytes()).hexdigest(),
                    'accounts_sha256': hashlib.sha256(accounts.read_bytes()).hexdigest(),
                    'started': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
            meta['schedule_guard_seconds'] = 3 if args.mode == 'load' else 0
            with db.cursor() as cursor:
                counts = {}
                for table in ['forum_user', 'forum_post', 'forum_comment', 'forum_postlike']:
                    cursor.execute('SELECT COUNT(*) FROM ' + table)
                    counts[table] = cursor.fetchone()[0]
                meta['baseline_counts'] = counts
            (directory / 'run.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'开始 {scene}：{args.users}用户，{args.mode}，结果 {directory}', flush=True)
            with (directory / 'console.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                java_process, site_process = psutil.Process(process.pid), psutil.Process(server.pid)
                owned = {'jmeter': [java_process] + java_process.children(recursive=True),
                         'site': [site_process] + site_process.children(recursive=True)}
                owned.update({f'mysql_{p.pid}': [p] for p in psutil.process_iter() if p.name().lower() == 'mysqld.exe'})
                psutil.cpu_percent()
                for processes in owned.values():
                    for p in processes:
                        p.cpu_percent()
                resource_rows = []
                danger = 0
                timeout = 120 if args.mode == 'smoke' else args.ramp + args.steady + 123
                deadline = time.monotonic() + timeout
                live_offset, live_buffer, live_header = 0, '', None
                live_recent = []
                with (directory / 'resources.csv').open('w', encoding='utf-8', newline='') as f:
                    writer = None
                    while process.poll() is None:
                        mem = psutil.virtual_memory()
                        row = {'timestamp_ms': int(time.time()*1000), 'cpu_total_percent': psutil.cpu_percent(),
                               'memory_used_percent': mem.percent, 'memory_available_mb': round(mem.available/2**20, 2)}
                        with db.cursor() as cursor:
                            cursor.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Slow_queries','Innodb_row_lock_current_waits','Innodb_row_lock_waits','Innodb_row_lock_time','Aborted_connects','Connections')")
                            row.update({'db_'+key: int(value) for key, value in cursor.fetchall()})
                        for label, processes in owned.items():
                            cpu, rss = 0, 0
                            for p in processes:
                                try:
                                    cpu += p.cpu_percent()/psutil.cpu_count()
                                    rss += p.memory_info().rss/2**20
                                except psutil.Error:
                                    pass
                            row[label+'_cpu_percent'], row[label+'_rss_mb'] = round(cpu, 3), round(rss, 3)
                        if writer is None:
                            writer = csv.DictWriter(f, fieldnames=list(row))
                            writer.writeheader()
                        writer.writerow(row)
                        f.flush()
                        resource_rows.append(row)
                        jtl = directory / 'results.jtl'
                        if jtl.exists():
                            with jtl.open(encoding='utf-8', newline='') as current:
                                current.seek(live_offset)
                                live_buffer += current.read()
                                live_offset = current.tell()
                            complete = live_buffer.split('\n')
                            live_buffer = complete.pop()
                            for line in complete:
                                fields = next(csv.reader([line]))
                                if live_header is None:
                                    live_header = fields
                                elif len(fields) == len(live_header):
                                    sample = dict(zip(live_header, fields))
                                    live_recent.append((int(sample['timeStamp']), sample['success'] == 'true'))
                            cutoff = int(time.time()*1000)-30000
                            live_recent = [item for item in live_recent if item[0] >= cutoff]
                        error_alarm = len(live_recent) >= 20 and sum(not ok for _, ok in live_recent)/len(live_recent) > .05
                        danger = danger+1 if row['cpu_total_percent'] > 90 or mem.available < 1024**3 else 0
                        if danger >= 30 or error_alarm or psutil.disk_usage(str(ROOT)).free < 5*1024**3 or time.monotonic() > deadline:
                            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                                sock.sendto(b'Shutdown', ('127.0.0.1', 55445))
                            try:
                                process.wait(timeout=20)
                            except subprocess.TimeoutExpired:
                                process.terminate()
                                process.wait(timeout=10)
                            raise RuntimeError('达到资源/错误率安全阈值或执行超时，已停止本次JMeter进程。')
                        time.sleep(1)
            if process.returncode != 0:
                raise RuntimeError('JMeter进程失败，请查看本轮console.log。')
            rows, stats = summary(directory / 'results.jtl')
            data = verify_data(scene, run_id, rows)
            stats['data_checks'] = data
            stats['resource_samples'] = len(resource_rows)
            stats['max_total_cpu_percent'] = max(r['cpu_total_percent'] for r in resource_rows)
            stats['min_available_memory_mb'] = min(r['memory_available_mb'] for r in resource_rows)
            stats['html_report_created'] = (directory / 'html/index.html').exists()
            stats['passed'] = stats['failures'] == 0 and data['passed'] and stats['html_report_created'] and (args.mode == 'smoke' or stats['peak_active_threads'] == args.users)
            stats['scene'] = scene
            if args.mode == 'load':
                from performance.analyze_run import analyze
                stats['stable'] = analyze(directory, rows, resource_rows, args.users, args.steady)
                stats['passed'] = stats['passed'] and stats['stable']['coverage_passed']
            (directory / 'summary.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
            results.append(stats)
            (run_root / 'summary.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'scene': scene, 'requests': stats['requests'], 'failures': stats['failures'], 'passed': stats['passed']}, ensure_ascii=False), flush=True)
            if not stats['passed']:
                raise RuntimeError('场景校验失败，停止后续测试，请先修复或检查。')
    finally:
        if process is not None and process.poll() is None:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(b'Shutdown', ('127.0.0.1', 55445))
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        server.terminate()
        server.wait(timeout=15)
        if db is not None:
            db.close()
        server_out.close()
    print('全部场景已结束：' + str(run_root), flush=True)


if __name__ == '__main__':
    main()
