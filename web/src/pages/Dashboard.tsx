import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchCalls, createBot, type Call } from '../api';
import { useAuth } from '../AuthContext';
import styles from './Dashboard.module.css';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  joining:      { label: 'Joining',       color: '#3b82f6' },
  transcribing: { label: 'Transcribing',  color: '#f59e0b' },
  extracting:   { label: 'Extracting AI', color: '#8b5cf6' },
  ready:        { label: 'Ready',         color: '#10b981' },
  reviewed:     { label: 'Reviewed',      color: '#10b981' },
  synced:       { label: 'Synced ✓',      color: '#64748b' },
  failed:       { label: 'Failed',        color: '#ef4444' },
};

function Badge({ status }: { status: string }) {
  const s = STATUS_LABELS[status] || { label: status, color: '#64748b' };
  return (
    <span className={styles.badge} style={{ background: s.color + '18', color: s.color }}>
      {s.label}
    </span>
  );
}

export default function Dashboard() {
  const [url, setUrl] = useState('');
  const [prospectName, setProspectName] = useState('');
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState('');

  const { email, logout } = useAuth();
  const { data: calls = [], refetch } = useQuery<Call[]>({
    queryKey: ['calls'],
    queryFn: fetchCalls,
    refetchInterval: 10000,
  });

  async function handleLaunch(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLaunching(true);
    setError('');
    try {
      await createBot(url.trim(), prospectName.trim());
      setUrl('');
      setProspectName('');
      refetch();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLaunching(false);
    }
  }

  const active = calls.filter(c => !['synced', 'failed'].includes(c.status));
  const past = calls.filter(c => ['synced', 'failed'].includes(c.status));

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/" className={styles.logo}>NoteAI</Link>
        <span className={styles.navTitle}>Dashboard</span>
        <div className={styles.navRight}>
          <span className={styles.navEmail}>{email}</span>
          <Link to="/app/settings" className={styles.navSettings}>Settings</Link>
          <button className={styles.navLogout} onClick={logout}>Sign out</button>
        </div>
      </nav>

      <main className={styles.main}>
        {/* Launch a bot */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Join a call</h2>
          <form onSubmit={handleLaunch} className={styles.form}>
            <input
              className={styles.input}
              type="url"
              placeholder="https://meet.google.com/xxx-xxx-xxx"
              value={url}
              onChange={e => setUrl(e.target.value)}
              required
            />
            <input
              className={styles.input}
              type="text"
              placeholder="Prospect name (e.g. Sarah from Acme)"
              value={prospectName}
              onChange={e => setProspectName(e.target.value)}
            />
            <button className={styles.btnPrimary} disabled={launching}>
              {launching ? 'Launching…' : 'Send bot →'}
            </button>
          </form>
          {error && <p className={styles.error}>{error}</p>}
        </div>

        {/* Active calls */}
        {active.length > 0 && (
          <section>
            <h3 className={styles.sectionLabel}>Active</h3>
            <div className={styles.callList}>
              {active.map(c => <CallRow key={c.bot_id} call={c} />)}
            </div>
          </section>
        )}

        {/* Past calls */}
        {past.length > 0 && (
          <section>
            <h3 className={styles.sectionLabel}>Completed</h3>
            <div className={styles.callList}>
              {past.map(c => <CallRow key={c.bot_id} call={c} />)}
            </div>
          </section>
        )}

        {calls.length === 0 && (
          <div className={styles.empty}>
            <div className={styles.emptyIcon}>🎙️</div>
            <p>No calls yet. Paste a meeting link above to get started.</p>
          </div>
        )}
      </main>
    </div>
  );
}

function CallRow({ call }: { call: Call }) {
  const sentiment = call.bant?.overall_sentiment;
  const sentimentEmoji = sentiment === 'positive' ? '🟢' : sentiment === 'negative' ? '🔴' : sentiment ? '🟡' : null;

  return (
    <Link to={`/app/calls/${call.bot_id}`} className={styles.callRow}>
      <div className={styles.callInfo}>
        <div className={styles.callUrl}>{call.meeting_url}</div>
        <div className={styles.callMeta}>
          <Badge status={call.status} />
          {sentimentEmoji && <span title={sentiment}>{sentimentEmoji}</span>}
          {call.bant?.deal_stage_signal && (
            <span className={styles.stageTag}>{call.bant.deal_stage_signal}</span>
          )}
        </div>
      </div>
      <span className={styles.arrow}>→</span>
    </Link>
  );
}
