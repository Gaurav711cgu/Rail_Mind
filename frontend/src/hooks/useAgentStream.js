import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useAgentStream — subscribes to /api/v1/stream/agents SSE endpoint.
 *
 * Returns:
 *   agents     — latest agent health snapshot (object keyed by agent name)
 *   connected  — boolean connection state
 *   lastUpdate — ISO timestamp of last successful event
 *   error      — last error message or null
 *   reconnect  — manually force a reconnection
 */
export default function useAgentStream() {
  const [agents, setAgents] = useState({});
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);

  const esRef = useRef(null);
  const retryRef = useRef(null);
  const retryDelay = useRef(2000); // start at 2s, exponential back-off

  const connect = useCallback(() => {
    // Clean up any existing connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    clearTimeout(retryRef.current);

    const es = new EventSource('/api/v1/stream/agents');
    esRef.current = es;

    es.onopen = () => {
      setConnected(true);
      setError(null);
      retryDelay.current = 2000; // reset backoff on successful connect
    };

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.agents) {
          setAgents(data.agents);
          setLastUpdate(data.timestamp);
        }
      } catch (err) {
        console.warn('[useAgentStream] Parse error:', err);
      }
    };

    es.onerror = () => {
      setConnected(false);
      setError('Stream disconnected — reconnecting…');
      es.close();
      esRef.current = null;

      // Exponential back-off: 2s → 4s → 8s → cap at 30s
      retryRef.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30000);
        connect();
      }, retryDelay.current);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (esRef.current) esRef.current.close();
      clearTimeout(retryRef.current);
    };
  }, [connect]);

  return { agents, connected, lastUpdate, error, reconnect: connect };
}
