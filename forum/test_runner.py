import json
from pathlib import Path
import time
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from django.conf import settings
from django.test.runner import DiscoverRunner


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.started = {}

    def startTest(self, test):
        self.started[test.id()] = time.perf_counter()
        super().startTest(test)

    def record(self, test, status, detail):
        self.records.append({'id': test.id(), '步骤与预期': test.shortDescription(), '结果': status,
                             '实际结果': detail, '耗时秒': round(time.perf_counter() - self.started.get(test.id(), time.perf_counter()), 3)})

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, '通过', '测试中所有断言均通过。')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, '失败', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, '错误', self._exc_info_to_string(err, test))


class RecordedRunner(DiscoverRunner):
    def get_resultclass(self):
        return RecordedResult

    def suite_result(self, suite, result, **kwargs):
        directory = Path(settings.BASE_DIR) / 'test-results'
        directory.mkdir(exist_ok=True)
        report = {'执行时间': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                  '数据库': settings.DATABASES['default']['TEST']['NAME'],
                  '执行数': result.testsRun, '成功': result.wasSuccessful(), '用例': result.records}
        (directory / 'functional-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = ['# 功能测试实际执行报告', '', f"执行时间：{report['执行时间']}", '',
                 f'执行 {result.testsRun} 项，整体结果：' + ('通过。' if result.wasSuccessful() else '存在失败，禁止进入性能测试。'), '',
                 '方式：Django测试客户端与真实MySQL隔离测试数据库；浏览器验证另见browser-results.json。通过表示该用例中的断言全部成立。', '',
                 '| 测试项目 | 测试步骤与预期 | 实际结果 | 是否通过 |', '| --- | --- | --- | --- |']
        for row in result.records:
            detail = row['实际结果'].replace('|', '/').replace('\n', ' ')[:500]
            lines.append(f"| {row['id'].split('.')[-1]} | {row['步骤与预期']} | {detail} | {row['结果']} |")
        (directory / '功能测试报告.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return super().suite_result(suite, result, **kwargs)
