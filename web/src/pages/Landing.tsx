import { Link } from 'react-router-dom';
import styles from './Landing.module.css';

const features = [
  { icon: '🎙️', title: 'Auto-joins every call', desc: 'Bot joins Zoom, Meet, and Teams automatically. No manual recording needed.' },
  { icon: '🗣️', title: 'Speaker diarization', desc: 'Knows who said what. Prospect signals are separated from rep talk — only buyer signals hit your CRM.' },
  { icon: '🎯', title: 'BANT + SaaS signals', desc: 'Pulls Budget, Authority, Need, Timeline — plus current tool, seat count, MRR potential, and contract end date.' },
  { icon: '⚔️', title: 'Competitor detection', desc: 'Automatically flags any competitor mentioned in the call so your AEs can prep the right battle card.' },
  { icon: '📈', title: 'Rep coaching scores', desc: 'Every call gets scored 0–100. See exactly what topics were missed and what the rep should do next.' },
  { icon: '🔗', title: 'Deep HubSpot sync', desc: 'Updates deal stage, logs a note, and creates tasks for every action item — all in one click.' },
];

const steps = [
  { n: '1', title: 'Paste a meeting link', desc: 'Drop in a Zoom, Meet, or Teams URL. The bot joins before the call starts.' },
  { n: '2', title: 'AI does the work', desc: 'Transcription with speaker labels → BANT extraction → call summary. All automatic.' },
  { n: '3', title: 'Review and sync', desc: 'See the extracted data, edit anything wrong, then push to HubSpot in one click.' },
];

const plans = [
  { name: 'Starter', price: 'Free', desc: 'For individuals testing the tool', features: ['5 calls/month', 'BANT extraction', 'HubSpot sync', 'Email support'] },
  { name: 'Pro', price: '$29', per: '/mo', desc: 'For active sales reps', features: ['Unlimited calls', 'Everything in Starter', 'Call sentiment analysis', 'Priority support'], highlight: true },
  { name: 'Team', price: '$99', per: '/mo', desc: 'For sales teams', features: ['Everything in Pro', 'Up to 10 seats', 'Team dashboard', 'Dedicated onboarding'] },
];

export default function Landing() {
  return (
    <div className={styles.page}>
      {/* Nav */}
      <nav className={styles.nav}>
        <span className={styles.logo}>NoteAI</span>
        <div className={styles.navLinks}>
          <a href="#features">Features</a>
          <a href="#pricing">Pricing</a>
          <Link to="/login" className={styles.navCta}>Sign in →</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className={styles.hero}>
        <div className={styles.badge}><span className={styles.badgeDot} />Built for SaaS sales teams</div>
        <h1 className={styles.heroTitle}>
          Your reps sell.<br />
          <span className={styles.accent}>NoteAI handles the rest.</span>
        </h1>
        <p className={styles.heroSub}>
          Joins every call, extracts BANT + SaaS signals, scores your reps,
          detects competitors, and syncs everything to HubSpot — without a single keystroke.
        </p>
        <div className={styles.heroCtas}>
          <Link to="/register" className={styles.btnPrimary}>Try it free</Link>
          <a href="#how-it-works" className={styles.btnGhost}>See how it works</a>
        </div>
        <p className={styles.heroNote}>No credit card required · Works with Zoom, Meet, Teams</p>

        {/* Mock UI preview */}
        <div className={styles.uiPreview}>
          <div className={styles.uiBar}>
            <span className={styles.dot} style={{ background: '#ef4444' }} />
            <span className={styles.dot} style={{ background: '#f59e0b' }} />
            <span className={styles.dot} style={{ background: '#22c55e' }} />
            <span className={styles.uiBarTitle}>NoteAI — Call Review</span>
          </div>
          <div className={styles.uiBody}>
            <div className={styles.uiLeft}>
              <div className={styles.uiLabel}>Transcript</div>
              <div className={styles.uiLine}><strong>Speaker A</strong> · 00:01:12</div>
              <div className={styles.uiText}>Our budget for this quarter is around $50k, but we could go higher if the ROI is clear.</div>
              <div className={styles.uiLine} style={{ marginTop: 12 }}><strong>Speaker B</strong> · 00:02:34</div>
              <div className={styles.uiText}>Final decision goes through our VP of Sales, Sarah Chen.</div>
            </div>
            <div className={styles.uiRight}>
              <div className={styles.uiLabel}>BANT Extraction</div>
              <div className={styles.bantRow}><span className={styles.bantKey}>Budget</span><span className={styles.bantVal}>~$50k</span><span className={styles.conf + ' ' + styles.high}>high</span></div>
              <div className={styles.bantRow}><span className={styles.bantKey}>Authority</span><span className={styles.bantVal}>Sarah Chen, VP Sales</span><span className={styles.conf + ' ' + styles.high}>high</span></div>
              <div className={styles.bantRow}><span className={styles.bantKey}>Need</span><span className={styles.bantVal}>Manual CRM entry</span><span className={styles.conf + ' ' + styles.med}>medium</span></div>
              <div className={styles.bantRow}><span className={styles.bantKey}>Timeline</span><span className={styles.bantVal}>This quarter</span><span className={styles.conf + ' ' + styles.med}>medium</span></div>
              <button className={styles.uiPush}>Push to HubSpot →</button>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className={styles.section} id="how-it-works">
        <div className={styles.sectionInner}>
          <p className={styles.sectionTag}>How it works</p>
          <h2 className={styles.sectionTitle}>From call to CRM in 3 steps</h2>
          <div className={styles.steps}>
            {steps.map(s => (
              <div key={s.n} className={styles.step}>
                <div className={styles.stepN}>{s.n}</div>
                <h3 className={styles.stepTitle}>{s.title}</h3>
                <p className={styles.stepDesc}>{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className={styles.section + ' ' + styles.sectionAlt} id="features">
        <div className={styles.sectionInner}>
          <p className={styles.sectionTag}>Features</p>
          <h2 className={styles.sectionTitle}>Built for SaaS discovery calls</h2>
          <div className={styles.features}>
            {features.map(f => (
              <div key={f.title} className={styles.feature}>
                <div className={styles.featureIcon}>{f.icon}</div>
                <h3 className={styles.featureTitle}>{f.title}</h3>
                <p className={styles.featureDesc}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className={styles.section} id="pricing">
        <div className={styles.sectionInner}>
          <p className={styles.sectionTag}>Pricing</p>
          <h2 className={styles.sectionTitle}>Simple, transparent pricing</h2>
          <div className={styles.plans}>
            {plans.map(p => (
              <div key={p.name} className={styles.plan + (p.highlight ? ' ' + styles.planHighlight : '')}>
                {p.highlight && <div className={styles.planBadge}>Most popular</div>}
                <div className={styles.planName}>{p.name}</div>
                <div className={styles.planPrice}>{p.price}<span className={styles.planPer}>{p.per}</span></div>
                <div className={styles.planDesc}>{p.desc}</div>
                <ul className={styles.planFeatures}>
                  {p.features.map(f => <li key={f}>✓ {f}</li>)}
                </ul>
                <Link to="/register" className={p.highlight ? styles.btnPrimary : styles.btnOutline}>
                  Get started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className={styles.ctaSection}>
        <div className={styles.sectionInner}>
          <h2 className={styles.ctaTitle}>Your competitors are already using AI.<br />Your reps shouldn't be the bottleneck.</h2>
          <p className={styles.ctaSub}>NoteAI captures everything — BANT, competitors, coaching — so your team can close faster.</p>
          <Link to="/register" className={styles.btnPrimary}>Start for free →</Link>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <span className={styles.logo}>NoteAI</span>
        <span className={styles.footerMuted}>
          Built by{' '}
          <a
            href="https://www.linkedin.com/in/rishiraj-paul/"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.footerLink}
          >
            Rishiraj Paul
          </a>
          {' '}· {new Date().getFullYear()}
        </span>
      </footer>
    </div>
  );
}
