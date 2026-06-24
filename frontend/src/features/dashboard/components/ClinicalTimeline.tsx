import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  MenuItem,
  Paper,
  Skeleton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import { getJsonWithSession } from "../../../shared/api/client";
import type {
  ClinicalTimelineEvent,
  RelationshipListResult,
  Role,
} from "../../../shared/types/auth";

type Props = {
  role: Role;
  sessionToken: string;
  userId: number;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function readableValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function ClinicalTimeline({ role, sessionToken, userId }: Props) {
  const [relationships, setRelationships] = useState<RelationshipListResult["relationships"]>([]);
  const [patientId, setPatientId] = useState(role === "patient" ? String(userId) : "");
  const [events, setEvents] = useState<ClinicalTimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [scopeLoading, setScopeLoading] = useState(role !== "patient");
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClinicalTimelineEvent | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (role === "patient") {
      setPatientId(String(userId));
      setRelationships([]);
      setScopeLoading(false);
      return;
    }
    let active = true;
    setScopeLoading(true);
    getJsonWithSession<RelationshipListResult>(
      "/relationships/patients?status=ACTIVE",
      sessionToken,
    )
      .then((result) => {
        if (!active) return;
        setRelationships(result.relationships);
        setPatientId((current) => current || String(result.relationships[0]?.patient.id || ""));
      })
      .catch((loadError) => {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Patients could not be loaded");
        }
      })
      .finally(() => {
        if (active) setScopeLoading(false);
      });
    return () => {
      active = false;
    };
  }, [role, sessionToken, userId]);

  const loadTimeline = useCallback(async () => {
    if (!patientId) {
      setEvents([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getJsonWithSession<{ events: ClinicalTimelineEvent[] }>(
        `/postoffice/timeline?patient_id=${encodeURIComponent(patientId)}&limit=50`,
        sessionToken,
      );
      if (mounted.current) setEvents(result.events);
    } catch (loadError) {
      if (mounted.current) {
        setError(loadError instanceof Error ? loadError.message : "Timeline could not be loaded");
      }
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [patientId, sessionToken]);

  useEffect(() => {
    void loadTimeline();
  }, [loadTimeline]);

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
        <Stack spacing={0.5}>
          <Typography variant="h2">Timeline</Typography>
          <Typography color="text.secondary">
            Simple history of care plans, responses, uploads and alerts.
          </Typography>
        </Stack>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => void loadTimeline()}
          disabled={loading || !patientId}
          sx={{ alignSelf: { xs: "stretch", md: "flex-start" } }}
        >
          Refresh
        </Button>
      </Stack>

      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}

      {role !== "patient" ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <TextField
            select
            fullWidth
            label="Patient"
            value={patientId}
            onChange={(event) => setPatientId(event.target.value)}
            disabled={scopeLoading}
          >
            {relationships.map((relationship) => (
              <MenuItem key={relationship.id} value={String(relationship.patient.id)}>
                {relationship.patient.full_name}
                {relationship.mobile_number ? ` · ${relationship.mobile_number}` : ""}
              </MenuItem>
            ))}
          </TextField>
        </Paper>
      ) : null}

      {role !== "patient" && relationships.length === 0 && !scopeLoading ? (
        <Alert severity="warning">No active linked patient found.</Alert>
      ) : null}

      {loading ? (
        <Stack spacing={1.5} aria-label="Loading timeline">
          {[1, 2, 3].map((item) => <Skeleton key={item} variant="rounded" height={92} />)}
        </Stack>
      ) : events.length === 0 ? (
        <Alert severity="info">No timeline events yet.</Alert>
      ) : (
        <Stack spacing={1.5}>
          {events.map((event) => (
            <Paper key={event.event_id} variant="outlined" sx={{ p: 2.25 }}>
              <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
                <Stack spacing={0.5}>
                  <Typography variant="h3">{event.label}</Typography>
                  <Typography color="text.secondary">{formatDate(event.timestamp)}</Typography>
                </Stack>
                <Button
                  size="small"
                  startIcon={<VisibilityOutlinedIcon />}
                  onClick={() => setDetail(event)}
                  sx={{ alignSelf: { xs: "flex-start", sm: "center" } }}
                >
                  Details
                </Button>
              </Stack>
            </Paper>
          ))}
        </Stack>
      )}

      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Event Details</DialogTitle>
        <DialogContent>
          {detail ? (
            <Stack spacing={2.25} sx={{ pt: 0.5 }}>
              <Box>
                <Typography variant="h3">{detail.label}</Typography>
                <Typography color="text.secondary">{formatDate(detail.timestamp)}</Typography>
              </Box>
              <Divider />
              <Grid container spacing={1.5}>
                {[
                  ["Event Type", detail.event_type],
                  ["Timestamp", formatDate(detail.timestamp)],
                  ["Source", detail.source_label],
                  ...Object.entries(detail.details),
                ].map(([label, value]) => (
                  <Grid key={String(label)} size={{ xs: 12, sm: 6 }}>
                    <Typography variant="caption" color="text.secondary">{label}</Typography>
                    <Typography sx={{ mt: 0.25, overflowWrap: "anywhere" }}>{readableValue(value)}</Typography>
                  </Grid>
                ))}
              </Grid>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetail(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
