import json
import logging

from fastapi import APIRouter, BackgroundTasks, Request

import store
from services.bant import assign_speakers, extract_bant, summarise_call
from services.recall import fetch_transcript, format_transcript, parse_transcript

logger = logging.getLogger(__name__)
router = APIRouter()

DONE_EVENTS = {"bot.done", "bot.recording_done", "recording.done"}


@router.post("/webhook/recall")
async def recall_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    event = payload.get("event", "")
    data = payload.get("data", {})
    bot_id = data.get("bot_id") or data.get("id") or "unknown"

    logger.info(f"[webhook] event={event!r} bot_id={bot_id}")
    print(f"[webhook] raw payload={json.dumps(payload)}")

    if event in DONE_EVENTS:
        background_tasks.add_task(_process, bot_id, payload)

    return {"status": "received"}


async def _process(bot_id: str, payload: dict) -> None:
    logger.info(f"[process] starting bot_id={bot_id}")

    # Use update() not save() — preserves deal_id, contact_id, rep_name, prospect_name, user_id
    store.update(bot_id, {"status": "processing", "transcript": [], "bant": {}, "summary": ""})

    try:
        segments = parse_transcript(payload)

        if not segments:
            logger.warning(f"[process] no transcript in payload for bot_id={bot_id} — fetching from API")
            segments = await fetch_transcript(bot_id)

        if not segments:
            logger.info(f"[process] no transcript for bot_id={bot_id} — handing off to poller for AssemblyAI")
            store.update(bot_id, {"status": "joining"})
            return

        # Assign real speaker names before BANT extraction
        call = store.get(bot_id) or {}
        segments = await assign_speakers(
            segments,
            rep_name=call.get("rep_name", ""),
            prospect_name=call.get("prospect_name", ""),
        )

        formatted = format_transcript(segments)
        bant = await extract_bant(formatted)
        summary = await summarise_call(formatted)

        store.update(bot_id, {
            "status": "ready",
            "transcript": segments,
            "bant": bant,
            "summary": summary,
        })
        logger.info(f"[process] done bot_id={bot_id} sentiment={bant.get('overall_sentiment')}")

    except Exception as exc:
        logger.error(f"[process] failed bot_id={bot_id} error={exc!r}")
        store.update(bot_id, {"status": "failed", "error": str(exc)})
