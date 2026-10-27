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
Write-Host "Organisms live: dashboard http://127.0.0.1:18000  (set META_API_KEY in .env for live Muse, then: docker compose up -d)"
