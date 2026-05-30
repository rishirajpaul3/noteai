import json
import os

from anthropic import AsyncAnthropic

MODEL = "claude-sonnet-4-6"

_SPEAKER_SYSTEM = """\
You are analyzing a sales call transcript excerpt. Identify which speaker label is the sales rep and which is the prospect/customer.

Sales rep: asks questions, pitches the product, runs the agenda ("Great, let me show you...", "Our product does...").
Prospect: describes their problems, answers questions about their company, mentions their team/budget/timeline.

Return ONLY valid JSON with no explanation: {"rep": "exact_speaker_label", "prospect": "exact_speaker_label"}
If you cannot determine with confidence, return: {"rep": null, "prospect": null}\
"""

_BANT_SYSTEM = """\
You are a SaaS sales intelligence assistant. You will be given a transcript of a B2B SaaS sales discovery call with speaker labels.

Extract BANT qualification data AND SaaS-specific signals, then return ONLY valid JSON. No explanation, no markdown, no preamble.

Return this exact structure:
{
  "budget": {
    "value": "string or null",
    "confidence": "high|medium|low|not_mentioned",
    "quote": "exact quote from transcript or null"
  },
  "authority": {
    "decision_maker": "name or null",
    "title": "title or null",
    "others_involved": ["name1", "name2"],
    "confidence": "high|medium|low|not_mentioned",
    "quote": "exact quote from transcript or null"
  },
  "need": {
    "primary_pain": "string or null",
    "secondary_pains": ["pain1", "pain2"],
    "confidence": "high|medium|low|not_mentioned",
    "quote": "exact quote from transcript or null"
  },
  "timeline": {
    "value": "string or null",
    "urgency": "immediate|this_quarter|this_year|not_defined",
    "confidence": "high|medium|low|not_mentioned",
    "quote": "exact quote from transcript or null"
  },
  "saas_signals": {
    "current_solution": "what tool/process they use today or null",
    "contract_end_date": "when their current contract ends or null",
    "seat_count": "number of users/seats mentioned or null",
    "mrr_potential": "estimated monthly revenue potential or null",
    "expansion_potential": "high|medium|low|not_mentioned",
    "competitor_mentions": ["competitor1", "competitor2"],
    "tech_stack": ["tool1", "tool2"]
  },
  "coaching": {
    "score": 0-100,
    "topics_covered": {
      "budget": true or false,
      "authority": true or false,
      "need": true or false,
      "timeline": true or false,
      "current_solution": true or false,
      "next_steps": true or false
    },
    "missed_opportunities": ["string1", "string2"],
    "strengths": ["string1", "string2"],
    "suggested_next_action": "string"
  },
  "action_items": ["item1", "item2"],
  "next_steps": "string or null",
  "overall_sentiment": "positive|neutral|negative",
  "deal_stage_signal": "early|mid|late|lost",
  "recommended_hubspot_stage": "appointmentscheduled|qualifiedtobuy|presentationscheduled|decisionmakerboughtin|contractsent|closedwon|closedlost or null"
}

Rules:
- Only extract what was explicitly said. Do not infer or assume.
- If something was not mentioned, use null and confidence: "not_mentioned"
- Quotes must be verbatim from the transcript
- Speaker labels matter — budget/timeline signals from the PROSPECT count, from the REP do not
- coaching.score: 0-100 based on how well the rep ran discovery (covered key topics, listened, asked follow-ups)
- SaaS signals are critical — current solution and competitor mentions are deal intelligence\
"""

_SUMMARY_SYSTEM = """\
You are a SaaS sales intelligence assistant. Given a B2B SaaS discovery call transcript, write a concise CRM note.

Format:
- 4-6 sentences max, plain prose, third person ("The prospect mentioned...")
- Cover: primary pain, BANT signals found, SaaS context (current tool, seats, contract timing), agreed next steps
- Flag any competitor mentions explicitly
- No bullet points, no markdown\
"""

_COACHING_TIPS = {
    "budget": "Ask: 'Do you have a budget range in mind for solving this?' or 'What's your current spend on tools like this?'",
    "authority": "Ask: 'Besides yourself, who else will be involved in this decision?'",
    "need": "Ask: 'What's the biggest pain this is causing your team right now?'",
    "timeline": "Ask: 'When are you looking to have something live?'",
    "current_solution": "Ask: 'What are you using today to handle this?' or 'What made you start looking?'",
    "next_steps": "Always close with: 'What makes sense as a next step from here?'",
}


def _is_generic_speaker(name: str) -> bool:
    n = name.lower().strip()
    return n in ("unknown", "") or "speaker" in n or "participant" in n or (len(n) <= 2)


async def assign_speakers(segments: list[dict], rep_name: str = "", prospect_name: str = "") -> list[dict]:
    """Remap generic speaker labels (Speaker 0, Unknown) to actual names using Claude inference."""
    if not segments:
        return segments

    unique_speakers = list(dict.fromkeys(s["speaker"] for s in segments))
    if not any(_is_generic_speaker(sp) for sp in unique_speakers):
        return segments  # already has real names

    if len(unique_speakers) == 2:
        sp0, sp1 = unique_speakers
        # Use first 12 utterances to let Claude identify who is who
        excerpt = "\n".join(
            f"[{s['timestamp']}] {s['speaker']}: {s['text']}"
            for s in segments[:12]
        )
        rep_label, prospect_label = sp0, sp1  # safe fallback
        try:
            client = _client()
            msg = await client.messages.create(
                model=MODEL,
                max_tokens=80,
                system=_SPEAKER_SYSTEM,
                messages=[{
                    "role": "user",
                    "content": f"Speaker labels present: {unique_speakers}\n\nTranscript excerpt:\n{excerpt}",
                }],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1].lstrip("json").strip().rstrip("`").strip()
            result = json.loads(raw)
            if result.get("rep") in unique_speakers:
                rep_label = result["rep"]
                prospect_label = result["prospect"]
        except Exception:
            pass  # stick with fallback order

        mapping = {
            rep_label: rep_name or "Rep",
            prospect_label: prospect_name or "Prospect",
        }
    else:
        # More than 2 speakers — label generics as Speaker A, B, C...
        mapping = {}
        generic_count = 0
        for sp in unique_speakers:
            if _is_generic_speaker(sp):
                mapping[sp] = f"Speaker {chr(65 + generic_count)}"
                generic_count += 1

    return [{**s, "speaker": mapping.get(s["speaker"], s["speaker"])} for s in segments]


async def extract_bant(transcript: str) -> dict:
    if _is_mock():
        return _mock_bant()

    client = _client()
    message = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=_BANT_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Here is the SaaS sales call transcript:\n\n{transcript}\n\nExtract the full qualification data now.",
        }],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude returned non-JSON: {raw[:300]}") from exc

    _validate_bant(result)
    return result


async def summarise_call(transcript: str) -> str:
    if _is_mock():
        return (
            "The prospect expressed a clear need to eliminate post-call admin burden, "
            "with reps spending 20-30 minutes updating HubSpot after each discovery call. "
            "Budget is within range at ~$8k/month tooling spend, and the decision maker "
            "confirmed authority to approve without procurement. Currently using Otter.ai "
            "which does not integrate meaningfully with HubSpot. "
            "A 14-day trial was agreed, with a Friday check-in and June go-live target."
        )

    client = _client()
    message = await client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=_SUMMARY_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Summarise this SaaS sales call:\n\n{transcript}",
        }],
    )
    return message.content[0].text.strip()


def get_coaching_tips(bant: dict) -> list[str]:
    """Return coaching tips for topics the rep missed."""
    topics = bant.get("coaching", {}).get("topics_covered", {})
    tips = []
    for topic, covered in topics.items():
        if not covered and topic in _COACHING_TIPS:
            tips.append(_COACHING_TIPS[topic])
    return tips


# ── Internal ──────────────────────────────────────────────────────────────────

def _is_mock() -> bool:
    return os.getenv("MOCK_BANT", "false").lower() == "true"


def _client() -> AsyncAnthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return AsyncAnthropic(api_key=api_key)


_REQUIRED_KEYS = {"budget", "authority", "need", "timeline", "action_items", "next_steps", "overall_sentiment", "deal_stage_signal"}


def _validate_bant(data: dict) -> None:
    missing = _REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"BANT response missing keys: {missing}")


def _mock_bant() -> dict:
    return {
        "budget": {"value": "~$8k/month", "confidence": "high", "quote": "Our tooling budget is around 8k a month."},
        "authority": {"decision_maker": "James", "title": "VP Sales", "others_involved": ["CRO"], "confidence": "high", "quote": "For anything under 10k I can approve myself."},
        "need": {"primary_pain": "Reps spending 20-30 min on CRM admin after every call", "secondary_pains": ["Poor HubSpot data quality", "Otter.ai doesn't integrate with HubSpot"], "confidence": "high", "quote": "They finish a discovery call and spend 20-30 minutes updating HubSpot."},
        "timeline": {"value": "June 2026", "urgency": "this_quarter", "confidence": "high", "quote": "Ideally before the new AEs start in July."},
        "saas_signals": {
            "current_solution": "Otter.ai",
            "contract_end_date": "End of quarter",
            "seat_count": "8 AEs",
            "mrr_potential": "$2,400/mo",
            "expansion_potential": "high",
            "competitor_mentions": ["Otter.ai", "Gong"],
            "tech_stack": ["HubSpot", "Slack", "Zoom"],
        },
        "coaching": {
            "score": 82,
            "topics_covered": {"budget": True, "authority": True, "need": True, "timeline": True, "current_solution": True, "next_steps": True},
            "missed_opportunities": ["Didn't ask about expansion potential", "Could have probed deeper on CRO involvement"],
            "strengths": ["Strong discovery questions", "Identified primary pain clearly", "Confirmed decision maker"],
            "suggested_next_action": "Send trial invite to James today and CC Priya. Schedule Friday check-in.",
        },
        "action_items": ["Send trial setup today", "CC Priya on email", "Friday check-in call"],
        "next_steps": "14-day trial, two AEs onboarded this week, Friday check-in",
        "overall_sentiment": "positive",
        "deal_stage_signal": "mid",
        "recommended_hubspot_stage": "qualifiedtobuy",
    }
