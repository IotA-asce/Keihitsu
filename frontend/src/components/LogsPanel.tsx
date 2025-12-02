import React from "react";
import { Paper, Typography } from "@mui/material";

type LogsPanelProps = {
  logs: string[];
};

const LogsPanel: React.FC<LogsPanelProps> = ({ logs }) => {
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, mt: 2, maxHeight: 260, overflow: "auto", bgcolor: "background.paper" }}
    >
      <Typography variant="subtitle1" gutterBottom>
        Activity Log
      </Typography>
      <pre style={{ margin: 0, fontFamily: "monospace", fontSize: 12 }}>
        {logs.join("\n")}
      </pre>
    </Paper>
  );
};

export default LogsPanel;
