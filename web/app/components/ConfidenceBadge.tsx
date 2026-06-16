"use client";

import type { Confidence } from "@/lib/types";

interface ConfidenceBadgeProps {
  confidence: Confidence | null;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (!confidence) return null;

  const thinSample = confidence.thin_sample || (confidence.effective_runs || 0) < 100;
  const lowCoverage = (confidence.rating_coverage || 1) < 0.9;
  const level = thinSample ? "low" : lowCoverage ? "medium" : "high";

  const colors = {
    high: "bg-green-900/30 border-green-700/50 text-green-300",
    medium: "bg-yellow-900/30 border-yellow-700/50 text-yellow-300",
    low: "bg-red-900/30 border-red-700/50 text-red-300",
  };

  const labels = {
    high: "High Confidence",
    medium: "Medium Confidence",
    low: "Low Confidence — Interpret with Caution",
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${colors[level]}`}>
      <span className={`w-2 h-2 rounded-full ${
        level === "high" ? "bg-green-400" : level === "medium" ? "bg-yellow-400" : "bg-red-400"
      }`} />
      {labels[level]}
      {confidence.effective_runs != null && (
        <span className="opacity-70">({confidence.effective_runs} runs)</span>
      )}
    </div>
  );
}
