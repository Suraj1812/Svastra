import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormHelperText,
  Paper,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";

import { apiRequest } from "../../../../shared/api/client";
import { SubmitButton } from "../../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../../shared/components/formHelpers";
import type { ConsentDocument } from "../../../../shared/types/auth";
import {
  consentSchema,
  type ConsentValues,
} from "../../../../shared/validation/authSchemas";
import { getErrorMessage } from "../../hooks/workflowUtils";

type ConsentStepProps = {
  loading: boolean;
  onBack: () => void;
  onAccept: (values: ConsentValues) => void;
};

function MarkdownConsent({ document }: { document: string }) {
  const lines = document.split("\n").filter((line) => line.trim().length > 0);

  return (
    <Stack spacing={1.25}>
      {lines.map((line, index) => {
        if (line.startsWith("# ")) {
          return (
            <Typography key={index} variant="h3">
              {line.replace("# ", "")}
            </Typography>
          );
        }
        return (
          <Typography key={index} color="text.secondary">
            {line}
          </Typography>
        );
      })}
    </Stack>
  );
}

export function ConsentStep({ loading, onBack, onAccept }: ConsentStepProps) {
  const [consent, setConsent] = useState<ConsentDocument | null>(null);
  const [documentLoading, setDocumentLoading] = useState(true);
  const [documentError, setDocumentError] = useState<string | null>(null);
  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<ConsentValues>({
    resolver: zodResolver(consentSchema),
    defaultValues: { unified_consent_accepted: false },
  });

  useEffect(() => {
    let active = true;
    setDocumentLoading(true);
    apiRequest<ConsentDocument>("/consent/current")
      .then((data) => {
        if (active) {
          setConsent(data);
          setDocumentError(null);
        }
      })
      .catch((error) => {
        if (active) {
          setDocumentError(getErrorMessage(error));
        }
      })
      .finally(() => {
        if (active) {
          setDocumentLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <Stack component="form" spacing={3} onSubmit={handleSubmit(onAccept)} noValidate>
      <Stack spacing={0.75}>
        <Typography variant="caption" color="text.secondary">
          Unified Consent Display
        </Typography>
        <Typography variant="h2">{consent?.consent_version || "Loading"}</Typography>
      </Stack>

      <Paper
        variant="outlined"
        tabIndex={0}
        aria-label="Unified Consent Document"
        sx={{
          p: { xs: 2, sm: 2.5 },
          maxHeight: 320,
          overflow: "auto",
          backgroundColor: "#f8fafc",
        }}
      >
        {documentLoading ? (
          <Stack spacing={1.5}>
            <Skeleton height={28} width="55%" />
            <Skeleton height={18} />
            <Skeleton height={18} />
            <Skeleton height={18} width="72%" />
          </Stack>
        ) : documentError ? (
          <Alert severity="error">{documentError}</Alert>
        ) : (
          <MarkdownConsent document={consent?.document || ""} />
        )}
      </Paper>

      <Controller
        name="unified_consent_accepted"
        control={control}
        render={({ field }) => (
          <FormControl error={Boolean(errors.unified_consent_accepted)}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={Boolean(field.value)}
                  onBlur={field.onBlur}
                  onChange={(_, checked) => field.onChange(checked)}
                  inputRef={field.ref}
                />
              }
              label="I have read and understood the consent"
            />
            <FormHelperText>
              {fieldHelperText(errors.unified_consent_accepted?.message)}
            </FormHelperText>
          </FormControl>
        )}
      />

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={onBack} fullWidth>
          Back
        </Button>
        <SubmitButton loading={loading} icon={<CheckCircleIcon />}>
          Accept & Continue
        </SubmitButton>
      </Stack>
    </Stack>
  );
}
