// ============================================================
// AgentChatManager — WebSocket chat manager with reconnection
// Handles WebSocket lifecycle, message queuing, and streaming
// ============================================================

import type {
  WsMessageFrame,
  WsProgressFrame,
  WsResultFrame,
  WsErrorFrame,
  WsConnectionState,
  ContextSnapshot,
} from '../types';

type WsAnyFrame = WsMessageFrame | WsProgressFrame | WsResultFrame | WsErrorFrame;

interface AgentChatManagerOptions {
  maxRetries?: number;
  baseRetryMs?: number;
}

export class AgentChatManager {
  private ws: WebSocket | null = null;
  private connectionState: WsConnectionState = 'disconnected';
  private messageQueue: WsMessageFrame[] = [];
  private retryCount = 0;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private url = '';
  private maxRetries: number;
  private baseRetryMs: number;

  // Event callbacks
  onMessage: ((frame: WsResultFrame) => void) | null = null;
  onProgress: ((frame: WsProgressFrame) => void) | null = null;
  onStreamChunk: ((messageId: string, chunk: string) => void) | null = null;
  onConnectionChange: ((state: WsConnectionState) => void) | null = null;
  onError: ((frame: WsErrorFrame) => void) | null = null;

  constructor(options: AgentChatManagerOptions = {}) {
    this.maxRetries = options.maxRetries ?? 5;
    this.baseRetryMs = options.baseRetryMs ?? 1000;
  }

  connect(url: string): void {
    this.url = url;
    this.retryCount = 0;
    this.doConnect();
  }

  disconnect(): void {
    this.retryCount = this.maxRetries; // prevent reconnect
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.setConnectionState('disconnected');
  }

  send(content: string, context: ContextSnapshot): string {
    const id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const frame: WsMessageFrame = {
      type: 'message',
      id,
      timestamp: new Date().toISOString(),
      content,
      context,
    };

    if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(frame));
    } else {
      this.messageQueue.push(frame);
    }

    return id;
  }

  getConnectionState(): WsConnectionState {
    return this.connectionState;
  }

  // --- Internal ---

  private doConnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.setConnectionState(this.retryCount > 0 ? 'reconnecting' : 'connecting');

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.retryCount = 0;
      this.setConnectionState('connected');
      this.flushQueue();
    };

    this.ws.onmessage = (event) => {
      this.handleFrame(event.data as string);
    };

    this.ws.onclose = (event) => {
      this.ws = null;
      if (event.code !== 1000) {
        this.scheduleReconnect();
      } else {
        this.setConnectionState('disconnected');
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror, so reconnect is handled there
    };
  }

  private handleFrame(raw: string): void {
    let frame: WsAnyFrame;
    try {
      frame = JSON.parse(raw) as WsAnyFrame;
    } catch {
      return;
    }

    switch (frame.type) {
      case 'result':
        // Stream chunks if content is present, then deliver full result
        if (this.onStreamChunk && frame.content) {
          this.onStreamChunk(frame.id, frame.content);
        }
        this.onMessage?.(frame);
        break;
      case 'progress':
        this.onProgress?.(frame);
        break;
      case 'error':
        this.onError?.(frame);
        break;
      default:
        break;
    }
  }

  private flushQueue(): void {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const frame = this.messageQueue.shift()!;
      this.ws.send(JSON.stringify(frame));
    }
  }

  private scheduleReconnect(): void {
    if (this.retryCount >= this.maxRetries) {
      this.setConnectionState('disconnected');
      return;
    }

    this.setConnectionState('reconnecting');
    const delay = this.baseRetryMs * Math.pow(2, this.retryCount);
    this.retryCount++;

    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      this.doConnect();
    }, delay);
  }

  private setConnectionState(state: WsConnectionState): void {
    if (this.connectionState === state) return;
    this.connectionState = state;
    this.onConnectionChange?.(state);
  }
}
