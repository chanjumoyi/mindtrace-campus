param(
  [string]$Prefix = 'http://+:8082/',
  [string]$UploadRoot = 'C:\yyh_project\mindtrace-collector\uploads',
  [string]$Token = $env:MINDTRACE_UPLOAD_TOKEN,
  [switch]$RequireToken,
  [int]$MaxBytes = 25MB,
  [int]$MinFreeBytes = 300MB
)

$ErrorActionPreference = 'Stop'
$LogPath = Join-Path (Split-Path -Parent $UploadRoot) 'logs\upload-server.log'
$ManifestPath = Join-Path $UploadRoot 'manifest.csv'

function Write-Log([string]$message) {
  $line = '{0} {1}' -f (Get-Date -Format 'o'), $message
  try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch { }
  Write-Host $line
}

function Send-Json($context, [int]$status, $payload) {
  $body = $payload | ConvertTo-Json -Compress -Depth 6
  $bytes = [Text.Encoding]::UTF8.GetBytes($body)
  $context.Response.StatusCode = $status
  $context.Response.ContentType = 'application/json; charset=utf-8'
  $context.Response.Headers['Access-Control-Allow-Origin'] = '*'
  $context.Response.Headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Upload-Token, X-Filename'
  $context.Response.Headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
  $context.Response.ContentLength64 = $bytes.Length
  $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  $context.Response.Close()
}

function Send-Empty($context, [int]$status) {
  $context.Response.StatusCode = $status
  $context.Response.Headers['Access-Control-Allow-Origin'] = '*'
  $context.Response.Headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Upload-Token, X-Filename'
  $context.Response.Headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
  $context.Response.ContentLength64 = 0
  $context.Response.Close()
}

function Get-SafeFileName([string]$requested, [string]$sessionId) {
  $name = $requested
  if ([string]::IsNullOrWhiteSpace($name)) { $name = $sessionId }
  $name = [Uri]::UnescapeDataString($name)
  $name = [IO.Path]::GetFileName($name)
  $name = [Text.RegularExpressions.Regex]::Replace($name, '[^A-Za-z0-9._-]', '_')
  $name = $name.Trim('.', '_', ' ')
  if ([string]::IsNullOrWhiteSpace($name)) { $name = 'session' }
  if ($name.Length -gt 110) { $name = $name.Substring(0, 110) }
  if (-not $name.ToLowerInvariant().EndsWith('.json')) { $name += '.json' }
  return $name
}

function Get-UniquePath([string]$directory, [string]$fileName) {
  $candidate = Join-Path $directory $fileName
  if (-not (Test-Path $candidate)) { return $candidate }
  $stem = [IO.Path]::GetFileNameWithoutExtension($fileName)
  $extension = [IO.Path]::GetExtension($fileName)
  for ($index = 1; $index -lt 10000; $index++) {
    $candidate = Join-Path $directory ('{0}-{1}{2}' -f $stem, $index, $extension)
    if (-not (Test-Path $candidate)) { return $candidate }
  }
  throw 'Unable to allocate a unique upload filename.'
}

function Write-Manifest([string]$storedAs, [string]$originalName, [string]$sessionId, [string]$participantId, [string]$eligibility, [int]$bytes) {
  $record = [PSCustomObject]@{
    uploaded_at = (Get-Date -Format 'o')
    stored_as = $storedAs
    original_name = $originalName
    session_id = $sessionId
    participant_id = $participantId
    dataset_eligibility = $eligibility
    bytes = $bytes
  }
  $exists = Test-Path $ManifestPath
  $line = ($record | ConvertTo-Csv -NoTypeInformation) -join "`r`n"
  if (-not $exists) {
    Add-Content -Path $ManifestPath -Value $line -Encoding UTF8
  } else {
    Add-Content -Path $ManifestPath -Value (($line -split "`r`n")[1]) -Encoding UTF8
  }
}

New-Item -ItemType Directory -Path $UploadRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $LogPath) -Force | Out-Null
if ($RequireToken -and [string]::IsNullOrWhiteSpace($Token)) {
  throw 'A non-empty upload token is required.'
}

function Test-FreeSpace {
  $drive = Get-PSDrive -Name (Get-Item $UploadRoot).PSDrive.Name
  return ($drive.Free -ge $MinFreeBytes)
}

$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add($Prefix)
$listener.Start()
Write-Log "Upload listener started on $Prefix; root=$UploadRoot"

try {
  while ($listener.IsListening) {
    $context = $listener.GetContext()
    $request = $context.Request
    $response = $context.Response
    try {
      if ($request.HttpMethod -eq 'OPTIONS') {
        Send-Empty $context 204
        continue
      }

      if ($request.HttpMethod -eq 'GET' -and $request.Url.AbsolutePath -eq '/health') {
        Send-Json $context 200 @{ ok = $true; service = 'mindtrace-upload'; time = (Get-Date -Format 'o'); requireToken = [bool]$RequireToken }
        continue
      }

      if ($request.HttpMethod -ne 'POST' -or $request.Url.AbsolutePath -ne '/api/handwriting-sessions') {
        Send-Json $context 404 @{ ok = $false; error = 'not_found' }
        continue
      }

      # The collector omits this header when VITE_UPLOAD_TOKEN is not configured.
      # Keep that default upload path working; deployments can explicitly require it.
      $providedToken = [string]$request.Headers['X-Upload-Token']
      $hasProvidedToken = -not [string]::IsNullOrWhiteSpace($providedToken)
      $hasConfiguredToken = -not [string]::IsNullOrWhiteSpace($Token)
      if (($RequireToken -or ($hasConfiguredToken -and $hasProvidedToken)) -and $providedToken -cne $Token) {
        Write-Log "Rejected upload from $($request.RemoteEndPoint): bad token"
        Send-Json $context 401 @{ ok = $false; error = 'invalid_token' }
        continue
      }

      if ($request.ContentLength64 -gt $MaxBytes) {
        Send-Json $context 413 @{ ok = $false; error = 'payload_too_large' }
        continue
      }
      if (-not (Test-FreeSpace)) {
        Send-Json $context 507 @{ ok = $false; error = 'server_storage_low' }
        continue
      }

      $reader = [IO.StreamReader]::new($request.InputStream, [Text.Encoding]::UTF8)
      try { $body = $reader.ReadToEnd() } finally { $reader.Dispose() }
      $bytes = [Text.Encoding]::UTF8.GetByteCount($body)
      if ($bytes -gt $MaxBytes) {
        Send-Json $context 413 @{ ok = $false; error = 'payload_too_large' }
        continue
      }

      try { $payload = $body | ConvertFrom-Json } catch {
        Send-Json $context 400 @{ ok = $false; error = 'invalid_json' }
        continue
      }
      if ([string]::IsNullOrWhiteSpace([string]$payload.schemaVersion) -or [string]::IsNullOrWhiteSpace([string]$payload.sessionId)) {
        Send-Json $context 422 @{ ok = $false; error = 'missing_schema_version_or_session_id' }
        continue
      }

      $dayDirectory = Join-Path $UploadRoot (Get-Date -Format 'yyyy-MM-dd')
      New-Item -ItemType Directory -Path $dayDirectory -Force | Out-Null
      $originalName = [string]$request.Headers['X-Filename']
      $safeName = Get-SafeFileName $originalName ([string]$payload.sessionId)
      $target = Get-UniquePath $dayDirectory $safeName
      [IO.File]::WriteAllText($target, $body, [Text.UTF8Encoding]::new($false))

      $storedAs = $target.Substring($UploadRoot.Length).TrimStart('\', '/')
      Write-Manifest $storedAs $originalName ([string]$payload.sessionId) ([string]$payload.participantId) ([string]$payload.datasetEligibility) $bytes
      Write-Log "Stored $storedAs ($bytes bytes, session=$($payload.sessionId))"

      Send-Json $context 200 @{ ok = $true; storedAs = $storedAs; bytes = $bytes }
    } catch {
      Write-Log "Request failed: $($_.Exception.Message)"
      try { Send-Json $context 500 @{ ok = $false; error = 'server_error' } } catch { }
    }
  }
} finally {
  $listener.Stop()
  $listener.Close()
  Write-Log 'Upload listener stopped'
}
