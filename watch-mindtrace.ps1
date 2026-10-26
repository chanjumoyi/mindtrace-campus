[CmdletBinding()]
param(
  [string]$Root = 'C:\yyh_project\mindtrace-collector',
  [switch]$Once,
  [ValidateRange(1, 3600)]
  [int]$RefreshSeconds = 5
)

$ErrorActionPreference = 'Stop'
$OutputEncoding = [Text.UTF8Encoding]::new($false)
try { [Console]::OutputEncoding = $OutputEncoding } catch { }
try { $Host.UI.RawUI.WindowTitle = 'MindTrace 采集服务监控 - 关闭窗口不会停止服务' } catch { }

# Each snapshot loads the file again, then returns before the next iteration.
# Replacing this file updates a running monitor without nested restart loops.
if (-not $Once) {
  $monitorScript = $PSCommandPath
  while ($true) {
    try {
      Clear-Host
      & $monitorScript -Root $Root -Once -RefreshSeconds $RefreshSeconds
    } catch {
      Write-Host '监控暂时无法刷新，将在下一轮重试。' -ForegroundColor Red
    }
    Start-Sleep -Seconds $RefreshSeconds
  }
  return
}

function Get-MindTraceHealth([string]$Url, [switch]$Upload) {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
    $payload = $null
    if ($Upload) {
      try { $payload = $response.Content | ConvertFrom-Json -ErrorAction Stop } catch { }
    }
    $healthy = ($response.StatusCode -eq 200)
    if ($Upload) { $healthy = $healthy -and ($null -ne $payload) -and ($payload.ok -eq $true) }
    $text = 'HTTP {0}' -f $response.StatusCode
    if (-not $healthy) { $text += '（健康检查未通过）' }
    return [PSCustomObject]@{ Ok = $healthy; Text = $text; Payload = $payload }
  } catch {
    $statusCode = $null
    if ($_.Exception.Response) {
      try { $statusCode = [int]$_.Exception.Response.StatusCode } catch { }
    }
    $text = if ($null -ne $statusCode) { 'HTTP {0}' -f $statusCode } else { '连接失败或超时' }
    return [PSCustomObject]@{ Ok = $false; Text = $text; Payload = $null }
  }
}

function Get-MindTraceTaskState([string]$Name) {
  if (-not (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) { return '无法查询' }
  try {
    $task = Get-ScheduledTask -TaskName $Name -ErrorAction Stop
    switch ([string]$task.State) {
      'Running' { return '运行中' }
      'Ready' { return '就绪' }
      'Disabled' { return '已禁用' }
      default { return [string]$task.State }
    }
  } catch {
    return '未找到或无权限'
  }
}

function Write-MindTraceStatus([string]$Label, [string]$TaskState, $Health) {
  $color = if ($Health.Ok) { 'Green' } else { 'Red' }
  Write-Host ('  {0}  |  计划任务：{1}  |  健康检查：{2}' -f $Label, $TaskState, $Health.Text) -ForegroundColor $color
}

function Get-MindTraceRecentFailures([string]$LogPath) {
  if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) { return }
  $lines = @(Get-Content -LiteralPath $LogPath -Encoding UTF8 -Tail 200 -ErrorAction Stop)
  $failures = @()
  foreach ($line in $lines) {
    $reason = $null
    switch -Regex ($line) {
      '(?i)bad token|invalid_token' { $reason = '上传令牌不匹配'; break }
      '(?i)payload_too_large' { $reason = '采集包超过大小限制'; break }
      '(?i)server_storage_low' { $reason = '服务器磁盘余量不足'; break }
      '(?i)invalid_json' { $reason = '采集包 JSON 格式错误'; break }
      '(?i)missing_schema_version_or_session_id' { $reason = '采集包缺少版本或会话编号'; break }
      '(?i)Request failed|server_error' { $reason = '上传处理异常'; break }
      '(?i)Rejected upload' { $reason = '上传被拒绝'; break }
    }
    if ($null -eq $reason) { continue }
    $time = '时间未记录'
    if ($line -match '^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})') {
      $time = '{0} {1}' -f $Matches[1], $Matches[2]
    }
    # Never display the original line: it can contain addresses or participant data.
    $failures += [PSCustomObject]@{ Time = $time; Reason = $reason }
  }
  $failures | Select-Object -Last 3 | Sort-Object Time -Descending
}

$uploadRoot = Join-Path $Root 'uploads'
$uploadLog = Join-Path $Root 'logs\upload-server.log'
$siteHealth = Get-MindTraceHealth 'http://127.0.0.1:8081/healthz'
$uploadHealth = Get-MindTraceHealth 'http://127.0.0.1:8082/health' -Upload
$siteTask = Get-MindTraceTaskState 'MindTraceSiteServer'
$uploadTask = Get-MindTraceTaskState 'MindTraceUploadServer'

Write-Host '================================================================' -ForegroundColor DarkCyan
Write-Host ('  MindTrace 采集服务监控    {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor Cyan
Write-Host '================================================================' -ForegroundColor DarkCyan
Write-MindTraceStatus '网页服务' $siteTask $siteHealth
Write-MindTraceStatus '上传服务' $uploadTask $uploadHealth

$authMode = '未知（上传健康接口未返回鉴权配置）'
$authColor = 'Yellow'
if ($uploadHealth.Ok -and $null -ne $uploadHealth.Payload) {
  $authProperty = $uploadHealth.Payload.PSObject.Properties['requireToken']
  if ($null -ne $authProperty -and $authProperty.Value -is [bool]) {
    $authMode = if ($authProperty.Value) { '强制上传令牌' } else { '默认允许无令牌上传' }
    $authColor = 'Gray'
  }
}
Write-Host ('  上传鉴权：{0}' -f $authMode) -ForegroundColor $authColor
Write-Host '  协议兼容：接收器支持 schema 1.6（十八题）和 1.7（WHO-5）。' -ForegroundColor Gray
Write-Host ''

$files = @()
$inventoryOk = $true
if (Test-Path -LiteralPath $uploadRoot -PathType Container) {
  try {
    # Inspect file metadata only; collected JSON bodies are never opened here.
    $files = @(Get-ChildItem -LiteralPath $uploadRoot -Recurse -File -Filter '*.json' -ErrorAction Stop)
  } catch {
    $inventoryOk = $false
  }
} else {
  $inventoryOk = $false
}
if ($inventoryOk) {
  $today = (Get-Date).Date
  $todayFiles = @($files | Where-Object { $_.LastWriteTime -ge $today })
  $totalBytes = [long]0
  if ($files.Count -gt 0) { $totalBytes = ($files | Measure-Object -Property Length -Sum).Sum }
  Write-Host ('  采集文件：共 {0} 个，{1:N2} MB；今日写入 {2} 个' -f $files.Count, ($totalBytes / 1MB), $todayFiles.Count) -ForegroundColor Yellow
} else {
  Write-Host '  采集文件：目录不存在或无法读取，暂时无法统计。' -ForegroundColor Yellow
}

Write-Host '  最近上传（最多 5 个，仅显示文件时间和大小）：' -ForegroundColor Yellow
$recentFiles = @($files | Sort-Object LastWriteTime -Descending | Select-Object -First 5)
if ($recentFiles.Count -eq 0) {
  Write-Host '    暂无可显示的上传记录。' -ForegroundColor DarkGray
} else {
  foreach ($file in $recentFiles) {
    Write-Host ('    {0}    {1:N1} KB' -f $file.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'), ($file.Length / 1KB)) -ForegroundColor Gray
  }
}

try {
  $rootItem = Get-Item -LiteralPath $Root -ErrorAction Stop
  $drive = Get-PSDrive -Name $rootItem.PSDrive.Name -PSProvider FileSystem -ErrorAction Stop
  if ($null -eq $drive.Free) { throw 'Disk capacity unavailable.' }
  $freeGb = [double]$drive.Free / 1GB
  $diskColor = if ($freeGb -lt 1) { 'Red' } elseif ($freeGb -lt 3) { 'Yellow' } else { 'Green' }
  Write-Host ('  数据目录所在磁盘可用：{0:N2} GB' -f $freeGb) -ForegroundColor $diskColor
} catch {
  Write-Host '  数据目录所在磁盘可用：无法查询。' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '  最近失败（最多 3 条，检查日志末尾 200 条）：' -ForegroundColor Yellow
try {
  $failures = @(Get-MindTraceRecentFailures $uploadLog)
  if ($failures.Count -eq 0) {
    Write-Host '    未记录失败，或尚无日志。' -ForegroundColor DarkGray
  } else {
    foreach ($failure in $failures) {
      Write-Host ('    {0}    {1}' -f $failure.Time, $failure.Reason) -ForegroundColor Yellow
    }
  }
} catch {
  Write-Host '    日志暂时无法读取。' -ForegroundColor DarkGray
}

Write-Host ''
Write-Host '================================================================' -ForegroundColor DarkCyan
Write-Host '  关闭窗口只会停止监控，不会停止后台采集服务。' -ForegroundColor DarkGray
Write-Host ('  每 {0} 秒刷新，并自动加载监控脚本更新。按 Ctrl+C 退出。' -f $RefreshSeconds) -ForegroundColor DarkGray
