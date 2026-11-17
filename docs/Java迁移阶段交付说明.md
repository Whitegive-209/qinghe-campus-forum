# Java迁移阶段交付说明

日期：2026-11-17。本阶段完成Java实现、功能验证及GitHub同仓库更新；性能分析是后续阶段，不能混作已经完成。

## 迁移前备份

按用户要求，先新建并上传Python版本，再改技术栈。仓库为[Whitegive-209/qinghe-campus-forum](https://github.com/Whitegive-209/qinghe-campus-forum)，实际为用户创建的公开仓库。

迁移前远程提交：`1f418a4acc493e0a9f813e884a6713fb9ade898f`；固定分支：[django-baseline](https://github.com/Whitegive-209/qinghe-campus-forum/tree/django-baseline)。72个文件的Git树为`8fefa242ad49c6b4e1a68cab399b3d07d0a2e8ce`，与原本地提交`8e883927f8e46e47fa62684666c19e570d532759`的文件树一致。提交标识因上传方式不同而不同，源码内容没有因此变化。

本地还保留`v1.0-django-baseline`标记和`deliverables/django-baseline-8e88392.bundle`。管理员密码、业务数据库密码、应用密钥、演示账号随机密码、性能账号密码及软件包不上传。

## 已完成

- 活跃网站后端为Java 17 / Spring Boot 3.5.16，页面为Thymeleaf，数据库仍为MySQL。启动命令直接运行Java，不调用Django业务服务。
- Spring Security负责登录、Session、CSRF；密码使用BCrypt强度12；数据库访问使用Spring JDBC与Hikari连接池，Flyway保存版本化SQL迁移。
- 核心功能均已迁移：注册、登录退出、个人资料、分类与最新/热门排序、标题正文搜索、帖子发布编辑删除、评论回复、删除自己评论并保留回复、点赞及取消。
- 建立三个新的独立库和专用账号，具体名称与限定权限经用户明确授权。未重置或清空Python旧库，没有导入旧用户或更改其密码。
- 固定Maven Wrapper 3.3.4 / Maven 3.9.11；构建成功，可执行JAR实际在本机8080运行。根目录新Java启动入口与旧Python入口分别保留。
- 39项自动化检查通过，其中28项实际MySQL集成测试、11项输入及密码哈希测试；0失败、0跳过。另有5项真实串行HTTP检查通过。Edge显示Java首页。

功能测试详情、真实用例、步骤对应、断言结果和发现问题见[Java版功能测试报告](Java版功能测试报告.md)。修复了实际发现的发布时间8小时偏移问题；仅更改本应用数据库会话时区，并用新增测试和重启后的页面复核。

## 页面与接口

本机演示地址`http://127.0.0.1:8080/`，健康检查`/health/`返回`backend: java`和`status: ok`。性能服务入口预留8081，仅连接`qinghe_forum_java_perf`，目前未启动正式负载。

主要路由沿用旧版形状，Java的表单令牌为`_csrf`，Session Cookie为`QINGHE_JAVA_SESSION`；旧Django JMX的CSRF处理不能直接用于Java。后续必须使用独立Java测试计划与新账号，先做少量请求调试。

## JProfiler当前状态及剩余工作

厂商Windows便携包16.2已下载到本机`.tools/jprofiler-16.2/`，SHA-256为`8f1b86e093bd26a877562e608e44c1b7390a562dfd13f0c1391a8a79dd3b3487`，与官方校验文件一致。压缩包未上传仓库。

界面启动尝试后未检测到JProfiler窗口或进程，原因尚未查明；尚未验证许可状态、连接Java进程或录制快照。不将下载成功当作分析成功。本轮没有JProfiler分析结论。

Java版JMeter 10/25/50/75/100用户梯度、100用户稳定5分钟、压力测试、性能瓶颈分析与优化前后对比均为未测试。Python历史成绩只属于旧实现，不能套用。超过100用户的具体压力参数仍须展示并取得单独确认。

下一阶段先解决JProfiler启动与许可、建立Java专用JMX及独立数据，再按既定顺序执行，保留原始JTL、HTML、资源记录、JProfiler快照及可见界面证据。开启分析器的诊断成绩与关闭分析器的基线成绩分别记录。
