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

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">Alerts</Typography>
        <Typography color="text.secondary">Items that need review.</Typography>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {alerts.length === 0 ? <Alert severity="success">No alerts.</Alert> : (
        <Grid container spacing={2}>
          {alerts.map((item) => (
            <Grid key={item.alert_id} size={{ xs: 12, md: 6 }}>
              <Paper variant="outlined" sx={{ p: 2.25, height: "100%", borderColor: item.status === "OPEN" ? "error.light" : "divider" }}>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Typography variant="h3">{item.advisory}</Typography>
                    <Chip size="small" color={item.status === "OPEN" ? "error" : "default"} label={item.status === "OPEN" ? "Needs review" : "Reviewed"} />
                  </Stack>
                  <Typography color="text.secondary">{item.patient.full_name}</Typography>
                  <Typography>{item.message}</Typography>
                  {item.status === "OPEN" ? <Button variant="contained" onClick={() => void acknowledge(item)} disabled={working === item.alert_id}>Mark reviewed</Button> : null}
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
