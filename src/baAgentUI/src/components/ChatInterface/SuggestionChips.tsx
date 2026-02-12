// ============================================================
// Suggestion Chips Component
// Quick action suggestions for users
// ============================================================

import { cn } from '../../utils/cn';

export interface Suggestion {
  icon: string;
  label: string;
  query: string;
}

interface SuggestionChipsProps {
  suggestions: Suggestion[];
  onClick: (query: string) => void;
  className?: string;
}

export function SuggestionChips({ suggestions, onClick, className }: SuggestionChipsProps) {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          onClick={() => onClick(suggestion.query)}
          className="group inline-flex items-center gap-2 px-3 py-2 bg-white/80 backdrop-blur-sm rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md hover:shadow-blue-500/10 transition-all duration-200 hover:-translate-y-0.5"
        >
          <span className="text-lg">{suggestion.icon}</span>
          <span className="text-sm text-slate-700 group-hover:text-blue-700 transition-colors">
            {suggestion.label}
          </span>
        </button>
      ))}
    </div>
  );
}
