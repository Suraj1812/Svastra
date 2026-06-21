import { useEffect, useState } from "react";
import { Alert, Box, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";

import { getJsonWithSession } from "../../../shared/api/client";
import type { PatientAdvisory } from "../../../shared/types/auth";

export function PatientAdvisories({ sessionToken }: { sessionToken: string }) {
  const [advisories, setAdvisories] = useState<PatientAdvisory[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getJsonWithSession<{ advisories: PatientAdvisory[] }>("/me/advisories", sessionToken)
      .then((result) => {
        if (active) setAdvisories(result.advisories);
      })
      .catch((loadError) => {
        if (active) setError(loadError instanceof Error ? loadError.message : "Advisories could not be loaded");
      });
    return () => { active = false; };
  }, [sessionToken]);

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">My Advisories</Typography>
        <Typography color="text.secondary">Read-only care instructions published by your linked provider.</Typography>
      </Stack>
      {error ? <Alert severity="error">{error}</Alert> : null}
      {advisories.length === 0 ? (
        <Alert severity="info">No published advisories yet.</Alert>
      ) : (
        <Grid container spacing={2}>
          {advisories.map((item) => (
            <Grid key={item.id} size={{ xs: 12, md: 6 }}>
              <Paper variant="outlined" sx={{ p: 2.5, height: "100%" }}>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between" gap={2}>
                    <Box><Typography variant="caption" color="text.secondary">{item.care_plan.title}</Typography><Typography variant="h3">{item.advisory}</Typography></Box>
                    <AssignmentTurnedInIcon color="primary" />
                  </Stack>
                  <Typography>{item.instruction}</Typography>
                  <Stack direction="row" spacing={1}>
                    <Chip size="small" label={item.advisory_type} />
                    <Chip size="small" color="success" label={item.status} />
                    <Chip size="small" color={item.execution_status === "pending" ? "info" : item.execution_status === "missed" ? "error" : "success"} variant="outlined" label={item.execution_status.replaceAll("_", " ")} />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    Published {new Intl.DateTimeFormat("en-IN", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(item.published_at))}
                  </Typography>
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
