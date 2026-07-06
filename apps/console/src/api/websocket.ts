import { useConnectionStore } from '@/stores/connection';

export interface WsMessage {
  type: 'presence' | 'cursor' | 'finding_update';
  payload: any;
}

export class VergeWebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectTimeout: any = null;
  private reconnectAttempts = 0;
  private handlers: Set<(msg: WsMessage) => void> = new Set();

  constructor(private url: string) {}

  connect() {
    try {
      const connStore = useConnectionStore.getState();
      connStore.setStatus('reconnecting');

      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to Verge sync server');
        connStore.setStatus('connected');
        connStore.setLastConnected(new Date().toISOString());
        connStore.resetReconnectAttempts();
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WsMessage;
          this.handlers.forEach((h) => h(msg));
        } catch {
          console.warn('[WebSocket] Failed to parse message:', event.data);
        }
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Connection closed');
        connStore.setStatus('disconnected');
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.error('[WebSocket] Error:', err);
        this.ws?.close();
      };
    } catch (err) {
      console.error('[WebSocket] Connection setup failed:', err);
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    const connStore = useConnectionStore.getState();
    if (this.reconnectAttempts >= 5) {
      console.warn('[WebSocket] Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 15000);
    this.reconnectTimeout = setTimeout(() => {
      connStore.incrementReconnectAttempts();
      this.reconnectAttempts++;
      this.connect();
    }, delay);
  }

  send(msg: WsMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  subscribe(handler: (msg: WsMessage) => void) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  close() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.ws?.close();
  }
}
