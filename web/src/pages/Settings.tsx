import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import styles from './Settings.module.css';

const BASE = import.meta.env.VITE_API_URL ?? '';

async function fetchHubspotSettings() {
  const res = await fetch(`${BASE}/settings/hubspot`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

async function saveToken(token: string) {
  const res = await fetch(`${BASE}/settings/hubspot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Failed to save token');
  return data;
}

async function disconnectHubspot() {
  const res = await fetch(`${BASE}/settings/hubspot`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to disconnect');
  return res.json();
}

export default function Settings() {
  const [token, setToken] = useState('');
  const qc = useQueryClient();

  const { data: settings } = useQuery({
    queryKey: ['hubspot-settings'],
    queryFn: fetchHubspotSettings,
  });

  const saveMutation = useMutation({
    mutationFn: () => saveToken(token),
    onSuccess: () => { setToken(''); qc.invalidateQueries({ queryKey: ['hubspot-settings'] }); },
  });

  const disconnectMutation = useMutation({
    mutationFn: disconnectHubspot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hubspot-settings'] }),
  });

  return (
    <div className={styles.page}>
      <nav className={styles.nav}>
        <Link to="/app" className={styles.back}>← Dashboard</Link>
        <span className={styles.logo}>NoteAI</span>
        <span />
      </nav>

      <main className={styles.main}>
        <h1 className={styles.title}>Settings</h1>

        {/* HubSpot connection */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>HubSpot</h2>
              <p className={styles.cardDesc}>Connect your HubSpot account to push BANT data to your deals automatically.</p>
            </div>
            {settings?.connected && (
              <span className={styles.connectedBadge}>● Connected</span>
            )}
          </div>

          {settings?.connected ? (
            <div className={styles.connected}>
              <div className={styles.portalInfo}>
                <div className={styles.portalName}>{settings.portal_name}</div>
                <div className={styles.tokenPreview}>Token: {settings.token_preview}</div>
              </div>
              <div className={styles.connectedNote}>
                ✓ Custom properties have been created in your portal automatically.
              </div>
              <button
                className={styles.btnDanger}
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
              >
                {disconnectMutation.isPending ? 'Disconnecting…' : 'Disconnect HubSpot'}
              </button>
            </div>
          ) : (
            <div className={styles.connectForm}>
              <div className={styles.steps}>
                <p className={styles.step}><strong>1.</strong> Go to HubSpot → Settings → Integrations → Private Apps</p>
                <p className={styles.step}><strong>2.</strong> Create a new Private App with scopes: <code>crm.objects.deals.write</code>, <code>crm.objects.contacts.write</code>, <code>crm.schemas.deals.write</code>, <code>crm.schemas.contacts.write</code>, <code>timeline</code></p>
                <p className={styles.step}><strong>3.</strong> Copy the token and paste it below</p>
              </div>
              <div className={styles.inputRow}>
                <input
                  className={styles.input}
                  type="password"
                  placeholder="pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={token}
                  onChange={e => setToken(e.target.value)}
                />
                <button
                  className={styles.btnPrimary}
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending || !token.trim()}
                >
                  {saveMutation.isPending ? 'Verifying…' : 'Connect'}
                </button>
              </div>
              {saveMutation.isError && (
                <p className={styles.error}>{(saveMutation.error as Error).message}</p>
              )}
            </div>
          )}
        </div>

        {/* What gets created */}
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>What NoteAI creates in HubSpot</h2>
          <p className={styles.cardDesc}>When you connect, these custom properties are automatically created in your portal:</p>
          <div className={styles.propList}>
            {[
              ['Budget Range', 'budget_range', 'Text'],
              ['Decision Maker Name', 'decision_maker_name', 'Text'],
              ['Primary Pain Point', 'primary_pain_point', 'Text area'],
              ['Expected Close Timeline', 'expected_close_timeline', 'Text'],
              ['Deal Urgency', 'deal_urgency', 'Dropdown'],
              ['Call Sentiment', 'call_sentiment', 'Dropdown'],
              ['BANT Confidence', 'bant_confidence', 'Dropdown'],
              ['Last Call Summary', 'last_call_summary', 'Text area'],
            ].map(([label, name, type]) => (
              <div key={name} className={styles.propRow}>
                <div>
                  <div className={styles.propLabel}>{label}</div>
                  <div className={styles.propName}>{name}</div>
                </div>
                <span className={styles.propType}>{type}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
