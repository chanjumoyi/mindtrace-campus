param(
  [string]$Root = 'C:\yyh_project\mindtrace-collector'
)

$ErrorActionPreference = 'Stop'
$uploads = Join-Path $Root 'uploads'
$backupRoot = Join-Path $Root ('backups\migration-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($name in @('manifest.csv', 'manifest-v2.csv', 'image-index.csv')) {
  $path = Join-Path $uploads $name
  if (Test-Path -LiteralPath $path) {
    Copy-Item -LiteralPath $path -Destination (Join-Path $backupRoot $name) -Force
  }
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

function Get-UniqueDirectory([string]$parent, [string]$name) {
  $candidate = Join-Path $parent $name
  if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
  for ($index = 1; $index -lt 10000; $index++) {
    $candidate = Join-Path $parent ('{0}-{1}' -f $name, $index)
    if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
  }
  throw 'Unable to allocate a unique migration directory.'
}

function Get-UniqueFile([string]$directory, [string]$fileName) {
  $candidate = Join-Path $directory $fileName
  if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
  $stem = [IO.Path]::GetFileNameWithoutExtension($fileName)
  $extension = [IO.Path]::GetExtension($fileName)
  for ($index = 1; $index -lt 10000; $index++) {
    $candidate = Join-Path $directory ('{0}-{1}{2}' -f $stem, $index, $extension)
    if (-not (Test-Path -LiteralPath $candidate)) { return $candidate }
  }
  throw 'Unable to allocate a unique migration filename.'
}

function Get-SessionDate($payload, $file) {
  foreach ($field in @('collectionCompletedAt', 'createdAt', 'exportedAt')) {
    $value = [string]$payload.$field
    if ([string]::IsNullOrWhiteSpace($value)) { continue }
    try {
      return ([DateTimeOffset]::Parse($value, [Globalization.CultureInfo]::InvariantCulture)).LocalDateTime.ToString('yyyy-MM-dd')
    } catch { }
  }
  return $file.LastWriteTime.ToString('yyyy-MM-dd')
}

function Copy-Verified([string]$source, [string]$target) {
  [IO.File]::Copy($source, $target, $false)
  $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
  $targetHash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
  if ($sourceHash -ne $targetHash) {
    Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
    throw "Hash verification failed: $source"
  }
}

function Get-PngSize([byte[]]$bytes) {
  if ($bytes.Length -lt 24) { return @{ Width = $null; Height = $null } }
  $width = [BitConverter]::ToUInt32([byte[]]@($bytes[19], $bytes[18], $bytes[17], $bytes[16]), 0)
  $height = [BitConverter]::ToUInt32([byte[]]@($bytes[23], $bytes[22], $bytes[21], $bytes[20]), 0)
  return @{ Width = $width; Height = $height }
}

$result = [ordered]@{
  ok = $false
  sessions = 0
  moved = 0
  already = 0
  images_moved = 0
  images_extracted = 0
  manifest_rows_updated = 0
  errors = @()
  backup = $backupRoot
}
$sessionMap = @{}
$indexRecords = New-Object System.Collections.Generic.List[object]
$jsonFiles = @(Get-ChildItem -LiteralPath $uploads -Recurse -File -Filter '*.json' -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -notmatch '^(manifest|DEPLOY-|CLEANUP-|MIGRATE-)' })

try {
  foreach ($file in $jsonFiles) {
    try {
      $payload = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
      if ([string]::IsNullOrWhiteSpace([string]$payload.sessionId)) { continue }
      $participant = Get-SafeSegment ([string]$payload.participantId) 'unknown-participant'
      $date = Get-SessionDate $payload $file
      $stem = Get-SafeSegment ([IO.Path]::GetFileNameWithoutExtension($file.Name)) 'session'
      $dateParent = Join-Path (Join-Path $uploads $participant) $date
      New-Item -ItemType Directory -Path $dateParent -Force | Out-Null

      $sourceParent = $file.Directory.FullName
      $existing = @(Get-ChildItem -LiteralPath $dateParent -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName $file.Name) } | Select-Object -First 1)
      if ($existing.Count -gt 0 -and $existing[0].FullName -eq $sourceParent) {
        $targetDir = $existing[0].FullName
      } else {
        $targetDir = Get-UniqueDirectory $dateParent $stem
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
      }
      $targetJson = Join-Path $targetDir $file.Name

      if ($sourceParent -ne $targetDir) {
        $sourcePngs = @(Get-ChildItem -LiteralPath $sourceParent -File -Filter '*.png' -ErrorAction SilentlyContinue)
        Copy-Verified $file.FullName $targetJson
        foreach ($png in $sourcePngs) {
          $pngTarget = Get-UniqueFile $targetDir $png.Name
          Copy-Verified $png.FullName $pngTarget
          $result.images_moved += 1
        }
        Remove-Item -LiteralPath $file.FullName -Force
        foreach ($png in $sourcePngs) {
          Remove-Item -LiteralPath $png.FullName -Force -ErrorAction SilentlyContinue
        }
        $result.moved += 1
      } else {
        $result.already += 1
      }

      $relativeStored = $targetJson.Substring($uploads.Length).TrimStart('\', '/')
      $sessionMap[[string]$payload.sessionId] = $relativeStored
      $attempts = @($payload.attempts)
      for ($index = 0; $index -lt $attempts.Count; $index++) {
        $attempt = $attempts[$index]
        if ($null -eq $attempt -or $null -eq $attempt.image) { continue }
        $fallback = 'attempt-{0}.png' -f ($index + 1)
        $imageName = Get-SafeImageName ([string]$attempt.image.filename) $fallback
        $imagePath = Join-Path $targetDir $imageName
        if (-not (Test-Path -LiteralPath $imagePath)) {
          $dataUrl = [string]$attempt.image.dataUrl
          $prefix = 'data:image/png;base64,'
          if ($dataUrl.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $bytes = [Convert]::FromBase64String($dataUrl.Substring($prefix.Length))
            $imagePath = Get-UniqueFile $targetDir $imageName
            [IO.File]::WriteAllBytes($imagePath, $bytes)
            $result.images_extracted += 1
          } else {
            continue
          }
        }
        $bytes = [IO.File]::ReadAllBytes($imagePath)
        $size = Get-PngSize $bytes
        $relativeImage = $imagePath.Substring($uploads.Length).TrimStart('\', '/')
        $indexRecords.Add([PSCustomObject]@{
          uploaded_at = (Get-Item -LiteralPath $targetJson).LastWriteTime.ToString('o')
          stored_as = $relativeStored
          session_id = [string]$payload.sessionId
          participant_id = [string]$payload.participantId
          attempt_index = $index
          attempt_id = [string]$attempt.attemptId
          task_id = [string]$attempt.taskId
          image_file = $relativeImage
          bytes = $bytes.Length
          sha256 = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash
          width = $size.Width
          height = $size.Height
        })
      }
      $result.sessions += 1
    } catch {
      $result.errors += ("{0}: {1}" -f $file.FullName, ($_ | Out-String))
    }
  }

  $indexPath = Join-Path $uploads 'image-index.csv'
  $indexHeader = 'uploaded_at,stored_as,session_id,participant_id,attempt_index,attempt_id,task_id,image_file,bytes,sha256,width,height'
  $indexLines = @($indexHeader)
  foreach ($record in $indexRecords) {
    $csv = @($record | ConvertTo-Csv -NoTypeInformation)
    if ($csv.Count -gt 1) { $indexLines += $csv[1] }
  }
  [IO.File]::WriteAllText($indexPath, (($indexLines -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))

  foreach ($name in @('manifest.csv', 'manifest-v2.csv')) {
    $path = Join-Path $uploads $name
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $rows = @(Import-Csv -LiteralPath $path -Encoding UTF8 | Where-Object {
      $_.session_id -notmatch '^(MIGRATE|DEPLOY|CLEANUP)-'
    })
    foreach ($row in $rows) {
      if ($sessionMap.ContainsKey([string]$row.session_id)) {
        $row.stored_as = $sessionMap[[string]$row.session_id]
        $result.manifest_rows_updated += 1
      }
    }
    $rows | Export-Csv -LiteralPath $path -NoTypeInformation -Encoding UTF8
  }

  Get-ChildItem -LiteralPath $uploads -Directory -Recurse -ErrorAction SilentlyContinue |
    Sort-Object { $_.FullName.Length } -Descending |
    ForEach-Object {
      if (@(Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue).Count -eq 0) {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
      }
    }

  $result.ok = ($result.errors.Count -eq 0)
} catch {
  $result.errors += ($_ | Out-String)
} finally {
  $self = Get-ChildItem -LiteralPath $uploads -Recurse -Filter 'MIGRATE-*.json' -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty FullName
  if ($self) { Remove-Item -LiteralPath $self -Force -ErrorAction SilentlyContinue }
  $resultPath = Join-Path $Root 'updates\migration-result.json'
  New-Item -ItemType Directory -Path (Split-Path -Parent $resultPath) -Force | Out-Null
  $json = $result | ConvertTo-Json -Compress -Depth 6
  [IO.File]::WriteAllText($resultPath, $json, [Text.UTF8Encoding]::new($false))
  Write-Host ('MIGRATION_RESULT=' + $json)
}
