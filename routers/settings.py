import logging

from fastapi import APIRouter, Depends, HTTPException

import store
from routers.auth import get_current_user_id
from services.hubspot import verify_token, ensure_properties

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/settings/hubspot")
async def get_hubspot_settings(user_id: int = Depends(get_current_user_id)):
    token = store.get_setting("hubspot_token", user_id)
    portal_name = store.get_setting("hubspot_portal_name", user_id)
    return {
        "connected": bool(token),
        "portal_name": portal_name or None,
        "token_preview": f"...{token[-6:]}" if token else None,
    }


@router.post("/settings/hubspot")
async def save_hubspot_token(body: dict, user_id: int = Depends(get_current_user_id)):
    token = (body.get("token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is required")
    try:
        info = await verify_token(token)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    portal_name = info.get("hub_domain") or info.get("user") or "HubSpot"
    store.set_setting("hubspot_token", token, user_id)
    store.set_setting("hubspot_portal_name", portal_name, user_id)

    try:
        await ensure_properties(token)
    except Exception as exc:
        logger.warning(f"[settings] property creation failed: {exc}")

    logger.info(f"[settings] HubSpot connected user_id={user_id} portal={portal_name}")
    return {"connected": True, "portal_name": portal_name}


@router.delete("/settings/hubspot")
async def disconnect_hubspot(user_id: int = Depends(get_current_user_id)):
    store.set_setting("hubspot_token", "", user_id)
    store.set_setting("hubspot_portal_name", "", user_id)
    return {"connected": False}
