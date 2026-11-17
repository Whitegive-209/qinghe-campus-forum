"""交互输入本机MySQL管理员密码，只创建本项目命名空间，不保存管理员密码。"""
import getpass
import json
from pathlib import Path
import secrets
import sys

import MySQLdb

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
CONFIG = RUNTIME / 'mysql-config.json'
DATABASES = ('qinghe_forum', 'qinghe_forum_perf', 'test_qinghe_forum')
APP_USER = 'qinghe_forum_app'


def check():
    if not CONFIG.exists():
        raise RuntimeError('尚未配置。请运行 .venv\\Scripts\\python.exe scripts\\setup_mysql.py init')
    c = json.loads(CONFIG.read_text(encoding='utf-8'))
    with MySQLdb.connect(host='127.0.0.1', port=c['db_port'], user=c['db_user'],
                         passwd=c['db_password'], db=c['db_name'], charset='utf8mb4', connect_timeout=5) as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION(), DATABASE(), @@default_storage_engine')
            version, name, engine = cursor.fetchone()
    print(f'MySQL连接正常：版本 {version}，数据库 {name}，默认存储引擎 {engine}。', flush=True)


def initialize():
    RUNTIME.mkdir(exist_ok=True)
    if CONFIG.exists():
        print('已有本项目MySQL配置，将只检查连接，不覆盖配置或数据库。')
        check()
        return
    print('=== 青禾校园论坛：MySQL一次性初始化 ===', flush=True)
    print('仅连接本机；密码输入时不会显示，也不会保存管理员密码。', flush=True)
    print('将新建 qinghe_forum / qinghe_forum_perf，授权专用账号访问它们及隔离测试库。', flush=True)
    admin = input('MySQL管理员用户名 [root]：').strip() or 'root'
    port = int(input('MySQL端口 [3306]：').strip() or '3306')
    password = getpass.getpass('请输入MySQL管理员密码（输入不显示）：')
    app_password = secrets.token_urlsafe(32)
    with MySQLdb.connect(host='127.0.0.1', port=port, user=admin, passwd=password,
                         charset='utf8mb4', connect_timeout=5) as conn:
        conn.autocommit(True)
        with conn.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            if tuple(int(p) for p in version.split('-')[0].split('.')[:3]) < (8, 0, 11):
                raise RuntimeError('本项目需要MySQL 8.0.11或更高版本。')
            cursor.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME IN (%s,%s,%s)', DATABASES)
            if cursor.fetchall():
                raise RuntimeError('检测到同名数据库，已停止，未覆盖。请联系开发助手检查。')
            cursor.execute('SELECT User FROM mysql.user WHERE User=%s', (APP_USER,))
            if cursor.fetchone():
                raise RuntimeError('检测到同名数据库账号，已停止，未修改。请联系开发助手检查。')
            # 所有标识符均为上方固定常量；密码使用驱动参数传递。
            for name in DATABASES[:2]:
                cursor.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs')
            cursor.execute("CREATE USER %s@'127.0.0.1' IDENTIFIED BY %s", (APP_USER, app_password))
            for name in DATABASES:
                cursor.execute(f"GRANT ALL PRIVILEGES ON `{name}`.* TO %s@'127.0.0.1'", (APP_USER,))
    password = None
    c = {'secret_key': secrets.token_urlsafe(64), 'db_user': APP_USER, 'db_password': app_password,
         'db_name': DATABASES[0], 'db_port': port, 'server_version': version}
    CONFIG.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding='utf-8')
    check()
    print('初始化完成。可以关闭本窗口，开发助手将继续建立数据表并测试。', flush=True)


if __name__ == '__main__':
    try:
        action = sys.argv[1] if len(sys.argv) > 1 else 'check'
        if action == 'init':
            initialize()
        elif action == 'check':
            check()
        else:
            raise RuntimeError('支持 init 或 check。')
    except (Exception, KeyboardInterrupt) as exc:
        print(f'未完成：{exc}', file=sys.stderr, flush=True)
        print('没有执行清库操作。如初始化中途失败，请保留现场供检查。', file=sys.stderr)
        raise SystemExit(1)
