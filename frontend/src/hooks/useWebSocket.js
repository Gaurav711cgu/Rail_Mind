import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * useWebSocket — connects to a WebSocket endpoint with exponential backoff.
 *
 * Returns:
 *   data      — latest parsed JSON message from the server
 *   connected — boolean connection state
 *   error     — last error message or null
 *   reconnect — manually force a reconnection
 */
export default function useWebSocket() {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const retryRef = useRef(null);
  const retryDelay = useRef(2000); // start at 2s, exponential backoff
  const unmountedRef = useRef(false);

  const connect = useCallback(() => {
    // Don't reconnect if component has unmounted
    if (unmountedRef.current) return;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    clearTimeout(retryRef.current);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/api/v1/stream/ws`;

    let ws;
    try {
      ws = new WebSocket(url);
    } catch (err) {
      setError(`WebSocket creation failed: ${err.message}`);
      setConnected(false);
      scheduleRetry();
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (unmountedRef.current) return;
      setConnected(true);
      setError(null);
      retryDelay.current = 2000; // reset backoff on successful connect
    };

    ws.onmessage = (evt) => {
      if (unmountedRef.current) return;
      try {
        const parsed = JSON.parse(evt.data);
        setData(parsed);
      } catch (err) {
        console.warn('[useWebSocket] Parse error:', err);
      }
    };

    ws.onerror = () => {
      if (unmountedRef.current) return;
      setError('WebSocket error');
    };

    ws.onclose = () => {
      if (unmountedRef.current) return;
      setConnected(false);
      setError('WebSocket disconnected — reconnecting…');
      wsRef.current = null;
      scheduleRetry();
    };
  }, []);

  const scheduleRetry = useCallback(() => {
    if (unmountedRef.current) return;
    retryRef.current = setTimeout(() => {
      retryDelay.current = Math.min(retryDelay.current * 2, 30000);
      connect();
    }, retryDelay.current);
  }, [connect]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();
    return () => {
      unmountedRef.current = true;
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      clearTimeout(retryRef.current);
    };
  }, [connect]);

  return { data, connected, error, reconnect: connect };
}
