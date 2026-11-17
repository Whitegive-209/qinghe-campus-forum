"""在项目目录初始化独立的PostgreSQL实例；不会安装或修改系统服务。"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
TOOLS = ROOT / '.tools'
PG = TOOLS / 'pgsql' / 'bin'
DATA = RUNTIME / 'pgdata'


def config():
    RUNTIME.mkdir(exist_ok=True)
    path = RUNTIME / 'config.json'
    if not path.exists():
        value = {'secret_key': secrets.token_urlsafe(64), 'db_user': 'campus_app',
                 'db_password': secrets.token_urlsafe(32), 'owner_password': secrets.token_urlsafe(32),
                 'db_port': 55432}
        path.write_text(json.dumps(value, indent=2), encoding='utf-8')
    return json.loads(path.read_text(encoding='utf-8'))


def run(args, **kwargs):
    subprocess.run([str(item) for item in args], check=True, cwd=ROOT, **kwargs)


def start():
    c = config()
    status = subprocess.run([str(PG / 'pg_ctl.exe'), '-D', str(DATA), 'status'], capture_output=True)
    if status.returncode == 0:
        print('项目数据库已运行。')
        return
    run([PG / 'pg_ctl.exe', '-D', DATA, '-l', RUNTIME / 'postgresql.log', '-w', '-t', '30', 'start'])


def initialize():
    c = config()
    archive = TOOLS / 'postgresql-17.12-1-windows-x64-binaries.zip'
    if not (PG / 'initdb.exe').exists():
        print('解压PostgreSQL官方便携包（只提取运行数据库所需文件）…', flush=True)
        digest = hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest()
        (TOOLS / 'postgresql-download-sha256.txt').write_text(digest + '\n', encoding='utf-8')
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                destination = (TOOLS / member.filename).resolve()
                if not destination.is_relative_to(TOOLS.resolve()):
                    raise ValueError('压缩包包含不安全路径。')
                if member.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/')):
                    z.extract(member, TOOLS)
    if not (DATA / 'PG_VERSION').exists():
        password_file = RUNTIME / 'init-password.tmp'
        password_file.write_text(c['owner_password'], encoding='utf-8')
        try:
            run([PG / 'initdb.exe', '-D', DATA, '-U', 'campus_owner', '--encoding=UTF8', '--locale=C',
                 '--auth=scram-sha-256', '--pwfile', password_file])
        finally:
            password_file.unlink(missing_ok=True)
        with (DATA / 'postgresql.conf').open('a', encoding='utf-8') as f:
            f.write("\n# 本项目专用，限本机访问\nlisten_addresses = '127.0.0.1'\nport = 55432\nmax_connections = 60\nshared_buffers = '128MB'\nlog_min_duration_statement = 500\n")
    start()
    import psycopg
    from psycopg import sql
    with psycopg.connect(host='127.0.0.1', port=c['db_port'], dbname='postgres',
                         user='campus_owner', password=c['owner_password'], autocommit=True) as conn:
        if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (c['db_user'],)).fetchone():
            # CREATEDB仅供本地Django隔离测试库使用；不授予超级用户权限。
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN CREATEDB PASSWORD {}').format(
                sql.Identifier(c['db_user']), sql.Literal(c['db_password'])))
        if not conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', ('campus_forum',)).fetchone():
            conn.execute(sql.SQL('CREATE DATABASE campus_forum OWNER {}').format(sql.Identifier(c['db_user'])))
    print('本地PostgreSQL已准备就绪：127.0.0.1:55432 / campus_forum。密码保存在.runtime/config.json。')


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'init'
    if action not in ('stop', 'status'):
        raise SystemExit('数据库已改为MySQL。请改用 scripts/setup_mysql.py init；本旧脚本仅保留stop/status以管理此前的本项目PostgreSQL实例。')
    if action == 'init':
        initialize()
    elif action == 'start':
        start()
    elif action in ('status', 'stop'):
        args = [PG / 'pg_ctl.exe', '-D', DATA]
        if action == 'stop':
            args += ['-m', 'fast', '-w']
        run(args + [action])
    else:
        raise SystemExit('支持的操作：init / start / status / stop')

