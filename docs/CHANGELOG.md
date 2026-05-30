# Changelog

All notable changes to this project will be documented here.

Format: `## [version] — YYYY-MM-DD` followed by what changed.

---

## [0.1.0] — 2026-05-14

### Added
- Initial project setup
- CLAUDE.md, README.md, DONT.md, PROMPTS.md, HUBSPOT_SETUP.md, PROGRESS.md
- sample_transcript.txt for BANT extraction testing
- .env.example

### Not built yet
- Everything else

---

## [0.2.0] — 2026-05-14

### Added
- `main.py` — FastAPI app entry point with health check and DB init on startup
- `db/database.py` — SQLAlchemy `Call` table, `get_db()`, `init_db()`, `CallStatus` enum
- `routers/webhook.py` — `POST /webhook/recall` stores raw payload, triggers background transcription on recording-complete events
- `services/deepgram.py` — `transcribe_audio()` with speaker diarization (nova-2), `extract_audio_url()` for Recall payload shapes
- Full project scaffold (routers/, services/, models/, db/, frontend/, tests/)
- `requirements.txt`, `.gitignore`, `.env.example`
- Python venv at `venv/`
