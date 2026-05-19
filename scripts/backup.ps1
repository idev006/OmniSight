# OmniSight Windows backup script
# Backs up: PostgreSQL, Qdrant vectors, storage files
# Retention: 7 days (configurable via $KeepDays)
#
# Usage (from project root):
#   powershell -ExecutionPolicy Bypass -File scripts\backup.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\backup.ps1 -SkipQdrant
#
# Requires: Docker Desktop running, Compose stack up

param(
    [switch]$SkipQdrant,
    [string]$BackupDir = ".\backups",
    [int]$KeepDays = 7,
    [string]$PostgresDb   = $env:POSTGRES_DB   ?? "omnisight",
    [string]$PostgresUser = $env:POSTGRES_USER  ?? "omnisight",
    [string]$QdrantUrl    = $env:QDRANT_URL     ?? "http://localhost:6333",
    [string]$Collection   = $env:QDRANT_COLLECTION ?? "face_registry"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Dest  = Join-Path $BackupDir $Stamp
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

Write-Host "=== OmniSight Backup — $Stamp ===" -ForegroundColor Cyan

# ── 1. PostgreSQL ──────────────────────────────────────────────────────────
Write-Host "[1/3] PostgreSQL dump..."
$pgFile = Join-Path $Dest "postgres.sql.gz"
docker compose exec -T postgres `
    pg_dump -U $PostgresUser $PostgresDb | `
    & { param($in) $in } | `
    gzip | Set-Content -Path $pgFile -AsByteStream
$size = (Get-Item $pgFile).Length / 1KB
Write-Host "      -> $pgFile ($([math]::Round($size,1)) KB)"

# ── 2. Qdrant snapshot ─────────────────────────────────────────────────────
if (-not $SkipQdrant) {
    Write-Host "[2/3] Qdrant snapshot..."
    try {
        $snapResp = Invoke-RestMethod -Method Post `
            -Uri "$QdrantUrl/collections/$Collection/snapshots" `
            -ErrorAction Stop
        $snapName = $snapResp.result.name

        $snapFile = Join-Path $Dest "qdrant_snapshot.snapshot"
        Invoke-WebRequest -Uri "$QdrantUrl/collections/$Collection/snapshots/$snapName" `
            -OutFile $snapFile -ErrorAction Stop

        # Cleanup from server
        Invoke-RestMethod -Method Delete `
            -Uri "$QdrantUrl/collections/$Collection/snapshots/$snapName" `
            -ErrorAction SilentlyContinue | Out-Null

        $size = (Get-Item $snapFile).Length / 1KB
        Write-Host "      -> $snapFile ($([math]::Round($size,1)) KB)"
    } catch {
        Write-Warning "      Qdrant snapshot failed: $_. Is the service running at $QdrantUrl ?"
    }
} else {
    Write-Host "[2/3] Qdrant snapshot — skipped (-SkipQdrant)"
}

# ── 3. Storage files ───────────────────────────────────────────────────────
Write-Host "[3/3] Storage files..."
$StorageSrc = ".\data\storage"
if (Test-Path $StorageSrc) {
    $storageFile = Join-Path $Dest "storage.zip"
    Compress-Archive -Path $StorageSrc -DestinationPath $storageFile -Force
    $size = (Get-Item $storageFile).Length / 1MB
    Write-Host "      -> $storageFile ($([math]::Round($size,2)) MB)"
} else {
    Write-Warning "      .\data\storage not found — skipping storage backup."
}

# ── 4. Rotate old backups ──────────────────────────────────────────────────
Write-Host "[4] Rotating backups older than $KeepDays days..."
$Cutoff = (Get-Date).AddDays(-$KeepDays)
Get-ChildItem -Path $BackupDir -Directory |
    Where-Object { $_.CreationTime -lt $Cutoff } |
    ForEach-Object {
        Write-Host "      Removing $($_.Name)"
        Remove-Item -Recurse -Force $_.FullName
    }

$totalMB = [math]::Round((Get-ChildItem $Dest -Recurse | Measure-Object Length -Sum).Sum / 1MB, 2)
Write-Host ""
Write-Host "=== Backup complete: $Dest ===" -ForegroundColor Green
Write-Host "    Total: ${totalMB} MB"
