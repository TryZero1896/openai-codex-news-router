param(
  [string]$InstallDir = "$HOME\openai-codex-news-router",
  [int]$Minutes = 30,
  [switch]$EnableInjection
)
$ErrorActionPreference = "Stop"
$cli = Join-Path $InstallDir "news_router\cli.py"
$config = Join-Path $InstallDir "windows\config.json"
if (!(Test-Path $config)) { throw "Zuerst windows/config.example.json als config.json kopieren und die Codex-Thread-IDs eintragen." }
if (!(Get-Command py -ErrorAction SilentlyContinue)) { throw "Python Launcher 'py' nicht gefunden. Python 3.10+ installieren." }
$flag = if ($EnableInjection) { " --apply" } else { "" }
$cmd = "Set-Location '$($InstallDir.Replace("'","''"))'; py -m news_router.cli dispatch --config 'windows/config.json'$flag"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$cmd`"" -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $Minutes)
Register-ScheduledTask -TaskName 'OpenAI-Codex-News-Router' -Description 'Checks official OpenAI news and optionally injects into configured local Codex threads' -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "Windows-Aufgabe erstellt: OpenAI-Codex-News-Router (alle $Minutes Minuten)"
if (!$EnableInjection) { Write-Host 'Sicherheitsmodus: Nur Simulation. Nach erfolgreichem Test mit -EnableInjection erneut registrieren.' }
