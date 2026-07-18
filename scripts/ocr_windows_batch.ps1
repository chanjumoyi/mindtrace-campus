param(
  [Parameter(Mandatory = $true)][string]$ImageDirectory,
  [Parameter(Mandatory = $true)][string]$OutputJsonl,
  [string]$Language = 'zh-Hans'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Await-WinRt {
  param([Parameter(Mandatory = $true)]$Operation, [Parameter(Mandatory = $true)][Type]$ResultType)
  $method = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
      $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
  $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
  $task.Wait()
  return $task.Result
}

$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$languageObject = [Windows.Globalization.Language]::new($Language)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($languageObject)
if ($null -eq $engine) { throw "Windows OCR language is unavailable: $Language" }

$images = Get-ChildItem -LiteralPath $ImageDirectory -Filter 'page-*.png' | Sort-Object Name
$outputPath = [IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputJsonl))
New-Item -ItemType Directory -Force -Path (Split-Path $outputPath) | Out-Null
$writer = [IO.StreamWriter]::new($outputPath, $false, [Text.UTF8Encoding]::new($false))
try {
  foreach ($image in $images) {
    $match = [regex]::Match($image.BaseName, '(\d+)$')
    if (-not $match.Success) { continue }
    $page = [int]$match.Groups[1].Value
    $file = Await-WinRt ([Windows.Storage.StorageFile]::GetFileFromPathAsync($image.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await-WinRt ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    try {
      $decoder = Await-WinRt ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
      $bitmap = Await-WinRt ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
      try {
        $result = Await-WinRt ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $record = [ordered]@{ pdfPage = $page; text = $result.Text; image = $image.Name }
        $writer.WriteLine(($record | ConvertTo-Json -Compress))
      } finally {
        if ($null -ne $bitmap) { $bitmap.Dispose() }
      }
    } finally {
      $stream.Dispose()
    }
  }
} finally {
  $writer.Dispose()
}

[pscustomobject]@{ pages = $images.Count; output = $outputPath }
