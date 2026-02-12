// ============================================================
// ChatInput Component
// Input area for AI chat with command suggestions
// ============================================================

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Paperclip, Mic, Sparkles } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  suggestions?: string[];
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Ask about alarms, optimization, or inspection...',
  suggestions = DEFAULT_SUGGESTIONS,
}: ChatInputProps) {
  const [input, setInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [input]);

  // Focus input on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setInput('');
      setShowSuggestions(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion);
    setShowSuggestions(false);
    textareaRef.current?.focus();
  };

  return (
    <div className="chat-input-container">
      {/* Suggestions dropdown */}
      {showSuggestions && !input && (
        <div className="chat-suggestions">
          {suggestions.map((suggestion, index) => (
            <button
              key={index}
              className="suggestion-chip"
              onClick={() => handleSuggestionClick(suggestion)}
              type="button"
            >
              <Sparkles size={14} />
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-wrapper">
        <div className="input-actions-left">
          <button
            type="button"
            className="action-btn"
            onClick={() => {}}
            title="Attach file"
            disabled={disabled}
          >
            <Paperclip size={18} />
          </button>
        </div>

        <textarea
          ref={textareaRef}
          className="chat-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => {
            // Delay to allow suggestion click to register
            setTimeout(() => setShowSuggestions(false), 200);
          }}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
        />

        <div className="input-actions-right">
          {input.length > 0 ? (
            <button
              type="button"
              className="send-btn"
              onClick={handleSubmit}
              disabled={disabled || !input.trim()}
              title="Send message"
            >
              <Send size={18} />
            </button>
          ) : (
            <button
              type="button"
              className="action-btn"
              onClick={() => {}}
              title="Voice input"
              disabled={disabled}
            >
              <Mic size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const DEFAULT_SUGGESTIONS = [
  'Diagnose active alarms',
  'Optimize AHU setpoints',
  'Run sensor inspection',
  'Generate HMI layout for AHUs',
  'Show energy consumption report',
];
