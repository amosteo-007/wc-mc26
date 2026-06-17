"use client";

import type { ResolvedBracket, ResolvedTie } from "@/lib/types";

interface KnockoutBracketProps {
  /** Resolved bracket from /tournament — teams fill in as results land. */
  bracket?: ResolvedBracket;
  groupStageComplete: boolean;
}

const ROUNDS: { key: keyof ResolvedBracket; label: string }[] = [
  { key: "R32", label: "Round of 32" },
  { key: "R16", label: "Round of 16" },
  { key: "QF", label: "Quarter-finals" },
  { key: "SF", label: "Semi-finals" },
  { key: "3rd_place", label: "3rd place" },
  { key: "Final", label: "Final" },
];

/** One side of a tie: resolved code (bold if it won) or the placeholder label. */
function Side({
  code,
  label,
  goals,
  isWinner,
}: {
  code: string | null;
  label: string;
  goals: number | null;
  isWinner: boolean;
}) {
  return (
    <div className="flex justify-between items-center gap-2">
      <span
        className={
          code
            ? isWinner
              ? "font-mono text-accent font-semibold"
              : "font-mono text-gray-300"
            : "font-mono text-gray-600 italic"
        }
      >
        {code ?? label}
      </span>
      {goals !== null && (
        <span className="font-mono text-gray-400 tabular-nums">{goals}</span>
      )}
    </div>
  );
}

function Tie({ tie }: { tie: ResolvedTie }) {
  return (
    <div className="text-[11px] bg-gray-800/60 rounded px-2 py-1 w-36 space-y-0.5">
      <Side
        code={tie.home_code}
        label={tie.home}
        goals={tie.home_goals}
        isWinner={tie.winner != null && tie.winner === tie.home_code}
      />
      <Side
        code={tie.away_code}
        label={tie.away}
        goals={tie.away_goals}
        isWinner={tie.winner != null && tie.winner === tie.away_code}
      />
      {!tie.played && (
        <div className="text-[10px] text-gray-600 text-center pt-0.5">TBD</div>
      )}
    </div>
  );
}

/** Knockout bracket rendered from live results. Each round shows resolved teams
 *  + scores once played; unplayed ties show their placeholder slot labels (1A,
 *  W32-1, …) and a TBD marker. The champion is highlighted when the Final ends. */
export function KnockoutBracket({ bracket, groupStageComplete }: KnockoutBracketProps) {
  const b = bracket ?? {};

  // Normalize single-match rounds (3rd_place, Final) into arrays for rendering.
  const roundTies = (key: keyof ResolvedBracket): ResolvedTie[] => {
    const v = b[key];
    if (!v) return [];
    return Array.isArray(v) ? (v as ResolvedTie[]) : [v as ResolvedTie];
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      {!groupStageComplete && (
        <p className="text-xs text-amber-400/90 mb-3">
          Group stage in progress — knockout matchups firm up as groups finish.
          Slots show the bracket structure (winners, runners-up, best thirds);
          teams and scores fill in automatically as results are recorded.
        </p>
      )}

      {b.champion && (
        <p className="text-xs mb-3">
          <span className="text-gray-500">Champion: </span>
          <span className="font-mono text-accent font-semibold">{b.champion}</span>
        </p>
      )}

      <div className="overflow-x-auto">
        <div className="flex gap-4 min-w-max">
          {ROUNDS.map(({ key, label }) => {
            const ties = roundTies(key);
            if (ties.length === 0) return null;
            return (
              <div key={String(key)} className="shrink-0">
                <div className="text-[11px] uppercase tracking-wide text-gray-500 mb-2">
                  {label}
                </div>
                <div
                  className={
                    key === "R32"
                      ? "grid grid-cols-2 gap-x-3 gap-y-1.5"
                      : "flex flex-col gap-1.5"
                  }
                >
                  {ties.map((t, i) => (
                    <Tie key={t.match ?? i} tie={t} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
