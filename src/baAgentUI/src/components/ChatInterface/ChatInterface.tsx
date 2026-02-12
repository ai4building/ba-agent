// ============================================================
// Modern Chat Interface Component
// Features: Glass morphism, typewriter animation, suggestions
// ============================================================

import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Plus,
  Trash2,
  Zap,
  Paperclip,
  MoreVertical,
  Bot,
  Loader2
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { TypingIndicator } from './TypingIndicator';
import { SuggestionChips } from './SuggestionChips';
import { ChatMessage } from './ChatMessage';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (content: string) => void | Promise<void>;
  isLoading?: boolean;
  onClearChat?: () => void;
  className?: string;
}

// Suggestion prompts for quick actions
const DEFAULT_SUGGESTIONS = [
  { icon: '🔍', label: '查询所有设备', query: 'equip' },
  { icon: '🌡️', label: '查看温度传感器', query: 'point and temp' },
  { icon: '❄️', label: '查看所有 AHU', query: 'equip and ahu' },
  { icon: '🚨', label: '当前报警', query: 'alarm and curVal' },
  { icon: 'ℹ️', label: '服务器信息', query: 'about' },
  { icon: '🔧', label: '可用操作', query: 'ops' },
];

export function ChatInterface({
  messages,
  onSendMessage,
  isLoading = false,
  onClearChat,
  className
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [inputHeight, setInputHeight] = useState(48);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = '48px';
      const scrollHeight = inputRef.current.scrollHeight;
      const newHeight = Math.min(Math.max(scrollHeight, 48), 200);
      setInputHeight(newHeight);
    }
  }, [inputValue]);

  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading) return;

    setInputValue('');
    setShowSuggestions(false);
    if (inputRef.current) {
      inputRef.current.style.height = '48px';
    }

    await onSendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSuggestionClick = (query: string) => {
    setInputValue(query);
    inputRef.current?.focus();
  };

  const showDefaultSuggestions = showSuggestions && messages.length <= 1;

  return (
    <div className={cn('flex flex-col h-full bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50', className)}>
      {/* Header with glass effect */}
      <header className="flex-shrink-0 px-6 py-4 backdrop-blur-xl bg-white/70 border-b border-slate-200/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-900">BA Agent</h1>
              <p className="text-xs text-slate-500 flex items-center gap-1">
                <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                在线 - Haystack 3.0
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setInputValue('');
                setShowSuggestions(true);
                inputRef.current?.focus();
              }}
              className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700"
              title="新对话"
            >
              <Plus className="w-5 h-5" />
            </button>
            {onClearChat && (
              <button
                onClick={onClearChat}
                className="p-2 rounded-lg hover:bg-red-50 transition-colors text-slate-500 hover:text-red-600"
                title="清空对话"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            )}
            <button className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-500 hover:text-slate-700">
              <MoreVertical className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onCopy={() => handleCopy(message.content, message.id)}
              isCopied={copiedId === message.id}
            />
          ))}

          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1">
                <TypingIndicator />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggestions Area */}
      {showDefaultSuggestions && !isLoading && (
        <div className="flex-shrink-0 px-4 py-3">
          <div className="max-w-4xl mx-auto">
            <SuggestionChips
              suggestions={DEFAULT_SUGGESTIONS}
              onClick={handleSuggestionClick}
            />
          </div>
        </div>
      )}

      {/* Input Area with glass effect */}
      <div className="flex-shrink-0 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative backdrop-blur-xl bg-white/80 rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200/50 overflow-hidden">
            {/* Textarea */}
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入查询或问题... (Enter 发送, Shift+Enter 换行)"
              className="w-full px-5 py-4 pr-28 bg-transparent text-slate-800 placeholder:text-slate-400 resize-none focus:outline-none"
              style={{ height: `${inputHeight}px`, maxHeight: '200px' }}
              rows={1}
            />

            {/* Action Buttons */}
            <div className="absolute right-3 bottom-3 flex items-center gap-2">
              {/* Attachment button */}
              <button
                className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-600"
                title="上传附件"
              >
                <Paperclip className="w-5 h-5" />
              </button>

              {/* Zap/Plugin button */}
              <button
                className="p-2 rounded-lg hover:bg-slate-100 transition-colors text-slate-400 hover:text-slate-600"
                title="插件"
              >
                <Zap className="w-4 h-4" />
              </button>

              {/* Divider */}
              <div className="w-px h-6 bg-slate-200" />

              {/* Send button */}
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                className={cn(
                  'p-2.5 rounded-xl transition-all duration-200 flex items-center justify-center',
                  inputValue.trim() && !isLoading
                    ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 hover:scale-105'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                )}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>

            {/* Character count hint */}
            {inputValue.length > 0 && (
              <div className="absolute left-5 bottom-2">
                <span className="text-xs text-slate-400">
                  {inputValue.length} 字符
                </span>
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="mt-3 text-center">
            <p className="text-xs text-slate-400">
              BA Agent 使用 Haystack 3.0 协议查询建筑自动化数据
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
