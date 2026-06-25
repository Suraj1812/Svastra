import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
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
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import RefreshIcon from "@mui/icons-material/Refresh";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import { getJsonWithSession } from "../../../shared/api/client";
import type {
  EventDeliveryStatus,
  EventMonitorDetail,
  EventMonitorItem,
  EventMonitorPage,
  EventMonitorSummary,
  RelationshipListResult,
  Role,
} from "../../../shared/types/auth";

type EventMonitorProps = {
  role: Role;
  sessionToken: string;
  userId: number;
};

const eventTypes = [
  "consent.request",
  "consent.grant",
  "consent.reject",
  "consent.revoke",
  "relationship.created",
  "relationship.deactivated",
  "schedule.generate",
  "advisory.publish",
  "task.generate",
  "response.log",
  "attachment.upload",
  "alert.trigger",
  "alert.acknowledge",
  "alert.resolve",
  "message.send",
] as const;

const deliveryStatuses: EventDeliveryStatus[] = [
  "pending",
  "sent",
  "acknowledged",
  "failed",
  "untracked",
];

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function statusColor(status: EventDeliveryStatus): "default" | "info" | "success" | "error" | "warning" {
  if (status === "acknowledged") return "success";
  if (status === "failed" || status === "untracked") return "error";
  if (status === "pending") return "warning";
  return "info";
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replaceAll(".", " · ");
}

export function EventMonitor({ role, sessionToken, userId }: EventMonitorProps) {
  const [relationships, setRelationships] = useState<RelationshipListResult["relationships"]>([]);
  const [patientId, setPatientId] = useState(role === "patient" ? String(userId) : "");
  const [eventType, setEventType] = useState("");
  const [deliveryStatus, setDeliveryStatus] = useState("");
  const [eventIdPrefix, setEventIdPrefix] = useState("");
  const [effectiveEventIdPrefix, setEffectiveEventIdPrefix] = useState("");
  const [summary, setSummary] = useState<EventMonitorSummary | null>(null);
  const [events, setEvents] = useState<EventMonitorItem[]>([]);
  const [page, setPage] = useState<EventMonitorPage["page"] | null>(null);
  const [detail, setDetail] = useState<EventMonitorDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [scopeLoading, setScopeLoading] = useState(role !== "patient");
  const [loadingMore, setLoadingMore] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const requestSequence = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      requestSequence.current += 1;
    };
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const trimmed = eventIdPrefix.trim();
      setEffectiveEventIdPrefix(trimmed.length >= 3 ? trimmed : "");
    }, 350);
    return () => window.clearTimeout(timer);
  }, [eventIdPrefix]);

  useEffect(() => {
    if (role === "patient") {
      setPatientId(String(userId));
      setRelationships([]);
      setScopeLoading(false);
      return;
    }
    let active = true;
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
          setError(loadError instanceof Error ? loadError.message : "Linked patients could not be loaded");
        }
      })
      .finally(() => {
        if (active) setScopeLoading(false);
      });
    return () => {
      active = false;
    };
  }, [role, sessionToken, userId]);

  const buildParams = useCallback((cursor?: string) => {
    const params = new URLSearchParams({ patient_id: patientId, limit: "25" });
    if (eventType) params.set("event_type", eventType);
    if (deliveryStatus) params.set("delivery_status", deliveryStatus);
    if (effectiveEventIdPrefix) params.set("event_id_prefix", effectiveEventIdPrefix);
    if (cursor) params.set("cursor", cursor);
    return params;
  }, [deliveryStatus, effectiveEventIdPrefix, eventType, patientId]);

  const loadMonitor = useCallback(async (append = false, cursor?: string) => {
    if (!patientId) {
      setLoading(false);
      setSummary(null);
      setEvents([]);
      return;
    }
    const sequence = ++requestSequence.current;
    append ? setLoadingMore(true) : setLoading(true);
    setError(null);
    try {
      const params = buildParams(cursor);
      const summaryParams = new URLSearchParams(params);
      summaryParams.delete("limit");
      summaryParams.delete("cursor");
      const [summaryResult, pageResult] = await Promise.all([
        getJsonWithSession<EventMonitorSummary>(
          `/postoffice/monitor/summary?${summaryParams.toString()}`,
          sessionToken,
        ),
        getJsonWithSession<EventMonitorPage>(
          `/postoffice/monitor/events?${params.toString()}`,
          sessionToken,
        ),
      ]);
      if (!mounted.current || sequence !== requestSequence.current) return;
      setSummary(summaryResult);
      setEvents((current) => append ? [...current, ...pageResult.events] : pageResult.events);
      setPage(pageResult.page);
      setRefreshedAt(new Date().toISOString());
    } catch (loadError) {
      if (mounted.current && sequence === requestSequence.current) {
        setError(loadError instanceof Error ? loadError.message : "Event monitor could not be loaded");
      }
    } finally {
      if (mounted.current && sequence === requestSequence.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }, [buildParams, patientId, sessionToken]);

  useEffect(() => {
    void loadMonitor();
  }, [loadMonitor]);

  async function openDetail(eventId: string) {
    setDetailLoading(true);
    setError(null);
    try {
      const result = await getJsonWithSession<EventMonitorDetail>(
        `/postoffice/monitor/events/${encodeURIComponent(eventId)}?patient_id=${encodeURIComponent(patientId)}`,
        sessionToken,
      );
      setDetail(result);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Event detail could not be loaded");
    } finally {
      setDetailLoading(false);
    }
  }

  const openQueue = summary
    ? summary.delivery_counts.pending + summary.delivery_counts.sent + summary.delivery_counts.failed
    : 0;

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
        <Stack spacing={0.5}>
          <Typography variant="h2">API Event Monitor</Typography>
          <Typography color="text.secondary">
            Role-scoped PostOffice delivery, acknowledgement, integrity and queue visibility.
          </Typography>
          {refreshedAt ? (
            <Typography variant="caption" color="text.secondary">Last refreshed {formatDate(refreshedAt)}</Typography>
          ) : null}
        </Stack>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => void loadMonitor()}
          disabled={loading || !patientId}
          sx={{ alignSelf: { xs: "stretch", md: "flex-start" } }}
        >
          Refresh
        </Button>
      </Stack>

      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {role !== "patient" && relationships.length === 0 && !scopeLoading ? (
        <Alert severity="warning">An active consent-backed patient relationship is required to view events.</Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}>
        <Grid container spacing={2}>
          {role !== "patient" ? (
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField select fullWidth label="Linked patient" value={patientId} onChange={(event) => setPatientId(event.target.value)}>
                {relationships.map((relationship) => (
                  <MenuItem key={relationship.id} value={relationship.patient.id}>{relationship.patient.full_name}</MenuItem>
                ))}
              </TextField>
            </Grid>
          ) : null}
          <Grid size={{ xs: 12, sm: 6, md: role === "patient" ? 4 : 3 }}>
            <TextField select fullWidth label="Event type" value={eventType} onChange={(event) => setEventType(event.target.value)}>
              <MenuItem value="">All event types</MenuItem>
              {eventTypes.map((item) => <MenuItem key={item} value={item}>{humanize(item)}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: role === "patient" ? 4 : 3 }}>
            <TextField select fullWidth label="Delivery status" value={deliveryStatus} onChange={(event) => setDeliveryStatus(event.target.value)}>
              <MenuItem value="">All statuses</MenuItem>
              {deliveryStatuses.map((item) => <MenuItem key={item} value={item}>{humanize(item)}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: role === "patient" ? 4 : 3 }}>
            <TextField
              fullWidth
              label="Event ID prefix"
              value={eventIdPrefix}
              onChange={(event) => setEventIdPrefix(event.target.value)}
              helperText="Enter at least 3 characters"
              inputProps={{ maxLength: 64 }}
            />
          </Grid>
        </Grid>
      </Paper>

      {loading ? (
        <Grid container spacing={2} aria-label="Loading event monitor">
          {[1, 2, 3, 4].map((item) => (
            <Grid key={item} size={{ xs: 12, sm: 6, lg: 3 }}><Skeleton variant="rounded" height={112} /></Grid>
          ))}
        </Grid>
      ) : summary ? (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}><Paper variant="outlined" sx={{ p: 2.25 }}><Typography variant="caption" color="text.secondary">Total events</Typography><Typography variant="h2">{summary.total_events}</Typography></Paper></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}><Paper variant="outlined" sx={{ p: 2.25 }}><Typography variant="caption" color="text.secondary">Acknowledged</Typography><Typography variant="h2">{summary.acknowledgement_rate}%</Typography></Paper></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}><Paper variant="outlined" sx={{ p: 2.25 }}><Typography variant="caption" color="text.secondary">Open queue</Typography><Typography variant="h2">{openQueue}</Typography></Paper></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <Paper variant="outlined" sx={{ p: 2.25 }}>
              <Typography variant="caption" color="text.secondary">System health</Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                {summary.health === "healthy" ? <CheckCircleOutlineIcon color="success" /> : <ErrorOutlineIcon color="warning" />}
                <Typography variant="h3" sx={{ textTransform: "capitalize" }}>{summary.health}</Typography>
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      ) : null}

      {summary?.anomaly_count ? (
        <Alert severity="warning">{summary.anomaly_count} delivery or integrity anomaly signal(s) need review.</Alert>
      ) : null}

      <Stack spacing={1.5}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
          <Typography variant="h3">Event stream</Typography>
          <Typography color="text.secondary">Newest first · keyset paginated</Typography>
        </Stack>
        {!loading && events.length === 0 ? (
          <Alert severity="info">No events match the selected filters.</Alert>
        ) : events.map((item) => (
          <Paper key={item.event_id} variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}>
            <Stack spacing={1.5}>
              <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={1.5}>
                <Stack spacing={0.5} sx={{ minWidth: 0 }}>
                  <Typography variant="h3">{humanize(item.event_type)}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontFamily: "monospace", overflowWrap: "anywhere" }}>{item.event_id}</Typography>
                </Stack>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip size="small" color={statusColor(item.delivery_status)} label={humanize(item.delivery_status)} />
                  {item.payload_preview.execution_status === "pending" ? <Chip size="small" color="info" variant="outlined" label="Execution: Pending" /> : null}
                  <Chip size="small" color={item.integrity_status === "verified" ? "success" : "warning"} variant="outlined" label={`Integrity: ${humanize(item.integrity_status)}`} />
                </Stack>
              </Stack>
              <Divider />
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Occurred</Typography><Typography>{formatDate(item.occurred_at)}</Typography></Grid>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Route</Typography><Typography>{item.source} → {item.target}</Typography></Grid>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Attempts</Typography><Typography>{item.retry_count}</Typography></Grid>
              </Grid>
              {item.anomalies.length ? <Alert severity="warning">{item.anomalies.join(", ")}</Alert> : null}
              <Button
                size="small"
                data-testid={`event-detail-${item.event_id}`}
                startIcon={<VisibilityOutlinedIcon />}
                onClick={() => void openDetail(item.event_id)}
                disabled={detailLoading}
                sx={{ alignSelf: "flex-start" }}
              >
                View lifecycle and payload
              </Button>
            </Stack>
          </Paper>
        ))}
        {page?.has_more ? (
          <Button variant="outlined" onClick={() => void loadMonitor(true, page.next_cursor || undefined)} disabled={loadingMore}>
            {loadingMore ? "Loading…" : "Load older events"}
          </Button>
        ) : null}
      </Stack>

      <Dialog open={Boolean(detail)} onClose={() => setDetail(null)} maxWidth="md" fullWidth>
        <DialogTitle>Event lifecycle</DialogTitle>
        <DialogContent>
          {detail ? (
            <Stack spacing={2.5} sx={{ pt: 1 }}>
              <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
                <Box><Typography variant="h3">{humanize(detail.event_type)}</Typography><Typography color="text.secondary" sx={{ fontFamily: "monospace", overflowWrap: "anywhere" }}>{detail.event_id}</Typography></Box>
                <Chip color={statusColor(detail.delivery_status)} label={humanize(detail.delivery_status)} />
              </Stack>
              <Grid container spacing={1.5}>
                {detail.lifecycle.map((step) => (
                  <Grid key={`${step.state}-${step.timestamp}`} size={{ xs: 12, sm: 6 }}>
                    <Paper variant="outlined" sx={{ p: 1.75 }}><Typography variant="caption" color="text.secondary">{humanize(step.state)}</Typography><Typography>{formatDate(step.timestamp)}</Typography></Paper>
                  </Grid>
                ))}
              </Grid>
              {detail.redacted_fields.length ? <Alert severity="info">Privacy redaction applied to: {detail.redacted_fields.join(", ")}</Alert> : null}
              <Box>
                <Typography variant="h3" gutterBottom>Validated payload</Typography>
                <Box component="pre" sx={{ m: 0, p: 2, bgcolor: "grey.950", color: "black", borderRadius: 2, overflow: "auto", fontSize: 13, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
                  {JSON.stringify(detail.payload, null, 2)}
                </Box>
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace", overflowWrap: "anywhere" }}>SHA-256: {detail.payload_sha256}</Typography>
            </Stack>
          ) : null}
        </DialogContent>
        <DialogActions><Button onClick={() => setDetail(null)}>Close</Button></DialogActions>
      </Dialog>
    </Stack>
  );
}
