$ErrorActionPreference = "Stop"

$exe = "C:\Users\Administrator\Desktop\JD\tools\cloudflared.exe"
$outLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-public-tunnel.out.log"
$errLog = "C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-public-tunnel.err.log"

Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item $outLog, $errLog -ErrorAction SilentlyContinue

for ($attempt = 1; $attempt -le 5; $attempt++) {
    $proc = Start-Process -FilePath $exe `
        -ArgumentList "tunnel", "--url", "http://localhost:8010", "--no-autoupdate" `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -WindowStyle Hidden `
        -PassThru

    $url = $null

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1

        if (Test-Path $errLog) {
            $match = Select-String -Path $errLog -Pattern "https://[-a-z0-9]+\\.trycloudflare\\.com" -AllMatches -ErrorAction SilentlyContinue | Select-Object -Last 1
            if ($match) {
                $url = $match.Matches[-1].Value
                break
            }

            $content = Get-Content $errLog -Raw -ErrorAction SilentlyContinue
            if ($content -match "failed to unmarshal quick Tunnel" -or $content -match "500 Internal Server Error") {
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

    if (-not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    Start-Sleep -Seconds 2
}

Write-Output "URL="
Write-Output "PID="
if (Test-Path $errLog) {
    Get-Content $errLog -Tail 20
}
exit 1
