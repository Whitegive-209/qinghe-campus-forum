$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Write-Output '项目使用电脑现有的MySQL服务，不自动停止它，以免影响其他项目。停止网站请在运行窗口按Ctrl+C。'

