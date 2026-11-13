# Run explicitly on Windows in the extracted project folder, after inspecting README.
param([string]$Account = 'TryZero1896')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if (!(Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) fehlt. winget install GitHub.cli' }
if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git fehlt. winget install Git.Git' }
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Bitte vorher gh auth login ausführen' }
Write-Warning 'Dieser Schritt erstellt ein ÖFFENTLICHES Repository. Nur offizielle OpenAI-News und generischer Code dürfen hinein – KEINE persönlichen Daten oder Thread-IDs.'
$confirm = Read-Host "Repository $Account/openai-codex-news-router wirklich ÖFFENTLICH erstellen? (JA)"
if ($confirm -cne 'JA') { throw 'Abgebrochen.' }
if (!(Test-Path .git)) { & git init -b main }
& git add .
& git commit -m 'feat: initialize OpenAI Codex news router'
& gh repo create "$Account/openai-codex-news-router" --public --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'GitHub-Repository konnte nicht erstellt werden.' }
Write-Host "Feed bereit: https://raw.githubusercontent.com/$Account/openai-codex-news-router/main/feed.json"
Write-Host 'In GitHub > Settings > Actions > General: GitHub Actions darf den Inhalt schreiben (Read and write permissions).'
