# NoteAI — Claude Code Project Brain

## What This Is

NoteAI is a production sales co-pilot for B2B SaaS teams. It is NOT a generic notetaker.

A Recall.ai bot joins every sales call → transcribes with real speaker names → Claude Sonnet 4.6 extracts BANT + coaching data → the rep sees live coaching tips during the call via WebSocket → after the call, BANT syncs to HubSpot deal fields automatically.

**The three things that make it better than Fireflies and Fathom:**
1. Live coaching during the call (not just notes after)
2. BANT writes directly to HubSpot deal properties (not just a note dump)
3. Deal timeline tracks BANT progression across multiple calls with the same prospect

---

## Actual Stack (as of May 2026)

| Layer | Tool | Location |
|---|---|---|
| Meeting bot | Recall.ai | `services/recall.py` |
| Transcription | Recall native → AssemblyAI fallback | `services/recall.py`, `services/assemblyai.py` |
| AI model | Anthropic Claude Sonnet 4.6 | `services/bant.py`, `services/live_coach.py` |
| Speaker naming | Claude inference on first 12 utterances | `services/bant.py` → `assign_speakers()` |
| CRM | HubSpot API v3 | `services/hubspot.py`, `routers/hubspot.py` |
| Backend | FastAPI + Python async | `main.py`, `routers/`, `services/` |
| Database | SQLite (JSON blob per call) | `store.py` |
| Frontend | React 19 + TypeScript + Vite | `web/src/` |
| Auth | JWT (python-jose + passlib) | `services/auth.py`, `routers/auth.py` |
| Deployment | Docker + Fly.io | `Dockerfile`, `fly.toml` |

> ⚠️ There is NO Deepgram. There is NO OpenAI. The old CLAUDE.md was wrong. This is the truth.

---

## Directory Map

```
/
├── CLAUDE.md              ← You are here. Navigational map only.
├── main.py                ← FastAPI app, router registration, poll_loop startup
├── store.py               ← SQLite wrapper. All call data is a JSON blob in `data` column.
├── requirements.txt
├── Dockerfile / fly.toml
│
├── .claude/               ← Claude Code configuration (hidden, not scanned as content)
│   ├── settings.json      ← Tool permissions
│   ├── rules/             ← Load these when working on specific subsystems
│   │   ├── hubspot-sync-logic.md
│   │   ├── recall-stream-handling.md
│   │   └── deterministic-validation.md
│   ├── skills/            ← On-demand operational scripts
│   │   ├── reprocess-call.md
│   │   ├── setup-hubspot-properties.md
│   │   └── debug-speakers.md
│   └── agents/            ← Sub-agent task profiles
│       └── bant-extractor.md
│
├── routers/               ← HTTP + WebSocket endpoints (no business logic here)
│   ├── auth.py            → JWT register/login
│   ├── bots.py            → POST /bots/create (dispatches Recall bot)
│   ├── calls.py           → CRUD + /coaching-response + /deals/{id}/timeline
│   ├── webhook.py         → POST /webhook/recall (Recall fires here on call end)
│   ├── live.py            → WS /ws/calls/{bot_id} (live coaching WebSocket)
│   ├── hubspot.py         → Push BANT to HubSpot deal
│   ├── settings.py        → Per-user HubSpot token config
│   └── demo.py            → POST /demo/run (no API keys needed for demo)
│
├── services/              ← Pure async functions. No FastAPI imports allowed here.
│   ├── bant.py            → extract_bant(), summarise_call(), assign_speakers()
│   ├── live_coach.py      → run_live_coaching() loop, fetch_partial_transcript()
│   ├── recall.py          → create_bot(), fetch_transcript(), parse_transcript()
│   ├── hubspot.py         → push_bant_to_hubspot(), create_properties()
│   ├── poller.py          → Background loop polls Recall every 30s for joining calls
│   ├── assemblyai.py      → Fallback transcription via AssemblyAI
│   └── auth.py            → Password hashing, JWT creation/verification
│
├── models/
│   ├── call.py            → Call data shape (informational — store uses JSON blob)
│   └── hubspot.py         → HubSpot property mapping reference
│
├── web/src/               ← React frontend
│   ├── App.tsx            → Routes: /app, /app/calls/:botId, /app/deals/:dealId
│   ├── api.ts             → All fetch calls to backend (single source of truth)
│   ├── pages/
│   │   ├── Dashboard.tsx      → Call list + launch bot form (with prospect name)
│   │   ├── CallDetail.tsx     → BANT editor + coaching report + LiveCoachPanel
│   │   ├── LiveCoachPanel.tsx → WebSocket client, shows live tips during call
│   │   ├── DealTimeline.tsx   → Multi-call BANT progression view
│   │   ├── Settings.tsx       → HubSpot token per user
│   │   └── Auth.tsx / Landing.tsx / Onboarding.tsx
│   └── AuthContext.tsx    → JWT token storage + auth state
│
├── docs/                  ← Human reference docs (not loaded by Claude)
│   ├── HUBSPOT_SETUP.md   → How to create custom HubSpot properties
│   ├── PROMPTS.md         → Prompt version history
│   ├── CHANGELOG.md       → Release notes
│   └── DONT.md            → Hard rules (also encoded in .claude/rules/)
│
└── tests/
    └── test_bant.py       → Tests BANT extraction against sample_transcript.txt
```

---

## Call Data Shape (the only database schema that matters)

All call state lives in a single JSON blob stored in `calls.data`. Know this cold:

```
{
  bot_id, status, meeting_url, transcript[],
  bant{}, summary, deal_id, contact_id,
  rep_name, prospect_name, created_at
}
```

**Status lifecycle:** `joining → processing → ready → reviewed → synced`  
**Failure path:** any step → `failed` with `error` field

---

## The Three Rules That Must Never Break

1. **Never push to HubSpot without review.** The rep confirms in the UI first. Automatic push on webhook completion is forbidden.
2. **Never import FastAPI into services/.** Routers call services. Services are pure async functions.
3. **Never use `store.save()` in the webhook processor.** Use `store.update()` — save() overwrites deal_id, rep_name, and user_id. This bug existed and was fixed. Don't reintroduce it.

---

## Rules Index (load when working on specific systems)

| Working on... | Load this rule file |
|---|---|
| HubSpot field mapping / CRM sync | `.claude/rules/hubspot-sync-logic.md` |
| WebSocket / live coaching / Recall partial transcripts | `.claude/rules/recall-stream-handling.md` |
| BANT validation / speaker assignment / JSON parsing | `.claude/rules/deterministic-validation.md` |

---

## Skills Index (invoke for operational tasks)

| Task | Skill |
|---|---|
| Reprocess a stuck/failed call | `.claude/skills/reprocess-call.md` |
| Set up HubSpot custom properties from scratch | `.claude/skills/setup-hubspot-properties.md` |
| Debug why speakers show as "Unknown" | `.claude/skills/debug-speakers.md` |

---

## Dev Commands

```bash
# Backend
cd "AI notetaker"
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend
cd web && npm run dev

# Demo (no API keys needed)
curl -X POST http://localhost:8000/demo/run | python3 -m json.tool
```

---

## Environment Variables Required

```
ANTHROPIC_API_KEY=
RECALL_API_KEY=
RECALL_REGION=us-west-2
RECALL_TRANSCRIPTION_PROVIDER=assembly_ai
ASSEMBLYAI_API_KEY=
HUBSPOT_ACCESS_TOKEN=
WEBHOOK_BASE_URL=https://your-domain.com
JWT_SECRET=
ALLOWED_ORIGINS=http://localhost:5173
MOCK_BANT=false
```
