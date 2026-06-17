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
import {
  findReferenceTerm,
  languages,
  relationships,
} from "../../../../shared/config/registrationOptions";
import {
  caregiverSchema,
  type CaregiverValues,
} from "../../../../shared/validation/authSchemas";

type CaregiverRegistrationFormProps = {
  mobile: string;
  loading: boolean;
  onBack: () => void;
  onSubmit: (values: CaregiverValues) => void;
};

export function CaregiverRegistrationForm({
  mobile,
  loading,
  onBack,
  onSubmit,
}: CaregiverRegistrationFormProps) {
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CaregiverValues>({
    resolver: zodResolver(caregiverSchema),
    defaultValues: {
      full_name: "",
      mobile_number: mobile,
      relationship_to_patient: undefined,
      preferred_language: undefined,
      terms_accepted: false,
    },
  });

  return (
    <Stack component="form" spacing={3.25} onSubmit={handleSubmit(onSubmit)} noValidate>
      <Typography variant="h2">Caregiver Registration Form</Typography>
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
          <Controller
            name="relationship_to_patient"
            control={control}
            render={({ field }) => (
              <TextField
                select
                SelectProps={{ native: true }}
                label="Relationship To Patient"
                error={Boolean(errors.relationship_to_patient)}
                helperText={fieldHelperText(errors.relationship_to_patient?.message)}
                {...field}
                value={field.value?.conceptId || ""}
                onChange={(event) =>
                  field.onChange(findReferenceTerm(relationships, event.target.value) || undefined)
                }
              >
                <option value="" aria-label="Select relationship to patient" />
                {relationships.map((option) => (
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
