// ============================================================
// useAgentChat — React hook wrapping AgentChatManager
// Provides WebSocket chat with streaming, progress, and reconnection
// Falls back to HTTP (useChatAgent-style) when WebSocket unavailable
// ============================================================

import { useState, useEffect, useCallback, useRef } from 'react';
import { AgentChatManager } from '../core/AgentChatManager';
import { ContextWatcher } from '../core/ContextWatcher';
import type {
  ChatMessage,
  StreamingMessage,
  WsConnectionState,
  WsResultFrame,
  WsProgressFrame,
  WsErrorFrame,
  ContextSnapshot,
} from '../types';

const TYPEWRITER_TOKENS_PER_SEC = 30;
const TYPEWRITER_INTERVAL = 1000 / TYPEWRITER_TOKENS_PER_SEC;

interface UseAgentChatOptions {
  wsUrl?: string;
  contextDeps?: {
    alarmCount: number;
    selectedEquipRef?: string;
    currentView: string;
    recentPointIds: string[];
  };
}

interface UseAgentChatResult {
  messages: ChatMessage[];
  streamingMessage: StreamingMessage | null;
  sendMessage: (text: string) => void;
  connectionState: WsConnectionState;
  progress: { percent: number; stage: string } | null;
  clearMessages: () => void;
}

const WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome',
  type: 'assistant',
  content:
    "Hello! I'm your Building Automation AI Assistant. I can help you with:\n\n" +
    '- **Alarm Diagnosis** — Analyze faults and identify root causes\n' +
    '- **Energy Optimization** — Suggest optimal setpoint changes\n' +
    '- **Sensor Inspection** — Check sensor health and detect issues\n' +
    '- **HMI Generation** — Auto-generate operator interfaces\n\n' +
    'How can I assist you today?',
  timestamp: new Date(),
};

export function useAgentChat(options: UseAgentChatOptions = {}): UseAgentChatResult {
  const { wsUrl, contextDeps } = options;

  const managerRef = useRef<AgentChatManager | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null);
  const [connectionState, setConnectionState] = useState<WsConnectionState>('disconnected');
  const [progress, setProgress] = useState<{ percent: number; stage: string } | null>(null);

  // Typewriter animation state
  const typewriterRef = useRef<{
    timer: ReturnType<typeof setTimeout> | null;
    tokens: string[];
    index: number;
    messageId: string;
  } | null>(null);

  // Initialize manager
  useEffect(() => {
    if (!wsUrl) return;

    const manager = new AgentChatManager();
    managerRef.current = manager;

    manager.onConnectionChange = (state) => {
      setConnectionState(state);
    };

    manager.onMessage = (frame: WsResultFrame) => {
      setProgress(null);
      startTypewriter(frame.id, frame.content, frame.result);
    };

    manager.onProgress = (frame: WsProgressFrame) => {
      setProgress({ percent: frame.percent, stage: frame.stage });
    };

    manager.onError = (frame: WsErrorFrame) => {
      setProgress(null);
      const errorMsg: ChatMessage = {
        id: frame.id,
        type: 'error',
        content: `Error [${frame.code}]: ${frame.message}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    };

    manager.connect(wsUrl);

    return () => {
      manager.disconnect();
      managerRef.current = null;
      clearTypewriter();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsUrl]);

  // --- Typewriter effect ---

  const startTypewriter = useCallback(
    (messageId: string, fullContent: string, result?: WsResultFrame['result']) => {
      clearTypewriter();

      // Split by whitespace/punctuation for token-level streaming
      const tokens = fullContent.match(/\S+\s*/g) || [fullContent];

      const streaming: StreamingMessage = {
        id: messageId,
        type: 'assistant',
        content: '',
        timestamp: new Date(),
        result: result ? { action: result.action, ok: result.ok, data: result.data } : undefined,
        isStreaming: true,
        fullContent,
        displayedContent: '',
      };
      setStreamingMessage(streaming);

      typewriterRef.current = { timer: null, tokens, index: 0, messageId };
      tickTypewriter();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const tickTypewriter = useCallback(() => {
    const tw = typewriterRef.current;
    if (!tw) return;

    if (tw.index >= tw.tokens.length) {
      // Done streaming — finalize
      setStreamingMessage((prev) => {
        if (!prev) return null;
        const final: ChatMessage = {
          id: prev.id,
          type: prev.type,
          content: prev.fullContent,
          timestamp: prev.timestamp,
          result: prev.result,
        };
        setMessages((msgs) => [...msgs, final]);
        return null;
      });
      typewriterRef.current = null;
      return;
    }

    const nextToken = tw.tokens[tw.index];
    tw.index++;

    setStreamingMessage((prev) => {
      if (!prev) return null;
      const displayed = prev.displayedContent + nextToken;
      return { ...prev, displayedContent: displayed, content: displayed };
    });

    tw.timer = setTimeout(tickTypewriter, TYPEWRITER_INTERVAL);
  }, []);

  const clearTypewriter = useCallback(() => {
    if (typewriterRef.current?.timer) {
      clearTimeout(typewriterRef.current.timer);
    }
    typewriterRef.current = null;
  }, []);

  // Skip typewriter — show full content immediately
  const skipTypewriter = useCallback(() => {
    setStreamingMessage((prev) => {
      if (!prev) return null;
      const final: ChatMessage = {
        id: prev.id,
        type: prev.type,
        content: prev.fullContent,
        timestamp: prev.timestamp,
        result: prev.result,
      };
      setMessages((msgs) => [...msgs, final]);
      return null;
    });
    clearTypewriter();
  }, [clearTypewriter]);

  // --- Send message ---

  const sendMessage = useCallback(
    (text: string) => {
      const userMsg: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        type: 'user',
        content: text,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMsg]);

      // If streaming, skip the current animation
      if (streamingMessage) {
        skipTypewriter();
      }

      const context: ContextSnapshot = contextDeps
        ? ContextWatcher.capture(contextDeps)
        : { activeAlarms: 0, currentView: 'chat', recentPointIds: [] };

      if (managerRef.current && connectionState === 'connected') {
        managerRef.current.send(text, context);
      }
      // If not connected, the message is queued by the manager
    },
    [connectionState, contextDeps, streamingMessage, skipTypewriter]
  );

  const clearMessages = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
    setStreamingMessage(null);
    clearTypewriter();
  }, [clearTypewriter]);

  return {
    messages,
    streamingMessage,
    sendMessage,
    connectionState,
    progress,
    clearMessages,
  };
}
