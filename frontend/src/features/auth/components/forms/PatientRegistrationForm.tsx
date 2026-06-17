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
import FactCheckIcon from "@mui/icons-material/FactCheck";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";

import { fieldHelperText } from "../../../../shared/components/formHelpers";
import { findReferenceTerm, genders, languages } from "../../../../shared/config/registrationOptions";
import { patientSchema, type PatientValues } from "../../../../shared/validation/authSchemas";

type PatientRegistrationFormProps = {
  mobile: string;
  onBack: () => void;
  onSubmit: (values: PatientValues) => void;
};

export function PatientRegistrationForm({
  mobile,
  onBack,
  onSubmit,
}: PatientRegistrationFormProps) {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<PatientValues>({
    resolver: zodResolver(patientSchema),
    defaultValues: {
      full_name: "",
      mobile_number: mobile,
      date_of_birth: "",
      gender: undefined,
      preferred_language: undefined,
      abha_number: "",
      emergency_contact_name: "",
      emergency_contact_mobile: "",
      terms_accepted: false,
    },
  });

  return (
    <Stack component="form" spacing={3.25} onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h2">Patient Registration Form</Typography>
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
            label="Date Of Birth"
            type="date"
            slotProps={{ inputLabel: { shrink: true } }}
            error={Boolean(errors.date_of_birth)}
            helperText={fieldHelperText(errors.date_of_birth?.message)}
            {...register("date_of_birth")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Controller
            name="gender"
            control={control}
            render={({ field }) => (
              <TextField
                select
                SelectProps={{ native: true }}
                label="Gender"
                error={Boolean(errors.gender)}
                helperText={fieldHelperText(errors.gender?.message)}
                {...field}
                value={field.value?.conceptId || ""}
                onChange={(event) =>
                  field.onChange(findReferenceTerm(genders, event.target.value) || undefined)
                }
              >
                <option value="" aria-label="Select gender" />
                {genders.map((option) => (
                  <option key={option.conceptId} value={option.conceptId}>
                    {option.term}
                  </option>
                ))}
              </TextField>
            )}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Controller
            name="preferred_language"
            control={control}
            render={({ field }) => (
              <TextField
                select
                SelectProps={{ native: true }}
                label="Preferred Language"
                error={Boolean(errors.preferred_language)}
                helperText={fieldHelperText(errors.preferred_language?.message)}
                {...field}
                value={field.value?.conceptId || ""}
                onChange={(event) =>
                  field.onChange(findReferenceTerm(languages, event.target.value) || undefined)
                }
              >
                <option value="" aria-label="Select preferred language" />
                {languages.map((option) => (
                  <option key={option.conceptId} value={option.conceptId}>
                    {option.term}
                  </option>
                ))}
              </TextField>
            )}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="ABHA Number"
            error={Boolean(errors.abha_number)}
            helperText={fieldHelperText(errors.abha_number?.message)}
            {...register("abha_number")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Emergency Contact Name"
            error={Boolean(errors.emergency_contact_name)}
            helperText={fieldHelperText(errors.emergency_contact_name?.message)}
            {...register("emergency_contact_name")}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <TextField
            label="Emergency Contact Mobile"
            autoComplete="tel"
            error={Boolean(errors.emergency_contact_mobile)}
            helperText={fieldHelperText(errors.emergency_contact_mobile?.message)}
            {...register("emergency_contact_mobile")}
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
        <Button type="submit" variant="contained" size="large" fullWidth startIcon={<FactCheckIcon />}>
          Review Unified Consent
        </Button>
      </Stack>
    </Stack>
  );
}
