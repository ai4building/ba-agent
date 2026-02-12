// ============================================================
// Chat Message Component
// Individual message bubble with copy functionality
// ============================================================

import { useState } from 'react';
import { User, Bot, Check, Copy } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: Message;
  onCopy: () => void;
  isCopied: boolean;
}

export function ChatMessage({ message, onCopy, isCopied }: ChatMessageProps) {
  const [isHovered, setIsHovered] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300',
        isUser && 'flex-row-reverse'
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
          isUser
            ? 'bg-gradient-to-br from-blue-500 to-indigo-500'
            : 'bg-gradient-to-br from-slate-700 to-slate-900'
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Message Bubble */}
      <div className={cn('flex-1 max-w-[80%]', isUser && 'flex flex-col items-end')}>
        <div
          className={cn(
            'relative group rounded-2xl px-4 py-3 shadow-sm',
            isUser
              ? 'bg-gradient-to-br from-blue-500 to-indigo-500 text-white rounded-tr-sm'
              : 'bg-white text-slate-800 border border-slate-200 rounded-tl-sm'
          )}
        >
          {/* Message Content */}
          <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
          </div>

          {/* Copy Button - appears on hover */}
          {(isHovered || isCopied) && (
            <button
              onClick={onCopy}
              className={cn(
                'absolute -top-2 transition-all duration-200 flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium shadow-md',
                isUser
                  ? '-right-2 bg-white text-blue-600 hover:bg-blue-50'
                  : '-right-2 bg-slate-800 text-white hover:bg-slate-700'
              )}
            >
              {isCopied ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  复制
                </>
              )}
            </button>
          )}
        </div>

        {/* Timestamp */}
        <div className={cn('mt-1 px-1', isUser ? 'text-right' : 'text-left')}>
          <span className="text-xs text-slate-400">
            {message.timestamp.toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
