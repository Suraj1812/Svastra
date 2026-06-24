import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Chip, Grid, Paper, Stack, Typography } from "@mui/material";

import { getJsonWithSession, postJsonWithSession } from "../../../shared/api/client";
import type { ClinicalAlert } from "../../../shared/types/auth";

export function ProviderAlerts({ sessionToken }: { sessionToken: string }) {
  const [alerts, setAlerts] = useState<ClinicalAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const load = useCallback(async () => {
    try {
      const result = await getJsonWithSession<{ alerts: ClinicalAlert[] }>("/provider/alerts", sessionToken);
      if (mounted.current) setAlerts(result.alerts);
    } catch (loadError) {
      if (mounted.current) setError(loadError instanceof Error ? loadError.message : "Alerts could not be loaded");
    }
  }, [sessionToken]);

  useEffect(() => { void load(); }, [load]);

  async function acknowledge(alert: ClinicalAlert) {
    setWorking(alert.alert_id);
    try {
      await postJsonWithSession(`/provider/alerts/${alert.alert_id}/acknowledge`, { confirmed: true }, sessionToken);
      await load();
    } catch (ackError) {
      setError(ackError instanceof Error ? ackError.message : "Alert could not be acknowledged");
    } finally {
      setWorking(null);
    }
  }

  const openAlerts = alerts.filter((item) => item.status === "OPEN");
  const resolvedAlerts = alerts.filter((item) => item.status !== "OPEN");

  function renderAlertCard(item: ClinicalAlert) {
    return (
      <Grid key={item.alert_id} size={{ xs: 12, md: 6 }}>
        <Paper variant="outlined" sx={{ p: 2.25, height: "100%", borderColor: item.status === "OPEN" ? "error.light" : "divider" }}>
          <Stack spacing={1.5}>
            <Stack direction="row" justifyContent="space-between" gap={1}>
              <Typography variant="h3">⚠ {item.display.title}</Typography>
              <Chip size="small" color={item.status === "OPEN" ? "error" : "default"} label={item.display.status_label} />
            </Stack>
            <Typography color="text.secondary">{item.patient.full_name}</Typography>
            {item.display.recorded_value ? (
              <Stack spacing={0.25}>
                <Typography variant="caption" color="text.secondary">Recorded Value</Typography>
                <Typography variant="h3">{item.display.recorded_value}</Typography>
              </Stack>
            ) : null}
            <Typography>{item.message}</Typography>
            {item.status === "OPEN" ? (
              <Button variant="contained" onClick={() => void acknowledge(item)} disabled={working === item.alert_id}>
                Mark reviewed
              </Button>
            ) : null}
          </Stack>
        </Paper>
      </Grid>
    );
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">Alerts</Typography>
        <Typography color="text.secondary">Open and reviewed clinical alerts.</Typography>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Alerts</Typography>
            <Typography variant="h2">{alerts.length}</Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Open Alerts</Typography>
            <Typography variant="h2">{openAlerts.length}</Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="caption" color="text.secondary">Resolved Alerts</Typography>
            <Typography variant="h2">{resolvedAlerts.length}</Typography>
          </Paper>
        </Grid>
      </Grid>

      {alerts.length === 0 ? <Alert severity="success">No alerts.</Alert> : null}

      {openAlerts.length ? (
        <Stack spacing={1.5}>
          <Typography variant="h3">Open Alerts</Typography>
          <Grid container spacing={2}>{openAlerts.map(renderAlertCard)}</Grid>
        </Stack>
      ) : null}

      {resolvedAlerts.length ? (
        <Stack spacing={1.5}>
          <Typography variant="h3">Resolved Alerts</Typography>
          <Grid container spacing={2}>{resolvedAlerts.map(renderAlertCard)}</Grid>
        </Stack>
      ) : null}
    </Stack>
  );
}
