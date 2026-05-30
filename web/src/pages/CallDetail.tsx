import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchCall, updateBant, pushToHubspot, getCoachingResponse, type Call } from '../api';
import styles from './CallDetail.module.css';
import LiveCoachPanel from './LiveCoachPanel';

const CONF_COLOR: Record<string, string> = {
  high: '#16a34a', medium: '#ca8a04', low: '#dc2626', not_mentioned: '#94a3b8',
};

function ConfBadge({ value }: { value?: string }) {
  if (!value) return null;
  return <span className={styles.conf} style={{ color: CONF_COLOR[value] || '#94a3b8' }}>{value}</span>;
}

function CoachingScore({ score }: { score: number }) {
  const color = score >= 75 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626';
  const bg = score >= 75 ? '#F0FDF4' : score >= 50 ? '#FFFBEB' : '#FEF2F2';
  return (
    <div className={styles.scoreCircle} style={{ background: bg, borderColor: color, color }}>
      <span className={styles.scoreNum}>{score}</span>
      <span className={styles.scoreLabel}>/ 100</span>
    </div>
  );
}

export default function CallDetail() {
  const { botId } = useParams<{ botId: string }>();
  const qc = useQueryClient();

  const { data: call, isLoading, error } = useQuery<Call>({
    queryKey: ['call', botId],
    queryFn: () => fetchCall(botId!),
    refetchInterval: (query) => ['joining', 'transcribing', 'extracting'].includes(query.state.data?.status ?? '') ? 5000 : false,
  });

  const [dealId, setDealId] = useState('');
  const [contactId, setContactId] = useState('');
  const [pushMsg, setPushMsg] = useState('');
  const [pushError, setPushError] = useState('');
  const [pushResult, setPushResult] = useState<{ recommended_stage?: string; tasks_created?: number } | null>(null);

  const updateMutation = useMutation({
    mutationFn: (patch: Record<string, any>) => updateBant(botId!, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['call', botId] }),
  });

  const pushMutation = useMutation({
    mutationFn: () => pushToHubspot(botId!, dealId || call?.deal_id || '', contactId || call?.contact_id),
    onSuccess: (data: any) => {
      setPushMsg('Synced to HubSpot ✓');
      setPushResult(data);
      qc.invalidateQueries({ queryKey: ['call', botId] });
    },
    onError: (err: any) => setPushError(err.message),
  });

  if (isLoading) return <LoadingState />;
  if (error || !call) return <div className={styles.error}>Call not found.</div>;

  const bant = call.bant || {};
  const saas = bant.saas_signals || {};
  const coaching = bant.coaching || {};
  const canPush = ['ready', 'reviewed'].includes(call.status);
  const isPending = ['joining', 'transcribing', 'extracting'].includes(call.status);

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
        <span className={styles.navStatus}>{call.status}</span>
      </nav>

      <div className={styles.layout}>
        {/* Left: Transcript */}
        <aside className={styles.sidebar}>
          <h3 className={styles.panelTitle}>Transcript</h3>
          {isPending && (
            <div className={styles.processing}>
              <div className={styles.spinner} />
              <span>{call.status === 'joining' ? 'Bot joining call…' : call.status === 'transcribing' ? 'Transcribing audio…' : 'Extracting BANT…'}</span>
            </div>
          )}
          {call.transcript?.length > 0 ? (
            <div className={styles.transcript}>
              {call.transcript.map((seg, i) => (
                <div key={i} className={styles.seg}>
                  <div className={styles.segMeta}>
                    <strong className={styles.speaker}>{seg.speaker}</strong>
                    <span className={styles.ts}>{seg.timestamp}</span>
                  </div>
                  <p className={styles.segText}>{seg.text}</p>
                </div>
              ))}
            </div>
          ) : !isPending && (
            <p className={styles.empty}>No transcript yet.</p>
          )}
        </aside>

        {/* Right: BANT + actions */}
        <main className={styles.content}>
          {/* Live coaching panel — only shown during active calls */}
          {isPending && <LiveCoachPanel botId={call.bot_id} />}

          {/* Summary */}
          {call.summary && (
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Call Summary</h3>
              <p className={styles.summary}>{call.summary}</p>
            </div>
          )}

          {/* BANT fields */}
          {Object.keys(bant).length > 0 && (
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>BANT Extraction</h3>
              <div className={styles.bantGrid}>
                <BantField label="Budget" data={bant.budget} field="value"
                  onSave={v => updateMutation.mutate({ budget: { ...bant.budget, value: v } })} />
                <BantField label="Authority" data={bant.authority} field="decision_maker"
                  onSave={v => updateMutation.mutate({ authority: { ...bant.authority, decision_maker: v } })} />
                <BantField label="Need" data={bant.need} field="primary_pain"
                  onSave={v => updateMutation.mutate({ need: { ...bant.need, primary_pain: v } })} />
                <BantField label="Timeline" data={bant.timeline} field="value"
                  onSave={v => updateMutation.mutate({ timeline: { ...bant.timeline, value: v } })} />
              </div>

              <div className={styles.signals}>
                {bant.overall_sentiment && (
                  <span className={styles.signal}>Sentiment: <strong>{bant.overall_sentiment}</strong></span>
                )}
                {bant.deal_stage_signal && (
                  <span className={styles.signal}>Stage: <strong>{bant.deal_stage_signal}</strong></span>
                )}
                {bant.recommended_hubspot_stage && (
                  <span className={styles.signal}>Recommended stage: <strong>{bant.recommended_hubspot_stage}</strong></span>
                )}
                {bant.next_steps && (
                  <span className={styles.signal}>Next steps: <strong>{bant.next_steps}</strong></span>
                )}
              </div>

              {bant.action_items?.length > 0 && (
                <div className={styles.actionItems}>
                  <div className={styles.aiLabel}>Action items → HubSpot tasks</div>
                  <ul className={styles.aiList}>
                    {bant.action_items.map((a: string, i: number) => <li key={i}>{a}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* SaaS Intelligence */}
          {(saas.current_solution || saas.competitor_mentions?.length > 0 || saas.mrr_potential || saas.seat_count) && (
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>SaaS Intelligence</h3>
              <div className={styles.saasGrid}>
                {saas.current_solution && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>Current tool</span>
                    <span className={styles.saasVal}>{saas.current_solution}</span>
                  </div>
                )}
                {saas.seat_count && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>Seats</span>
                    <span className={styles.saasVal}>{saas.seat_count}</span>
                  </div>
                )}
                {saas.mrr_potential && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>MRR potential</span>
                    <span className={`${styles.saasVal} ${styles.saasAccent}`}>{saas.mrr_potential}</span>
                  </div>
                )}
                {saas.contract_end_date && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>Contract ends</span>
                    <span className={styles.saasVal}>{saas.contract_end_date}</span>
                  </div>
                )}
                {saas.expansion_potential && saas.expansion_potential !== 'not_mentioned' && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>Expansion</span>
                    <span className={styles.saasVal}>{saas.expansion_potential}</span>
                  </div>
                )}
                {saas.tech_stack?.length > 0 && (
                  <div className={styles.saasItem}>
                    <span className={styles.saasKey}>Tech stack</span>
                    <span className={styles.saasVal}>{saas.tech_stack.join(', ')}</span>
                  </div>
                )}
              </div>
              {saas.competitor_mentions?.length > 0 && (
                <div className={styles.competitors}>
                  <span className={styles.competitorLabel}>Competitors mentioned</span>
                  <div className={styles.competitorTags}>
                    {saas.competitor_mentions.map((c: string) => (
                      <span key={c} className={styles.competitorTag}>{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Coaching Report */}
          {coaching.score !== undefined && (
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Rep Coaching Report</h3>
              <div className={styles.coachingTop}>
                <CoachingScore score={coaching.score} />
                <div className={styles.coachingMeta}>
                  {coaching.suggested_next_action && (
                    <div className={styles.nextAction}>
                      <span className={styles.nextActionLabel}>Suggested next action</span>
                      <span className={styles.nextActionText}>{coaching.suggested_next_action}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Talk ratio */}
              {call.transcript?.length > 0 && <TalkRatio transcript={call.transcript} />}

              {coaching.topics_covered && (
                <div className={styles.topicsGrid}>
                  {Object.entries(coaching.topics_covered).map(([topic, covered]) => (
                    <div key={topic} className={styles.topicChip + ' ' + (covered ? styles.topicCovered : styles.topicMissed)}>
                      <span>{covered ? '✓' : '✗'}</span>
                      <span>{topic.replace('_', ' ')}</span>
                    </div>
                  ))}
                </div>
              )}

              {coaching.strengths?.length > 0 && (
                <div className={styles.coachingSection}>
                  <div className={styles.coachingSectionLabel}>Strengths</div>
                  <ul className={styles.coachingList}>
                    {coaching.strengths.map((s: string, i: number) => (
                      <li key={i} className={styles.strengthItem}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {coaching.missed_opportunities?.length > 0 && (
                <div className={styles.coachingSection}>
                  <div className={styles.coachingSectionLabel}>Missed opportunities</div>
                  <div className={styles.missedList}>
                    {coaching.missed_opportunities.map((m: string, i: number) => (
                      <MissedOpportunity key={i} text={m} botId={botId!} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* HubSpot push */}
          {canPush && (
            <div className={styles.card}>
              <h3 className={styles.cardTitle}>Push to HubSpot</h3>
              <div className={styles.hsForm}>
                <div className={styles.hsField}>
                  <label className={styles.label}>Deal ID</label>
                  <input className={styles.input} placeholder={call.deal_id || 'HubSpot deal ID'}
                    value={dealId} onChange={e => setDealId(e.target.value)} />
                </div>
                <div className={styles.hsField}>
                  <label className={styles.label}>Contact ID <span className={styles.optional}>(optional)</span></label>
                  <input className={styles.input} placeholder={call.contact_id || 'HubSpot contact ID'}
                    value={contactId} onChange={e => setContactId(e.target.value)} />
                </div>
              </div>
              {bant.recommended_hubspot_stage && (
                <p className={styles.stageHint}>
                  AI will update deal stage to <strong>{bant.recommended_hubspot_stage}</strong> and create {bant.action_items?.length || 0} HubSpot tasks.
                </p>
              )}
              <button
                className={styles.btnPush}
                disabled={pushMutation.isPending || (!dealId && !call.deal_id)}
                onClick={() => { setPushMsg(''); setPushError(''); setPushResult(null); pushMutation.mutate(); }}
              >
                {pushMutation.isPending ? 'Pushing…' : 'Push to HubSpot →'}
              </button>
              {pushMsg && (
                <div className={styles.successBox}>
                  <p className={styles.success}>{pushMsg}</p>
                  {pushResult?.tasks_created != null && pushResult.tasks_created > 0 && (
                    <p className={styles.successSub}>{pushResult.tasks_created} tasks created in HubSpot</p>
                  )}
                  {pushResult?.recommended_stage && (
                    <p className={styles.successSub}>Deal stage → {pushResult.recommended_stage}</p>
                  )}
                </div>
              )}
              {pushError && <p className={styles.errorMsg}>{pushError}</p>}
            </div>
          )}

          {call.status === 'synced' && (
            <div className={styles.synced}>✓ Synced to HubSpot{call.deal_id ? ` · Deal ${call.deal_id}` : ''}</div>
          )}

          {call.deal_id && (
            <Link to={`/app/deals/${call.deal_id}`} className={styles.timelineLink}>
              View deal timeline →
            </Link>
          )}
        </main>
      </div>
    </div>
  );
}

function BantField({ label, data, field, onSave }: {
  label: string; data: any; field: string; onSave: (v: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState('');
  const value = data?.[field];
  const conf = data?.confidence;
  const quote = data?.quote;

  function startEdit() { setVal(value || ''); setEditing(true); }
  function save() { onSave(val); setEditing(false); }

  return (
    <div className={styles.bantField}>
      <div className={styles.bantHeader}>
        <span className={styles.bantLabel}>{label}</span>
        <ConfBadge value={conf} />
      </div>
      {editing ? (
        <div className={styles.bantEdit}>
          <input className={styles.bantInput} value={val} onChange={e => setVal(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && save()} autoFocus />
          <button className={styles.saveBtn} onClick={save}>Save</button>
          <button className={styles.cancelBtn} onClick={() => setEditing(false)}>✕</button>
        </div>
      ) : (
        <div className={styles.bantValue} onClick={startEdit} title="Click to edit">
          {value || <span className={styles.na}>Not mentioned</span>}
        </div>
      )}
      {quote && <div className={styles.bantQuote}>"{quote}"</div>}
    </div>
  );
}

function TalkRatio({ transcript }: { transcript: { speaker: string; text: string }[] }) {
  const counts: Record<string, number> = {};
  for (const seg of transcript) {
    counts[seg.speaker] = (counts[seg.speaker] || 0) + seg.text.split(' ').length;
  }
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, w]) => s + w, 0);
  if (total === 0 || entries.length === 0) return null;

  const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ec4899'];

  return (
    <div className={styles.talkRatio}>
      <div className={styles.talkRatioLabel}>Talk ratio</div>
      <div className={styles.talkBar}>
        {entries.map(([speaker, words], i) => (
          <div
            key={speaker}
            className={styles.talkSegment}
            style={{ width: `${(words / total) * 100}%`, background: COLORS[i % COLORS.length] }}
            title={`${speaker}: ${Math.round((words / total) * 100)}%`}
          />
        ))}
      </div>
      <div className={styles.talkLegend}>
        {entries.map(([speaker, words], i) => (
          <span key={speaker} className={styles.talkLegendItem}>
            <span className={styles.talkDot} style={{ background: COLORS[i % COLORS.length] }} />
            {speaker} {Math.round((words / total) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}

function MissedOpportunity({ text, botId }: { text: string; botId: string }) {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAsk() {
    setLoading(true);
    try {
      const res = await getCoachingResponse(botId, text);
      setSuggestion(res.suggestion);
    } catch {
      setSuggestion('Could not generate suggestion. Try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.missedCard}>
      <div className={styles.missedText}>{text}</div>
      {!suggestion && (
        <button className={styles.askBtn} onClick={handleAsk} disabled={loading}>
          {loading ? 'Thinking…' : 'What could I have said? →'}
        </button>
      )}
      {suggestion && (
        <div className={styles.suggestionBox}>
          <span className={styles.suggestionLabel}>Try this next time</span>
          <p className={styles.suggestionText}>"{suggestion}"</p>
          <button className={styles.askBtn} onClick={() => setSuggestion(null)}>Try again</button>
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
      </nav>
      <div className={styles.loading}><div className={styles.spinner} /> Loading call…</div>
    </div>
  );
}
