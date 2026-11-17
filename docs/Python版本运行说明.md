# 青禾校园论坛

校园论坛网站开发及性能测试课程项目。中文页面，支持注册、登录退出、资料编辑、帖子分类与搜索、发帖与编辑删除、评论与回复、点赞与取消。使用Django和MySQL，正式本地服务使用Waitress。

## 本机启动（第一次环境初始化完成后）

1. 可以双击 `启动论坛.cmd` 启动；也可以在此文件所在目录打开PowerShell，按照以下步骤操作。
2. 执行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`。
3. 保持这个窗口打开，浏览器访问 http://127.0.0.1:8000 。
4. 在网站注册自己的账号，或者查看 `.runtime/demo_accounts.json` 中的演示账号。密码是随机生成的，请勿公开。
5. 按Ctrl+C停止网站。MySQL是电脑已有服务，保持运行，不要随意停止，以免影响其他项目。

网站使用8000端口，数据库默认连接已有的3306端口。如果网站端口被占用，不要随意结束其他进程，先核实占用者。

## 环境初始化

本项目使用Python 3.14；依赖版本在requirements.txt中锁定。项目不需要Node.js。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

数据库使用电脑已有的MySQL 8.0（本机客户端检查为8.0.41，服务端版本由连接时确认）。在本机PowerShell运行以下初始化命令，按提示输入管理员用户名、端口、密码；输入密码不显示字符是正常现象。管理员密码不会保存，也不要发到聊天里。

```powershell
.\.venv\Scripts\python.exe scripts\setup_mysql.py init
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

setup_mysql.py只创建qinghe_forum演示库、qinghe_forum_perf性能库，并为专用账号授予这两个库及test_qinghe_forum隔离测试库的权限。不更改全局数据库配置、不修改现有账号或其他数据库。检测到同名数据库或账号时会停止，不覆盖。业务账号随机密码保存在.runtime/mysql-config.json，勿公开。

编码为utf8mb4（支持中文和表情），使用InnoDB事务及外键。连接采用严格模式和READ COMMITTED事务隔离。旧的PostgreSQL下载包、程序及.runtime/pgdata保留，但不再用于本项目；本项目启动的旧实例已停止，不会通过start.ps1启动。

需要管理后台时自行执行 ` .\.venv\Scripts\python.exe manage.py createsuperuser`，按提示设置管理员账号；不提供公开默认管理员密码。

## 功能测试

```powershell
.\.venv\Scripts\python.exe manage.py test forum --verbosity 2
```

此命令会创建并销毁独立的test_qinghe_forum数据库，不修改qinghe_forum演示库。自定义测试运行器自动输出JSON与Markdown逐项报告。浏览器验证脚本另见scripts/browser_check.py（存在时），结果与截图保存在test-results。

网站启动后，可在另一个PowerShell窗口执行真实浏览器检查（使用电脑现有Chrome，不自动下载浏览器）：

```powershell
.\.venv\Scripts\python.exe scripts\browser_check.py
.\.venv\Scripts\python.exe scripts\stage_report.py
```

浏览器脚本会新增两个带时间标识的测试账号，并通过网站流程创建、编辑、删除本次测试帖子；不会清空已有帖子。stage_report.py读取实际结果生成阶段报告，并在deliverables中创建带时间的源码与证据压缩包，不包含.runtime秘密配置、数据库文件、.venv或.tools。

已执行的阶段结果见 `docs/开发与功能测试阶段报告.md`。JMeter各阶段目前尚未测试，不能把功能测试通过解释为100用户性能通过。

## 目录

- campus：项目设置和服务入口。
- forum：模型、表单、业务、迁移和功能测试。
- templates、static：中文页面和样式脚本。
- scripts：本地数据库及服务工具。
- docs：设计说明与阶段报告。
- test-results：真实执行结果和截图，不提交版本控制。
- .runtime：私密连接配置、演示账号和保留的旧数据库文件，不要删除或公开。
- .tools：保留此前下载的PostgreSQL程序与下载包，目前不使用。

JMeter文件已经准备，少量用户调试已经执行，实际记录见docs/JMeter准备与调试报告.md。尚未执行的正式性能测试不能当作已通过。超过100用户的压力测试必须再次确认后执行。

第四阶段的JMeter计划、独立性能数据和执行器见 [performance/README.md](performance/README.md)。小流量调试和正式100用户测试是不同阶段，不能互相替代。MySQL管理员密码不在这些测试文件中。
