
# Progress Tracker

Update this file at the end of every Claude Code session. This is how Claude Code picks up where it left off.

---

## Current Status

**Overall**: Everything built. Ready for API keys + end-to-end test.

**Last updated**: 2026-05-14

---

## Steps

- [x] Step 1 — Scaffold + health check + Recall webhook receiver
- [x] Step 2 — Transcript parsing from Recall payload (native diarization, real names)
- [x] Step 3 — Claude Haiku 4.5 BANT extraction + call summary (MOCK_BANT=true available)
- [x] Step 4 — Review UI (transcript + BANT side by side, inline editing, Confirm button)
- [x] Step 5 — HubSpot PATCH deal properties + contact + note logged on deal
- [x] Bot creation endpoint (POST /bots/create — dispatches Recall bot to meeting URL)
- [x] Dockerfile + .dockerignore for Google Cloud Run
- [x] tests/test_bant.py — 13 assertions, mock mode (no API key needed), live mode (MOCK_BANT=false)

---

## Architecture (current)

**Stack:** Recall.ai → FastAPI → Claude Haiku 4.5 → in-memory store → Review UI → HubSpot API v3

**No database.** In-memory dict (`store.py`) keeps last 50 calls. Cleared on server restart — fine for internal team use.

**Flow:**
1. Recall bot joins call via API
2. Call ends → Recall fires `POST /webhook/recall`
3. `routers/webhook.py` extracts transcript from payload (real participant names)
4. Background task: `services/bant.py` calls Claude Haiku 4.5 → BANT JSON + summary
5. Result stored in `store.py`
6. AE opens `GET /` → review UI shows transcript + BANT fields
7. AE edits if needed → `PATCH /calls/{bot_id}/bant`
8. AE hits Confirm → `POST /hubspot/push/{bot_id}` → HubSpot PATCH deal + contact + note

---

## What's Built

| File | Purpose |
|---|---|
| `main.py` | FastAPI entry point, mounts all routers |
| `store.py` | In-memory call store (OrderedDict, max 50 calls) |
| `services/recall.py` | `parse_transcript()` from webhook payload, `fetch_transcript()` API fallback, `format_transcript()` |
| `services/bant.py` | `extract_bant()` + `summarise_call()` via Claude Haiku 4.5 (Anthropic SDK); MOCK_BANT=true for dev |
| `services/hubspot.py` | `push_bant_to_deal()` PATCH deal props + create + associate note; `push_contact()` PATCH contact |
| `routers/webhook.py` | Receives Recall webhook, dispatches background processing task |
| `routers/calls.py` | `GET /calls`, `GET /calls/{id}`, `PATCH /calls/{id}/bant`, serves `frontend/index.html` |
| `routers/hubspot.py` | `POST /hubspot/push/{bot_id}` — validates state, calls services/hubspot.py |
| `frontend/index.html` | Single-file review UI — sidebar, transcript + BANT columns, inline edit, Confirm button |

---

## What's Removed vs Original Plan

- ~~Deepgram~~ — Recall.ai transcribes natively with real participant names
- ~~SQLAlchemy / SQLite / alembic~~ — replaced by in-memory store
- ~~OpenAI SDK~~ — replaced by Anthropic SDK (Claude Haiku 4.5)
- ~~DEEPGRAM_API_KEY, DATABASE_URL~~ — removed from .env

---

## What's Blocked / Needs Testing

- **Recall transcript path**: Built for standard Recall format (`data.transcript.data[].speaker + words[]`). Need a real `bot.done` webhook to confirm. Parser logs clearly if path is wrong.
- **ANTHROPIC_API_KEY**: Add to `.env` to enable live BANT extraction. Use `MOCK_BANT=true` until then.
- **HubSpot custom properties**: Must be created per HUBSPOT_SETUP.md before push works.
- **HUBSPOT_ACCESS_TOKEN + HUBSPOT_PORTAL_ID**: Add to `.env`.

---

## Decisions Made

| Decision | Reason | Date |
|---|---|---|
| Recall.ai for bot | Only reliable cross-platform option | 2026-05-14 |
| Recall native transcription, no Deepgram | Real participant names, lower cost, simpler stack | 2026-05-14 |
| Claude Sonnet 4.6 for BANT | Marginal price difference vs Haiku, meaningfully better extraction quality | 2026-05-14 |
| In-memory store, no database | Internal tool for 6 people — no need for persistence | 2026-05-14 |
| Google Cloud Run for deployment | Free tier handles webhook volume, no server cost | 2026-05-14 |
| Human review before HubSpot push | Trust — bad CRM data kills adoption | 2026-05-14 |

---

## Next Steps

1. Add API keys to `.env` (ANTHROPIC_API_KEY, RECALL_API_KEY, HUBSPOT_ACCESS_TOKEN, HUBSPOT_PORTAL_ID)
2. Create HubSpot custom properties per HUBSPOT_SETUP.md
3. Run `venv/bin/uvicorn main:app --reload --port 8000` + `ngrok http 8000`
4. Set ngrok URL as webhook in Recall.ai dashboard
5. Make a test call → watch logs → confirm transcript path → review UI → push to HubSpot
6. Write Dockerfile for Cloud Run deployment

---

## Next Session — Start Here

"Read CLAUDE.md, DONT.md, and PROGRESS.md. Based on PROGRESS.md, tell me exactly where we left off and what the next action is. Do not write code until I confirm."
