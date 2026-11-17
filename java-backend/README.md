# 青禾校园 Java后端

Java 17、Spring Boot 3.5.16、Spring Security、Thymeleaf、Spring JDBC、Flyway、MySQL。网站所有业务由Java执行，Python仅保留历史实现和部分初始化/测试辅助脚本。

## 本机使用

1. 已完成Java数据库初始化，无需重复创建。数据库连接与演示账号密码在根目录`.runtime/java-mysql-config.json`和`.runtime/java-demo-account.json`，不上传GitHub。
2. 在项目根目录运行`powershell -ExecutionPolicy Bypass -File .\build-java.ps1`。Maven Wrapper固定为Maven 3.9.11，首次使用需下载官方构建工具和依赖。
3. 双击根目录`启动Java论坛.cmd`，或执行`powershell -ExecutionPolicy Bypass -File .\start-java.ps1`。该启动入口直接运行Java，不启动Django或依赖Python业务服务。
4. 打开`http://127.0.0.1:8080/`，注册账号即可操作。账号`java_demo`的随机密码仅在上述本机配置中。
5. 按Ctrl+C停止网站；不要停止共享MySQL服务。

性能服务启动使用`start-java.ps1 -Perf`，只连接`qinghe_forum_java_perf`，监听本机8081；本阶段尚未执行Java负载测试。演示初始化不用于性能库。

## 在新电脑配置

需要JDK 17、MySQL 8和构建下载所需网络。先按授权范围新建`qinghe_forum_java`、`qinghe_forum_java_perf`、`test_qinghe_forum_java`三个库和专用账号，避免覆盖同名现有库。MySQL字符集`utf8mb4`、排序规则`utf8mb4_0900_as_cs`。

根目录`scripts/setup_java_mysql.py`是可选的本机交互初始化工具，需要Python和mysqlclient；管理员密码由操作者输入，不保存。它拒绝覆盖同名库或账号。若手动完成建库，可以通过环境变量配置，无需该辅助工具：`FORUM_DB_USER`、`FORUM_DB_PASSWORD`、`FORUM_DB_PORT`。请在本机设置，不要把密码写入Git文件或发到聊天。

使用Maven Wrapper编译：在本目录执行`mvnw.cmd package`（Windows）或`./mvnw package`（其他系统，需为脚本设置执行权限）。直接运行：`java -Xms128m -Xmx512m -jar target/campus-forum-2.0.0.jar`。环境变量`FORUM_DATABASE`默认Java演示库，`FORUM_PORT`默认8080；应用始终仅监听127.0.0.1。

只有显式传入`--forum.seed-demo=true`且提供`FORUM_DEMO_PASSWORD`时才新增演示账号和帖子；账号存在时不修改其密码。Flyway负责表迁移，禁止clean，不使用自动清库。

## 功能与验证

支持注册登录退出、个人资料、分类/最新/热门列表、帖子发布编辑删除、评论回复和评论删除占位、点赞/取消、标题与正文搜索。BCrypt强度12，Session隔离，保留CSRF保护、HTML转义及服务端所有权检查。

普通`mvnw.cmd test`运行11项校验/哈希用例，数据库用例默认跳过。完整功能验证需设置`FORUM_RUN_DB_TESTS=1`和专用数据库凭据，再运行`mvnw.cmd test`。数据库集成测试固定使用`test_qinghe_forum_java`，逐用例事务回滚，不访问演示库或Python库。

当前电脑可从根目录执行`.\.venv\Scripts\python.exe scripts/run_java.py test`自动注入本地配置并留存JUnit结果。此Python脚本是测试执行辅助工具，测试目标为Java处理链和MySQL。

真实结果见`../docs/Java版功能测试报告.md`。39项测试已通过；Java的100用户并发、压力和JProfiler采集尚未测试。

## 后续性能分析

JMeter承担10/25/50/75/100用户的请求和业务断言，Java版要重新提取表单`_csrf`令牌与独立会话，不直接执行Django JMX。JProfiler连接本项目Java进程，不能误选JMeter自己的JVM；录制CPU、内存、线程和JDBC数据时单独记录开关与开销。

JProfiler便携包已经从厂商下载并校验，存放于本机`.tools/jprofiler-16.2`，不上传软件包。实际许可状态和采集功能尚待界面验证。超过100用户前仍需再次确认具体测试参数。
