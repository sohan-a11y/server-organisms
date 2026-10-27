# Server Organisms - one-command install (Windows). Your data stays on your server.
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker required: https://docs.docker.com/get-docker/" }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Select-String -Path .env -Pattern "^BROKER_TOKEN=" -Quiet)) {
  $token = -join ((1..48) | ForEach-Object { "{0:x}" -f (Get-Random -Maximum 16) })
  Add-Content .env "`nBROKER_TOKEN=$token"
  Write-Host "Generated private BROKER_TOKEN in .env (keep secret)"
}
docker compose up --build -d
$tokLine = Get-Content .env | Where-Object { $_ -match "^BROKER_TOKEN=" } | Select-Object -First 1
$tok = $tokLine -replace "^BROKER_TOKEN=", ""
Write-Host ""
Write-Host "OPEN YOUR DASHBOARD (judge/demo link, contains your private token - do not share publicly):"
Write-Host "http://127.0.0.1:18000/?token=$tok"
Write-Host "(Optional: set META_API_KEY in .env for live Muse, then: docker compose up -d)"
