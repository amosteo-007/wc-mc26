"use client";

import type { Confidence, Condition } from "@/lib/types";

interface ConditionalExplainerProps {
  confidence?: Confidence | null;
  condition?: Condition | null;
}

/**
 * Explains what a conditional ("what-if") result means so the redistributed
 * numbers never read as a forecast. Renders nothing for unconditional runs.
 */
export function ConditionalExplainer({ confidence, condition }: ConditionalExplainerProps) {
  if (!confidence) return null;

  // `team_wins` forces a champion; we now drop that pinned team from the board,
  // so the explainer describes the redistribution rather than a 100% bar.
  const pinsChampion = condition?.type === "team_wins";
  const pinnedTeam = condition?.params?.team_fifa_code;

  const accept = confidence.acceptance_rate;
  const effective = confidence.effective_runs;
  const requested = confidence.requested_runs;

  // Unconditional runs keep every rollout (rate ≈ 1) — no explainer needed.
  const isConditional =
    typeof accept === "number" && accept < 0.999;
  if (!isConditional) return null;

  const pct = (accept * 100).toFixed(accept < 0.01 ? 2 : 1);
  const thin = confidence.thin_sample;

  return (
    <div className="card border-amber-600/40 bg-amber-600/5">
      <div className="flex items-start gap-3">
        <span className="text-amber-400 text-lg leading-none mt-0.5">ⓘ</span>
        <div className="text-sm text-gray-300 space-y-2">
          <p>
            <span className="font-semibold text-amber-300">
              This is a conditional &ldquo;what-if&rdquo; view.
            </span>{" "}
            You asked to see only the tournaments that match your selected
            condition.{" "}
            {pinsChampion ? (
              <>
                Since {pinnedTeam ?? "your team"} is forced to win in every
                matching world, it is left off the board — the table below shows
                how the <em>runner-up</em> field redistributes when that happens.
              </>
            ) : (
              <>
                The numbers below are computed only within those matching worlds,
                so they are <span className="font-semibold">not</span> a forecast
                that this scenario will happen.
              </>
            )}
          </p>
          <p>
            Your scenario occurred in{" "}
            <span className="font-mono text-gray-100">{pct}%</span> of simulated
            tournaments
            {typeof effective === "number" && typeof requested === "number" && (
              <>
                {" "}
                (<span className="font-mono">{effective.toLocaleString()}</span>{" "}
                of <span className="font-mono">{requested.toLocaleString()}</span>{" "}
                runs matched)
              </>
            )}
            . That percentage is the real likelihood of the condition; the
            interesting results are how the <em>other</em> outcomes
            (finalists, paths, narrative reaction) redistribute within those
            matching worlds.
          </p>
          {thin && (
            <p className="text-amber-300">
              ⚠ Thin sample: few tournaments matched, so the redistributed
              numbers are noisy. Try a less extreme condition or a higher tier
              for a steadier read.
            </p>
          )}
          <p className="text-xs text-gray-500">
            Want the straight &ldquo;who is most likely to win&rdquo; board?
            Run again with no condition.
          </p>
        </div>
      </div>
    </div>
  );
}
