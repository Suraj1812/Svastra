import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

import { getJsonWithSession, postJsonWithSession } from "../../../shared/api/client";
import type { ClinicalAlert } from "../../../shared/types/auth";

export function ProviderAlerts({ sessionToken }: { sessionToken: string }) {
  const [alerts, setAlerts] = useState<ClinicalAlert[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClinicalAlert | null>(null);
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

  async function resolve(alert: ClinicalAlert) {
    setWorking(alert.alert_id);
    try {
      await postJsonWithSession(`/provider/alerts/${alert.alert_id}/resolve`, { confirmed: true }, sessionToken);
      await load();
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : "Alert could not be resolved");
    } finally {
      setWorking(null);
    }
  }

  function diagnosisText(alert: ClinicalAlert) {
    const diagnosis = alert.detail.diagnosis || alert.care_plan?.diagnosis;
    if (!diagnosis) return "Not recorded";
    if (typeof diagnosis === "string") return diagnosis;
    return diagnosis.term || "Not recorded";
  }

  function formatDate(value?: string | null) {
    if (!value) return "Not recorded";
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }

  const openAlerts = alerts.filter((item) => item.status === "NEW" || item.status === "OPEN");
  const acknowledgedAlerts = alerts.filter((item) => item.status === "ACKNOWLEDGED");
  const resolvedAlerts = alerts.filter((item) => item.status === "RESOLVED");

  function renderAlertCard(item: ClinicalAlert) {
    const isOpen = item.status === "NEW" || item.status === "OPEN";
    return (
      <Grid key={item.alert_id} size={{ xs: 12, md: 6 }}>
        <Paper variant="outlined" sx={{ p: 2.25, height: "100%", borderColor: isOpen ? "error.light" : "divider" }}>
          <Stack spacing={1.5}>
            <Stack direction="row" justifyContent="space-between" gap={1}>
              <Typography variant="h3">⚠ {item.display.title}</Typography>
              <Chip size="small" color={isOpen ? "error" : item.status === "ACKNOWLEDGED" ? "warning" : "success"} label={item.display.status_label} />
            </Stack>
            <Typography color="text.secondary">{item.patient.full_name}</Typography>
            {item.display.recorded_value ? (
              <Stack spacing={0.25}>
                <Typography variant="caption" color="text.secondary">Recorded Value</Typography>
                <Typography variant="h3">{item.display.recorded_value}</Typography>
              </Stack>
            ) : null}
            <Typography>{item.message}</Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button variant="outlined" onClick={() => setDetail(item)}>Details</Button>
              {isOpen ? (
                <Button variant="contained" onClick={() => void acknowledge(item)} disabled={working === item.alert_id}>
                  Acknowledge
                </Button>
              ) : null}
              {item.status === "ACKNOWLEDGED" ? (
                <Button variant="contained" color="success" onClick={() => void resolve(item)} disabled={working === item.alert_id}>
                  Resolve
                </Button>
              ) : null}
            </Stack>
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
            <Typography variant="caption" color="text.secondary">Acknowledged Alerts</Typography>
            <Typography variant="h2">{acknowledgedAlerts.length}</Typography>
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

      {acknowledgedAlerts.length ? (
        <Stack spacing={1.5}>
          <Typography variant="h3">Acknowledged Alerts</Typography>
          <Grid container spacing={2}>{acknowledgedAlerts.map(renderAlertCard)}</Grid>
        </Stack>
      ) : null}

      {resolvedAlerts.length ? (
        <Stack spacing={1.5}>
          <Typography variant="h3">Resolved Alerts</Typography>
          <Grid container spacing={2}>{resolvedAlerts.map(renderAlertCard)}</Grid>
        </Stack>
      ) : null}

      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Alert Details</DialogTitle>
        <DialogContent>
          {detail ? (
            <Grid container spacing={2} sx={{ pt: 0.5 }}>
              {[
                ["Patient", detail.detail.patient],
                ["Diagnosis", diagnosisText(detail)],
                ["Measurement", detail.detail.measurement],
                ["Recorded Value", detail.detail.recorded_value || "Not recorded"],
                ["Time Recorded", formatDate(detail.detail.time_recorded)],
                ["Rule Triggered", detail.detail.rule_triggered.replaceAll("_", " ")],
                ["Alert Status", detail.display.status_label],
              ].map(([label, value]) => (
                <Grid key={label} size={{ xs: 12, sm: 6 }}>
                  <Typography variant="caption" color="text.secondary">{label}</Typography>
                  <Typography sx={{ mt: 0.25 }}>{value}</Typography>
                </Grid>
              ))}
            </Grid>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetail(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
