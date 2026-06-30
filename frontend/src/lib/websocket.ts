const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type MessageHandler = (data: unknown) => void;

export class ManagedWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closed = false;

  constructor(path: string) {
    this.url = `${WS_BASE}${path}`;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const url = token ? `${this.url}?token=${token}` : this.url;

    this.ws = new WebSocket(url);

    this.ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data as string);
        this.handlers.forEach((h) => h(data));
      } catch {
        // non-JSON message — ignore
      }
    };

    this.ws.onclose = () => {
      if (!this.closed) {
        this.reconnectTimer = setTimeout(() => this.connect(), 3000);
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  subscribe(handler: MessageHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  disconnect() {
    this.closed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }
}

const _instances = new Map<string, ManagedWebSocket>();

export function getWebSocket(path: string): ManagedWebSocket {
  if (!_instances.has(path)) {
    const ws = new ManagedWebSocket(path);
    _instances.set(path, ws);
    ws.connect();
  }
  return _instances.get(path)!;
}

export function closeWebSocket(path: string) {
  _instances.get(path)?.disconnect();
  _instances.delete(path);
}
