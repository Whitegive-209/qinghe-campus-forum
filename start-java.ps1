param([switch]$Perf, [int]$Port = 0)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$javaExe = 'C:\Program Files\Java\jdk-17\bin\java.exe'
if (-not (Test-Path -LiteralPath $javaExe)) {
    if ($env:JAVA_HOME) { $javaExe = Join-Path $env:JAVA_HOME 'bin/java.exe' }
    else { $javaExe = (Get-Command java.exe -ErrorAction Stop).Source }
}
$configPath = Join-Path $PSScriptRoot '.runtime/java-mysql-config.json'
if (Test-Path -LiteralPath $configPath) {
    $javaDbConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $env:FORUM_DB_USER = $javaDbConfig.db_user
    $env:FORUM_DB_PASSWORD = $javaDbConfig.db_password
    $env:FORUM_DB_PORT = [string]$javaDbConfig.db_port
}
if (-not $env:FORUM_DB_PASSWORD) { throw '请先完成Java独立数据库初始化，或设置FORUM_DB_PASSWORD等连接环境变量。' }
$env:FORUM_DATABASE = if ($Perf) { 'qinghe_forum_java_perf' } else { 'qinghe_forum_java' }
if ($Port -eq 0) { $Port = if ($Perf) { 8081 } else { 8080 } }
if ($Port -lt 1024 -or $Port -gt 65535) { throw '端口范围应为1024至65535。' }
$env:FORUM_PORT = [string]$Port
$jarPath = Join-Path $PSScriptRoot 'java-backend/target/campus-forum-2.0.0.jar'
if (-not (Test-Path -LiteralPath $jarPath)) { throw '请先运行build-java.ps1构建Java网站。' }
$javaArgs = @('-Xms128m','-Xmx512m','-jar',$jarPath)
if (-not $Perf) {
    $demoPath = Join-Path $PSScriptRoot '.runtime/java-demo-account.json'
    if (-not (Test-Path -LiteralPath $demoPath)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $demoPath) -Force | Out-Null
        $passwordBytes = New-Object byte[] 24
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($passwordBytes) } finally { $rng.Dispose() }
        @{username='java_demo';password=([Convert]::ToBase64String($passwordBytes)+'!Aa7')} | ConvertTo-Json | Set-Content -LiteralPath $demoPath -Encoding UTF8
    }
    $demoAccount = Get-Content -LiteralPath $demoPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $env:FORUM_DEMO_PASSWORD = $demoAccount.password
    $javaArgs += '--forum.seed-demo=true'
}
Write-Output "青禾校园Java版：http://127.0.0.1:$Port ，数据库：$env:FORUM_DATABASE 。按Ctrl+C停止网站。"
& $javaExe @javaArgs
exit $LASTEXITCODE
