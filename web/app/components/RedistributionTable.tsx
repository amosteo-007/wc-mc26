"use client";

import type { ChampionEntry } from "@/lib/types";

interface RedistributionTableProps {
  championProbs: Record<string, number>;
  baseProbs?: Record<string, number>;
}

export function RedistributionTable({ championProbs, baseProbs }: RedistributionTableProps) {
  const entries: ChampionEntry[] = Object.entries(championProbs)
    .map(([team, probability]) => ({
      team,
      probability,
      change: baseProbs ? probability - (baseProbs[team] || 0) : undefined,
    }))
    .sort((a, b) => b.probability - a.probability)
    .slice(0, 10);

  const maxProb = entries[0]?.probability || 0;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">
        Champion Probability Redistribution
      </h3>
      <div className="space-y-2">
        {entries.map((entry) => (
          <div key={entry.team} className="flex items-center gap-3">
            <span className="w-10 text-xs font-mono text-gray-400">{entry.team}</span>
            <div className="flex-1 bg-gray-800 rounded-full h-5 overflow-hidden">
              <div
                className="h-full bg-blue-600 rounded-full transition-all"
                style={{ width: `${(entry.probability / maxProb) * 100}%` }}
              />
            </div>
            <span className="w-16 text-right text-sm font-mono">
              {(entry.probability * 100).toFixed(1)}%
            </span>
            {entry.change !== undefined && (
              <span
                className={`w-16 text-right text-xs ${
                  entry.change > 0 ? "text-green-400" : entry.change < 0 ? "text-red-400" : "text-gray-500"
                }`}
              >
                {entry.change > 0 ? "+" : ""}
                {(entry.change * 100).toFixed(1)}%
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
