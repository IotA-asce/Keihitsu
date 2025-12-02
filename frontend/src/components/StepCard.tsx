import React from "react";
import {
  Card,
  CardContent,
  CardActions,
  Button,
  Typography,
  LinearProgress,
} from "@mui/material";

type StepCardProps = {
  title: string;
  description: string;
  running: boolean;
  onRun: () => void;
};

const StepCard: React.FC<StepCardProps> = ({
  title,
  description,
  running,
  onRun,
}) => {
  return (
    <Card variant="outlined" sx={{ minHeight: 160, display: "flex", flexDirection: "column" }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </CardContent>
      {running && <LinearProgress />}
      <CardActions sx={{ justifyContent: "flex-end" }}>
        <Button
          variant="contained"
          disabled={running}
          onClick={onRun}
          size="small"
        >
          {running ? "Running..." : "Run"}
        </Button>
      </CardActions>
    </Card>
  );
};

export default StepCard;
