import asyncio
import logging
import os

import httpx

import store
from services.assemblyai import transcribe
from services.bant import extract_bant, summarise_call
from services.recall import format_transcript

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 30  # seconds between checks


async def poll_loop():
    """Background task: every 30s check all joining bots, process when done."""
    logger.info("[poller] started — checking every 30s")
    while True:
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            await _check_pending()
        except Exception as exc:
            logger.error(f"[poller] unexpected error: {exc!r}")


async def _check_pending():
    pending = [c for c in store.all_calls() if c.get("status") == "joining"]
    if not pending:
        return

    api_key = os.getenv("RECALL_API_KEY", "").strip()
    region = os.getenv("RECALL_REGION", "us-west-2")
    base = f"https://{region}.recall.ai/api/v1"

    for call in pending:
        bot_id = call["bot_id"]
        try:
            await _process_if_done(bot_id, api_key, base)
        except Exception as exc:
            logger.error(f"[poller] failed bot_id={bot_id}: {exc!r}")
            store.update(bot_id, {"status": "failed", "error": str(exc)})


async def _process_if_done(bot_id: str, api_key: str, base: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{base}/bot/{bot_id}/",
            headers={"Authorization": f"Token {api_key}"},
            timeout=15,
        )
        resp.raise_for_status()
        bot = resp.json()

    codes = {s["code"] for s in bot.get("status_changes", [])}
    if "done" not in codes:
        return  # still in progress

    recordings = bot.get("recordings", [])
    if not recordings:
        raise RuntimeError("No recordings on bot")

    video = recordings[0].get("media_shortcuts", {}).get("video_mixed", {})
    audio_url = (video.get("data") or {}).get("download_url")
    if not audio_url:
        raise RuntimeError("No video download URL on recording")

    logger.info(f"[poller] bot_id={bot_id} done — starting transcription")
    store.update(bot_id, {"status": "transcribing"})

    segments = await transcribe(audio_url)
    if not segments:
        raise RuntimeError("AssemblyAI returned empty transcript")

    store.update(bot_id, {"status": "extracting", "transcript": segments})
    formatted = format_transcript(segments)

    bant = await extract_bant(formatted)
    summary = await summarise_call(formatted)

    store.update(bot_id, {"status": "ready", "bant": bant, "summary": summary})
    logger.info(f"[poller] bot_id={bot_id} ready sentiment={bant.get('overall_sentiment')}")
