$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputDirectory = Join-Path $env:TEMP "agentsinc-ara3d-agent-avatars"
$targetDirectory = Join-Path $repoRoot "frontend/public/models/agents"
$manifestPath = Join-Path $targetDirectory "manifest.json"

$characters = @(
    @{ Id = "ceo";        Seed = 9101 },
    @{ Id = "team_lead";  Seed = 9102 },
    @{ Id = "developer";  Seed = 9103 },
    @{ Id = "designer";   Seed = 9104 },
    @{ Id = "researcher"; Seed = 9105 },
    @{ Id = "tester";     Seed = 9106 }
)

$seedRange = "$($characters[0].Seed)-$($characters[-1].Seed)"
$animations = "idle,walk,run,talk,sit_down,sit_idle,stand_up"

Write-Host ""
Write-Host "AgentSINC realistic avatar generator" -ForegroundColor Cyan
Write-Host "Six local, rigged human characters will be generated."
Write-Host "The first run downloads Ara 3D Gen and its character data; no API key or paid avatar service is used."
Write-Host ""

if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeMajor = [int]((node --version).TrimStart("v").Split(".")[0])
    if ($nodeMajor -lt 20) {
        throw "Node.js 20 or newer is required. Current version: $(node --version)"
    }
} else {
    throw "Node.js 20 or newer was not found on PATH."
}

if (Test-Path $outputDirectory) {
    Remove-Item $outputDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

Write-Host "Generating six high-detail GLB characters..." -ForegroundColor Yellow
& npx --yes ara3d export --random $seedRange --formats glb --detail high --animations $animations --out $outputDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Ara 3D Gen failed with exit code $LASTEXITCODE. Existing avatar assets were not marked ready."
}

$generatedFiles = @{}
foreach ($character in $characters) {
    $expectedName = "random_$($character.Seed).glb"
    $sourceFile = Get-ChildItem -Path $outputDirectory -Filter $expectedName -File -Recurse |
        Select-Object -First 1

    if (-not $sourceFile) {
        throw "Expected generated model '$expectedName' was not found in $outputDirectory."
    }

    $destination = Join-Path $targetDirectory "$($character.Id).glb"
    Copy-Item -LiteralPath $sourceFile.FullName -Destination $destination -Force
    $generatedFiles[$character.Id] = [PSCustomObject]@{
        file = "$($character.Id).glb"
        seed = $character.Seed
        bytes = (Get-Item -LiteralPath $destination).Length
    }

    Write-Host ("Created {0} ({1:N1} MB)" -f $character.Id, ((Get-Item -LiteralPath $destination).Length / 1MB)) -ForegroundColor Green
}

$manifest = [PSCustomObject]@{
    version = 1
    enabled = $true
    source = "Ara 3D Gen / MakeHuman CC0 assets"
    detail = "high"
    animations = @("idle", "walk", "run", "talk", "sit_down", "sit_idle", "stand_up")
    agents = @($characters | ForEach-Object { $_.Id })
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    models = $generatedFiles
}
$temporaryManifest = "$manifestPath.tmp"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $temporaryManifest -Encoding UTF8
Move-Item -LiteralPath $temporaryManifest -Destination $manifestPath -Force

Write-Host ""
Write-Host "All six realistic agent models are ready." -ForegroundColor Green
Write-Host "Restart the AgentSINC frontend and reload http://localhost:3000."
Write-Host "Generated local assets: $targetDirectory"
Write-Host ""
Write-Host "For a hosted deployment, add the six .glb files and manifest.json to Git before deploying."
