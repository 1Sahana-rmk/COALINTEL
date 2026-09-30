'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Sparkles, Send } from 'lucide-react';
import { CIL_SUBSIDIARIES } from '@/lib/constants';

interface QueryInputProps {
  prompt: string;
  onPromptChange: (val: string) => void;
  onSubmit: (customPrompt?: string) => void;
  selectedSubsidiary: string;
  onSubsidiaryChange: (val: string) => void;
  isLoading?: boolean;
}

const SAMPLE_QUERIES = [
  'What is the total coal production of ECL in FY 2023-24?',
  'List all mines with overburden removal exceeding 100 M.Cu.M',
  'Which subsidiary achieved the highest actual vs target ratio?',
  'Compare SECL and MCL coal extraction numbers',
];

export const QueryInput: React.FC<QueryInputProps> = ({
  prompt,
  onPromptChange,
  onSubmit,
  selectedSubsidiary,
  onSubsidiaryChange,
  isLoading = false,
}) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <Card className="border-[#30383D] shadow-sm bg-[#1C2226]">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Top Controls: Input Bar & Subsidiary Filter */}
        <div className="flex flex-col lg:flex-row items-stretch gap-3">
          <div className="flex-1">
            <Input
              placeholder="Ask any natural-language geological, production, OBR, or parliamentary query..."
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              leftIcon={<Sparkles className="h-4 w-4 text-[#C58B3A]" />}
              className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-sm py-2.5"
            />
          </div>

          <div className="flex items-center gap-3">
            <Select
              value={selectedSubsidiary}
              onChange={(e) => onSubsidiaryChange(e.target.value)}
              options={CIL_SUBSIDIARIES}
              className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs py-2.5 w-48"
              aria-label="Filter Query Subsidiary Scope"
            />

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={!prompt.trim() || isLoading}
              isLoading={isLoading}
              leftIcon={<Send className="h-4 w-4" />}
            >
              Ask Assistant
            </Button>
          </div>
        </div>

        {/* Sample Query Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[#30383D]">
          <span className="text-[10px] font-mono text-[#9BA5A8] uppercase tracking-widest font-semibold shrink-0">
            Sample Inquiries:
          </span>
          {SAMPLE_QUERIES.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                onPromptChange(sq);
                onSubmit(sq);
              }}
              className="px-2.5 py-1 rounded-md bg-[#242C30] border border-[#30383D] hover:border-[#C58B3A]/60 hover:text-[#C58B3A] text-[#E8ECEB] text-xs font-mono transition-all duration-150 text-left truncate max-w-xs"
            >
              {sq}
            </button>
          ))}
        </div>
      </form>
    </Card>
  );
};
