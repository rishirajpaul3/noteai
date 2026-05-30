import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchDealTimeline } from '../api';
import styles from './DealTimeline.module.css';

const SENTIMENT_EMOJI: Record<string, string> = {
  positive: '🟢', neutral: '🟡', negative: '🔴',
};

const STAGE_COLOR: Record<string, string> = {
  early: '#6366f1', mid: '#f59e0b', late: '#10b981', lost: '#ef4444',
};

const PROGRESS_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  new:     { bg: '#EFF6FF', color: '#2563EB', label: 'New' },
  updated: { bg: '#F0FDF4', color: '#16a34a', label: 'Updated' },
  same:    { bg: '#F8FAFC', color: '#94a3b8', label: 'Same' },
  missing: { bg: '#FEF2F2', color: '#dc2626', label: 'Missing' },
};

export default function DealTimeline() {
  const { dealId } = useParams<{ dealId: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['deal-timeline', dealId],
    queryFn: () => fetchDealTimeline(dealId!),
    enabled: !!dealId,
  });

  if (isLoading) return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
      </nav>
      <div className={styles.loading}>Loading deal timeline…</div>
    </div>
  );

  if (error || !data) return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
      </nav>
      <div className={styles.error}>Deal not found.</div>
    </div>
  );

  const { calls } = data;

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
        <span className={styles.dealId}>Deal {dealId}</span>
      </nav>

      <main className={styles.main}>
        <div className={styles.header}>
          <h1 className={styles.title}>Deal Timeline</h1>
          <p className={styles.subtitle}>
            {calls.length} {calls.length === 1 ? 'call' : 'calls'} · tracking how BANT evolved across the deal
          </p>
        </div>

        {calls.length === 0 && (
          <div className={styles.empty}>
            No completed calls found for this deal. Make sure you set the Deal ID when launching bots.
          </div>
        )}

        <div className={styles.timeline}>
          {calls.map((call, index) => {
            const date = call.created_at
              ? new Date(call.created_at * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
              : 'Unknown date';

            const score = call.coaching_score;
            const scoreColor = score == null ? '#94a3b8' : score >= 75 ? '#16a34a' : score >= 50 ? '#ca8a04' : '#dc2626';

            return (
              <div key={call.bot_id} className={styles.callCard}>
                {/* Timeline connector */}
                <div className={styles.connector}>
                  <div className={styles.node} />
                  {index < calls.length - 1 && <div className={styles.line} />}
                </div>

                <div className={styles.cardBody}>
                  {/* Header row */}
                  <div className={styles.cardHeader}>
                    <div className={styles.cardMeta}>
                      <span className={styles.cardDate}>{date}</span>
                      {call.prospect_name && (
                        <span className={styles.prospectTag}>{call.prospect_name}</span>
                      )}
                    </div>
                    <div className={styles.cardBadges}>
                      {call.overall_sentiment && (
                        <span title={call.overall_sentiment}>{SENTIMENT_EMOJI[call.overall_sentiment] || ''}</span>
                      )}
                      {call.deal_stage_signal && (
                        <span className={styles.stageBadge} style={{ color: STAGE_COLOR[call.deal_stage_signal] || '#64748b' }}>
                          {call.deal_stage_signal}
                        </span>
                      )}
                      {score != null && (
                        <span className={styles.scoreBadge} style={{ color: scoreColor, borderColor: scoreColor + '40', background: scoreColor + '12' }}>
                          {score}/100
                        </span>
                      )}
                    </div>
                  </div>

                  {/* BANT snapshot */}
                  <div className={styles.bantGrid}>
                    {(['budget', 'authority', 'need', 'timeline'] as const).map(field => {
                      const value = call.bant_snapshot[field];
                      const progress = call.bant_progress[field] || 'missing';
                      const ps = PROGRESS_STYLE[progress];
                      return (
                        <div key={field} className={styles.bantCell} style={{ background: ps.bg }}>
                          <div className={styles.bantCellHeader}>
                            <span className={styles.bantCellLabel}>{field}</span>
                            <span className={styles.bantCellProgress} style={{ color: ps.color }}>{ps.label}</span>
                          </div>
                          <div className={styles.bantCellValue} style={{ color: value ? '#0f172a' : '#94a3b8' }}>
                            {value || 'Not discussed'}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <Link to={`/app/calls/${call.bot_id}`} className={styles.viewLink}>
                    View full call →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
