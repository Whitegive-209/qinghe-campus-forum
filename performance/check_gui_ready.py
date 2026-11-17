"""点击JMeter开始前执行的只读检查；不会启动服务或发起并发测试。"""
import json
from pathlib import Path
import sys
import time
from urllib.request import urlopen

import psutil

ROOT = Path(__file__).resolve().parents[1]


def check_ready():
    info = json.loads((ROOT / '.runtime/gui-latest.json').read_text(encoding='utf-8'))
    if info.get('status') != 'ready':
        raise RuntimeError('监控未就绪或已经停止；禁止点击JMeter开始。')
    age = time.time() - info.get('heartbeat_epoch', 0)
    if not 0 <= age <= 5:
        raise RuntimeError('监控状态超过5秒未更新；禁止开始。')
    if info.get('port') != 8001 or info.get('database') != 'qinghe_forum_perf':
        raise RuntimeError('测试地址或独立数据库不符合要求。')
    for role in ('observer', 'server'):
        process = psutil.Process(info[role + '_pid'])
        if abs(process.create_time() - info[role + '_created']) > 0.01:
            raise RuntimeError('进程已更换，需要重新准备。')
        if not process.is_running():
            raise RuntimeError('监控或测试服务已停止。')
    # 单次健康请求，只确认服务可用，不作为性能样本。
    with urlopen('http://127.0.0.1:8001/health/', timeout=3) as response:
        if response.status != 200:
            raise RuntimeError('测试服务健康检查失败。')
        health = json.load(response)
        if health.get('status') != 'ok':
            raise RuntimeError('测试服务返回异常。')
    return {'ready': True, 'users': info['users'], 'scene': info['scene'],
            'directory': info['directory'],
            '说明': '服务与监控当前可用。核对GUI计划后立即开始；等待或中断后必须重新检查。'}


if __name__ == '__main__':
    try:
        print(json.dumps(check_ready(), ensure_ascii=False))
    except (OSError, ValueError, KeyError, RuntimeError, psutil.Error) as exc:
        print(json.dumps({'ready': False, '原因': str(exc)}, ensure_ascii=False))
        sys.exit(1)
