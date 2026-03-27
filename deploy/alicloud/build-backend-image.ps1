param(
  [string]$ImageTag = "resume-screening-api:latest"
)

$ErrorActionPreference = "Stop"
$backendPath = Resolve-Path (Join-Path $PSScriptRoot "..\..\backend")

Push-Location $backendPath
try {
  Write-Host "Building backend image: $ImageTag"
  docker build -t $ImageTag .
  Write-Host "Backend image build completed."
} finally {
  Pop-Location
}
