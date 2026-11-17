# 青禾校园论坛：Java版

校园论坛网站开发及性能测试课程项目。当前后端已迁移为 **Java 17 + Spring Boot 3.5.16 + MySQL**，使用Thymeleaf中文页面，保留注册登录、帖子、评论回复、点赞、搜索和个人资料功能。

## 打开网站

本机Java网站地址：<http://127.0.0.1:8080/>。

在项目根目录运行 `powershell -ExecutionPolicy Bypass -File .\build-java.ps1` 构建，再双击 `启动Java论坛.cmd`。网站启动入口直接运行Java；运行时不启动Python后端。详细配置、在新电脑构建和数据库初始化见 [Java运行说明](java-backend/README.md)。

数据库连接和随机演示账号保存在本机 `.runtime/`，不上传仓库。也可在页面注册自己的账号。共享MySQL服务不应随网站关闭。

## 版本与GitHub历史

- 迁移前Python版本已先上传；固定保留在 [`django-baseline` 分支](https://github.com/Whitegive-209/qinghe-campus-forum/tree/django-baseline)，远程提交 `1f418a4acc493e0a9f813e884a6713fb9ade898f`。
- `main`分支继续记录Java实现更新。旧Python文件及数据库保留，便于课程对照，不再作为当前网站后端。旧运行方式见 [Python版本运行说明](docs/Python版本运行说明.md)。
- Java代码位于 [`java-backend/`](java-backend/)，包括Maven Wrapper、数据库SQL迁移及自动化测试。
- 密码、令牌、测试账号密码、生成报告原件、软件安装包、虚拟环境和打包目录均排除出版本控制。

## 已执行的验证

[Java版功能测试报告](docs/Java版功能测试报告.md)：**39项通过，0项失败，0项跳过**，包含28项真实MySQL集成用例及11项输入/哈希测试。测试使用独立 `test_qinghe_forum_java`，不重置Python库。已修复实际页面发现的8小时时区偏移，并新增回归检查。

可执行JAR已在本机启动，健康接口返回 `backend: java`；首页、登录/注册表单和CSS的5项串行HTTP检查通过，Edge中已实际显示中文首页。这些结果不是并发性能成绩。

## 性能测试状态

继续使用 **Apache JMeter + JProfiler**：JMeter模拟用户并统计响应、吞吐与错误；JProfiler分析Java内部CPU、内存、线程和SQL耗时。

**Java版并发、压力及JProfiler录制尚未测试。** 旧Python性能记录单独保留，不套用到Java，也不将功能通过等同于100用户性能通过。Java的CSRF令牌和登录机制已变化，后续会建立独立JMX再调试。

100用户须全部线程共同保持至少5分钟，用户数不等于RPS。超过100用户前仍必须展示具体地址、线程数、Ramp-up、持续时间、场景和停止条件，并取得单独确认。分析器开启和关闭的成绩分开记录，优化前后保持相同条件。

[迁移及联合测试方案](docs/Java后端迁移与联合测试方案_20261117.md)记录了分阶段安排；其中“等待确认”是方案编制时的历史状态，已在随后获得确认并实施。
