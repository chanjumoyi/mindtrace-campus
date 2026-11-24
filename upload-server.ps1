param(
  [string]$Prefix = 'http://+:8082/',
  [string]$UploadRoot = 'C:\yyh_project\mindtrace-collector\uploads',
  [string]$Token = $env:MINDTRACE_UPLOAD_TOKEN,
  [switch]$RequireToken,
  [int]$MaxBytes = 25MB,
  [int]$MinFreeBytes = 300MB,
  [int]$MaxImageBytes = 8MB,
  [int]$MaxImageTotalBytes = 16MB,
  [int]$MaxImagesPerSession = 12,
  [switch]$RequireImageConsent
)

$ErrorActionPreference = 'Stop'
$LogPath = Join-Path (Split-Path -Parent $UploadRoot) 'logs\upload-server.log'
$ManifestPath = Join-Path $UploadRoot 'manifest.csv'
$ManifestV2Path = Join-Path $UploadRoot 'manifest-v2.csv'
$ImageIndexPath = Join-Path $UploadRoot 'image-index.csv'

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

function Get-UniqueDirectory([string]$parent, [string]$name) {
  $candidate = Join-Path $parent $name
  if (-not (Test-Path $candidate)) { return $candidate }
  for ($index = 1; $index -lt 10000; $index++) {
    $candidate = Join-Path $parent ('{0}-{1}' -f $name, $index)
    if (-not (Test-Path $candidate)) { return $candidate }
  }
  throw 'Unable to allocate a unique session directory.'
}

function Get-SafeImageName([string]$requested, [string]$fallback) {
  $name = $requested
  if ([string]::IsNullOrWhiteSpace($name)) { $name = $fallback }
  $name = [Uri]::UnescapeDataString($name)
  $name = [IO.Path]::GetFileName($name)
  $name = [Text.RegularExpressions.Regex]::Replace($name, '[^A-Za-z0-9._-]', '_')
  $name = $name.Trim('.', '_', ' ')
  if ([string]::IsNullOrWhiteSpace($name)) { $name = 'image' }
  if ($name.Length -gt 110) { $name = $name.Substring(0, 110) }
  if (-not $name.ToLowerInvariant().EndsWith('.png')) { $name += '.png' }
  return $name
}

function Get-SafeSegment([string]$value, [string]$fallback) {
  $name = [string]$value
  $name = $name.Trim()
  $name = [Text.RegularExpressions.Regex]::Replace($name, '[^A-Za-z0-9._-]', '_')
  $name = $name.Trim('.', '_', ' ')
  if ([string]::IsNullOrWhiteSpace($name)) { $name = $fallback }
  if ($name.Length -gt 80) { $name = $name.Substring(0, 80) }
  return $name
}

function Get-SessionDate($payload) {
  foreach ($field in @('collectionCompletedAt', 'createdAt', 'exportedAt')) {
    $value = [string]$payload.$field
    if ([string]::IsNullOrWhiteSpace($value)) { continue }
    try {
      return ([DateTimeOffset]::Parse($value, [Globalization.CultureInfo]::InvariantCulture)).LocalDateTime.ToString('yyyy-MM-dd')
    } catch { }
  }
  return (Get-Date -Format 'yyyy-MM-dd')
}

function New-Rejection([int]$status, [string]$errorCode, [string]$detail) {
  return [PSCustomObject]@{ Ok = $false; Status = $status; Error = $errorCode; Detail = $detail }
}

function Test-ImagePayload($image, [int]$attemptIndex) {
  $where = "attempts[$attemptIndex].image"
  if ($null -eq $image) { return New-Rejection 422 'invalid_image_payload' "$where is null" }

  $filename = [string]$image.filename
  if ($filename -notmatch '^[A-Za-z0-9._-]{1,120}\.png$') {
    return New-Rejection 422 'invalid_image_payload' "$where.filename must be a safe .png name"
  }
  if (-not ([string]$image.mimeType -ieq 'image/png')) {
    return New-Rejection 422 'invalid_image_payload' "$where.mimeType must be image/png"
  }

  $prefix = 'data:image/png;base64,'
  $dataUrl = [string]$image.dataUrl
  if (-not $dataUrl.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    return New-Rejection 422 'invalid_image_payload' "$where.dataUrl must be a PNG base64 data URL"
  }
  $encoded = [Text.RegularExpressions.Regex]::Replace($dataUrl.Substring($prefix.Length), '\s', '')
  if ([string]::IsNullOrWhiteSpace($encoded)) {
    return New-Rejection 422 'invalid_image_payload' "$where.dataUrl has no base64 data"
  }
  $encodedLimit = [Math]::Ceiling($MaxImageBytes * 4.0 / 3.0) + 8
  if ($encoded.Length -gt $encodedLimit) {
    return New-Rejection 413 'image_too_large' "$where exceeds MaxImageBytes"
  }

  try { $decoded = [Convert]::FromBase64String($encoded) } catch {
    return New-Rejection 422 'invalid_image_payload' "$where.dataUrl is not valid base64"
  }
  if ($decoded.Length -eq 0) {
    return New-Rejection 422 'invalid_image_payload' "$where.dataUrl is empty"
  }
  if ($decoded.Length -gt $MaxImageBytes) {
    return New-Rejection 413 'image_too_large' "$where exceeds MaxImageBytes"
  }
  if ($decoded.Length -lt 24) {
    return New-Rejection 422 'invalid_image_payload' "$where is too short to be a PNG"
  }

  $signature = @(0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A)
  for ($index = 0; $index -lt $signature.Count; $index++) {
    if ($decoded[$index] -ne $signature[$index]) {
      return New-Rejection 422 'invalid_image_payload' "$where does not have a PNG signature"
    }
  }
  $ihdrLength = [BitConverter]::ToInt32([byte[]]@($decoded[11], $decoded[10], $decoded[9], $decoded[8]), 0)
  $chunkType = [Text.Encoding]::ASCII.GetString($decoded, 12, 4)
  if ($ihdrLength -ne 13 -or $chunkType -ne 'IHDR') {
    return New-Rejection 422 'invalid_image_payload' "$where does not start with a valid IHDR chunk"
  }
  $width = [BitConverter]::ToUInt32([byte[]]@($decoded[19], $decoded[18], $decoded[17], $decoded[16]), 0)
  $height = [BitConverter]::ToUInt32([byte[]]@($decoded[23], $decoded[22], $decoded[21], $decoded[20]), 0)
  $pixels = [uint64]$width * [uint64]$height
  if ($width -lt 1 -or $height -lt 1 -or $width -gt 4096 -or $height -gt 4096 -or $pixels -gt 8000000) {
    return New-Rejection 422 'invalid_image_payload' "$where has unsupported dimensions"
  }

  return [PSCustomObject]@{
    Ok = $true
    Filename = $filename
    Bytes = $decoded.Length
    Width = $width
    Height = $height
    Content = $decoded
  }
}

function Get-ImageBatchInfo($attempts) {
  $count = 0
  $totalBytes = 0
  $items = @()
  if ($null -eq $attempts) { return [PSCustomObject]@{ Ok = $true; Count = 0; Bytes = 0; Items = @() } }
  $list = @($attempts)
  for ($index = 0; $index -lt $list.Count; $index++) {
    $attempt = $list[$index]
    if ($null -eq $attempt -or $null -eq $attempt.image) { continue }
    $count += 1
    if ($count -gt $MaxImagesPerSession) {
      return New-Rejection 413 'too_many_images' "more than $MaxImagesPerSession images in one session"
    }
    $checked = Test-ImagePayload $attempt.image $index
    if (-not $checked.Ok) { return $checked }
    $totalBytes += $checked.Bytes
    if ($totalBytes -gt $MaxImageTotalBytes) {
      return New-Rejection 413 'image_bytes_too_large' 'total decoded image bytes exceed MaxImageTotalBytes'
    }
    $items += [PSCustomObject]@{
      AttemptIndex = $index
      AttemptId = [string]$attempt.attemptId
      TaskId = [string]$attempt.taskId
      Filename = $checked.Filename
      Bytes = $checked.Bytes
      Width = $checked.Width
      Height = $checked.Height
      Content = $checked.Content
    }
  }
  return [PSCustomObject]@{ Ok = $true; Count = $count; Bytes = $totalBytes; Items = $items }
}

function Get-ConsentInfo($payload) {
  $consent = $payload.consent
  $accepted = $false
  $version = ''
  $scopes = @()
  if ($null -ne $consent) {
    $accepted = (($consent.accepted -eq $true) -or ([string]$consent.accepted -ieq 'true')) -and ([string]$consent.status -ieq 'granted')
    $version = [string]$consent.version
    if ($null -ne $consent.dataUseScope) {
      $scopes = @($consent.dataUseScope | ForEach-Object { [string]$_ })
    }
  }
  return [PSCustomObject]@{ Accepted = $accepted; Version = $version; Scopes = $scopes }
}

function Test-ImageConsent($consentInfo) {
  if (-not $consentInfo.Accepted) {
    return New-Rejection 422 'consent_missing_or_not_granted' 'image uploads require consent.accepted=true and status=granted'
  }
  if (-not $RequireImageConsent) { return [PSCustomObject]@{ Ok = $true } }

  $approvedVersions = @(
    'trajectory-upload-collection-v1.3',
    'trajectory-upload-collection-v1.4',
    'local-anonymous-collection-v1.3',
    'local-anonymous-collection-v1.4'
  )
  if ($approvedVersions -notcontains $consentInfo.Version) {
    return New-Rejection 422 'consent_version_too_old' 'image uploads require an approved consent version'
  }
  foreach ($scope in @('server_storage', 'model_development')) {
    if ($consentInfo.Scopes -notcontains $scope) {
      return New-Rejection 422 'consent_scope_missing' "image uploads require consent scope: $scope"
    }
  }
  return [PSCustomObject]@{ Ok = $true }
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

function Write-ManifestV2([string]$storedAs, [string]$originalName, $payload, [int]$bytes, [int]$attemptCount, $imageInfo, $consentInfo) {
  $record = [PSCustomObject]@{
    uploaded_at = (Get-Date -Format 'o')
    stored_as = $storedAs
    original_name = $originalName
    session_id = [string]$payload.sessionId
    participant_id = [string]$payload.participantId
    schema_version = [string]$payload.schemaVersion
    app_version = [string]$payload.appVersion
    dataset_eligibility = [string]$payload.datasetEligibility
    consent_version = $consentInfo.Version
    consent_accepted = $consentInfo.Accepted
    consent_scopes = ($consentInfo.Scopes -join '|')
    attempts = $attemptCount
    images = $imageInfo.Count
    image_bytes = $imageInfo.Bytes
    bytes = $bytes
  }
  $exists = Test-Path $ManifestV2Path
  $line = ($record | ConvertTo-Csv -NoTypeInformation) -join "`r`n"
  if (-not $exists) {
    Add-Content -Path $ManifestV2Path -Value $line -Encoding UTF8
  } else {
    Add-Content -Path $ManifestV2Path -Value (($line -split "`r`n")[1]) -Encoding UTF8
  }
}

function Write-ImageIndex([string]$uploadedAt, [string]$storedAs, $payload, $item, [string]$imagePath, [string]$imageRelative) {
  $hash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash
  $record = [PSCustomObject]@{
    uploaded_at = $uploadedAt
    stored_as = $storedAs
    session_id = [string]$payload.sessionId
    participant_id = [string]$payload.participantId
    attempt_index = $item.AttemptIndex
    attempt_id = $item.AttemptId
    task_id = $item.TaskId
    image_file = $imageRelative
    bytes = $item.Bytes
    sha256 = $hash
    width = $item.Width
    height = $item.Height
  }
  $exists = Test-Path $ImageIndexPath
  $line = ($record | ConvertTo-Csv -NoTypeInformation) -join "`r`n"
  if (-not $exists) {
    Add-Content -Path $ImageIndexPath -Value $line -Encoding UTF8
  } else {
    Add-Content -Path $ImageIndexPath -Value (($line -split "`r`n")[1]) -Encoding UTF8
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
        Send-Json $context 200 @{
          ok = $true
          service = 'mindtrace-upload'
          time = (Get-Date -Format 'o')
          requireToken = [bool]$RequireToken
          requireImageConsent = [bool]$RequireImageConsent
          maxImageBytes = $MaxImageBytes
          maxImageTotalBytes = $MaxImageTotalBytes
          maxImagesPerSession = $MaxImagesPerSession
        }
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

      $attemptList = @()
      if ($null -ne $payload.attempts) { $attemptList = @($payload.attempts) }
      $imageInfo = Get-ImageBatchInfo $attemptList
      if (-not $imageInfo.Ok) {
        Write-Log "Rejected upload from $($request.RemoteEndPoint): $($imageInfo.Error) ($($imageInfo.Detail))"
        Send-Json $context $imageInfo.Status @{ ok = $false; error = $imageInfo.Error; detail = $imageInfo.Detail }
        continue
      }
      $consentInfo = Get-ConsentInfo $payload
      if ($imageInfo.Count -gt 0) {
        $consentCheck = Test-ImageConsent $consentInfo
        if (-not $consentCheck.Ok) {
          Write-Log "Rejected upload from $($request.RemoteEndPoint): $($consentCheck.Error) ($($consentCheck.Detail))"
          Send-Json $context $consentCheck.Status @{ ok = $false; error = $consentCheck.Error; detail = $consentCheck.Detail }
          continue
        }
      }

      $originalName = [string]$request.Headers['X-Filename']
      $safeName = Get-SafeFileName $originalName ([string]$payload.sessionId)
      $sessionStem = [IO.Path]::GetFileNameWithoutExtension($safeName)
      $participantSegment = Get-SafeSegment ([string]$payload.participantId) 'unknown-participant'
      $dateSegment = Get-SessionDate $payload
      $participantDirectory = Join-Path $UploadRoot $participantSegment
      $dateDirectory = Join-Path $participantDirectory $dateSegment
      New-Item -ItemType Directory -Path $dateDirectory -Force | Out-Null
      $sessionDirectory = Get-UniqueDirectory $dateDirectory $sessionStem
      New-Item -ItemType Directory -Path $sessionDirectory -Force | Out-Null
      $uploadedAt = (Get-Date -Format 'o')
      $imagePaths = @()
      $target = Join-Path $sessionDirectory $safeName
      $storedAs = $target.Substring($UploadRoot.Length).TrimStart('\', '/')
      $writtenImages = @()
      try {
        foreach ($item in $imageInfo.Items) {
          $fallback = 'attempt-{0}.png' -f ($item.AttemptIndex + 1)
          $imageName = Get-SafeImageName $item.Filename $fallback
          $imagePath = Get-UniquePath $sessionDirectory $imageName
          [IO.File]::WriteAllBytes($imagePath, $item.Content)
          $imageRelative = $imagePath.Substring($UploadRoot.Length).TrimStart('\', '/')
          $imagePaths += $imageRelative
          $writtenImages += [PSCustomObject]@{ Item = $item; Path = $imagePath; Relative = $imageRelative }
        }
        [IO.File]::WriteAllText($target, $body, [Text.UTF8Encoding]::new($false))
      } catch {
        if (Test-Path -LiteralPath $sessionDirectory) {
          Remove-Item -LiteralPath $sessionDirectory -Recurse -Force -ErrorAction SilentlyContinue
        }
        throw
      }
      foreach ($written in $writtenImages) {
        try {
          Write-ImageIndex $uploadedAt $storedAs $payload $written.Item $written.Path $written.Relative
        } catch {
          Write-Log "Image index write failed for $($written.Relative): $($_.Exception.Message)"
        }
      }

      Write-Manifest $storedAs $originalName ([string]$payload.sessionId) ([string]$payload.participantId) ([string]$payload.datasetEligibility) $bytes
      Write-ManifestV2 $storedAs $originalName $payload $bytes $attemptList.Count $imageInfo $consentInfo
      Write-Log "Stored $storedAs ($bytes bytes, session=$($payload.sessionId), schema=$($payload.schemaVersion), images=$($imageInfo.Count), imageBytes=$($imageInfo.Bytes), imageFiles=$($imagePaths.Count), consent=$($consentInfo.Version))"

      Send-Json $context 200 @{ ok = $true; storedAs = $storedAs; bytes = $bytes; schemaVersion = [string]$payload.schemaVersion; images = $imageInfo.Count; imageBytes = $imageInfo.Bytes; imageFiles = @($imagePaths) }
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
