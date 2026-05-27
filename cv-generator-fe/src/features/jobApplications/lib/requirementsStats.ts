import type { RequirementsAnalysis } from "../../../api/job-applications/jobApplications";

export type RequirementsStats = {
  mustMet: number;
  mustTotal: number;
  niceMet: number;
  niceTotal: number;
};

export function computeRequirementsStats(
  analysis: RequirementsAnalysis | null | undefined,
): RequirementsStats | null {
  if (!analysis || !analysis.requirements.length) return null;
  let mustMet = 0;
  let mustTotal = 0;
  let niceMet = 0;
  let niceTotal = 0;
  for (const r of analysis.requirements) {
    if (r.importance === "must_have") {
      mustTotal += 1;
      if (r.met) mustMet += 1;
    } else {
      niceTotal += 1;
      if (r.met) niceMet += 1;
    }
  }
  return { mustMet, mustTotal, niceMet, niceTotal };
}
