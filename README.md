# BadBoerdi Backend (FastAPI)

Python-Service mit Chat-API, Pattern-Engine, mehrstufiger Safety-Pipeline, RAG, MCP-Integration
und Auslieferung des `<boerdi-chat>`-Widgets. Konfiguration ausschließlich über Dateien unter
`chatbots/wlo/v1/` — kein Code-Deploy für inhaltliche Änderungen nötig.

## 1. Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # OPENAI_API_KEY, OPENAI_MODEL, MCP-URL, …
python run.py              # uvicorn auf :8000
```

Health-Check: `GET http://localhost:8000/api/health`

## 2. Wichtige Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `POST` | `/api/chat` | Hauptendpoint. Erwartet `{session_id, message, environment, action?}`. Rückgabe enthält `content`, `cards`, `quick_replies`, `pagination`, `debug` (Triple-Schema-Trace). |
| `GET`  | `/api/sessions/{id}/messages?limit=20` | History für Cross-Page-Continuity. Wird vom Widget genutzt. |
| `POST` | `/api/sessions/{id}/restart` | Reset der Session inkl. Rate-Limit-State. |
| `GET`  | `/api/safety/logs` | Geloggte Risk-Events (siehe `safety-config.yaml → logging`). |
| `GET`  | `/api/config/...` | Liest/schreibt die Konfigurations-Dateien für das Studio. |
| `POST` | `/api/speech/transcribe` · `/api/speech/synthesize` | Whisper / TTS. |
| `GET`  | `/widget/boerdi-widget.js` | Auslieferung der Web-Component. |
| `GET`  | `/widget/` | Demo-HTML für Embedder. |

## 3. Konfigurationslayout — die 5 Schichten

Alle Schichten liegen unter `backend/chatbots/wlo/v1/` und werden über
`app/services/config_loader.py` geladen.

```
chatbots/wlo/v1/
├── 01-base/                      ← Schicht 1: Identität & Schutz (immer im Prompt)
│   ├── base-persona.md           ←   Wer ist BOERDi?
│   ├── guardrails.md             ←   Harte Grenzen (kommt als LETZTER Block)
│   ├── safety-config.yaml        ←   Presets off/basic/standard/strict/paranoid + Rate-Limits
│   └── device-config.yaml        ←   Geräte-/Persona-Heuristiken
├── 02-domain/                    ← Schicht 2: Domain & Regeln (immer im Prompt)
│   ├── domain-rules.md           ←   Dauerregeln
│   ├── policy.yaml               ←   Strukturelle Erlaubnisse/Verbote
│   └── wlo-plattform-wissen.md   ←   Plattform-Wissen WLO
├── 03-patterns/                  ← Schicht 3: 20 Konversations-Patterns
│   ├── pat-01-direkt-antwort.md
│   ├── pat-02-gefuehrte-klaerung.md
│   └── … pat-20-orientierungs-guide.md
├── 04-personas/                  ← Schicht 4: Dimensionen
├── 04-intents/
├── 04-entities/
├── 04-slots/
├── 04-signals/
├── 04-states/
├── 04-contexts/
└── 05-knowledge/                 ← Schicht 5: Wissen
    ├── rag-config.yaml           ←   Wissensbereiche (query_knowledge-Tools)
    └── mcp-servers.yaml          ←   Externe MCP-Server
```

Welche Datei wann in den Prompt wandert, ist im Quelltext nachvollziehbar:
`app/services/llm_service.py → generate_response()`, Variable `system_parts`.

## 4. Safety-Pipeline (Triple-Schema v2)

Die Safety läuft **vor** dem LLM-Call und kann Tools sperren oder Patterns erzwingen
(z.B. `PAT-CRISIS`).

```
Regex-Gate (immer)
   │
   ▼
OpenAI-Moderation  (mode: smart/always — in Presets festgelegt)
   │
   ▼
Legal-Classifier (gpt-4.1-mini)  (smart: nur bei Trigger-Treffer / always: jeder Turn)
   │
   ▼
Confidence-Adjustment aus Tool-Outcomes
```

Konfiguration: `chatbots/wlo/v1/01-base/safety-config.yaml`

* `security_level`: `off | basic | standard | strict | paranoid`
* `presets.*`: definieren `moderation`, `legal_classifier`, `prompt_injection`,
  optional `threshold_multiplier` und `double_check`
* `escalation.legal_thresholds.flag` / `.high`: Schwellwerte für den Legal-Classifier
* `escalation.thresholds.*`: Schwellwerte je Moderation-Kategorie
* `crisis_blocked_tools`: Tools, die bei Crisis-Pattern blockiert werden

## 5. Rate Limits & Concurrency

`safety-config.yaml → rate_limits` — Sliding-Window pro Session und pro IP, plus
optionale IP-Whitelist. Defaults für 50 parallele Nutzer:

```yaml
per_session:
  enabled: true
  requests_per_minute: 30
  requests_per_hour: 600
per_ip:
  enabled: true
  requests_per_minute: 300
  requests_per_hour: 3000
```

Pro Session-ID gibt es einen `asyncio.Lock` (`app/routers/chat.py`), sodass parallele Requests
einer Session strikt sequentiell verarbeitet werden — verschiedene Sessions laufen parallel.

## 6. Widget-Auslieferung

`app/routers/widget.py` liest **direkt** `frontend/dist/widget/browser/main.js`. Es gibt
**keinen Kopier-Schritt**. Build-Reihenfolge:

```bash
cd ../frontend && npm run build:widget   # erzeugt main.js
# Backend ist bereits am Laufen → /widget/boerdi-widget.js liefert das Bundle aus
```

Falls das Bundle fehlt, antwortet der Endpoint mit `503` und einer expliziten Anleitung.

## 7. MCP & RAG

* **MCP**: WLO-Suche via `app/services/mcp_client.py` (Tools `search_wlo_collections`,
  `search_wlo_content`, `get_collection_contents`, `lookup_wlo_vocabulary`, …).
  Server-Konfiguration in `chatbots/wlo/v1/05-knowledge/mcp-servers.yaml`.
* **RAG**: Wissensbereiche werden im Studio hochgeladen und in
  `chatbots/wlo/v1/05-knowledge/rag-config.yaml` registriert. Das LLM bekommt sie als
  `query_knowledge(area=…)`-Tool.

## 8. Datenbank

SQLite (`badboerdi.db`) für Sessions, Messages, Safety-Logs. Init in
`app/services/database.py`. Für Produktion gegen PostgreSQL austauschbar.

## 9. Debug-Output

Jede `/api/chat`-Antwort enthält ein `debug`-Objekt mit:

* `persona`, `intent`, `state`, `pattern`, `signals`, `entities`
* `phase1_eliminated`, `phase2_scores`, `phase3_modulations` (Pattern-Scoring)
* `outcomes` (Tool-Outcomes mit Status/Latenz)
* `safety` (Stages, Risk-Level, Categories, Legal-Flags, Escalated)
* `policy` (Allowed/Blocked-Tools/Disclaimers)
* `context`, `trace` (Phase-Trace mit Dauer)

Das Frontend rendert dieses Objekt im Debug-Panel; das Studio nutzt es für Sessions-Inspektion.
