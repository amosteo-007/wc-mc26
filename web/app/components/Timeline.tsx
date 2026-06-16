"use client";

import type { TurningPoint } from "@/lib/types";

interface TimelineProps {
  turningPoints: TurningPoint[];
}

export function Timeline({ turningPoints }: TimelineProps) {
  if (!turningPoints?.length) return null;

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">
        Narrative Timeline — Turning Points
      </h3>
      <div className="space-y-3">
        {turningPoints.slice(0, 5).map((tp, i) => (
          <div key={i} className="flex items-start gap-3">
            <div
              className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                tp.direction === "up" ? "bg-green-400" : "bg-red-400"
              }`}
            />
            <div>
              <div className="text-sm font-medium">
                Round {tp.round}{" "}
                <span className={tp.direction === "up" ? "text-green-400" : "text-red-400"}>
                  {tp.direction === "up" ? "↑" : "↓"}
                </span>
              </div>
              <div className="text-xs text-gray-500">
                Sentiment shift: {tp.magnitude.toFixed(3)} to {tp.sentiment.toFixed(2)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
