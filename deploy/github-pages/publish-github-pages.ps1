param(
    [string]$RepoName = "resume-screening-mvp",
    [ValidateSet("private", "public")]
    [string]$Visibility = "private",
    [string]$ApiBaseUrl = ""
)

$ErrorActionPreference = "Stop"

Set-Location "C:\Users\Administrator\Desktop\JD"

gh auth status | Out-Null

$owner = gh api user -q .login

if (-not (git remote | Select-String '^origin$' -Quiet)) {
    gh repo create $RepoName --$Visibility --source . --remote origin --push
} else {
    git push -u origin main
}

if ($ApiBaseUrl.Trim()) {
    gh variable set NEXT_PUBLIC_API_BASE_URL --repo "$owner/$RepoName" --body $ApiBaseUrl
}

try {
    gh api --method POST "/repos/$owner/$RepoName/pages" -f build_type=workflow | Out-Null
} catch {
    Write-Host "GitHub Pages may already be configured. Continuing..."
}

Write-Host "Repository: https://github.com/$owner/$RepoName"
Write-Host "Pages will deploy from .github/workflows/pages.yml after the workflow runs."
