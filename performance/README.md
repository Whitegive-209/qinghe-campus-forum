# Apache JMeter测试资料

本目录使用Apache JMeter 5.6.3和Java 17，不能用k6或Locust代替。正式负载使用命令行运行，不开启结果树等消耗资源的图形监听器。

## 地址和隔离

- 演示网站：http://127.0.0.1:8000，库为qinghe_forum。
- 性能网站：http://127.0.0.1:8001，库为qinghe_forum_perf。
- run_jmeter.py在每次执行时临时启动8001服务，结束后停止它；不停止MySQL或演示服务。
- 服务配置：Waitress 8线程，连接上限256，DEBUG关闭，与正常网站使用同一业务代码。
- 只允许本机目标。执行器限制最多100用户，超过100用户的压力测试需要单独列明参数并得到确认。

## 文件

plans/home.jmx：首页访问。
plans/browse.jmx：分类帖子列表和详情。
plans/login.jmx：不同账号登录、身份核对和退出，每轮都实际重新登录。
plans/write.jmx：登录后发布带唯一标识的帖子，查看、评论并核对保存内容。
plans/like.jmx：登录后点赞、重复点赞和取消，验证状态与最终数据库记录。

data/accounts.csv包含200个合成账号的用户名、随机测试密码、用户ID、目标帖子ID，不含MySQL管理员密码或真实用户。每线程固定一行，账号不轮换，Cookie Manager使线程会话独立。
data/manifest.json记录初始数据规模：1000篇帖子、5000评论、999点赞；目标帖子初始没有点赞。
build_plans.py可以从源码重新生成计划。手工修改计划后不要无意重生成覆盖修改。

## 必须理解的概念

| 概念 | 通俗解释 |
| --- | --- |
| 线程组Thread Group | 一组按相同流程访问的模拟用户 |
| 虚拟用户Virtual User | 一个模拟访问者，独立身份与会话 |
| Ramp-up | 逐步启动全部用户所用时间，100用户/60秒约每0.6秒启动一个 |
| 循环次数 | 每个用户重复整个场景多少次 |
| 响应时间 | 请求发送到完整接收响应的耗时，单位毫秒 |
| P90/P95/P99 | 分别有90%/95%/99%的请求耗时不超过该值 |
| 吞吐量Throughput | 单位时间完成多少请求，本项目以请求/秒RPS表示 |
| 错误率 | 请求失败数÷总请求数，包含业务断言失败 |

100用户不等于100RPS，也不代表100条请求在同一个瞬间到达。正式场景每个请求前有1～2秒停顿；会话登录和CSRF准备请求均计入并单独标注。JMeter不执行页面JavaScript，本项目实际请求来自已通过浏览器功能验证的表单和接口；这里测量HTTP服务能力，不是页面视觉加载速度。

## 准备及小流量调试

在项目根目录的PowerShell中执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:FORUM_DATABASE = 'qinghe_forum_perf'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_perf
Remove-Item Env:FORUM_DATABASE
.\.venv\Scripts\python.exe performance\build_plans.py
.\.venv\Scripts\python.exe performance\run_jmeter.py --mode smoke --scene all --users 2 --ramp 1
```

移除的是当前窗口的环境变量，不是文件。seed_perf仅接受独立性能库，不清空已有数据；已有数据清单存在时保留原数据。若出现同名或不一致情况，先核对，禁止擅自清库。

默认每类2用户、1循环，无阅读停顿，只调试脚本。JMX直接打开的默认值为1用户、1循环。独立打开JMX时，还需设置JMeter属性accounts为accounts.csv绝对路径、run_id为唯一运行编号、CookieManager.save.cookies=true；推荐直接使用执行器。

## 第五阶段正式参数（尚未执行时不得当作成绩）

五种场景分别执行，不同时开启五组100用户。

| 用户数 | Ramp-up秒 | 全部用户启动后的稳定时间秒 | 调度总时间秒 |
| ---: | ---: | ---: | ---: |
| 10 | 10 | 120 | 130 |
| 25 | 25 | 120 | 145 |
| 50 | 50 | 120 | 170 |
| 75 | 75 | 120 | 195 |
| 100 | 60 | 300 | 360 |

正式负载示例（此说明不会自动执行）：

```powershell
.\.venv\Scripts\python.exe performance\run_jmeter.py --mode load --scene home --users 100 --ramp 60 --steady 300
```

计划循环为-1并启用定时停止，总时长含Ramp-up；需检查活跃线程曲线，确认100用户阶段保持目标。调试通过后，正式测试前单独预热，预热结果独立保存。记录包含爬升的全程指标，并额外按稳定区间统计，不能用小样本成绩冒充持续测试成绩。

## 结果与资源监控

每次创建新的results/模式_时间/场景目录，不复用旧JTL或HTML目录：

- results.jtl：原始HTTP请求数据（CSV格式），含时间戳、耗时、成功标记、断言失败、活跃线程数。
- html/index.html：JMeter自动生成的HTML报告。
- jmeter.log、console.log：JMeter日志与控制台输出。
- resources.csv：约每1秒记录整机CPU、可用内存、内存占比，以及网站/JMeter/MySQL进程CPU和RSS内存。进程CPU按全部逻辑处理器归一化为0～100%。首条CPU采样用于启动基准，不作为稳态判断。
- run.json：参数、目标、数据与计划SHA256，便于复现。
- summary.json：从JTL计算总数、成功失败数、平均/P90/P95/P99、RPS、错误率及业务数据核对。
- site.log：独立性能网站日志。

分位数使用最近秩法。RPS=样本数÷第一条请求开始到最后一条完成的时间。全程RPS、稳定区间RPS和JMeter按标签的RPS不能混为一个值。正式报告须说明口径。HTML默认百分位展示可能与最近秩法存在小样本差异，保留原始JTL供核对。

发帖评论通过本轮唯一标识进行实际数据库数量、作者及关联关系核对；点赞检查最终目标点赞为0且没有用户帖子组合重复。每个HTTP请求都有状态和相应内容/身份/JSON断言，不能只看HTTP 200。写入数据按运行编号保留，不在测试后自动清库；正式优化对比前应在明确授权后恢复同等基线，或者使用可证明等价的新隔离基线。

## 安全与结论边界

GUI测试点击开始前必须执行`performance/check_gui_ready.py`，只在其当前返回`ready: true`时立即开始。检查不启动负载；等待或中断后必须重查，不能使用几分钟前的就绪结论。测试网站和监控关闭后，需要重新准备新一轮，不能继续使用旧目录。2026-11-16浏览75用户的一次准备超时故障已单独标记无效，见`docs/JMeter测试异常分析_20261116.md`；用户随后明确恢复，新的75和100用户浏览测试均已完成，故障未复现。

连续30个采样点整机CPU高于90%或可用内存不足1GB，执行器发送JMeter Shutdown；不能在限定时间结束时仅终止本次启动的JMeter。达到超时也会停止。错误请求使对应线程停止，运行后非零失败或数据不一致使后续场景停止。正式梯度还需持续观察错误率和数据库连接、锁等待，异常时人工停止或降低负载。

资源CSV同时采集MySQL全局状态中的连接数、运行线程、慢查询计数、当前锁等待、累计锁等待次数和时长、连接失败数。累计值需比较起止差值。这些属于共享MySQL实例指标，可能受到其他项目影响，不等于本论坛专属计数。执行器不采集慢SQL文本或其他项目的数据，不能仅靠计数声称已完成瓶颈分析。JMeter、网站和数据库共用电脑，因此测试结果只反映该本机联合运行条件，不能直接推算线上承载能力。

超过100用户前必须再次展示地址、线程数、Ramp-up、时长、场景和停止条件，获得确认后执行。本阶段小流量调试结果不代表100并发通过，未执行的项目写“未测试”。

参考：[JMeter官方组件说明](https://jmeter.apache.org/usermanual/component_reference.html)、[JMeter HTML报告说明](https://jmeter.apache.org/usermanual/generating-dashboard.html)。
