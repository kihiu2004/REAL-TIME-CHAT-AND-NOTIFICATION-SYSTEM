# Wait until the ConnectHub API actually answers, then open the browser.
# Called by run.bat in a hidden PowerShell window.

$url = "http://127.0.0.1:8000"
$deadline = (Get-Date).AddSeconds(60)

while ((Get-Date) -lt $deadline) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing "$url/health" -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Start-Process $url
            break
        }
    } catch {
        # Server not ready yet; keep waiting.
    }
    Start-Sleep -Milliseconds 750
}
