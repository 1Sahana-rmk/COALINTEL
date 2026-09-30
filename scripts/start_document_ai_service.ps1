param(
    [int]$Port = 8765,
    [string]$HostAddress = "127.0.0.1",
    [string]$LogPath = ""
)

$ErrorActionPreference = "Continue"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$pythonPath = Join-Path $repoRoot ".venv-paddle312\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Error "Isolated Paddle Python was not found at $pythonPath"
    exit 2
}

$env:DOCUMENT_AI_HOST = $HostAddress
$env:DOCUMENT_AI_PORT = [string]$Port
$env:DOCUMENT_AI_DEVICE = if ($env:DOCUMENT_AI_DEVICE) { $env:DOCUMENT_AI_DEVICE } else { "cpu" }
$env:DOCUMENT_AI_CPU_THREADS = if ($env:DOCUMENT_AI_CPU_THREADS) { $env:DOCUMENT_AI_CPU_THREADS } else { "2" }
$env:DOCUMENT_AI_DISABLE_MKLDNN = if ($env:DOCUMENT_AI_DISABLE_MKLDNN) { $env:DOCUMENT_AI_DISABLE_MKLDNN } else { "true" }
$env:PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK = "True"

Push-Location $repoRoot
try {
    Write-Host "Starting COALINTEL Document AI service in the foreground on $HostAddress`:$Port"
    Write-Host "Python: $pythonPath"
    if ($LogPath) {
        $resolvedLogPath = [System.IO.Path]::GetFullPath($LogPath)
        Write-Host "Log: $resolvedLogPath"
        & $pythonPath -u -m document_ai_service.server 2>&1 | Tee-Object -FilePath $resolvedLogPath
    } else {
        & $pythonPath -u -m document_ai_service.server
    }
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Error "Document AI service exited with code $exitCode"
    }
    exit $exitCode
} finally {
    Pop-Location
}
