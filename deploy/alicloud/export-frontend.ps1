param(
  [Parameter(Mandatory = $true)]
  [string]$ApiBaseUrl
)

$ErrorActionPreference = "Stop"
$frontendPath = Resolve-Path (Join-Path $PSScriptRoot "..\..\frontend")

Push-Location $frontendPath
try {
  $env:NEXT_PUBLIC_API_BASE_URL = $ApiBaseUrl
  Write-Host "Exporting frontend with NEXT_PUBLIC_API_BASE_URL=$ApiBaseUrl"
  npm ci
  npm run build
  Write-Host "Frontend export completed. Upload frontend/out/ to OSS."
} finally {
  Pop-Location
}
