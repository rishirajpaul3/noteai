import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.assemblyai.com/v2"


def _headers() -> dict:
    key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not key:
        raise ValueError("ASSEMBLYAI_API_KEY not set")
    return {"authorization": key, "content-type": "application/json"}


async def transcribe(audio_url: str) -> list[dict]:
    """Submit audio/video URL to AssemblyAI, poll until done, return segments."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE}/transcript",
            headers=_headers(),
            json={"audio_url": audio_url, "speaker_labels": True, "speech_models": ["universal-2"]},
            timeout=30,
        )
        resp.raise_for_status()
        transcript_id = resp.json()["id"]
        logger.info(f"[assemblyai] submitted transcript_id={transcript_id}")

        for _ in range(60):  # poll up to 10 minutes
            await asyncio.sleep(10)
            resp = await client.get(
                f"{_BASE}/transcript/{transcript_id}",
                headers=_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data["status"]
            logger.info(f"[assemblyai] transcript_id={transcript_id} status={status}")

            if status == "completed":
                segments = _parse_utterances(data)
                logger.info(f"[assemblyai] done — {len(segments)} utterances")
                return segments
            if status == "error":
                raise RuntimeError(f"AssemblyAI transcription error: {data.get('error')}")

    raise RuntimeError("AssemblyAI transcription timed out after 10 minutes")


def _parse_utterances(data: dict) -> list[dict]:
    segments = []
    for utt in data.get("utterances") or []:
        text = utt.get("text", "").strip()
        if not text:
            continue
        start_ms = utt.get("start", 0)
        segments.append({
            "speaker": f"Speaker {utt.get('speaker', '?')}",
            "text": text,
            "timestamp": _fmt_time(start_ms / 1000),
        })
    return segments


def _fmt_time(seconds: float) -> str:
    s = int(seconds or 0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
