// ============================================================
// ChatMessage Component
// Displays individual messages in the AI chat interface
// ============================================================

import type { ChatMessage } from '../../types';
import type { DiagnosisData, OptimizationData, InspectionData, HmiLayout } from '../../types';
import { DiagnosticCard } from '../DiagnosticCard';
import { OptimizationPanel } from '../OptimizationPanel';
import { InspectionPanel } from '../InspectionPanel';
import { HmiPreview } from '../HmiPreview';
import { AlertCircle, User, Bot } from 'lucide-react';
import { cn } from '../../utils/cn';

interface ChatMessageProps {
  message: ChatMessage;
  onCreateTicket?: (diagnosis: DiagnosisData) => void;
  onApplyOptimization?: (optimization: OptimizationData) => void;
  onConfirmHmi?: (layout: HmiLayout) => void;
}

// Pre-define formatted message content to avoid type inference issues
function formatMessageContent(content: string): string {
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br />');
}

export function ChatMessage({
  message,
  onCreateTicket,
  onApplyOptimization,
  onConfirmHmi,
}: ChatMessageProps) {
  const isUser = message.type === 'user';
  const isError = message.type === 'error';
  const isSystem = message.type === 'system';

  if (isSystem) {
    return (
      <div className="chat-message chat-message-system">
        <div className="system-message">{message.content}</div>
      </div>
    );
  }

  // Helper functions defined inside to avoid type inference issues
  const renderMessageText = () => {
    if (isUser) {
      return <div className="message-text user-text">{message.content}</div>;
    }
    if (message.content) {
      return (
        <div className="message-text">
          <span
            dangerouslySetInnerHTML={{
              __html: formatMessageContent(message.content),
            }}
          />
        </div>
      );
    }
    return null;
  };

  const renderResultData = () => {
    if (!message.result?.data) return null;

    const data = message.result.data;

    // Type guard for diagnosis data
    if (isDiagnosisData(data)) {
      return <DiagnosticCard diagnosis={data} onCreateTicket={onCreateTicket} />;
    }
    // Type guard for optimization data
    if (isOptimizationData(data)) {
      return <OptimizationPanel optimization={data} onApply={onApplyOptimization} />;
    }
    // Type guard for inspection data
    if (isInspectionData(data)) {
      return <InspectionPanel inspection={data} />;
    }
    // Type guard for HMI layout data
    if (isHmiLayout(data)) {
      return <HmiPreview layout={data} onConfirm={onConfirmHmi} />;
    }
    // Generic data display
    if (typeof data === 'object' && data !== null) {
      return (
        <div className="generic-result">
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      );
    }
    return null;
  };

  return (
    <div
      className={cn(
        'chat-message',
        isUser ? 'chat-message-user' : 'chat-message-assistant',
        isError && 'chat-message-error'
      )}
    >
      <div className="message-avatar">
        {isUser ? <User size={18} /> : <Bot size={18} />}
      </div>
      <div className="message-content">
        {!isUser && message.result?.ok === false ? (
          <div className="error-banner">
            <AlertCircle size={16} />
            <span>Operation failed</span>
          </div>
        ) : null}

        {/* Message text */}
        {renderMessageText()}

        {/* Structured result rendering */}
        {renderResultData()}

        {/* Timestamp */}
        <div className="message-timestamp">
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

// Type guards
function isDiagnosisData(data: unknown): data is DiagnosisData {
  return (
    typeof data === 'object' &&
    data !== null &&
    'root_cause' in data &&
    'confidence' in data &&
    'severity' in data
  );
}

function isOptimizationData(data: unknown): data is OptimizationData {
  return (
    typeof data === 'object' &&
    data !== null &&
    'equip_id' in data &&
    'setpoints' in data &&
    'predicted_savings' in data
  );
}

function isInspectionData(data: unknown): data is InspectionData {
  return (
    typeof data === 'object' &&
    data !== null &&
    'total_sensors' in data &&
    'sensors' in data
  );
}

function isHmiLayout(data: unknown): data is HmiLayout {
  return (
    typeof data === 'object' &&
    data !== null &&
    'pages' in data &&
    Array.isArray((data as HmiLayout).pages)
  );
}

function formatTimestamp(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}
