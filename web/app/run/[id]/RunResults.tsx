"use client";

import { useEffect, useState } from "react";
import { getSimulation } from "@/lib/api";
import type { SimulationResult } from "@/lib/types";
import Link from "next/link";
import { RedistributionTable } from "@/app/components/RedistributionTable";
import { ConfidenceBadge } from "@/app/components/ConfidenceBadge";
import { ConditionalExplainer } from "@/app/components/ConditionalExplainer";
import { SimDisclaimer } from "@/app/components/SimDisclaimer";
import {
  describeCondition,
  conditionStageTarget,
  isNonNumericCondition,
} from "@/lib/conditions";
import { Heatmap } from "@/app/components/Heatmap";
import { Timeline } from "@/app/components/Timeline";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  outcome_running: "Simulating Outcomes...",
  outcome_done: "Outcomes Complete",
  narrative_running: "Simulating Narratives...",
  synthesizing: "Synthesizing Report...",
  done: "Complete",
  failed: "Failed",
};

/** Read the run id from the live URL. Under static export (`output: 'export'`)
 *  the dynamic route is served by the `_` shell, so Next's route params are the
 *  build-time placeholder ("_"), not the real segment — we must parse the path. */
function useRunIdFromPath(): string {
  const [runId, setRunId] = useState("");
  useEffect(() => {
    const segs = window.location.pathname.split("/").filter(Boolean);
    setRunId(decodeURIComponent(segs[segs.length - 1] ?? ""));
  }, []);
  return runId;
}

export default function RunResults() {
  const runId = useRunIdFromPath();
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || runId === "_") return;
    let mounted = true;
    let interval: ReturnType<typeof setInterval>;

    const poll = async () => {
      try {
        const data = await getSimulation(runId);
        if (!mounted) return;
        setResult(data);
        if (data.status === "done" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Failed to load simulation");
      }
    };

    poll();
    interval = setInterval(poll, 2000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [runId]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="card text-center">
          <h2 className="text-lg font-semibold text-red-400 mb-2">Error</h2>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-accent border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-400">Loading simulation...</p>
        </div>
      </div>
    );
  }

  const status = result.status;
  const isDone = status === "done";
  const isFailed = status === "failed";
  const hasOutcome = result.outcome && (
    status === "outcome_done" || status === "narrative_running" ||
    status === "synthesizing" || status === "done"
  );
  const hasNarrative = result.narrative && (status === "done");

  // What was simulated + the unconditional probability of the chosen event.
  const conditionLabel = describeCondition(result.condition);
  const stageTarget = conditionStageTarget(result.condition);
  const stageProb =
    stageTarget && result.outcome?.stage_probs
      ? result.outcome.stage_probs[stageTarget.stage]?.[stageTarget.team]
      : undefined;
  const nonNumeric = isNonNumericCondition(result.condition);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/wizard"
              className="text-sm text-gray-400 hover:text-gray-100 transition-colors whitespace-nowrap"
            >
              ← New simulation
            </Link>
            <div className="border-l border-gray-800 pl-4">
              <h1 className="text-lg font-bold">Simulation Results</h1>
              <p className="text-xs text-gray-600 font-mono">{runId}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!isDone && !isFailed && (
              <div className="animate-spin w-4 h-4 border-2 border-accent border-t-transparent rounded-full" />
            )}
            <span
              className={`text-sm font-medium px-3 py-1 rounded-full ${
                isFailed
                  ? "bg-red-900/30 text-red-300"
                  : isDone
                  ? "bg-green-900/30 text-green-300"
                  : "bg-amber-900/30 text-amber-300"
              }`}
            >
              {STATUS_LABELS[status] || status}
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Disclaimer — always visible */}
        <SimDisclaimer />

        {/* Failed state */}
        {isFailed && (
          <div className="card text-center py-8">
            <h2 className="text-lg font-semibold text-red-400 mb-2">Simulation Failed</h2>
            <p className="text-gray-400">
              An error occurred during processing. Please try again with different parameters.
            </p>
          </div>
        )}

        {/* Quantitative Panel */}
        {hasOutcome && result.outcome && (
          <section>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-base font-semibold">Quantitative Results</h2>
              <ConfidenceBadge confidence={result.outcome.confidence} />
            </div>
            {/* What was simulated */}
            <p className="text-sm text-gray-400 mb-4">
              Simulating:{" "}
              <span className="text-gray-200 font-medium">{conditionLabel}</span>
              {nonNumeric && (
                <span className="text-amber-400">
                  {" "}— this condition does not change the outcome math
                </span>
              )}
            </p>
            {/* Explains a pinned 100% champion on conditional ("what-if") runs */}
            <div className="mb-4">
              <ConditionalExplainer
                confidence={result.outcome.confidence}
                condition={result.condition}
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <RedistributionTable
                championProbs={result.outcome.champion_probs}
              />
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">
                  Simulation Summary
                </h3>
                <dl className="space-y-2 text-sm">
                  {stageTarget && typeof stageProb === "number" && (
                    <div className="flex justify-between border-b border-gray-800 pb-2 mb-1">
                      <dt className="text-gray-400">
                        P({stageTarget.team} {stageTarget.verb})
                      </dt>
                      <dd className="font-mono text-blue-300">
                        {(stageProb * 100).toFixed(1)}%
                      </dd>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Effective Runs</dt>
                    <dd className="font-mono">
                      {result.outcome.effective_runs?.toLocaleString()}
                      {result.outcome.confidence?.requested_runs && (
                        <span className="text-gray-600">
                          {" "}/ {result.outcome.confidence.requested_runs.toLocaleString()}
                        </span>
                      )}
                    </dd>
                  </div>
                  {typeof result.outcome.confidence?.acceptance_rate === "number" &&
                    result.outcome.confidence.acceptance_rate < 0.999 && (
                      <div className="flex justify-between">
                        <dt className="text-gray-500" title="How often your condition occurred across all simulated tournaments">
                          Scenario Frequency
                        </dt>
                        <dd className="font-mono text-amber-300">
                          {(result.outcome.confidence.acceptance_rate * 100).toFixed(
                            result.outcome.confidence.acceptance_rate < 0.01 ? 2 : 1
                          )}%
                        </dd>
                      </div>
                    )}
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Data Quality</dt>
                    <dd className="font-mono capitalize">
                      {result.outcome.confidence?.data_quality || "unknown"}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Rating Coverage</dt>
                    <dd className="font-mono">
                      {((result.outcome.confidence?.rating_coverage || 0) * 100).toFixed(0)}%
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          </section>
        )}

        {/* Qualitative Panel */}
        {hasNarrative && result.narrative && (
          <section>
            <h2 className="text-base font-semibold mb-4">Transfer & News Reactions</h2>

            {/* Narrative Clusters */}
            {result.narrative.narratives?.length > 0 && (
              <div className="card mb-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">
                  Transfer & News Clusters
                </h3>
                <div className="space-y-2">
                  {result.narrative.narratives.map((cluster) => (
                    <div key={cluster.cluster_id} className="flex items-center gap-3">
                      <span className="w-32 text-xs text-gray-400 truncate">
                        {cluster.label}
                      </span>
                      <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                        <div
                          className="h-full bg-purple-600 rounded-full"
                          style={{ width: `${(cluster.dominance || 0) * 100}%` }}
                        />
                      </div>
                      <span className="w-16 text-right text-xs font-mono text-gray-500">
                        {cluster.agent_count} agents
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              {/* Sentiment Heatmap */}
              {result.narrative.sentiment && (
                <Heatmap sentiment={result.narrative.sentiment} />
              )}

              {/* Turning Points */}
              {result.narrative.turning_points && (
                <Timeline turningPoints={result.narrative.turning_points} />
              )}
            </div>

            {/* Sample Posts */}
            {result.narrative.sample_posts?.length > 0 && (
              <div className="card mt-4">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">
                  Sample Synthetic Posts
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {result.narrative.sample_posts.slice(0, 10).map((post) => (
                    <div
                      key={post.post_id}
                      className="bg-gray-800/50 rounded-lg p-3 text-sm"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs text-gray-500 font-mono">
                          {post.agent_id}
                        </span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-purple-900/40 text-purple-300">
                          SYNTHETIC
                        </span>
                      </div>
                      <p className="text-gray-300">{post.content}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Comparative Panel — side-by-side when multiple worlds simulated */}
        {hasNarrative && result.comparative && result.comparative.length > 0 && (
          <section>
            <h2 className="text-base font-semibold mb-4">
              Comparative Analysis — Top {result.comparative.length + 1} Winner Worlds
            </h2>
            <div className={`grid gap-4 ${
              result.comparative.length === 1 ? 'md:grid-cols-2' :
              result.comparative.length >= 2 ? 'md:grid-cols-3' : ''
            }`}>
              {/* Primary world (already shown above, show compact card) */}
              <div className="card border-blue-600/50 bg-blue-600/5">
                <div className="text-xs text-blue-400 font-medium mb-2">
                  Primary World
                </div>
                <div className="text-lg font-bold mb-1">
                  {Object.entries(result.outcome?.champion_probs || {})
                    .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[0] || '—'}
                </div>
                <div className="text-xs text-gray-500">
                  {(Object.entries(result.outcome?.champion_probs || {})
                    .sort(([, a], [, b]) => (b as number) - (a as number))[0]?.[1] as number * 100 || 0).toFixed(1)}% probability
                </div>
                {result.narrative?.sentiment && (
                  <div className="mt-3">
                    <div className="text-xs text-gray-500 mb-1">Sentiment</div>
                    <div className="flex items-end gap-0.5 h-10">
                      {result.narrative.sentiment.overall.slice(-12).map((v, i) => (
                        <div
                          key={i}
                          className={`flex-1 rounded-t-sm ${
                            v >= 0 ? 'bg-green-500/50' : 'bg-red-500/50'
                          }`}
                          style={{ height: `${Math.max(Math.abs(v) * 60, 4)}%` }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Comparative worlds */}
              {result.comparative.map((world) => (
                <div key={world._winner} className="card border-gray-700">
                  <div className="text-xs text-purple-400 font-medium mb-2">
                    Alternative World
                  </div>
                  <div className="text-lg font-bold mb-1">{world._winner}</div>
                  <div className="text-xs text-gray-500">
                    {(world._winner_prob * 100).toFixed(1)}% probability
                  </div>
                  {world.sentiment?.overall && (
                    <div className="mt-3">
                      <div className="text-xs text-gray-500 mb-1">Sentiment</div>
                      <div className="flex items-end gap-0.5 h-10">
                        {world.sentiment.overall.slice(-12).map((v, i) => (
                          <div
                            key={i}
                            className={`flex-1 rounded-t-sm ${
                              v >= 0 ? 'bg-green-500/50' : 'bg-red-500/50'
                            }`}
                            style={{ height: `${Math.max(Math.abs(v) * 60, 4)}%` }}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  {world.narratives && world.narratives.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs text-gray-500 mb-1">
                        Top Narrative
                      </div>
                      <div className="text-xs text-gray-300">
                        {world.narratives[0]?.label || '—'}
                        <span className="text-gray-600 ml-2">
                          ({world.narratives[0]?.agent_count || 0} agents)
                        </span>
                      </div>
                    </div>
                  )}
                  {world.error && (
                    <div className="mt-2 text-xs text-red-400">{world.error}</div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
