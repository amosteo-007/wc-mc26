"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { MatchResult, Team } from "@/lib/types";
import { getTeams, runMatch } from "@/lib/api";
import { MATCH_PRESETS, TEAMS } from "@/app/wizard/wizard.config";

// Use the static teams list as fallback; the page tries the orchestrator first.
const FALLBACK_TEAMS: Team[] = TEAMS;

export default function MatchPage() {
  const [homeCode, setHomeCode] = useState("ARG");
  const [awayCode, setAwayCode] = useState("BRA");
  const [goalLine, setGoalLine] = useState<string>("");
  const [nRuns, setNRuns] = useState(20000);
  const [neutral, setNeutral] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>(FALLBACK_TEAMS);

  // Try to fetch the live team list on mount (via the /api proxy, same as the
  // rest of the app). Falls back to the static list on any error.
  useEffect(() => {
    getTeams()
      .then((t) => { if (t.length) setTeams(t); })
      .catch(() => {}); // fallback to static list
  }, []);

  const handleRunMatch = async () => {
    if (homeCode === awayCode) {
      setError("Home and away teams must be different");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await runMatch({
        home_fifa_code: homeCode,
        away_fifa_code: awayCode,
        n_runs: nRuns,
        neutral,
        goal_line: goalLine && !isNaN(Number(goalLine)) ? Number(goalLine) : null,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Match simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const probPct = (v: number) => (v * 100).toFixed(1) + "%";

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <Link href="/wizard" className="text-sm text-gray-400 hover:text-gray-100 transition-colors">
            ← Wizard
          </Link>
          <div className="border-l border-gray-800 pl-4">
            <h1 className="text-lg font-bold">Match Simulator</h1>
            <p className="text-xs text-gray-600">Single-match Monte Carlo</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6 space-y-6">
        {/* Controls */}
        <div className="card space-y-4">
          <h2 className="text-sm font-semibold text-gray-300">Match Setup</h2>

          {/* Presets */}
          <div className="flex flex-wrap gap-2">
            {MATCH_PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => { setHomeCode(p.home); setAwayCode(p.away); }}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  homeCode === p.home && awayCode === p.away
                    ? "border-blue-500 bg-blue-900/30 text-blue-300"
                    : "border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Team pickers */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Home Team</label>
              <select
                value={homeCode}
                onChange={(e) => setHomeCode(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              >
                {teams.map((t) => (
                  <option key={t.fifa_code} value={t.fifa_code}>
                    {t.name} ({t.fifa_code})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Away Team</label>
              <select
                value={awayCode}
                onChange={(e) => setAwayCode(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              >
                {teams.map((t) => (
                  <option key={t.fifa_code} value={t.fifa_code}>
                    {t.name} ({t.fifa_code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Options */}
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Goal Line (optional)</label>
              <input
                type="number"
                min="0"
                max="15"
                step="0.5"
                value={goalLine}
                onChange={(e) => setGoalLine(e.target.value)}
                placeholder="e.g. 3"
                className="w-24 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Runs</label>
              <select
                value={nRuns}
                onChange={(e) => setNRuns(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200"
              >
                <option value={5000}>5,000</option>
                <option value={10000}>10,000</option>
                <option value={20000}>20,000</option>
                <option value={50000}>50,000</option>
                <option value={100000}>100,000</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-400 pt-5">
              <input
                type="checkbox"
                checked={neutral}
                onChange={(e) => setNeutral(e.target.checked)}
                className="rounded border-gray-600"
              />
              Neutral venue
            </label>
            <button
              onClick={handleRunMatch}
              disabled={loading}
              className="ml-auto px-6 py-2 bg-accent hover:bg-accent-hover text-surface-base disabled:bg-gray-700 disabled:text-gray-400 rounded-lg text-sm font-semibold transition-colors"
            >
              {loading ? "Simulating..." : "Simulate Match"}
            </button>
          </div>

          {error && (
            <div className="text-sm text-red-400 bg-red-900/20 rounded-lg px-3 py-2">{error}</div>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* W/D/L bar */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">
                {result.home_team.name} vs {result.away_team.name}
              </h3>
              <div className="flex h-8 rounded-full overflow-hidden text-xs font-mono font-semibold">
                <div
                  className="bg-green-600 flex items-center justify-center transition-all"
                  style={{ width: `${Math.max(result.win_home * 100, 1)}%` }}
                >
                  {probPct(result.win_home)}
                </div>
                <div
                  className="bg-gray-500 flex items-center justify-center transition-all"
                  style={{ width: `${Math.max(result.draw * 100, 1)}%` }}
                >
                  {probPct(result.draw)}
                </div>
                <div
                  className="bg-red-600 flex items-center justify-center transition-all"
                  style={{ width: `${Math.max(result.win_away * 100, 1)}%` }}
                >
                  {probPct(result.win_away)}
                </div>
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{result.home_team.fifa_code} Win</span>
                <span>Draw</span>
                <span>{result.away_team.fifa_code} Win</span>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {/* Goal distribution */}
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-300 mb-3">Total Goals Distribution</h3>
                <div className="space-y-1">
                  {Object.entries(result.total_goals_distribution).map(([goals, prob]) => (
                    <div key={goals} className="flex items-center gap-2">
                      <span className="w-8 text-right text-xs font-mono text-gray-400">{goals}</span>
                      <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
                        <div
                          className="h-full bg-purple-600 rounded-full transition-all"
                          style={{ width: `${(prob as number) * 100}%` }}
                        />
                      </div>
                      <span className="w-14 text-right text-xs font-mono text-gray-500">
                        {((prob as number) * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Over/Under + BTS + Goal line */}
              <div className="space-y-4">
                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Over/Under Lines</h3>
                  <div className="grid grid-cols-5 gap-2 text-center text-xs">
                    {[0.5, 1.5, 2.5, 3.5, 4.5].map((line) => {
                      const overKey = `over_${String(line).replace('.', '_')}`;
                      return (
                        <div key={line}>
                          <div className="text-gray-500 mb-0.5">{line}</div>
                          <div className="font-mono text-gray-200">
                            {(result.over_under[overKey] as number * 100).toFixed(0)}%
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-300 mb-2">Quick Stats</h3>
                  <dl className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Both Teams Score</dt>
                      <dd className="font-mono">{probPct(result.both_teams_score)}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Expected Goals (Total)</dt>
                      <dd className="font-mono">{result.expected_total}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-gray-500">Simulated Avg Goals</dt>
                      <dd className="font-mono">{(result.mean_simulated_home + result.mean_simulated_away).toFixed(2)}</dd>
                    </div>
                    {result.goal_line_query && (
                      <div className="flex justify-between border-t border-gray-800 pt-1 mt-1">
                        <dt className="text-gray-400">P(Total ≥ {result.goal_line_query.line})</dt>
                        <dd className="font-mono text-blue-300">
                          {probPct(result.goal_line_query.prob_over)}
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>
              </div>
            </div>

            {/* Top scorelines */}
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Top Scorelines</h3>
              <div className="flex flex-wrap gap-2">
                {result.top_scorelines.slice(0, 8).map((sl) => (
                  <span
                    key={sl.scoreline}
                    className="px-2 py-1 bg-gray-800 rounded text-xs font-mono"
                  >
                    {sl.scoreline}{" "}
                    <span className="text-gray-500">{probPct(sl.probability)}</span>
                  </span>
                ))}
              </div>
            </div>

            {/* Confidence */}
            <div className="text-xs text-gray-600 text-right">
              {result.confidence.n_runs.toLocaleString()} runs •
              Elo: {result.home_team.elo} vs {result.away_team.elo} •
              Form: {result.confidence.form_applied ? 'applied' : 'not applied'}
            </div>
          </div>
        )}

        {/* Scenario disclaimer */}
        <div className="text-xs text-center text-gray-600 border-t border-gray-800 pt-4">
          Scenario simulation, not a prediction. Goal model uses Elo-derived Poisson expectations.
          All probabilities are Monte Carlo estimates with ± sampling error.
        </div>
      </main>
    </div>
  );
}
