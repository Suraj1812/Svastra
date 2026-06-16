import {
  Alert,
  Box,
  Grid,
  Paper,
  Skeleton,
  Snackbar,
  Stack,
  Step,
  StepLabel,
  Stepper,
} from "@mui/material";
import { DashboardShell } from "../../dashboard/DashboardShell";
import { CaregiverRegistrationForm } from "./forms/CaregiverRegistrationForm";
import { PatientRegistrationForm } from "./forms/PatientRegistrationForm";
import { ProviderRegistrationForm } from "./forms/ProviderRegistrationForm";
import { ClinicalMediaPanel } from "./ClinicalMediaPanel";
import { WorkflowNav } from "./WorkflowNav";
import { ConsentStep } from "./steps/ConsentStep";
import { MobileStep } from "./steps/MobileStep";
import { OtpStep } from "./steps/OtpStep";
import { useAuthWorkflow } from "../hooks/useAuthWorkflow";

function WorkflowSkeleton() {
  return (
    <Stack
      spacing={2}
      sx={{
        minHeight: "100vh",
        justifyContent: "center",
        px: { xs: 2, md: 8 },
        backgroundColor: "background.default",
      }}
    >
      <Skeleton variant="rounded" height={82} />
      <Skeleton variant="rounded" height={420} />
    </Stack>
  );
}

export function AuthWorkflow() {
  const workflow = useAuthWorkflow();

  if (workflow.booting) {
    return <WorkflowSkeleton />;
  }

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background:
          "linear-gradient(180deg, #f3fbf8 0%, #f7f9fc 34%, #ffffff 100%)",
      }}
    >


      {workflow.step !== "dashboard" && (
        <WorkflowNav
          activeStep={workflow.activeStep}
          mode={workflow.mode}
          steps={workflow.steps}
          onModeChange={workflow.switchMode}
        />
      )}

      <Box
        component="main"
        sx={{
          width: "100%",
          maxWidth: 1280,
          mx: "auto",
          px: { xs: 2, sm: 3, md: 4 },
          py: { xs: 2.5, md: 4 },
        }}
      >
        <Stack spacing={{ xs: 2.5, md: 3.5 }}>
          {workflow.error ? (
            <Alert severity="error" role="alert" aria-live="assertive">
              {workflow.error}
            </Alert>
          ) : null}

          {workflow.step === "dashboard" && workflow.auth ? (
            <DashboardShell
              auth={workflow.auth}
              onLogout={workflow.handleLogout}
              loggingOut={workflow.loading}
            />
          ) : (
            <Grid container spacing={{ xs: 2.5, lg: 3.5 }} alignItems="stretch">
              <Grid
                size={{ xs: 12, lg: 7 }}
                sx={{ display: "flex" }}
              >
                <Paper
                  variant="outlined"
                  sx={{
                    flex: 1,
                    p: { xs: 2.5, sm: 3.5, md: 5 },
                    height: "100%",
                    minHeight: { xs: 520, lg: 580 },
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "flex-start",
                    borderColor: "rgba(15, 118, 110, 0.16)",
                    boxShadow: "0 24px 70px rgba(15, 23, 42, 0.08)",
                  }}
                >
                  <Stepper
                    activeStep={workflow.activeStep}
                    alternativeLabel
                    sx={{
                      mb: 5,
                      "& .MuiStepLabel-label": {
                        typography: "caption",
                        color: "text.secondary",
                        mt: 0.75,
                      },
                      "& .Mui-active .MuiStepLabel-label, & .Mui-completed .MuiStepLabel-label":
                      {
                        color: "text.primary",
                        fontWeight: 700,
                      },
                    }}
                  >
                    {workflow.steps.map((label) => (
                      <Step key={label}>
                        <StepLabel>{label}</StepLabel>
                      </Step>
                    ))}
                  </Stepper>

                  {workflow.step === "mobile" ? (
                    <MobileStep
                      mode={workflow.mode}
                      loading={workflow.loading}
                      onSubmit={workflow.handleSendOtp}
                    />
                  ) : null}

                  {workflow.step === "otp" ? (
                    <OtpStep
                      mobile={workflow.mobile}
                      mode={workflow.mode}
                      loading={workflow.loading}
                      onBack={() => workflow.setStep("mobile")}
                      onSubmit={workflow.handleVerifyOtp}
                    />
                  ) : null}

                  {workflow.step === "registration" &&
                    workflow.mode === "provider" ? (
                    <ProviderRegistrationForm
                      mobile={workflow.mobile}
                      loading={workflow.loading}
                      onBack={() => workflow.setStep("otp")}
                      onSubmit={workflow.handleProviderRegistration}
                    />
                  ) : null}

                  {workflow.step === "registration" &&
                    workflow.mode === "patient" ? (
                    <PatientRegistrationForm
                      mobile={workflow.mobile}
                      onBack={() => workflow.setStep("otp")}
                      onSubmit={workflow.handlePatientForm}
                    />
                  ) : null}

                  {workflow.step === "registration" &&
                    workflow.mode === "caregiver" ? (
                    <CaregiverRegistrationForm
                      mobile={workflow.mobile}
                      loading={workflow.loading}
                      onBack={() => workflow.setStep("otp")}
                      onSubmit={workflow.handleCaregiverRegistration}
                    />
                  ) : null}

                  {workflow.step === "consent" ? (
                    <ConsentStep
                      loading={workflow.loading}
                      onBack={() => workflow.setStep("registration")}
                      onAccept={workflow.handleConsentAccept}
                    />
                  ) : null}
                </Paper>
              </Grid>
              <Grid
                size={{ xs: 12, lg: 5 }}
                sx={{ display: "flex" }}
              >
                <ClinicalMediaPanel mode={workflow.mode} step={workflow.step} />
              </Grid>
            </Grid>
          )}
        </Stack>
      </Box>

      <Snackbar
        open={Boolean(workflow.success)}
        autoHideDuration={3200}
        onClose={() => workflow.setSuccess(null)}
        message={workflow.success}
      />
    </Box>
  );
}
