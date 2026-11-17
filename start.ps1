$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' 'scripts\setup_mysql.py' check
if ($LASTEXITCODE -ne 0) { throw 'MySQL连接失败，请确认已有MySQL服务已启动，并运行scripts/setup_mysql.py init完成初始化。' }
& '.\.venv\Scripts\python.exe' 'scripts\serve.py'

