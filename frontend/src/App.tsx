import React from "react";
import { CssBaseline, Container, AppBar, Toolbar, Typography } from "@mui/material";
import PipelineDashboard from "./components/PipelineDashboard";

const App: React.FC = () => {
  return (
    <>
      <CssBaseline />
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6" component="div">
            Manga Continuation Pipeline
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ mt: 3, mb: 4 }}>
        <PipelineDashboard />
      </Container>
    </>
  );
};

export default App;
