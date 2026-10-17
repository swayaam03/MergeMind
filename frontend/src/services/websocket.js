/**
 * WebSocket service for subscribing to live MergeMind pipeline and merge events.
 */

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

function getWebSocketUrl(channelId) {
  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const backendHost = BACKEND_URL.replace(/^https?:\/\//, '');
  return `${wsProto}//${backendHost}/api/ws/progress/${channelId}`;
}

export function subscribeToPipelineProgress(channelId, onEvent, onError) {
  let ws = null;
  let isClosed = false;
  let reconnectTimer = null;

  function connect() {
    if (isClosed) return;

    try {
      const url = getWebSocketUrl(channelId);
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to channel: ${channelId}`);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onEvent) onEvent(data);
        } catch (err) {
          console.warn('[WebSocket] Received non-JSON message:', event.data);
        }
      };

      ws.onerror = (err) => {
        console.warn(`[WebSocket] Error on channel ${channelId}:`, err);
        if (onError) onError(err);
      };

      ws.onclose = () => {
        if (!isClosed) {
          reconnectTimer = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    } catch (err) {
      console.error('[WebSocket] Setup exception:', err);
    }
  }

  connect();

  return function unsubscribe() {
    isClosed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  };
}
