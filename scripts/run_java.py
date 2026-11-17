"""Java版构建、功能测试和本机运行入口；密码仅由忽略的本地配置注入环境。"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
JAVA=Path(r'C:\Program Files\Java\jdk-17\bin\java.exe')
IDE_MAVEN=Path(r'F:\IntelliJ IDEA 2022.2.4\plugins\maven\lib\maven3\bin\mvn.cmd')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('build','test','serve'))
    parser.add_argument('--perf',action='store_true')
    parser.add_argument('--port',type=int)
    parser.add_argument('--seed-demo',action='store_true')
    args=parser.parse_args()
    env=os.environ.copy();env['JAVA_HOME']=str(JAVA.parents[1])
    if args.action!='build':
        config=json.loads((ROOT/'.runtime/java-mysql-config.json').read_text(encoding='utf-8'))
        env.update(FORUM_DB_USER=config['db_user'],FORUM_DB_PASSWORD=config['db_password'],FORUM_DB_PORT=str(config['db_port']))
    if args.action in ('build','test'):
        maven=shutil.which('mvn.cmd') or str(IDE_MAVEN)
        command=[maven,'-B','-f',str(ROOT/'java-backend/pom.xml')]
        settings=ROOT/'.runtime/maven-java-settings.xml'
        if settings.exists():command+=['-s',str(settings)]
        if args.action=='test':env['FORUM_RUN_DB_TESTS']='1';command+=['test']
        else:command+=['-DskipTests','package']
        code=subprocess.call(command,cwd=ROOT,env=env)
        if args.action=='test':
            destination=ROOT/'test-results'/('java_functional_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
            source=ROOT/'java-backend/target/surefire-reports'
            if source.exists():shutil.copytree(source,destination)
        return code
    port=args.port or (8081 if args.perf else 8080)
    if not 1024<=port<=65535:raise ValueError('端口必须为1024至65535。')
    env['FORUM_DATABASE']='qinghe_forum_java_perf' if args.perf else 'qinghe_forum_java'
    env['FORUM_PORT']=str(port)
    command=[str(JAVA),'-Xms128m','-Xmx512m','-jar',str(ROOT/'java-backend/target/campus-forum-2.0.0.jar')]
    if args.seed_demo:
        if args.perf:raise ValueError('性能库不能使用演示数据初始化。')
        demo_path=ROOT/'.runtime/java-demo-account.json'
        if not demo_path.exists():
            with demo_path.open('x',encoding='utf-8') as f:json.dump({'username':'java_demo','password':secrets.token_urlsafe(18)+'!Aa7'},f)
        env['FORUM_DEMO_PASSWORD']=json.loads(demo_path.read_text(encoding='utf-8'))['password']
        command+=['--forum.seed-demo=true']
    print(f'Java版启动：http://127.0.0.1:{port}，只连接{env["FORUM_DATABASE"]}。',flush=True)
    process=subprocess.Popen(command,cwd=ROOT,env=env)
    try:return process.wait()
    except KeyboardInterrupt:
        process.terminate();return process.wait(timeout=20)


if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError) as error:
        print('操作未完成：'+str(error),file=sys.stderr);sys.exit(1)
