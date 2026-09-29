<#
.SYNOPSIS
    Reconstrói e recria o container do frontend garantindo que o Docker sirva a última versão.

.DESCRIPTION
    Usa `docker compose build --no-cache frontend` seguido de `up -d --force-recreate frontend`.
    Assim, mesmo com camadas Docker em cache, o Angular é buildado novamente e o container é substituído.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\rebuild-frontend.ps1
#>

[CmdletBinding()]
param(
    [switch]$NoCache
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Rebuild frontend (Docker)" -ForegroundColor Cyan

if ($NoCache) {
    docker compose build --no-cache frontend
} else {
    docker compose build --pull frontend
}
if ($LASTEXITCODE -ne 0) { throw "build falhou" }

docker compose up -d --force-recreate --no-deps frontend
if ($LASTEXITCODE -ne 0) { throw "up falhou" }

Start-Sleep -Seconds 2
$status = docker compose ps --format "{{.Name}} {{.Status}}" | Select-String frontend
Write-Host ""
Write-Host "==> $status" -ForegroundColor Green
Write-Host "==> Abra http://127.0.0.1:8081 e use Ctrl+F5 no navegador para descartar cache local."
