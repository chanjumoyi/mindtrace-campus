[CmdletBinding(SupportsShouldProcess)]
param(
  [string]$Root = 'C:\yyh_project\mindtrace-collector',
  [string]$TaskName = 'MindTraceUploadServer'
)

$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'upload-server.ps1'))
$target = [IO.Path]::GetFullPath((Join-Path $Root 'upload-server.ps1'))
if ($source -eq $target) { throw 'Extract the update package into a separate directory first.' }
if (-not (Test-Path -LiteralPath $source)) { throw 'The update package is missing upload-server.ps1.' }
if (-not (Test-Path -LiteralPath $target)) { throw 'The existing upload-server.ps1 was not found.' }

function Read-ScriptAst([string]$path) {
  $tokens = $null
  $parseErrors = $null
  $ast = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
  if ($parseErrors.Count) { throw "PowerShell syntax errors in $path" }
  return $ast
}

$existingAst = Read-ScriptAst $target
$newAst = Read-ScriptAst $source
$updatedText = [IO.File]::ReadAllText($source)
# Keep the installed listener, data directory, limits, and token. In particular,
# an old embedded token stays on that server and never enters the update package.
$replacements = @()
foreach ($name in @('Prefix', 'UploadRoot', 'Token', 'MaxBytes', 'MinFreeBytes')) {
  $oldParam = $existingAst.ParamBlock.Parameters | Where-Object { $_.Name.VariablePath.UserPath -eq $name }
  $newParam = $newAst.ParamBlock.Parameters | Where-Object { $_.Name.VariablePath.UserPath -eq $name }
  if ($oldParam.DefaultValue -and $newParam.DefaultValue) {
    $replacements += [PSCustomObject]@{
      Start = $newParam.DefaultValue.Extent.StartOffset
      End = $newParam.DefaultValue.Extent.EndOffset
      Text = $oldParam.DefaultValue.Extent.Text
    }
  }
}
foreach ($replacement in ($replacements | Sort-Object Start -Descending)) {
  $updatedText = $updatedText.Substring(0, $replacement.Start) + $replacement.Text + $updatedText.Substring($replacement.End)
}
$tokens = $null
$parseErrors = $null
$updatedAst = [Management.Automation.Language.Parser]::ParseInput($updatedText, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'The merged server configuration contains PowerShell syntax errors.' }

if (-not $PSCmdlet.ShouldProcess($target, 'Back up and update the upload receiver; restart only its scheduled task')) { return }
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  throw 'Run this updater from an elevated PowerShell session.'
}
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
$prefixParam = $updatedAst.ParamBlock.Parameters | Where-Object { $_.Name.VariablePath.UserPath -eq 'Prefix' }
$prefix = [string]$prefixParam.DefaultValue.SafeGetValue()
foreach ($action in $task.Actions) {
  if ($action.Arguments -match '(?i)(?:^|\s)-Prefix\s+"?([^"\s]+)') { $prefix = $Matches[1] }
}
$healthUri = ([Uri]($prefix -replace '^http://[+*]', 'http://127.0.0.1')).GetLeftPart([UriPartial]::Authority) + '/health'

function Stop-UploadTask {
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $deadline = (Get-Date).AddSeconds(10)
  while ((Get-ScheduledTask -TaskName $TaskName).State -eq 'Running') {
    if ((Get-Date) -ge $deadline) { throw 'The upload task did not stop in time.' }
    Start-Sleep -Milliseconds 100
  }
}

$backup = $target + '.backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
Copy-Item -LiteralPath $target -Destination $backup -ErrorAction Stop
Stop-UploadTask
try {
  [IO.File]::WriteAllText($target, $updatedText, [Text.UTF8Encoding]::new($false))
  Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop
  $deadline = (Get-Date).AddSeconds(12)
  $healthy = $false
  while ((Get-Date) -lt $deadline) {
    try {
      $health = Invoke-RestMethod -Uri $healthUri -TimeoutSec 1
      if ($health.ok -and $health.service -eq 'mindtrace-upload' -and $health.PSObject.Properties.Name -contains 'requireToken') {
        $healthy = $true
        break
      }
    } catch { }
    Start-Sleep -Milliseconds 100
  }
  if (-not $healthy) { throw 'The updated upload receiver did not pass its health check.' }
} catch {
  Stop-UploadTask
  Copy-Item -LiteralPath $backup -Destination $target -Force
  Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  throw
}
Write-Host "Receiver updated. Previous script: $backup"
Write-Host "Health check passed: $healthUri"
Write-Host 'Existing uploads, logs, and the static-site task were preserved.'
