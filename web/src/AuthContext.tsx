import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';

const BASE = import.meta.env.VITE_API_URL ?? '';

interface AuthState {
  token: string | null;
  email: string | null;
  userId: number | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>({ token: null, email: null, userId: null });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('noteai_token');
    const email = localStorage.getItem('noteai_email');
    const userId = localStorage.getItem('noteai_user_id');
    if (token && email) {
      setAuth({ token, email, userId: userId ? parseInt(userId) : null });
    }
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string) {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    _persist(data);
  }

  async function register(email: string, password: string) {
    const res = await fetch(`${BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    _persist(data);
  }

  function _persist(data: { token: string; email: string; user_id: number }) {
    localStorage.setItem('noteai_token', data.token);
    localStorage.setItem('noteai_email', data.email);
    localStorage.setItem('noteai_user_id', String(data.user_id));
    setAuth({ token: data.token, email: data.email, userId: data.user_id });
  }

  function logout() {
    localStorage.removeItem('noteai_token');
    localStorage.removeItem('noteai_email');
    localStorage.removeItem('noteai_user_id');
    setAuth({ token: null, email: null, userId: null });
  }

  return (
    <AuthContext.Provider value={{ ...auth, login, register, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
