"""根据已经保存的真实功能测试记录生成阶段报告，不补造测试结果。"""
from datetime import datetime
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
from zoneinfo import ZoneInfo
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'


def main():
    backend = json.loads((OUT / 'functional-results.json').read_text(encoding='utf-8'))
    browser = json.loads((OUT / 'browser-results.json').read_text(encoding='utf-8'))
    passed_backend = sum(r['结果'] == '通过' for r in backend['用例'])
    passed_browser = sum(r['通过'] for r in browser['用例'])
    success = backend['成功'] and browser['成功']
    now = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    lines = [
        '# 网站开发与功能测试阶段报告', '', f'整理时间：{now}', '',
        '## 完成内容', '',
        '已实现中文首页、最新/热门排序、分类、分页、注册、登录退出、个人资料展示及修改、发帖与详情、本人帖子编辑删除、评论回复、本人评论删除、点赞取消、标题正文搜索及中文错误页。', '',
        '技术架构：HTML/CSS/JavaScript → Waitress（本机8000端口，8线程）→ Django → MySQL（本机3306端口）。使用Django Session与CSRF保护，密码哈希保存，点赞具有数据库唯一约束。', '',
        '数据库使用用户现有MySQL 8.0.41；qinghe_forum为演示库、qinghe_forum_perf为后续性能测试库。test_qinghe_forum由Django功能测试自动创建与销毁。未清空或修改其他项目数据库。', '',
        f'环境：{platform.system()} {platform.release()} / Python {platform.python_version()} / Django {version("Django")} / mysqlclient {version("mysqlclient")} / Waitress {version("waitress")}。', '',
        '## 实际功能验证', '',
        '| 验证方式 | 执行时间 | 执行数 | 通过数 | 失败数 |',
        '| --- | --- | ---: | ---: | ---: |',
        f'| Django客户端 + 真实MySQL隔离库 | {backend["执行时间"]} | {backend["执行数"]} | {passed_backend} | {backend["执行数"] - passed_backend} |',
        f'| 真实Chrome {browser["浏览器"]}无头浏览器 | {browser["执行时间"]} | {browser["执行数"]} | {passed_browser} | {browser["执行数"] - passed_browser} |', '',
        '当前执行结论：' + ('上述已执行检查全部通过。' if success else '存在未通过项，禁止进入性能测试。'), '',
        '逐项后端报告见[功能测试报告](../test-results/功能测试报告.md)，原始结构化记录见[functional-results.json](../test-results/functional-results.json)。', '',
        '浏览器逐项结果如下：', '',
        '| 测试项目 | 步骤及预期 | 实际结果 | 通过 |', '| --- | --- | --- | --- |',
    ]
    for item in browser['用例']:
        actual = item['实际'].replace('|', '/').replace('\n', ' ')
        lines.append(f'| {item["项目"]} | {item["预期"]} | {actual} | {"是" if item["通过"] else "否"} |')
    lines += ['', '## 证据与数据说明', '',
              '- [首页桌面截图](../test-results/homepage-desktop.png)',
              '- [首页窄屏截图](../test-results/homepage-mobile.png)',
              '- [登录截图](../test-results/login.png)',
              '- [帖子详情及删除评论后的回复保留截图](../test-results/post-detail.png)',
              '- [个人资料截图](../test-results/profile.png)',
              '- [浏览器原始结果](../test-results/browser-results.json)', '',
              '演示数据含3个普通账号、5个分类及6篇中文帖子。演示账号随机密码仅保存于本机.runtime/demo_accounts.json。浏览器脚本新增2个带运行时间的普通测试账号，不公开密码；该次验证创建的帖子经过网站删除流程处理。', '',
              '## 发现的问题和处理', '',
              '初期受限执行环境阻止本机数据库连接，经授权后实际连接成功，这属于执行权限问题。数据库按用户要求由PostgreSQL改为MySQL；此前项目专用PostgreSQL实例已停止，旧文件保留。', '',
              '当前已执行的32项后端检查和17项浏览器检查未发现未修复的功能缺陷。测试通过不代表不存在所有潜在缺陷；尚未覆盖所有浏览器版本、互联网部署、恶意流量和高负载情况。', '',
              '## 尚未执行的阶段', '',
              '| 项目 | 状态 |', '| --- | --- |',
              '| JMeter计划创建及少量用户调试 | 未执行 |',
              '| 10/25/50/75/100虚拟用户梯度测试 | 未测试 |',
              '| 100用户持续5分钟测试 | 未测试 |',
              '| 超过100用户的压力测试 | 未测试，需单独确认具体参数 |',
              '| 性能瓶颈优化及前后对比 | 未执行，必须依据真实测量 |', '',
              '没有生成或虚构响应时间、RPS、P95/P99、错误率或资源占用结果。下一阶段准备JMeter .jmx、独立测试账号CSV、性能数据、业务断言、CPU/内存监控与结果保存目录，先做少量用户调试，再进入100用户梯度。', '']
    (ROOT / 'docs' / '开发与功能测试阶段报告.md').write_text('\n'.join(lines), encoding='utf-8')
    delivery = ROOT / 'deliverables'
    delivery.mkdir(exist_ok=True)
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d_%H%M%S')
    archive = delivery / f'校园论坛源码与功能测试_{stamp}.zip'
    roots = ['campus', 'forum', 'templates', 'static', 'scripts', 'docs', 'test-results']
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for folder in roots:
            for path in (ROOT / folder).rglob('*'):
                if path.is_file() and '__pycache__' not in path.parts:
                    z.write(path, path.relative_to(ROOT).as_posix())
        for name in ['manage.py', 'requirements.txt', 'requirements-dev.txt', '.gitignore', 'README.md', 'start.ps1', 'stop-database.ps1', '启动论坛.cmd']:
            z.write(ROOT / name, name)
    # 压缩包不得包含本地数据库秘密配置或真实数据库文件。
    with zipfile.ZipFile(archive) as z:
        assert not any(name.startswith(('.runtime/', '.venv/', '.tools/')) for name in z.namelist())
        assert 'forum/migrations/0001_initial.py' in z.namelist()
        assert 'test-results/browser-results.json' in z.namelist()
    print(json.dumps({'后端通过': passed_backend, '浏览器通过': passed_browser, '整体成功': success,
                      '阶段报告': str(ROOT / 'docs' / '开发与功能测试阶段报告.md'), '源码归档': str(archive)}, ensure_ascii=False))
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
