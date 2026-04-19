param(
    [string]$ScheduleMode = "",   # daily | hourly | interval | immediate
    [string]$ScheduleTime = "",   # daily/immediate 模式使用
    [string]$ScheduleInterval = "",   # interval 模式使用（小时）
    [string]$DingTalkWebhook = ""      # 也可留空，使用系统环境变量 DINGTALK_WEBHOOK
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$appConfigFile = Join-Path $projectRoot "config\app_config.json"

$cfgMode = "daily"
$cfgTime = "22:00"
$cfgInterval = "6"
$cfgWebhook = ""
if (Test-Path $appConfigFile) {
    try {
        $cfg = Get-Content -Raw -Path $appConfigFile | ConvertFrom-Json
        if ($cfg.scheduler.mode) { $cfgMode = [string]$cfg.scheduler.mode }
        if ($cfg.scheduler.time) { $cfgTime = [string]$cfg.scheduler.time }
        if ($cfg.scheduler.interval_hours) { $cfgInterval = [string]$cfg.scheduler.interval_hours }
        if ($cfg.notification.dingtalk_webhook) { $cfgWebhook = [string]$cfg.notification.dingtalk_webhook }
    } catch {
        Write-Host "WARN: 读取 config/app_config.json 失败，使用默认值。" -ForegroundColor Yellow
    }
}

if (-not $ScheduleMode) { $ScheduleMode = $cfgMode }
if (-not $ScheduleTime) { $ScheduleTime = $cfgTime }
if (-not $ScheduleInterval) { $ScheduleInterval = $cfgInterval }
if (-not $DingTalkWebhook) { $DingTalkWebhook = $cfgWebhook }

if (-not $DingTalkWebhook) {
    $DingTalkWebhook = $env:DINGTALK_WEBHOOK
}

if (-not $DingTalkWebhook) {
    Write-Host "WARN: 未提供 DingTalkWebhook，回测会运行但不会发送钉钉通知。" -ForegroundColor Yellow
}

$baseEnv = @{
    "PYTHONUTF8" = "1"
    "PYTHONIOENCODING" = "utf-8"
    "SCHEDULE_MODE" = $ScheduleMode
    "SCHEDULE_TIME" = $ScheduleTime
    "SCHEDULE_INTERVAL" = $ScheduleInterval
}

if ($DingTalkWebhook) {
    $baseEnv["DINGTALK_WEBHOOK"] = $DingTalkWebhook
}

foreach ($k in $baseEnv.Keys) {
    [System.Environment]::SetEnvironmentVariable($k, $baseEnv[$k], "Process")
}

Write-Host "项目目录: $projectRoot"
Write-Host "Python: $pythonExe"
Write-Host "调度: mode=$ScheduleMode time=$ScheduleTime interval=${ScheduleInterval}h"

# 1) 启动实时扫描 main.py
$mainCmd = "cd /d `"$projectRoot`" && `"$pythonExe`" src/main.py"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $mainCmd -WorkingDirectory $projectRoot
Write-Host "已启动 main.py（新终端）"

# 2) 启动定时回测 auto_backtest.py
$envPrefix = "set PYTHONUTF8=1 && set PYTHONIOENCODING=utf-8 && set SCHEDULE_MODE=$ScheduleMode && set SCHEDULE_TIME=$ScheduleTime && set SCHEDULE_INTERVAL=$ScheduleInterval"
if ($DingTalkWebhook) {
    $escapedWebhook = $DingTalkWebhook.Replace("&", "^&")
    $envPrefix += " && set DINGTALK_WEBHOOK=$escapedWebhook"
}
$schedulerCmd = "$envPrefix && cd /d `"$projectRoot`" && `"$pythonExe`" scripts/auto_backtest.py"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $schedulerCmd -WorkingDirectory $projectRoot
Write-Host "已启动 auto_backtest.py（新终端）"

Write-Host ""
Write-Host "全部启动完成。关闭对应终端即可停止服务。"
