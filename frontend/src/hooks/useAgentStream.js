import { useState, useEffect, useRef, useCallback } from 'react';
import useWebSocket from './useWebSocket';

/**
 * useAgentStream — subscribes to agent health data via WebSocket (preferred)
 * with automatic fallback to SSE /api/v1/stream/agents.
 *
 * Returns:
 *   agents     — latest agent health snapshot (object keyed by agent name)
 *   connected  — boolean connection state
 *   lastUpdate — ISO timestamp of last successful event
 *   error      — last error message or null
 *   reconnect  — manually force a reconnection
 */
export default function useAgentStream() {
  // --- WebSocket transport (preferred) ---
  const ws = useWebSocket();

  // --- SSE fallback state ---
  const [sseAgents, setSseAgents] = useState({});
  const [sseConnected, setSseConnected] = useState(false);
  const [sseLastUpdate, setSseLastUpdate] = useState(null);
  const [sseError, setSseError] = useState(null);

  const esRef = useRef(null);
  const retryRef = useRef(null);
  const retryDelay = useRef(2000); // start at 2s, exponential back-off
  const wsWasConnected = useRef(false);

  const connectSSE = useCallback(function doConnectSSE() {
    // Don't start SSE if WebSocket is connected
    if (ws.connected) return;

    // Clean up any existing connection
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
    clearTimeout(retryRef.current);

    const es = new EventSource('/api/v1/stream/agents');
    esRef.current = es;

    es.onopen = () => {
      setSseConnected(true);
      setSseError(null);
      retryDelay.current = 2000; // reset backoff on successful connect
    };

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.agents) {
          setSseAgents(data.agents);
          setSseLastUpdate(data.timestamp);
        }
      } catch (err) {
        console.warn('[useAgentStream] SSE parse error:', err);
      }
    };

    es.onerror = () => {
      setSseConnected(false);
      setSseError('Stream disconnected — reconnecting…');
      es.close();
      esRef.current = null;

      // Exponential back-off: 2s → 4s → 8s → cap at 30s
      retryRef.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30000);
        doConnectSSE();
      }, retryDelay.current);
    };
  }, [ws.connected]);

  // Manage SSE lifecycle based on WebSocket connection state
  useEffect(() => {
    if (ws.connected) {
      // WebSocket connected — tear down SSE if active
      wsWasConnected.current = true;
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
      clearTimeout(retryRef.current);
      setSseConnected(false);
    } else if (!ws.connected && !esRef.current) {
      // WebSocket not connected and no SSE active — start SSE fallback
      connectSSE();
    }
  }, [ws.connected, connectSSE]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (esRef.current) esRef.current.close();
      clearTimeout(retryRef.current);
    };
  }, []);

  // --- Merge: prefer WebSocket data when connected ---
  const reconnect = useCallback(() => {
    ws.reconnect();
    // Also reset SSE so it can pick up if WS fails
    connectSSE();
  }, [ws, connectSSE]);

  if (ws.connected && ws.data) {
    return {
      agents: ws.data.agents || {},
      connected: true,
      lastUpdate: ws.data.timestamp || null,
      error: null,
      reconnect,
    };
  }

  // Fallback to SSE data
  return {
    agents: sseAgents,
    connected: sseConnected,
    lastUpdate: sseLastUpdate,
    error: ws.error || sseError,
    reconnect,
  };
}
