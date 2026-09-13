# Belong Database Verification Script
param (
    [string]$ContainerName = "belong-postgres",
    [string]$DbUser = "belong_user",
    [string]$DbName = "belong"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   Belong Database Readiness Check       " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check if container is running
$containerStatus = docker inspect -f '{{.State.Status}}' $ContainerName 2>$null
if ($containerStatus -ne "running") {
    Write-Host "ERROR: Container '$ContainerName' is not running (Status: $containerStatus)." -ForegroundColor Red
    Write-Host "Please start the container using: docker compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "Container '$ContainerName' is RUNNING." -ForegroundColor Green

# 2. Check pg_isready inside container
Write-Host "Checking PostgreSQL readiness..." -ForegroundColor Cyan
$ready = docker exec $ContainerName pg_isready -U $DbUser -d $DbName
if ($LASTEXITCODE -ne 0) {
    Write-Host "PostgreSQL is not ready yet: $ready" -ForegroundColor Red
    exit 1
}
Write-Host "PostgreSQL is accepting connections." -ForegroundColor Green

# 3. Execute verification SQL
Write-Host "`nRunning database verification queries..." -ForegroundColor Cyan
$sqlPath = Join-Path $PSScriptRoot "verify_db.sql"
if (Test-Path $sqlPath) {
    Get-Content $sqlPath | docker exec -i $ContainerName psql -U $DbUser -d $DbName
} else {
    docker exec $ContainerName psql -U $DbUser -d $DbName -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
    docker exec $ContainerName psql -U $DbUser -d $DbName -c "\dt"
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] PostgreSQL + pgvector is fully configured and ready for Belong MVP!" -ForegroundColor Green
} else {
    Write-Host "`n[FAIL] Database verification failed with exit code $LASTEXITCODE." -ForegroundColor Red
}
