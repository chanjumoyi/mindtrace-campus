param(
    [ValidateSet("qwen", "mock")]
    [string]$LlmMode = "qwen",

    [string]$QwenModel = "qwen3.6-flash",
    [string]$QwenBaseUrl = "https://llm-hqvb1tgrlyoft4ye.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    [int]$QwenTimeoutSeconds = 30,
    [ValidateRange(1, 5)]
    [int]$QwenMaxAttempts = 3,
    [ValidateRange(30, 600)]
    [int]$StartupTimeoutSeconds = 240,
    [switch]$NoBuild,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $projectRoot "docker-compose.yml"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-DockerEngine {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Windows PowerShell 5.1 can turn native stderr into a terminating error
        # when the script-wide preference is Stop. A stopped engine is expected
        # here, so suppress that error only for this probe.
        $ErrorActionPreference = "SilentlyContinue"
        & docker info 1> $null 2> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

function Start-DockerEngine {
    if (Test-DockerEngine) {
        return
    }

    Write-Step "Docker Engine is not running; attempting to start Docker Desktop"
    try {
        & docker desktop start | Out-Host
    }
    catch {
        $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path -LiteralPath $dockerDesktop)) {
            throw "Docker Desktop could not be started. Open Docker Desktop manually and rerun this script."
        }
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden | Out-Null
    }

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-DockerEngine) {
            Write-Host "Docker Engine is ready." -ForegroundColor Green
            return
        }
        Write-Host "." -NoNewline -ForegroundColor DarkGray
    }

    throw "Docker Engine did not become ready within $StartupTimeoutSeconds seconds. Check Docker Desktop and WSL 2."
}

function Set-QwenEnvironment {
    $env:HANDWRITING_LLM_MODE = $LlmMode
    $env:QWEN_MODEL = $QwenModel
    $env:QWEN_BASE_URL = $QwenBaseUrl.TrimEnd("/")
    $env:QWEN_TIMEOUT_SECONDS = "$QwenTimeoutSeconds"
    $env:QWEN_MAX_ATTEMPTS = "$QwenMaxAttempts"

    if ($LlmMode -eq "mock") {
        Write-Host "Handwriting analysis mode: mock" -ForegroundColor Yellow
        return
    }

    if ([string]::IsNullOrWhiteSpace($env:QWEN_API_KEY)) {
        $secureKey = Read-Host "Enter Bailian API Key (input is hidden)" -AsSecureString
        $plainKey = [System.Net.NetworkCredential]::new("", $secureKey).Password.Trim()
        Remove-Variable secureKey
        if ([string]::IsNullOrWhiteSpace($plainKey)) {
            throw "QWEN_API_KEY cannot be empty when LlmMode is qwen."
        }
        $env:QWEN_API_KEY = $plainKey
        Remove-Variable plainKey
    }

    Write-Host "Handwriting analysis mode: qwen ($QwenModel)" -ForegroundColor Green
    Write-Host "API Key is used only by this process and is not written to a file." -ForegroundColor DarkGray
}

function Wait-MindLineServices {
    $services = [ordered]@{
        "Frontend"            = "http://127.0.0.1:8088/"
        "Backend"             = "http://127.0.0.1:8080/actuator/health"
        "Handwriting service" = "http://127.0.0.1:8091/api/v1/health"
        "Mock Agent"          = "http://127.0.0.1:8090/health"
    }
    $pending = @{}
    foreach ($name in $services.Keys) {
        $pending[$name] = $services[$name]
    }

    Write-Step "Waiting for all services to become available"
    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    while ($pending.Count -gt 0 -and (Get-Date) -lt $deadline) {
        foreach ($name in @($pending.Keys)) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri $pending[$name] -TimeoutSec 5
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                    Write-Host "[READY] $name - $($pending[$name])" -ForegroundColor Green
                    $pending.Remove($name)
                }
            }
            catch {
                # The service may still be starting. Retry until the shared deadline.
            }
        }
        if ($pending.Count -gt 0) {
            Start-Sleep -Seconds 3
        }
    }

    if ($pending.Count -gt 0) {
        Write-Host ""
        foreach ($name in $pending.Keys) {
            Write-Host "[NOT READY] $name - $($pending[$name])" -ForegroundColor Red
        }
        Write-Host ""
        Write-Host "Recent container logs:" -ForegroundColor Yellow
        & docker compose -f $composeFile logs --tail 80 postgres mock-agent handwriting-service backend frontend
        throw "Some services did not become ready within $StartupTimeoutSeconds seconds."
    }
}

if (-not (Test-Path -LiteralPath $composeFile)) {
    throw "docker-compose.yml not found: $composeFile"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or is not available in PATH. Install and start Docker Desktop first."
}

try {
    Push-Location $projectRoot

    Write-Step "Checking Docker Desktop"
    Start-DockerEngine
    Set-QwenEnvironment

    Write-Step "Validating Docker Compose configuration"
    & docker compose -f $composeFile config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose configuration validation failed."
    }

    Write-Step "Starting MindLine services"
    $composeArguments = @("compose", "-f", $composeFile, "up", "-d")
    if (-not $NoBuild) {
        $composeArguments += "--build"
    }
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed."
    }

    Wait-MindLineServices

    Write-Step "MindLine is ready"
    & docker compose -f $composeFile ps

    Write-Host ""
    Write-Host "Workspace:            http://localhost:8088" -ForegroundColor White
    Write-Host "Handwriting test:     http://localhost:8091/collector/" -ForegroundColor White
    Write-Host "Backend health:       http://localhost:8080/actuator/health" -ForegroundColor White
    Write-Host "Handwriting health:   http://localhost:8091/api/v1/health" -ForegroundColor White
    Write-Host ""
    Write-Host "Demo accounts:" -ForegroundColor Cyan
    Write-Host "  student_demo   / demo123"
    Write-Host "  counselor_demo / demo123"
    Write-Host "  admin_demo     / admin123"
    Write-Host ""
    Write-Host "Stop the project with: docker compose down" -ForegroundColor DarkGray

    if (-not $NoBrowser) {
        Start-Process "http://localhost:8088"
    }
}
catch {
    Write-Host ""
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
