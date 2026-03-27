$ErrorActionPreference = "Stop"

$outLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-localtunnel.out.log"
$errLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-localtunnel.err.log"

Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*node.exe" } | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue

$proc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npx --yes localtunnel --port 8010" `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

$url = $null
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Seconds 1

    if (Test-Path $outLog) {
        $match = Select-String -Path $outLog -Pattern "https://[-a-z0-9]+\\.loca\\.lt" -AllMatches -ErrorAction SilentlyContinue | Select-Object -Last 1
        if ($match) {
            $url = $match.Matches[-1].Value
            break
        }
    }

    if (Test-Path $errLog) {
        $match = Select-String -Path $errLog -Pattern "https://[-a-z0-9]+\\.loca\\.lt" -AllMatches -ErrorAction SilentlyContinue | Select-Object -Last 1
        if ($match) {
            $url = $match.Matches[-1].Value
            break
        }
    }

    if ($proc.HasExited) {
        break
    }
}

if ($url) {
    Write-Output "URL=$url"
    Write-Output "PID=$($proc.Id)"
    exit 0
}

Write-Output "URL="
Write-Output "PID=$($proc.Id)"
if (Test-Path $outLog) {
    Get-Content $outLog -Tail 20
}
if (Test-Path $errLog) {
    Get-Content $errLog -Tail 20
}
exit 1
