$ErrorActionPreference = "Stop"

$ssh = "C:\Windows\System32\OpenSSH\ssh.exe"
$outLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-pinggy.out.log"
$errLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-pinggy.err.log"

Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue

$proc = Start-Process -FilePath $ssh `
    -ArgumentList "-p", "443", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R0:localhost:8010", "a.pinggy.io" `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog `
    -WindowStyle Hidden `
    -PassThru

$url = $null
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1

    foreach ($log in @($outLog, $errLog)) {
        if (Test-Path $log) {
            $match = Select-String -Path $log -Pattern "https://[-a-zA-Z0-9.]+pinggy[.]link" -AllMatches -ErrorAction SilentlyContinue | Select-Object -Last 1
            if ($match) {
                $url = $match.Matches[-1].Value
                break
            }
        }
    }

    if ($url) {
        break
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
    Get-Content $outLog -Tail 30
}
if (Test-Path $errLog) {
    Get-Content $errLog -Tail 30
}
exit 1
