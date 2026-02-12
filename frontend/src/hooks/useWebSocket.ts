/**
 * WebSocket hook for agent runtime streaming
 *
 * Supports auto-reconnect (exponential backoff) and connection state management
 */

import { useState, useCallback, useRef } from 'react';
import type { RuntimeMessage } from '@/types';

export type WebSocketStatus = 'idle' | 'connecting' | 'connected' | 'error' | 'closed';

/** Reconnect configuration */
const RECONNECT_BASE_DELAY = 1000;   // Initial reconnect interval 1s
const RECONNECT_MAX_DELAY = 16000;   // Max reconnect interval 16s
const RECONNECT_MAX_ATTEMPTS = 5;    // Max reconnect attempts

interface UseAgentWebSocketOptions {
  onMessage?: (message: RuntimeMessage) => void;
  onError?: (error: Event) => void;
  onComplete?: () => void;
  onClose?: () => void;
}

export function useAgentWebSocket(options: UseAgentWebSocketOptions = {}) {
  const [status, setStatus] = useState<WebSocketStatus>('idle');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  // Save the latest run params for reconnection
  const lastParamsRef = useRef<{ agentId: string; userId: string; inputContent: string } | null>(null);
  // Flag for intentional close by user (skip reconnect)
  const intentionalCloseRef = useRef(false);
  // Flag for receiving complete message (normal finish, skip reconnect)
  const completedRef = useRef(false);

  const { onMessage, onError, onComplete, onClose } = options;

  /** Clear reconnect timer */
  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  /** Create WebSocket connection */
  const connect = useCallback(
    (agentId: string, userId: string, inputContent: string): Promise<void> => {
      return new Promise<void>((resolve, reject) => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/agent/run`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        setStatus('connecting');

        ws.onopen = () => {
          setStatus('connected');
          reconnectAttemptRef.current = 0; // Connection succeeded, reset reconnect counter
          ws.send(JSON.stringify({
            agent_id: agentId,
            user_id: userId,
            input_content: inputContent,
            working_source: 'chat',
          }));
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data) as RuntimeMessage;
            onMessage?.(message);

            if (message.type === 'complete') {
              completedRef.current = true;
              onComplete?.();
              resolve();
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onerror = (error) => {
          setStatus('error');
          onError?.(error);
          reject(error);
        };

        ws.onclose = () => {
          wsRef.current = null;

          // Normal completion or intentional close -> skip reconnect
          if (completedRef.current || intentionalCloseRef.current) {
            setStatus('closed');
            onClose?.();
            return;
          }

          // Unexpected disconnect -> attempt reconnect
          if (reconnectAttemptRef.current < RECONNECT_MAX_ATTEMPTS && lastParamsRef.current) {
            const attempt = reconnectAttemptRef.current;
            const delay = Math.min(RECONNECT_BASE_DELAY * Math.pow(2, attempt), RECONNECT_MAX_DELAY);
            console.warn(`WebSocket closed unexpectedly. Reconnecting in ${delay}ms (attempt ${attempt + 1}/${RECONNECT_MAX_ATTEMPTS})`);
            setStatus('connecting');

            reconnectTimerRef.current = setTimeout(() => {
              reconnectAttemptRef.current++;
              const params = lastParamsRef.current!;
              connect(params.agentId, params.userId, params.inputContent).catch(() => {
                // Reconnect failure will be handled by the next onclose
              });
            }, delay);
          } else {
            setStatus('error');
            onClose?.();
          }
        };
      });
    },
    [onMessage, onError, onComplete, onClose]
  );

  /** Initiate a new Agent request */
  const run = useCallback(
    async (agentId: string, userId: string, inputContent: string) => {
      // Close existing connection
      if (wsRef.current) {
        intentionalCloseRef.current = true;
        wsRef.current.close();
        intentionalCloseRef.current = false;
      }
      clearReconnectTimer();

      // Reset state
      reconnectAttemptRef.current = 0;
      completedRef.current = false;
      intentionalCloseRef.current = false;
      lastParamsRef.current = { agentId, userId, inputContent };

      return connect(agentId, userId, inputContent);
    },
    [connect, clearReconnectTimer]
  );

  /** Manually close connection (skip reconnect) */
  const close = useCallback(() => {
    clearReconnectTimer();
    intentionalCloseRef.current = true;
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    lastParamsRef.current = null;
    setStatus('idle');
  }, [clearReconnectTimer]);

  return {
    run,
    close,
    status,
    isConnected: status === 'connected',
    isLoading: status === 'connecting' || status === 'connected',
  };
}
