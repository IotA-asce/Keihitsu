export const API_BASE_URL = "http://localhost:8000";

async function callStep(path: string, body?: Record<string, any>): Promise<any> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }

  return res.json();
}

export const PipelineApi = {
  health: async () => {
    const res = await fetch(`${API_BASE_URL}/api/health`);
    return res.json();
  },
  runChapters: () => callStep("/api/steps/chapters"),
  runVlm: () => callStep("/api/steps/vlm"),
  runNovel: () => callStep("/api/steps/novel"),
  runAnchors: () => callStep("/api/steps/anchors"),
  runBranches: () => callStep("/api/steps/branches"),
  runCharacters: () => callStep("/api/steps/characters"),
  runScales: () => callStep("/api/steps/scales"),
  continueMain: (timelinePath?: string) =>
    callStep("/api/steps/continue-main", { timeline_path: timelinePath ?? null }),
  branchPlan: (branchId: string) =>
    callStep("/api/steps/branch-plan?branch_id=" + encodeURIComponent(branchId)),
  branchGenerate: (branchId: string) =>
    callStep("/api/steps/branch-generate?branch_id=" + encodeURIComponent(branchId)),
  branchContinue: (branchId: string) =>
    callStep("/api/steps/branch-continue?branch_id=" + encodeURIComponent(branchId)),
};
