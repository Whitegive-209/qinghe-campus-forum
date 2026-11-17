# 第四阶段：JMeter环境准备与小流量调试报告

整理时间：2026-11-16T13:43:53.743272+08:00

## 本阶段结论

已准备5份真实JMeter测试计划、200个独立合成账号CSV、独立MySQL性能库、结果保存和资源监控工具。五类场景各2用户1循环的调试均通过。仅确认脚本可执行，不代表100并发性能通过。

环境：Windows / Python 3.14 / Django 5.2.19 / MySQL 8.0.41 / Apache JMeter 5.6.3 / Java 17.0.12。JMeter及网站和数据库在同一电脑，存在资源竞争。

目标：http://127.0.0.1:8001；仅本机，独立数据库qinghe_forum_perf。演示网站8000端口及qinghe_forum库不参与本次调试。

准备的初始数据：200账号、5分类、1000帖子、5000评论、999基础点赞。本次发帖场景新增2篇帖子、2条评论，按运行编号保留，未清库。

## 五类场景实际结果（2用户、1循环、无阅读停顿）

| 场景 | HTTP请求 | 成功 | 失败 | 平均ms | P90 | P95 | P99 | RPS | 错误率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 首页 | 2 | 2 | 0 | 199.0 | 199 | 199 | 199 | 10.05 | 0.00% |
| 帖子浏览 | 4 | 4 | 0 | 65.75 | 79 | 79 | 79 | 22.099 | 0.00% |
| 登录 | 8 | 8 | 0 | 155.5 | 434 | 434 | 434 | 9.558 | 0.00% |
| 发帖评论 | 16 | 16 | 0 | 72.38 | 446 | 448 | 448 | 19.441 | 0.00% |
| 点赞 | 14 | 14 | 0 | 77.79 | 453 | 457 | 457 | 19.471 | 0.00% |

合计44个HTTP请求，失败0个。各场景计入登录、CSRF准备等真实请求；不计虚构的业务事务样本。小样本分位数仅描述本次请求，不能据此判断稳定性或承载上限。

结果口径：RPS按各场景第一条请求开始至最后一条完成统计；分位数按最近秩法。CPU/内存采样范围包括JMeter启动及HTML报告生成，不能直接当作稳定负载资源消耗。

## 业务与数据校验

登录对比返回的用户名与用户ID，每线程固定账号、独立Cookie。保留CSRF安全机制，使用动态Cookie令牌。

发帖评论实际数据库核对：

```json
{
  "expected_posts": 2,
  "stored_posts": 2,
  "expected_comments": 2,
  "stored_comments": 2,
  "duplicate_titles": 0,
  "wrong_authors": 0,
  "wrong_comment_relations": 0,
  "passed": true
}
```

点赞实际数据库核对：

```json
{
  "remaining_target_likes": 0,
  "duplicate_user_post_pairs": 0,
  "passed": true
}
```

## 定时与监控调试

- load_20261116_134103：2用户、1秒Ramp-up+5秒稳定配置，5请求、0失败，定时正常结束。整机CPU峰值37.2%，最低可用内存5674.42MB（含启动与报告生成）。
  已记录MySQL连接数、运行线程、慢查询计数和锁等待计数。
- load_20261116_134216：2用户、1秒Ramp-up+5秒稳定配置，6请求、0失败，定时正常结束。整机CPU峰值40.9%，最低可用内存5776.48MB（含启动与报告生成）。
  已记录MySQL连接数、运行线程、慢查询计数和锁等待计数。

发现并修复的监控问题：Windows虚拟环境启动器会创建真正的Python服务子进程。最初五场景的site进程CPU/RSS仅包含启动器，数据不完整，禁止用于网站进程占用分析。执行器已修正为合计网站进程树，并用额外2用户定时检查复核，原始记录未删除。此修正属于测量工具修正，不是网站性能优化。

共享MySQL全局计数及进程资源可能受到其他项目影响。正式性能测试应对齐JTL时间戳、单独统计稳定区间，结合连接/锁等待差值判断；不能将全局计数直接归因于本论坛。

## 文件与复现

- [运行说明与术语](../performance/README.md)
- [首页JMX](../performance/plans/home.jmx)
- [浏览JMX](../performance/plans/browse.jmx)
- [登录JMX](../performance/plans/login.jmx)
- [发帖评论JMX](../performance/plans/write.jmx)
- [点赞JMX](../performance/plans/like.jmx)
- [合成测试账号CSV](../performance/data/accounts.csv)
- [初始数据清单](../performance/data/manifest.json)

- 首页：[原始JTL](../performance/results/smoke_20261116_133838/home/results.jtl)、[HTML报告](../performance/results/smoke_20261116_133838/home/html/index.html)、[资源CSV](../performance/results/smoke_20261116_133838/home/resources.csv)、[真实摘要](../performance/results/smoke_20261116_133838/home/summary.json)。
- 帖子浏览：[原始JTL](../performance/results/smoke_20261116_133838/browse/results.jtl)、[HTML报告](../performance/results/smoke_20261116_133838/browse/html/index.html)、[资源CSV](../performance/results/smoke_20261116_133838/browse/resources.csv)、[真实摘要](../performance/results/smoke_20261116_133838/browse/summary.json)。
- 登录：[原始JTL](../performance/results/smoke_20261116_133838/login/results.jtl)、[HTML报告](../performance/results/smoke_20261116_133838/login/html/index.html)、[资源CSV](../performance/results/smoke_20261116_133838/login/resources.csv)、[真实摘要](../performance/results/smoke_20261116_133838/login/summary.json)。
- 发帖评论：[原始JTL](../performance/results/smoke_20261116_133838/write/results.jtl)、[HTML报告](../performance/results/smoke_20261116_133838/write/html/index.html)、[资源CSV](../performance/results/smoke_20261116_133838/write/resources.csv)、[真实摘要](../performance/results/smoke_20261116_133838/write/summary.json)。
- 点赞：[原始JTL](../performance/results/smoke_20261116_133838/like/results.jtl)、[HTML报告](../performance/results/smoke_20261116_133838/like/html/index.html)、[资源CSV](../performance/results/smoke_20261116_133838/like/resources.csv)、[真实摘要](../performance/results/smoke_20261116_133838/like/summary.json)。

执行器默认smoke模式；所有JMX默认1用户1循环。独立CSV不含真实用户或数据库管理员密码，勿把它当作生产账号。运行参数、计划SHA256、CSV SHA256保存在每轮run.json中；新版本还记录运行前的数据表行数。

## 后续状态

| 项目 | 状态 |
| --- | --- |
| 环境、JMX、CSV、数据及少量用户调试 | 已完成 |
| 10/25/50/75/100用户正式梯度 | 未测试 |
| 100用户稳定5分钟 | 未测试 |
| 超过100用户压力测试 | 未测试，必须另行确认具体参数 |
| 根据性能瓶颈优化和同条件复测 | 未执行 |

下一阶段按已确认的10/25/50/75/100梯度分别执行五种场景，100用户稳定时间5分钟。此前应单独预热，固定数据规模与参数，检查资源余量。超过100用户前，另行展示地址、线程数、Ramp-up、时长、场景及停止条件并等待确认。
