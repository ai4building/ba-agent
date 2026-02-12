// ============================================================
// Typing Indicator Component
// Animated dots to show AI is "thinking"
// ============================================================

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3 bg-white rounded-2xl rounded-tl-sm border border-slate-200 shadow-sm w-fit">
      <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
      <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
      <span className="typing-dot w-2 h-2 bg-slate-400 rounded-full animate-bounce" />

      <style>{`
        .typing-dot {
          animation: bounce 1.4s infinite ease-in-out both;
        }
        @keyframes bounce {
          0%, 80%, 100% {
            transform: scale(0.8);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}
