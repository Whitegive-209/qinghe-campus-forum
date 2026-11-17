"""仅新建Java版独立数据库。管理员密码只在本机输入，不保存。"""
import getpass
import json
from pathlib import Path
import secrets
import sys

import MySQLdb

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / '.runtime/java-mysql-config.json'
DATABASES = ('qinghe_forum_java', 'qinghe_forum_java_perf', 'test_qinghe_forum_java')
APP_USER = 'qinghe_java_app'


def check():
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    with MySQLdb.connect(host='127.0.0.1', port=config['db_port'],
                         user=config['db_user'], passwd=config['db_password'],
                         db=DATABASES[0], charset='utf8mb4', connect_timeout=5) as db:
        with db.cursor() as cursor:
            cursor.execute('SELECT VERSION(), DATABASE()')
            print('Java独立数据库连接正常：', cursor.fetchone(), flush=True)


def initialize():
    if CONFIG.exists():
        print('Java配置已存在，只检查连接，不覆盖。', flush=True)
        check()
        return
    print('=== 青禾校园 Java版：新建独立MySQL数据库 ===', flush=True)
    print('保留Python数据库。只新建：' + ' / '.join(DATABASES), flush=True)
    print('管理员密码输入不显示，不保存。', flush=True)
    admin = input('管理员用户名 [root]：').strip() or 'root'
    port = int(input('端口 [3306]：').strip() or '3306')
    password = getpass.getpass('MySQL管理员密码：')
    app_password = secrets.token_urlsafe(32)
    with MySQLdb.connect(host='127.0.0.1', port=port, user=admin, passwd=password,
                         charset='utf8mb4', connect_timeout=5) as db:
        db.autocommit(True)
        with db.cursor() as cursor:
            cursor.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME IN (%s,%s,%s)', DATABASES)
            if cursor.fetchall():
                raise RuntimeError('发现同名数据库，已停止；不会覆盖或清空。')
            cursor.execute('SELECT User FROM mysql.user WHERE User=%s', (APP_USER,))
            if cursor.fetchone():
                raise RuntimeError('发现同名账号，已停止；不会更改账号。')
            for name in DATABASES:
                cursor.execute(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs')
            cursor.execute("CREATE USER %s@'127.0.0.1' IDENTIFIED BY %s", (APP_USER, app_password))
            for name in DATABASES:
                cursor.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE,CREATE,ALTER,INDEX,REFERENCES,DROP ON `{name}`.* TO %s@'127.0.0.1'", (APP_USER,))
    password = None
    CONFIG.parent.mkdir(exist_ok=True)
    config = {'db_user': APP_USER, 'db_password': app_password,
              'db_name': DATABASES[0], 'db_port': port}
    with CONFIG.open('x', encoding='utf-8') as output:
        json.dump(config, output, ensure_ascii=False, indent=2)
    check()
    print('初始化完成，可以关闭窗口；开发助手会继续建表与验证。', flush=True)


if __name__ == '__main__':
    try:
        check() if len(sys.argv)>1 and sys.argv[1]=='check' else initialize()
    except (Exception, KeyboardInterrupt) as exc:
        print('未完成：'+str(exc), file=sys.stderr, flush=True)
        print('未执行清库；如新建中途失败，请保留现场，不重复覆盖。', flush=True)
        sys.exit(1)
