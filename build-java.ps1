$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath 'C:\Program Files\Java\jdk-17') { $env:JAVA_HOME = 'C:\Program Files\Java\jdk-17' }
$mavenArgs = @('-f',(Join-Path $PSScriptRoot 'java-backend/pom.xml'),'-B','package')
$settingsPath = Join-Path $PSScriptRoot '.runtime/maven-java-settings.xml'
if (Test-Path -LiteralPath $settingsPath) { $mavenArgs += @('-s',$settingsPath) }
& (Join-Path $PSScriptRoot 'java-backend/mvnw.cmd') @mavenArgs
exit $LASTEXITCODE
