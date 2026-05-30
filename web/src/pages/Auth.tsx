import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import styles from './Auth.module.css';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await login(email, password);
      navigate('/app');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" sub="Sign in to your NoteAI account">
      <form onSubmit={handleSubmit} className={styles.form}>
        <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />
        <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" />
        {error && <p className={styles.error}>{error}</p>}
        <button className={styles.btnPrimary} disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in →'}
        </button>
      </form>
      <p className={styles.switchLink}>
        No account? <Link to="/register">Create one free</Link>
      </p>
    </AuthLayout>
  );
}

export function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      await register(email, password);
      navigate('/onboarding');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Start for free" sub="No credit card required">
      <form onSubmit={handleSubmit} className={styles.form}>
        <Field label="Work email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />
        <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="8+ characters" />
        {error && <p className={styles.error}>{error}</p>}
        <button className={styles.btnPrimary} disabled={loading}>
          {loading ? 'Creating account…' : 'Create account →'}
        </button>
      </form>
      <p className={styles.switchLink}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}

function AuthLayout({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <Link to="/" className={styles.logo}>NoteAI</Link>
        <h1 className={styles.title}>{title}</h1>
        <p className={styles.sub}>{sub}</p>
        {children}
      </div>
    </div>
  );
}

function Field({ label, type, value, onChange, placeholder }: {
  label: string; type: string; value: string;
  onChange: (v: string) => void; placeholder: string;
}) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      <input
        className={styles.input} type={type} value={value} placeholder={placeholder}
        onChange={e => onChange(e.target.value)} required
      />
    </div>
  );
}
