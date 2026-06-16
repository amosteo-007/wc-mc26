"use client";

import type { GroupState } from "@/lib/types";

interface GroupTablesProps {
  groups: GroupState[];
}

/** 12 compact group standings tables. Top-2 highlighted (auto-advance),
 *  3rd flagged as a best-third contender. Empty groups show "Not started". */
export function GroupTables({ groups }: GroupTablesProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {groups.map((g) => {
        const notStarted = g.played === 0;
        return (
          <div
            key={g.group}
            className="bg-gray-900 border border-gray-800 rounded-lg p-3"
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-gray-200">
                Group {g.group}
              </h4>
              {notStarted ? (
                <span className="text-[10px] uppercase tracking-wide text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded">
                  Not started
                </span>
              ) : (
                <span className="text-[10px] text-gray-500">
                  {g.played} played
                </span>
              )}
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left font-normal py-1">Team</th>
                  <th className="w-5 text-center font-normal">P</th>
                  <th className="w-7 text-center font-normal">GD</th>
                  <th className="w-6 text-center font-normal">Pts</th>
                </tr>
              </thead>
              <tbody>
                {g.standings.map((s) => {
                  const advance = s.rank <= 2;
                  const thirdContender = s.rank === 3;
                  return (
                    <tr
                      key={s.team}
                      className={`border-b border-gray-800/50 last:border-0 ${
                        advance
                          ? "bg-green-900/15"
                          : thirdContender
                          ? "bg-amber-900/10"
                          : ""
                      }`}
                      title={
                        advance
                          ? "Advances (top 2)"
                          : thirdContender
                          ? "Best-third contender"
                          : undefined
                      }
                    >
                      <td className="py-1 text-gray-200">
                        <span className="text-gray-600 mr-1">{s.rank}.</span>
                        {s.team}
                        {notStarted ? null : advance ? (
                          <span className="text-green-500 ml-1">●</span>
                        ) : thirdContender ? (
                          <span className="text-amber-500 ml-1">○</span>
                        ) : null}
                      </td>
                      <td className="text-center text-gray-400">{s.p}</td>
                      <td className="text-center text-gray-400">
                        {s.gd > 0 ? `+${s.gd}` : s.gd}
                      </td>
                      <td className="text-center font-mono text-gray-100">
                        {s.pts}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
