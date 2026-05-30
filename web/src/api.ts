const BASE = import.meta.env.VITE_API_URL ?? '';

export interface Call {
  bot_id: string;
  status: string;
  meeting_url: string;
  transcript: { speaker: string; text: string; timestamp: string }[];
  bant: Record<string, any>;
  summary: string;
  deal_id?: string;
  contact_id?: string;
  rep_name?: string;
  prospect_name?: string;
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('noteai_token');
  return token
    ? { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    : { 'Content-Type': 'application/json' };
}

async function apiFetch(path: string, init: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers || {}) },
  });
  if (res.status === 401) {
    localStorage.removeItem('noteai_token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  return res;
}

export async function fetchCalls(): Promise<Call[]> {
  const res = await apiFetch('/calls');
  if (!res.ok) throw new Error('Failed to fetch calls');
  return res.json();
}

export async function fetchCall(botId: string): Promise<Call> {
  const res = await apiFetch(`/calls/${botId}`);
  if (!res.ok) throw new Error('Call not found');
  return res.json();
}

export async function updateBant(botId: string, body: Record<string, any>) {
  const res = await apiFetch(`/calls/${botId}/bant`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Update failed');
  return res.json();
}

export async function pushToHubspot(botId: string, dealId: string, contactId?: string) {
  const res = await apiFetch(`/hubspot/push/${botId}`, {
    method: 'POST',
    body: JSON.stringify({ deal_id: dealId, contact_id: contactId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'HubSpot push failed');
  }
  return res.json();
}

export async function fetchDealContext(dealId: string) {
  const res = await apiFetch(`/hubspot/deal-context/${dealId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDealTimeline(dealId: string) {
  const res = await apiFetch(`/deals/${dealId}/timeline`);
  if (!res.ok) throw new Error('Failed to fetch deal timeline');
  return res.json() as Promise<{
    deal_id: string;
    calls: {
      bot_id: string;
      meeting_url: string;
      created_at: number;
      status: string;
      coaching_score?: number;
      overall_sentiment?: string;
      deal_stage_signal?: string;
      bant_snapshot: Record<string, string | null>;
      bant_progress: Record<string, string>;
      prospect_name: string;
    }[];
  }>;
}

export async function getCoachingResponse(botId: string, missedOpportunity: string): Promise<{ suggestion: string }> {
  const res = await apiFetch(`/calls/${botId}/coaching-response`, {
    method: 'POST',
    body: JSON.stringify({ missed_opportunity: missedOpportunity }),
  });
  if (!res.ok) throw new Error('Failed to get coaching response');
  return res.json();
}

export async function createBot(meetingUrl: string, prospectName: string = '', repName: string = '') {
  const res = await apiFetch('/bots/create', {
    method: 'POST',
    body: JSON.stringify({ meeting_url: meetingUrl, prospect_name: prospectName, rep_name: repName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create bot');
  }
  return res.json();
}
