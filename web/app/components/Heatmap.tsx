"use client";

interface HeatmapProps {
  sentiment: {
    overall: number[];
    timestamps: string[];
  };
}

export function Heatmap({ sentiment }: HeatmapProps) {
  if (!sentiment.overall?.length) return null;

  const values = sentiment.overall;
  const max = Math.max(...values.map(Math.abs));

  return (
    <div className="card">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">
        Sentiment by Time
      </h3>
      <div className="flex items-end gap-1 h-24">
        {values.map((v, i) => {
          const height = max > 0 ? Math.abs(v) / max * 100 : 0;
          const isPositive = v >= 0;
          return (
            <div
              key={i}
              className="flex-1 flex flex-col justify-end"
              title={`${sentiment.timestamps[i] || `T+${i}`}: ${v.toFixed(2)}`}
            >
              <div
                className={`w-full rounded-t-sm transition-all ${
                  isPositive ? "bg-green-500/60" : "bg-red-500/60"
                }`}
                style={{ height: `${Math.max(height, 2)}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-2 text-xs text-gray-600">
        <span>{sentiment.timestamps[0]}</span>
        <span>{sentiment.timestamps[sentiment.timestamps.length - 1]}</span>
      </div>
    </div>
  );
}
