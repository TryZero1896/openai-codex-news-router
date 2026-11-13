# OpenAI → Codex News Router (v0.1 – Installationspaket)

**Ziel:** Offizielle OpenAI-Meldungen aus einem zentralen Feed an ausgewählte **lokale Codex-Threads** geben; **Codex Cloud** prüft bei Start einer neuen Aufgabe nur projektbezogene Meldungen. Störungen, Entwarnungen und Codex-Releases werden dedupliziert.

**Stand:** Code und Unit-Tests liegen vor. **Noch nicht live eingerichtet.** Es ist kein Windows-PC und kein neues GitHub-Repository verbunden. Der bestehende ChatGPT-Tagesnews-Chat kann erst nach Einrichtung des GitHub-Feeds dorthin schreiben; die Verbindung aus der ChatGPT-Aufgabe muss gesondert autorisiert und getestet werden.

## Architektur

```text
Offizielles OpenAI Status API ─┐
OpenAI/Codex GitHub Releases ──┼─> GitHub Actions (alle 3h) ─> feed.json
Kuratierte ChatGPT-Tagesnews ──┘                        (vorerst separater Publish-Schritt)
                                                            |
                          +---------------------------------+---------------------+
                          |                                                       |
            Windows: Python + Codex App Server                    Codex Cloud: AGENTS.md
            gezielte thread/inject_items                           bei jedem neuen Lauf
            (nur explizite Thread-IDs)                            liest relevanten Feed
```

## Einmalige Einrichtung

1. **Windows:** Python >= 3.10, Git und GitHub CLI installieren; Codex CLI installiert und mit demselben ChatGPT-Konto angemeldet.
   ```powershell
   winget install Git.Git GitHub.cli Python.Python.3.12
   npm install -g @openai/codex
   gh auth login
   ```
2. ZIP nach `C:\Users\<Du>\openai-codex-news-router` entpacken. Die PowerShell-Datei `windows/create-feed-repo.ps1` prüfen. Dann im Projektordner explizit ausführen:
   ```powershell
   .\windows\create-feed-repo.ps1
   ```
   Sie legt **nach einer expliziten Bestätigung** das **öffentliche** Repository `TryZero1896/openai-codex-news-router` an. Dort stehen nur öffentliche OpenAI-News, keine privaten Thread-IDs. Alternative **privat**: Repository selbst anlegen; dann müssen Windows- und Cloud-Lesezugriff authentifiziert werden (nicht in v0.1 enthalten).
3. GitHub Actions für das Feed-Repository aktivieren und `Settings → Actions → General → Workflow permissions → Read and write permissions` gestatten. Workflow `OpenAI official updates` einmal über **Run workflow** testen. Er sammelt automatisiert Codex-Releases und Statusmeldungen; der Feed wird danach alle 3 Stunden aktualisiert.
4. Lokale Codex-Threads anzeigen:
   ```powershell
   py -m news_router.cli threads
   ```
   `windows/config.example.json` zu `windows/config.json` kopieren, Feed-URL und die **wirklichen** lokalen Thread-IDs eintragen. Pro Thread gewünschte `topics` setzen. Es werden **nur** explizit eingetragene Threads beliefert.
5. **Trockenlauf zuerst:**
   ```powershell
   py -m news_router.cli dispatch --config windows/config.json
   ```
   Mit einem **unwichtigen Test-Thread** und einem überprüften Testereignis (separat von echten Nachrichten) testen:
   ```powershell
   py -m news_router.cli dispatch --config windows/config.json --apply
   ```
   `--apply` schreibt in den gespeicherten Modellkontext des Threads. Die Anzeige in einer bereits offenen Codex-Desktop-Oberfläche ist **nicht garantiert**. Vor Nutzung auf wichtigen Chats prüfen, ob der Thread korrekt fortgesetzt werden kann, und ggf. Codex Desktop neu öffnen.
6. Optional Windows-Aufgabe für 30-minütliche Prüfung registrieren (erst Dry-Run):
   ```powershell
   .\windows\register-task.ps1
   ```
   **Erst nach erfolgreichem Test** die echte Injektion einschalten:
   ```powershell
   .\windows\register-task.ps1 -EnableInjection
   ```
   PC muss eingeschaltet und Zugang zu GitHub bestehen. Status: Windows Aufgabenplanung → `OpenAI-Codex-News-Router`.
7. **Codex Cloud:** Für jedes ausgewählte Projekt `cloud/check_news.py` in dessen Repository unter `.codex/news/check_news.py` kopieren. `cloud/AGENTS-snippet.md` an bestehende `AGENTS.md` **anhängen**, dabei Account und Themen anpassen. Nicht ersetzen! Nach Commit und nächster Codex-Cloud-Aufgabe liest Codex die Meldungen, **sofern Internetzugriff in seiner Umgebung zugelassen ist**. Es erfolgt **keine direkte Nachricht** in bereits laufende Cloud-Chats.

## Automatische Zuordnung

Eintragen von Themen in `windows/config.json` bzw. `AGENTS.md` pro Projekt, z. B.:

- AA: `codex,api,images,security,windows`
- NEXIQA: `chatgpt,work,connectors,api`
- Home Assistant: `api,connectors,security`

Nichts wird an nicht registrierte Chats übermittelt. Meldungen werden mit ID/Updatezeit/Status dedupliziert, während aktive Störungen erneut als **Entwarnung** zugestellt werden können.

## Verbindung zur täglichen News-Aufgabe (noch offen)

Sobald das Feed-Repository existiert, kann der bestehende ChatGPT-Tagesnews-Task als weitere Quelle eingerichtet werden: Nach **offiziell verifizierter** Meldung einen Eintrag im Event-Schema mit korrektem `id`, `updated_at`, `topics`, `kind`, `status` und Originalquellenlink erstellen und über den verbundenen GitHub-Connector die `feed.json` im News-Router-Repository aktualisieren. Wichtig: GitHub-Datei zuerst lesen, mit vorhandenem Blob-SHA aktualisieren, nicht versehentlich ältere Updates überschreiben; erforderliche Connector-Genehmigungen prüfen. Alternativ ein Event als JSON lokal speichern und publizieren:

```powershell
py -m news_router.cli publish --feed feed.json --file event.json
git add feed.json; git commit -m 'news: curated update'; git push
```

**Wichtig:** Diese Integration ist **nicht** durch die Existenz dieses ZIPs automatisch aktiviert. ChatGPT-Unterhaltungen erzeugen nicht von selbst Webhooks. Ein manueller/automatisierter Publish-Schritt muss eingerichtet werden. Der GitHub-Actions-Collector deckt bis dahin **nur** offizielle Störungen und Codex-GitHub-Releases ab, nicht alle OpenAI-News.

## Sicherheit und Grenzen

- Feed-Inhalte sind **Daten**, keine privilegierten Anweisungen; keine automatischen Änderungen am Code.
- Externe Quelle wird für die lokale Injektion auf offizielle Domains beschränkt. Keine persönlichen Projektdaten im öffentlichen Feed.
- `thread/inject_items` schreibt ohne neuen Turn in den Modellkontext, aber **nicht garantiert in die Live-Oberfläche der Windows-Codex-App**. Ein separat gestarteter App Server kann mit einem aktiven UI-Thread kollidieren. Nur in **inaktiven** und vorher getesteten Threads einsetzen. Kein `turn/start`/`turn/steer`, kein Unterbrechen laufender Arbeit.
- Die Cloud-Integration liest nur beim *nächsten Run* und nur bei Internetzugriff. Wenn Codex den Befehl wegen Sandbox-Regeln nicht ausführen kann, fällt die Funktion aus, die übrige Arbeit läuft normal.
- Keine Dienstverfügbarkeitsgarantie: Webscraping wird vermieden, API-/RSS-Erreichbarkeit kann sich ändern. Bei HTTP-Fehlern bleibt die bisherige Feed-Datei bestehen.
- Die aktuelle Version enthält keine gegenseitige Synchronisation der Lieferbestätigungen zwischen Windows und Cloud, da Cloud keine persistente lokale Historie pflegt.
- Keine Integration mit bestehenden ChatGPT-Threads über eine allgemeine API vorhanden; die ChatGPT-Aufgabe muss den GitHub-Feed ausdrücklich publizieren.

## Quellen

- Codex App Server: https://learn.chatgpt.com/docs/app-server
- AGENTS.md: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex-Releases: https://github.com/openai/codex/releases
- OpenAI Status: https://status.openai.com/
- ChatGPT geplante Aufgaben: https://help.openai.com/en/articles/10291617-scheduled-tasks-in-chatgpt

## Tests

```powershell
py -m unittest discover -s tests -v
```
