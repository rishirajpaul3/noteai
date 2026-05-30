"""
BANT extraction + call summary test.

Modes:
  MOCK_BANT=true  (default) — runs against fixture data, no API key needed.
                               Use this in dev and CI.
  MOCK_BANT=false            — hits Claude Sonnet 4.6 for real.
                               Requires ANTHROPIC_API_KEY in .env.

Usage:
    cd /path/to/project
    source venv/bin/activate
    python tests/test_bant.py
"""

import asyncio
import json
import os
import sys

# Default to mock so the test is always runnable without an API key
os.environ.setdefault("MOCK_BANT", "true")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from services.bant import extract_bant, summarise_call
from services.recall import format_transcript

TRANSCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_transcript.txt")


async def main() -> None:
    mock_mode = os.environ.get("MOCK_BANT", "true").lower() == "true"
    print("=" * 60)
    print(f"Mode: {'MOCK (no API call)' if mock_mode else 'LIVE (Claude Sonnet 4.6)'}")
    print("=" * 60)

    with open(TRANSCRIPT_PATH) as f:
        raw = f.read()

    # sample_transcript.txt is already formatted — pass directly.
    # For real Recall transcripts, use format_transcript(segments) first.
    transcript = raw

    print("\nRunning extract_bant()...")
    bant = await extract_bant(transcript)
    print(json.dumps(bant, indent=2))

    print("\nRunning summarise_call()...")
    summary = await summarise_call(transcript)
    print(summary)

    print("\n" + "=" * 60)
    print("ASSERTIONS")
    print("=" * 60)

    checks = {
        "budget.value is not null":
            bant["budget"]["value"] is not None,
        "budget.confidence is high or medium":
            bant["budget"]["confidence"] in ("high", "medium"),
        "authority.decision_maker is not null":
            bant["authority"]["decision_maker"] is not None,
        "authority.confidence is high or medium":
            bant["authority"]["confidence"] in ("high", "medium"),
        "need.primary_pain is not null":
            bant["need"]["primary_pain"] is not None,
        "need.confidence is high or medium":
            bant["need"]["confidence"] in ("high", "medium"),
        "timeline.value is not null":
            bant["timeline"]["value"] is not None,
        "timeline.urgency is this_quarter or immediate":
            bant["timeline"]["urgency"] in ("this_quarter", "immediate"),
        "overall_sentiment == positive":
            bant["overall_sentiment"] == "positive",
        "deal_stage_signal is mid or late":
            bant["deal_stage_signal"] in ("mid", "late"),
        "action_items is non-empty list":
            isinstance(bant["action_items"], list) and len(bant["action_items"]) > 0,
        "next_steps is not null":
            bant["next_steps"] is not None,
        "summary is non-empty string":
            isinstance(summary, str) and len(summary) > 20,
    }

    passed = 0
    for label, result in checks.items():
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {label}")
        if result:
            passed += 1

    print()
    total = len(checks)
    if passed == total:
        print(f"All {total} checks passed.")
    else:
        print(f"{passed}/{total} passed — review failures above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
