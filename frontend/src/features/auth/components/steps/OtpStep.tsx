import { Button, Stack, TextField, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { SubmitButton } from "../../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../../shared/components/formHelpers";
import type { FlowMode } from "../../../../shared/types/auth";
import { otpSchema, type OtpValues } from "../../../../shared/validation/authSchemas";

type OtpStepProps = {
  mobile: string;
  mode: FlowMode;
  loading: boolean;
  onBack: () => void;
  onSubmit: (values: OtpValues) => void;
};

export function OtpStep({ mobile, mode, loading, onBack, onSubmit }: OtpStepProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<OtpValues>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  return (
    <Stack
      component="form"
      spacing={3}
      onSubmit={handleSubmit(onSubmit)}
      noValidate
      sx={{ maxWidth: 520 }}
    >
      <Stack spacing={0.75}>
        <Typography variant="caption" color="text.secondary">
          OTP Verification
        </Typography>
        <Typography variant="h1">{mobile}</Typography>
      </Stack>
      <TextField
        label="OTP"
        autoComplete="one-time-code"
        inputMode="numeric"
        error={Boolean(errors.otp)}
        helperText={fieldHelperText(errors.otp?.message)}
        {...register("otp")}
      />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={onBack} fullWidth>
          Back
        </Button>
        <SubmitButton loading={loading} icon={<VerifiedUserIcon />}>
          {mode === "login" ? "Verify & Login" : "Verify & Continue"}
        </SubmitButton>
      </Stack>
    </Stack>
  );
}
