import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import store
from routers.auth import get_current_user_id
from services.recall import create_bot

logger = logging.getLogger(__name__)
router = APIRouter()


class BotRequest(BaseModel):
    meeting_url: str
    bot_name: str = "NoteAI"
    deal_id: str = ""
    contact_id: str = ""
    rep_name: str = ""
    prospect_name: str = ""


@router.post("/bots/create")
async def dispatch_bot(req: BotRequest, user_id: int = Depends(get_current_user_id)):
    if not req.meeting_url.startswith("http"):
        raise HTTPException(status_code=400, detail="meeting_url must be a valid URL")

    try:
        result = await create_bot(req.meeting_url, req.bot_name)
    except (RuntimeError, ValueError) as exc:
        logger.error(f"[bots] create_bot failed: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    bot_id = result["id"]
    store.save(bot_id, {
        "bot_id": bot_id,
        "status": "joining",
        "meeting_url": req.meeting_url,
        "transcript": [],
        "bant": {},
        "summary": "",
        "deal_id": req.deal_id,
        "contact_id": req.contact_id,
        "rep_name": req.rep_name,
        "prospect_name": req.prospect_name,
    }, user_id=user_id)

    logger.info(f"[bots] bot dispatched bot_id={bot_id} user_id={user_id}")
    return {"bot_id": bot_id, "status": "joining", "message": "Bot is joining the call"}
