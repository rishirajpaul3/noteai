import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://api.hubapi.com"

# Custom properties NoteAI creates in each customer's portal
_DEAL_PROPERTIES = [
    {"name": "budget_range",             "label": "Budget Range",             "type": "string",        "fieldType": "text"},
    {"name": "decision_maker_name",      "label": "Decision Maker Name",      "type": "string",        "fieldType": "text"},
    {"name": "primary_pain_point",       "label": "Primary Pain Point",       "type": "string",        "fieldType": "textarea"},
    {"name": "expected_close_timeline",  "label": "Expected Close Timeline",  "type": "string",        "fieldType": "text"},
    {"name": "last_call_summary",        "label": "Last Call Summary",        "type": "string",        "fieldType": "textarea"},
    {"name": "bant_confidence",          "label": "BANT Confidence",          "type": "enumeration",   "fieldType": "select",
     "options": [
         {"label": "Fully Qualified",    "value": "fully_qualified",    "displayOrder": 0},
         {"label": "Partially Qualified","value": "partially_qualified","displayOrder": 1},
         {"label": "Not Qualified",      "value": "not_qualified",      "displayOrder": 2},
     ]},
    {"name": "deal_urgency",             "label": "Deal Urgency",             "type": "enumeration",   "fieldType": "select",
     "options": [
         {"label": "Immediate",          "value": "immediate",       "displayOrder": 0},
         {"label": "This Quarter",       "value": "this_quarter",    "displayOrder": 1},
         {"label": "This Year",          "value": "this_year",       "displayOrder": 2},
         {"label": "Undefined",          "value": "undefined",       "displayOrder": 3},
     ]},
    {"name": "call_sentiment",           "label": "Call Sentiment",           "type": "enumeration",   "fieldType": "select",
     "options": [
         {"label": "Positive",  "value": "positive",  "displayOrder": 0},
         {"label": "Neutral",   "value": "neutral",   "displayOrder": 1},
         {"label": "Negative",  "value": "negative",  "displayOrder": 2},
     ]},
    # SaaS intelligence properties
    {"name": "current_solution",         "label": "Current Solution",         "type": "string",        "fieldType": "text"},
    {"name": "competitor_mentions",      "label": "Competitor Mentions",      "type": "string",        "fieldType": "text"},
    {"name": "mrr_potential",            "label": "MRR Potential",            "type": "string",        "fieldType": "text"},
    {"name": "seat_count",               "label": "Seat Count",               "type": "string",        "fieldType": "text"},
    {"name": "coaching_score",           "label": "Coaching Score",           "type": "number",        "fieldType": "number"},
    {"name": "contract_end_date",        "label": "Contract End Date",        "type": "string",        "fieldType": "text"},
    {"name": "expansion_potential",      "label": "Expansion Potential",      "type": "enumeration",   "fieldType": "select",
     "options": [
         {"label": "High",            "value": "high",            "displayOrder": 0},
         {"label": "Medium",          "value": "medium",          "displayOrder": 1},
         {"label": "Low",             "value": "low",             "displayOrder": 2},
         {"label": "Not Mentioned",   "value": "not_mentioned",   "displayOrder": 3},
     ]},
]

_CONTACT_PROPERTIES = [
    {"name": "decision_maker_name", "label": "Decision Maker Name", "type": "string", "fieldType": "text"},
]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_token(token: str | None) -> str:
    t = token or os.getenv("HUBSPOT_ACCESS_TOKEN", "").strip()
    if not t:
        raise ValueError("No HubSpot token. Connect HubSpot in Settings first.")
    return t


async def ensure_properties(token: str) -> None:
    """Create NoteAI custom properties in the customer's HubSpot portal if they don't exist."""
    async with httpx.AsyncClient() as client:
        await _ensure_object_properties(client, token, "deals", _DEAL_PROPERTIES)
        await _ensure_object_properties(client, token, "contacts", _CONTACT_PROPERTIES)
    logger.info("[hubspot] custom properties verified/created")


async def _ensure_object_properties(client: httpx.AsyncClient, token: str, obj: str, props: list) -> None:
    # Fetch existing property names
    resp = await client.get(f"{_BASE}/crm/v3/properties/{obj}", headers=_headers(token), timeout=15)
    if resp.is_error:
        logger.warning(f"[hubspot] could not fetch {obj} properties: {resp.status_code}")
        return
    existing = {p["name"] for p in resp.json().get("results", [])}

    for prop in props:
        if prop["name"] in existing:
            continue
        payload = {
            "name": prop["name"],
            "label": prop["label"],
            "type": prop["type"],
            "fieldType": prop["fieldType"],
            "groupName": f"{obj[:-1]}information",  # dealinformation / contactinformation
        }
        if "options" in prop:
            payload["options"] = prop["options"]

        r = await client.post(
            f"{_BASE}/crm/v3/properties/{obj}",
            headers=_headers(token), json=payload, timeout=15,
        )
        if r.is_error:
            logger.warning(f"[hubspot] failed to create {obj} property '{prop['name']}': {r.text[:200]}")
        else:
            logger.info(f"[hubspot] created {obj} property '{prop['name']}'")


async def get_deal_context(deal_id: str, token: str | None = None) -> dict:
    """Fetch existing deal properties from HubSpot so we can show what's already there."""
    t = _get_token(token)
    props = ",".join([
        "dealname", "dealstage", "amount", "closedate",
        "budget_range", "decision_maker_name", "primary_pain_point",
        "current_solution", "last_call_summary", "bant_confidence",
    ])
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BASE}/crm/v3/objects/deals/{deal_id}",
            headers=_headers(t),
            params={"properties": props},
            timeout=15,
        )
        if resp.is_error:
            return {}
        return resp.json().get("properties", {})


async def push_bant_to_deal(deal_id: str, bant: dict, summary: str, token: str | None = None) -> None:
    t = _get_token(token)
    props = _build_deal_properties(bant, summary)

    # Auto-update deal stage if recommended
    recommended_stage = bant.get("recommended_hubspot_stage")
    if recommended_stage:
        props["dealstage"] = recommended_stage

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_BASE}/crm/v3/objects/deals/{deal_id}",
            headers=_headers(t), json={"properties": props}, timeout=15,
        )
        _raise(resp, f"PATCH deal/{deal_id}")
        logger.info(f"[hubspot] deal/{deal_id} updated")

        note_id = await _create_note(client, t, summary, bant.get("action_items", []))
        await _associate_note_to_deal(client, t, note_id, deal_id)
        logger.info(f"[hubspot] note/{note_id} logged on deal/{deal_id}")

        # Create HubSpot tasks for each action item
        action_items = bant.get("action_items", [])
        for item in action_items:
            try:
                task_id = await _create_task(client, t, item)
                await _associate_task_to_deal(client, t, task_id, deal_id)
            except Exception as exc:
                logger.warning(f"[hubspot] task creation failed for '{item}': {exc}")


async def push_contact(contact_id: str, bant: dict, token: str | None = None) -> None:
    t = _get_token(token)
    authority = bant.get("authority", {})
    name = authority.get("decision_maker")
    if not name:
        return
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{_BASE}/crm/v3/objects/contacts/{contact_id}",
            headers=_headers(t), json={"properties": {"decision_maker_name": name}}, timeout=15,
        )
        _raise(resp, f"PATCH contact/{contact_id}")


async def verify_token(token: str) -> dict:
    """Check a token is valid and return portal info."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BASE}/oauth/v1/access-tokens/{token}",
            timeout=10,
        )
        if resp.is_error:
            raise RuntimeError("Invalid HubSpot token — check your Private App key.")
        return resp.json()


# ── Internal ──────────────────────────────────────────────────────────────────

def _build_deal_properties(bant: dict, summary: str) -> dict:
    props: dict = {}
    if bant.get("budget", {}).get("value"):
        props["budget_range"] = bant["budget"]["value"]
    if bant.get("authority", {}).get("decision_maker"):
        props["decision_maker_name"] = bant["authority"]["decision_maker"]
    if bant.get("need", {}).get("primary_pain"):
        props["primary_pain_point"] = bant["need"]["primary_pain"]
    if bant.get("timeline", {}).get("value"):
        props["expected_close_timeline"] = bant["timeline"]["value"]
    if bant.get("timeline", {}).get("urgency"):
        props["deal_urgency"] = bant["timeline"]["urgency"]
    if bant.get("overall_sentiment"):
        props["call_sentiment"] = bant["overall_sentiment"]
    props["bant_confidence"] = _bant_confidence(bant)
    if summary:
        props["last_call_summary"] = summary

    # SaaS intelligence fields
    saas = bant.get("saas_signals", {})
    if saas.get("current_solution"):
        props["current_solution"] = saas["current_solution"]
    if saas.get("competitor_mentions"):
        props["competitor_mentions"] = ", ".join(saas["competitor_mentions"])
    if saas.get("mrr_potential"):
        props["mrr_potential"] = saas["mrr_potential"]
    if saas.get("seat_count"):
        props["seat_count"] = saas["seat_count"]
    if saas.get("contract_end_date"):
        props["contract_end_date"] = saas["contract_end_date"]
    if saas.get("expansion_potential") and saas["expansion_potential"] != "not_mentioned":
        props["expansion_potential"] = saas["expansion_potential"]

    coaching = bant.get("coaching", {})
    if coaching.get("score") is not None:
        props["coaching_score"] = coaching["score"]

    return props


def _bant_confidence(bant: dict) -> str:
    fields = ["budget", "authority", "need", "timeline"]
    with_signal = sum(1 for f in fields if bant.get(f, {}).get("confidence") in ("high", "medium"))
    if with_signal == 4: return "fully_qualified"
    if with_signal >= 2: return "partially_qualified"
    return "not_qualified"


async def _create_note(client: httpx.AsyncClient, token: str, summary: str, action_items: list) -> str:
    items_text = "\n".join(f"• {a}" for a in action_items) if action_items else ""
    body = summary + (f"\n\nAction items:\n{items_text}" if items_text else "")
    resp = await client.post(
        f"{_BASE}/crm/v3/objects/notes",
        headers=_headers(token),
        json={"properties": {
            "hs_note_body": body,
            "hs_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }}, timeout=15,
    )
    _raise(resp, "POST note")
    return resp.json()["id"]


async def _associate_note_to_deal(client: httpx.AsyncClient, token: str, note_id: str, deal_id: str) -> None:
    resp = await client.put(
        f"{_BASE}/crm/v4/objects/notes/{note_id}/associations/deals/{deal_id}",
        headers=_headers(token),
        json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}],
        timeout=15,
    )
    _raise(resp, f"associate note/{note_id} → deal/{deal_id}")


async def _create_task(client: httpx.AsyncClient, token: str, subject: str) -> str:
    due_ts = int(datetime.now(timezone.utc).timestamp() * 1000) + 86_400_000  # tomorrow
    resp = await client.post(
        f"{_BASE}/crm/v3/objects/tasks",
        headers=_headers(token),
        json={"properties": {
            "hs_task_subject": subject,
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "HIGH",
            "hs_timestamp": str(due_ts),
        }},
        timeout=15,
    )
    _raise(resp, "POST task")
    return resp.json()["id"]


async def _associate_task_to_deal(client: httpx.AsyncClient, token: str, task_id: str, deal_id: str) -> None:
    resp = await client.put(
        f"{_BASE}/crm/v4/objects/tasks/{task_id}/associations/deals/{deal_id}",
        headers=_headers(token),
        json=[{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 216}],
        timeout=15,
    )
    _raise(resp, f"associate task/{task_id} → deal/{deal_id}")


def _raise(resp: httpx.Response, label: str) -> None:
    if resp.is_error:
        raise RuntimeError(f"[hubspot] {label} failed {resp.status_code}: {resp.text[:300]}")
