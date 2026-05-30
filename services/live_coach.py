"""
Live coaching service — polls Recall for partial transcripts during an active call
and generates real-time coaching tips via Claude.

Called by the WebSocket endpoint in routers/live.py. Runs as an async loop until
the call ends (status leaves "joining"/"transcribing") or the WebSocket disconnects.
"""
import asyncio
import logging
import os

import httpx
from anthropic import AsyncAnthropic

import store

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
POLL_INTERVAL = 20  # seconds between Recall transcript polls
MAX_WORDS_FOR_TIP = 600  # last N words of transcript sent to Claude


_LIVE_COACH_SYSTEM = """\
You are a real-time B2B SaaS sales coach whispering tips to a sales rep mid-call.
The rep can see your message on their screen while talking.

Rules:
- ONE tip only, max 2 sentences
- Be specific to what just happened in the transcript, not generic
- If the rep is doing well, say so briefly ("Good move asking about timeline")
- If something is missing, say what to ask next ("Budget not discussed yet — try: 'Do you have a rough budget range in mind?'")
- If the call is going badly, flag it calmly ("Prospect sounds disengaged — ask an open question")
- Never repeat a tip from earlier in the session
- Tone: supportive, direct, like a coach in your ear\
"""


async def fetch_partial_transcript(bot_id: str) -> list[dict]:
    """Fetch the current partial transcript from Recall API during an active call."""
    api_key = os.getenv("RECALL_API_KEY", "")
    region = os.getenv("RECALL_REGION", "us-west-2")
    if not api_key:
        return []

    url = f"https://{region}.recall.ai/api/v1/bot/{bot_id}/transcript"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Token {api_key}"},
            )
            if resp.is_error:
                return []
            data = resp.json()
            utterances = data if isinstance(data, list) else data.get("results", [])
            segments = []
            for utt in utterances:
                speaker = utt.get("speaker") or "Unknown"
                words = utt.get("words") or []
                text = " ".join(w.get("text", "") for w in words).strip()
                if text:
                    segments.append({"speaker": speaker, "text": text})
            return segments
    except Exception as exc:
        logger.warning(f"[live_coach] fetch_partial_transcript failed: {exc}")
        return []


def _last_n_words(segments: list[dict], n: int = MAX_WORDS_FOR_TIP) -> str:
    """Return the last N words of the transcript as a readable string."""
    all_lines = [f"{s['speaker']}: {s['text']}" for s in segments]
    full_text = "\n".join(all_lines)
    words = full_text.split()
    if len(words) > n:
        truncated = " ".join(words[-n:])
        return f"[...earlier transcript omitted...]\n{truncated}"
    return full_text


async def generate_tip(transcript_excerpt: str, prev_tips: list[str]) -> str:
    """Ask Claude for one live coaching tip based on the recent transcript."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    client = AsyncAnthropic(api_key=api_key)
    prev_context = ""
    if prev_tips:
        prev_context = f"\n\nTips already given this call (do NOT repeat these):\n" + "\n".join(f"- {t}" for t in prev_tips[-5:])

    try:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=120,
            system=_LIVE_COACH_SYSTEM,
            messages=[{
                "role": "user",
                "content": f"Live transcript (most recent):\n\n{transcript_excerpt}{prev_context}\n\nGive me one coaching tip now:",
            }],
        )
        return message.content[0].text.strip()
    except Exception as exc:
        logger.warning(f"[live_coach] generate_tip failed: {exc}")
        return ""


async def run_live_coaching(bot_id: str, send_message) -> None:
    """
    Main loop. Polls Recall every POLL_INTERVAL seconds, generates a tip,
    and calls send_message(data) to push it to the WebSocket client.

    send_message is a coroutine: async def send_message(data: dict) -> None
    Stops when the call is no longer active or send_message raises (client disconnected).
    """
    prev_tips: list[str] = []
    active_statuses = {"joining", "transcribing", "processing"}

    logger.info(f"[live_coach] starting loop for bot_id={bot_id}")

    while True:
        await asyncio.sleep(POLL_INTERVAL)

        call = store.get(bot_id)
        if not call or call.get("status") not in active_statuses:
            logger.info(f"[live_coach] call ended or not found, stopping loop bot_id={bot_id}")
            try:
                await send_message({"type": "done", "message": "Call complete — full analysis ready."})
            except Exception:
                pass
            return

        segments = await fetch_partial_transcript(bot_id)
        if not segments:
            # No transcript yet (bot still joining) — send a joining ping
            try:
                await send_message({"type": "status", "message": "Bot is joining the call…"})
            except Exception:
                return
            continue

        excerpt = _last_n_words(segments)
        tip = await generate_tip(excerpt, prev_tips)

        if tip:
            prev_tips.append(tip)
            try:
                await send_message({"type": "tip", "message": tip})
            except Exception:
                logger.info(f"[live_coach] client disconnected bot_id={bot_id}")
                return
