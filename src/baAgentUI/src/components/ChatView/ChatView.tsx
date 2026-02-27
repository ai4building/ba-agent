// ============================================================
// ChatView Component
// Main AI chat interface with message history
// ============================================================

import { useState, useRef, useEffect } from 'react';
import { Scroll } from 'lucide-react';
import { ChatMessage } from '../ChatMessage';
import { ChatInput } from '../ChatInput';
import { useChatAgent } from '../../hooks/useChatAgent';
import { useAgentChat } from '../../hooks/useAgentChat';
import type { ChatMessage as ChatMessageType, DiagnosisData, OptimizationData, HmiLayout, StreamingMessage, WsConnectionState } from '../../types';
import './ChatView.css';

interface ChatViewProps {
  /** When provided, use WebSocket mode via useAgentChat */
  wsUrl?: string;
}

export function ChatView({ wsUrl }: ChatViewProps = {}) {
  // HTTP fallback
  const httpChat = useChatAgent();
  // WebSocket mode
  const wsChat = useAgentChat({ wsUrl });

  // Select active mode
  const useWs = !!wsUrl;
  const messages: ChatMessageType[] = useWs ? wsChat.messages : httpChat.messages;
  const sendMessage = useWs ? wsChat.sendMessage : httpChat.sendMessage;
  const isLoading = useWs ? false : httpChat.isLoading;
  const streamingMessage: StreamingMessage | null = useWs ? wsChat.streamingMessage : null;
  const wsConnectionState: WsConnectionState = wsChat.connectionState;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Show scroll button when not at bottom
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
      setShowScrollButton(!isAtBottom);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  const handleCreateTicket = (diagnosis: DiagnosisData) => {
    // TODO: Implement ticket creation
    console.log('Creating ticket for diagnosis:', diagnosis);
  };

  const handleApplyOptimization = (optimization: OptimizationData) => {
    // TODO: Implement optimization application
    console.log('Applying optimization:', optimization);
  };

  const handleConfirmHmi = (layout: HmiLayout) => {
    // TODO: Implement HMI confirmation
    console.log('Confirming HMI layout:', layout);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="chat-view">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-title">
          <h1>BA Agent</h1>
          <span className="status-badge">
            {useWs ? wsConnectionState : 'Online'}
          </span>
        </div>
        <div className="chat-actions">
          <button className="icon-btn" title="Clear history">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="chat-messages" ref={containerRef}>
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <h2>How can I help you today?</h2>
            <p>Ask me about alarm diagnosis, energy optimization, or HMI generation.</p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onCreateTicket={handleCreateTicket}
                onApplyOptimization={handleApplyOptimization}
                onConfirmHmi={handleConfirmHmi}
              />
            ))}
            {/* Streaming message (typewriter effect) */}
            {streamingMessage && (
              <ChatMessage
                key={streamingMessage.id}
                message={streamingMessage}
                onCreateTicket={handleCreateTicket}
                onApplyOptimization={handleApplyOptimization}
                onConfirmHmi={handleConfirmHmi}
              />
            )}
            {isLoading && (
              <div className="chat-message chat-message-assistant">
                <div className="message-avatar">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" />
                    <path d="M12 16a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2Z" />
                    <path d="M4.93 4.93a2 2 0 0 1 2.83 0l1.41 1.41a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0L4.93 7.76a2 2 0 0 1 0-2.83Z" />
                    <path d="M14.83 14.83a2 2 0 0 1 0 2.83l1.41 1.41a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-1.41-1.41a2 2 0 0 1 0-2.83Z" />
                    <path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2 2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" />
                    <path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2Z" />
                  </svg>
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}

        {/* Scroll to bottom button */}
        {showScrollButton && (
          <button
            className="scroll-bottom-btn"
            onClick={scrollToBottom}
            title="Scroll to bottom"
          >
            <Scroll size={16} />
          </button>
        )}
      </div>

      {/* Input area */}
      <ChatInput
        onSend={sendMessage}
        disabled={isLoading}
        placeholder="Ask about alarms, optimization, or inspection..."
      />
    </div>
  );
}
