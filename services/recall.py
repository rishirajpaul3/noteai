import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Override with RECALL_REGION env var if your account is on a different region.
# Valid values: us-east-1, us-west-2, eu-central-1, ap-northeast-1
_RECALL_BASE = f"https://{os.getenv('RECALL_REGION', 'us-west-2')}.recall.ai/api/v1"


def parse_transcript(payload: dict) -> list[dict]:
    """
    Extract transcript segments from a Recall.ai webhook payload.
    Returns [{speaker, text, timestamp}] — one entry per utterance.

    Recall returns real participant names (not Speaker 0/1) when native
    transcription is enabled. Logs clearly if the expected path is missing
    so we can adjust once a real payload is seen.
    """
    data = payload.get("data", {})

    # Standard Recall transcript path
    utterances = (
        data.get("transcript", {}).get("data")
        or data.get("transcript", [])
        or []
    )

    if not utterances:
        logger.warning(
            "[recall] No transcript found in webhook payload. "
            "Check that transcription is enabled in your Recall.ai bot settings. "
            f"Payload keys: {list(data.keys())}"
        )
        return []

    segments = []
    for utt in utterances:
        speaker = utt.get("speaker") or utt.get("participant", {}).get("name") or "Unknown"
        words = utt.get("words") or []
        text = " ".join(w.get("text", "") for w in words).strip()
        if not text:
            continue
        start = words[0].get("start_time", 0) if words else 0
        segments.append({
            "speaker": speaker,
            "text": text,
            "timestamp": _fmt_time(start),
        })

    logger.info(f"[recall] parsed {len(segments)} utterances from transcript")
    return segments


def format_transcript(segments: list[dict]) -> str:
    """Convert [{speaker, text, timestamp}] to LLM-readable string."""
    return "\n".join(
        f"[{s['timestamp']}] {s['speaker']}: {s['text']}"
        for s in segments
    )


async def create_bot(meeting_url: str, bot_name: str = "Sales Notetaker") -> dict:
    """
    Send a Recall.ai bot to a Zoom / Meet / Teams meeting URL.
    Returns the full Recall bot object — use result["id"] as the bot_id.
    Webhook URL is set per-bot if WEBHOOK_BASE_URL is configured, otherwise
    fall back to the global webhook set in the Recall.ai dashboard.
    """
    api_key = os.getenv("RECALL_API_KEY")
    if not api_key:
        raise ValueError("RECALL_API_KEY not set")

    payload: dict = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
    }

    webhook_base = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")
    if webhook_base:
        payload["webhook_url"] = f"{webhook_base}/webhook/recall"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_RECALL_BASE}/bot/",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
        if resp.is_error:
            raise RuntimeError(f"Recall API error {resp.status_code}: {resp.text[:300]}")
        return resp.json()


async def fetch_transcript(bot_id: str) -> list[dict]:
    """
    Fallback: fetch transcript directly from Recall API if not in webhook payload.
    Only needed if Recall sends the webhook before transcript is embedded.
    """
    api_key = os.getenv("RECALL_API_KEY")
    if not api_key:
        raise ValueError("RECALL_API_KEY not set")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_RECALL_BASE}/transcript/",
            headers={"Authorization": f"Token {api_key}"},
            params={"bot_id": bot_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    utterances = data.get("results", data) if isinstance(data, dict) else data
    segments = []
    for utt in utterances:
        speaker = utt.get("speaker") or "Unknown"
        words = utt.get("words") or []
        text = " ".join(w.get("text", "") for w in words).strip()
        if not text:
            continue
        start = words[0].get("start_time", 0) if words else 0
        segments.append({"speaker": speaker, "text": text, "timestamp": _fmt_time(start)})

    return segments


def _fmt_time(seconds: float) -> str:
    s = int(seconds or 0)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"
