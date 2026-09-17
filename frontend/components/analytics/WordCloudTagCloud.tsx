'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Cloud } from 'lucide-react';
import { WordCloudTopicItem } from '@/lib/api/analyticsApi';

interface WordCloudTagCloudProps {
  topics: WordCloudTopicItem[];
}

const CATEGORY_COLORS: Record<string, string> = {
  Operational: 'text-[#C58B3A] bg-[#C58B3A]/15 border-[#C58B3A]/30',
  Production: 'text-[#4F8A62] bg-[#4F8A62]/15 border-[#4F8A62]/30',
  Infrastructure: 'text-[#54788A] bg-[#54788A]/15 border-[#54788A]/30',
  Metric: 'text-[#C58B3A] bg-[#C58B3A]/10 border-[#C58B3A]/30',
  Regulatory: 'text-[#C94B45] bg-[#C94B45]/15 border-[#C94B45]/30',
  Equipment: 'text-[#9BA5A8] bg-[#242C30] border-[#30383D]',
  Logistics: 'text-[#54788A] bg-[#54788A]/20 border-[#54788A]/30',
};

export const WordCloudTagCloud: React.FC<WordCloudTagCloudProps> = ({ topics }) => {
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  const categories = ['ALL', ...Array.from(new Set(topics.map((t) => t.category)))];

  const filteredTopics = topics.filter(
    (t) => selectedCategory === 'ALL' || t.category === selectedCategory
  );

  const maxWeight = Math.max(...topics.map((t) => t.weight), 1);
  const minWeight = Math.min(...topics.map((t) => t.weight), 1);

  const getFontSize = (weight: number) => {
    if (maxWeight === minWeight) return '16px';
    const minSize = 13;
    const maxSize = 28;
    const size = minSize + ((weight - minWeight) / (maxWeight - minWeight)) * (maxSize - minSize);
    return `${Math.round(size)}px`;
  };

  return (
    <Card className="border-[#30383D] shadow-sm bg-[#1C2226]">
      <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Cloud className="h-4 w-4 text-[#C58B3A]" />
            <CardTitle className="text-sm font-bold text-[#E8ECEB]">TF-IDF Mining Word Cloud Visualization</CardTitle>
          </div>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 text-xs font-mono rounded-lg transition-colors whitespace-nowrap select-none ${
                  selectedCategory === cat
                    ? 'bg-[#C58B3A]/15 text-[#C58B3A] border border-[#C58B3A]/50 font-bold'
                    : 'text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30]'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-8">
        <div className="flex flex-wrap items-center justify-center gap-4 min-h-[220px]">
          {filteredTopics.map((item, idx) => {
            const colorClass = CATEGORY_COLORS[item.category] || 'text-[#C58B3A] bg-[#C58B3A]/15 border-[#C58B3A]/30';
            const fontSize = getFontSize(item.weight);

            return (
              <div
                key={idx}
                style={{ fontSize }}
                className={`px-3.5 py-1.5 rounded-lg border transition-colors cursor-pointer font-sans font-semibold shadow-sm ${colorClass}`}
                title={`Topic: ${item.word} | Category: ${item.category} | Weight: ${item.weight}`}
              >
                <span>{item.word}</span>
                <span className="ml-2 text-[10px] opacity-75 font-mono">({item.weight})</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
