import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { postJsonWithSession } from "../../../shared/api/client";
import { SubmitButton } from "../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../shared/components/formHelpers";
import type {
  ConsentRequestSummary,
  ConsentStatusResult,
} from "../../../shared/types/auth";
import {
  consentDecisionSchema,
  type ConsentDecisionValues,
} from "../../../shared/validation/authSchemas";

type ConsentWorkspaceProps = {
  consentStatus: ConsentStatusResult | null;
  requests: ConsentRequestSummary[];
  sessionToken: string;
  onRefresh: () => void;
};

type PendingDecision = {
  action: "grant" | "reject";
  request: ConsentRequestSummary;
};

function formatDate(value?: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function ConsentDecisionDialog({
  decision,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  decision: PendingDecision | null;
  loading: boolean;
  error: string | null;
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

  const title =
    decision?.action === "grant" ? "Grant Consent Request" : "Reject Consent Request";

  function handleClose() {
    reset();
    onClose();
  }

  return (
    <Dialog open={Boolean(decision)} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack
          component="form"
          id="consent-decision-form"
          spacing={2.5}
          onSubmit={handleSubmit(onSubmit)}
          noValidate
        >
          <Typography color="text.secondary">
            Enter the OTP to confirm this consent decision.
          </Typography>
          <TextField
            label="OTP"
            autoComplete="one-time-code"
            inputMode="numeric"
            error={Boolean(errors.otp)}
            helperText={fieldHelperText(errors.otp?.message)}
            {...register("otp")}
          />
          {error ? <Alert severity="error">{error}</Alert> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <SubmitButton
          form="consent-decision-form"
          loading={loading}
          icon={decision?.action === "grant" ? <CheckCircleIcon /> : <CloseIcon />}
          sx={{ width: "auto" }}
        >
          Continue
        </SubmitButton>
      </DialogActions>
    </Dialog>
  );
}

export function ConsentWorkspace({
  consentStatus,
  requests,
  sessionToken,
  onRefresh,
}: ConsentWorkspaceProps) {
  const [decision, setDecision] = useState<PendingDecision | null>(null);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  async function submitDecision(values: ConsentDecisionValues) {
    if (!decision) return;
    setDecisionLoading(true);
    setDecisionError(null);
    try {
      await postJsonWithSession(
        `/consent/request/${decision.request.id}/${decision.action}`,
        values,
        sessionToken,
      );
      setDecision(null);
      onRefresh();
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Consent decision failed");
    } finally {
      setDecisionLoading(false);
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

      <Paper variant="outlined" sx={{ p: { xs: 2.5, md: 3 } }}>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
            <Box>
              <Typography variant="h2">Pending Consent Requests</Typography>
            </Box>
            <FactCheckIcon color="primary" />
          </Stack>

          {requests.length === 0 ? (
            <Alert severity="info">No pending consent requests.</Alert>
          ) : (
            <Stack spacing={1.5}>
              {requests.map((request) => (
                <Paper key={request.id} variant="outlined" sx={{ p: 2 }}>
                  <Grid container spacing={2} alignItems="center">
                    <Grid size={{ xs: 12, md: 3 }}>
                      <Typography variant="caption" color="text.secondary">
                        Requestor Name
                      </Typography>
                      <Typography>{request.requestor_name}</Typography>
                    </Grid>
                    <Grid size={{ xs: 12, md: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Requestor Role
                      </Typography>
                      <Typography>{request.requestor_role}</Typography>
                    </Grid>
                    <Grid size={{ xs: 12, md: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Consent Type
                      </Typography>
                      <Typography>{request.consent_type}</Typography>
                    </Grid>
                    <Grid size={{ xs: 12, md: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Request Date
                      </Typography>
                      <Typography>{formatDate(request.request_date)}</Typography>
                    </Grid>
                    <Grid size={{ xs: 12, md: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Status
                      </Typography>
                      <Box sx={{ mt: 0.5 }}>
                        <Chip size="small" color="warning" label={request.status} />
                      </Box>
                    </Grid>
                    <Grid size={{ xs: 12, md: 2 }}>
                      <Stack direction="row" spacing={1} justifyContent={{ md: "flex-end" }}>
                        <Button
                          variant="contained"
                          size="small"
                          onClick={() => setDecision({ action: "grant", request })}
                        >
                          Grant
                        </Button>
                        <Button
                          variant="outlined"
                          color="error"
                          size="small"
                          onClick={() => setDecision({ action: "reject", request })}
                        >
                          Reject
                        </Button>
                      </Stack>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>

      <ConsentDecisionDialog
        decision={decision}
        loading={decisionLoading}
        error={decisionError}
        onClose={() => {
          setDecision(null);
          setDecisionError(null);
        }}
        onSubmit={submitDecision}
      />
    </Stack>
  );
}
