import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import store
from routers.auth import get_current_user_id
from services.poller import _process_if_done

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def serve_ui():
    return FileResponse("frontend/index.html")


@router.get("/calls")
def list_calls(user_id: int = Depends(get_current_user_id)):
    return store.all_calls(user_id)


@router.get("/calls/{bot_id}")
def get_call(bot_id: str, user_id: int = Depends(get_current_user_id)):
    call = store.get_for_user(bot_id, user_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.patch("/calls/{bot_id}/bant")
def update_bant(bot_id: str, body: dict, user_id: int = Depends(get_current_user_id)):
    call = store.get_for_user(bot_id, user_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.get("status") not in ("ready", "reviewed"):
        raise HTTPException(status_code=400, detail=f"Call not in editable state (status={call.get('status')})")

    top_level = {}
    if "deal_id" in body:
        top_level["deal_id"] = body.pop("deal_id")
    if "contact_id" in body:
        top_level["contact_id"] = body.pop("contact_id")

    bant = call.get("bant", {})
    bant.update(body)
    store.update(bot_id, {"bant": bant, "status": "reviewed", **top_level})
    logger.info(f"[calls] BANT updated bot_id={bot_id}")
    return {"status": "updated"}


class CoachingResponseRequest(BaseModel):
    missed_opportunity: str
    context: str = ""


@router.post("/calls/{bot_id}/coaching-response")
async def get_coaching_response(bot_id: str, body: CoachingResponseRequest, user_id: int = Depends(get_current_user_id)):
    call = store.get_for_user(bot_id, user_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    from services.bant import _client, MODEL
    client = _client()
    bant = call.get("bant", {})
    prospect = call.get("prospect_name", "the prospect")

    message = await client.messages.create(
        model=MODEL,
        max_tokens=300,
        system="You are an expert B2B SaaS sales coach. Give a concrete, natural-sounding script line the rep could have said to address a missed opportunity. Keep it to 2-3 sentences max. Be specific, not generic.",
        messages=[{
            "role": "user",
            "content": (
                f"The rep missed this opportunity: \"{body.missed_opportunity}\"\n\n"
                f"Call context: BANT so far — Budget: {bant.get('budget', {}).get('value', 'unknown')}, "
                f"Need: {bant.get('need', {}).get('primary_pain', 'unknown')}, "
                f"Prospect: {prospect}\n\n"
                f"What exact words could the rep have said?"
            ),
        }],
    )
    return {"suggestion": message.content[0].text.strip()}


@router.get("/deals/{deal_id}/timeline")
def get_deal_timeline(deal_id: str, user_id: int = Depends(get_current_user_id)):
    all_user_calls = store.all_calls(user_id)
    deal_calls = [c for c in all_user_calls if c.get("deal_id") == deal_id and c.get("status") in ("ready", "reviewed", "synced")]
    deal_calls.sort(key=lambda c: c.get("created_at", 0))

    timeline = []
    for i, call in enumerate(deal_calls):
        bant = call.get("bant", {})
        prev_bant = deal_calls[i - 1].get("bant", {}) if i > 0 else {}

        def field_status(key: str, sub: str) -> str:
            curr = (bant.get(key) or {}).get(sub)
            prev = (prev_bant.get(key) or {}).get(sub)
            if not curr:
                return "missing"
            if not prev:
                return "new"
            if curr != prev:
                return "updated"
            return "same"

        timeline.append({
            "bot_id": call["bot_id"],
            "meeting_url": call.get("meeting_url", ""),
            "created_at": call.get("created_at", 0),
            "status": call.get("status"),
            "coaching_score": (bant.get("coaching") or {}).get("score"),
            "overall_sentiment": bant.get("overall_sentiment"),
            "deal_stage_signal": bant.get("deal_stage_signal"),
            "bant_snapshot": {
                "budget": (bant.get("budget") or {}).get("value"),
                "authority": (bant.get("authority") or {}).get("decision_maker"),
                "need": (bant.get("need") or {}).get("primary_pain"),
                "timeline": (bant.get("timeline") or {}).get("value"),
            },
            "bant_progress": {
                "budget": field_status("budget", "value"),
                "authority": field_status("authority", "decision_maker"),
                "need": field_status("need", "primary_pain"),
                "timeline": field_status("timeline", "value"),
            },
            "prospect_name": call.get("prospect_name", ""),
        })

    return {"deal_id": deal_id, "calls": timeline}


@router.post("/calls/{bot_id}/reprocess")
async def reprocess_call(bot_id: str, user_id: int = Depends(get_current_user_id)):
    import os
    api_key = os.getenv("RECALL_API_KEY", "").strip()
    region = os.getenv("RECALL_REGION", "us-west-2")
    base = f"https://{region}.recall.ai/api/v1"
    store.save(bot_id, {
        "bot_id": bot_id, "status": "joining",
        "meeting_url": "reprocess", "transcript": [],
        "bant": {}, "summary": "", "deal_id": "", "contact_id": "",
    }, user_id=user_id)
    try:
        await _process_if_done(bot_id, api_key, base)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    call = store.get(bot_id)
    return {"status": call.get("status") if call else "unknown"}
