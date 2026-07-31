param(
    [string]$BackendBaseUrl = "http://127.0.0.1:8080",
    [string]$FrontendUrl = "http://127.0.0.1:8088/",
    [string]$HandwritingHealthUrl = "http://127.0.0.1:8091/api/v1/health",
    [string]$AgentHealthUrl = "http://127.0.0.1:8090/health",
    [string]$Username = "student_demo",
    [string]$Password = "demo123"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$apiBaseUrl = $BackendBaseUrl.TrimEnd("/") + "/api/v1"

function Write-Check {
    param([string]$Message)
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Invoke-JsonRequest {
    param(
        [ValidateSet("Get", "Post", "Patch", "Delete")]
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [object]$Body
    )

    $parameters = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        TimeoutSec = 20
    }
    if ($null -ne $Body) {
        $parameters.ContentType = "application/json; charset=utf-8"
        $parameters.Body = $Body | ConvertTo-Json -Depth 10 -Compress
    }

    return Invoke-RestMethod @parameters
}

try {
    $frontend = Invoke-WebRequest -UseBasicParsing -Uri $FrontendUrl -TimeoutSec 10
    if ($frontend.StatusCode -lt 200 -or $frontend.StatusCode -ge 400) {
        throw "Frontend returned HTTP $($frontend.StatusCode)."
    }
    Write-Check "Frontend is reachable"

    $backendHealth = Invoke-JsonRequest -Method Get -Uri ($BackendBaseUrl.TrimEnd("/") + "/actuator/health")
    if ($backendHealth.status -ne "UP") {
        throw "Backend health is not UP."
    }
    Write-Check "Backend health is UP"

    $handwritingHealth = Invoke-JsonRequest -Method Get -Uri $HandwritingHealthUrl
    if ($handwritingHealth.status -ne "UP" -or $null -eq $handwritingHealth.llm) {
        throw "Handwriting health response is incomplete."
    }
    if ($handwritingHealth.llm.mode -eq "qwen" -and -not [bool]$handwritingHealth.llm.configured) {
        throw "Handwriting service reports qwen mode without a configured API key."
    }
    Write-Check ("Handwriting service is UP ({0}/{1})" -f $handwritingHealth.llm.provider, $handwritingHealth.llm.model)

    $agentHealth = Invoke-JsonRequest -Method Get -Uri $AgentHealthUrl
    if ($agentHealth.status -ne "UP" -or $null -eq $agentHealth.llm) {
        throw "AI companion health response is incomplete."
    }
    if ($agentHealth.llm.mode -eq "qwen" -and -not [bool]$agentHealth.llm.configured) {
        throw "AI companion service reports qwen mode without a configured API key."
    }
    Write-Check ("AI companion service is UP ({0}/{1})" -f $agentHealth.llm.provider, $agentHealth.llm.model)

    $login = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/auth/login" -Body @{
        username = $Username
        password = $Password
    }
    $token = [string]$login.data.accessToken
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "Login response did not include an access token."
    }
    $headers = @{ Authorization = "Bearer $token" }
    Write-Check "Demo user login succeeded"

    $profile = Invoke-JsonRequest -Method Get -Uri "$apiBaseUrl/me" -Headers $headers
    if ($profile.data.username -ne $Username) {
        throw "Profile username does not match the smoke-test account."
    }
    Write-Check "Profile endpoint returned the expected user"

    $navigation = Invoke-JsonRequest -Method Get -Uri "$apiBaseUrl/navigation" -Headers $headers
    if ($null -eq $navigation.data) {
        throw "Navigation response did not include data."
    }
    Write-Check "Navigation endpoint returned data"

    $task = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/tasks" -Headers $headers -Body @{
        moduleCode = "COMMON"
        taskType = "SMOKE_TEST"
        title = "MindLine Windows smoke test"
    }
    $taskId = [string]$task.data.id
    if ([string]::IsNullOrWhiteSpace($taskId)) {
        throw "Task creation response did not include an id."
    }

    $running = Invoke-JsonRequest -Method Patch -Uri "$apiBaseUrl/tasks/$taskId/status" -Headers $headers -Body @{
        status = "RUNNING"
        progress = 50
    }
    if ($running.data.status -ne "RUNNING") {
        throw "Task did not enter RUNNING state."
    }

    $completed = Invoke-JsonRequest -Method Patch -Uri "$apiBaseUrl/tasks/$taskId/status" -Headers $headers -Body @{
        status = "SUCCEEDED"
        progress = 100
    }
    if ($completed.data.status -ne "SUCCEEDED") {
        throw "Task did not enter SUCCEEDED state."
    }
    Write-Check "Task state machine completed"

    $idempotencyKey = "smoke-" + [guid]::NewGuid().ToString("N")
    $aiHeaders = @{
        Authorization = "Bearer $token"
        "Idempotency-Key" = $idempotencyKey
    }
    $aiBody = @{
        moduleCode = "COMMON"
        operation = "health"
        input = @{ source = "windows-smoke-test" }
    }
    $firstAiCall = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/ai/invoke" -Headers $aiHeaders -Body $aiBody
    $replayedAiCall = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/ai/invoke" -Headers $aiHeaders -Body $aiBody
    if ($firstAiCall.data.replayed -ne $false -or $replayedAiCall.data.replayed -ne $true) {
        throw "AI gateway idempotency replay check failed."
    }
    Write-Check "AI gateway call and idempotency replay succeeded"

    $analysisRef = "sandplay-smoke-" + [guid]::NewGuid().ToString("N")
    $analysisTask = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/tasks" -Headers $headers -Body @{
        moduleCode = "MULTIMODAL_AGENT"
        taskType = "SANDPLAY_ANALYSIS"
        title = "Sandplay tracked-analysis smoke test"
        requestRef = $analysisRef
    }
    $analysisTaskId = [string]$analysisTask.data.id
    [void](Invoke-JsonRequest -Method Patch -Uri "$apiBaseUrl/tasks/$analysisTaskId/status" -Headers $headers -Body @{
        status = "RUNNING"
        progress = 10
    })
    $analysisGateway = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/ai/invoke" -Headers @{
        Authorization = "Bearer $token"
        "Idempotency-Key" = $analysisRef
    } -Body @{
        moduleCode = "MULTIMODAL_AGENT"
        operation = "echo"
        input = @{
            requestedOperation = "sandplay.analyze"
            elements = @(@{ type = "tree"; x = 50; y = 50 })
        }
    }
    $analysisRecord = Invoke-JsonRequest -Method Post -Uri "$apiBaseUrl/analysis-records" -Headers $headers -Body @{
        moduleType = "SANDPLAY"
        taskId = $analysisTaskId
        sourceRef = $analysisRef
        title = "Sandplay tracked-analysis smoke test"
        observations = @("One centered tree element", "Smoke test stores no personal narrative")
        features = @{ count = 1; centerRatio = 1.0; quadrants = @(0, 0, 0, 1) }
        provider = [string]$agentHealth.llm.provider
        model = [string]$agentHealth.llm.model
        mockResult = ([string]$agentHealth.llm.provider -eq "mock")
    }
    $analysisRecordId = [string]$analysisRecord.data.id
    $analysisCompleted = Invoke-JsonRequest -Method Patch -Uri "$apiBaseUrl/tasks/$analysisTaskId/status" -Headers $headers -Body @{
        status = "SUCCEEDED"
        progress = 100
        resultRef = $analysisRecordId
    }
    if ($analysisCompleted.data.status -ne "SUCCEEDED") {
        throw "Tracked multimodal analysis task did not complete."
    }
    Write-Check "Sandplay analysis gateway and task tracking completed"
    $storedRecord = Invoke-JsonRequest -Method Get -Uri "$apiBaseUrl/analysis-records/$analysisRecordId" -Headers $headers
    if ($storedRecord.data.taskId -ne $analysisTaskId -or $storedRecord.data.observations.Count -lt 1) {
        throw "Persisted analysis record could not be read back."
    }
    [void](Invoke-JsonRequest -Method Get -Uri "$apiBaseUrl/analysis-records?moduleType=SANDPLAY" -Headers $headers)
    [void](Invoke-JsonRequest -Method Delete -Uri "$apiBaseUrl/analysis-records/$analysisRecordId" -Headers $headers)
    Write-Check "Sandplay analysis record persisted, queried, and deleted"

    Write-Host ""
    Write-Host "MindLine full-stack smoke test passed." -ForegroundColor Green
    Write-Host "Note: smoke-test tasks and related audit records were written to the local demo database." -ForegroundColor DarkGray
}
catch {
    Write-Host ""
    Write-Host "MindLine smoke test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
