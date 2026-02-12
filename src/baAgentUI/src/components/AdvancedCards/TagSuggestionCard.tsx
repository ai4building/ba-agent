// ============================================================
// Tag Suggestion Card Component
// EPC (Engineering) auto-tagging suggestions
// ============================================================

import { Tag, CheckCircle2, Sparkles, ArrowRight } from 'lucide-react';
import { cn } from '../../utils/cn';
import { useState } from 'react';

export interface TagSuggestion {
  tag: string;
  confidence: number;
  current_value?: string;
  suggested_value: string;
  reason: string;
}

export interface TagSuggestionData {
  equip_id: string;
  equip_name: string;
  discovered_points: number;
  tags: TagSuggestion[];
  coverage_percent: number;
}

interface TagSuggestionCardProps {
  data: TagSuggestionData;
  onApplyTags?: (tags: string[]) => void;
  onApplySingle?: (tag: string, value: string) => void;
  className?: string;
}

export function TagSuggestionCard({ data, onApplyTags, onApplySingle, className }: TagSuggestionCardProps) {
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [appliedTags, setAppliedTags] = useState<Set<string>>(new Set());

  const toggleTag = (tag: string) => {
    const newSelected = new Set(selectedTags);
    if (newSelected.has(tag)) {
      newSelected.delete(tag);
    } else {
      newSelected.add(tag);
    }
    setSelectedTags(newSelected);
  };

  const handleApplyAll = () => {
    if (onApplyTags && selectedTags.size > 0) {
      onApplyTags(Array.from(selectedTags));
      setAppliedTags(new Set([...appliedTags, ...selectedTags]));
      setSelectedTags(new Set());
    }
  };

  const handleApplySingle = (tag: string, value: string) => {
    if (onApplySingle) {
      onApplySingle(tag, value);
      setAppliedTags(new Set([...appliedTags, tag]));
      setSelectedTags(prev => {
        const newSet = new Set(prev);
        newSet.delete(tag);
        return newSet;
      });
    }
  };

  return (
    <div className={cn('rounded-xl border border-slate-200 bg-white overflow-hidden', className)}>
      {/* Header */}
      <div className="px-4 py-3 bg-gradient-to-r from-emerald-50 to-teal-50 border-b border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            <span className="font-semibold text-slate-900">AI 标签推荐</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">
              覆盖率 {data.coverage_percent}%
            </span>
            <span className="text-xs text-slate-400">·</span>
            <span className="text-xs text-slate-500">
              {data.discovered_points} 点位
            </span>
          </div>
        </div>
        <div className="mt-2 text-sm text-slate-600">
          {data.equip_name} · <span className="font-mono text-xs">{data.equip_id}</span>
        </div>
      </div>

      {/* Tag List */}
      <div className="p-4 space-y-2">
        {data.tags.map((item, index) => {
          const isSelected = selectedTags.has(item.tag);
          const isApplied = appliedTags.has(item.tag);

          return (
            <div
              key={index}
              className={cn(
                'p-3 rounded-lg border transition-all',
                isApplied
                  ? 'bg-emerald-50 border-emerald-200'
                  : isSelected
                    ? 'bg-blue-50 border-blue-300 shadow-sm'
                    : 'bg-slate-50 border-slate-200 hover:border-slate-300'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 flex-1">
                  {/* Checkbox */}
                  <button
                    onClick={() => !isApplied && toggleTag(item.tag)}
                    disabled={isApplied}
                    className={cn(
                      'mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors',
                      isApplied
                        ? 'bg-emerald-500 border-emerald-500'
                        : isSelected
                          ? 'bg-blue-500 border-blue-500'
                          : 'border-slate-300 hover:border-blue-400'
                    )}
                  >
                    {(isSelected || isApplied) && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                    )}
                  </button>

                  {/* Tag Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-medium text-slate-800">
                        {item.tag}
                      </span>
                      <span className={cn(
                        'px-1.5 py-0.5 rounded text-xs font-medium',
                        item.confidence >= 90 ? 'bg-emerald-100 text-emerald-700' :
                        item.confidence >= 70 ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-600'
                      )}>
                        {item.confidence}%
                      </span>
                    </div>

                    {item.current_value && item.current_value !== item.suggested_value && (
                      <div className="flex items-center gap-2 text-xs mb-1">
                        <span className="text-slate-400">当前:</span>
                        <span className="text-slate-500 line-through">{item.current_value}</span>
                        <ArrowRight className="w-3 h-3 text-slate-400" />
                        <span className="text-emerald-600">{item.suggested_value}</span>
                      </div>
                    )}

                    <div className="text-xs text-slate-500 flex items-center gap-1">
                      <span>📝</span>
                      {item.reason}
                    </div>
                  </div>
                </div>

                {/* Apply Single Button */}
                {!isApplied && onApplySingle && (
                  <button
                    onClick={() => handleApplySingle(item.tag, item.suggested_value)}
                    className="px-3 py-1.5 bg-white hover:bg-emerald-50 text-emerald-600 border border-emerald-200 text-xs font-medium rounded-lg transition-colors flex-shrink-0"
                  >
                    {isApplied ? '已应用' : '应用'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
        <div className="text-sm text-slate-500">
          已选择 <span className="font-semibold text-slate-700">{selectedTags.size}</span> 个标签
        </div>

        <div className="flex items-center gap-2">
          {onApplyTags && (
            <button
              onClick={handleApplyAll}
              disabled={selectedTags.size === 0}
              className={cn(
                'px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-1.5',
                selectedTags.size > 0
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white shadow-lg shadow-emerald-500/30'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              )}
            >
              <Tag className="w-4 h-4" />
              批量应用到 Folio
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
