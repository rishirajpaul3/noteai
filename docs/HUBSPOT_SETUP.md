# HubSpot Setup Guide

Do this before running Step 5 of the build. If these properties don't exist in HubSpot, the API push will fail.

---

## 1. Create Custom Deal Properties

Go to: HubSpot → Settings → Data Management → Properties → Deal Properties → Create property

Create each of the following:

---

### budget_range

| Field | Value |
|---|---|
| Label | Budget Range |
| Internal name | budget_range |
| Field type | Single-line text |
| Group | Deal information |
| Description | Budget range extracted from sales call transcript |

---

### decision_maker_name

| Field | Value |
|---|---|
| Label | Decision Maker Name |
| Internal name | decision_maker_name |
| Field type | Single-line text |
| Group | Deal information |
| Description | Name of the decision maker identified on the call |

---

### primary_pain_point

| Field | Value |
|---|---|
| Label | Primary Pain Point |
| Internal name | primary_pain_point |
| Field type | Multi-line text |
| Group | Deal information |
| Description | Main business pain identified during the discovery call |

---

### expected_close_timeline

| Field | Value |
|---|---|
| Label | Expected Close Timeline |
| Internal name | expected_close_timeline |
| Field type | Single-line text |
| Group | Deal information |
| Description | Timeline to purchase expressed by the prospect |

---

### deal_urgency

| Field | Value |
|---|---|
| Label | Deal Urgency |
| Internal name | deal_urgency |
| Field type | Dropdown select |
| Group | Deal information |
| Description | Urgency signal extracted from call |

**Options** (add exactly as below):

| Label | Internal value |
|---|---|
| Immediate | immediate |
| This Quarter | this_quarter |
| This Year | this_year |
| Undefined | not_defined |

---

### call_sentiment

| Field | Value |
|---|---|
| Label | Call Sentiment |
| Internal name | call_sentiment |
| Field type | Dropdown select |
| Group | Deal information |
| Description | Overall sentiment of the sales call |

**Options**:

| Label | Internal value |
|---|---|
| Positive | positive |
| Neutral | neutral |
| Negative | negative |

---

### bant_confidence

| Field | Value |
|---|---|
| Label | BANT Confidence |
| Internal name | bant_confidence |
| Field type | Dropdown select |
| Group | Deal information |
| Description | How complete the BANT qualification is after the call |

**Options**:

| Label | Internal value |
|---|---|
| Fully Qualified | fully_qualified |
| Partially Qualified | partially_qualified |
| Not Qualified | not_qualified |

---

### last_call_summary

| Field | Value |
|---|---|
| Label | Last Call Summary |
| Internal name | last_call_summary |
| Field type | Multi-line text |
| Group | Deal information |
| Description | AI-generated summary of the most recent sales call |

---

## 2. Get Your Property Internal Names

After creating each property, click into it and check the Internal name field. It should match exactly what's in the table above. If HubSpot auto-modified the name, update `services/hubspot.py` to match.

---

## 3. Get Your HubSpot Access Token

Go to: HubSpot → Settings → Account Setup → Integrations → Private Apps → Create private app

**Required scopes**:
- `crm.objects.deals.read`
- `crm.objects.deals.write`
- `crm.objects.contacts.read`
- `crm.objects.contacts.write`
- `crm.objects.notes.write`
- `timeline` (for logging call engagements)

Copy the access token and paste it as `HUBSPOT_ACCESS_TOKEN` in your .env file.

---

## 4. Get Your Portal ID

Go to: HubSpot → Settings → Account Setup → Account Details

Your Portal ID (also called Hub ID) is shown at the top. Paste it as `HUBSPOT_PORTAL_ID` in your .env file.

---

## 5. Find a Test Deal and Contact ID

For testing the HubSpot push before going live:

Go to any deal in HubSpot. The deal ID is in the URL:
`https://app.hubspot.com/contacts/{PORTAL_ID}/deal/{DEAL_ID}`

Go to any contact. The contact ID is also in the URL:
`https://app.hubspot.com/contacts/{PORTAL_ID}/contact/{CONTACT_ID}`

Note these down for use in `tests/test_bant.py` when testing the HubSpot push.

---

## 6. How Properties Get Updated

After the AE confirms in the review UI, the app sends two PATCH calls:

**Deal update** — maps BANT fields to deal properties:
```
PATCH https://api.hubapi.com/crm/v3/objects/deals/{dealId}
{
  "properties": {
    "budget_range": "...",
    "decision_maker_name": "...",
    "primary_pain_point": "...",
    "expected_close_timeline": "...",
    "deal_urgency": "...",
    "call_sentiment": "...",
    "last_call_summary": "..."
  }
}
```

**Note logged on deal** — full action items and next steps:
```
POST https://api.hubapi.com/crm/v3/objects/notes
{
  "properties": {
    "hs_note_body": "...",
    "hs_timestamp": "..."
  }
}
```
Then associate the note with the deal via the associations API.
