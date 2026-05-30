import logging
import os

from fastapi import APIRouter, Depends, HTTPException

import store
from routers.auth import get_current_user_id
from services.hubspot import push_bant_to_deal, push_contact, ensure_properties, get_deal_context

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/hubspot/deal-context/{deal_id}")
async def fetch_deal_context(deal_id: str, user_id: int = Depends(get_current_user_id)):
    """Read existing deal properties from HubSpot so the rep can see what's already there."""
    token = store.get_setting("hubspot_token", user_id) or os.getenv("HUBSPOT_ACCESS_TOKEN", "") or None
    if not token:
        raise HTTPException(status_code=400, detail="HubSpot not connected")
    try:
        ctx = await get_deal_context(deal_id, token=token)
        return {"deal_id": deal_id, "properties": ctx}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/hubspot/push/{bot_id}")
async def push_to_hubspot(bot_id: str, body: dict = {}, user_id: int = Depends(get_current_user_id)):
    call = store.get_for_user(bot_id, user_id)
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if call.get("status") not in ("ready", "reviewed"):
        raise HTTPException(status_code=400, detail=f"Call must be ready or reviewed (status={call.get('status')})")

    deal_id = body.get("deal_id") or call.get("deal_id")
    contact_id = body.get("contact_id") or call.get("contact_id")
    if not deal_id:
        raise HTTPException(status_code=400, detail="deal_id is required")

    token = store.get_setting("hubspot_token", user_id) or os.getenv("HUBSPOT_ACCESS_TOKEN", "") or None

    bant = call.get("bant", {})
    summary = call.get("summary", "")

    try:
        await ensure_properties(token)
        await push_bant_to_deal(deal_id, bant, summary, token=token)
        if contact_id:
            await push_contact(contact_id, bant, token=token)
    except RuntimeError as exc:
        logger.error(f"[hubspot] push failed bot_id={bot_id}: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    store.update(bot_id, {"status": "synced", "deal_id": deal_id, "contact_id": contact_id})
    logger.info(f"[hubspot] synced bot_id={bot_id} deal={deal_id}")

    recommended_stage = bant.get("recommended_hubspot_stage")
    action_count = len(bant.get("action_items", []))
    return {
        "status": "synced",
        "deal_id": deal_id,
        "recommended_stage": recommended_stage,
        "tasks_created": action_count,
    }
