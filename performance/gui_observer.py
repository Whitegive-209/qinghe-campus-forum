"""仅启动独立网站并记录GUI测试资源；不通过命令行发起任何负载。"""
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from zoneinfo import ZoneInfo
import psutil
import MySQLdb
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from performance.run_jmeter import summary, verify_data
from performance.analyze_run import analyze

users = int(sys.argv[1]) if len(sys.argv)>1 else 10
scene = sys.argv[2] if len(sys.argv)>2 else 'home'
steady = 300 if users == 100 else 120
if users not in (10,25,50,75,100) or scene not in ('home','browse','login','write','like'):
    raise SystemExit('仅允许已确认的五档负载与五类场景。')
directory = ROOT/'performance/results'/('gui_'+scene+str(users)+'_'+datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S'))
directory.mkdir(parents=True, exist_ok=False)
latest = {'directory':str(directory),'jtl':str(directory/'results.jtl'),'users':users,'mode':'GUI','port':8001,
          'database':'qinghe_forum_perf','observer_pid':os.getpid(),
          'observer_created':psutil.Process().create_time()}
latest.update(scene=scene,steady_seconds=steady,ramp_seconds=60 if users==100 else users)
def publish_state(status):
    latest.update(status=status, heartbeat_epoch=time.time())
    state_path=ROOT/'.runtime/gui-latest.json'
    pending=state_path.with_suffix('.pending.json')
    pending.write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf-8')
    pending.replace(state_path)

publish_state('starting')
print(json.dumps(latest,ensure_ascii=False),flush=True)
config=json.loads((ROOT/'.runtime/mysql-config.json').read_text(encoding='utf-8'))
db=MySQLdb.connect(host='127.0.0.1',port=config['db_port'],user=config['db_user'],passwd=config['db_password'],db='qinghe_forum_perf',charset='utf8mb4')
db.autocommit(True)
with db.cursor() as c:
    latest['baseline_counts']={}
    for table in ('forum_user','forum_post','forum_comment','forum_postlike'):
        c.execute('SELECT COUNT(*) FROM '+table)
        latest['baseline_counts'][table]=c.fetchone()[0]
(directory/'run.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding='utf-8')
env=os.environ.copy(); env['FORUM_DATABASE']='qinghe_forum_perf'; env['PYTHONUTF8']='1'
out=(directory/'site.log').open('w',encoding='utf-8')
server=subprocess.Popen([sys.executable,'scripts/serve.py','--port','8001'],cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
gui_log=ROOT/'jmeter-gui.log'
offset=gui_log.stat().st_size
records=[]; logs=[]; starts=0; ends=0; danger=0
try:
    time.sleep(2)
    if server.poll() is not None: raise RuntimeError('8001服务启动失败，请查看site.log。')
    with urlopen('http://127.0.0.1:8001/health/',timeout=3) as response:
        if response.status!=200:raise RuntimeError('8001健康检查失败。')
    latest.update(server_pid=server.pid,server_created=psutil.Process(server.pid).create_time())
    roots=[p for p in psutil.process_iter() if p.name().lower()=='javaw.exe' and any('ApacheJMeter.jar' in a for a in p.cmdline())]
    if len(roots)!=1: raise RuntimeError('无法唯一识别可视化JMeter进程。')
    site=psutil.Process(server.pid)
    watched={'jmeter':roots,'site':[site]+site.children(recursive=True)}
    watched.update({f'mysql_{p.pid}':[p] for p in psutil.process_iter() if p.name().lower()=='mysqld.exe'})
    for group in watched.values():
        for p in group:p.cpu_percent()
    psutil.cpu_percent()
    publish_state('ready')
    print('网站和监控已就绪，请在JMeter界面点击运行。',flush=True)
    with (directory/'resources.csv').open('w',encoding='utf-8',newline='') as f:
        writer=None
        deadline=time.monotonic()+3600
        test_clock_started=False
        while time.monotonic()<deadline:
            if server.poll() is not None:raise RuntimeError('独立网站已停止，本轮不能继续。')
            with gui_log.open(encoding='utf-8',errors='replace') as g:
                g.seek(offset); part=g.read();offset=g.tell()
            if part:
                logs.append(part); starts+=part.count('Thread started:'); ends+=part.count('Thread finished:')
                (directory/'jmeter.log').write_text(''.join(logs),encoding='utf-8')
                if starts and not test_clock_started:
                    # 等待用户查看和配置GUI的时间，不能消耗正式测试的调度时间。
                    deadline=time.monotonic()+latest['ramp_seconds']+steady+123
                    test_clock_started=True
            publish_state('running' if test_clock_started else 'ready')
            m=psutil.virtual_memory()
            row={'timestamp_ms':int(time.time()*1000),'cpu_total_percent':psutil.cpu_percent(),'memory_used_percent':m.percent,'memory_available_mb':round(m.available/2**20,2)}
            for label,group in watched.items():
                cpu=rss=0
                for p in group:
                    try:cpu+=p.cpu_percent()/psutil.cpu_count();rss+=p.memory_info().rss/2**20
                    except psutil.Error:pass
                row[label+'_cpu_percent']=round(cpu,3);row[label+'_rss_mb']=round(rss,3)
            with db.cursor() as c:
                c.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected','Threads_running','Slow_queries','Innodb_row_lock_current_waits','Innodb_row_lock_waits','Innodb_row_lock_time','Aborted_connects','Connections')")
                row.update({'db_'+k:int(v) for k,v in c.fetchall()})
            if writer is None:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader()
            writer.writerow(row);f.flush();records.append(row)
            danger=danger+1 if row['cpu_total_percent']>90 or m.available<1024**3 else 0
            if danger>=30:
                (directory/'STOP_REQUIRED.txt').write_text('资源接近安全上限，请立即在JMeter界面停止测试。',encoding='utf-8')
                print('需要立即停止：资源达到安全阈值。',flush=True)
                raise RuntimeError('资源达到安全阈值，停止本项目独立网站以降低负载；本轮保留为中止记录。')
            if starts and ends>=users:break
            time.sleep(1)
    if starts!=users or ends!=users:raise RuntimeError('线程未完整运行，不能宣称测试完成。')
    time.sleep(2)
    rows,stats=summary(directory/'results.jtl')
    stats['stable']=analyze(directory,rows,records,users,steady)
    stats['execution_mode']='GUI';stats['users']=users
    stats['scene']=scene
    stats['data_checks']=verify_data(scene,directory.name,rows)
    stable=stats['stable']
    stats['load_requirement_met']=stable['coverage_passed']
    stats['performance_goals_met']=bool(stable.get('mean_ms') is not None and
        stable['mean_ms']<=1000 and stable['p95_ms']<=2000 and
        stable['p99_ms']<=3000 and stable['error_rate']<.01)
    stats['passed']=(stats['failures']==0 and stats['load_requirement_met'] and
                     stats['performance_goals_met'] and stats['data_checks']['passed'])
    (directory/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False),flush=True)
    if not stats['passed']:raise RuntimeError('本轮未通过，禁止继续提高负载。')
finally:
    publish_state('closed')
    server.terminate();server.wait(timeout=15);out.close();db.close()
