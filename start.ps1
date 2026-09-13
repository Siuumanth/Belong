# Belong Environment Start Script
# Spins up PostgreSQL with pgvector and verifies readiness

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       Starting Belong Environment       " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check if Docker CLI is available
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Check if Docker daemon is running
Write-Host "Checking Docker daemon..." -ForegroundColor Cyan
$daemonReady = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $daemonReady = $true
    }
} catch {
    $daemonReady = $false
}

if (-not $daemonReady) {
    Write-Host "[NOTICE] Docker Desktop daemon is not currently running." -ForegroundColor Yellow
    Write-Host "Attempting to launch Docker Desktop..." -ForegroundColor Yellow
    $dockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopPath) {
        Start-Process $dockerDesktopPath
        Write-Host "Waiting for Docker daemon to initialize (this may take 20-30s)..." -ForegroundColor Cyan
        $retries = 30
        while ($retries -gt 0) {
            Start-Sleep -Seconds 2
            $null = docker info 2>&1
            if ($LASTEXITCODE -eq 0) {
                $daemonReady = $true
                break
            }
            $retries--
            Write-Host -NoNewline "."
        }
        Write-Host ""
    }
}

if (-not $daemonReady) {
    Write-Host "[ERROR] Could not connect to Docker daemon. Please ensure Docker Desktop is started manually, then re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Docker daemon is running." -ForegroundColor Green

# Spin up containers
Write-Host "`nStarting containers via Docker Compose..." -ForegroundColor Cyan
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start Docker Compose services." -ForegroundColor Red
    exit 1
}

Write-Host "`nWaiting for PostgreSQL + pgvector to be ready..." -ForegroundColor Cyan
$maxAttempts = 30
$attempt = 1
$isReady = $false

while ($attempt -le $maxAttempts) {
    $status = docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' belong-postgres 2>$null
    if ($status -eq "healthy" -or $status -eq "running") {
        # Check pg_isready
        $pgReady = docker exec belong-postgres pg_isready -U belong_user -d belong 2>$null
        if ($LASTEXITCODE -eq 0) {
            $isReady = $true
            break
        }
    }
    Write-Host "Waiting for database readiness (Attempt $attempt/$maxAttempts)..."
    Start-Sleep -Seconds 2
    $attempt++
}

if (-not $isReady) {
    Write-Host "[ERROR] PostgreSQL did not become ready within timeout." -ForegroundColor Red
    docker logs belong-postgres --tail 20
    exit 1
}

Write-Host "[OK] Database container is healthy and ready!" -ForegroundColor Green

# Run verification script
$verifyScript = Join-Path $PSScriptRoot "scripts\verify_db.ps1"
if (Test-Path $verifyScript) {
    & $verifyScript
}
