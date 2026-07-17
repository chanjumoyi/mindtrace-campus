param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$collectorPath = Join-Path $projectRoot "local\ai-lab\handwriting\collector"

if (-not (Test-Path -LiteralPath (Join-Path $collectorPath "index.html"))) {
    throw "Collector not found: $collectorPath"
}

$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $listener) {
    $process = Start-Process `
        -FilePath "python" `
        -ArgumentList "-m", "http.server", "$Port", "--bind", "0.0.0.0" `
        -WorkingDirectory $collectorPath `
        -WindowStyle Hidden `
        -PassThru
    Start-Sleep -Milliseconds 500
    Write-Host "Collector started. PID: $($process.Id)" -ForegroundColor Green
} else {
    Write-Host "Port $Port is already listening. PID: $($listener.OwningProcess)" -ForegroundColor Yellow
}

$network = Get-NetIPConfiguration |
    Where-Object {
        $_.IPv4DefaultGateway -and
        $_.NetAdapter.Status -eq "Up" -and
        $_.IPv4Address.IPAddress -notlike "169.254.*"
    } |
    Select-Object -First 1

if (-not $network) {
    Write-Host "No LAN IPv4 address found. Connect this PC to Wi-Fi first." -ForegroundColor Red
    exit 1
}

$ipAddress = $network.IPv4Address.IPAddress
$url = "http://${ipAddress}:$Port"

Write-Host ""
Write-Host "Open this URL on the tablet:" -ForegroundColor Cyan
Write-Host $url -ForegroundColor White
Write-Host ""
Write-Host "Keep the tablet and PC on the same Wi-Fi. Leave PC debug mode unchecked on the tablet."

