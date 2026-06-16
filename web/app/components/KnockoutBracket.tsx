"use client";

import type { BracketTie } from "@/lib/types";

interface KnockoutBracketProps {
  r32?: BracketTie[];
  groupStageComplete: boolean;
}

/** Knockout bracket. R32 ties show their slot labels (1A, 2C, 3C/D/E…); the
 *  actual teams are TBD until the group stage finishes. Later rounds are shown
 *  as TBD placeholders. */
export function KnockoutBracket({ r32, groupStageComplete }: KnockoutBracketProps) {
  const ties = r32 ?? [];

  const laterRounds = [
    { label: "Round of 16", count: 8 },
    { label: "Quarter-finals", count: 4 },
    { label: "Semi-finals", count: 2 },
    { label: "Final", count: 1 },
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      {!groupStageComplete && (
        <p className="text-xs text-amber-400/90 mb-3">
          Group stage in progress — knockout matchups are determined once all
          groups finish. Slots below show the bracket structure (winners,
          runners-up, and best third-placed teams).
        </p>
      )}

      <div className="overflow-x-auto">
        <div className="flex gap-4 min-w-max">
          {/* Round of 32 — show the authored slot pairings */}
          <div className="shrink-0">
            <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-2">
              Round of 32
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
              {ties.map((t) => (
                <div
                  key={t.match}
                  className="text-[11px] bg-gray-800/60 rounded px-2 py-1 w-36"
                >
                  <div className="flex justify-between text-gray-300">
                    <span className="font-mono text-gray-400">{t.home}</span>
                    <span className="text-gray-600">vs</span>
                    <span className="font-mono text-gray-400">{t.away}</span>
                  </div>
                  <div className="text-[10px] text-gray-600 text-center mt-0.5">
                    TBD
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Later rounds — TBD placeholders */}
          {laterRounds.map((r) => (
            <div key={r.label} className="shrink-0">
              <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-2">
                {r.label}
              </div>
              <div className="flex flex-col gap-1.5">
                {Array.from({ length: r.count }).map((_, i) => (
                  <div
                    key={i}
                    className="text-[10px] text-gray-600 bg-gray-800/40 rounded px-2 py-1 w-24 text-center"
                  >
                    TBD
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
