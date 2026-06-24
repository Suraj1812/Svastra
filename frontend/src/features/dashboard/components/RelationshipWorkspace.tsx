import { useCallback, useEffect, useMemo, useState } from "react";
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
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import LinkIcon from "@mui/icons-material/Link";
import LinkOffIcon from "@mui/icons-material/LinkOff";
import SearchIcon from "@mui/icons-material/Search";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import {
  deleteJsonWithSession,
  getJsonWithSession,
  postJsonWithSession,
} from "../../../shared/api/client";
import type {
  HealthcareRelationship,
  LinkablePatientsResult,
  PatientSearchResult,
  PatientStatusSummary,
  ProviderDashboardFeed,
  RelationshipListResult,
  Role,
} from "../../../shared/types/auth";

type Props = {
  role: Role;
  sessionToken: string;
  pendingCount?: number;
};

function formatDate(value?: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function RelationshipWorkspace({ role, sessionToken, pendingCount = 0 }: Props) {
  const [relationships, setRelationships] = useState<HealthcareRelationship[]>([]);
  const [linkable, setLinkable] = useState<LinkablePatientsResult["patients"]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [details, setDetails] = useState<HealthcareRelationship | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<HealthcareRelationship | null>(null);
  const [mobileNumber, setMobileNumber] = useState("");
  const [searchResult, setSearchResult] = useState<PatientSearchResult | null>(null);
  const [patientStatuses, setPatientStatuses] = useState<Record<number, PatientStatusSummary>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (role === "patient") {
        const [providers, caregivers] = await Promise.all([
          getJsonWithSession<RelationshipListResult>("/relationships/providers?status=ALL", sessionToken),
          getJsonWithSession<RelationshipListResult>("/relationships/caregivers?status=ALL", sessionToken),
        ]);
        setRelationships([...providers.relationships, ...caregivers.relationships]);
        setLinkable([]);
        setPatientStatuses({});
      } else {
        const [linked, available, feed] = await Promise.all([
          getJsonWithSession<RelationshipListResult>("/relationships/patients?status=ALL", sessionToken),
          getJsonWithSession<LinkablePatientsResult>("/relationships/linkable", sessionToken),
          role === "provider"
            ? getJsonWithSession<ProviderDashboardFeed>("/provider/dashboard-feed", sessionToken)
            : Promise.resolve<ProviderDashboardFeed>({ active_alerts: [], recent_responses: [], patient_status: [] }),
        ]);
        setRelationships(linked.relationships);
        setLinkable(available.patients);
        setPatientStatuses(
          Object.fromEntries(feed.patient_status.map((item) => [item.patient.id, item])),
        );
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Relationships could not be loaded");
    } finally {
      setLoading(false);
    }
  }, [role, sessionToken]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => {
    const active = relationships.filter((item) => item.relationship_status === "ACTIVE");
    return {
      providers: active.filter((item) => item.linked_user.role === "provider").length,
      caregivers: active.filter((item) => item.linked_user.role === "caregiver").length,
      inactive: relationships.filter((item) => item.relationship_status === "INACTIVE").length,
    };
  }, [relationships]);

  async function viewRelationship(item: HealthcareRelationship) {
    setError(null);
    try {
      const result = await getJsonWithSession<HealthcareRelationship>(
        `/relationships/${item.id}`,
        sessionToken,
      );
      setDetails(result);
    } catch (viewError) {
      setError(viewError instanceof Error ? viewError.message : "Relationship details failed to load");
    }
  }

  async function deactivate() {
    if (!deactivateTarget) return;
    setWorking(true);
    setError(null);
    try {
      await deleteJsonWithSession<HealthcareRelationship>(
        `/relationships/${deactivateTarget.id}`,
        sessionToken,
      );
      setDeactivateTarget(null);
      setDetails(null);
      setNotice("Relationship deactivated. Consent remains unchanged.");
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Relationship could not be deactivated");
    } finally {
      setWorking(false);
    }
  }

  async function createLink(patientId: number) {
    setWorking(true);
    setError(null);
    try {
      const endpoint = role === "provider" ? "/relationships/provider-patient" : "/relationships/patient-caregiver";
      await postJsonWithSession(endpoint, { patient_id: patientId, confirmed: true }, sessionToken);
      setNotice("Healthcare relationship is now active.");
      await load();
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Relationship could not be created");
    } finally {
      setWorking(false);
    }
  }

  async function searchPatient() {
    setWorking(true);
    setError(null);
    setSearchResult(null);
    try {
      const result = await getJsonWithSession<PatientSearchResult>(
        `/relationships/search?mobile_number=${encodeURIComponent(mobileNumber.trim())}`,
        sessionToken,
      );
      setSearchResult(result);
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "Patient could not be found");
    } finally {
      setWorking(false);
    }
  }

  async function requestConsent() {
    if (!searchResult || role === "patient") return;
    setWorking(true);
    setError(null);
    try {
      await postJsonWithSession(
        "/consent/request",
        {
          patient_id: searchResult.patient.id,
          consent_type: role === "provider" ? "provider_access" : "caregiver_access",
        },
        sessionToken,
      );
      setNotice("Access request sent to the patient.");
      setSearchResult({ ...searchResult, consent_status: "PENDING" });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Consent request could not be sent");
    } finally {
      setWorking(false);
    }
  }

  function statusChip(item: HealthcareRelationship) {
    if (role !== "provider") return null;
    const status = patientStatuses[item.patient.id];
    if (!status) return null;
    const color: "success" | "warning" | "error" =
      status.color === "red" ? "error" : status.color === "yellow" ? "warning" : "success";
    return <Chip size="small" color={color} label={status.label} />;
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">Relationship Management</Typography>
        <Typography color="text.secondary">
          Consent gives permission; an active relationship enables operational care access.
        </Typography>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}
      {notice ? <Alert severity="success" onClose={() => setNotice(null)}>{notice}</Alert> : null}

      <Grid container spacing={2}>
        {[
          ["Active Providers", summary.providers],
          ["Active Caregivers", summary.caregivers],
          ["Pending Requests", pendingCount],
          ["Inactive Relationships", summary.inactive],
        ].map(([label, value]) => (
          <Grid key={String(label)} size={{ xs: 6, md: 3 }}>
            <Paper variant="outlined" sx={{ p: 2.25, height: "100%" }}>
              <Typography variant="caption" color="text.secondary">{label}</Typography>
              <Typography variant="h2" sx={{ mt: 0.5 }}>{value}</Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {role !== "patient" ? (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2}>
            <Typography variant="h3">Find a patient</Typography>
            <Typography color="text.secondary">
              Search by the exact registered mobile number, then send a patient-controlled access request.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <TextField
                label="Registered mobile number"
                value={mobileNumber}
                onChange={(event) => setMobileNumber(event.target.value)}
                inputMode="tel"
                fullWidth
              />
              <Button
                variant="outlined"
                startIcon={<SearchIcon />}
                onClick={searchPatient}
                disabled={working || mobileNumber.trim().length < 10}
              >
                Search
              </Button>
            </Stack>
            {searchResult ? (
              <Alert
                severity={searchResult.consent_status === "ACTIVE" ? "success" : "info"}
                action={
                  !searchResult.consent_status ? (
                    <Button color="inherit" size="small" onClick={requestConsent} disabled={working}>
                      Request access
                    </Button>
                  ) : undefined
                }
              >
                {searchResult.patient.full_name} — {searchResult.consent_status || "No access request"}
              </Alert>
            ) : null}
          </Stack>
        </Paper>
      ) : null}

      {linkable.length > 0 ? (
        <Alert severity="info">
          <Stack spacing={1}>
            <Typography>Approved relationships ready to activate</Typography>
            {linkable.map((item) => (
              <Button
                key={item.consent_request_id}
                size="small"
                startIcon={<LinkIcon />}
                onClick={() => createLink(item.patient.id)}
                disabled={working}
              >
                Link {item.patient.full_name}
              </Button>
            ))}
          </Stack>
        </Alert>
      ) : null}

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Box sx={{ px: { xs: 2, md: 3 }, py: 2.5 }}>
          <Typography variant="h3">
            {role === "patient" ? "Linked Providers and Caregivers" : "Linked Patients"}
          </Typography>
        </Box>
        <Divider />
        {loading ? (
          <Box sx={{ p: 3 }}><Typography>Loading relationships…</Typography></Box>
        ) : relationships.length === 0 ? (
          <Box sx={{ p: 3 }}><Alert severity="info">No healthcare relationships yet.</Alert></Box>
        ) : (
          relationships.map((item) => (
            <Box key={item.id} sx={{ px: { xs: 2, md: 3 }, py: 2, borderTop: "1px solid", borderColor: "divider", "&:first-of-type": { borderTop: 0 } }}>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, md: 3 }}>
                  <Typography variant="caption" color="text.secondary">
                    {role === "patient" ? "Alias" : "Patient"}
                  </Typography>
                  <Typography sx={{ mt: 0.5 }}>{item.alias}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="caption" color="text.secondary">Role</Typography>
                  <Typography sx={{ mt: 0.5 }}>{role === "patient" ? item.linked_user.role : "patient"}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="caption" color="text.secondary">Status</Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                    <Chip size="small" color={item.relationship_status === "ACTIVE" ? "success" : "default"} label={item.relationship_status} />
                    {statusChip(item)}
                  </Stack>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>
                  <Typography variant="caption" color="text.secondary">Created</Typography>
                  <Typography sx={{ mt: 0.5 }}>{formatDate(item.relationship_date)}</Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 3 }}>
                  <Stack direction="row" spacing={1} justifyContent={{ md: "flex-end" }}>
                    <Button size="small" startIcon={<VisibilityOutlinedIcon />} onClick={() => viewRelationship(item)}>Details</Button>
                    {item.relationship_status === "ACTIVE" ? (
                      <Button size="small" color="error" startIcon={<LinkOffIcon />} onClick={() => setDeactivateTarget(item)}>Deactivate</Button>
                    ) : null}
                  </Stack>
                </Grid>
              </Grid>
            </Box>
          ))
        )}
      </Paper>

      <Dialog open={Boolean(details)} onClose={() => setDetails(null)} fullWidth maxWidth="sm">
        <DialogTitle>Relationship Details</DialogTitle>
        <DialogContent>
          {details ? (
            <Grid container spacing={2} sx={{ pt: 0.5 }}>
              {[
                ["Full Name", role === "patient" ? details.linked_user.full_name : details.patient.full_name],
                ["Alias", details.alias],
                ["Mobile Number", details.mobile_number || "Hidden"],
                ["Role", role === "patient" ? details.linked_user.role : "patient"],
                ["Relationship Status", details.relationship_status],
                ["Relationship Date", formatDate(details.relationship_date)],
              ].map(([label, value]) => (
                <Grid key={label} size={{ xs: 12, sm: 6 }}>
                  <Typography variant="caption" color="text.secondary">{label}</Typography>
                  <Typography sx={{ mt: 0.5 }}>{value}</Typography>
                </Grid>
              ))}
            </Grid>
          ) : null}
        </DialogContent>
        <DialogActions>
          {details?.relationship_status === "ACTIVE" ? (
            <Button color="error" onClick={() => setDeactivateTarget(details)}>Deactivate</Button>
          ) : null}
          <Button onClick={() => setDetails(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deactivateTarget)} onClose={() => setDeactivateTarget(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Deactivate relationship?</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            Operational access will stop. The patient’s consent record will not be revoked automatically.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeactivateTarget(null)} disabled={working}>Cancel</Button>
          <Button color="error" variant="contained" onClick={deactivate} disabled={working}>Yes, deactivate</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
