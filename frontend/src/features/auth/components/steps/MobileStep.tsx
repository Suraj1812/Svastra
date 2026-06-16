import { Stack, TextField, Typography } from "@mui/material";
import MarkunreadMailboxIcon from "@mui/icons-material/MarkunreadMailbox";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { SubmitButton } from "../../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../../shared/components/formHelpers";
import { modeLabels } from "../../../../shared/config/registrationOptions";
import type { FlowMode } from "../../../../shared/types/auth";
import {
  mobileSchema,
  type MobileValues,
} from "../../../../shared/validation/authSchemas";

type MobileStepProps = {
  mode: FlowMode;
  loading: boolean;
  onSubmit: (values: MobileValues) => void;
};

export function MobileStep({ mode, loading, onSubmit }: MobileStepProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MobileValues>({
    resolver: zodResolver(mobileSchema),
    defaultValues: { mobile_number: "" },
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
          Mobile Number
        </Typography>
        <Typography variant="h1">{mode === "login" ? "Login" : modeLabels[mode]}</Typography>
      </Stack>
      <TextField
        label="Mobile Number"
        autoComplete="tel"
        inputMode="tel"
        error={Boolean(errors.mobile_number)}
        helperText={fieldHelperText(errors.mobile_number?.message)}
        {...register("mobile_number")}
      />
      <SubmitButton loading={loading} icon={<MarkunreadMailboxIcon />}>
        Send OTP
      </SubmitButton>
    </Stack>
  );
}
