from datetime import datetime
from zoneinfo import ZoneInfo


def analyze(directory, samples, resources, users, steady):
    from performance.run_jmeter import percentile
    starts, finishes = [], []
    for line in (directory / 'jmeter.log').read_text(encoding='utf-8', errors='replace').splitlines():
        if 'Thread started:' in line or 'Thread finished:' in line:
            stamp = int(datetime.strptime(line[:23], '%Y-%m-%d %H:%M:%S,%f').replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()*1000)
            (starts if 'Thread started:' in line else finishes).append(stamp)
    if len(starts) != users or len(finishes) != users:
        return {'coverage_passed': False, 'started_threads': len(starts), 'finished_threads': len(finishes)}
    begin, end = max(starts), max(starts)+steady*1000
    selected = [r for r in samples if int(r['timeStamp']) >= begin and int(r['timeStamp'])+int(r['elapsed']) <= end]
    observed = [r for r in resources if begin <= r['timestamp_ms'] <= end]
    times = [int(r['elapsed']) for r in selected]
    failed = sum(r['success'] != 'true' for r in selected)
    active_duration = (min(finishes)-max(starts))/1000
    result = {'coverage_passed': active_duration >= steady, 'all_threads_alive_seconds': active_duration,
              'window_start_ms': begin, 'window_end_ms': end, 'window_seconds': steady,
              'requests': len(selected), 'success': len(selected)-failed, 'failures': failed,
              'mean_ms': round(sum(times)/len(times), 2) if times else None,
              'p90_ms': percentile(times,.90), 'p95_ms': percentile(times,.95), 'p99_ms': percentile(times,.99),
              'rps': round(len(selected)/steady, 3), 'error_rate': failed/len(selected) if selected else None}
    if observed:
        for label in ['cpu_total_percent','site_cpu_percent','jmeter_cpu_percent']:
            result[label+'_mean'] = round(sum(r[label] for r in observed)/len(observed),3)
            result[label+'_max'] = max(r[label] for r in observed)
        result['site_rss_mb_max'] = max(r['site_rss_mb'] for r in observed)
        result['jmeter_rss_mb_max'] = max(r['jmeter_rss_mb'] for r in observed)
        result['memory_available_mb_min'] = min(r['memory_available_mb'] for r in observed)
        for label in observed[0]:
            if label.startswith('mysql_') and label.endswith('_rss_mb'):
                result[label+'_max'] = max(r[label] for r in observed)
            if label.startswith('db_'):
                result[label+'_max'] = max(r[label] for r in observed)
                result[label+'_delta'] = observed[-1][label]-observed[0][label]
    result['coverage_passed'] = result['coverage_passed'] and bool(times)
    stamps=[r['timestamp_ms'] for r in observed]
    result['resource_sampling']={'points':len(stamps),
        'first_offset_ms':stamps[0]-begin if stamps else None,
        'last_missing_ms':end-stamps[-1] if stamps else None,
        'max_gap_ms':max((b-a for a,b in zip(stamps,stamps[1:])),default=None),
        '说明':'负载持续时间由线程启动与退出日志证明；监控采样按真实时间戳统计，不能把每次采样的执行耗时误算为用户提前退出。'}
    return result
