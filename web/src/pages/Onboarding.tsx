import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import styles from './Onboarding.module.css';

const STEPS = [
  {
    n: 1, title: 'Connect HubSpot', icon: '🔗',
    desc: 'Link your HubSpot account so NoteAI can push BANT data to your deals automatically.',
    action: 'Connect HubSpot →',
    skip: 'Skip for now',
  },
  {
    n: 2, title: 'Send your first bot', icon: '🤖',
    desc: 'Paste a Google Meet, Zoom, or Teams link. The bot joins, records, and transcribes for you.',
    action: 'Go to Dashboard →',
    skip: null,
  },
  {
    n: 3, title: 'Review & push', icon: '✅',
    desc: 'After the call, NoteAI extracts BANT data. Review it, edit anything wrong, then push to HubSpot in one click.',
    action: 'Got it, let\'s go →',
    skip: null,
  },
];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const navigate = useNavigate();
  const { email } = useAuth();

  function handleAction() {
    if (step === 0) {
      navigate('/app/settings');
    } else if (step === STEPS.length - 1) {
      navigate('/app');
    } else {
      setStep(s => s + 1);
    }
  }

  const current = STEPS[step];

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.logo}>NoteAI</div>
        <p className={styles.welcome}>Welcome{email ? `, ${email.split('@')[0]}` : ''}! Let's get you set up.</p>

        {/* Progress dots */}
        <div className={styles.dots}>
          {STEPS.map((_, i) => (
            <div key={i} className={styles.dot + (i === step ? ' ' + styles.dotActive : i < step ? ' ' + styles.dotDone : '')} />
          ))}
        </div>

        <div className={styles.stepCard}>
          <div className={styles.stepIcon}>{current.icon}</div>
          <div className={styles.stepN}>Step {current.n} of {STEPS.length}</div>
          <h2 className={styles.stepTitle}>{current.title}</h2>
          <p className={styles.stepDesc}>{current.desc}</p>
        </div>

        <button className={styles.btnPrimary} onClick={handleAction}>
          {current.action}
        </button>

        {current.skip && (
          <button className={styles.btnSkip} onClick={() => setStep(s => s + 1)}>
            {current.skip}
          </button>
        )}
      </div>
    </div>
  );
}
