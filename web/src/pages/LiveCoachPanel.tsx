import { useEffect, useRef, useState } from 'react';
import styles from './LiveCoachPanel.module.css';

interface Tip {
  id: number;
  type: 'tip' | 'status' | 'connected' | 'done';
  message: string;
}

interface Props {
  botId: string;
}

const WS_BASE = import.meta.env.VITE_WS_URL ?? (
  typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:8000'
);

export default function LiveCoachPanel({ botId }: Props) {
  const [tips, setTips] = useState<Tip[]>([]);
  const [connected, setConnected] = useState(false);
  const [done, setDone] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const counterRef = useRef(0);
  const tipsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/calls/${botId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Keep-alive ping every 30s
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 30_000);
      ws.addEventListener('close', () => clearInterval(ping));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;

        const tip: Tip = {
          id: ++counterRef.current,
          type: data.type,
          message: data.message,
        };

        setTips(prev => [...prev, tip]);

        if (data.type === 'done') {
          setDone(true);
          ws.close();
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    return () => {
      ws.close();
    };
  }, [botId]);

  // Auto-scroll to newest tip
  useEffect(() => {
    tipsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [tips]);

  if (done) return null;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.dot + (connected ? ' ' + styles.dotLive : '')} />
        <span className={styles.title}>Live Coach</span>
        <span className={styles.subtitle}>{connected ? 'Listening…' : 'Connecting…'}</span>
      </div>

      <div className={styles.feed}>
        {tips.length === 0 && (
          <div className={styles.waiting}>
            Waiting for the conversation to start…
          </div>
        )}
        {tips.map(tip => (
          <div
            key={tip.id}
            className={
              styles.tipCard +
              (tip.type === 'tip' ? ' ' + styles.tipCardMain : ' ' + styles.tipCardStatus)
            }
          >
            {tip.type === 'tip' && <span className={styles.tipIcon}>💡</span>}
            <span className={styles.tipText}>{tip.message}</span>
          </div>
        ))}
        <div ref={tipsEndRef} />
      </div>
    </div>
  );
}
