# NoteAI

AI sales co-pilot for B2B teams. A Recall.ai bot joins every sales call, transcribes with real speaker names, Claude Sonnet extracts BANT in real time, and the rep sees live coaching tips during the call via WebSocket. After the call, BANT syncs automatically to HubSpot deal fields.

Built by [Rishiraj Paul](https://rishirajpaul.com) — GTM Engineer.

---

## What makes it different from Fireflies and Fathom

- **Live coaching during the call** — not just notes after. Reps get real-time tips as the conversation unfolds.
- **BANT writes directly to HubSpot deal properties** — not a note dump. Structured data that sales ops can actually use.
- **Deal timeline tracks BANT progression** across multiple calls with the same prospect.

---

## Stack

| Layer | Tool |
|---|---|
| Meeting bot | Recall.ai |
| Transcription | Recall native → AssemblyAI fallback |
| AI model | Claude Sonnet 4.6 (Anthropic) |
| Speaker naming | Claude inference on first 12 utterances |
| CRM | HubSpot API v3 |
| Backend | FastAPI + Python async |
| Database | SQLite |
| Frontend | React 19 + TypeScript + Vite |
| Auth | JWT |
| Deployment | Docker + Fly.io |

---

## How it works

```
Recall.ai bot joins call
  → real-time transcript stream
  → Claude assigns speaker names from first 12 utterances
  → live coaching tips pushed to rep via WebSocket
  → call ends
  → Claude extracts BANT fields + call summary
  → BANT syncs to HubSpot deal properties
  → deal timeline updated
```

---

## Running locally

```bash
# Backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd web
npm install
npm run dev
```

Requires env vars: `ANTHROPIC_API_KEY`, `RECALL_API_KEY`, `HUBSPOT_ACCESS_TOKEN`, `ASSEMBLYAI_API_KEY`, `JWT_SECRET`

---

## More

- **Website:** [rishirajpaul.com](https://rishirajpaul.com)
- **Builds & tools:** [rishirajpaul.com/builds](https://rishirajpaul.com/builds)
- **LinkedIn:** [linkedin.com/in/rishiraj-paul-gtm](https://www.linkedin.com/in/rishiraj-paul-gtm/)
