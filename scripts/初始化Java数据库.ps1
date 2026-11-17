$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:PYTHONUTF8 = '1'
& '.\.venv\Scripts\python.exe' 'scripts/setup_java_mysql.py'
Read-Host '按回车关闭窗口'
