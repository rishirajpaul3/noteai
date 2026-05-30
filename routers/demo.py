"""
Demo endpoint — runs the full pipeline on sample_transcript.txt.
Uses real Claude Sonnet 4.6 and stores the result in memory so you can
review it in the UI and push to HubSpot. No Recall bot needed.
"""
import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException

import store
from services.bant import extract_bant, summarise_call
from services.recall import format_transcript

logger = logging.getLogger(__name__)
router = APIRouter()

SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_transcript.txt")
DEMO_BOT_ID = "demo-call-001"


@router.post("/demo/run")
async def run_demo(background_tasks: BackgroundTasks):
    """
    Load sample_transcript.txt, run BANT extraction via Claude Sonnet 4.6,
    store result. Open the UI at / to review and push to HubSpot.
    """
    if not os.path.exists(SAMPLE_PATH):
        raise HTTPException(status_code=500, detail="sample_transcript.txt not found")

    store.save(DEMO_BOT_ID, {
        "bot_id": DEMO_BOT_ID,
        "status": "processing",
        "meeting_url": "demo",
        "transcript": [],
        "bant": {},
        "summary": "",
        "deal_id": "",
        "contact_id": "",
    })

    background_tasks.add_task(_process_demo)
    return {"bot_id": DEMO_BOT_ID, "status": "processing", "message": "Demo running — refresh the UI in a few seconds"}


async def _process_demo():
    try:
        with open(SAMPLE_PATH) as f:
            raw = f.read()

        # sample_transcript.txt is already formatted with speaker labels
        segments = _parse_sample(raw)
        formatted = format_transcript(segments)

        bant = await extract_bant(formatted)
        summary = await summarise_call(formatted)

        store.save(DEMO_BOT_ID, {
            "bot_id": DEMO_BOT_ID,
            "status": "ready",
            "meeting_url": "demo",
            "transcript": segments,
            "bant": bant,
            "summary": summary,
            "deal_id": "",
            "contact_id": "",
        })
        logger.info(f"[demo] done sentiment={bant.get('overall_sentiment')}")

    except Exception as exc:
        logger.error(f"[demo] failed: {exc!r}")
        store.update(DEMO_BOT_ID, {"status": "failed", "error": str(exc)})


def _parse_sample(raw: str) -> list[dict]:
    """Convert sample_transcript.txt lines into [{speaker, text, timestamp}]."""
    segments = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Format: [00:00:12] Speaker 0 (Sarah): text
        try:
            ts = line[1:line.index("]")]
            rest = line[line.index("]") + 2:]
            speaker, text = rest.split(":", 1)
            segments.append({
                "speaker": speaker.strip(),
                "text": text.strip(),
                "timestamp": ts,
            })
        except (ValueError, IndexError):
            continue
    return segments
