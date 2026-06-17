import { useEffect, useState } from "react";
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
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LockResetIcon from "@mui/icons-material/LockReset";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import {
  getJsonWithSession,
  postJsonWithSession,
  putJsonWithSession,
} from "../../../shared/api/client";
import { SubmitButton } from "../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../shared/components/formHelpers";
import type {
  ConsentOtpResult,
  ConsentStatusResult,
  RelationshipConsentSummary,
} from "../../../shared/types/auth";
import {
  consentAliasSchema,
  consentDecisionSchema,
  type ConsentAliasValues,
  type ConsentDecisionValues,
} from "../../../shared/validation/authSchemas";

type ConsentWorkspaceProps = {
  consentStatus: ConsentStatusResult | null;
  activeConsents: RelationshipConsentSummary[];
  pendingRequests: RelationshipConsentSummary[];
  inactiveConsents: RelationshipConsentSummary[];
  sessionToken: string;
  onRefresh: () => void;
};

type ConsentBucket = "active" | "pending" | "inactive";
type ConsentAction = "grant" | "reject" | "revoke";

type PendingDecision = {
  action: ConsentAction;
  consent: RelationshipConsentSummary;
};

const actionLabel: Record<ConsentAction, string> = {
  grant: "Grant",
  reject: "Reject",
  revoke: "Revoke",
};

function formatDate(value?: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function formatConsentType(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusColor(status: RelationshipConsentSummary["status"]) {
  if (status === "ACTIVE") return "success";
  if (status === "PENDING") return "warning";
  return "default";
}

function detailRows(consent: RelationshipConsentSummary) {
  return [
    ["Registered Full Name", consent.registered_full_name],
    ["Patient Alias", consent.alias],
    ["Mobile Number", consent.mobile_number || "Hidden"],
    ["Role", consent.role],
    ["Consent Type", formatConsentType(consent.consent_type)],
    ["Status", consent.status],
    ["Requested", formatDate(consent.relevant_dates.requested_at)],
    ["Granted", formatDate(consent.relevant_dates.granted_at)],
    ["Rejected", formatDate(consent.relevant_dates.rejected_at)],
    ["Revoked", formatDate(consent.relevant_dates.revoked_at)],
    ["Expired", formatDate(consent.relevant_dates.expired_at)],
  ];
}

function ConsentDecisionDialog({
  decision,
  otpSending,
  loading,
  error,
  otpMessage,
  onClose,
  onSubmit,
}: {
  decision: PendingDecision | null;
  otpSending: boolean;
  loading: boolean;
  error: string | null;
  otpMessage: string | null;
  onClose: () => void;
  onSubmit: (values: ConsentDecisionValues) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ConsentDecisionValues>({
    resolver: zodResolver(consentDecisionSchema),
    defaultValues: { otp: "" },
  });

  useEffect(() => {
    reset({ otp: "" });
  }, [decision?.action, decision?.consent.id, reset]);

  const title = decision ? `${actionLabel[decision.action]} Consent` : "Consent Decision";

  return (
    <Dialog open={Boolean(decision)} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          id="consent-decision-form"
          spacing={2.5}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
        >
          {otpMessage ? <Alert severity="success">{otpMessage}</Alert> : null}
          {otpSending ? <Alert severity="info">Sending OTP...</Alert> : null}
          <TextField
            label="OTP"
            autoComplete="one-time-code"
            inputMode="numeric"
            error={Boolean(errors.otp)}
            helperText={fieldHelperText(errors.otp?.message)}
            disabled={otpSending || loading}
            {...register("otp")}
          />
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <SubmitButton
          form="consent-decision-form"
          loading={loading}
          disabled={otpSending}
          icon={decision?.action === "grant" ? <CheckCircleIcon /> : <CloseIcon />}
          sx={{ width: "auto" }}
        >
          Confirm
        </SubmitButton>
      </DialogActions>
    </Dialog>
  );
}

function AliasDialog({
  consent,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  consent: RelationshipConsentSummary | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (values: ConsentAliasValues) => void;
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ConsentAliasValues>({
    resolver: zodResolver(consentAliasSchema),
    defaultValues: { alias: "" },
  });

  useEffect(() => {
    reset({ alias: consent?.alias || "" });
  }, [consent?.alias, consent?.id, reset]);

  return (
    <Dialog open={Boolean(consent)} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Edit Alias</DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          id="consent-alias-form"
          spacing={2.5}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
        >
          <TextField
            label="Alias"
            error={Boolean(errors.alias)}
            helperText={fieldHelperText(errors.alias?.message)}
            disabled={loading}
            {...register("alias")}
          />
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          Cancel
        </Button>
        <SubmitButton
          form="consent-alias-form"
          loading={loading}
          icon={<EditOutlinedIcon />}
          sx={{ width: "auto" }}
        >
          Save
        </SubmitButton>
      </DialogActions>
    </Dialog>
  );
}

function DetailsDialog({
  consent,
  onClose,
}: {
  consent: RelationshipConsentSummary | null;
  onClose: () => void;
}) {
  return (
    <Dialog open={Boolean(consent)} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Consent Details</DialogTitle>
      <DialogContent>
        {consent ? (
          <Grid container spacing={2} sx={{ pt: 0.5 }}>
            {detailRows(consent).map(([label, value]) => (
              <Grid key={label} size={{ xs: 12, sm: 6 }}>
                <Typography variant="caption" color="text.secondary">
                  {label}
                </Typography>
                <Typography sx={{ mt: 0.5 }}>{value}</Typography>
              </Grid>
            ))}
          </Grid>
        ) : null}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

function EmptyConsentList({ label }: { label: string }) {
  return <Alert severity="info">No {label.toLowerCase()}.</Alert>;
}

function ConsentRow({
  consent,
  bucket,
  onView,
  onAlias,
  onDecision,
}: {
  consent: RelationshipConsentSummary;
  bucket: ConsentBucket;
  onView: (consent: RelationshipConsentSummary) => void;
  onAlias: (consent: RelationshipConsentSummary) => void;
  onDecision: (action: ConsentAction, consent: RelationshipConsentSummary) => void;
}) {
  const primaryDate =
    bucket === "active"
      ? consent.granted_date
      : bucket === "pending"
        ? consent.request_date
        : consent.decision_date;
  const dateLabel =
    bucket === "active" ? "Granted Date" : bucket === "pending" ? "Request Date" : "Decision Date";

  return (
    <Box
      sx={{
        py: 2,
        borderTop: "1px solid",
        borderColor: "divider",
        "&:first-of-type": { borderTop: 0 },
      }}
    >
      <Grid container spacing={2} alignItems="center">
        <Grid size={{ xs: 12, md: 2.4 }}>
          <Typography variant="caption" color="text.secondary">
            Alias
          </Typography>
          <Typography sx={{ mt: 0.5 }}>{consent.alias}</Typography>
        </Grid>
        <Grid size={{ xs: 6, md: 1.6 }}>
          <Typography variant="caption" color="text.secondary">
            Role
          </Typography>
          <Typography sx={{ mt: 0.5 }}>{consent.role}</Typography>
        </Grid>
        <Grid size={{ xs: 6, md: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Consent Type
          </Typography>
          <Typography sx={{ mt: 0.5 }}>{formatConsentType(consent.consent_type)}</Typography>
        </Grid>
        <Grid size={{ xs: 6, md: 1.8 }}>
          <Typography variant="caption" color="text.secondary">
            {dateLabel}
          </Typography>
          <Typography sx={{ mt: 0.5 }}>{formatDate(primaryDate)}</Typography>
        </Grid>
        <Grid size={{ xs: 6, md: 1.2 }}>
          <Typography variant="caption" color="text.secondary">
            Status
          </Typography>
          <Box sx={{ mt: 0.5 }}>
            <Chip size="small" color={statusColor(consent.status)} label={consent.status} />
          </Box>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Stack direction="row" spacing={1} justifyContent={{ md: "flex-end" }} flexWrap="wrap">
            <Button size="small" startIcon={<InfoOutlinedIcon />} onClick={() => onView(consent)}>
              View Details
            </Button>
            {bucket !== "inactive" ? (
              <Button size="small" startIcon={<EditOutlinedIcon />} onClick={() => onAlias(consent)}>
                Edit Alias
              </Button>
            ) : null}
            {bucket === "pending" ? (
              <>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<CheckCircleIcon />}
                  onClick={() => onDecision("grant", consent)}
                >
                  Grant
                </Button>
                <Button
                  size="small"
                  color="error"
                  startIcon={<CloseIcon />}
                  onClick={() => onDecision("reject", consent)}
                >
                  Reject
                </Button>
              </>
            ) : null}
            {bucket === "active" ? (
              <Button
                size="small"
                color="error"
                startIcon={<RemoveCircleOutlineIcon />}
                onClick={() => onDecision("revoke", consent)}
              >
                Revoke
              </Button>
            ) : null}
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

export function ConsentWorkspace({
  consentStatus,
  activeConsents,
  pendingRequests,
  inactiveConsents,
  sessionToken,
  onRefresh,
}: ConsentWorkspaceProps) {
  const [bucket, setBucket] = useState<ConsentBucket>("active");
  const [decision, setDecision] = useState<PendingDecision | null>(null);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [otpSending, setOtpSending] = useState(false);
  const [otpMessage, setOtpMessage] = useState<string | null>(null);
  const [details, setDetails] = useState<RelationshipConsentSummary | null>(null);
  const [detailsError, setDetailsError] = useState<string | null>(null);
  const [aliasTarget, setAliasTarget] = useState<RelationshipConsentSummary | null>(null);
  const [aliasLoading, setAliasLoading] = useState(false);
  const [aliasError, setAliasError] = useState<string | null>(null);

  const bucketItems =
    bucket === "active" ? activeConsents : bucket === "pending" ? pendingRequests : inactiveConsents;

  async function openDecision(action: ConsentAction, consent: RelationshipConsentSummary) {
    setDecision({ action, consent });
    setDecisionError(null);
    setOtpMessage(null);
    setOtpSending(true);
    try {
      const result = await postJsonWithSession<ConsentOtpResult>(
        "/consent/send-otp",
        { consent_id: consent.id, action },
        sessionToken,
      );
      setOtpMessage(result.otp_sent ? "OTP sent" : null);
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "OTP could not be sent");
    } finally {
      setOtpSending(false);
    }
  }

  async function submitDecision(values: ConsentDecisionValues) {
    if (!decision) return;
    setDecisionLoading(true);
    setDecisionError(null);
    try {
      await postJsonWithSession<ConsentOtpResult>(
        "/consent/verify-otp",
        {
          consent_id: decision.consent.id,
          action: decision.action,
          otp: values.otp,
        },
        sessionToken,
      );
      await postJsonWithSession<RelationshipConsentSummary>(
        `/consent/request/${decision.consent.id}/${decision.action}`,
        values,
        sessionToken,
      );
      setDecision(null);
      setOtpMessage(null);
      onRefresh();
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Consent decision failed");
    } finally {
      setDecisionLoading(false);
    }
  }

  async function viewDetails(consent: RelationshipConsentSummary) {
    setDetailsError(null);
    try {
      const result = await getJsonWithSession<RelationshipConsentSummary>(
        `/consent/${consent.id}`,
        sessionToken,
      );
      setDetails(result);
    } catch (error) {
      setDetailsError(error instanceof Error ? error.message : "Consent details failed to load");
    }
  }

  async function submitAlias(values: ConsentAliasValues) {
    if (!aliasTarget) return;
    setAliasLoading(true);
    setAliasError(null);
    try {
      await putJsonWithSession<RelationshipConsentSummary>(
        `/consent/${aliasTarget.id}/alias`,
        values,
        sessionToken,
      );
      setAliasTarget(null);
      onRefresh();
    } catch (error) {
      setAliasError(error instanceof Error ? error.message : "Alias could not be saved");
    } finally {
      setAliasLoading(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="caption" color="text.secondary">
              Consent Version
            </Typography>
            <Typography variant="h3" sx={{ mt: 0.75 }}>
              {consentStatus?.consent_version || "Not recorded"}
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="caption" color="text.secondary">
              Accepted Date
            </Typography>
            <Typography variant="h3" sx={{ mt: 0.75 }}>
              {formatDate(consentStatus?.accepted_at)}
            </Typography>
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper variant="outlined" sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="caption" color="text.secondary">
              Consent Status
            </Typography>
            <Box sx={{ mt: 1 }}>
              <Chip
                color={consentStatus?.accepted ? "success" : "warning"}
                label={consentStatus?.consent_status || "Pending"}
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {detailsError ? <Alert severity="error">{detailsError}</Alert> : null}

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Stack spacing={0}>
          <Box sx={{ px: { xs: 2, md: 3 }, pt: 2.5 }}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
              <Typography variant="h2">Consent Admin</Typography>
              <LockResetIcon color="primary" />
            </Stack>
            <Tabs
              value={bucket}
              onChange={(_, value) => setBucket(value)}
              variant="scrollable"
              scrollButtons="auto"
              aria-label="Consent Admin sections"
              sx={{ mt: 1.5 }}
            >
              <Tab value="active" label="Active Consents" />
              <Tab value="pending" label="Pending Requests" />
              <Tab value="inactive" label="Inactive Consents" />
            </Tabs>
          </Box>
          <Divider />
          <Box sx={{ px: { xs: 2, md: 3 }, py: 1 }}>
            {bucketItems.length === 0 ? (
              <Box sx={{ py: 2 }}>
                <EmptyConsentList
                  label={
                    bucket === "active"
                      ? "active consents"
                      : bucket === "pending"
                        ? "pending requests"
                        : "inactive consents"
                  }
                />
              </Box>
            ) : (
              bucketItems.map((consent) => (
                <ConsentRow
                  key={consent.id}
                  consent={consent}
                  bucket={bucket}
                  onView={viewDetails}
                  onAlias={(target) => {
                    setAliasError(null);
                    setAliasTarget(target);
                  }}
                  onDecision={openDecision}
                />
              ))
            )}
          </Box>
        </Stack>
      </Paper>

      <ConsentDecisionDialog
        decision={decision}
        otpSending={otpSending}
        loading={decisionLoading}
        error={decisionError}
        otpMessage={otpMessage}
        onClose={() => {
          setDecision(null);
          setDecisionError(null);
          setOtpMessage(null);
        }}
        onSubmit={submitDecision}
      />

      <AliasDialog
        consent={aliasTarget}
        loading={aliasLoading}
        error={aliasError}
        onClose={() => {
          setAliasTarget(null);
          setAliasError(null);
        }}
        onSubmit={submitAlias}
      />

      <DetailsDialog consent={details} onClose={() => setDetails(null)} />
    </Stack>
  );
}
