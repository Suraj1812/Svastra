import {
  Button,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormHelperText,
  Grid,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";

import { SubmitButton } from "../../../../shared/components/SubmitButton";
import { fieldHelperText } from "../../../../shared/components/formHelpers";
import { occupations } from "../../../../shared/config/registrationOptions";
import {
  providerSchema,
  type ProviderValues,
} from "../../../../shared/validation/authSchemas";

type ProviderRegistrationFormProps = {
  mobile: string;
  loading: boolean;
  onBack: () => void;
  onSubmit: (values: ProviderValues) => void;
};

export function ProviderRegistrationForm({
  mobile,
  loading,
  onBack,
  onSubmit,
}: ProviderRegistrationFormProps) {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProviderValues>({
    resolver: zodResolver(providerSchema),
    defaultValues: {
      full_name: "",
      mobile_number: mobile,
      email_address: "",
      professional_category: "",
      registration_number: "",
      hpid_number: "",
      terms_accepted: false,
    },
  });

  return (
    <Stack component="form" spacing={3.25} onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h2">Provider Registration Form</Typography>
      <Grid container spacing={2.25}>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Full Name"
            autoComplete="name"
            error={Boolean(errors.full_name)}
            helperText={fieldHelperText(errors.full_name?.message)}
            {...register("full_name")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Mobile Number"
            autoComplete="tel"
            error={Boolean(errors.mobile_number)}
            helperText={fieldHelperText(errors.mobile_number?.message)}
            {...register("mobile_number")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Email Address"
            autoComplete="email"
            error={Boolean(errors.email_address)}
            helperText={fieldHelperText(errors.email_address?.message)}
            {...register("email_address")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Controller
            name="professional_category"
            control={control}
            render={({ field }) => (
              <TextField
                select
                SelectProps={{ native: true }}
                label="Professional Category"
                error={Boolean(errors.professional_category)}
                helperText={fieldHelperText(errors.professional_category?.message)}
                {...field}
                value={field.value || ""}
              >
                <option value="" aria-label="Select professional category" />
                {occupations.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </TextField>
            )}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Registration Number"
            error={Boolean(errors.registration_number)}
            helperText={fieldHelperText(errors.registration_number?.message)}
            {...register("registration_number")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="HPID Number"
            error={Boolean(errors.hpid_number)}
            helperText={fieldHelperText(errors.hpid_number?.message)}
            {...register("hpid_number")}
          />
        </Grid>
      </Grid>
      <Controller
        name="terms_accepted"
        control={control}
        render={({ field }) => (
          <FormControl error={Boolean(errors.terms_accepted)}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={Boolean(field.value)}
                  onBlur={field.onBlur}
                  onChange={(_, checked) => field.onChange(checked)}
                  inputRef={field.ref}
                />
              }
              label="Terms Acceptance"
            />
            <FormHelperText>{fieldHelperText(errors.terms_accepted?.message)}</FormHelperText>
          </FormControl>
        )}
      />
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="outlined" startIcon={<ArrowBackIcon />} onClick={onBack} fullWidth>
          Back
        </Button>
        <SubmitButton loading={loading} icon={<CheckCircleIcon />}>
          Complete Registration
        </SubmitButton>
      </Stack>
    </Stack>
  );
}
