"use client";

import Link from "next/link";
import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { createSimulation, getTeams, getTournament } from "@/lib/api";
import type {
  SelectionState,
  Condition,
  Team,
  TournamentState,
} from "@/lib/types";
import { GroupTables } from "@/app/components/GroupTables";
import { KnockoutBracket } from "@/app/components/KnockoutBracket";
import {
  EDITIONS,
  MODES,
  CONDITIONS,
  NARRATIVE_PACKS,
  AUDIENCE_SCOPES,
  REPORT_TIERS,
  TEAMS,
} from "./wizard.config";
import { RadioGroup } from "@/app/components/RadioGroup";
import { MultiSelect } from "@/app/components/MultiSelect";
import Select from "@/app/components/Select";

export default function WizardPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Teams come from the backend (the real seeded field) with the static list as
  // a fallback so the dropdown never drifts from what's actually simulated.
  const [teams, setTeams] = useState<Team[]>(TEAMS);
  const [tournament, setTournament] = useState<TournamentState | null>(null);
  const [showTournament, setShowTournament] = useState(true);
  useEffect(() => {
    getTeams()
      .then((t) => {
        if (t.length > 0) setTeams(t);
      })
      .catch(() => {
        /* keep static fallback */
      });
    getTournament()
      .then(setTournament)
      .catch(() => {
        /* tournament view is optional — fall back to condition picker only */
      });
  }, []);

  const [edition, setEdition] = useState("WC2026");
  const [mode, setMode] = useState<SelectionState["mode"]>("combined");
  const [conditionType, setConditionType] = useState<string | null>(null);
  const [conditionTeam, setConditionTeam] = useState<string>("");
  const [narrativePacks, setNarrativePacks] = useState<string[]>([]);
  const [audienceScope, setAudienceScope] = useState<string[]>([]);
  const [reportTier, setReportTier] = useState<SelectionState["report_tier"]>("quick");

  // Narrative-only has no Monte Carlo condition step, but the transfer/news
  // narrative still needs a subject team to anchor on (whose squad it names).
  // We model that as a team_wins condition so the orchestrator's existing
  // winner-anchoring path picks it up.
  const [narrativeTeam, setNarrativeTeam] = useState<string>("");

  const buildCondition = useCallback((): Condition | null => {
    if (mode === "narrative") {
      return narrativeTeam
        ? { type: "team_wins", params: { team_fifa_code: narrativeTeam } }
        : null;
    }
    if (!conditionType) return null;
    const template = CONDITIONS.find((c) => c.id === conditionType);
    if (!template) return null;
    const params: Record<string, string> = {};
    if (template.needsTeam && conditionTeam) {
      params.team_fifa_code = conditionTeam;
    }
    return { type: conditionType, params };
  }, [mode, narrativeTeam, conditionType, conditionTeam]);

  // Step 3 (Condition) is for outcome/combined; step 4 (Narrative Packs) is for
  // narrative/combined. Skip the steps that don't apply so the user never lands
  // on an empty card.
  const applicableSteps = [
    1,
    2,
    ...(mode !== "narrative" ? [3] : []),
    ...(mode !== "outcome" ? [4] : []),
    5,
    6,
  ];
  // If the mode change made the current step inapplicable (e.g. on step 4 then
  // switching to outcome-only), snap to the nearest valid step.
  useEffect(() => {
    if (!applicableSteps.includes(step)) {
      const fallback = [...applicableSteps].reverse().find((s) => s < step);
      setStep(fallback ?? applicableSteps[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const stepIndex = applicableSteps.indexOf(step);
  const isFirstStep = stepIndex <= 0;
  const isLastStep = stepIndex === applicableSteps.length - 1;
  const goNext = () => {
    const next = applicableSteps[stepIndex + 1];
    if (next) setStep(next);
  };
  const goBack = () => {
    const prev = applicableSteps[stepIndex - 1];
    if (prev) setStep(prev);
  };

  const canSubmit =
    edition &&
    mode &&
    (mode === "outcome" || narrativePacks.length > 0) &&
    (mode !== "narrative" || narrativeTeam) &&
    audienceScope.length > 0 &&
    reportTier;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const selections: SelectionState = {
        edition,
        mode,
        condition: buildCondition(),
        narrative_packs: narrativePacks,
        audience_scope: audienceScope,
        report_tier: reportTier,
      };
      const { run_id } = await createSimulation(selections);
      router.push(`/run/${run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create simulation");
      setSubmitting(false);
    }
  };

  const selectedCondition = CONDITIONS.find((c) => c.id === conditionType);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold tracking-tight">WC2026 Simulation Console</h1>
        <p className="text-sm text-gray-500 mt-1">
          Constrained forecasting — every selection is bounded
        </p>
        <div className="flex items-center gap-4 mt-2">
          <Link href="/match" className="text-sm text-blue-400 hover:text-blue-300 transition-colors">
            Match Simulator →
          </Link>
        </div>
        {/* Step indicator — one segment per applicable step for the chosen mode */}
        <div className="flex gap-1 mt-4">
          {applicableSteps.map((s, i) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full ${
                i <= stepIndex ? "bg-blue-600" : "bg-gray-800"
              }`}
            />
          ))}
        </div>
      </header>

      {/* Steps */}
      <div className="wizard-step">
        {step === 1 && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 1: Tournament</h2>
            <p className="text-gray-400 mb-6">Select the tournament edition to simulate.</p>
            <RadioGroup
              options={EDITIONS.map((e) => ({
                value: e.id,
                label: e.label,
                description: e.format,
              }))}
              value={edition}
              onChange={setEdition}
            />
          </div>
        )}

        {step === 2 && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 2: Simulation Type</h2>
            <p className="text-gray-400 mb-6">
              Choose what kind of simulation to run. &ldquo;Combined&rdquo; runs both the Monte
              Carlo outcome engine and the narrative layer.
            </p>
            <RadioGroup
              options={MODES.map((m) => ({
                value: m.id,
                label: m.label,
                description: m.description,
              }))}
              value={mode}
              onChange={(v) => setMode(v as SelectionState["mode"])}
            />
          </div>
        )}

        {step === 3 && mode !== "narrative" && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 3: Condition</h2>
            <p className="text-gray-400 mb-6">
              Apply a constraint to the Monte Carlo simulation. Leave empty for unconditional
              probabilities.
            </p>

            {/* Live tournament context — group tables + TBD knockout bracket */}
            {tournament && (
              <div className="mb-6">
                <button
                  type="button"
                  onClick={() => setShowTournament((v) => !v)}
                  className="flex items-center gap-2 text-sm font-medium text-gray-300 hover:text-gray-100 mb-3"
                >
                  <span className="text-gray-500">{showTournament ? "▾" : "▸"}</span>
                  Tournament so far
                  <span className="text-xs text-gray-500">
                    {tournament.group_stage_complete
                      ? "group stage complete"
                      : "group stage in progress"}
                  </span>
                </button>
                {showTournament && (
                  <div className="space-y-4">
                    <GroupTables groups={tournament.groups} />
                    <div>
                      <h3 className="text-sm font-semibold text-gray-300 mb-2">
                        Knockout Bracket
                      </h3>
                      <KnockoutBracket
                        r32={tournament.knockout_bracket?.R32}
                        groupStageComplete={tournament.group_stage_complete}
                      />
                    </div>
                  </div>
                )}
                <div className="border-t border-gray-800 mt-6 mb-4" />
              </div>
            )}

            <RadioGroup
              options={[
                { value: "", label: "None (unconditional)", description: "No constraint applied" },
                ...CONDITIONS.map((c) => ({
                  value: c.id,
                  label: c.label,
                  description: c.description,
                })),
              ]}
              value={conditionType || ""}
              onChange={(v) => setConditionType(v || null)}
            />
            {selectedCondition?.needsTeam && (
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1 text-gray-300">
                  Select Team
                </label>
                <select
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
                  value={conditionTeam}
                  onChange={(e) => setConditionTeam(e.target.value)}
                >
                  <option value="">-- Select a team --</option>
                  {teams.map((t) => (
                    <option key={t.fifa_code} value={t.fifa_code}>
                      {t.name} ({t.fifa_code})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        {step === 4 && mode !== "outcome" && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 4: Narrative Packs</h2>
            <p className="text-gray-400 mb-6">
              Select which stakeholder layers to simulate. Each pack adds agents to the narrative
              simulation.
            </p>
            <MultiSelect
              options={NARRATIVE_PACKS.map((p) => ({
                value: p.id,
                label: p.label,
                description: p.description,
              }))}
              values={narrativePacks}
              onChange={setNarrativePacks}
            />

            {/* Narrative-only has no condition step, so pick the subject team
                here — the transfer/news narrative anchors on its squad. */}
            {mode === "narrative" && (
              <div className="mt-6 border-t border-gray-800 pt-4">
                <label className="block text-sm font-medium mb-1 text-gray-300">
                  Narrative subject team
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  Transfer rumors and value shifts will be about this team&apos;s players.
                </p>
                <select
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
                  value={narrativeTeam}
                  onChange={(e) => setNarrativeTeam(e.target.value)}
                >
                  <option value="">-- Select a team --</option>
                  {teams.map((t) => (
                    <option key={t.fifa_code} value={t.fifa_code}>
                      {t.name} ({t.fifa_code})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}

        {step === 5 && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 5: Audience Scope</h2>
            <p className="text-gray-400 mb-6">
              Which audience lenses should be active? This determines which personas are
              instantiated in the narrative simulation.
            </p>
            <MultiSelect
              options={AUDIENCE_SCOPES.map((a) => ({
                value: a.id,
                label: a.label,
                description: a.description,
              }))}
              values={audienceScope}
              onChange={setAudienceScope}
            />
          </div>
        )}

        {step === 6 && (
          <div className="card">
            <h2 className="text-lg font-semibold mb-2">Step 6: Report Tier</h2>
            <p className="text-gray-400 mb-6">
              Higher tiers run more simulations, more agents, and more rounds — producing richer
              results but taking longer.
            </p>
            <RadioGroup
              options={REPORT_TIERS.map((t) => ({
                value: t.id,
                label: `${t.label} (${t.estimatedCost} · ${t.estimatedLatency})`,
                description: t.description,
              }))}
              value={reportTier}
              onChange={(v) => setReportTier(v as SelectionState["report_tier"])}
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between mt-6">
          <button
            className="btn-secondary"
            disabled={isFirstStep}
            onClick={goBack}
          >
            Back
          </button>

          {!isLastStep ? (
            <button
              className="btn-primary"
              onClick={goNext}
            >
              Next
            </button>
          ) : (
            <button
              className="btn-primary"
              disabled={!canSubmit || submitting}
              onClick={handleSubmit}
            >
              {submitting ? "Submitting..." : "Run Simulation"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
