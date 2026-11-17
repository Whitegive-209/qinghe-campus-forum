import os
from pathlib import Path
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus.settings')
from campus.wsgi import application
from waitress import serve

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    print(f'青禾校园启动：http://127.0.0.1:{args.port} （按 Ctrl+C 停止）', flush=True)
    serve(application, host='127.0.0.1', port=args.port, threads=8, connection_limit=256,
          channel_timeout=30, max_request_body_size=1024 * 1024, expose_tracebacks=False)

