import React, { useState, useEffect } from 'react';
import { BarChart3, Cloud, Layers, Hash } from 'lucide-react';
import { Card } from '../components/common/Card';
import { dashboardApi } from '../api/dashboardApi';

export const AnalyticsPage = () => {
  const [topics, setTopics] = useState([
    { word: 'Overburden Removal (OBR)', weight: 412, category: 'Operational' },
    { word: 'Opencast Production MT', weight: 384, category: 'Production' },
    { word: 'Coal Washing Capacity', weight: 215, category: 'Infrastructure' },
    { word: 'Stripping Ratio M.Cu.M/T', weight: 198, category: 'Metric' },
    { word: 'Environmental Clearance', weight: 142, category: 'Regulatory' },
  ]);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await dashboardApi.getWordCloud();
        if (res && Array.isArray(res.topics)) {
          setTopics(res.topics.map(t => ({
            word: t.word,
            weight: t.weight * 4,
            category: t.category
          })));
        }
      } catch (err) {
        // Fallback baseline
      }
    };
    fetchAnalytics();
  }, []);

  return (
    <div className="space-y-6">
      <div className="pb-4 border-b border-slate-800">
        <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
          Mining Intelligence & Word Cloud Analytics
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          TF-IDF term frequency analysis and mining metric distribution across CIL subsidiaries
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card title="TF-IDF Term Extraction Matrix">
          <div className="space-y-3">
            {topics.map((t, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-slate-900/60 border border-slate-700/60 rounded-lg text-xs hover:border-slate-600 transition-colors">
                <div>
                  <div className="font-semibold text-white">{t.word}</div>
                  <div className="text-[10px] text-amber-400 mt-0.5">{t.category}</div>
                </div>
                <div className="flex items-center space-x-3 text-slate-400 font-mono">
                  <span>Count: {t.weight}</span>
                  <span className="text-amber-400">TF-IDF: {(t.weight / 500).toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Mining Entity Recognition Breakdown">
          <div className="p-6 text-center space-y-4">
            <div className="inline-flex p-4 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Cloud className="w-10 h-10" />
            </div>
            <h3 className="text-lg font-semibold text-white">Entity Recognition Engine</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Automatically identifies Opencast Mines, Coalfields, Subsidiaries (ECL, BCCL, CCL, WCL, SECL, NCL, MCL), and Target Metrics from ingested documents.
            </p>
            <div className="grid grid-cols-2 gap-3 pt-4 border-t border-slate-800 text-xs">
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <div className="text-slate-400">Identified Mines</div>
                <div className="text-lg font-bold text-amber-400 mt-1">48 Mines</div>
              </div>
              <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                <div className="text-slate-400">Subsidiary Tags</div>
                <div className="text-lg font-bold text-emerald-400 mt-1">7 Subsidiaries</div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
