import React, { useState } from "react";
import {
  Box,
  Grid,
  TextField,
  Button,
  Typography,
  Alert,
  Snackbar,
} from "@mui/material";
import StepCard from "./StepCard";
import LogsPanel from "./LogsPanel";
import { PipelineApi } from "../apiClient";

type StepKey =
  | "chapters"
  | "vlm"
  | "novel"
  | "anchors"
  | "branches"
  | "characters"
  | "scales"
  | "continueMain"
  | "branchPlan"
  | "branchGenerate"
  | "branchContinue";

const PipelineDashboard: React.FC = () => {
  const [running, setRunning] = useState<Record<StepKey, boolean>>({
    chapters: false,
    vlm: false,
    novel: false,
    anchors: false,
    branches: false,
    characters: false,
    scales: false,
    continueMain: false,
    branchPlan: false,
    branchGenerate: false,
    branchContinue: false,
  });

  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [timelinePath, setTimelinePath] = useState<string>("");
  const [branchId, setBranchId] = useState<string>("");

  const pushLog = (msg: string) => {
    const stamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev, `[${stamp}] ${msg}`]);
  };

  const runStep = async (key: StepKey, fn: () => Promise<any>) => {
    try {
      setRunning((prev) => ({ ...prev, [key]: true }));
      pushLog(`Starting step: ${key}`);
      const res = await fn();
      pushLog(`Finished step: ${key} (response: ${JSON.stringify(res)})`);
    } catch (err: any) {
      console.error(err);
      const msg = err?.message ?? String(err);
      setError(msg);
      pushLog(`Error in step ${key}: ${msg}`);
    } finally {
      setRunning((prev) => ({ ...prev, [key]: false }));
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        {/* Core pipeline steps */}
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="1. Segment Chapters"
            description="Split raw manga pages into per-chapter folders using heuristics + VLM title checks."
            running={running.chapters}
            onRun={() => runStep("chapters", PipelineApi.runChapters)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="2. VLM Extraction"
            description="Use Grok VLM to describe each chapter batch-wise into JSON summaries."
            running={running.vlm}
            onRun={() => runStep("vlm", PipelineApi.runVlm)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="3. Novelization"
            description="Adapt VLM summaries into light-novel style prose chapters with rolling context."
            running={running.novel}
            onRun={() => runStep("novel", PipelineApi.runNovel)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="4. Anchor Extraction"
            description="Extract key anchor events from prose chapters for branching."
            running={running.anchors}
            onRun={() => runStep("anchors", PipelineApi.runAnchors)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="5. Branch Suggestions"
            description="Generate behavioral / bad-end / wildcard branch ideas per anchor."
            running={running.branches}
            onRun={() => runStep("branches", PipelineApi.runBranches)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="6. Character Analysis"
            description="Build character bible from full novel text."
            running={running.characters}
            onRun={() => runStep("characters", PipelineApi.runCharacters)}
          />
        </Grid>
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="7. Scales"
            description="Rate each chapter on action / romance / erotism scales."
            running={running.scales}
            onRun={() => runStep("scales", PipelineApi.runScales)}
          />
        </Grid>

        {/* Mainline continuation */}
        <Grid item xs={12} md={6} lg={4}>
          <StepCard
            title="8. Continue Mainline"
            description="Generate a new mainline JSON chapter using author DNA + anchors + characters."
            running={running.continueMain}
            onRun={() =>
              runStep("continueMain", () => PipelineApi.continueMain(timelinePath || undefined))
            }
          />
        </Grid>

        {/* Branch controls */}
        <Grid item xs={12} md={6} lg={4}>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
              height: "100%",
            }}
          >
            <Typography variant="h6" gutterBottom>
              Branch Tools
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Use a branch_id from branches.json (e.g. <code>ch_005_anchor_b01</code>).
            </Typography>

            <TextField
              label="Branch ID"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              fullWidth
              size="small"
              margin="dense"
            />

            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
              <Button
                variant="contained"
                size="small"
                disabled={running.branchPlan || !branchId}
                onClick={() =>
                  runStep("branchPlan", () => PipelineApi.branchPlan(branchId))
                }
              >
                Plan Branch
              </Button>
              <Button
                variant="outlined"
                size="small"
                disabled={running.branchGenerate || !branchId}
                onClick={() =>
                  runStep("branchGenerate", () => PipelineApi.branchGenerate(branchId))
                }
              >
                Generate Chapter
              </Button>
              <Button
                variant="outlined"
                size="small"
                disabled={running.branchContinue || !branchId}
                onClick={() =>
                  runStep("branchContinue", () => PipelineApi.branchContinue(branchId))
                }
              >
                Continue Timeline
              </Button>
            </Box>
          </Box>
        </Grid>

        {/* Timeline path control */}
        <Grid item xs={12} md={6} lg={4}>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              border: "1px solid",
              borderColor: "divider",
              height: "100%",
            }}
          >
            <Typography variant="h6" gutterBottom>
              Alternate Timeline Path
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Optional: path to an alternate <code>summary.json</code> directory to continue.
            </Typography>
            <TextField
              label="Timeline directory (optional)"
              value={timelinePath}
              onChange={(e) => setTimelinePath(e.target.value)}
              fullWidth
              size="small"
              margin="dense"
            />
          </Box>
        </Grid>
      </Grid>

      {/* Logs */}
      <LogsPanel logs={logs} />

      {/* Error Snackbar */}
      <Snackbar
        open={Boolean(error)}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        {error && <Alert severity="error">{error}</Alert>}
      </Snackbar>
    </Box>
  );
};

export default PipelineDashboard;
